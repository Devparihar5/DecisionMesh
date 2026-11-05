"""Durable run lifecycle around the transport-independent coordinator."""
import asyncio
from collections.abc import AsyncIterator

from backend.app.agents.factory import agno_available
from backend.app.agents.registry import AgentRegistry
from backend.app.core.errors import ApplicationError
from backend.app.orchestration.coordinator import Coordinator
from backend.app.orchestration.events import RunEvent, timestamp
from backend.app.schemas.runs import RunInput
from backend.app.services.models import ModelService
from backend.app.storage.runs import RunRepository


class RunService:
    def __init__(self, registry: AgentRegistry, models: ModelService, coordinator: Coordinator, history: RunRepository):
        self.registry = registry
        self.models = models
        self.coordinator = coordinator
        self.history = history

    async def prepare(self, request: RunInput) -> AsyncIterator[RunEvent]:
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

    async def _record(self, source: AsyncIterator[RunEvent], run_id: str) -> AsyncIterator[RunEvent]:
        sequence = 0
        try:
            async for event in source:
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
                # Also covers closing an iterator between emitted events.
                self.history.finish(run_id, 'cancelled', 'Workflow stopped before a terminal event.')
