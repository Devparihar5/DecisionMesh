"""Persistent run, history, and agent execution response contracts."""
from typing import Literal

from pydantic import BaseModel

from backend.app.orchestration.events import RunEvent
from backend.app.schemas.agents import AgentDefinition

StoredRunStatus = Literal['running', 'complete', 'failed', 'cancelled', 'interrupted', 'awaiting_review', 'revised']
ExecutionStatus = Literal['queued', 'running', 'complete', 'failed', 'cancelled', 'skipped', 'interrupted']


class RunSummary(BaseModel):
    id: str
    scenario: str
    model: str
    status: StoredRunStatus
    created_at: str
    finished_at: str | None
    duration_ms: int | None
    require_approval: bool
    degraded: bool
    error: str | None
    agent_count: int
    parent_run_id: str | None = None


class ExecutionRecord(BaseModel):
    agent_id: str
    name: str
    role: str
    color: str
    status: ExecutionStatus
    started_at: str | None
    finished_at: str | None
    duration_ms: int | None
    content: str | None
    error: str | None


class RunDetail(RunSummary):
    input_feedback: str = ""
    review_feedback: str | None = None
    review_action: str | None = None
    reviewed_at: str | None = None
    agents: list[AgentDefinition]
    executions: list[ExecutionRecord]
    events: list[RunEvent]


class RunPage(BaseModel):
    items: list[RunSummary]
    total: int
    limit: int
    offset: int
