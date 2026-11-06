import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { HealthStatus } from '../types';

export function ResearchModelPicker({ value, onChange, disabled = false }: {value: string; onChange: (value: string) => void; disabled?: boolean}) {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    api.health(controller.signal).then((next) => { setHealth(next); setError(''); }).catch((cause) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Model discovery failed.');
    });
    return () => controller.abort();
  }, [revision]);
  return <div className="lab-model"><label>Decision model<select value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
    <option value="">Server default</option>{health?.models.map((model) => <option key={model} value={model}>{model}</option>)}
  </select></label><button type="button" className="text-button" onClick={() => setRevision((count) => count + 1)} disabled={disabled}>Refresh models</button>
    {(error || health?.error) && <p className="notice" role="status">{error || health?.error} Event ingestion and rule-based simulation remain available.</p>}
  </div>;
}
