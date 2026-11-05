import type { AgentDefinition, AgentStatus, RunStatus } from '../types';
import { Panel } from './Panel';

interface Props {
  agents: AgentDefinition[];
  selected: string[];
  statuses: Record<string, AgentStatus>;
  approval: boolean;
  runStatus: RunStatus;
  elapsedMs: number;
}

export function OrchestrationGraph({ agents, selected, statuses, approval, runStatus, elapsedMs }: Props) {
  const specialists = agents.filter((agent) => !agent.core && selected.includes(agent.id));
  const height = Math.max(248, specialists.length * 57 + 28);
  const center = height / 2;
  const y = (index: number) => center - ((specialists.length - 1) * 57) / 2 + index * 57;
  const seconds = Math.floor(elapsedMs / 1000);
  const time = `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
  const active = runStatus === 'running';
  const path = (x1: number, y1: number, x2: number, y2: number, working = false) => <path d={`M${x1},${y1} C${(x1 + x2) / 2},${y1} ${(x1 + x2) / 2},${y2} ${x2},${y2}`} className={`edge ${active && working ? 'active' : ''}`} />;
  const node = (id: string, label: string, sub: string, x: number, cy: number, color: string, icon = '✳') => {
    const status = id === 'orchestrator'
      ? active ? 'working' : runStatus === 'complete' ? 'complete' : undefined
      : statuses[id];
    return <g transform={`translate(${x},${cy - 22})`}>
      <title>{label} · {status || sub}</title>
      <rect width="142" height="44" rx="8" className={`node-box ${status || ''}`} />
      <text x="11" y="18" fill={color} className="node-icon">{icon}</text>
      <text x="29" y="18" className="node-label">{label.length > 17 ? `${label.slice(0, 15)}…` : label}</text>
      <text x="11" y="33" className="node-sub">{(status || sub).toUpperCase()}</text>
    </g>;
  };
  return (
    <Panel index="03" title="Live orchestration" className="orchestration-panel" action={<div className={`live-indicator ${active ? 'running' : ''}`}><i />{runStatus === 'idle' ? 'STANDING BY' : runStatus.toUpperCase()}</div>}>
      <div className="flow-wrap"><svg viewBox={`0 0 840 ${height}`} role="img" aria-label="Selected specialists share scenario context; their findings feed oversight and final synthesis">
        <defs><linearGradient id="flow-gradient"><stop stopColor="#78a9ff" /><stop offset="1" stopColor="#62d6bd" /></linearGradient></defs>
        {specialists.map((agent, index) => <g key={`edge-${agent.id}`}>
          {path(158, center, 212, y(index), statuses[agent.id] === 'working')}
          {path(354, y(index), approval ? 479 : 680, center, statuses.human_review === 'working' || statuses.decision_synth === 'working')}
        </g>)}
        {approval && path(621, center, 680, center, statuses.decision_synth === 'working')}
        {node('orchestrator', 'Orchestrator', active ? 'COORDINATING' : 'SHARED CONTEXT', 16, center, '#9ba9ff')}
        {specialists.map((agent, index) => <g key={agent.id}>{node(agent.id, agent.name, 'QUEUED', 212, y(index), agent.color, agent.icon)}</g>)}
        {approval && node('human_review', 'Human oversight', 'REVIEW', 479, center, '#ff9fd0', '◎')}
        {node('decision_synth', 'Decision brief', 'SYNTHESIS', 680, center, '#9ba9ff')}
      </svg></div>
      <div className="flow-legend"><span><i className="legend-dot done" />Complete</span><span><i className="legend-dot active" />Working</span><span><i className="legend-dot idle" />Queued</span><span className="flow-clock" role="timer" aria-label="Elapsed time">{time}</span></div>
      <p className="flow-note">Specialists run sequentially for the local model, then share findings with review and synthesis.</p>
    </Panel>
  );
}
