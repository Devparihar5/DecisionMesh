import type { HealthStatus } from '../types';

interface Props {
  health: HealthStatus | null;
  model: string;
  busy: boolean;
  refreshing: boolean;
  onModelChange: (value: string) => void;
  onRefresh: () => void;
}

export function Header({ health, model, busy, refreshing, onModelChange, onRefresh }: Props) {
  const connected = health?.llm_online && health.models.length > 0;
  return (
    <div className="workspace-toolbar">
      <span className="quiet-label">WORKSPACE / LIVE ORCHESTRATION</span>
      <div className="top-meta">
        <span className={`connection ${connected ? 'online' : 'offline'}`}><i />{connected ? 'Local model connected' : refreshing ? 'Connecting…' : 'Model unavailable'}</span>
        <button className="icon-button" onClick={onRefresh} disabled={refreshing || busy} aria-label="Refresh model connection" title="Refresh model connection">↻</button>
        <span className="divider" />
        <label htmlFor="model">MODEL</label>
        <select id="model" value={model} disabled={busy || !connected} onChange={(e) => onModelChange(e.target.value)}>
          {!connected && <option value="">No model found</option>}
          {health?.models.map((id) => <option key={id} value={id}>{id}</option>)}
        </select>
      </div>
    </div>
  );
}
