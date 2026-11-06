import { useState } from 'react';
import type { ActionKind, Approval, DecisionCase, Execution } from '../types/enterprise';
import { enterpriseApi } from '../services/enterprise';

export function SimulatedAction({ decision, action, stale, negotiating, onExecuted }: {decision: DecisionCase; action: ActionKind; stale: boolean; negotiating: boolean; onExecuted: (receipt: Execution) => void}) {
  const [reviewer, setReviewer] = useState('');
  const [rationale, setRationale] = useState('');
  const [approval, setApproval] = useState<(Approval & {key: string}) | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState<Execution | null>(null);
  const candidate = decision.candidates.find((item) => item.action === action)!;
  const blocked = stale || negotiating || !!decision.execution_id || !!candidate.violations.length || busy || !!receipt;
  const approve = async () => {
    setBusy(true); setError('');
    try { setApproval({ ...await enterpriseApi.approve(decision.id, { action, state_version: decision.state_version, reviewer: reviewer.trim(), rationale: rationale.trim() }), key: crypto.randomUUID() }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Approval failed.'); }
    finally { setBusy(false); }
  };
  const execute = async () => {
    if (!approval) return;
    setBusy(true); setError('');
    try { const result = await enterpriseApi.execute(decision.id, approval.id, approval.key); setReceipt(result); onExecuted(result); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Simulation execution failed.'); }
    finally { setBusy(false); }
  };
  return <div className="simulated-action">
    <h3>Review and authorize the local simulation</h3>
    <p>Selected: <strong>{action}</strong> · projected spend {candidate.cost.toFixed(2)} · unmet demand {candidate.unmet}. Approval is bound to state v{decision.state_version}, this exact action, and a 15-minute expiry.</p>
    <p className="lab-muted">Reviewer name provides local attribution. This workspace does not authenticate enterprise decision rights. Execution changes the local twin only.</p>
    {(stale || negotiating) && <p className="notice">{stale ? 'Newer state is available. Open its latest decision before authorizing.' : 'Agent negotiation is running. Wait for its result before reviewing.'}</p>}
    {!!candidate.violations.length && <p className="notice">Blocked: {candidate.violations.join('; ')}. A reviewer cannot override hard budget limits.</p>}
    <div className="lab-form-grid"><label>Reviewer name<input value={reviewer} maxLength={100} onChange={(event) => setReviewer(event.target.value)} disabled={busy} /></label>
      <label>Reason for choosing this action<input value={rationale} maxLength={1000} onChange={(event) => setRationale(event.target.value)} placeholder="Explain accepted risks or an arbitration override" disabled={busy} /></label></div>
    <div className="lab-actions"><button className="secondary-button" disabled={blocked || reviewer.trim().length < 2 || rationale.trim().length < 8} onClick={() => { void approve(); }}>Approve {action} simulation</button>
      {approval && <button className="run-button" disabled={blocked || approval.action !== action} onClick={() => { void execute(); }}>{busy ? 'Applying…' : `Execute approved ${approval.action} locally →`}</button>}</div>
    {approval && <p className="lab-muted">Approved by {approval.reviewer}. Expires {new Date(approval.expires_at).toLocaleTimeString()}. Changing the action requires a new approval.</p>}
    {error && <p role="alert" className="notice">{error}</p>}
    {receipt && <p className="success-banner" role="status">Simulation acknowledged. State v{receipt.before_version} → v{receipt.after_version}. Outcome feedback created a new decision case.</p>}
  </div>;
}
