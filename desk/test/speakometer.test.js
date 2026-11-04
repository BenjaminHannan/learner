'use strict';
// Always-on v2 phase 2: the speak-o-meter learns when Glim should talk.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const S = require('../src/speakometer');
const { AlwaysOn } = require('../src/alwayson');
const { Senses, AlwaysOnState } = require('../src/senses');

const ctxA = { cat: 'code', act: 'active', minsSinceSay: 60, stuckError: false };

test('starts quiet in ordinary moments, permissive when Ben is stuck, quiet while he types or games', () => {
  const m = new S.SpeakOMeter();
  assert.strictEqual(m.decide(ctxA).speak, false);
  assert.strictEqual(m.decide({ ...ctxA, stuckError: true }).speak, true);
  assert.strictEqual(m.decide({ ...ctxA, stuckError: true, act: 'typing' }).speak, false);
  assert.ok(m.decide({ ...ctxA, stuckPage: true }).p > m.decide(ctxA).p);
});

test('an ordinary moment stays quiet even at its loudest (never spoken, full surprise, code page); stuck or a full share urge speaks', () => {
  const m = new S.SpeakOMeter();
  const loud = { cat: 'code', act: 'active', minsSinceSay: null, urges: { bored: 1, curious: 1, share: 0 }, surprise: 1, stuckError: false, stuckPage: false };
  for (const cat of S.CATS) assert.strictEqual(m.decide({ ...loud, cat }).speak, false, cat);
  assert.strictEqual(m.decide({ ...loud, cat: 'browser', surprise: 0.9 }).speak, false, 'random browsing after start-up (the real-path case)');
  assert.strictEqual(m.decide({ ...loud, stuckError: true }).speak, true);
  assert.strictEqual(m.decide({ ...loud, surprise: 0, minsSinceSay: 30, stuckPage: true }).speak, true);
  assert.strictEqual(m.decide({ ...loud, surprise: 0, urges: { share: 1 } }).speak, true, 'something worth telling, after a long silence');
});

test('the score DROPS after 👎 / "not now" in a context and RISES after 👍', () => {
  const m = new S.SpeakOMeter();
  const ctx = { ...ctxA, stuckError: true };
  const p0 = m.decide(ctx).p;
  m.learn(m.decide(ctx).x, 'down'); const p1 = m.decide(ctx).p;
  assert.ok(p1 < p0, '👎 lowers it: ' + p0 + ' -> ' + p1);
  m.learn(m.decide(ctx).x, 'notnow'); const p2 = m.decide(ctx).p;
  assert.ok(p2 < p1, '"not now" lowers it more: ' + p1 + ' -> ' + p2);
  { const a = new S.SpeakOMeter(), b = new S.SpeakOMeter(); a.learn(a.decide(ctx).x, 'down'); b.learn(b.decide(ctx).x, 'notnow');
    assert.ok(b.decide(ctx).p < a.decide(ctx).p, '"not now" (weight 3) is a stronger no than 👎 (weight 2)'); }
  const q0 = m.decide(ctxA).p;
  m.learn(m.decide(ctxA).x, 'up'); m.learn(m.decide(ctxA).x, 'up');
  assert.ok(m.decide(ctxA).p > q0, '👍 raises it');
  // ignored is a weak no: smaller than a 👎
  const a = new S.SpeakOMeter(), b = new S.SpeakOMeter();
  const pa = a.decide(ctx).p; a.learn(a.decide(ctx).x, 'ignored'); b.learn(b.decide(ctx).x, 'down');
  assert.ok(pa - a.decide(ctx).p < pa - b.decide(ctx).p);
});

test('every event is logged with its features; the nightly refit replays the log from the prior', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'som-'));
  const m = new S.SpeakOMeter({ dir });
  const ctx = { ...ctxA, cat: 'video', act: 'video', urges: { share: 1 } };
  for (let i = 0; i < 6; i++) m.learn(m.decide(ctx).x, 'down');
  const lines = fs.readFileSync(path.join(dir, 'speakometer-events.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.strictEqual(lines.length, 6); assert.strictEqual(lines[0].kind, 'down'); assert.strictEqual(lines[0].x.cat_video, 1);
  const m2 = new S.SpeakOMeter({ dir });   // weights survive a restart
  assert.ok(Math.abs(m2.decide(ctx).p - m.decide(ctx).p) < 1e-9);
  const before = new S.SpeakOMeter().decide(ctx).p;
  const r = m2.refit(); assert.strictEqual(r.events, 6);
  assert.ok(m2.decide(ctx).p < before, 'after the refit video moments are still quieter than the prior');
});

test('categories, activity and the stuck detector (same error 3x, same page 10 min)', () => {
  assert.strictEqual(S.categorize('Google Chrome', 'Lofi beats - YouTube'), 'video');
  assert.strictEqual(S.categorize('Minecraft', ''), 'game');
  assert.strictEqual(S.categorize('Code', 'main.js'), 'code');
  assert.strictEqual(S.categorize('Safari', 'Schoology'), 'school');
  assert.strictEqual(S.activity({ idleS: 1, typing: true, cat: 'code' }), 'typing');
  assert.strictEqual(S.activity({ idleS: 500, cat: 'code' }), 'idle');
  let t = 0; const st = new S.Stuck({ now: () => t });
  for (let i = 0; i < 2; i++) { st.observe('screen', 'npm ERR! TypeError: Cannot read properties of undefined (reading "x") at line 12'); t += 60000; }
  assert.strictEqual(st.error(), null);
  st.observe('screen', 'npm ERR! TypeError: Cannot read properties of undefined (reading "y") at line 40');
  assert.ok(st.error() && st.error().n === 3, 'the same error (numbers/quotes ignored) three times');
  st.observe('windows', 'Front app: Safari. Open: Safari — Khan Academy; Code — main.js.');
  t += 9 * 60000; assert.ok(st.pageMinutes() < 10);
  t += 2 * 60000; st.observe('windows', 'Front app: Safari. Open: Safari — Khan Academy; Code — main.js.');
  assert.ok(st.pageMinutes() >= 10); assert.strictEqual(st.front().title, 'Khan Academy');
});

test('the loop: the meter can hold a say, but never lets one through the code limits', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'som-loop-'));
  const state = new AlwaysOnState(dir);
  const senses = new Senses({ consent: { on: true, senses: { chats: true } }, state });
  let speak = false, busy = false; const said = [];
  const loop = new AlwaysOn({ senses, state, ask: async () => JSON.stringify({ say: 'Hi Ben', note: null, learn: null, why: 'x' }),
    deliver: { say: (t, d) => said.push(d) }, gates: { busy: () => busy }, speakGate: () => ({ speak, p: speak ? 0.9 : 0.1, x: { bias: 1 } }) });
  senses.push('chats', 'one'); await loop.tick();
  assert.strictEqual(said.length, 0); assert.strictEqual(loop.stats.meterHeld, 1);
  speak = true; senses.push('chats', 'two'); await loop.tick();
  assert.strictEqual(said.length, 1); assert.deepStrictEqual(said[0].features, { bias: 1 });
  senses.push('chats', 'three'); await loop.tick();
  assert.strictEqual(said.length, 1, 'the 20-minute limit still holds even when the meter says speak');
  busy = true; senses.push('chats', 'four'); state.lastSpokeAt = 0; await loop.tick();
  assert.strictEqual(said.length, 1, 'Ben first still holds');
});

test('main wires the meter into the loop, outcomes into learn(), and the refit into sleep', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  // the gate goes through the look-ahead wrapper (imagining ahead L1), which still scores with aoMeter on aoContext(...)
  assert.match(m, /speakGate: \(d\) => (?:aoMeter \? aoMeter\.decide\(aoContext\(|aoSpeakAhead\(d\))/);
  if (/speakGate: \(d\) => aoSpeakAhead/.test(m)) assert.match(m, /function aoSpeakAhead\(d\) \{\n  if \(!aoMeter\) return \{ speak: true \};\n  const ctx = aoContext\(/);
  assert.match(m, /aoMeter\.learn\(m\.features, kind/);
  assert.match(m, /aoNightlyJobs = \[\(\) => aoMeter && aoMeter\.refit\(\),/);
  assert.match(m, /helpers\.pauseForSleep\(\);[^\n]*\n  try \{ aoNightly\(\); aoSleepHandoff\(\); \}/);
});
