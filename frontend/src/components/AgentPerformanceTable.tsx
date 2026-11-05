import { useMemo, useState } from 'react';
import { dateTime, duration, percent } from '../services/format';
import type { AgentPerformance } from '../types';
import { Panel } from './Panel';

type Sort = 'attempts' | 'success_rate' | 'average_duration_ms';

export function AgentPerformanceTable({ agents }: { agents: AgentPerformance[] }) {
  const [sort, setSort] = useState<Sort>('attempts');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const sorted = useMemo(() => [...agents].sort((a, b) => {
    const left = a[sort], right = b[sort];
    if (left === null) return right === null ? a.name.localeCompare(b.name) : 1;
    if (right === null) return -1;
    return (sort === 'average_duration_ms' ? left - right : right - left) || a.name.localeCompare(b.name);
  }), [agents, sort]);
  const selected = agents.find((agent) => agent.agent_id === selectedId);
  return <Panel index="AGENTS" title="Agent-by-agent performance" action={<label className="table-sort">Sort <select aria-label="Sort agent performance" value={sort} onChange={(event) => setSort(event.target.value as Sort)}><option value="attempts">Most active</option><option value="success_rate">Success rate</option><option value="average_duration_ms">Fastest response</option></select></label>}>
    <div className="table-scroll"><table className="performance-table"><thead><tr><th scope="col">Agent</th><th scope="col">Attempts</th><th scope="col">Success</th><th scope="col">Avg response</th><th scope="col">P95</th><th scope="col">Failures</th></tr></thead><tbody>
      {sorted.map((agent) => <tr key={agent.agent_id} className={selectedId === agent.agent_id ? 'selected' : ''}><th scope="row"><button className="agent-metric-name" onClick={() => setSelectedId(agent.agent_id)} aria-pressed={selectedId === agent.agent_id}><i style={{ background: agent.color }} /><span>{agent.name}<small>{agent.role}</small></span></button></th><td>{agent.attempts}</td><td><span className="rate-number">{percent(agent.success_rate)}</span><span className="rate-track"><span style={{ width: `${agent.success_rate || 0}%` }} /></span></td><td>{duration(agent.average_duration_ms)}</td><td>{duration(agent.p95_duration_ms)}</td><td className={agent.failed ? 'finding-error' : ''}>{agent.failed}</td></tr>)}
    </tbody></table></div>
    {selected && <div className="agent-metric-detail"><div><h3>{selected.name}</h3><code>{selected.agent_id}</code></div><dl><div><dt>Completed</dt><dd>{selected.completed}</dd></div><div><dt>Failed</dt><dd>{selected.failed}</dd></div><div><dt>Cancelled</dt><dd>{selected.cancelled}</dd></div><div><dt>Interrupted</dt><dd>{selected.interrupted}</dd></div><div><dt>Running</dt><dd>{selected.running}</dd></div><div><dt>Skipped</dt><dd>{selected.skipped}</dd></div></dl><p>Last attempt: {dateTime(selected.last_run_at)}</p></div>}
    <p className="flow-note">Select an agent for its outcome breakdown. Success rate = completed ÷ (completed + failed). Skipped, active, cancelled, and interrupted attempts are excluded. Response timings use completed attempts; P95 uses the nearest rank.</p>
  </Panel>;
}
