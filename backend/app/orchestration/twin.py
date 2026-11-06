"""Pure one-day inventory twin. No external actions or model-generated arithmetic."""
from backend.app.schemas.enterprise import ActionKind, Inventory, Simulation

ACTIONS: tuple[ActionKind, ...] = ('hold', 'overtime', 'backup', 'defer')
RULE_VERSION = 'inventory-v1'


def simulate(state: Inventory, action: ActionKind) -> Simulation:
    required = max(0, state.demand - state.inventory)
    produced = 0 if action == 'defer' else min(state.capacity, required)
    shortfall = max(0, required - produced)
    extra = min(shortfall, state.capacity // 4) if action == 'overtime' else (
        min(shortfall, state.backup_capacity) if action == 'backup' else 0)
    cost = round(produced * state.unit_cost + extra * (
        state.backup_unit_cost if action == 'backup' else state.unit_cost * 1.5), 2)
    available = state.inventory + produced + extra
    served = min(state.demand, available)
    unmet = state.demand - served
    fill = served / state.demand if state.demand else 1.0
    violations = ['Hard budget exceeded'] if cost > state.budget else []
    reasons = (['Unmet demand'] if unmet else []) + (['Spend exceeds local review threshold (500)'] if cost > 500 else [])
    # Public rubric: service has greater weight than spending, subject to a hard budget.
    utility = round(100 * fill - 5 * cost / max(state.budget, 1), 6)
    return Simulation(action=action, produced=produced, extra_units=extra, served=served, unmet=unmet,
                      remaining_inventory=max(0, available - state.demand), cost=cost, fill_rate=round(fill * 100, 2),
                      utility=utility, violations=violations, requires_review=bool(reasons), review_reasons=reasons)


def candidates(state: Inventory) -> list[Simulation]:
    return [simulate(state, action) for action in ACTIONS]


def oracle(options: list[Simulation]) -> Simulation:
    return max((item for item in options if not item.violations), key=lambda item: (item.utility, -item.cost, -ACTIONS.index(item.action)))
