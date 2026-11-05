import { useCallback } from 'react';
import { useMemoryQuery } from '../hooks/useMemoryQuery';
import { dateTime, duration } from '../services/format';
import { memoryApi } from '../services/memory';
import { EventTimeline } from './EventTimeline';
import { Panel } from './Panel';
import { StatusBadge } from './StatusBadge';

export function RunHistoryDetail({ id }: { id: string }) {
  const load = useCallback((signal: AbortSignal) => memoryApi.detail(id, signal), [id]);
  const { data: run, loading, error, refresh } = useMemoryQuery(load);
  if (error) return <div className="page-error" role="alert">{error}<button className="text-button" onClick={refresh}>Retry</button></div>;
  if (loading || !run) return <div className="panel memory-loading" role="status">Loading saved run…</div>;
  return <div className="history-detail">
    <Panel index="RUN" title="Saved decision context" action={<button className="text-button" onClick={refresh}>↻ Refresh</button>}>
      <div className="saved-run-heading"><StatusBadge status={run.status} partial={run.degraded} /><code>{run.id.slice(0, 12)}</code></div>
      {run.status === 'awaiting_review' && <p className="review-waiting"><span>This run is waiting for your suggestions.</span><a className="secondary-button" href={`#/?review=${run.id}`}>Review & continue →</a></p>}
      {run.parent_run_id && <p className="flow-note">Revision of run <code>{run.parent_run_id.slice(0, 12)}</code></p>}
      {run.input_feedback && <p className="saved-feedback"><strong>Suggestions used for this analysis</strong>{run.input_feedback}</p>}
      {run.review_action && <p className="saved-feedback"><strong>Operator choice: {run.review_action === 'rerun' ? 'Revise and rerun' : 'Generate final brief'}</strong>{run.review_feedback || 'No additional suggestions supplied.'}</p>}
      <p className="saved-scenario">{run.scenario}</p>
      <dl className="run-metadata">
        <div><dt>Started</dt><dd>{dateTime(run.created_at)}</dd></div>
        <div><dt>Duration</dt><dd>{duration(run.duration_ms)}</dd></div>
        <div><dt>Model</dt><dd>{run.model || 'Unavailable'}</dd></div>
        <div><dt>Review preference</dt><dd>{run.review_action ? 'Review submitted' : run.require_approval ? 'Human review required' : 'Not required by operator'}</dd></div>
      </dl>
      {run.error && <p className="inline-error">{run.error}</p>}
      <p className="flow-note">Saved agent definitions and findings reflect this run, even if a role is later changed or removed.</p>
    </Panel>
    <Panel index="RESULTS" title="Agent findings" action={<span className="quiet-label">{run.agent_count} AGENTS</span>}>
      {run.executions.map((execution) => <details key={execution.agent_id} className={`finding-card ${execution.agent_id === 'decision_synth' ? 'is-final' : ''}`} open={execution.agent_id === 'decision_synth'}>
        <summary><strong>{execution.name}</strong><StatusBadge status={execution.status} /><span>{duration(execution.duration_ms)}</span></summary>
        <p className="finding-body">{execution.content || execution.error || (execution.status === 'queued' ? 'Waiting to start.' : 'No finding was generated.')}</p>
        <details className="saved-instructions"><summary>Role and saved instructions</summary><p>{run.agents.find((agent) => agent.id === execution.agent_id)?.instructions}</p></details>
      </details>)}
    </Panel>
    <EventTimeline events={run.events} live={false} />
  </div>;
}
