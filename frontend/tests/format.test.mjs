import assert from 'node:assert/strict';
import { test } from 'node:test';
import { duration, percent } from '../src/services/format.ts';

test('unknown measurements remain distinct from zero', () => {
  assert.equal(duration(null), '—');
  assert.equal(duration(0), '0 ms');
  assert.equal(percent(null), '—');
  assert.equal(percent(0), '0.0%');
});

test('duration rounding carries seconds into the next minute', () => {
  assert.equal(duration(119_800), '2m 0s');
  assert.equal(duration(61_000), '1m 1s');
});
