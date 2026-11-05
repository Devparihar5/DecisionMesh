import { useCallback, useEffect, useState } from 'react';
import { RunHistoryDetail } from '../components/RunHistoryDetail';
import { StatusBadge } from '../components/StatusBadge';
import { useMemoryQuery } from '../hooks/useMemoryQuery';
import { dateTime, duration } from '../services/format';
import { memoryApi } from '../services/memory';
import type { StoredRunStatus } from '../types';

export function HistoryPage() {
  const [search, setSearch] = useState('');
  const [draft, setDraft] = useState('');
  const [status, setStatus] = useState<StoredRunStatus | ''>('');
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const load = useCallback((signal: AbortSignal) => memoryApi.runs({ search, status, offset }, signal), [search, status, offset]);
  const { data, loading, error, refresh } = useMemoryQuery(load);
  useEffect(() => {
    const timer = window.setTimeout(() => { setSearch(draft.trim()); setOffset(0); }, 300);
    return () => window.clearTimeout(timer);
  }, [draft]);
  const selectedId = selected || data?.items[0]?.id;

  return <main className="shell memory-page">
    <section className="memory-page-heading"><div><div className="eyebrow"><span />LOCAL MEMORY</div><h1>Every run.<br /><span>A lasting record.</span></h1><p>Revisit scenarios, findings, and the decisions behind each recommendation.</p></div>
      <button className="secondary-button" onClick={refresh} disabled={loading}>↻ Refresh history</button>
    </section>
    <div className="history-controls"><div><label htmlFor="history-search" className="field-label">SEARCH SCENARIOS OR RUN IDS</label><input id="history-search" type="search" maxLength={200} value={draft} placeholder="Find a previous decision…" onChange={(event) => { setDraft(event.target.value); setSelected(null); }} /></div>
      <div><label htmlFor="history-status" className="field-label">OUTCOME</label><select id="history-status" value={status} onChange={(event) => { setStatus(event.target.value as StoredRunStatus | ''); setOffset(0); setSelected(null); }}><option value="">All outcomes</option>{['running', 'complete', 'failed', 'cancelled', 'interrupted'].map((value) => <option value={value} key={value}>{value}</option>)}</select></div>
    </div>
    {error && <div className="page-error" role="alert">{error}<button className="text-button" onClick={refresh}>Retry</button></div>}
    {loading && <p className="memory-loading" role="status">Reading local run history…</p>}
    {data && !data.total && <div className="panel large-empty"><span className="empty-mark">◷</span><h2>{search || status ? 'No runs match these filters' : 'Your local memory starts here'}</h2><p>{search || status ? 'Try another search or outcome.' : 'New workflows will be saved here automatically, including partial and failed runs.'}</p><a className="secondary-button" href="#/">Open workspace ↗</a></div>}
    {data && data.total > 0 && <div className="history-layout"><section aria-label="Saved runs" className="history-list">
      <p className="history-result-count">{data.total} saved {data.total === 1 ? 'run' : 'runs'}</p>
      {data.items.map((run) => <button key={run.id} className={`history-run ${selectedId === run.id ? 'selected' : ''}`} onClick={() => setSelected(run.id)} aria-pressed={selectedId === run.id}>
        <div><StatusBadge status={run.status} partial={run.degraded} /><time dateTime={run.created_at}>{dateTime(run.created_at)}</time></div><h2>{run.scenario}</h2><footer><span>{run.model || 'Model unavailable'}</span><span>{duration(run.duration_ms)} · {run.agent_count} agents</span></footer>
      </button>)}
      <div className="pagination"><button className="secondary-button" disabled={!offset} onClick={() => { setOffset(offset - 12); setSelected(null); }}>← Previous</button><span>{Math.floor(offset / 12) + 1} / {Math.ceil(data.total / 12)}</span><button className="secondary-button" disabled={offset + 12 >= data.total} onClick={() => { setOffset(offset + 12); setSelected(null); }}>Next →</button></div>
    </section><section aria-label="Run details">{selectedId && <RunHistoryDetail key={selectedId} id={selectedId} />}</section></div>}
  </main>;
}
