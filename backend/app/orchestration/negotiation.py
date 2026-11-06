"""Bounded proposal exchange and deterministic, explainable arbitration."""
import json

from backend.app.schemas.enterprise import AgentProposal, DecisionCase, NegotiationRound, Proposal, Simulation


def parse_proposal(content: str, evidence: list[str]) -> Proposal:
    text = content.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    proposal = Proposal.model_validate_json(text)
    # Compact aliases are explicitly supplied to the model, then resolved to
    # the original immutable source IDs before persistence. Unknown IDs fail.
    references = {f'E{index + 1}': value for index, value in enumerate(evidence)}
    proposal.evidence = [references.get(value, value) for value in proposal.evidence]
    if not set(proposal.evidence).issubset(set(evidence)):
        raise ValueError('Proposal cites evidence outside the supplied snapshot.')
    return proposal


def arbitrate(proposals: list[AgentProposal], options: list[Simulation], number: int,
              errors: list[str] | None = None) -> NegotiationRound:
    by_action = {item.action: item for item in options}
    conflicts = []
    for index, left in enumerate(proposals):
        for right in proposals[index + 1:]:
            first, second = by_action[left.action], by_action[right.action]
            if (first.served, first.cost, first.violations) == (second.served, second.cost, second.violations):
                continue
            conflicts.append({'left': left.agent_id, 'right': right.agent_id,
                'reason': f'{left.action} (served {first.served}, cost {first.cost:.2f}) versus '
                          f'{right.action} (served {second.served}, cost {second.cost:.2f}); '
                          + ('hard budget compliance differs' if bool(first.violations) != bool(second.violations) else 'competing service/cost outcomes')})
    eligible = [by_action[item.action] for item in proposals if not by_action[item.action].violations]
    selected = max(eligible, key=lambda item: (item.utility, -item.cost, item.action)) if eligible else by_action['defer']
    reason = ('Hard budget enforced; among valid proposed actions, maximize service utility '
              '(100 × served/demand − 5 × cost/budget), then minimize cost. '
              f'Selected {selected.action} at utility {selected.utility:.3f}.')
    if not eligible:
        reason = 'No valid proposals; defer production and escalate to the operator.'
    return NegotiationRound(number=number, proposals=proposals, errors=errors or [], conflicts=conflicts,
                            selected_action=selected.action, reason=reason)


def proposal_prompt(case: DecisionCase, previous: NegotiationRound | None = None) -> str:
    references = {f'E{index + 1}': value for index, value in enumerate(case.evidence)}
    snapshot = {'entity_id': case.entity_id, 'state_version': case.state_version,
                'inventory_state': case.state.state.model_dump(), 'evidence_ids': list(references),
                'evidence_map': references,
                'candidate_simulations': [item.model_dump() for item in case.candidates]}
    exchange = '\nPrevious round (review peers and revise or defend your choice):\n' + previous.model_dump_json() if previous else ''
    return (f'One-day supply-chain decision. Use only this normalized snapshot:\n{json.dumps(snapshot)}{exchange}\n'
            'Choose hold (normal production), overtime (+25% capacity), backup (alternate supplier), or defer (inventory only). '
            'Hard budget violations cannot be approved. Explain service/cost trade-offs from your assigned role. '
            'Cite only the supplied short evidence references (E1, E2). Do not generate source IDs yourself. '
            'Return ONLY a JSON object: {"action":"backup","reason":"brief rationale, at most 40 words",'
            '"evidence":["E1"]}. No markdown or additional keys. Do not execute actions.')


def apply_resolution(case: DecisionCase, rounds: list[NegotiationRound]) -> DecisionCase:
    latest = rounds[-1]
    selected = next(item for item in case.candidates if item.action == latest.selected_action)
    reasons = list(selected.review_reasons)
    if latest.conflicts:
        reasons.append('Agent disagreement requires operator review')
    if latest.errors or not latest.proposals:
        reasons.append('Incomplete or invalid agent proposals require operator review')
    if latest.selected_action == 'defer':
        reasons.append('Production deferred; operator intervention required')
    return case.model_copy(update={'rounds': rounds, 'selected_action': selected.action,
        'requires_review': bool(reasons), 'review_reasons': reasons,
        'status': 'review_required' if reasons else 'ready',
        'rejection_reasons': {item.action: '; '.join(item.violations) if item.violations else
            f'Not selected under inventory-v1; utility {item.utility:.3f}, cost {item.cost:.2f}.'
            for item in case.candidates if item.action != selected.action}})
