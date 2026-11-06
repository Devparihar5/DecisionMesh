import { getJson } from './api';
import type { ActionKind, Approval, DecisionCase, EnterpriseEvent, EnterpriseSnapshot, EventReceipt, Execution, Inventory, ResearchJob, TwinState } from '../types/enterprise';

const post = <T,>(url: string, value: unknown) => getJson<T>(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) });
const id = encodeURIComponent;
export const enterpriseApi = {
  entities: (signal?: AbortSignal) => getJson<TwinState[]>('/api/enterprise/entities', { signal }),
  create: (value: {id: string; name: string; state: Inventory}) => post<TwinState>('/api/enterprise/entities', value),
  snapshot: (entity: string, signal?: AbortSignal) => getJson<EnterpriseSnapshot>(`/api/enterprise/entities/${id(entity)}`, { signal }),
  event: (value: EnterpriseEvent) => post<EventReceipt>('/api/enterprise/events', value),
  case: (caseId: string, signal?: AbortSignal) => getJson<DecisionCase>(`/api/enterprise/cases/${id(caseId)}`, { signal }),
  negotiate: (caseId: string, model: string, agents: string[]) => post<ResearchJob>(`/api/enterprise/cases/${id(caseId)}/negotiate`, { model, agents }),
  approve: (caseId: string, value: {action: ActionKind; state_version: number; reviewer: string; rationale: string}) => post<Approval>(`/api/enterprise/cases/${id(caseId)}/approvals`, value),
  execute: (caseId: string, approvalId: string, key: string) => post<Execution>(`/api/enterprise/cases/${id(caseId)}/execute`, { approval_id: approvalId, idempotency_key: key }),
  jobs: (kind: string, signal?: AbortSignal) => getJson<ResearchJob[]>(`/api/research/jobs?kind=${id(kind)}`, { signal }),
  job: (jobId: string, signal?: AbortSignal) => getJson<ResearchJob>(`/api/research/jobs/${id(jobId)}`, { signal }),
  cancel: (jobId: string) => post<ResearchJob>(`/api/research/jobs/${id(jobId)}/cancel`, {}),
  benchmark: (model: string, repetitions: number) => post<ResearchJob>('/api/research/benchmarks', { model, repetitions }),
  dataset: (signal?: AbortSignal) => getJson<{version: string; cases: {id: string; name: string; state: Inventory}[]}>('/api/research/dataset', { signal }),
};
