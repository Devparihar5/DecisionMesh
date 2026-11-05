"""Coordinate analysis, a durable human checkpoint, and final synthesis."""
import asyncio
import time
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import uuid4

from backend.app.orchestration.events import EventType, RunEvent, timestamp
from backend.app.schemas.agents import AgentDefinition
from backend.app.schemas.runs import RunInput


class AgentRunner(Protocol):
    async def run(self, config: AgentDefinition, model_id: str, prompt: str) -> str: ...


def shared_context(scenario: str, findings: list[tuple[str, str]], failed: list[str], feedback: str = '') -> str:
    per_finding = min(1600, 8000 // max(1, len(findings)))
    reports = '\n\n'.join(
        f'### {name}\n{text[:per_finding]}' + ('\n[Truncated for context limit]' if len(text) > per_finding else '')
        for name, text in findings
    )
    missing = f"\nMissing assessments: {', '.join(failed)}" if failed else ''
    guidance = f'\n\nOperator suggestions:\n{feedback}' if feedback else ''
    return f'Scenario:\n{scenario}\n\nAssessments:\n{reports}{missing}{guidance}'


class EventSequence:
    def __init__(self, run_id: str, sequence: int = 0):
        self.run_id, self.sequence = run_id, sequence

    def emit(self, kind: EventType, **data) -> RunEvent:
        self.sequence += 1
        return RunEvent(type=kind, sequence=self.sequence, run_id=self.run_id, timestamp=timestamp(), **data)


class Coordinator:
    def __init__(self, runner: AgentRunner):
        self.runner = runner

    async def events(
        self, request: RunInput, model: str, specialists: list[AgentDefinition],
        oversight: AgentDefinition, synthesizer: AgentDefinition,
        run_id: str | None = None, feedback: str = '', parent_run_id: str | None = None,
    ) -> AsyncIterator[RunEvent]:
        sequence = EventSequence(run_id or uuid4().hex)
        findings: list[tuple[str, str]] = []
        failed: list[str] = []
        started = time.monotonic()
        analysis = [*specialists, *([oversight] if request.require_approval else [])]
        yield sequence.emit('start', model=model, agents=[agent.id for agent in [*analysis, synthesizer]], parent_run_id=parent_run_id)
        for config in analysis:
            if config.core and not findings:
                yield sequence.emit('error', message='No specialist returned a finding. Check the local model.')
                return
            prompt = shared_context(request.scenario, findings, failed, feedback) if config.core else (
                f'Enterprise scenario:\n{request.scenario}\n\nOperator suggestions:\n{feedback or "None supplied."}\n\nProvide your specialist assessment.'
            )
            yield sequence.emit('agent_start', agent_id=config.id, name=config.name)
            agent_started = time.monotonic()
            try:
                output = await self.runner.run(config, model, prompt)
                findings.append((config.name, output))
                yield sequence.emit('agent_done', agent_id=config.id, name=config.name, content=output,
                                    duration_ms=round((time.monotonic() - agent_started) * 1000))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failed.append(config.name)
                message = 'Agent response timed out. Reduce scenario size or increase AGENT_TIMEOUT_SECONDS.' if isinstance(exc, asyncio.TimeoutError) else 'Agent request failed. Check your model server and its model support.'
                yield sequence.emit('agent_error', agent_id=config.id, name=config.name, message=message,
                                    duration_ms=round((time.monotonic() - agent_started) * 1000))
        if not findings:
            yield sequence.emit('error', message='No specialist returned a finding. Check the local model.')
            return
        if request.require_approval:
            assessment = next((text for name, text in findings if name == oversight.name), None)
            yield sequence.emit('review_required', agent_id=oversight.id, name='Your review', content=assessment,
                                message='Review the findings. Add suggestions, then rerun the agents or generate the final brief.',
                                degraded=bool(failed), elapsed_ms=round((time.monotonic() - started) * 1000))
            return
        async for event in self.synthesize(request, model, synthesizer, findings, failed, sequence, feedback, human_reviewed=False):
            yield event

    async def synthesize(
        self, request: RunInput, model: str, synthesizer: AgentDefinition,
        findings: list[tuple[str, str]], failed: list[str], sequence: EventSequence,
        feedback: str = '', human_reviewed: bool = True,
    ) -> AsyncIterator[RunEvent]:
        prompt = shared_context(request.scenario, findings, failed, feedback)
        prompt += ('\n\nThe operator reviewed these findings and chose to generate a final brief. Incorporate their suggestions; explain any suggestion you cannot support with evidence.'
                   if human_reviewed else '\n\nThe operator did not require a review checkpoint. Flag any additional review needs.')
        prompt += '\nInclude rejected alternatives, uncertainties, and next steps. Do not claim external actions were executed.'
        yield sequence.emit('agent_start', agent_id=synthesizer.id, name=synthesizer.name)
        started = time.monotonic()
        try:
            output = await self.runner.run(synthesizer, model, prompt)
            yield sequence.emit('agent_done', agent_id=synthesizer.id, name=synthesizer.name, content=output,
                                duration_ms=round((time.monotonic() - started) * 1000))
        except asyncio.CancelledError:
            raise
        except Exception:
            yield sequence.emit('agent_error', agent_id=synthesizer.id, name=synthesizer.name,
                                message='Synthesis failed. Specialist findings are retained.', duration_ms=round((time.monotonic() - started) * 1000))
            yield sequence.emit('error', message='Synthesis failed. Specialist findings are still available.')
            return
        yield sequence.emit('complete', human_approval_required=False, human_reviewed=human_reviewed, degraded=bool(failed))
