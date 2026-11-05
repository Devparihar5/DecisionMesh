import assert from 'node:assert/strict';
import { test } from 'node:test';
import { consumeEvents } from '../src/services/stream.ts';

function stream(chunks) {
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
      controller.close();
    },
  });
}

const event = { version: 1, sequence: 1, run_id: 'example', timestamp: '', type: 'start', degraded: false };

test('parses fragmented frames, CRLF, heartbeat, and a final unterminated frame', async () => {
  const result = [];
  const source = `: keepalive\r\n\r\nevent: start\r\ndata: ${JSON.stringify(event)}\r\n\r\ndata: ${JSON.stringify({ ...event, sequence: 2, type: 'complete' })}`;
  const chunks = [...source]; // Every byte-sized character may arrive in a separate chunk.
  await consumeEvents(stream(chunks), (value) => result.push(value));
  assert.deepEqual(result.map((value) => value.type), ['start', 'complete']);
});

test('rejects incompatible event versions', async () => {
  await assert.rejects(consumeEvents(stream([`data: ${JSON.stringify({ ...event, version: 2 })}\n\n`]), () => {}), /Unsupported run event/);
});

test('preserves non-ASCII content across byte boundaries', async () => {
  const bytes = new TextEncoder().encode(`data: ${JSON.stringify({ ...event, content: '✓ café' })}\n\n`);
  const source = new ReadableStream({ start(controller) { for (const byte of bytes) controller.enqueue(new Uint8Array([byte])); controller.close(); } });
  const events = [];
  await consumeEvents(source, (value) => events.push(value));
  assert.equal(events[0].content, '✓ café');
});
