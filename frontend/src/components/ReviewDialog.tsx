import { useEffect, useRef, useState } from 'react';
import type { ReviewInput, RunEvent } from '../types';

interface Props {
  checkpoint: RunEvent;
  findings: RunEvent[];
  submitting: boolean;
  error: string;
  onSubmit: (input: ReviewInput) => void;
  onLater: () => void;
  onCancel: () => void;
}

export function ReviewDialog({ checkpoint, findings, submitting, error, onSubmit, onLater, onCancel }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [feedback, setFeedback] = useState('');
  const [validation, setValidation] = useState('');
  useEffect(() => { dialog.current?.showModal(); }, []);
  const submit = (action: ReviewInput['action']) => {
    if (action === 'rerun' && !feedback.trim()) { setValidation('Add suggestions so the agents know what to reconsider.'); return; }
    setValidation(''); onSubmit({ action, feedback: feedback.trim() });
  };
  return <dialog ref={dialog} className="review-dialog" aria-labelledby="review-title" onCancel={(event) => { event.preventDefault(); if (!submitting) onLater(); }}>
    <div className="dialog-head"><div><span className="section-index">HUMAN REVIEW · WORKFLOW PAUSED</span><h2 id="review-title">Your judgment, before the final brief.</h2></div><button className="icon-button" aria-label="Review later" disabled={submitting} onClick={onLater}>×</button></div>
    <p className="review-intro">Review the assessments, add your priorities or corrections, then choose how to continue.</p>
    {checkpoint.degraded && <p className="approval-banner">Some agents could not return a finding. Their missing perspectives will be noted in the final brief.</p>}
    <div className="review-assessments">{findings.filter((event) => event.type === 'agent_done' || event.type === 'agent_error').map((event) => <details key={event.sequence} open={event.agent_id === 'human_review'}><summary>{event.name}{event.type === 'agent_error' ? ' · failed' : ''}</summary><p>{event.content || event.message}</p></details>)}</div>
    <form onSubmit={(event) => { event.preventDefault(); submit('finalize'); }}>
      <label className="field-label" htmlFor="review-feedback">YOUR SUGGESTIONS</label>
      <textarea id="review-feedback" value={feedback} maxLength={2000} disabled={submitting} onChange={(event) => setFeedback(event.target.value)} placeholder="e.g. Prioritize delivery commitments; compare a partial supplier switch before recommending the higher-cost option." />
      <p className="review-hint">Required to rerun; optional when generating the final brief. {feedback.length} / 2000</p>
      {(validation || error) && <p className="inline-error" role="alert">{validation || error}</p>}
      <div className="review-actions"><button type="button" className="secondary-button" disabled={submitting} onClick={() => submit('rerun')}>↻ Revise & rerun agents</button><button className="run-button" disabled={submitting}>{submitting ? 'Continuing…' : 'Generate final brief →'}</button></div>
      <div className="review-secondary"><button type="button" className="text-button" disabled={submitting} onClick={onLater}>Review later</button><button type="button" className="text-button remove-agent" disabled={submitting} onClick={onCancel}>Cancel workflow</button></div>
    </form>
  </dialog>;
}
