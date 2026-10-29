'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { waitForReady } = require('../renderer/sleepwake');
const { Warmer } = require('../src/warm');
const completion = JSON.stringify({ choices: [{ message: { role: 'assistant', content: '.' } }] });

test('wake waits for a stopped trainer AND a ready model', async () => {
  const states = [{ asleep: true }, { waking: true }, { modelReady: false }, { modelReady: true }];
  let reads = 0, clock = 0;
  await waitForReady({ wake: async () => ({ ok: true }), state: async () => states[reads++],
    now: () => clock, wait: async (ms) => { clock += ms; }, timeoutMs: 1000, pollMs: 10 });
  assert.equal(reads, 4);
});
test('wake errors stop immediately without waiting for a state transition', async () => {
  await assert.rejects(waitForReady({ wake: async () => ({ error: 'wake failed' }),
    state: async () => { throw new Error('must not read'); } }), /wake failed/);
  await assert.rejects(waitForReady({ wake: async () => ({ ok: true }),
    state: async () => ({ modelReady: false, error: 'model did not start' }) }), /model did not start/);
});
test('a stopped trainer with an unavailable model has a bounded wait', async () => {
  let clock = 0;
  await assert.rejects(waitForReady({ wake: async () => ({ ok: true }), state: async () => ({ modelReady: false }),
    now: () => clock, wait: async (ms) => { clock += ms; }, timeoutMs: 25, pollMs: 10 }), /took too long/);
});
test('an IPC request that never resolves also times out', async () => {
  await assert.rejects(waitForReady({ wake: () => new Promise(() => {}), state: async () => ({}), timeoutMs: 10 }), /took too long/);
});
test('a reachable gateway with failed chat requests is never announced ready', async () => {
  let allowChat = false;
  const states = [];
  const w = new Warmer({ getSettings: () => ({ gatewayUrl: 'http://test/v1' }), getTools: () => [],
    onState: (s) => states.push(s), downMs: 1000,
    fetch: async (_, options) => ({ ok: !options || allowChat, text: async () => completion }) });
  w.stopped = false;
  await w._tick(); w.stop();
  assert.equal(w.state, 'down'); assert.equal(states.includes('ready'), false);
  allowChat = true; w.stopped = false;
  await w._tick(); w.stop();
  assert.equal(w.state, 'ready');
  w.gatewayMoved(); assert.equal(w.state, 'down', 'old readiness is invalid after a gateway restart');
});
test('a warm response from an old gateway cannot make a new gateway ready', async () => {
  let release;
  const states = [];
  const w = new Warmer({ getSettings: () => ({ gatewayUrl: 'http://test/v1' }), getTools: () => [],
    onState: (s) => states.push(s), fetch: async (_, options) => !options ? { ok: true } :
      new Promise((r) => { release = () => r({ ok: true, text: async () => completion }); }) });
  w.stopped = false;
  const ticking = w._tick();
  while (!release) await new Promise((r) => setImmediate(r));
  w.gatewayMoved(); w.stop(); release(); await ticking;
  assert.equal(w.state, 'down'); assert.equal(w.warmCount, 0); assert.equal(states.includes('ready'), false);
});
test('a model setting change invalidates an in-flight warm before the old model replies', async () => {
  let settings = { gatewayUrl: 'http://test/v1', modelFast: 'old-model' }, release;
  const states = [], requests = [];
  const w = new Warmer({ getSettings: () => settings, getTools: () => [],
    onState: (s) => states.push(s), fetch: async (_, options) => {
      if (!options || !options.method) return { ok: true };
      requests.push(JSON.parse(options.body).model);
      return new Promise((resolve) => { release = () => resolve({ ok: true, text: async () => completion }); });
    } });
  w.stopped = false;
  const ticking = w._tick();
  while (!release) await new Promise((resolve) => setImmediate(resolve));
  settings = { ...settings, modelFast: 'new-model' };
  w.rewarm();
  assert.equal(w.state, 'down');
  release(); await ticking; w.stop();
  assert.deepEqual(requests, ['old-model']);
  assert.equal(w.state, 'down');
  assert.equal(w.warmCount, 0);
  assert.equal(states.includes('ready'), false);
});
test('HTTP success with an error or malformed chat body does not count as model readiness', async () => {
  for (const body of ['{"error":{"message":"model is loading"}}', '{"choices":[]}', 'not JSON', '']) {
    const states = [];
    const w = new Warmer({ getSettings: () => ({ gatewayUrl: 'http://test/v1' }), getTools: () => [],
      onState: (s) => states.push(s), fetch: async () => ({ ok: true, text: async () => body }) });
    w.stopped = false;
    await w._tick(); w.stop();
    assert.equal(w.state, 'down'); assert.equal(w.warmCount, 0); assert.equal(states.includes('ready'), false);
  }
});
