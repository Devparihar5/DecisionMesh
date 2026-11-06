import { useState } from 'react';
import type { Inventory, TwinState } from '../types/enterprise';
import { enterpriseApi } from '../services/enterprise';

const INITIAL: Inventory = { inventory: 40, demand: 140, capacity: 60, backup_capacity: 60, unit_cost: 5, backup_unit_cost: 15, budget: 1500 };
const LABELS: Record<keyof Inventory, string> = { inventory: 'Inventory units', demand: 'Demand units', capacity: 'Daily production capacity', backup_capacity: 'Backup capacity', unit_cost: 'Unit production cost', backup_unit_cost: 'Backup unit cost', budget: 'Remaining budget' };

export function EntityCreator({ onCreated }: {onCreated: (entity: TwinState) => void}) {
  const [name, setName] = useState('Demo warehouse');
  const [id, setId] = useState('demo-warehouse');
  const [state, setState] = useState(INITIAL);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return <details className="entity-creator"><summary>Create an inventory twin</summary><form onSubmit={(event) => {
    event.preventDefault(); setBusy(true); setError('');
    enterpriseApi.create({ id, name, state }).then(onCreated).catch((cause) => setError(cause instanceof Error ? cause.message : 'Creation failed.')).finally(() => setBusy(false));
  }}><div className="lab-form-grid"><label>Entity ID<input required pattern={'[a-z][a-z0-9_\\-]{1,63}'} maxLength={64} value={id} onChange={(event) => setId(event.target.value)} /></label>
    <label>Name<input required minLength={2} maxLength={100} value={name} onChange={(event) => setName(event.target.value)} /></label>
    {(Object.keys(INITIAL) as (keyof Inventory)[]).map((key) => <label key={key}>{LABELS[key]}<input required type="number" min={key.includes('cost') ? 0.01 : 0} step={key.includes('cost') || key === 'budget' ? '.01' : '1'} value={state[key]} onChange={(event) => setState((value) => ({ ...value, [key]: event.target.valueAsNumber }))} /></label>)}
    </div><button className="secondary-button" disabled={busy}>Create twin</button>{error && <p className="notice" role="alert">{error}</p>}</form></details>;
}
