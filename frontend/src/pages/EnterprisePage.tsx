import { useCallback, useEffect, useState } from 'react';
import { EnterpriseFeed } from '../components/EnterpriseFeed';
import { EntityCreator } from '../components/EntityCreator';
import { MetricCard } from '../components/MetricCard';
import { NegotiationTrace } from '../components/NegotiationTrace';
import { Panel } from '../components/Panel';
import { ResearchJobProgress } from '../components/ResearchJobProgress';
import { ResearchModelPicker } from '../components/ResearchModelPicker';
import { SimulatedAction } from '../components/SimulatedAction';
import { TwinComparison } from '../components/TwinComparison';
import { usePollingResource } from '../hooks/usePollingResource';
import { api } from '../services/api';
import { enterpriseApi } from '../services/enterprise';
import type { AgentDefinition } from '../types';
import type { ActionKind, Execution } from '../types/enterprise';

export function EnterprisePage() {
  const [entityId, setEntityId] = useState('');
  const [caseId, setCaseId] = useState('');
  const [jobId, setJobId] = useState('');
  const [model, setModel] = useState('');
  const [agents, setAgents] = useState<AgentDefinition[]>([]);
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [action, setAction] = useState<ActionKind>('hold');
  const [error, setError] = useState('');
  const [starting, setStarting] = useState(false);
  const [outcome, setOutcome] = useState<Execution | null>(null);
  const loadEntities = useCallback((signal: AbortSignal) => enterpriseApi.entities(signal), []);
  const entities = usePollingResource(loadEntities, 10000);
  const loadSnapshot = useCallback((signal: AbortSignal) => enterpriseApi.snapshot(entityId, signal), [entityId]);
  const snapshot = usePollingResource(entityId ? loadSnapshot : null);
  const loadJob = useCallback((signal: AbortSignal) => enterpriseApi.job(jobId, signal), [jobId]);
  const job = usePollingResource(jobId ? loadJob : null);
  const loadJobs = useCallback((signal: AbortSignal) => enterpriseApi.jobs('negotiation', signal), []);
  const jobs = usePollingResource(loadJobs, 5000);
  const data = snapshot.data?.entity.id === entityId ? snapshot.data : null;
  const currentCase = data?.cases.find((item) => item.id === caseId);
  const loadArchivedCase = useCallback((signal: AbortSignal) => enterpriseApi.case(caseId, signal), [caseId]);
  const archivedCase = usePollingResource(caseId && data && !currentCase ? loadArchivedCase : null, 5000);
  const archived = archivedCase.data?.id === caseId ? archivedCase.data : undefined;
  const decision = caseId ? currentCase || archived || undefined : data?.cases[0];
  const latestRound = decision?.rounds.at(-1);
  const decisionKey = `${decision?.id}-${decision?.rounds.length}-${latestRound?.selected_action}`;
  const negotiating = starting || !!jobs.data?.some((item) => item.config.case_id === decision?.id && item.status === 'running');
  const stale = !!decision && decision.state_version !== data?.entity.version;
  useEffect(() => {
    const first = entities.data?.[0];
    if (first) setEntityId((current) => current || first.id);
  }, [entities.data]);
  useEffect(() => { if (decision) setAction(decision.selected_action); }, [decisionKey]); // Reset only when the decision changes.
  useEffect(() => {
    const controller = new AbortController();
    api.agents(controller.signal).then((catalog) => {
      const specialists = catalog.filter((agent) => !agent.core);
      const preferred = ['operations', 'finance', 'risk', 'compliance'];
      setAgents(specialists); setSelectedAgents([...specialists].sort((left, right) => {
        const rank = (id: string) => preferred.includes(id) ? preferred.indexOf(id) : preferred.length;
        return rank(left.id) - rank(right.id);
      }).slice(0, 4).map((agent) => agent.id));
    }).catch((cause) => { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Catalog unavailable.'); });
    return () => controller.abort();
  }, []);
  const negotiate = async () => {
    if (!decision) return;
    setStarting(true); setError('');
    try { const created = await enterpriseApi.negotiate(decision.id, model, selectedAgents); setJobId(created.id); jobs.refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not start negotiation.'); }
    finally { setStarting(false); }
  };
  return <main className="shell memory-page enterprise-page">
    <section className="lab-heading"><div className="eyebrow"><span />ENTERPRISE DECISION LOOP</div><h1>Observe. Negotiate. Act.</h1><p>Versioned enterprise events → agent proposals → twin simulation → approved local action → outcome feedback.</p></section>
    <div className="lab-toolbar"><label>Inventory twin<select value={entityId} onChange={(event) => { setEntityId(event.target.value); setCaseId(''); setJobId(''); setOutcome(null); }}>
      <option value="">Choose or create an entity</option>{entities.data?.map((entity) => <option value={entity.id} key={entity.id}>{entity.name}</option>)}</select></label>
      <button className="text-button" onClick={() => { entities.refresh(); snapshot.refresh(); }}>Refresh</button></div>
    <EntityCreator onCreated={(entity) => { entities.refresh(); setEntityId(entity.id); setCaseId(''); }} />
    {(error || entities.error || snapshot.error || job.error || jobs.error || archivedCase.error) && <p className="notice" role="alert">{error || entities.error || snapshot.error || job.error || jobs.error || archivedCase.error}</p>}
    {!entityId && <p className="notice">Create your first inventory twin above, then send a disruption or an external event.</p>}
    {data && <>
      <div className="metric-grid"><MetricCard label="STATE VERSION" value={`v${data.entity.version}`} note={`${data.entity.simulated_steps} simulated actions`} /><MetricCard label="INVENTORY / DEMAND" value={`${data.entity.state.inventory} / ${data.entity.state.demand}`} note="Units · unmet demand becomes backlog after execution" /><MetricCard label="DAILY CAPACITY" value={String(data.entity.state.capacity)} note={`${data.entity.state.backup_capacity} backup units available`} /><MetricCard label="REMAINING BUDGET" value={data.entity.state.budget.toFixed(2)} note="Local scenario currency units" /></div>
      <Panel index="01" title="Enterprise event ingestion"><EnterpriseFeed key={entityId} entityId={entityId} onReceipt={(receipt) => {
        if (receipt.case_id) setCaseId(receipt.case_id); snapshot.refresh();
      }} /></Panel>
      {decision ? <>
        <Panel index="02" title="Decision and agent negotiation">
          <div className="lab-toolbar"><label>Saved decision<select value={decision.id} onChange={(event) => setCaseId(event.target.value)}>{!data.cases.some((item) => item.id === decision.id) && <option value={decision.id}>v{decision.state_version} · archived decision · {decision.id.slice(0, 8)}</option>}{data.cases.map((item) => <option key={item.id} value={item.id}>v{item.state_version} · {item.origin.replaceAll('_', ' ')} · {item.id.slice(0, 8)}</option>)}</select></label>
            <span className="status-badge">{decision.status.replaceAll('_', ' ')}</span></div>
          <p className="lab-muted">Evidence: {decision.evidence.join(' · ')}. Rule: {decision.rule_version}. Initial proposals are explicitly rule-based; Run agent negotiation calls your selected Agno specialists.</p>
          {decision.drift && <p className="notice">Inventory drift: predicted {decision.drift.predicted_inventory}, observed {decision.drift.observed_inventory} ({decision.drift.difference_units > 0 ? '+' : ''}{decision.drift.difference_units} units).</p>}
          {stale && <p className="notice">This decision is based on an older state. <button className="text-button" onClick={() => setCaseId(data.cases[0].id)}>Open latest decision</button></p>}
          <ResearchModelPicker value={model} onChange={setModel} disabled={negotiating} />
          <fieldset className="negotiator-selection"><legend>Specialists · choose 2–7</legend>{agents.map((agent) => <label key={agent.id}><input type="checkbox" checked={selectedAgents.includes(agent.id)} disabled={negotiating} onChange={() => setSelectedAgents((items) => items.includes(agent.id) ? items.filter((id) => id !== agent.id) : [...items, agent.id])} />{agent.name}</label>)}</fieldset>
          <div className="lab-actions"><button className="secondary-button" onClick={() => { void negotiate(); }} disabled={stale || negotiating || !!decision.execution_id || selectedAgents.length < 2 || selectedAgents.length > 7}>{negotiating ? 'Agents negotiating…' : 'Run agent negotiation →'}</button>
            <a href={`#/?case=${encodeURIComponent(decision.id)}`}>Open evidence in decision workspace →</a></div>
          <p className="lab-muted">At most two rounds. Agents see peer proposals on the second round. Hard budget limits take priority; feasible proposals are ranked by the published service/cost utility.</p>
          <NegotiationTrace rounds={decision.rounds} />
          {jobs.data && jobs.data.some((item) => item.config.case_id === decision.id) && <label className="lab-job-select">Negotiation jobs<select value={jobId} onChange={(event) => setJobId(event.target.value)}><option value="">Choose a saved job</option>{jobs.data.filter((item) => item.config.case_id === decision.id).map((item) => <option value={item.id} key={item.id}>{item.status} · {item.id.slice(0, 8)}</option>)}</select></label>}
          {job.data && job.data.config.case_id === decision.id && <ResearchJobProgress job={job.data} onChange={() => { job.refresh(); jobs.refresh(); snapshot.refresh(); }} />}
        </Panel>
        <Panel index="03" title="Digital twin · compare candidate outcomes">
          <p className="lab-muted">One-day model: normal production, up to 25% overtime capacity, backup supply, or inventory-only deferral. No arrivals, uncertainty distribution, or enterprise transactions are assumed.</p>
          <TwinComparison candidates={decision.candidates} selected={action} onSelect={setAction} />
          <p className="arbitration-rule">Recommended: <strong>{decision.selected_action}</strong>. {decision.review_reasons.join(' · ') || 'Within local policy thresholds; explicit approval is still required for simulation execution.'}</p>
          <details><summary>Rejected alternatives and reasons</summary>{Object.entries(decision.rejection_reasons).map(([name, reason]) => <p key={name}><strong>{name}:</strong> {reason}</p>)}</details>
          <SimulatedAction key={decisionKey} decision={decision} action={action} stale={stale} negotiating={negotiating} onExecuted={(receipt) => { setOutcome(receipt); snapshot.refresh(); }} />
        </Panel>
      </> : <p className="notice">{caseId ? 'Loading saved decision…' : 'Send your first event to create a decision and compare simulated actions.'}</p>}
      {(outcome || data.executions.length > 0) && <Panel index="04" title="Action acknowledgments and feedback">
        {(outcome && !data.executions.some((item) => item.id === outcome.id) ? [outcome, ...data.executions] : data.executions).map((item) => <article className="outcome-record" key={item.id}><h3>{item.action} · simulated</h3><p>Served {item.outcome.served}; unmet {item.outcome.unmet}; spend {item.outcome.cost.toFixed(2)}. State v{item.before_version} → v{item.after_version}. Reviewed by {item.approval.reviewer}.</p><button className="text-button" onClick={() => setCaseId(item.feedback_case_id)}>Open outcome reassessment →</button></article>)}
      </Panel>}
      <Panel index="05" title="Incoming event ledger"><div className="event-ledger">{data.events.length ? data.events.map((item) => <details key={`${item.event.source}-${item.event.event_id}`}><summary>{item.receipt.status} · {item.event.source} · {new Date(item.received_at).toLocaleTimeString()}</summary><pre>{JSON.stringify(item, null, 2)}</pre></details>) : <p className="lab-muted">No events received yet.</p>}</div></Panel>
    </>}
  </main>;
}
