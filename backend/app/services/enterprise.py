"""Event-to-decision service and the explicitly local simulated action adapter."""
from datetime import datetime, timezone
from uuid import uuid4

from backend.app.actions.simulator import ActionAdapter, InventorySimulator
from backend.app.core.errors import ApplicationError
from backend.app.orchestration.events import timestamp
from backend.app.orchestration.negotiation import apply_resolution, arbitrate
from backend.app.orchestration.twin import candidates
from backend.app.schemas.enterprise import AgentProposal, DecisionCase, EnterpriseEvent, Inventory, TwinState
from backend.app.storage.enterprise import EnterpriseRepository

MAX_EVENT_AGE_SECONDS = 86_400


def build_case(state: TwinState, evidence: list[str], origin: str = 'event', parent: str | None = None) -> DecisionCase:
    options = candidates(state.state)
    valid = [item for item in options if not item.violations]
    choices = {
        'rule:operations': max(valid, key=lambda item: (item.served, -item.cost)),
        'rule:finance': min(valid, key=lambda item: (item.cost, -item.served)),
        'rule:risk': max(valid, key=lambda item: (item.fill_rate, -item.cost)),
    }
    proposals = [AgentProposal(agent_id=role, round=0, action=choice.action,
        reason=f'Deterministic seed proposal for {role.split(":")[1]} using the supplied one-day twin.', evidence=evidence)
        for role, choice in choices.items()]
    initial = DecisionCase(id=uuid4().hex, entity_id=state.id, state_version=state.version, state=state,
        evidence=evidence, created_at=timestamp(), origin=origin, parent_case_id=parent,
        candidates=options, rounds=[], selected_action='defer', requires_review=True, review_reasons=[], rejection_reasons={})
    return apply_resolution(initial, [arbitrate(proposals, options, 0)])


class EnterpriseService:
    def __init__(self, repository: EnterpriseRepository):
        self.repository = repository
        self.adapter: ActionAdapter = InventorySimulator()

    def ingest(self, event: EnterpriseEvent) -> dict:
        def transform(current: TwinState) -> tuple[TwinState, DecisionCase]:
            age = (datetime.now(timezone.utc) - event.occurred_at).total_seconds()
            if age > MAX_EVENT_AGE_SECONDS or age < -60:
                raise ApplicationError('Event is older than 24 hours or more than 60 seconds in the future.', 409)
            if current.observed_at and event.occurred_at <= datetime.fromisoformat(current.observed_at):
                raise ApplicationError('Out-of-order event; the current state has a newer observation.', 409)
            changes = event.changes.model_dump(exclude_none=True)
            state = Inventory.model_validate({**current.state.model_dump(), **changes})
            updated = current.model_copy(update={'state': state, 'version': current.version + 1,
                'observed_at': event.occurred_at.isoformat(), 'updated_at': timestamp(),
                'predicted_inventory': None if 'inventory' in changes else current.predicted_inventory})
            evidence = [f'{event.source}:{event.event_id}', f'state:{current.id}:{updated.version}']
            case = build_case(updated, evidence)
            if current.predicted_inventory is not None and 'inventory' in changes:
                case.drift = {'predicted_inventory': current.predicted_inventory, 'observed_inventory': state.inventory,
                              'difference_units': state.inventory - current.predicted_inventory,
                              'basis': 'Latest unreconciled simulated inventory versus incoming inventory observation'}
            return updated, case
        return self.repository.ingest(event, transform)

    def transition(self, case: DecisionCase, state: TwinState, approval: dict) -> tuple[TwinState, DecisionCase, dict]:
        chosen = next(item for item in case.candidates if item.action == approval['action'])
        updated, outcome = self.adapter.apply(state, chosen)
        feedback = build_case(updated, [f'simulated-outcome:{case.id}', f'state:{state.id}:{updated.version}'], 'simulated_feedback', case.id)
        return updated, feedback, outcome

    def snapshot(self, entity_id: str) -> dict:
        return self.repository.snapshot(entity_id)
