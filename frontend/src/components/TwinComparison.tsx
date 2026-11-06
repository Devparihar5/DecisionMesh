import type { ActionKind, Simulation } from '../types/enterprise';

export function TwinComparison({ candidates, selected, onSelect }: {candidates: Simulation[]; selected: ActionKind; onSelect: (action: ActionKind) => void}) {
  return <div className="table-scroll"><table className="performance-table twin-table"><caption className="sr-only">One-day candidate action simulations</caption>
    <thead><tr><th>Candidate action</th><th>Served</th><th>Unmet</th><th>Cost</th><th>Fill rate</th><th>Policy</th></tr></thead>
    <tbody>{candidates.map((item) => <tr key={item.action} className={item.action === selected ? 'selected' : ''}>
      <th scope="row"><label><input type="radio" name="candidate-action" value={item.action} checked={selected === item.action} onChange={() => onSelect(item.action)} /> {item.action}</label></th>
      <td>{item.served}</td><td>{item.unmet}</td><td>{item.cost.toFixed(2)}</td><td>{item.fill_rate}%</td><td>{item.violations.join('; ') || (item.requires_review ? 'Review required' : 'Within limits')}</td>
    </tr>)}</tbody>
  </table></div>;
}
