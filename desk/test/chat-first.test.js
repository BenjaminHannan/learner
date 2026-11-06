'use strict';
// CHAT-FIRST (2026-11-05, docs/chat-first/MARKS.md U1-U3): background asks give way to Ben's chat, are streamed (abortable on the
// server), and a tick carries a picture only on a meaningful screen change. Fakes only: no model, no Python.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const AoAsk = require('../src/aoask');
const Eyes = require('../src/eyes');
const SenseSleep = require('../src/sense-sleep');

const sse = (parts) => parts.map((t) => 'data: ' + JSON.stringify({ choices: [{ delta: { content: t } }] }) + '\n\n').join('') + 'data: [DONE]\n\n';
function fakeFetch(o = {}) {
  const f = async (url, init) => {
    f.calls.push({ url, body: JSON.parse(init.body), signal: init.signal });
    if (o.hang) return new Promise((res, rej) => init.signal.addEventListener('abort', () => rej(Object.assign(new Error('aborted'), { name: 'AbortError' }))));
    return { ok: true, text: async () => sse(o.parts || ['hel', 'lo']) };
  };
  f.calls = []; return f;
}
const mkAsk = (held, fetch) => AoAsk.makeAsk({ settings: () => ({ gatewayUrl: 'http://x:8090/v1' }), model: () => 'qwen36-fast', url: () => 'http://x:8090/v1/chat/completions', held, fetch });

test('U1: chat in flight or < 120 s since Ben\'s last message holds the ask (no network call); at 121 s it asks', async () => {
  let t = 1e12, running = false, last = 0;
  const held = () => AoAsk.chatHeld({ chatRunning: () => running, lastChatAt: () => last }, t);
  const f = fakeFetch(); const ask = mkAsk(held, f); const sig = new AbortController().signal;
  running = true; await assert.rejects(ask([{ role: 'user', content: 'x' }], sig), (e) => e.gate && e.held === 'chat');
  running = false; last = t; t += 119000; await assert.rejects(ask([{ role: 'user', content: 'x' }], sig), (e) => e.gate && e.held === 'chat-hold');
  assert.strictEqual(f.calls.length, 0);
  t += 2000; assert.strictEqual(await ask([{ role: 'user', content: 'x' }], sig), 'hello');
  assert.strictEqual(f.calls.length, 1);
  assert.strictEqual(AoAsk.chatHeld({ chatRunning: () => false, lastChatAt: () => 0 }, t), null, 'no chat yet: free');
});

test('U2: every ask is streamed, keeps the caller\'s max tokens, joins the text; aborting it aborts the fetch', async () => {
  const f = fakeFetch({ parts: ['{"say"', ': null}'] }); const ask = mkAsk(() => null, f);
  assert.strictEqual(await ask([{ role: 'user', content: 'x' }], new AbortController().signal, { maxTokens: 120 }), '{"say": null}');
  assert.strictEqual(f.calls[0].body.stream, true); assert.strictEqual(f.calls[0].body.max_tokens, 120);
  const h = fakeFetch({ hang: true }); const ask2 = mkAsk(() => null, h); const ctl = new AbortController();
  const p = ask2([{ role: 'user', content: 'x' }], ctl.signal); await new Promise((r) => setImmediate(r));
  ctl.abort(); await assert.rejects(p); assert.ok(h.calls[0].signal.aborted, 'the request to the gateway is closed');
});

test('U2b: main.js routes every always-on ask (tick, Motes, checks, quiz) through the one streamed, held door', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.ok(/async function aoAsk\(messages, signal, opts\) \{ return aoAskDoor\(/.test(src));
  assert.ok(/async function aoAskStream\(messages, signal, opts\) \{ return aoAskDoor\(/.test(src));
  assert.ok(/const aoBusy = \(\) => !!aoChatHeld\(\) \|\|/.test(src), 'the loop and the Mote gate see the hold too');
  assert.ok(/lastChatAt = Date\.now\(\);   \/\/ CHAT-FIRST A1/.test(src), 'a chat message starts the hold');
  assert.ok(/aoEyesObj\.tickPart\(\)/.test(src), 'ticks use the meaningful-change picture');
  assert.ok(!/stream: false, maxTokens: \(opts && opts\.maxTokens\) \|\| 220/.test(src), 'no non-streamed always-on ask left');
});

// eyes fakes: each encode returns the vector the test queues
const base = () => { const a = new Float32Array(64 * 768); for (let i = 0; i < a.length; i++) a[i] = Math.sin(i * 0.37); return a; };
const seedV = (k) => { const a = new Float32Array(64 * 768); for (let i = 0; i < a.length; i++) a[i] = Math.sin(i * 0.37 + k * 1.7); return a; };
const nudge = (a, k) => { const b = Float32Array.from(a); for (let i = 0; i < b.length; i += 97) b[i] += k; return b; };
function mkEyes() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'chat-first-'));
  let t = Date.parse('2026-11-05T12:00:00Z'); const q = [];
  const worker = { async encode() { return { ok: true, eye: Eyes.EYE_ID, shape: [64, 768], f16: SenseSleep.encodeF16(q.shift()).toString('base64'), ms: 5 }; }, stop() {} };
  const eyes = new Eyes.Eyes({ userData: dir, worker, platform: 'darwin', now: () => t, on: () => true, keepEvidence: () => false, shot: async () => Buffer.from([0xff, 0xd8, 1]) });
  const frame = async (v, ms = Eyes.CLIP_EVERY_MS) => { q.push(v); eyes.lastTickAt = 0; await eyes.clipTick('s', ''); t += ms; };
  return { eyes, frame, adv: (ms) => { t += ms; } };
}

test('U3: a tick sends a picture only on a meaningful change; a second clip within 180 s is at most a single picture', async () => {
  const { eyes, frame, adv } = mkEyes();
  const a = base();
  const S = Eyes.CLIP_STILL_MS;   // a still screen is sampled every 10 s
  await frame(a, S); assert.ok(eyes.tickPart(), 'first frame: sent');
  await frame(a, S); assert.strictEqual(eyes.tickPart(), null, 'still screen: nothing');
  const small = nudge(a, 0.05); assert.ok(Eyes.cosine(a, small) >= Eyes.SEND_COS);
  await frame(small, S); assert.strictEqual(eyes.tickPart(), null, 'small change: nothing');
  // a moving screen: frames that differ a lot -> one clip
  let k = 1; for (let i = 0; i < 4; i++) await frame(seedV(k++));
  const c1 = eyes.tickPart(); assert.ok(c1 && c1.image_features.clip, 'big change: a clip');
  for (let i = 0; i < 4; i++) await frame(seedV(k++));
  const c2 = eyes.tickPart(); assert.ok(c2 && !c2.image_features.clip && c2.image_features.shape[0] === 64, 'within 180 s: one picture, not a clip');
  adv(Eyes.CLIP_GAP_MS);
  for (let i = 0; i < 4; i++) await frame(seedV(k++));
  assert.ok(eyes.tickPart().image_features.clip, 'after 180 s a moving screen is a clip again');
  assert.strictEqual(eyes.tickPart(), null, 'never the same frame twice');
});
