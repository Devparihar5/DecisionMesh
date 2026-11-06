import { useState } from 'react';
import type { ResearchJob } from '../types/enterprise';
import { enterpriseApi } from '../services/enterprise';

export function ResearchJobProgress({ job, onChange }: {job: ResearchJob; onChange: () => void}) {
  const [error, setError] = useState('');
  const latest = job.progress.at(-1);
  return <div className="research-job" role="status">
    <div className="lab-actions"><strong>{job.kind} · {job.status}</strong><span className="mono">{job.id.slice(0, 10)}</span>
      {job.status === 'running' && <button className="text-button" onClick={() => { setError(''); enterpriseApi.cancel(job.id).then(onChange).catch((cause) => setError(cause instanceof Error ? cause.message : 'Cancellation failed.')); }}>Cancel job</button>}
      <a href={`/api/research/jobs/${encodeURIComponent(job.id)}/export`}>Export JSON</a></div>
    {latest && <p>{latest.stage.replaceAll('_', ' ')}{latest.agent || latest.agent_id ? ` · ${latest.agent || latest.agent_id}` : ''}{latest.round ? ` · round ${latest.round}` : ''}{latest.scenario ? ` · ${latest.scenario}` : ''}</p>}
    {job.error && <p className="notice">{job.error}</p>}
    {error && <p className="notice" role="alert">{error}</p>}
    <details><summary>Saved job trace · {job.progress.length} events</summary><ol className="job-event-list">{job.progress.map((event, index) => <li key={index}>
      <span>{new Date(event.timestamp).toLocaleTimeString()} · {event.stage}</span>{typeof event.reason === 'string' && <p>{event.reason}</p>}
      {event.action && <p>{event.agent_id}: {event.action}</p>}
      {typeof event.raw_output === 'string' && <pre>{event.raw_output}</pre>}
    </li>)}</ol></details>
  </div>;
}
