export interface AgentInput {
  name: string;
  role: string;
  instructions: string;
  icon: string;
  color: string;
}

export interface AgentDefinition extends AgentInput {
  id: string;
  core: boolean;
}

export interface HealthStatus {
  agno_installed: boolean;
  llm_url: string;
  llm_online: boolean;
  models: string[];
  default_model: string;
  error: string | null;
}

export interface RunInput {
  scenario: string;
  model: string;
  selected_agents: string[];
  require_approval: boolean;
  decision_case_id?: string;
}

export type EventType = 'start' | 'agent_start' | 'agent_done' | 'agent_error' | 'complete' | 'error' | 'review_required' | 'review_submitted';

/** Version 1 matches backend/app/orchestration/events.py. */
export interface RunEvent {
  version: 1;
  sequence: number;
  run_id: string;
  timestamp: string;
  type: EventType;
  agent_id?: string;
  name?: string;
  content?: string;
  message?: string;
  model?: string;
  agents?: string[];
  duration_ms?: number;
  elapsed_ms?: number;
  human_approval_required?: boolean;
  degraded: boolean;
  human_reviewed?: boolean;
  review_action?: 'finalize' | 'rerun';
  feedback?: string;
  parent_run_id?: string;
  decision_case_id?: string;
}

export type AgentStatus = 'queued' | 'working' | 'complete' | 'error' | 'skipped' | 'cancelled' | 'awaiting_review';
export type RunStatus = 'idle' | 'running' | 'complete' | 'failed' | 'cancelled' | 'awaiting_review';

export type StoredRunStatus = 'running' | 'complete' | 'failed' | 'cancelled' | 'interrupted' | 'awaiting_review' | 'revised';
export type ExecutionStatus = 'queued' | 'running' | 'complete' | 'failed' | 'cancelled' | 'skipped' | 'interrupted';

export interface RunSummary {
  id: string;
  scenario: string;
  model: string;
  status: StoredRunStatus;
  created_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  require_approval: boolean;
  degraded: boolean;
  error: string | null;
  agent_count: number;
  parent_run_id: string | null;
}

export interface ExecutionRecord {
  agent_id: string;
  name: string;
  role: string;
  color: string;
  status: ExecutionStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  content: string | null;
  error: string | null;
}

export interface RunDetail extends RunSummary {
  input_feedback: string;
  review_feedback: string | null;
  review_action: 'finalize' | 'rerun' | null;
  reviewed_at: string | null;
  agents: AgentDefinition[];
  executions: ExecutionRecord[];
  events: RunEvent[];
}

export interface RunPage {
  items: RunSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface AgentPerformance {
  agent_id: string;
  name: string;
  role: string;
  color: string;
  attempts: number;
  completed: number;
  failed: number;
  cancelled: number;
  interrupted: number;
  running: number;
  skipped: number;
  success_rate: number | null;
  average_duration_ms: number | null;
  p95_duration_ms: number | null;
  last_run_at: string | null;
}

export interface DailyRuns {
  date: string;
  total: number;
  completed: number;
  failed: number;
  cancelled: number;
  interrupted: number;
}

export interface AnalyticsReport {
  period_days: number;
  total_runs: number;
  completed_runs: number;
  partial_runs: number;
  failed_runs: number;
  cancelled_runs: number;
  interrupted_runs: number;
  running_runs: number;
  awaiting_review_runs: number;
  revised_runs: number;
  completion_rate: number | null;
  average_duration_ms: number | null;
  agents: AgentPerformance[];
  daily: DailyRuns[];
}

export interface ReviewInput { action: 'finalize' | 'rerun'; feedback: string }
