'use strict';
// The study keeper (SWITCH-ON 2026-11-05): Ben's rule "it should always be doing something".
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'); const os = require('os'); const path = require('path');
const K = require('../src/studykeeper');

function rig(o) {
  o = o || {};
  const clock = { t: 1e9 }, w = { free: { ok: true }, cur: o.cur || null, running: new Set(), ran: [], started: [], stopped: 0, quiz: o.quiz || null, cands: o.cands || [], ben: o.ben || [] };
  const k = new K.StudyKeeper({ dir: fs.mkdtempSync(path.join(os.tmpdir(), 'sk-')), now: () => clock.t, free: () => w.free,
    study: { cur: () => w.cur, start: (topic) => { w.started.push(topic); w.cur = { topic, ids: ['a', 'b', 'c'], by: 'glim' }; return { ok: true }; }, stop: () => { w.stopped++; w.cur = null; } },
    isRunning: (ids) => ids.some((id) => w.running.has(id)), runNext: (ids, turn) => { const id = ids[turn % ids.length]; w.ran.push(id); w.running.add(id); return true; },
    quiz: () => w.quiz, examDue: () => { w.exam = (w.exam || 0) + 1; }, candidates: () => w.cands, benWords: () => w.ben });
  return { k, w, clock, tick: (ms) => { clock.t += ms || K.KICK_GAP_MS; } };
}
const BEN = K.words('Ben AP Chemistry lab report gas stoichiometry Mr Phipps; T3 Code beautiful-model video projector training sleep; schoolwork');

test('nothing running + brain free -> starts a topic relevant to Ben, not a meta topic about watching him', () => {
  const r = rig({ ben: BEN, cands: [
    { topic: 'Track app-switching patterns around evening code sessions', kind: 'proposal', interest: 0.9 },
    { topic: 'Session context classification: front-app transition intent inference', kind: 'proposal', interest: 0.9 },
    { topic: 'basketball history', kind: 'proposal', interest: 0.9 },
    { topic: 'gas stoichiometry and the ideal gas law for AP Chemistry labs', kind: 'proposal', interest: 0.2 }] });
  const x = r.k.kick('nothing to say');
  assert.strictEqual(x.action, 'start'); assert.strictEqual(r.w.started[0], 'gas stoichiometry and the ideal gas law for AP Chemistry labs');
});
test('one topic keeps going: its Motes run back to back until the quiz plateaus; then a NEW topic (never the old one)', () => {
  const r = rig({ ben: BEN, cands: [{ topic: 'gas stoichiometry for AP Chemistry', kind: 'proposal' }, { topic: 'video projector training for vision language models', kind: 'proposal' }] });
  assert.strictEqual(r.k.kick('x').action, 'start');
  r.tick(); assert.strictEqual(r.k.kick('x').action, 'continue'); assert.deepStrictEqual(r.w.ran, ['a']);
  r.tick(); assert.strictEqual(r.k.kick('x').action, 'running', 'a run in flight is left alone');
  r.w.running.clear(); r.k.ran('a'); r.tick(); assert.strictEqual(r.k.kick('x').action, 'continue'); assert.deepStrictEqual(r.w.ran, ['a', 'b']);
  r.w.quiz = { status: 'ready', levels: [{ level: 1 }], scores: [{ level: 1, pct: 40 }, { level: 1, pct: 60 }, { level: 1, pct: 62 }, { level: 1, pct: 61 }] };
  r.tick(); assert.strictEqual(r.k.kick('x').action, 'running', 'plateau, but the current run finishes first');
  r.w.running.clear(); r.tick(); const x = r.k.kick('x');
  assert.strictEqual(x.action, 'start'); assert.strictEqual(r.w.stopped, 1);
  assert.strictEqual(r.w.started[1], 'video projector training for vision language models');
  assert.strictEqual(r.w.started.length, 2);
});
test('plateau rule', () => {
  const q = (s, extra) => ({ status: 'ready', levels: [{ level: 1 }], scores: s.map((pct) => ({ level: 1, pct })), ...(extra || {}) });
  assert.strictEqual(K.plateau(q([50, 52, 51]), 3).done, true);
  assert.strictEqual(K.plateau(q([50, 60, 70]), 3).done, false);
  assert.strictEqual(K.plateau(q([30, 50, 51, 52]), 3).done, false, 'flat but the newest (52) is a new best: still climbing');
  assert.strictEqual(K.plateau(q([30, 50, 52, 51]), 3).done, true);
});
test('plateau: a new best in the last three keeps the topic', () => {
  const q = { status: 'ready', levels: [{ level: 1 }], scores: [60, 50, 51, 52].map((pct) => ({ level: 1, pct })) };
  assert.strictEqual(K.plateau(q, 3).done, true, 'best earlier 60, last 3 flat below it');
  assert.strictEqual(K.plateau(null, 11).done, false); assert.strictEqual(K.plateau(null, 12).done, true);
  assert.strictEqual(K.plateau({ status: 'ready', levels: [{ level: 1 }], scores: [], levelUpDue: true }, 30).done, false);
});
test('limits: Ben first / memory / night / model lock = wait; Ben\'s own Learn study is kept going, never replaced', () => {
  const r = rig({ ben: BEN, cands: [{ topic: 'gas stoichiometry', kind: 'proposal' }] });
  for (const why of ['chat', 'memory', 'night', 'model lock', 'asleep']) { r.w.free = { ok: false, why }; r.tick(); assert.deepStrictEqual(r.k.kick('x'), { action: 'wait', why }); }
  assert.strictEqual(r.w.started.length, 0);
  r.w.free = { ok: true }; r.w.cur = { topic: 'black holes', ids: ['x', 'y'], by: 'ben' };
  r.tick(); const x = r.k.kick('x'); assert.strictEqual(x.action, 'continue'); assert.strictEqual(x.by, 'ben');
  assert.strictEqual(r.w.started.length, 0); assert.strictEqual(r.w.stopped, 0);
});
test('the brain\'s "learn" is a proposal, not a new study; near-copies of a done topic are skipped', () => {
  const r = rig({ ben: BEN });
  r.k.propose('Hypergraphs in transformer modeling and app-usage switching patterns');
  r.k.propose('gas stoichiometry lab report sig figs');
  assert.strictEqual(r.k.kick('x').action, 'start'); assert.strictEqual(r.w.started[0], 'gas stoichiometry lab report sig figs');
  assert.ok(K.jaccard('gas stoichiometry lab report sig figs', 'gas stoichiometry lab report sig fig rules') >= 0.5);
});
test('duty sample: free + studying rows', () => {
  const r = rig({ ben: BEN, cands: [{ topic: 'gas stoichiometry', kind: 'proposal' }] });
  assert.deepStrictEqual([r.k.sample().free, r.k.sample().studying], [true, false]);
  r.k.kick('x'); r.tick(); r.k.kick('x');
  assert.strictEqual(r.k.sample().studying, true);
});
