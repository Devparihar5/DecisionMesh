import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { consumeEvents } from '../services/stream';
import type { ReviewInput, RunEvent, RunInput, RunStatus } from '../types';

export function useRun() {
  const [status, setStatus] = useState<RunStatus>('idle');
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [review, setReview] = useState<RunEvent | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [elapsedMs, setElapsedMs] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const startedAt = useRef(0);
  const baseElapsed = useRef(0);
  const elapsed = useCallback(() => baseElapsed.current + Math.round(performance.now() - startedAt.current), []);

  useEffect(() => () => { controller.current?.abort(); }, []);
  useEffect(() => {
    if (status !== 'running') return;
    const timer = window.setInterval(() => setElapsedMs(elapsed()), 200);
    return () => window.clearInterval(timer);
  }, [status, elapsed]);

  const execute = useCallback(async (
    request: (signal: AbortSignal) => Promise<Response>, reset: boolean, seed?: RunEvent[],
  ) => {
    if (controller.current) return;
    const current = new AbortController();
    controller.current = current;
    startedAt.current = performance.now();
    if (reset) { baseElapsed.current = 0; setElapsedMs(0); setEvents([]); setReview(null); }
    if (seed) setEvents(seed);
    setError(''); setStatus('running');
    let terminal = false, accepted = false;
    let measured: number | undefined;
    try {
      const response = await request(current.signal);
      accepted = true; setReview(null); setSubmitting(false);
      if (!response.body) throw new Error('The server did not return an event stream.');
      await consumeEvents(response.body, (event) => {
        // A rerun starts a new linked run; finalization keeps the original log.
        if (event.type === 'start' && event.parent_run_id) {
          baseElapsed.current = 0; startedAt.current = performance.now(); setEvents([event]);
        } else setEvents((previous) => [...previous, event]);
        if (event.type === 'review_required') {
          terminal = true; measured = event.elapsed_ms; setStatus('awaiting_review'); setReview(event);
        }
        if (event.type === 'complete') { terminal = true; measured = event.elapsed_ms; setStatus('complete'); }
        if (event.type === 'error') { terminal = true; measured = event.elapsed_ms; setStatus('failed'); setError(event.message || 'Run failed.'); }
      });
      if (!terminal) throw new Error('The connection closed before the workflow reached a checkpoint.');
    } catch (cause) {
      if (current.signal.aborted) { setStatus('cancelled'); setReview(null); }
      else {
        // A review rejected before streaming is still pending and can be retried.
        setStatus(!reset && !accepted ? 'awaiting_review' : 'failed');
        setError(cause instanceof Error ? cause.message : 'Could not run the workflow.');
      }
    } finally {
      controller.current = null; setSubmitting(false);
      baseElapsed.current = measured ?? elapsed();
      setElapsedMs(baseElapsed.current);
    }
  }, [elapsed]);

  const start = useCallback((input: RunInput) => execute((signal) => api.run(input, signal), true), [execute]);
  const submitReview = useCallback((input: ReviewInput, checkpoint?: RunEvent, seed?: RunEvent[]) => {
    const target = checkpoint || review;
    if (!target || controller.current) return Promise.resolve();
    setReview(target); setSubmitting(true);
    return execute((signal) => api.review(target.run_id, input, signal), false, seed);
  }, [execute, review]);
  const restoreReview = useCallback((checkpoint: RunEvent, savedEvents: RunEvent[]) => {
    setEvents(savedEvents); setReview(checkpoint); setStatus('awaiting_review');
  }, []);
  const cancel = useCallback(async () => {
    controller.current?.abort();
    if (review) {
      setSubmitting(true);
      try { await api.cancelReview(review.run_id); setReview(null); setStatus('cancelled'); }
      catch (cause) { setError(cause instanceof Error ? cause.message : 'Could not cancel review.'); }
      finally { setSubmitting(false); }
    }
  }, [review]);
  return { status, events, review, submitting, error, elapsedMs, start, submitReview, restoreReview, cancel };
}
