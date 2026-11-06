import { useEffect, useRef, useState } from 'react';
import type { EnterpriseEvent, EventReceipt, Inventory } from '../types/enterprise';
import { enterpriseApi } from '../services/enterprise';

export function EnterpriseFeed({ entityId, onReceipt }: {entityId: string; onReceipt: (receipt: EventReceipt) => void}) {
  const [streaming, setStreaming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState<EventReceipt | null>(null);
  const [raw, setRaw] = useState('');
  const count = useRef(0);
  const callback = useRef(onReceipt);
  callback.current = onReceipt;
  const ingest = async (changes: Partial<Inventory>) => {
    setBusy(true); setError('');
    try {
      const result = await enterpriseApi.event({ event_id: crypto.randomUUID(), source: 'simulated-feed', entity_id: entityId,
        occurred_at: new Date().toISOString(), changes, description: 'Local demonstration feed' });
      setReceipt(result); callback.current(result);
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Ingestion failed.'); setStreaming(false); }
    finally { setBusy(false); }
  };
  useEffect(() => {
    if (!streaming) return;
    let stopped = false;
    let timer = 0;
    const next = async () => {
      if (stopped) return;
      count.current += 1;
      try {
        const result = await enterpriseApi.event({ event_id: crypto.randomUUID(), source: 'simulated-feed', entity_id: entityId,
          occurred_at: new Date().toISOString(), changes: { demand: count.current % 2 ? 180 : 140, capacity: count.current % 3 ? 45 : 75 },
          description: `Simulated enterprise observation ${count.current}` });
        if (!stopped) { setReceipt(result); callback.current(result); }
      } catch (cause) { if (!stopped) { setError(cause instanceof Error ? cause.message : 'Feed stopped.'); setStreaming(false); } }
      if (!stopped) timer = window.setTimeout(() => { void next(); }, 5000);
    };
    timer = window.setTimeout(() => { void next(); }, 5000);
    return () => { stopped = true; window.clearTimeout(timer); };
  }, [entityId, streaming]);
  const submitRaw = async () => {
    setBusy(true); setError('');
    try { const result = await enterpriseApi.event(JSON.parse(raw) as EnterpriseEvent); setReceipt(result); onReceipt(result); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Invalid event.'); }
    finally { setBusy(false); }
  };
  return <div className="enterprise-feed">
    <div className="lab-actions"><button className="secondary-button" disabled={busy || streaming} onClick={() => { void ingest({ capacity: 25 }); }}>Supplier disruption</button>
      <button className="secondary-button" disabled={busy || streaming} onClick={() => { void ingest({ demand: 200 }); }}>Demand surge</button>
      <button className="secondary-button" disabled={busy || streaming} onClick={() => { void ingest({ inventory: 90 }); }}>Inventory observation</button>
      <button className="secondary-button" disabled={busy} aria-pressed={streaming} onClick={() => setStreaming((value) => !value)}>{streaming ? 'Stop simulated feed' : 'Start feed · every 5 seconds'}</button></div>
    <p className="lab-muted">Each accepted event updates state and triggers a new decision. Pause the feed before negotiation or approval; new state invalidates old approvals. External producers can POST the same contract to <code>/api/enterprise/events</code>.</p>
    <details><summary>Ingest an external event as JSON</summary><button className="text-button" onClick={() => setRaw(JSON.stringify({ event_id: crypto.randomUUID(), source: 'erp-webhook', entity_id: entityId,
      occurred_at: new Date().toISOString(), changes: { inventory: 55, demand: 150 }, description: 'Inventory reconciliation' }, null, 2))}>Fill an example</button>
      <label className="sr-only" htmlFor="enterprise-event-json">Enterprise event JSON</label><textarea id="enterprise-event-json" className="event-json" rows={10} value={raw} onChange={(event) => setRaw(event.target.value)} />
      <button className="secondary-button" disabled={busy || !raw.trim()} onClick={() => { void submitRaw(); }}>Ingest event</button></details>
    {receipt && <p role="status" className={receipt.status === 'rejected' ? 'notice' : 'success-banner'}>{receipt.duplicate ? 'Duplicate receipt; state unchanged.' : `${receipt.status}: ${receipt.reason || `state v${receipt.state_version}`}`}</p>}
    {error && <p role="alert" className="notice">{error}</p>}
  </div>;
}
