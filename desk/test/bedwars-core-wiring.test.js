'use strict';
// Glim team, Bedwars side: the adapter wired to I3's real core, driven by a fake slow brain as slow and as wrong as the measured one
// (Nanbeige on the M1, I3 real/: ~2.7 s per call, 3.5-11 s per plan, so <= 0.35 calls/s; always well-formed, but the right next
// call only 6/12, whole plans 1/12, the "already done" list often ignored, no required follow-up after a lock 0/6).
// What must hold: play continues every tick, the plan advances between brain answers, required steps appear without the brain,
// timed jumps keep firing; and without the plan rules the same brain fails.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const A = require('../src/games/bedwars/adapter');
const C = require('../src/games/bedwars/core-iface');
const { rng } = require('../src/tinynet');

const PLAN_LATENCY = [3500, 11000];   // measured seconds per plan
// the fake brain: real prompt in, text out, parsed by the core's parser (the same path as the real model's reply)
function badBrain(seed) {
  const r = rng(seed * 31 + 7), log = [];
  return { log, think(obs, view, need) {
    const prompt = C.buildPrompt(A, obs, view, need);
    const lines = ['GET res=iron n=16', 'BUY item=wool', 'BRIDGE n=20', 'BREAK_BED'];   // ignores "already done": always the whole rush again
    if (r() < 0.5) lines.unshift(['HOLD', 'DEFEND', 'RETREAT', 'HOME'][Math.floor(r() * 4)]);   // the wrong next call half the time
    if (r() < 0.3) lines.splice(lines.length - 3, 1);   // a step missing; never BUY item=shears, even for a covered bed
    const text = lines.join('\n'); log.push({ need, text, sawDone: view.done.length, promptChars: prompt.user.length });
    return C.parseCalls(A.vocab, text);
  } };
}
function play(adapter, seed, covered, o) {
  const brain = badBrain(seed), m = { ticks: 0, noMove: 0, advances: [], answers: [], movedWhileWaiting: 0, callsSeen: new Set() };
  const r = C.runLive(adapter, { seed, game: { covered }, brain, latencyMs: PLAN_LATENCY, log: false, ...(o || {}), onTick: (t, out, obs, lp) => {
    m.ticks++; if (typeof out.move !== 'number') m.noMove++;
    if (out.call) m.callsSeen.add(out.call.code);
    if (out.event === 'advanced') m.advances.push(t);
    if (lp.pending && out.move !== 0) m.movedWhileWaiting++;
  } });
  m.answers = r.planLog.filter((p) => p.by === 'brain').map((p) => p.t);
  return { r, m, brain };
}
const SEEDS = [1, 2, 3, 4, 5, 6];

test('a 0.35 Hz brain that is wrong half the time: the goal is reached, the plan and reflex carry the play between calls', () => {
  let goals = 0, games = 0;
  for (const covered of [false, true]) for (const seed of SEEDS) {
    const { r, m, brain } = play(A, seed, covered); games++;
    const tag = 'seed ' + seed + (covered ? ' covered' : '');
    if (r.outcome.goalDone) goals++;
    // the brain is never asked faster than its measured rate, and it is asked rarely
    for (let i = 1; i < r.askTimes.length; i++) assert.ok(r.askTimes[i] - r.askTimes[i - 1] >= C.MIN_ASK_GAP_MS, tag + ' asked too fast');
    assert.ok(r.brainRatePerS == null || r.brainRatePerS <= 0.35, tag + ' rate ' + r.brainRatePerS);
    assert.ok(r.brainAsks <= 4, tag + ' brain asks ' + r.brainAsks);
    // play continues: a move on every tick; something done (not just standing) while the brain was still thinking
    assert.strictEqual(m.noMove, 0, tag);
    assert.ok(m.movedWhileWaiting > 0 && m.advances.some((t) => t < m.answers[0]), tag + ': no standing still while the first plan is thought about');
    // the plan advances by itself between brain answers: more advances than answers, and several after the last answer
    const between = m.advances.filter((t) => !m.answers.includes(t)).length;
    assert.ok(r.advancedByPlan > m.answers.length, tag + ' advanced ' + r.advancedByPlan + ' vs answers ' + m.answers.length);
    assert.ok(between >= 3, tag + ' plan advances on ticks with no brain answer: ' + between);
    // the brain ignored the done list every time; the plan memory did not
    assert.ok(brain.log.every((x) => x.text.startsWith('GET') || x.text.split('\n')[1].startsWith('GET')));
    if (r.outcome.goalDone) {
      assert.deepStrictEqual(r.plan.remaining.map((id) => id.split('#')[0]), ['break_bed'], tag + ': the bed broke during the last step');
      assert.ok(r.outcome.crossings >= 1, tag + ': the jump at the bridge end fired on time at least once');
      // the required follow-up the brain never sends: shears for a covered bed, bought because the plan added them
      if (covered) assert.ok(r.outcome.bought.includes('shears'), tag + ' shears');
      assert.ok(!brain.log.some((x) => /shears/.test(x.text)));
    }
    assert.ok(r.timing.contacts >= 1, tag + ' timed actions were scored');
  }
  assert.ok(goals >= games - 1, 'goal reached ' + goals + '/' + games);
});

test('timed jumps keep firing between brain calls: edge jumps land within the crossing window', () => {
  const errs = [];
  for (const covered of [false, true]) for (const seed of SEEDS) {
    let lp0; C.runLive(A, { seed, game: { covered }, brain: badBrain(seed), latencyMs: PLAN_LATENCY, log: false, onTick: (t, o, obs, lp) => { lp0 = lp; } });
    for (const it of lp0.sched.items.values()) if (it.id.startsWith('edge:') && it.err != null) errs.push(Math.abs(it.err));
  }
  errs.sort((a, b) => a - b);
  assert.ok(errs.length >= SEEDS.length, 'edge jumps fired: ' + errs.length);
  assert.ok(errs[Math.floor(errs.length / 2)] <= A.tickMs, 'median edge error ' + errs[Math.floor(errs.length / 2)] + ' ms');
  assert.ok(errs.filter((e) => e <= A.P.EDGE_WIN).length / errs.length >= 0.9, 'within the crossing window: ' + JSON.stringify(errs));
});

test('control: the same brain without the plan rules (repair / urgent / interruptions) does worse; covered beds are never broken', () => {
  const bare = { ...A, repair: null, urgent: null, interrupted: null };
  let wired = 0, ctrl = 0, ctrlCovered = 0, ctrlAsks = 0, wiredAsks = 0;
  for (const covered of [false, true]) for (const seed of SEEDS) {
    const w = play(A, seed, covered).r, c = play(bare, seed, covered).r;
    wired += w.outcome.goalDone ? 1 : 0; ctrl += c.outcome.goalDone ? 1 : 0; if (covered && c.outcome.goalDone) ctrlCovered++;
    wiredAsks += w.brainAsks; ctrlAsks += c.brainAsks;
  }
  assert.strictEqual(ctrlCovered, 0, 'without the rules nobody buys shears');
  assert.ok(wired >= ctrl + SEEDS.length - 1, 'wired ' + wired + ' vs control ' + ctrl);
  assert.ok(ctrlAsks > wiredAsks, 'without the rules the slow brain is asked more: ' + ctrlAsks + ' vs ' + wiredAsks);
});

test('the brain never answers (down or hung): the rules alone still play to the goal; brain-first would stand still', () => {
  const hung = { think: () => new Promise(() => {}) };
  for (const covered of [false, true]) {
    const r = C.runLive(A, { seed: 3, game: { covered }, brain: hung, log: false });
    assert.ok(r.outcome.goalDone, 'rules first, covered=' + covered); assert.strictEqual(r.brainAsks, 1, 'asked once, never re-asked while it hangs');
    assert.ok(!C.runLive(A, { seed: 3, game: { covered }, brain: hung, log: false, rulesFirst: false }).outcome.goalDone);
  }
});

test('a real-model-shaped brain (answers as Promises) works in an async tick loop and is not re-asked while thinking', async () => {
  const lp = new C.LiveLoop(A, { brain: { think: (obs, view, need) => new Promise((res) => setTimeout(() => res(badBrain(1).think(obs, view, need)), 5)) } });
  let s = A.init(1, { covered: false }), asks = 0;
  for (let i = 0; i < 400 && !A.done(s); i++) {
    const t = i * A.tickMs, obs = A.observe(s, t), out = lp.tick(obs, t); asks = lp.stats.brainAsks;
    const res = A.step(s, out.move, out.fired, t); s = res.state; lp.contacts(res.contacts);
    await new Promise((r) => setImmediate(r));
  }
  assert.ok(lp.plan.goal, 'a plan arrived'); assert.ok(lp.plan.done.length >= 2, 'and advanced: ' + lp.plan.done.join(','));
  assert.ok(asks <= 3, 'asks ' + asks);
});

test('the core\'s own runEpisode (stand-in brain) plays the adapter too; a day of frames feeds the reflex sleep', () => {
  let ok = 0;
  for (const seed of [1, 2, 3, 4]) { const e = C.runEpisode(A, { seed }); if (e.outcome.goalDone) ok++; assert.ok(e.acts.length > 0 && e.reflexP95Ms < 5); }
  assert.ok(ok >= 3, 'runEpisode goal ' + ok + '/4');
  const day = C.runLive(A, { seed: 2, brain: badBrain(2), latencyMs: PLAN_LATENCY });
  assert.ok(day.acts.length > 100 && day.acts.some((a) => a.r.truth), 'frames logged with the truth for the night labeller');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'glim-bw-sleep-'));   // our own scratch
  const sl = new C.ReflexSleep({ dir, now: () => new Date(2026, 10, 4, 12).getTime(), cfg: { steps: 60, tSteps: 60 } });
  assert.ok(sl.logDay(day.acts, day.times) > 0);
  const rec = sl.nightly({ features: A.features, label: A.nightLabel, fallback: A.fallbackRaw, nIn: A.nIn, nA: A.nA }, { seed: 3 });
  assert.ok(!/error/.test(rec.why || ''), JSON.stringify(rec)); assert.ok(rec.train && rec.train.a > 0, JSON.stringify(rec));
});
