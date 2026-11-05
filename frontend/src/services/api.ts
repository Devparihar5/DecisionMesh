import type { AgentDefinition, AgentInput, HealthStatus, RunInput } from '../types';

async function checked(response: Response): Promise<Response> {
  if (response.ok) return response;
  let message = `Request failed (${response.status}).`;
  try {
    const data = await response.json();
    if (typeof data.detail === 'string') message = data.detail;
    else if (Array.isArray(data.detail)) {
      message = data.detail.map((issue: { msg: string }) => issue.msg).join('; ');
    }
  } catch { /* A proxy error may have no JSON body. */ }
  throw new Error(message);
}

async function json<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await checked(await fetch(url, options));
  return response.json() as Promise<T>;
}

export { json as getJson };

const body = (value: unknown) => ({
  headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value),
});

export const api = {
  health: (signal?: AbortSignal) => json<HealthStatus>('/api/health', { signal }),
  agents: (signal?: AbortSignal) => json<AgentDefinition[]>('/api/agents', { signal }),
  createAgent: (value: AgentInput) => json<AgentDefinition>('/api/agents', { method: 'POST', ...body(value) }),
  updateAgent: (id: string, value: AgentInput) => json<AgentDefinition>(`/api/agents/${encodeURIComponent(id)}`, { method: 'PUT', ...body(value) }),
  deleteAgent: async (id: string) => { await checked(await fetch(`/api/agents/${encodeURIComponent(id)}`, { method: 'DELETE' })); },
  run: async (value: RunInput, signal: AbortSignal) => checked(await fetch('/api/run', {
    method: 'POST', ...body(value), signal,
  })),
};
