import type { ExecutionStatus, StoredRunStatus } from '../types';

export function StatusBadge({ status, partial = false }: { status: StoredRunStatus | ExecutionStatus; partial?: boolean }) {
  return <span className={`status-badge ${partial ? 'partial' : status}`}><i />{partial && status === 'complete' ? 'Partial' : status.replaceAll('_', ' ')}</span>;
}
