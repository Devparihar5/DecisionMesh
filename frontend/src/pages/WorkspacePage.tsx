import { useCallback, useEffect, useRef, useState } from 'react';
import { AgentDialog } from '../components/AgentDialog';
import { AgentRoster } from '../components/AgentRoster';
import { EventTimeline } from '../components/EventTimeline';
import { Header } from '../components/Header';
import { OrchestrationGraph } from '../components/OrchestrationGraph';
import { RunFindings } from '../components/RunFindings';
import { ReviewDialog } from '../components/ReviewDialog';
import { SCENARIOS } from '../data/scenarios';
import { memoryApi } from '../services/memory';
import { ScenarioComposer } from '../components/ScenarioComposer';
import { useRun } from '../hooks/useRun';
import { api } from '../services/api';
import type { AgentDefinition, AgentInput, AgentStatus, HealthStatus } from '../types';

export function WorkspacePage({ active = true }: { active?: boolean }) {
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [model, setModel] = useState('');
  const [scenario, setScenario] = useState(SCENARIOS[0].scenario);
  const [approval, setApproval] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [catalogBusy, setCatalogBusy] = useState(false);
  const [error, setError] = useState('');
  const [dialog, setDialog] = useState<{ agent: AgentDefinition | null } | null>(null);
  const [runSelection, setRunSelection] = useState<string[] | null>(null);
  const [runAgents, setRunAgents] = useState<AgentDefinition[] | null>(null);
  const [runApproval, setRunApproval] = useState(true);
  const { status, events, review, submitting, error: runError, elapsedMs, start, submitReview, restoreReview, cancel } = useRun();
  const [reviewHidden, setReviewHidden] = useState(false);
  const awaitingReview = status === 'awaiting_review';
  const busy = status === 'running' || awaitingReview;
  const running = status === 'running';
  const refreshController = useRef<AbortController | null>(null);

  const refreshHealth = useCallback(async () => {
    refreshController.current?.abort();
    const controller = new AbortController();
    refreshController.current = controller;
    setRefreshing(true);
    try {
      const next = await api.health(controller.signal);
      setHealth(next);
      setModel((current) => next.models.includes(current) ? current : next.models.includes(next.default_model) ? next.default_model : next.models[0] || '');
    } catch (cause) {
      if (!controller.signal.aborted) {
        setHealth(null);
        setError(cause instanceof Error ? cause.message : 'Could not reach the API.');
      }
    } finally { if (!controller.signal.aborted) setRefreshing(false); }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void refreshHealth();
    api.agents(controller.signal).then((catalog) => {
      setAgents(catalog); setSelected(catalog.filter((agent) => !agent.core).map((agent) => agent.id));
    }).catch((cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not load agents.'); });
    return () => { controller.abort(); refreshController.current?.abort(); };
  }, [refreshHealth]);

  const canRun = active && !busy && !catalogBusy && !dialog && scenario.trim().length >= 8 && selected.length > 0 && !!model && !!health?.llm_online && !!health.agno_installed;
  const run = useCallback(() => {
    if (!canRun) return;
    setRunSelection([...selected]); setRunApproval(approval); setRunAgents([...agents]);
    void start({ scenario: scenario.trim(), model, selected_agents: selected, require_approval: approval });
  }, [canRun, selected, approval, start, scenario, model, agents]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') { event.preventDefault(); run(); }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [run]);

  useEffect(() => { if (review) setReviewHidden(false); }, [review]);

  useEffect(() => {
    if (!active) return;
    const id = new URLSearchParams(window.location.hash.split('?')[1] || '').get('review');
    if (!id) return;
    if (busy) { setError('Finish or cancel the current workflow before opening another saved review.'); return; }
    const controller = new AbortController();
    memoryApi.detail(id, controller.signal).then((saved) => {
      if (controller.signal.aborted) return;
      const checkpoint = [...saved.events].reverse().find((event) => event.type === 'review_required');
      if (saved.status !== 'awaiting_review' || !checkpoint) throw new Error('This run is no longer awaiting review.');
      setScenario(saved.scenario); setApproval(true); setRunApproval(true); setRunAgents(saved.agents);
      setRunSelection(saved.agents.filter((agent) => !agent.core).map((agent) => agent.id));
      restoreReview(checkpoint, saved.events);
      window.history.replaceState(null, '', '#/');
    }).catch((cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not load saved review.'); });
    return () => controller.abort();
  }, [active, busy, restoreReview]);

  const statuses: Record<string, AgentStatus> = {};
  for (const event of events) {
    if (!event.agent_id) continue;
    if (event.type === 'agent_start') statuses[event.agent_id] = 'working';
    if (event.type === 'agent_done') statuses[event.agent_id] = 'complete';
    if (event.type === 'agent_error') statuses[event.agent_id] = 'error';
  }
  if (awaitingReview) statuses.human_review = 'awaiting_review';
  if (status === 'cancelled' || status === 'failed') {
    for (const id of Object.keys(statuses)) if (statuses[id] === 'working') statuses[id] = 'cancelled';
  }

  const saveAgent = async (input: AgentInput) => {
    const previous = dialog?.agent;
    const agent = previous ? await api.updateAgent(previous.id, input) : await api.createAgent(input);
    setAgents((current) => previous ? current.map((item) => item.id === agent.id ? agent : item) : [...current, agent]);
    if (!previous) setSelected((current) => [...current, agent.id]);
  };
  const removeAgent = async (id: string) => {
    setCatalogBusy(true); setError('');
    try { await api.deleteAgent(id); setAgents((current) => current.filter((agent) => agent.id !== id)); setSelected((current) => current.filter((item) => item !== id)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not remove agent.'); }
    finally { setCatalogBusy(false); }
  };

  return <div className="shell">
    <Header health={health} model={model} busy={busy} refreshing={refreshing} onModelChange={setModel} onRefresh={() => { setError(''); void refreshHealth(); }} />
    <main className="workspace-main">
      <h1 className="sr-only">Decision workspace</h1>
      {error && <div className="page-error" role="alert">{error}<button type="button" className="icon-button" onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
      {health && (!health.llm_online || !health.models.length) && <p className="notice">{health.error || 'The model server has no available models. Download or enable a chat model, then refresh.'} <span>Configured endpoint: <code>{health.llm_url}</code></span></p>}
      {health && !health.agno_installed && <p className="notice">The agent runtime is unavailable. Install the backend dependencies with Poetry.</p>}
      {awaitingReview && <div className="review-waiting" role="status"><span>Workflow paused for your review. Add suggestions, rerun analysis, or generate a final brief.</span><button className="secondary-button" onClick={() => setReviewHidden(false)}>Review & continue →</button></div>}
      <div className="workspace"><aside className="left-column">
        <ScenarioComposer scenario={scenario} approval={approval} running={running} awaitingReview={awaitingReview} canRun={canRun} onScenario={setScenario} onApproval={setApproval} onRun={run} onCancel={() => { void cancel(); }} />
        <AgentRoster agents={awaitingReview && runAgents ? runAgents : agents} selected={awaitingReview && runSelection ? runSelection : selected} statuses={statuses} approval={approval} locked={busy || catalogBusy} onToggle={(id) => setSelected((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id])} onAdd={() => setDialog({ agent: null })} onEdit={(agent) => setDialog({ agent })} onRemove={(id) => { void removeAgent(id); }} />
      </aside><section className="right-column" aria-label="Run workspace">
        <OrchestrationGraph agents={runAgents || agents} selected={runSelection || selected} statuses={statuses} approval={runSelection ? runApproval : approval} runStatus={status} elapsedMs={elapsedMs} />
        <RunFindings events={events} status={status} error={runError} />
        <EventTimeline events={events} />
      </section></div>
    </main>
    <footer><span>DECISIONMESH · LOCAL DECISION INTELLIGENCE</span><span>POWERED BY AGNO · YOUR MODEL STAYS LOCAL</span></footer>
    {active && review && !reviewHidden && <ReviewDialog key={`${review.run_id}-${review.sequence}`} checkpoint={review} findings={events} submitting={submitting} error={runError}
      onSubmit={(input) => { void submitReview(input); }} onLater={() => setReviewHidden(true)} onCancel={() => { void cancel(); }} />}
    {dialog && <AgentDialog agent={dialog.agent} onClose={() => setDialog(null)} onSave={saveAgent} />}
  </div>;
}
