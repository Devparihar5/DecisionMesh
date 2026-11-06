"""Supervise bounded local jobs; retain partial progress and interrupted outcomes."""
import asyncio
import time
from collections.abc import Awaitable, Callable

from backend.app.agents.factory import AgnoRunner, agno_available
from backend.app.agents.registry import AgentRegistry
from backend.app.core.errors import ApplicationError
from backend.app.orchestration.negotiation import apply_resolution, arbitrate, parse_proposal, proposal_prompt
from backend.app.schemas.agents import AgentDefinition
from backend.app.schemas.enterprise import AgentProposal, DecisionCase, Job, NegotiationRound
from backend.app.services.models import ModelService
from backend.app.storage.enterprise import EnterpriseRepository


class ResearchJobs:
    def __init__(self, repository: EnterpriseRepository, models: ModelService, registry: AgentRegistry, runner: AgnoRunner):
        self.repository, self.models, self.registry, self.runner = repository, models, registry, runner
        self.tasks: dict[str, asyncio.Task] = {}

    async def resolve_model(self, requested: str) -> str:
        if not agno_available():
            raise ApplicationError('Agno is missing. Run poetry install.', 503)
        return await self.models.resolve(requested)

    def start(self, job: Job, work: Callable[[], Awaitable[dict]]) -> None:
        async def run() -> None:
            try:
                result = await work()
                self.repository.update_job(job.id, status='complete', result=result)
            except asyncio.CancelledError:
                self.repository.update_job(job.id, status='cancelled', error='Job cancelled; partial progress retained.')
                raise
            except Exception as exc:
                detail = exc.detail if isinstance(exc, ApplicationError) else 'Job failed. Check model availability and saved progress.'
                self.repository.update_job(job.id, status='failed', error=detail)
            finally:
                self.tasks.pop(job.id, None)
        self.tasks[job.id] = asyncio.create_task(run())
        self.tasks[job.id].add_done_callback(lambda _: self.tasks.pop(job.id, None))

    async def shutdown(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def cancel(self, job_id: str) -> Job:
        job = self.repository.job(job_id)
        if job.status == 'running':
            task = self.tasks.get(job_id)
            if task:
                task.cancel()
            return self.repository.update_job(job_id, status='cancelled', error='Operator cancelled this job.')
        return job

    async def collect_proposal(self, agent: AgentDefinition, case: DecisionCase, model: str, prompt: str,
                               number: int, progress: Callable[[dict], None]) -> tuple[AgentProposal | None, str | None]:
        total_duration = 0
        for attempt in (1, 2):
            started = time.perf_counter()
            progress({'stage': 'agent_start', 'agent': agent.id, 'round': number, 'attempt': attempt, 'prompt': prompt})
            try:
                output = await self.runner.propose(agent, model, prompt)
            except asyncio.CancelledError:
                raise
            except Exception:
                progress({'stage': 'agent_error', 'agent': agent.id, 'round': number, 'attempt': attempt,
                          'duration_ms': round((time.perf_counter() - started) * 1000)})
                return None, f'{agent.id}: provider request failed or timed out'
            duration = round((time.perf_counter() - started) * 1000)
            total_duration += duration
            try:
                parsed = parse_proposal(output, case.evidence)
            except (ValueError, TypeError):
                progress({'stage': 'invalid_proposal', 'agent': agent.id, 'round': number, 'attempt': attempt,
                          'duration_ms': duration, 'raw_output': output[:4000]})
                prompt += ('\nYour previous answer was invalid JSON, failed the schema, or cited unsupported evidence. '
                           'Return exactly action, reason, evidence. Use only E1/E2 references listed above; '
                           'keep reason to one short sentence. Previous answer to correct:\n' + output[:1500])
            else:
                proposal = AgentProposal(**parsed.model_dump(), agent_id=agent.id, round=number, duration_ms=total_duration)
                progress({'stage': 'proposal', 'attempt': attempt, **proposal.model_dump()})
                return proposal, None
        return None, f'{agent.id}: invalid structured proposal or unsupported evidence after one repair'

    async def rounds(self, case: DecisionCase, agents: list[AgentDefinition], model: str,
                     progress: Callable[[dict], None]) -> list[NegotiationRound]:
        rounds: list[NegotiationRound] = []
        for number in (1, 2):
            proposals: list[AgentProposal] = []
            errors: list[str] = []
            prompt = proposal_prompt(case, rounds[-1] if rounds else None)
            for agent in agents:
                proposal, error = await self.collect_proposal(agent, case, model, prompt, number, progress)
                if proposal:
                    proposals.append(proposal)
                if error:
                    errors.append(error)
            resolved = arbitrate(proposals, case.candidates, number, errors)
            rounds.append(resolved)
            progress({'stage': 'arbitration', **resolved.model_dump()})
            # One peer exchange is sufficient when the first round is unanimous and valid.
            if not resolved.conflicts and not errors:
                break
        return rounds

    async def negotiate(self, case_id: str, model_id: str, selected: list[str]) -> Job:
        agents = self.registry.specialists(list(dict.fromkeys(selected)))
        if len(agents) < 2:
            raise ApplicationError('Choose at least two different specialist agents.')
        model = await self.resolve_model(model_id)
        case, revision = self.repository.case_revision(case_id)
        job = self.repository.create_job('negotiation', case_id, {'case_id': case_id, 'model': model,
            'rule_version': case.rule_version, 'state_version': case.state_version,
            'agents': [agent.model_dump() for agent in agents], 'max_rounds': 2, 'max_format_repairs': 1,
            'prompt_template_version': 'inventory-proposal-v2'})

        async def work() -> dict:
            rounds = await self.rounds(case, agents, model, lambda event: self.repository.update_job(job.id, progress=event))
            resolved = apply_resolution(case, [*case.rounds, *rounds])
            self.repository.save_negotiation(resolved, revision, job.id)
            return {'case_id': case.id, 'selected_action': resolved.selected_action,
                    'requires_review': resolved.requires_review, 'rounds': len(rounds)}
        self.start(job, work)
        return job
