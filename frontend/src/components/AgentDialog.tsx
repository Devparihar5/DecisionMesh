import { useEffect, useRef, useState } from 'react';
import type { AgentDefinition, AgentInput } from '../types';

interface Props { agent: AgentDefinition | null; onClose: () => void; onSave: (input: AgentInput) => Promise<void> }

export function AgentDialog({ agent, onClose, onSave }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { dialog.current?.showModal(); }, []);
  return (
    <dialog ref={dialog} aria-labelledby="agent-dialog-title" onCancel={(e) => { if (saving) e.preventDefault(); else onClose(); }}>
      <form onSubmit={async (e) => {
        e.preventDefault();
        const form = new FormData(e.currentTarget);
        setSaving(true); setError('');
        try {
          await onSave({ name: String(form.get('name')).trim(), role: String(form.get('role')).trim(),
            instructions: String(form.get('instructions')).trim(), color: agent?.color || '#78a9ff', icon: agent?.icon || '✳' });
          onClose();
        } catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not save this agent.'); }
        finally { setSaving(false); }
      }}>
        <div className="dialog-head"><div><span className="section-index">SPECIALIST ROLE</span><h2 id="agent-dialog-title">{agent ? 'Edit specialist' : 'Add a specialist'}</h2></div>
          <button type="button" className="icon-button" aria-label="Close dialog" disabled={saving} onClick={onClose}>×</button>
        </div>
        <fieldset disabled={saving}>
          <label htmlFor="agent-name">Name</label><input id="agent-name" name="name" autoFocus required minLength={2} maxLength={48} defaultValue={agent?.name} placeholder="e.g. Customer impact" />
          <label htmlFor="agent-role">Role</label><input id="agent-role" name="role" required minLength={2} maxLength={80} defaultValue={agent?.role} placeholder="e.g. Customer experience" />
          <label htmlFor="agent-instructions">Instructions</label><textarea id="agent-instructions" name="instructions" required minLength={8} maxLength={1200} defaultValue={agent?.instructions} placeholder="Describe the perspective this agent should contribute…" />
        </fieldset>
        {error && <p className="inline-error" role="alert">{error}</p>}
        <button className="run-button" disabled={saving}>{saving ? 'Saving…' : agent ? 'Save specialist' : 'Add to agent team'}<span aria-hidden="true">↗</span></button>
      </form>
    </dialog>
  );
}
