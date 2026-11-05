import type { RunEvent } from '../types';

/** Handles chunk boundaries, CRLF, multiline data, comments, and trailing frames. */
export async function consumeEvents(
  stream: ReadableStream<Uint8Array>, onEvent: (event: RunEvent) => void,
): Promise<void> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  const dispatch = (frame: string) => {
    const data = frame.split('\n').filter((line) => line.startsWith('data:'))
      .map((line) => line.slice(5).trimStart()).join('\n');
    if (!data) return;
    const event = JSON.parse(data) as RunEvent;
    if (event.version !== 1 || !event.type || !event.run_id) {
      throw new Error('Unsupported run event. Reload the app and backend.');
    }
    onEvent(event);
  };
  const flush = () => {
    buffer = buffer.replace(/\r\n/g, '\n');
    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      dispatch(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf('\n\n');
    }
  };
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      flush();
    }
    buffer += decoder.decode();
    flush();
    if (buffer.trim()) dispatch(buffer);
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
