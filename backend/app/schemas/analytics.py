"""Observable runtime metrics; no inferred decision-quality scores."""
from pydantic import BaseModel


class AgentPerformance(BaseModel):
    agent_id: str
    name: str
    role: str
    color: str
    attempts: int
    completed: int
    failed: int
    cancelled: int
    interrupted: int
    running: int
    skipped: int
    success_rate: float | None
    average_duration_ms: int | None
    p95_duration_ms: int | None
    last_run_at: str | None


class DailyRuns(BaseModel):
    date: str
    total: int
    completed: int
    failed: int
    cancelled: int
    interrupted: int


class AnalyticsReport(BaseModel):
    period_days: int
    total_runs: int
    completed_runs: int
    partial_runs: int
    failed_runs: int
    cancelled_runs: int
    interrupted_runs: int
    running_runs: int
    completion_rate: float | None
    average_duration_ms: int | None
    agents: list[AgentPerformance]
    daily: list[DailyRuns]
