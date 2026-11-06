import { useCallback, useState } from 'react';
import { BenchmarkResults } from '../components/BenchmarkResults';
import { Panel } from '../components/Panel';
import { ResearchJobProgress } from '../components/ResearchJobProgress';
import { ResearchModelPicker } from '../components/ResearchModelPicker';
import { usePollingResource } from '../hooks/usePollingResource';
import { enterpriseApi } from '../services/enterprise';
import type { BenchmarkTrial } from '../types/enterprise';

export function ResearchPage() {
  const [model, setModel] = useState('');
  const [repetitions, setRepetitions] = useState(1);
  const [selectedId, setSelectedId] = useState('');
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const loadJobs = useCallback((signal: AbortSignal) => enterpriseApi.jobs('benchmark', signal), []);
  const jobs = usePollingResource(loadJobs, 5000);
  const loadDataset = useCallback((signal: AbortSignal) => enterpriseApi.dataset(signal), []);
  const dataset = usePollingResource(loadDataset, 0);
  const selected = jobs.data?.find((item) => item.id === selectedId) || jobs.data?.[0];
  const id = selected?.id || selectedId;
  const loadJob = useCallback((signal: AbortSignal) => enterpriseApi.job(id, signal), [id]);
  const job = usePollingResource(id ? loadJob : null, 2500);
  const active = job.data?.id === id ? job.data : selected;
  const pending = jobs.data?.some((item) => item.status === 'running') || starting;
  const trials = active?.result?.trials || active?.progress.filter((item) => item.stage === 'trial_complete').map((item) => item.trial).filter((item): item is BenchmarkTrial => !!item) || [];
  const start = async () => {
    setStarting(true); setError('');
    try { const created = await enterpriseApi.benchmark(model, repetitions); setSelectedId(created.id); jobs.refresh(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not start benchmark.'); }
    finally { setStarting(false); }
  };
  return <main className="shell memory-page research-page">
    <section className="lab-heading"><div className="eyebrow"><span />RESEARCH EVALUATION</div><h1>Measure the decision.</h1><p>Compare a centralized Agno analyst with bounded multi-agent negotiation on the same six inventory scenarios and selected model.</p></section>
    {(error || jobs.error || job.error || dataset.error) && <p className="notice" role="alert">{error || jobs.error || job.error || dataset.error}</p>}
    <Panel index="01" title="Controlled benchmark">
      <ResearchModelPicker value={model} onChange={setModel} disabled={!!pending} />
      <div className="lab-toolbar"><label>Repetitions<select value={repetitions} disabled={!!pending} onChange={(event) => setRepetitions(Number(event.target.value))}><option value={1}>1 · 12 architecture trials</option><option value={2}>2 · 24 architecture trials</option><option value={3}>3 · 36 architecture trials</option></select></label>
        <button className="run-button" disabled={!!pending} onClick={() => { void start(); }}>{starting ? 'Starting…' : pending ? 'Benchmark running…' : 'Run live-model benchmark →'}</button></div>
      <p className="lab-muted">This performs real model calls and may take several minutes. Centralized: one proposal per scenario. Orchestrated: up to four specialists over two rounds. Each proposal permits one format-repair call, included in timings and call counts. Jobs continue while you navigate, can be cancelled, and retain partial trials. Calls share the local model concurrency limit with the workspace.</p>
      <details><summary>Dataset · {dataset.data?.version || 'loading'}</summary><div className="dataset-grid">{dataset.data?.cases.map((item) => <article key={item.id}><h3>{item.name}</h3><p>Inventory {item.state.inventory}, demand {item.state.demand}, capacity {item.state.capacity}, budget {item.state.budget}.</p></article>)}</div></details>
    </Panel>
    <Panel index="02" title="Saved experiments and results">
      <div className="lab-toolbar"><label>Experiment<select value={active?.id || ''} onChange={(event) => setSelectedId(event.target.value)}><option value="">Choose an experiment</option>{jobs.data?.map((item) => <option key={item.id} value={item.id}>{new Date(item.created_at).toLocaleString()} · {item.status} · {item.config.model}</option>)}</select></label><button className="text-button" onClick={() => { jobs.refresh(); job.refresh(); }}>Refresh</button></div>
      {active ? <><ResearchJobProgress job={active} onChange={() => { jobs.refresh(); job.refresh(); }} /><p className="lab-muted">Completed trials: {trials.length}. Trials without a valid proposal score zero. Partial agent failures are retained and reported separately.</p><BenchmarkResults summary={active.result?.summary} trials={trials} /></> : <p className="lab-muted">No experiments yet. Run the benchmark to populate measured results.</p>}
    </Panel>
    <Panel index="03" title="Rubric and interpretation">
      <p>Every candidate is evaluated by the same deterministic one-day twin. Hard budget violations are disallowed. Utility = 100 × served/demand − 5 × cost/budget. The oracle enumerates all four actions. Quality compares chosen utility with the best feasible utility; invalid responses and policy violations score zero.</p>
      <ul><li>Both architectures receive identical state, evidence, and candidate simulations. Execution order alternates by scenario and repetition.</li><li>Agent instructions, dataset snapshot/hash, model ID, rules, proposal traces, errors, outcomes, and timings are retained in the JSON export.</li><li>Latency includes model queueing and machine processing; human waiting is excluded. Call counts differ and are displayed.</li><li>The orchestrated variant includes deterministic policy/arbitration. Gains cannot be attributed solely to agent reasoning.</li><li>Evidence coverage checks reference IDs. Explanation truth, human trust, actual human intervention, and recovery time are unmeasured.</li><li>This benchmark measures synthetic inventory decisions under a published rubric. It does not establish enterprise-scale or general decision-making quality.</li></ul>
      {active?.config.limitations && <details><summary>Saved experiment limitations</summary><ul>{active.config.limitations.map((item) => <li key={item}>{item}</li>)}</ul></details>}
    </Panel>
  </main>;
}
