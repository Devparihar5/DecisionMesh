"""Version 1 of the SSE event envelope shared with the React client."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

EventType = Literal["start", "agent_start", "agent_done", "agent_error", "complete", "error", "review_required", "review_submitted"]


class RunEvent(BaseModel):
    version: int = 1
    sequence: int
    run_id: str
    timestamp: str
    type: EventType
    agent_id: str | None = None
    name: str | None = None
    content: str | None = None
    message: str | None = None
    model: str | None = None
    agents: list[str] | None = None
    duration_ms: int | None = None
    elapsed_ms: int | None = None
    human_approval_required: bool | None = None
    degraded: bool = False
    human_reviewed: bool = False
    review_action: str | None = None
    feedback: str | None = None
    parent_run_id: str | None = None

    def sse(self) -> str:
        return f"id: {self.sequence}\nevent: {self.type}\ndata: {self.model_dump_json(exclude_none=True)}\n\n"


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()
