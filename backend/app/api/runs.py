"""Run validation and SSE transport; coordination lives in its own service."""
import asyncio
from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import StreamingResponse

from backend.app.api.dependencies import history, run_service
from backend.app.schemas.runs import RunInput
from backend.app.schemas.reviews import ReviewInput
from backend.app.storage.runs import RunRepository
from backend.app.services.runs import RunService

router = APIRouter(tags=["runs"])


async def stream_events(events):
    """Send heartbeats while a model is busy, cancelling work on disconnect."""
    iterator = events.__aiter__()
    task = None
    try:
        while True:
            task = asyncio.create_task(anext(iterator))
            while not task.done():
                done, _ = await asyncio.wait({task}, timeout=10)
                if not done:
                    yield ": keepalive\n\n"
            try:
                yield task.result().sse()
            except StopAsyncIteration:
                break
    finally:
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError, StopAsyncIteration):
                await task
        await iterator.aclose()


@router.post("/api/run")
async def run(
    body: RunInput,
    service: Annotated[RunService, Depends(run_service)],
):
    events = await service.prepare(body)
    return StreamingResponse(
        stream_events(events), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post('/api/runs/{run_id}/review')
async def submit_review(run_id: str, body: ReviewInput, service: Annotated[RunService, Depends(run_service)]):
    events = await service.review(run_id, body)
    return StreamingResponse(stream_events(events), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@router.post('/api/runs/{run_id}/cancel', status_code=204)
def cancel_review(run_id: str, repository: Annotated[RunRepository, Depends(history)]):
    repository.cancel_review(run_id)
    return Response(status_code=204)
