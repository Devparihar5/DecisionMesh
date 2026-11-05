import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { consumeEvents } from '../services/stream';
import type { RunEvent, RunInput, RunStatus } from '../types';

export function useRun() {
  const [status, setStatus] = useState<RunStatus>('idle');
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [error, setError] = useState('');
  const [elapsedMs, setElapsedMs] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const startedAt = useRef(0);
  const elapsed = useCallback(() => Math.round(performance.now() - startedAt.current), []);

  useEffect(() => () => { controller.current?.abort(); }, []);
  useEffect(() => {
    if (status !== 'running') return;
    const timer = window.setInterval(() => setElapsedMs(elapsed()), 200);
    return () => window.clearInterval(timer);
  }, [status, elapsed]);

  const start = useCallback(async (input: RunInput) => {
    if (controller.current) return;
    const current = new AbortController();
    controller.current = current;
    startedAt.current = performance.now();
    setElapsedMs(0);
    setEvents([]);
    setError('');
    setStatus('running');
    let terminal = false;
    try {
      const response = await api.run(input, current.signal);
      if (!response.body) throw new Error('The server did not return an event stream.');
      await consumeEvents(response.body, (event) => {
        setEvents((previous) => [...previous, event]);
        if (event.type === 'complete') { terminal = true; setStatus('complete'); }
        if (event.type === 'error') { terminal = true; setStatus('failed'); setError(event.message || 'Run failed.'); }
      });
      if (!terminal) throw new Error('The connection closed before the workflow completed.');
    } catch (cause) {
      if (current.signal.aborted) setStatus('cancelled');
      else {
        setStatus('failed');
        setError(cause instanceof Error ? cause.message : 'Could not run the workflow.');
      }
    } finally {
      controller.current = null;
      setElapsedMs(elapsed());
    }
  }, [elapsed]);

  const cancel = useCallback(() => { controller.current?.abort(); }, []);
  return { status, events, error, elapsedMs, start, cancel };
}
