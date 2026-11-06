import { useEffect, useState } from 'react';

/** One in-flight read, cancellation on navigation, and visible refresh failures. */
export function usePollingResource<T>(load: ((signal: AbortSignal) => Promise<T>) | null, interval = 3000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => { setData(null); }, [load]);
  useEffect(() => {
    setError('');
    if (!load) return;
    const controller = new AbortController();
    let timer = 0;
    const poll = async () => {
      try { const value = await load(controller.signal); if (!controller.signal.aborted) { setData(value); setError(''); } }
      catch (cause) { if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not load data.'); }
      if (!controller.signal.aborted && interval) timer = window.setTimeout(() => { void poll(); }, interval);
    };
    void poll();
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [load, interval, revision]);
  return { data, error, refresh: () => setRevision((value) => value + 1) };
}
