'use strict';
// HELPER-BG (2026-11-06, docs/helper-bg/MARKS.md): helper requests carry CHAT-FIRST's X-Glim-Background tag, so Ben's chat stops them;
// a stopped helper waits for Ben and retries. H4: a chat request is never tagged background (every request path in desk/).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { streamChat } = require('../src/llm');
const { Agent } = require('../src/agent');

const ROOT = path.join(__dirname, '..');
function sources() {
  const out = [];
  const walk = (d) => {
    for (const f of fs.readdirSync(d, { withFileTypes: true })) {
      if (['node_modules', 'test', 'dist', 'out', '.git'].includes(f.name)) continue;
      const p = path.join(d, f.name);
      if (f.isDirectory()) walk(p); else if (/\.(c|m)?js$/.test(f.name)) out.push(p);
    }
  };
  walk(ROOT); return out;
}
const enc = new TextEncoder();
function fakeFetch(seen, { status = 200, text = '', chunks = [] } = {}) {
  return async (url, o) => {
    seen.push(o.headers);
    if (status !== 200) return { ok: false, status, text: async () => text };
    let i = 0;
    return { ok: true, status, headers: { get: () => 'text/event-stream' }, body: { getReader: () => ({ read: async () => (i < chunks.length ? { value: enc.encode(chunks[i++]), done: false } : { done: true }) }) } };
  };
}
async function withFetch(f, fn) { const saved = globalThis.fetch; globalThis.fetch = f; try { return await fn(); } finally { globalThis.fetch = saved; } }
const base = { gatewayUrl: 'http://127.0.0.1:1/v1', model: 'm', messages: [{ role: 'user', content: 'hi' }], tools: [] };
const DONE = ['data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\n', 'data: [DONE]\n\n'];

test('H4: only llm.js sets the background header, and only agent.js asks for it (helper branch + helper summaries)', () => {
  const hits = [];
  for (const f of sources()) {
    const s = fs.readFileSync(f, 'utf8'), rel = path.relative(ROOT, f);
    if (/x-glim-background/i.test(s)) hits.push(rel + ':header');
    if (/background\s*:\s*(true|background|!!|1\b)/.test(s)) hits.push(rel + ':flag');
  }
  assert.deepStrictEqual(hits.sort(), ['src/agent.js:flag', 'src/llm.js:header']);
  const a = fs.readFileSync(path.join(ROOT, 'src/agent.js'), 'utf8');
  const flags = a.split('\n').filter((l) => /background\s*:\s*(true|background)|await summaryCall\([^)]*,[^)]*,[^)]*,/.test(l));
  for (const l of flags) assert.match(l, /helperId|background: background === true|\{ \.\.\.options, background: true \}/, 'unexpected background use: ' + l.trim());
});

test('H4: a chat (no helperId) goes out untagged; a helper goes out tagged', async () => {
  const sent = [];
  const fake = (o) => ({ o, requestFitted: async (t, s, opts) => { sent.push(opts.background === true); return { content: 'x' }; } });
  await Agent.prototype.requestWithBudget.call(fake({}), {}, {}, { messages: [] });
  await Agent.prototype.requestWithBudget.call(fake({}), {}, {}, { messages: [], background: true });
  await Agent.prototype.requestWithBudget.call(fake({ helperId: 'h1' }), {}, {}, { messages: [] });
  assert.deepStrictEqual(sent, [false, false, true]);
  const seen = [];
  await withFetch(fakeFetch(seen, { chunks: DONE }), async () => {
    await streamChat({ ...base });
    await streamChat({ ...base, background: true });
  });
  assert.strictEqual(seen[0]['x-glim-background'], undefined);
  assert.strictEqual(seen[0]['x-test'], undefined);
  assert.strictEqual(seen[1]['x-glim-background'], '1');
  assert.strictEqual(seen[1]['x-test'], undefined, 'helpers are not test traffic: the diary keeps them');
});

test('a background request stopped or refused for Ben comes back as a yielded error, never as an empty answer', async () => {
  const seen = [];
  await withFetch(fakeFetch(seen, { status: 404, text: '{"error":"stopped: Ben\'s chat goes first"}' }), async () => {
    await assert.rejects(streamChat({ ...base, background: true }), (e) => e.yielded === true);
  });
  await withFetch(fakeFetch(seen, { status: 503, text: 'held' }), async () => {
    await assert.rejects(streamChat({ ...base, background: true }), (e) => e.yielded === true);
    await assert.rejects(streamChat({ ...base }), (e) => !e.yielded);   // a chat's 503 is a normal error
  });
  await withFetch(fakeFetch(seen, { chunks: [] }), async () => {   // connection closed mid-stream with nothing said
    await assert.rejects(streamChat({ ...base, background: true }), (e) => e.yielded === true);
    const r = await streamChat({ ...base });
    assert.strictEqual(r.content, '');
  });
});

test('a yielded helper waits for Ben, then retries (bounded); other errors are not retried', async () => {
  let calls = 0, busy = true;
  const self = {
    o: { helperId: 'h', benBusy: () => busy },
    requestFitted: async () => { calls++; if (calls === 1) { setTimeout(() => { busy = false; }, 50); throw Object.assign(new Error('y'), { yielded: true }); } return { content: 'done' }; },
  };
  const r = await Agent.prototype.requestWithBudget.call(self, {}, {}, { messages: [] });
  assert.strictEqual(r.content, 'done');
  assert.strictEqual(calls, 2);
  let n = 0;
  const bad = { o: { helperId: 'h' }, requestFitted: async () => { n++; throw new Error('boom'); } };
  await assert.rejects(Agent.prototype.requestWithBudget.call(bad, {}, {}, { messages: [] }), /boom/);
  assert.strictEqual(n, 1);
});

test('a partial helper stream and a streamed chat-first error are retried, not saved as finished work', async () => {
  const seen = [];
  for (const chunks of [
    ['data: {"choices":[{"delta":{"content":"unfinished"},"finish_reason":null}]}\n\n'],
    ['data: {"error":{"message":"stopped: Ben\'s chat goes first"}}\n\n'],
  ]) {
    await withFetch(fakeFetch(seen, { chunks }), async () => {
      await assert.rejects(streamChat({ ...base, background: true }), (error) => error.yielded === true);
    });
  }
});

test('step 2: helper requests take turns on the local brain (1 in flight, FIFO, nobody starves); waiting for Ben holds no slot', async () => {
  const { Limiter } = require('../src/helpers');
  const brain = new Limiter(() => 1);
  let inFlight = 0, peak = 0; const order = [];
  const mk = (id) => ({ o: { helperId: id, brainSlot: brain },
    requestFitted: async () => { inFlight++; peak = Math.max(peak, inFlight); order.push(id); await new Promise((r) => setTimeout(r, 20)); inFlight--; return { content: id }; } });
  const runs = ['a', 'b', 'c', 'd'].map((id) => Agent.prototype.requestWithBudget.call(mk(id), {}, {}, { messages: [] }));
  assert.deepStrictEqual((await Promise.all(runs)).map((r) => r.content), ['a', 'b', 'c', 'd']);
  assert.strictEqual(peak, 1);
  assert.deepStrictEqual(order, ['a', 'b', 'c', 'd']);
  let busy = true, n = 0;
  const y = { o: { helperId: 'y', brainSlot: brain, benBusy: () => busy },
    requestFitted: async () => { n++; if (n === 1) throw Object.assign(new Error('y'), { yielded: true }); return { content: 'y' }; } };
  const py = Agent.prototype.requestWithBudget.call(y, {}, {}, { messages: [] });
  await new Promise((r) => setTimeout(r, 50));
  assert.strictEqual(brain.active, 0, 'no slot held while waiting for Ben');
  const other = await Agent.prototype.requestWithBudget.call(mk('z'), {}, {}, { messages: [] });
  assert.strictEqual(other.content, 'z');
  busy = false;
  assert.strictEqual((await py).content, 'y');
  const chat = { o: { brainSlot: brain }, requestFitted: async () => ({ content: 'chat', active: brain.active }) };
  const hold = await brain.acquire();
  const r = await Agent.prototype.requestWithBudget.call(chat, {}, {}, { messages: [] });
  hold(); assert.strictEqual(r.content, 'chat');
});

test('step 2 wiring: main.js gives helpers (only) the one-at-a-time brain slot on a local gateway', () => {
  const m = fs.readFileSync(path.join(ROOT, 'main.js'), 'utf8');
  assert.match(m, /brainSlot: isHelper \? helperBrain : null/);
  assert.ok(m.includes('helperBrain = new Limiter(() => (hasLocalAssistant && /^https?:\\/\\/(127\\.0\\.0\\.1|localhost)[:/]/.test(String(store.getSettings().gatewayUrl || \'\')) ? 1 : 0))'));
});

test('helper summaries share the brain slot; chat summaries stay untagged', async () => {
  const { Limiter } = require('../src/helpers');
  const brain = new Limiter(1);
  const release = await brain.acquire();
  const settings = { gatewayUrl: base.gatewayUrl, model: 'm' };
  const thread = () => ({ messages: [{ role: 'user', content: 'Remember that school starts at nine.' }], ctxFrom: 1 });
  const helper = new Agent({ helperId: 'h', brainSlot: brain, getSettings: () => settings, toolDefs: [], tools: {} });
  const chat = new Agent({ getSettings: () => settings, toolDefs: [], tools: {} });
  const seen = [];
  await withFetch(fakeFetch(seen, { chunks: DONE }), async () => {
    const pending = helper.summarizeLeftOut(thread(), settings, null, 0);
    await new Promise((resolve) => setImmediate(resolve));
    assert.strictEqual(seen.length, 0);
    await chat.summarizeLeftOut(thread(), settings, null, 0);
    assert.strictEqual(seen[0]['x-glim-background'], undefined);
    release();
    await pending;
    assert.strictEqual(seen[1]['x-glim-background'], '1');
    assert.strictEqual(seen[1]['x-test'], undefined);
  });
  assert.strictEqual(brain.active, 0);
});

test('cancelled queued helpers never send; failed helpers release the brain', async () => {
  const { Limiter } = require('../src/helpers');
  const brain = new Limiter(1);
  const release = await brain.acquire();
  const controller = new AbortController();
  let calls = 0;
  const helper = { o: { helperId: 'h', brainSlot: brain }, requestFitted: async () => { calls++; throw new Error('broken'); } };
  const pending = Agent.prototype.requestWithBudget.call(helper, {}, {}, { signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, /aborted/);
  assert.strictEqual(calls, 0);
  release();
  await assert.rejects(Agent.prototype.requestWithBudget.call(helper, {}, {}, {}), /broken/);
  assert.strictEqual(brain.active, 0);
  assert.strictEqual(brain.q.length, 0);
});
