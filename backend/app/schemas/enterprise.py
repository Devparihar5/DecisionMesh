"""Typed contracts for the local enterprise decision loop."""
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ActionKind = Literal['hold', 'overtime', 'backup', 'defer']


class Inventory(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    inventory: int = Field(default=40, ge=0, le=1_000_000)
    demand: int = Field(default=140, ge=0, le=1_000_000)
    capacity: int = Field(default=60, ge=0, le=1_000_000)
    backup_capacity: int = Field(default=60, ge=0, le=1_000_000)
    unit_cost: float = Field(default=5, gt=0, le=1_000_000)
    backup_unit_cost: float = Field(default=15, gt=0, le=1_000_000)
    budget: float = Field(default=1500, ge=0, le=1_000_000_000)


class EntityInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(pattern=r'^[a-z][a-z0-9_-]{1,63}$')
    name: str = Field(min_length=2, max_length=100)
    state: Inventory = Field(default_factory=Inventory)


class TwinState(EntityInput):
    version: int = 0
    observed_at: str | None = None
    updated_at: str
    simulated_steps: int = 0
    predicted_inventory: int | None = None


class StateChange(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    inventory: int | None = Field(default=None, ge=0, le=1_000_000)
    demand: int | None = Field(default=None, ge=0, le=1_000_000)
    capacity: int | None = Field(default=None, ge=0, le=1_000_000)
    backup_capacity: int | None = Field(default=None, ge=0, le=1_000_000)
    unit_cost: float | None = Field(default=None, gt=0, le=1_000_000)
    backup_unit_cost: float | None = Field(default=None, gt=0, le=1_000_000)
    budget: float | None = Field(default=None, ge=0, le=1_000_000_000)

    @model_validator(mode='after')
    def not_empty(self) -> 'StateChange':
        if not self.model_dump(exclude_none=True):
            raise ValueError('Supply at least one state change.')
        return self


class EnterpriseEvent(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    event_id: str = Field(min_length=1, max_length=120)
    source: str = Field(min_length=2, max_length=80)
    entity_id: str = Field(min_length=2, max_length=64)
    occurred_at: datetime
    changes: StateChange
    description: str = Field(default='', max_length=1000)

    @model_validator(mode='after')
    def aware_time(self) -> 'EnterpriseEvent':
        if self.occurred_at.tzinfo is None:
            raise ValueError('occurred_at must include a timezone.')
        self.occurred_at = self.occurred_at.astimezone(timezone.utc)
        return self


class Simulation(BaseModel):
    action: ActionKind
    produced: int
    extra_units: int
    served: int
    unmet: int
    remaining_inventory: int
    cost: float
    fill_rate: float
    utility: float
    violations: list[str]
    requires_review: bool
    review_reasons: list[str]


class Proposal(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    action: ActionKind
    reason: str = Field(min_length=8, max_length=1500)
    evidence: list[str] = Field(min_length=1, max_length=10)


class AgentProposal(Proposal):
    agent_id: str
    round: int
    duration_ms: int = 0


class NegotiationRound(BaseModel):
    number: int
    proposals: list[AgentProposal]
    errors: list[str]
    conflicts: list[dict[str, str]]
    selected_action: ActionKind
    reason: str


class DecisionCase(BaseModel):
    id: str
    entity_id: str
    state_version: int
    state: TwinState
    evidence: list[str]
    created_at: str
    parent_case_id: str | None = None
    origin: str = 'event'
    status: str = 'review_required'
    candidates: list[Simulation]
    rounds: list[NegotiationRound]
    selected_action: ActionKind
    requires_review: bool
    review_reasons: list[str]
    rejection_reasons: dict[str, str]
    rule_version: str = 'inventory-v1'
    execution_id: str | None = None
    drift: dict | None = None


class NegotiationInput(BaseModel):
    model: str = Field(default='', max_length=200)
    agents: list[str] = Field(default_factory=lambda: ['operations', 'finance', 'risk', 'compliance'], min_length=2, max_length=7)


class ApprovalInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    action: ActionKind
    state_version: int = Field(ge=0)
    reviewer: str = Field(min_length=2, max_length=100)
    rationale: str = Field(min_length=8, max_length=1000)


class ExecutionInput(BaseModel):
    approval_id: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=8, max_length=120)


class BenchmarkInput(BaseModel):
    model: str = Field(default='', max_length=200)
    repetitions: int = Field(default=1, ge=1, le=3)


class Job(BaseModel):
    id: str
    kind: str
    status: str
    created_at: str
    updated_at: str
    config: dict
    progress: list[dict] = Field(default_factory=list)
    result: dict | None = None
    error: str | None = None


class EventReceipt(BaseModel):
    status: Literal['accepted', 'rejected']
    duplicate: bool
    event_id: str
    source: str
    reason: str | None = None
    state_version: int | None = None
    case_id: str | None = None


class EventRecord(BaseModel):
    event: EnterpriseEvent
    receipt: EventReceipt
    received_at: str


class ActionApproval(BaseModel):
    id: str
    case_id: str
    action: ActionKind
    state_version: int
    reviewer: str
    rationale: str
    case_revision: int
    created_at: str
    expires_at: str
    adapter: Literal['local_simulator']
    action_fingerprint: str
    recommended_action: ActionKind
    operator_override: bool
    rule_version: str


class ActionReceipt(BaseModel):
    id: str
    case_id: str
    approval: ActionApproval
    idempotency_key: str
    adapter: Literal['local_simulator']
    status: Literal['simulated']
    created_at: str
    before_version: int
    after_version: int
    feedback_case_id: str
    action: ActionKind
    outcome: Simulation
    assumptions: list[str]


class EnterpriseSnapshot(BaseModel):
    entity: TwinState
    cases: list[DecisionCase]
    events: list[EventRecord]
    executions: list[ActionReceipt]
