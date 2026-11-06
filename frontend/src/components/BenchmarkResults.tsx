import type { BenchmarkSummary, BenchmarkTrial } from '../types/enterprise';
import { duration } from '../services/format';

export function BenchmarkResults({ summary, trials }: {summary?: Record<string, BenchmarkSummary>; trials: BenchmarkTrial[]}) {
  return <>
    {summary && <div className="benchmark-summary">{Object.entries(summary).map(([architecture, item]) => <article className="benchmark-card" key={architecture}>
      <h3>{architecture}</h3><strong>{item.quality_score.toFixed(1)}<small> / 100 simulated quality</small></strong><progress max={100} value={item.quality_score} aria-label={`${architecture} simulated quality`} />
      <dl><div><dt>Samples</dt><dd>{item.samples}</dd></div><div><dt>Optimal choices</dt><dd>{item.optimal_decision_rate}%</dd></div><div><dt>Policy compliance</dt><dd>{item.policy_compliance_rate}%</dd></div><div><dt>Mean machine phase</dt><dd>{duration(item.mean_machine_time_ms)}</dd></div><div><dt>P95 machine phase</dt><dd>{duration(item.p95_machine_time_ms)}</dd></div><div><dt>Model calls</dt><dd>{item.model_calls}</dd></div><div><dt>Conflict rate</dt><dd>{item.conflict_rate === null ? 'Not applicable' : `${item.conflict_rate}%`}</dd></div><div><dt>Review required</dt><dd>{item.review_required_rate}%</dd></div><div><dt>Evidence IDs validated</dt><dd>{item.evidence_coverage_rate}%</dd></div><div><dt>Provider / format failures</dt><dd>{item.provider_or_format_failure_rate}%</dd></div></dl>
      <p className="lab-muted">Approximate 95% quality interval: {item.quality_ci95_approx ? `${item.quality_ci95_approx[0]}–${item.quality_ci95_approx[1]}` : 'Insufficient samples'}. Synthetic tasks are correlated; this is descriptive.</p>
    </article>)}</div>}
    {!!trials.length && <div className="table-scroll"><table className="performance-table"><caption className="sr-only">Benchmark trials</caption><thead><tr><th>Scenario</th><th>Architecture</th><th>Chosen / oracle</th><th>Quality</th><th>Policy</th><th>Machine phase</th><th>Trace</th></tr></thead>
      <tbody>{trials.map((trial) => <tr key={`${trial.scenario}-${trial.repetition}-${trial.architecture}`}><th scope="row">{trial.scenario}<small className="lab-subtitle">Repetition {trial.repetition}</small></th><td>{trial.architecture}</td><td>{trial.action || 'Invalid response'} / {trial.oracle_action}</td><td>{trial.quality_score}</td><td>{trial.policy_compliant ? 'Pass' : 'Fail'}</td><td>{duration(trial.machine_time_ms)}</td><td><details><summary>Details</summary><pre>{JSON.stringify(trial, null, 2)}</pre></details></td></tr>)}</tbody>
    </table></div>}
  </>;
}
