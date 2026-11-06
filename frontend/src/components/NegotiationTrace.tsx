import type { NegotiationRound } from '../types/enterprise';

export function NegotiationTrace({ rounds }: {rounds: NegotiationRound[]}) {
  return <div className="negotiation-trace">{rounds.map((turn, index) => <details key={`${index}-${turn.number}`} open={index === rounds.length - 1}>
    <summary>{turn.number === 0 ? 'Rule-based seed proposals' : `Agent round ${turn.number}`} · {turn.conflicts.length} conflicts · selected {turn.selected_action}</summary>
    <div className="proposal-grid">{turn.proposals.map((proposal) => <article key={proposal.agent_id}>
      <span className="mono">{proposal.agent_id}</span><h3>{proposal.action}</h3><p>{proposal.reason}</p><small>Evidence: {proposal.evidence.join(', ')}</small>
    </article>)}</div>
    {turn.conflicts.map((conflict, i) => <p className="conflict-note" key={i}>{conflict.left} ↔ {conflict.right}: {conflict.reason}</p>)}
    {turn.errors.map((error, i) => <p role="status" className="notice" key={i}>{error}</p>)}
    <p className="arbitration-rule"><strong>Arbitration:</strong> {turn.reason}</p>
  </details>)}</div>;
}
