import type { AnalyticsReport, RunDetail, RunPage, StoredRunStatus } from '../types';
import { getJson } from './api';

export interface HistoryQuery {
  search: string;
  status: StoredRunStatus | '';
  offset: number;
}

export const memoryApi = {
  runs: (query: HistoryQuery, signal?: AbortSignal) => {
    const params = new URLSearchParams({ limit: '12', offset: String(query.offset), search: query.search });
    if (query.status) params.set('status', query.status);
    return getJson<RunPage>(`/api/runs?${params}`, { signal });
  },
  detail: (id: string, signal?: AbortSignal) => getJson<RunDetail>(`/api/runs/${encodeURIComponent(id)}`, { signal }),
  analytics: (days: number, signal?: AbortSignal) => getJson<AnalyticsReport>(`/api/analytics?days=${days}`, { signal }),
};
