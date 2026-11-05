'use strict';
// vid-in (2026-11-05): the eyes' clip ring (src/eyes.js clipTick / clipPart / seePart) and the chat hook (src/llm.js setRequestHook).
// Fakes only: no Python, no screenshot, no model.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const Eyes = require('../src/eyes');
const SenseSleep = require('../src/sense-sleep');
const SensesMod = require('../src/senses');

const JPEG = Buffer.concat([Buffer.from([0xff, 0xd8, 0xff, 0xe0]), Buffer.alloc(1000, 7)]);
const vec = (seed) => { const a = new Float32Array(64 * 768); for (let i = 0; i < a.length; i++) a[i] = Math.sin(i * 0.37 + seed * 1.7); return SenseSleep.encodeF16(a).toString('base64'); };
function mk(o = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'eyes-clip-'));
  let t = Date.parse('2026-11-05T12:00:00Z'), seed = 0;
  const worker = { calls: 0, async encode() { this.calls++; return { ok: true, eye: Eyes.EYE_ID, shape: [64, 768], f16: vec(o.still ? 0 : seed++), ms: 20 }; }, stop() {} };
  const shots = [];
  const eyes = new Eyes.Eyes({ userData: dir, worker, isPrivate: SensesMod.isPrivate, platform: 'darwin', now: () => t,
    on: () => o.on !== false, keepEvidence: () => false, shot: async () => { shots.push(1); return JPEG; } });
  return { dir, eyes, worker, shots, adv: (ms) => { t += ms; } };
}

test('a moving screen becomes ONE clip part (frames in order, times from the first frame); nothing is stored', async () => {
  const { eyes, dir, adv } = mk();
  for (let i = 0; i < 4; i++) { await eyes.clipTick('a video', 'Front app: QuickTime Player.'); adv(Eyes.CLIP_EVERY_MS); }
  const part = eyes.seePart(false);
  const x = part.image_features;
  assert.strictEqual(part.type, 'image_features');
  assert.deepStrictEqual(x.shape, [4 * 64, 768]);
  assert.deepStrictEqual(x.clip.times, [0, 3, 5, 8]);   // 2.5 s apart, rounded
  assert.strictEqual(x.clip.frames, 4);
  assert.strictEqual(Buffer.from(x.f16, 'base64').length, 4 * 64 * 768 * 2);
  assert.ok(Buffer.from(x.f16, 'base64').subarray(0, 64 * 768 * 2).equals(Buffer.from(eyes.ring[0].f16, 'base64')), 'oldest frame first');
  assert.ok(!fs.existsSync(path.join(dir, 'sense-sleep')), 'clip frames are memory only');
  assert.ok(Eyes.labelFor(part).includes('last 8 seconds'));
  // once=true: sent once; a new frame makes a new clip
  assert.ok(eyes.clipPart(true)); assert.strictEqual(eyes.clipPart(true), null);
  await eyes.clipTick('a video', ''); assert.ok(eyes.clipPart(true));
});

test('at most 8 frames, only the last 20 s, and a still screen stays a single picture (image projector)', async () => {
  const { eyes, adv } = mk();
  for (let i = 0; i < 12; i++) { await eyes.clipTick('v', ''); adv(Eyes.CLIP_EVERY_MS); }
  assert.strictEqual(eyes.seePart(false).image_features.clip.frames, 8);
  adv(Eyes.CLIP_WINDOW_MS + 1);
  assert.strictEqual(eyes.clipPart(false), null, 'old frames age out');
  const still = mk({ still: true });
  for (let i = 0; i < 5; i++) { await still.eyes.clipTick('doc', ''); still.adv(Eyes.CLIP_STILL_MS); }
  const p = still.eyes.seePart(false);
  assert.ok(p && !p.image_features.clip && p.image_features.shape[0] === 64, 'still screen: one picture');
});

test('still screens slow the ticker; private windows clear the ring and take no picture; off = nothing', async () => {
  const s = mk({ still: true });
  await s.eyes.clipTick('doc', ''); s.adv(Eyes.CLIP_EVERY_MS); await s.eyes.clipTick('doc', ''); s.adv(Eyes.CLIP_EVERY_MS);
  const n = s.shots.length; await s.eyes.clipTick('doc', '');
  assert.strictEqual(s.shots.length, n, 'still: waits CLIP_STILL_MS');
  const m = mk();
  for (let i = 0; i < 3; i++) { await m.eyes.clipTick('v', ''); m.adv(Eyes.CLIP_EVERY_MS); }
  const shots = m.shots.length;
  assert.deepStrictEqual(await m.eyes.clipTick('v', 'Front app: Safari. Open: Safari — Private Browsing.'), { skipped: 'private' });
  assert.strictEqual(m.shots.length, shots); assert.strictEqual(m.eyes.ring.length, 0); assert.strictEqual(m.eyes.seePart(false), null);
  const off = mk({ on: false });
  assert.strictEqual(await off.eyes.clipTick('v', ''), null); assert.strictEqual(off.shots.length, 0);
});

test('wantsSight: questions about the screen or a video', () => {
  for (const q of ['what happened in the last few seconds of this video?', 'What is on my screen?', 'can you see this', 'what am I watching'])
    assert.ok(Eyes.wantsSight(q), q);
  for (const q of ['write me a poem about cats', 'what is 2+2', 'remind me tomorrow']) assert.ok(!Eyes.wantsSight(q), q);
});

test('llm request hook: changes the sent messages only, and a throwing hook never breaks the chat', async () => {
  const llm = require('../src/llm');
  const http = require('http');
  let body = null;
  const srv = http.createServer((req, res) => { let b = ''; req.on('data', (c) => { b += c; }); req.on('end', () => { body = JSON.parse(b); res.writeHead(200, { 'content-type': 'text/event-stream' }); res.end('data: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'); }); });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const url = 'http://127.0.0.1:' + srv.address().port;
  try {
    const msgs = [{ role: 'user', content: 'what happened in this video?' }];
    llm.setRequestHook((m) => Eyes.withFrame(m, { type: 'image_features', image_features: { f16: 'AA==', shape: [128, 768], clip: { frames: 2, times: [0, 2] } } }, 'Clip:'));
    await llm.streamChat({ gatewayUrl: url, model: 'm', messages: msgs, tools: [] });
    assert.strictEqual(body.messages[0].content[1].type, 'image_features');
    assert.strictEqual(typeof msgs[0].content, 'string', 'the caller\'s messages are unchanged');
    llm.setRequestHook(() => { throw new Error('boom'); });
    await llm.streamChat({ gatewayUrl: url, model: 'm', messages: msgs, tools: [] });
    assert.strictEqual(body.messages[0].content, 'what happened in this video?');
  } finally { llm.setRequestHook(null); srv.close(); }
});
