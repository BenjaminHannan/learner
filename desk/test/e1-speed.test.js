'use strict';
// Track E1 (2026-11-04): prompt-prefix order, batched Mote tries, change-only intake, and the three new settings (all off).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const AO = require('../src/alwayson');
const Senses = require('../src/senses');
const { MotePool } = require('../src/motepool');
const MB = require('../src/motebatch');
const { DEFAULT_SETTINGS, sanitize } = require('../src/store');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'e1-'));
const at = (h, m) => new Date(2026, 10, 4, h, m || 0).getTime();
const linesOf = (msgs) => msgs.map((m) => m.role + '|' + m.content).join('\n').split('\n').map((l) => l.replace(/^(system|user)\|/, '')).filter(Boolean).sort();

// ---- prefix reuse ----------------------------------------------------------------------------------------------
test('the new loop prompt holds exactly the same lines as the old one (only the order changed)', () => {
  const now = at(14, 5);
  const cases = [
    [[{ t: now - 120000, sense: 'screen', text: 'Maya texted: practice at 5' }], 'No current focus. Last spoke to Ben unprompted: never.', { now }],
    [[{ t: now - 60000, sense: 'windows', text: 'Front app: Safari.' }, { t: null, sense: 'screen', text: 'old' }], 'Current focus: learn "tides". Last spoke to Ben unprompted: 12 min ago.',
      { now, likely: 'Usually at this time: code 62%.', recall: ['(seen 2 h ago) Sam emailed'], patterns: ['Pattern (seen 3×): after Xcode comes Safari'] }],
    [[], 'No current focus.', { now, recall: ['a', 'b'] }]
  ];
  for (const [fresh, summary, extra] of cases) {
    const v1 = AO.buildMessagesV1(fresh, summary, extra), v2 = AO.buildMessages(fresh, summary, extra);
    assert.strictEqual(v2[0].content, v1[0].content, 'system text unchanged');
    // the summary's two sentences were one line in v1 and are two lines in v2: compare sentence by sentence
    const norm = (msgs) => linesOf(msgs).flatMap((l) => l.split(/(?<=\.) (?=Last spoke)/)).sort();
    assert.deepStrictEqual(norm(v2), norm(v1));
    assert.match(v2[1].content, /Answer with the JSON object only\.$/);
  }
});

test('stable parts come first: two ticks a minute apart share everything up to the new observations', () => {
  const sum = (n) => 'Current focus: learn "tides". Last spoke to Ben unprompted: ' + n + ' min ago.';
  const ctx = (now) => ({ now, patterns: ['Pattern (seen 3×): after Xcode comes Safari'] });
  const a = AO.buildMessages([{ t: at(14, 4), sense: 'screen', text: 'one' }], sum(3), ctx(at(14, 5)));
  const b = AO.buildMessages([{ t: at(14, 5), sense: 'screen', text: 'two' }], sum(4), ctx(at(14, 6)));
  const common = (x, y) => { let i = 0; while (i < x.length && x[i] === y[i]) i++; return i; };
  const ta = a.map((m) => m.content).join('\n'), tb = b.map((m) => m.content).join('\n');
  const old = (m) => AO.buildMessagesV1(...m).map((x) => x.content).join('\n');
  const oa = old([[{ t: at(14, 4), sense: 'screen', text: 'one' }], sum(3), ctx(at(14, 5))]), ob = old([[{ t: at(14, 5), sense: 'screen', text: 'two' }], sum(4), ctx(at(14, 6))]);
  assert.ok(common(ta, tb) > common(oa, ob), 'shared prefix grew: ' + common(oa, ob) + ' -> ' + common(ta, tb));
  assert.ok(ta.slice(0, common(ta, tb)).includes('Patterns seen before'), 'patterns are inside the shared prefix');
  assert.deepStrictEqual(AO.splitSummary('No current focus.'), { stable: 'No current focus.', moving: '' });
});

// ---- batching --------------------------------------------------------------------------------------------------
test('makeAskBatch sends the K tries at the same time, try 0 cool and the rest warm; a failed try is an empty slot', async () => {
  let live = 0, peak = 0; const temps = [];
  const askOne = async (m, sig, o) => { live++; peak = Math.max(peak, live); temps.push(o.temperature); await new Promise((r) => setTimeout(r, 20)); live--; if (o.tryIndex === 2) throw new Error('boom'); return 'ok' + o.tryIndex; };
  const batch = MB.makeAskBatch({ askOne });
  const out = await batch([[1], [1], [1], [1]], new AbortController().signal, { tries: true });
  assert.strictEqual(peak, 4, 'all four in flight together');
  assert.deepStrictEqual(out, ['ok0', 'ok1', '', 'ok3']);
  assert.deepStrictEqual(temps.sort(), [0.2, 0.8, 0.8, 0.8]);
});

test('one abort stops the whole batch (Ben typed)', async () => {
  const ctl = new AbortController(); let aborted = 0;
  const askOne = (m, sig) => new Promise((res, rej) => { sig.addEventListener('abort', () => { aborted++; rej(new Error('aborted')); }); });
  const p = MB.makeAskBatch({ askOne })([[1], [1], [1], [1]], ctl.signal, { tries: true });
  setTimeout(() => ctl.abort(), 10);
  await assert.rejects(p);
  assert.strictEqual(aborted, 4);
  await assert.rejects(MB.makeAskBatch({ askOne })([[1]], ctl.signal), /gate/, 'an already-stopped batch never sends');
});

test('streamText reads an SSE reply and sends stream: true', async () => {
  let sent = null;
  const enc = new TextEncoder();
  const chunks = ['data: {"choices":[{"delta":{"content":"{\\"claims\\""}}]}\n\n', 'data: {"choices":[{"delta":{"content":": []}"}}]}\n\ndata: [DONE]\n\n'];
  const fetch = async (url, o) => { sent = JSON.parse(o.body); let i = 0; return { ok: true, body: { getReader: () => ({ read: async () => (i < chunks.length ? { value: enc.encode(chunks[i++]), done: false } : { done: true }) }) } }; };
  const t = await MB.streamText({ fetch, url: 'x', headers: {}, body: { model: 'm', stream: false }, signal: new AbortController().signal });
  assert.strictEqual(t, '{"claims": []}');
  assert.strictEqual(sent.stream, true);
});

function pool(o) {
  const results = [];
  const p = new MotePool({ gate: () => ({ budget: 4 }), prompt: (j) => [{ role: 'user', content: j.topic }], tries: 4, pick: () => 1,
    onResult: (job, r, t, x) => results.push({ job, t, x }), ...o });
  return { p, results };
}
test('MotePool: batching off = tries back-to-back; on = one batch of K per job, and the checker still picks', async () => {
  let asks = 0, batches = 0, on = false;
  const { p, results } = pool({ ask: async () => { asks++; return '{"claims":["a"],"question":null}'; }, askBatch: async (list) => { batches++; return list.map((_, i) => '{"claims":["b' + i + '"],"question":null}'); }, canBatch: () => on });
  p.startBatch([{ kind: 'day', topic: 'x' }]); await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(asks, 4); assert.strictEqual(batches, 0);
  on = true;
  p.startBatch([{ kind: 'day', topic: 'y' }, { kind: 'day', topic: 'z' }]); await new Promise((r) => setTimeout(r, 20));
  assert.strictEqual(batches, 2, 'one K-batch per job (not one try per job)');
  assert.strictEqual(results.length, 3); assert.strictEqual(results[2].x.tries.length, 4); assert.strictEqual(results[2].t, '{"claims":["b1"],"question":null}');
  assert.strictEqual(p.stats.batchedTries, 8);
});

test('MotePool: Ben typing (gate closes) aborts a batch in flight; nothing is delivered', async () => {
  let budget = 4, sig = null;
  const { p, results } = pool({ gate: () => ({ budget, why: budget ? null : 'chat' }), ask: async () => 'x', canBatch: () => true,
    askBatch: (list, signal) => { sig = signal; return new Promise((res, rej) => signal.addEventListener('abort', () => rej(new Error('stopped')))); } });
  p.startBatch([{ kind: 'day', topic: 'x' }]); await new Promise((r) => setTimeout(r, 5));
  budget = 0; p.tick();
  await new Promise((r) => setTimeout(r, 5));
  assert.ok(sig.aborted); assert.strictEqual(results.length, 0); assert.strictEqual(p.count(), 0);
});

// ---- change-only intake ------------------------------------------------------------------------------------------
function rig(o) {
  let now = at(10); const calls = { screen: 0, windows: 0 }; let screenText = 'line a\nline b\nline c', winText = 'Front app: Notes. In Notes: ' + 'x'.repeat(100);
  const state = new Senses.AlwaysOnState(tmp(), { now: () => now });
  const senses = new Senses.Senses({ consent: { ...Senses.defaults(), senses: { ...Senses.defaults().senses, screen: true, windows: o.windows !== false } }, state, now: () => now,
    changeOnly: o.changeOnly, samplers: { screen: async () => { calls.screen++; return screenText; }, windows: async () => { calls.windows++; return winText; } } });
  return { senses, state, calls, tick: (ms) => { now += ms; return senses.sample(); }, setScreen: (t) => { screenText = t; }, setWin: (t) => { winText = t; } };
}
test('change-only off: the old 20 s pace for both senses', async () => {
  const r = rig({ changeOnly: false });
  assert.strictEqual(r.senses.sampleEveryMs(), 20000);
  for (let i = 0; i < 12; i++) await r.tick(5000);
  assert.deepStrictEqual(r.calls, { screen: 3, windows: 3 });
});
test('change-only on: cheap look every 5 s, OCR only on a change or after 60 s; OCR stores the change', async () => {
  const r = rig({ changeOnly: () => true });
  assert.strictEqual(r.senses.sampleEveryMs(), 5000);
  await r.tick(5000); assert.deepStrictEqual(r.calls, { screen: 1, windows: 1 }, 'first look reads both');
  for (let i = 0; i < 5; i++) await r.tick(5000);
  assert.deepStrictEqual(r.calls, { screen: 1, windows: 6 }, 'nothing changed: no OCR');
  r.setWin('Front app: Safari. In Safari: ' + 'y'.repeat(100)); r.setScreen('line a\nline b\nline c\nline d is new');
  await r.tick(5000);
  assert.strictEqual(r.calls.screen, 2, 'a window change triggers OCR at once');
  const last = r.state.inbox.filter((x) => x.sense === 'screen').pop();
  assert.strictEqual(last.text, 'Changed on screen: line d is new');
  for (let i = 0; i < 12; i++) await r.tick(5000);
  assert.strictEqual(r.calls.screen, 3, 'rich accessibility text: a stale check every 60 s');
});
test('change-only on, poor accessibility text (a game, a video): OCR keeps the 20 s pace', async () => {
  const r = rig({ changeOnly: true });
  r.setWin('Front app: Minecraft.');
  for (let i = 0; i < 12; i++) await r.tick(5000);
  assert.strictEqual(r.calls.windows, 12); assert.strictEqual(r.calls.screen, 3);
});
test('change-only on but the windows sense off: never read; screen stays at 20 s', async () => {
  const r = rig({ changeOnly: true, windows: false });
  for (let i = 0; i < 12; i++) await r.tick(5000);
  assert.deepStrictEqual(r.calls, { screen: 3, windows: 0 });
});
test('screenDiff: nothing new = nothing stored; mostly new = the whole screen', () => {
  assert.strictEqual(Senses.screenDiff('a\nb', 'b\na'), '');
  assert.strictEqual(Senses.screenDiff('a\nb\nc', 'x\ny\nc'), 'x\ny\nc');
  assert.strictEqual(Senses.screenDiff(null, 'a\n\nb'), 'a\nb');
});
test('the always-on loop samples at the senses\' pace', () => {
  const timers = [];
  const r = rig({ changeOnly: true });
  const loop = new AO.AlwaysOn({ senses: r.senses, state: r.state, ask: async () => '', setTimer: (fn, ms) => { timers.push(ms); return timers.length; }, clearTimer: () => {} });
  loop.start(); loop.stop();
  assert.ok(timers.includes(5000), 'sample timer ' + timers.join(','));
});

// ---- settings ------------------------------------------------------------------------------------------------
test('the three E1 settings exist, are off by default, and only take booleans', () => {
  for (const k of ['keepBrainInMemory', 'moteBatch', 'senseChangeOnly']) {
    assert.strictEqual(DEFAULT_SETTINGS[k], false, k);
    assert.strictEqual(sanitize({ [k]: true })[k], true);
    assert.notStrictEqual(sanitize({ [k]: 'yes' })[k], 'yes');
  }
});
