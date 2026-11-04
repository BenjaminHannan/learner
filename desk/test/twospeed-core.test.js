'use strict';
// I3 two-speed core: intent channel, plan memory, timed actions (tau), reflex-in-sleep, the loop on two different games.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { IntentChannel, parse } = require('../src/games/core/intent');
const { PlanMemory } = require('../src/games/core/plan');
const { ActionSchedule, TauEstimator } = require('../src/games/core/schedule');
const { ReflexSleep } = require('../src/games/core/reflex');
const { runEpisode } = require('../src/games/core/loop');
const { buildPrompt, parseCalls } = require('../src/games/core/brain');
const sparksquest = require('../src/games/adapters/sparksquest');
const orchard = require('../src/games/adapters/orchard');

const V = { STRAFE: { args: { dir: { enum: ['left', 'right'] }, wtap: { min: 0, max: 1, int: true, default: 0 } } }, JUMPCRIT: { args: { at: { min: 1, max: 6 } } } };

test('intent: fixed vocabulary, text parsing, rejects unknown, keeps the last call when the brain is quiet', () => {
  const ch = new IntentChannel(V, { holdMs: 2000 });
  assert.equal(ch.send('strafe dir=LEFT wtap=1', 0).ok, true);
  assert.deepEqual(ch.current(100).call, { code: 'STRAFE', args: { dir: 'left', wtap: 1 } });
  assert.equal(ch.send('FLY up', 200).ok, false);
  assert.equal(ch.send({ code: 'JUMPCRIT', args: { at: 9 } }, 300).ok, false, 'out of range');
  const late = ch.current(2500); assert.equal(late.call.code, 'STRAFE'); assert.equal(late.stale, true, 'older than 2 s: kept, marked stale');
  assert.equal(parse(V, 'Sure! JUMPCRIT(at=3)').call.args.at, 3);
  assert.equal(parse(V, '{"code":"STRAFE","args":{"dir":"right"}}').call.args.wtap, 0, 'default filled');
  ch.send('JUMPCRIT at=3', 1000); const st = ch.stats(); assert.equal(st.fromBrain, 2); assert.equal(st.rejected, 2); assert.ok(st.ratePerS > 0);
});

test('plan memory: advances, a blocked step asks for a replan, done steps survive the replan and a restart', () => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'i3plan-')), 'plan.json');
  const pm = new PlanMemory({ file, patienceMs: 1000 });
  pm.setPlan('g', [{ id: 'a', call: {} }, { id: 'b', call: {} }, { id: 'c', call: {} }], 0);
  const judge = (st, obs) => obs[st.id] || { status: 'going', progress: 0 };
  assert.equal(pm.tick({ a: { status: 'done' } }, judge, 10).event, 'advanced');
  assert.equal(pm.tick({ b: { status: 'blocked', why: 'locked' } }, judge, 20).event, 'surprise');
  assert.match(pm.needsReplan, /blocked: locked/);
  pm.replan([{ id: 'k', call: {} }, { id: 'b', call: {} }, { id: 'c', call: {} }], 30);
  assert.equal(pm.replans, 1); assert.deepEqual(pm.view().done, ['a']); assert.equal(pm.current().id, 'k');
  const again = new PlanMemory({ file, patienceMs: 1000 }); assert.deepEqual(again.view().done, ['a']); assert.equal(again.current().id, 'k');
  assert.equal(again.tick({}, judge, 5000).event, null); assert.equal(again.tick({}, judge, 7000).event, 'surprise', 'no progress for patienceMs = stalled');
});

test('timed actions: tau fires on the right tick (with the wind-up lag), re-estimates under acceleration, cancels a receding target', () => {
  // constant speed: gap 10 - 4 t (s) -> contact 2.5 s; lag 150 ms -> fire at ~2350 ms
  const a = new ActionSchedule({ tickMs: 50 }); let fired = null;
  for (let t = 0; t <= 3000 && !fired; t += 50) { const f = a.tick(t, [{ id: 'x', action: 'jump', lagMs: 150, gap: 10 - 4 * t / 1000 }]); if (f.length) fired = f[0].atMs; }
  assert.ok(Math.abs(fired + 150 - 2500) <= 25, 'fired at ' + fired); assert.ok(Math.abs(a.contact('x', 2500)) <= 25);
  // accelerating (gravity from rest): h = 8 - 0.5*4*t^2 -> contact 2 s. 'tau' within a tick, 'once' (constant speed, never updated) far off
  const run = (mode) => { const s = new ActionSchedule({ tickMs: 50, mode }); for (let t = 0; t <= 2500; t += 50) { const h = 8 - 2 * (t / 1000) ** 2; if (h <= 0) break; s.tick(t, [{ id: 'f', action: 'catch', lagMs: 100, gap: h }]); } s.contact('f', 2000); return s.report(); };
  assert.ok(run('tau').medianAbsMs <= 50, JSON.stringify(run('tau'))); assert.ok(run('once').medianAbsMs > 200, JSON.stringify(run('once')));
  // receding: never fires, gets cancelled
  const c = new ActionSchedule({ tickMs: 50 }); for (let t = 0; t <= 1000; t += 50) assert.equal(c.tick(t, [{ id: 'r', action: 'jump', lagMs: 0, gap: 2 + t / 1000 }]).length, 0);
  assert.equal(c.items.get('r').status, 'cancelled');
  // "in 120 ms I will jump": explicit plan, can be moved later
  const e = new ActionSchedule({ tickMs: 50 }); e.plan('j', 'jump', 120, 0); e.move('j', 100);
  let at = null; for (let t = 0; t <= 400 && at == null; t += 50) { const f = e.tick(t, []); if (f.length) at = t; }
  assert.equal(at, 200);
  const est = new TauEstimator(8); for (let t = 0; t < 400; t += 50) est.add(t, 5 - 0.01 * t); assert.equal(est.features().length, 5);
});

test('reflex sleep: learns from the day\'s frames only, keeps a better head, rejects a poisoned night, crash-safe', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'i3sleep-')); let day = 1;
  const mk = () => new ReflexSleep({ dir, now: () => new Date(2026, 0, day, 12).getTime(), cfg: { steps: 400, tSteps: 400 } });
  // toy: 2 inputs, label = 1 when x0 > x1; the hand rule always says 0. Timing: true ttg = 1.3 x plain estimate.
  const AD = { features: (r) => Float64Array.from(r), label: (r) => (r[0] > r[1] ? 1 : 0), fallback: () => 0, nIn: 2, nA: 2 };
  const dayFrames = (seed) => { let s = seed; const R = () => ((s = (s * 16807) % 2147483647) / 2147483647); const acts = [], times = []; for (let i = 0; i < 400; i++) { acts.push({ r: [R(), R()], a: 0 }); const q = 0.2 + 0.6 * R(); times.push({ f: [q, q, 0, 1, 0], q, y: 1.3 * q }); } return { acts, times }; };
  let d = dayFrames(7); mk().logDay(d.acts, d.times);
  const n1 = mk().nightly(AD, { seed: 1 }); assert.equal(n1.keptAction, true, JSON.stringify(n1)); assert.equal(n1.keptTiming, true, JSON.stringify(n1));
  assert.ok(fs.existsSync(path.join(dir, 'model.json')));
  day = 2; d = dayFrames(99); mk().logDay(d.acts, d.times);
  const p = mk().nightly(AD, { seed: 2, poison: 0.6 }); assert.equal(p.kept, false, 'a 60 % poisoned night is rolled back: ' + JSON.stringify(p));
  const bad = mk().nightly({ ...AD, label: () => { throw new Error('boom'); } }); assert.equal(bad.kept, false); assert.match(bad.why, /error: boom/);
  assert.ok(fs.readFileSync(path.join(dir, 'nightly.jsonl'), 'utf8').split('\n').filter(Boolean).length >= 3);
});

test('loop: the same core plays two different games (long goal with a replan, timed actions); controls do worse', () => {
  for (const ad of [sparksquest, orchard]) {
    let ok = 0, noReplanOk = 0; const errs = [];
    for (let k = 0; k < 4; k++) {
      const r = runEpisode(ad, { seed: 4242 + k }); if (r.outcome.goalDone && r.replans >= 1) ok++; errs.push(...r.errors.map(Math.abs));
      if (runEpisode(ad, { seed: 4242 + k, replan: false, log: false }).outcome.goalDone) noReplanOk++;
      assert.ok(r.acts.length > 0 && r.reflexP95Ms < 5);
    }
    errs.sort((a, b) => a - b);
    assert.ok(ok >= 3, ad.name + ' goal+replan ' + ok + '/4'); assert.equal(noReplanOk, 0, ad.name + ' never finishes without replanning');
    assert.ok(errs[Math.floor(errs.length / 2)] <= 50, ad.name + ' median timing ' + errs[Math.floor(errs.length / 2)]);
  }
});

test('core stays game-agnostic; T6 files untouched by the core; brain prompt round-trips through the vocabulary', () => {
  for (const f of fs.readdirSync(path.join(__dirname, '..', 'src', 'games', 'core'))) assert.doesNotMatch(fs.readFileSync(path.join(__dirname, '..', 'src', 'games', 'core', f), 'utf8'), /sparks|orchard|checkpoint|fruit|tree|shockwave|basket|barrel/i, f);
  const s = orchard.init(3), obs = orchard.observe(s, 0), pr = buildPrompt(orchard, obs, { done: [] }, 'plan');
  assert.match(pr.system, /CATCH tree=T1\|T2/); assert.match(pr.user, /Deliver in order/);
  const pc = parseCalls(orchard.vocab, 'CATCH tree=T2\nDEPOSIT\nplease wait\nCATCH tree=T9');
  assert.equal(pc.calls.length, 2); assert.equal(pc.bad.length, 2);
});

test('main: two-speed play is behind a setting that defaults OFF, plays only while Ben is away, distils at night', () => {
  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(main, /if \(store\.getSettings\(\)\.twoSpeedPlay !== true \|\| Date\.now\(\) - aoTwoLast < 600000\) return;/);
  assert.match(main, /aoNightlyJobs\.push\(\(\) => \{ if \(store\.getSettings\(\)\.twoSpeedPlay !== true\) return;/);
  const store = require('../src/store'); assert.equal(store.DEFAULT_SETTINGS ? store.DEFAULT_SETTINGS.twoSpeedPlay : false, false);
  assert.match(fs.readFileSync(path.join(__dirname, '..', 'src', 'store.js'), 'utf8'), /twoSpeedPlay: false,/);
  assert.match(fs.readFileSync(path.join(__dirname, '..', 'renderer', 'app.js'), 'utf8'), /key: 'twoSpeedPlay', type: 'toggle', label: 'Two-speed play'/);
});
