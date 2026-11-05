import type { RunEvent, RunStatus } from '../types';
import { Panel } from './Panel';

interface Props { events: RunEvent[]; status: RunStatus; error: string }

export function RunFindings({ events, status, error }: Props) {
  const findings = events.filter((event) => event.type === 'agent_done' || event.type === 'agent_error');
  const complete = events.find((event) => event.type === 'complete');
  return <Panel index="04" title="Agent findings" action={<span className="quiet-label">{status === 'idle' ? 'NO RUN YET' : `${findings.length} FINDINGS`}</span>}>
    {error && <p className="inline-error" role="alert">{error}</p>}
    {!findings.length && <div className="findings-empty"><span className="empty-mark" aria-hidden="true">✳</span><strong>{status === 'running' ? 'Agents are analyzing your scenario' : 'Waiting for a decision to analyze'}</strong><span>{status === 'running' ? 'The first finding will appear when the local model responds.' : 'Start a workflow to see specialist findings and a decision brief.'}</span></div>}
    {findings.map((event) => <details key={event.sequence} className={`finding-card ${event.agent_id === 'decision_synth' ? 'is-final' : ''}`} open>
      <summary><strong>{event.name}</strong><span>{event.type === 'agent_error' ? 'FAILED' : `${((event.duration_ms || 0) / 1000).toFixed(1)}s`}</span></summary>
      <p className={`finding-body ${event.type === 'agent_error' ? 'finding-error' : ''}`}>{event.content || event.message}</p>
    </details>)}
    {complete?.degraded && <p className="approval-banner">Partial results · Some agents failed. Review missing perspectives before making a decision.</p>}
    {complete?.human_approval_required && <p className="approval-banner">Human review required · This recommendation awaits a decision owner’s review.</p>}
    {status === 'cancelled' && <p className="approval-banner">Workflow stopped. Completed findings are preserved; no final decision was approved.</p>}
  </Panel>;
}
