"""Coordinate specialists, oversight, and synthesis independently of FastAPI."""
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


class Coordinator:
    def __init__(self, runner: AgentRunner):
        self.runner = runner

    async def events(
        self, request: RunInput, model: str, specialists: list[AgentDefinition],
        oversight: AgentDefinition, synthesizer: AgentDefinition,
        run_id: str | None = None,
    ) -> AsyncIterator[RunEvent]:
        run_id, sequence, started = run_id or uuid4().hex, 0, time.monotonic()
        findings: list[tuple[str, str]] = []
        failed: list[str] = []

        def event(kind: EventType, **data) -> RunEvent:
            nonlocal sequence
            sequence += 1
            return RunEvent(type=kind, sequence=sequence, run_id=run_id, timestamp=timestamp(), **data)

        def context() -> str:
            # Bound accumulated context for the local model's context window.
            per_finding = min(1600, 8000 // max(1, len(findings)))
            reports = "\n\n".join(
                f"### {name}\n{text[:per_finding]}" + ("\n[Truncated for context limit]" if len(text) > per_finding else "")
                for name, text in findings
            )
            missing = f"\nMissing assessments: {', '.join(failed)}" if failed else ""
            return f"Scenario:\n{request.scenario}\n\nAssessments:\n{reports}{missing}"

        workflow = [*specialists]
        if request.require_approval:
            workflow.append(oversight)
        workflow.append(synthesizer)
        yield event("start", model=model, agents=[a.id for a in workflow])
        try:
            for config in workflow:
                if config.core and not findings:
                    yield event("error", message="No specialist returned a finding. Check the local model.")
                    return
                prompt = f"Enterprise scenario:\n{request.scenario}\n\nProvide your specialist assessment."
                if config.core:
                    prompt = context()
                if config.id == synthesizer.id:
                    approval = "Human decision owner review is required." if request.require_approval else "Operator has not required review; flag additional review needs."
                    prompt += f"\n\n{approval} Include rejected alternatives and uncertainty."
                yield event("agent_start", agent_id=config.id, name=config.name)
                agent_started = time.monotonic()
                try:
                    output = await self.runner.run(config, model, prompt)
                    findings.append((config.name, output))
                    yield event("agent_done", agent_id=config.id, name=config.name, content=output,
                                duration_ms=round((time.monotonic() - agent_started) * 1000))
                except Exception as exc:
                    failed.append(config.name)
                    message = "Agent response timed out. Reduce scenario size or increase AGENT_TIMEOUT_SECONDS." if isinstance(exc, asyncio.TimeoutError) else "Agent request failed. Check your model server and its model support."
                    yield event("agent_error", agent_id=config.id, name=config.name, message=message,
                                duration_ms=round((time.monotonic() - agent_started) * 1000))
                    if config.id == synthesizer.id:
                        yield event("error", message="Synthesis failed. Specialist findings are still available.")
                        return
            yield event("complete", elapsed_ms=round((time.monotonic() - started) * 1000),
                        human_approval_required=request.require_approval, degraded=bool(failed))
        except asyncio.CancelledError:
            # Client disconnect cancels the current async model request.
            raise
