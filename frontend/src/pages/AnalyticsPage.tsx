import { useCallback, useState } from 'react';
import { AgentPerformanceTable } from '../components/AgentPerformanceTable';
import { MetricCard } from '../components/MetricCard';
import { RunActivityChart } from '../components/RunActivityChart';
import { useMemoryQuery } from '../hooks/useMemoryQuery';
import { duration, percent } from '../services/format';
import { memoryApi } from '../services/memory';

export function AnalyticsPage() {
  const [days, setDays] = useState(30);
  const load = useCallback((signal: AbortSignal) => memoryApi.analytics(days, signal), [days]);
  const { data, loading, error, refresh } = useMemoryQuery(load);
  return <main className="shell memory-page">
    <section className="memory-page-heading"><div><div className="eyebrow"><span />PERFORMANCE INTELLIGENCE</div><h1>Know your agents.<br /><span>Improve every run.</span></h1><p>Understand reliability and response time across your local decision workflows.</p></div>
      <div className="analytics-actions"><label htmlFor="analytics-period" className="sr-only">Analytics period</label><select id="analytics-period" value={days} onChange={(event) => setDays(Number(event.target.value))}><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option><option value={90}>Last 90 days</option><option value={0}>All time</option></select><button className="secondary-button" onClick={refresh} disabled={loading}>↻ Refresh</button></div>
    </section>
    {loading && <p className="memory-loading" role="status">Analyzing saved runs…</p>}
    {error && <div className="page-error" role="alert">{error}<button className="text-button" onClick={refresh}>Retry</button></div>}
    {data && <>
      <div className="metric-grid"><MetricCard label="TOTAL RUNS" value={String(data.total_runs)} note={`${data.running_runs} currently running`} /><MetricCard label="COMPLETION RATE" value={percent(data.completion_rate)} note={`${data.completed_runs} completed · ${data.partial_runs} partial`} accent /><MetricCard label="AVG WORKFLOW TIME" value={duration(data.average_duration_ms)} note="Completed workflows only" /><MetricCard label="FAILED RUNS" value={String(data.failed_runs)} note={`${data.cancelled_runs} cancelled · ${data.interrupted_runs} interrupted`} /></div>
      {!data.total_runs && <div className="notice">No saved runs in this period yet. <a href="#/">Start a workflow</a> to build your analytics.</div>}
      <RunActivityChart days={data.daily} />
      <AgentPerformanceTable agents={data.agents} />
      <p className="analytics-method">Metrics reflect observed execution, not decision accuracy. Completion rate includes partial workflows and excludes currently running runs from its denominator. Periods and daily buckets use UTC. {days === 0 ? 'All-time totals are shown; the chart covers the last 90 days.' : `Showing ${days} calendar days, including today.`}</p>
    </>}
  </main>;
}
