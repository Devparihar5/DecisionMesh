"""Local inventory transitions; this adapter makes no external calls."""
from typing import Protocol

from backend.app.orchestration.events import timestamp
from backend.app.schemas.enterprise import Simulation, TwinState


class ActionAdapter(Protocol):
    def apply(self, state: TwinState, chosen: Simulation) -> tuple[TwinState, dict]: ...


class InventorySimulator:
    def apply(self, state: TwinState, chosen: Simulation) -> tuple[TwinState, dict]:
        values = state.state.model_copy(update={'inventory': chosen.remaining_inventory, 'demand': chosen.unmet,
                                                'budget': round(state.state.budget - chosen.cost, 2)})
        updated = state.model_copy(update={'state': values, 'version': state.version + 1,
            'simulated_steps': state.simulated_steps + 1, 'predicted_inventory': chosen.remaining_inventory,
            'updated_at': timestamp()})
        return updated, {'action': chosen.action, 'outcome': chosen.model_dump(),
            'assumptions': ['One-day deterministic production horizon', 'Demand served is removed; unmet demand becomes backlog',
                            'Spend reduces remaining budget', 'No ERP, supplier, payment, or physical action was performed']}
