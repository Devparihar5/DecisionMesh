import { useState } from 'react';
import type { DailyRuns } from '../types';
import { Panel } from './Panel';

export function RunActivityChart({ days }: { days: DailyRuns[] }) {
  const [inspected, setInspected] = useState<string | null>(null);
  const maximum = Math.max(1, ...days.map((day) => day.total));
  const focused = days.find((day) => day.date === inspected) || days.at(-1);
  return <Panel index="TREND" title="Run activity" action={<span className="quiet-label">DAILY · UTC</span>}>
    <div className="activity-chart" role="group" aria-label="Daily run counts; focus a day for its outcomes">
      {days.map((day) => <button className={`activity-day ${day.date === inspected ? 'inspected' : ''}`} key={day.date} onFocus={() => setInspected(day.date)} onMouseEnter={() => setInspected(day.date)} onClick={() => setInspected(day.date)}
        aria-label={`${day.date}: ${day.total} runs, ${day.completed} completed, ${day.failed} failed`}>
        <div className="activity-stack" style={{ height: `${Math.max(2, day.total / maximum * 100)}%` }}>
          {day.total > 0 ? <><span className="completed" style={{ flex: day.completed }} /><span className="failed" style={{ flex: day.failed }} /><span className="other" style={{ flex: day.total - day.completed - day.failed }} /></> : <span className="zero" />}
        </div>
      </button>)}
    </div>
    <div className="chart-dates"><span>{days[0]?.date}</span><span>{days.at(-1)?.date}</span></div>
    <div className="chart-legend"><span><i className="completed" />Completed</span><span><i className="failed" />Failed</span><span><i className="other" />Other</span></div>
    <p className="chart-inspection" aria-live="polite">{focused?.date} · {focused?.total} runs · {focused?.completed} completed · {focused?.failed} failed · {focused?.cancelled} cancelled · {focused?.interrupted} interrupted</p>
  </Panel>;
}
