import type { CSSProperties } from 'react';
import type { AgentDefinition, AgentStatus } from '../types';
import { Panel } from './Panel';

interface Props {
  agents: AgentDefinition[];
  selected: string[];
  statuses: Record<string, AgentStatus>;
  locked: boolean;
  approval: boolean;
  onToggle: (id: string) => void;
  onAdd: () => void;
  onEdit: (agent: AgentDefinition) => void;
  onRemove: (id: string) => void;
}

export function AgentRoster(props: Props) {
  return (
    <Panel index="02" title="Agent team" action={<button className="text-button" onClick={props.onAdd} disabled={props.locked}>＋ Add agent</button>}>
      <div className="agent-list">
        {props.agents.map((agent) => {
          const included = agent.core ? agent.id !== 'human_review' || props.approval : props.selected.includes(agent.id);
          const status = props.statuses[agent.id] || (included ? 'ready' : 'skipped');
          return (
            <div className={`agent-row ${included ? '' : 'not-selected'}`} key={agent.id}>
              <input type="checkbox" className="agent-check" checked={included} disabled={props.locked || agent.core}
                aria-label={`Include ${agent.name}`} onChange={() => props.onToggle(agent.id)} />
              <span className="agent-icon" style={{ '--agent-color': agent.color } as CSSProperties}>{agent.icon}</span>
              <div className="agent-copy"><strong>{agent.name}</strong><small>{agent.role}</small></div>
              <span className={`agent-state ${status}`}>{status}</span>
              {!agent.core && <div className="agent-actions">
                <button className="icon-button" aria-label={`Edit ${agent.name}`} disabled={props.locked} onClick={() => props.onEdit(agent)}>✎</button>
                <button className="icon-button remove-agent" aria-label={`Remove ${agent.name}`} disabled={props.locked} onClick={() => props.onRemove(agent.id)}>×</button>
              </div>}
            </div>
          );
        })}
      </div>
      <p className="roster-note"><span className="roster-dot" />Shared scenario context · recommendations only</p>
    </Panel>
  );
}
