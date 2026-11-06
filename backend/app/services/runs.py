"""Durable execution, human review, and revision lifecycle."""
import asyncio
import json
from collections.abc import AsyncIterator

from backend.app.agents.factory import agno_available
from backend.app.agents.registry import AgentRegistry
from backend.app.core.errors import ApplicationError
from backend.app.orchestration.coordinator import Coordinator, EventSequence
from backend.app.orchestration.events import RunEvent, timestamp
from backend.app.schemas.history import RunDetail
from backend.app.schemas.reviews import ReviewInput
from backend.app.schemas.runs import RunInput
from backend.app.services.models import ModelService
from backend.app.storage.runs import RunRepository
from backend.app.services.enterprise import EnterpriseService


class RunService:
    def __init__(self, registry: AgentRegistry, models: ModelService, coordinator: Coordinator, history: RunRepository,
                 enterprise: EnterpriseService | None = None):
        self.registry, self.models, self.coordinator, self.history = registry, models, coordinator, history
        self.enterprise = enterprise

    async def prepare(self, request: RunInput) -> AsyncIterator[RunEvent]:
        if request.decision_case_id:
            if not self.enterprise:
                raise ApplicationError('Enterprise decision context is unavailable.', 503)
            case = self.enterprise.repository.case(request.decision_case_id)
            current = self.enterprise.repository.entity(case.entity_id)
            if current.version != case.state_version or case.execution_id:
                raise ApplicationError('This enterprise decision is stale or executed. Open its latest reassessment.', 409)
            context = {'case_id': case.id, 'state_version': case.state_version, 'state': case.state.state.model_dump(),
                'source_evidence': case.evidence, 'selected_action': case.selected_action,
                'candidate_simulations': [item.model_dump() for item in case.candidates],
                'policy_review_reasons': case.review_reasons,
                'agent_proposals': [{'agent': item.agent_id, 'action': item.action, 'reason': item.reason[:300]}
                                    for item in case.rounds[-1].proposals]}
            scenario = request.scenario + '\n\nNormalized enterprise decision evidence (local simulation only):\n' + json.dumps(context, ensure_ascii=False)
            if len(scenario) > 6000:
                raise ApplicationError('Shorten the scenario to leave room for the enterprise evidence snapshot.')
            request = request.model_copy(update={'scenario': scenario, 'require_approval': request.require_approval or case.requires_review})
        specialists = self.registry.specialists(request.selected_agents)
        oversight, synth = self.registry.get('human_review'), self.registry.get('decision_synth')
        workflow = [*specialists, *([oversight] if request.require_approval else []), synth]
        run_id = self.history.create(request, workflow)
        try:
            if not agno_available():
                raise ApplicationError('Agno is missing. Run poetry install.', 503)
            model = await self.models.resolve(request.model)
        except asyncio.CancelledError:
            self.history.finish(run_id, 'cancelled', 'Request cancelled during model discovery.')
            raise
        except Exception:
            self.history.finish(run_id, 'failed', 'Model discovery or agent runtime unavailable before generation.')
            raise
        source = self.coordinator.events(request, model, specialists, oversight, synth, run_id=run_id)
        return self._record(source, run_id)

    async def review(self, run_id: str, decision: ReviewInput) -> AsyncIterator[RunEvent]:
        saved = self.history.detail(run_id)
        if saved.status != 'awaiting_review':
            raise ApplicationError('This run is no longer waiting for review.', 409)
        # Resolve first: an unavailable server leaves the review safely pending.
        model = await self.models.resolve(saved.model)
        request = RunInput(scenario=saved.scenario, model=model,
                           selected_agents=[agent.id for agent in saved.agents if not agent.core], require_approval=True,
                           decision_case_id=next((event.decision_case_id for event in saved.events if event.type == 'start'), None))
        guidance = '\n\n'.join(value for value in [saved.input_feedback, decision.feedback] if value)[-4000:]
        target_id, submitted = self.history.accept_review(run_id, decision, request, saved.agents, guidance)
        if decision.action == 'rerun':
            specialists = [agent for agent in saved.agents if not agent.core]
            oversight = next(agent for agent in saved.agents if agent.id == 'human_review')
            synth = next(agent for agent in saved.agents if agent.id == 'decision_synth')
            source = self.coordinator.events(request, model, specialists, oversight, synth,
                                             run_id=target_id, feedback=guidance, parent_run_id=run_id)
            return self._record(source, target_id)
        return self._record(self._finalize(saved, request, model, guidance, submitted), run_id, submitted.sequence)

    async def _finalize(self, saved: RunDetail, request: RunInput, model: str,
                        guidance: str, submitted: RunEvent) -> AsyncIterator[RunEvent]:
        # The review event was stored atomically with the claim; send it once.
        yield submitted
        findings = [(item.name, item.content) for item in saved.executions if item.status == 'complete' and item.content]
        failed = [item.name for item in saved.executions if item.status == 'failed']
        synth = next(agent for agent in saved.agents if agent.id == 'decision_synth')
        async for event in self.coordinator.synthesize(request, model, synth, findings, failed,
                                                       EventSequence(saved.id, submitted.sequence), guidance):
            yield event

    async def _record(self, source: AsyncIterator[RunEvent], run_id: str, sequence: int = 0) -> AsyncIterator[RunEvent]:
        try:
            async for event in source:
                if event.type in {'complete', 'error'}:
                    event.elapsed_ms = self.history.elapsed_ms(run_id)
                # Submitted review is already committed with the exclusive claim.
                if event.type != 'review_submitted':
                    self.history.record(event)
                sequence = event.sequence
                yield event
        except (asyncio.CancelledError, GeneratorExit):
            self.history.finish(run_id, 'cancelled', 'Workflow stopped or client disconnected.')
            raise
        except Exception:
            event = RunEvent(sequence=sequence + 1, run_id=run_id, timestamp=timestamp(), type='error',
                             message='Workflow failed unexpectedly. Partial findings were retained in local memory.')
            self.history.record(event)
            yield event
        finally:
            try:
                await source.aclose()
            finally:
                # A persisted awaiting_review state deliberately survives closure.
                self.history.finish(run_id, 'cancelled', 'Workflow stopped before a terminal event.')
