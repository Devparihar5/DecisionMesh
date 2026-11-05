import { useEffect, useState } from 'react';

/** Abort stale reads on filter/page changes and expose an explicit refresh. */
export function useMemoryQuery<T>(load: (signal: AbortSignal) => Promise<T>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(''); setData(null);
    load(controller.signal).then((result) => {
      if (!controller.signal.aborted) setData(result);
    }).catch((cause) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not read local memory.');
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [load, revision]);
  return { data, loading, error, refresh: () => setRevision((value) => value + 1) };
}
