import type { RunEvent } from '../types';
import { Panel } from './Panel';

export function EventTimeline({ events, live = true }: { events: RunEvent[]; live?: boolean }) {
  const latest = events.at(-1);
  return <Panel index="05" title="Execution log" action={<span className="quiet-label">{live ? 'LIVE EVENTS' : 'SAVED EVENTS'}</span>}>
    <p className="sr-only" role="status" aria-live="polite">{latest ? `${latest.name || 'Workflow'} ${latest.type.replaceAll('_', ' ')}` : 'No active workflow'}</p>
    {!events.length ? <p className="flow-note">The event timeline will record each step of your workflow.</p> : <ol className="timeline">
      {events.map((event) => <li key={event.sequence}><time dateTime={event.timestamp}>{new Date(event.timestamp).toLocaleTimeString()}</time><span className={event.type.includes('error') ? 'finding-error' : ''}>{event.name || 'Workflow'}</span><small>{event.type.replaceAll('_', ' ')}</small></li>)}
    </ol>}
  </Panel>;
}
