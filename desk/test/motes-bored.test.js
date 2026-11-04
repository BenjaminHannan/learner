'use strict';
// Always-on v2 phase 4: urges, the memory gauge and bored-mode Motes.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const U = require('../src/urges');
const M = require('../src/memgauge');
const { MotePool, parseThought } = require('../src/motepool');

test('urges: bored fills over a quiet half hour, drains when Ben chats; curious follows the wonder list; share fades', () => {
  let t = 0; const u = new U.Urges({ now: () => t });
  for (let i = 0; i < 20; i++) { t += 60000; u.tick({ fresh: false, chatting: false, wonder: 0 }); }
  assert.ok(u.bored > 0.6 && u.isBored());
  t += 60000; u.tick({ chatting: true }); assert.ok(u.bored < 0.6 + 0.0001);
  for (let i = 0; i < 5; i++) { t += 60000; u.tick({ chatting: true }); }
  assert.strictEqual(u.isBored(), false);
  u.tick({ wonder: 4 }); assert.ok(u.curious >= 0.6);
  u.worthTelling(); const s0 = u.share; t += 3600000; u.tick({}); assert.ok(u.share < s0);
  u.spoke(); assert.strictEqual(u.share, 0);
  const u2 = new U.Urges({ saved: u.view() }); assert.strictEqual(u2.curious, u.view().curious);
});

test('topic choice: Learn topics, then his day, then the wonder list; recently studied topics are skipped', () => {
  const now = 1e7;
  const src = { learn: ['black holes'], day: ['the npm error'], wonder: ['why is the sky blue'], recent: {} };
  assert.deepStrictEqual(U.chooseTopics(src, 3, now).map((x) => x.kind), ['learn', 'day', 'wonder']);
  assert.deepStrictEqual(U.chooseTopics(src, 1, now).map((x) => x.topic), ['black holes']);
  assert.deepStrictEqual(U.chooseTopics({ ...src, recent: { 'black holes': now - 60000 } }, 1, now).map((x) => x.topic), ['the npm error']);
});

test('memory gauge: green/yellow/red from pressure and swap growth; budget per the design', () => {
  assert.strictEqual(M.gauge({ pressure: 1 }), 'green');
  assert.strictEqual(M.gauge({ pressure: 2 }), 'yellow');
  assert.strictEqual(M.gauge({ pressure: 4 }), 'red');
  assert.strictEqual(M.gauge({ pressure: 1, swapGrowMB: 400 }), 'red');
  assert.strictEqual(M.budget({ gauge: 'green', away: true, onAC: true }), M.FULL_BATCH);
  assert.strictEqual(M.budget({ gauge: 'green', away: false, onAC: true }), 2);
  assert.strictEqual(M.budget({ gauge: 'green', away: true, onAC: false }), 2);
  assert.strictEqual(M.budget({ gauge: 'yellow', away: true }), 1);
  assert.strictEqual(M.budget({ gauge: 'yellow', away: false }), 0);
  assert.strictEqual(M.budget({ gauge: 'red', away: true, onAC: true }), 0);
  assert.strictEqual(M.budget({ gauge: 'green', away: true, onAC: true, chatting: true }), 0);
  assert.strictEqual(M.parseSwap('total = 2048.00M  used = 1234.50M  free = 813.50M  (encrypted)'), 1234.5);
  assert.strictEqual(M.parseSwap('total = 4.00G  used = 1.50G  free = 2.50G'), 1536);
  let swap = 1000, t = 0; const g = new M.MemGauge({ now: () => t, pressure: () => 1, swapMB: () => swap });
  assert.strictEqual(g.read().level, 'green');
  swap = 1500; t += 30000; assert.strictEqual(g.read().level, 'red', 'swap growing');
  t += 30000; assert.strictEqual(g.read().level, 'green', 'steady swap is fine again');
});

// a fake model that answers only when told to (so a request can be "in flight")
function rig() {
  const st = { budget: 4, why: null }; const pending = []; const results = []; const asked = [];
  const pool = new MotePool({
    gate: () => ({ budget: st.budget, why: st.why }),
    prompt: (job) => [{ role: 'user', content: 'Topic: ' + job.topic }],
    ask: (messages, signal) => new Promise((res, rej) => { asked.push(messages); pending.push({ res, signal }); signal.addEventListener('abort', () => rej(new Error('aborted'))); }),
    onResult: (job, r) => results.push({ job, r })
  });
  const answer = async (text) => { const p = pending.shift(); p.res(text); await new Promise((r) => setImmediate(r)); await new Promise((r) => setImmediate(r)); };
  return { st, pool, pending, results, asked, answer };
}
const topics = (n) => Array.from({ length: n }, (_, i) => ({ kind: 'learn', topic: 'topic ' + i }));

test('a batch runs back-to-back (one request at a time: the local server is serial) up to the budget', async () => {
  const r = rig(); r.st.budget = 2;
  assert.strictEqual(r.pool.startBatch(topics(5)), 2, 'trimmed to the budget');
  assert.strictEqual(r.pending.length, 1, 'one request in flight at a time');
  await r.answer('{"claims": ["A black hole has an event horizon."], "question": "What is Hawking radiation?"}');
  assert.strictEqual(r.results.length, 1); assert.deepStrictEqual(r.results[0].r.claims, ['A black hole has an event horizon.']);
  assert.strictEqual(r.pending.length, 1, 'the next Mote starts after the first finishes');
  await r.answer('not json'); assert.strictEqual(r.results[1].r, null);
  assert.strictEqual(r.pool.count(), 0);
});

test('Motes stop within one tick when a chat starts (stopAll and tick both abort the request in flight)', async () => {
  const r = rig();
  r.pool.startBatch(topics(4)); assert.strictEqual(r.pool.count(), 4);
  r.st.budget = 0; r.st.why = 'chat';   // Ben started a chat: the gate now says 0
  const t = r.pool.tick();
  assert.ok(t.stopped); assert.strictEqual(r.pool.count(), 0);
  assert.ok(r.pending[0].signal.aborted, 'the request in flight was aborted');
  await new Promise((res) => setImmediate(res));
  assert.strictEqual(r.results.length, 0, 'an aborted Mote delivers nothing');
  assert.strictEqual(r.pool.lastStop, 'chat');
  // main also calls stopAll('chat') directly when Ben sends (no wait for the tick)
  const r2 = rig(); r2.pool.startBatch(topics(3)); r2.pool.stopAll('chat');
  assert.strictEqual(r2.pool.count(), 0); assert.ok(r2.pending[0].signal.aborted);
});

test('Motes stop within one tick under 🔴, and a 🟡 budget trims the batch to one', async () => {
  const r = rig(); r.pool.startBatch(topics(4));
  r.st.budget = 1; r.pool.tick(); assert.strictEqual(r.pool.count(), 1, '🟡: one Mote left (the one in flight)');
  r.st.budget = M.budget({ gauge: M.gauge({ pressure: 4 }), away: true, onAC: true }); r.st.why = 'memory';
  r.pool.tick(); assert.strictEqual(r.pool.count(), 0); assert.ok(r.pending[0].signal.aborted);
  assert.strictEqual(r.pool.startBatch(topics(2)), 0, 'nothing starts under 🔴');
});

test('a gate that closes between two Motes stops the rest before the next request', async () => {
  const r = rig(); r.pool.startBatch(topics(3));
  r.st.budget = 0; r.st.why = 'chat';
  await r.answer('{"claims": [], "question": null}');
  assert.strictEqual(r.pending.length, 0, 'no second request'); assert.strictEqual(r.pool.count(), 0);
});

test('parseThought keeps at most 5 claims and drops junk', () => {
  assert.deepStrictEqual(parseThought('<think>x</think>{"claims": ["a", 3, "", "b"], "question": " q "}'), { claims: ['a', 'b'], question: 'q' });
  assert.strictEqual(parseThought('nope'), null);
});

test('main: chat and typing stop every Mote at once; the gate uses Ben first, sleep, night and the gauge; 🔴 pauses Learn Motes', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /if \(aoLoop\) aoLoop\.cancel\('chat'\); aoPool\.stopAll\('chat'\);/);
  assert.match(m, /aoPool\.stopAll\('typing'\)/);
  const gate = m.slice(m.indexOf('function aoMoteGate()'), m.indexOf('const MOTE_SYSTEM'));
  assert.match(gate, /if \(aoBusy\(\)\) return \{ budget: 0, why: 'chat' \}/);
  assert.match(gate, /sl\.asleep \|\| sl\.waking/);
  assert.match(gate, /GaugeMod\.budget\(/);
  assert.match(m, /try \{ aoPool\.tick\(\); \}/);
  assert.match(m, /helpers\.pauseForSleep\('Paused: the Mac is short on memory'\)/);
  assert.match(m, /ask: \(m, sig\) => aoAsk\(m, sig, \{ maxTokens: 350 \}\)/, 'Motes ask chat\'s model through aoAsk');
});
