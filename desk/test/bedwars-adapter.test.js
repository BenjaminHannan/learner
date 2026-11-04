'use strict';
// Glim team, Bedwars side: the adapter (allowed inputs, intent, timed actions, plan + replan, sleep data hooks) and harness latency.
const test = require('node:test');
const assert = require('node:assert');
const A = require('../src/games/bedwars/adapter');
const H = require('../src/games/bedwars/harness');
const core = require('../src/games/bedwars/core-iface');
const T = require('../src/games/bedwars/tactics');

test('human-equivalent inputs only: the HUD whitelist refuses minimap / reach / distance / coords / truth; FOV <= 110; one view', () => {
  assert.ok(A.validateObs({ frame: { ref: 'f1', fov: 110, view: 'f5' }, hud: { hp: 20, hotbar: [], tnt_timer: 3 }, sound: [], est: { dist: 4 } }).ok);
  for (const k of ['minimap', 'reach', 'distance', 'coords', 'f3', 'opp_pos', 'speed']) assert.strictEqual(A.validateObs({ hud: { [k]: 1 } }).ok, false, k);
  assert.strictEqual(A.validateObs({ truth: [] }).ok, false, 'the truth log is never an input');
  assert.strictEqual(A.validateObs({ frame: { fov: 120 } }).ok, false);
  assert.strictEqual(A.validateObs({ frame: { view: 'freelook' } }).ok, false);
  assert.ok(!A.HUD_FIELDS.some((k) => A.FORBIDDEN.includes(k)));
  assert.throws(() => new A.BedwarsAdapter().tick(0, { hud: { minimap: [] } }), /forbidden/);
});

test('realtime adapter: budget, the last call is kept when none arrives for > 2 s, a bad line keeps the last good call', () => {
  const a = new A.BedwarsAdapter();
  assert.strictEqual(a.realtime, true); assert.strictEqual(A.realtime, true);
  assert.deepStrictEqual(a.budget, { frameToKeyMs: 30, tickMs: 50, staleMs: 2000 });
  assert.ok(a.onCall('st l w', 0).ok);
  let r = a.tick(1000); assert.strictEqual(r.stale, false); assert.strictEqual(T.lineText(r.calls), 'st l w');
  assert.strictEqual(a.onCall('do a flip', 1500).ok, false);
  r = a.tick(2500); assert.strictEqual(r.stale, true); assert.strictEqual(T.lineText(r.calls), 'st l w', 'kept after 2 s');
  assert.strictEqual(r.cond.length, A.COND_WIDTH); assert.strictEqual(r.cond[A.COND_WIDTH - 1], 1);
  assert.strictEqual(r.cond[T.CODES.indexOf('st')], 1);
  assert.strictEqual(a.callLog.length, 2); assert.strictEqual(a.callLog[1].ok, false);
  // the vector tells codes and params apart
  const c1 = A.conditioning([{ code: 'st', params: { dir: 'l', wtap: true } }]), c2 = A.conditioning([{ code: 'st', params: { dir: 'r', wtap: true } }]);
  assert.notDeepStrictEqual(Array.from(c1), Array.from(c2));
});

test('a timed call ("jc 3") goes on the action schedule and fires on the right tick; a new call replaces the old timing', () => {
  const a = new A.BedwarsAdapter(); const est = (t) => ({ hud: { hp: 20 }, est: { dist: 6 - 4 * t / 1000, closing: 4 } });
  a.tick(0, est(0)); a.onCall('jc 3; st l', 0);
  assert.deepStrictEqual(a.schedule.list().map((x) => [x.skill, x.ttgMs]), [['crit_on_fall', 300]]);
  const fired = []; for (let t = 50; t <= 600; t += 50) fired.push(...a.tick(t, est(t)).fired);
  assert.deepStrictEqual(fired.map((f) => [f.skill, f.t]), [['crit_on_fall', 300]], 'he is in reach at 750 ms; jump 450 ms before');
  a.onCall('bh', 600); a.onCall('bh', 650);
  assert.strictEqual(a.schedule.list().filter((x) => x.skill === 'block_at_hit').length, 1);
  assert.deepStrictEqual(A.TIMED_BY_CODE, { jc: 'crit_on_fall', bh: 'block_at_hit', jg: 'jump_at_edge' });
});

test('long horizon in the adapter: plan -> step calls -> replan on a knock-off; the scorer reads the replan from the plan log', () => {
  const a = new A.BedwarsAdapter({ me: 'G' });
  a.startPlan(null, 0);
  assert.strictEqual(a.plan.step(), 'get_resources'); assert.strictEqual(a.stepCall('get_resources'), 'get iron 16');
  a.stepDone(2000); a.stepDone(3000);
  assert.strictEqual(a.plan.step(), 'bridge'); assert.strictEqual(a.checkPlan(4000), null);
  const rp = a.checkPlan(5100, { knockedOff: true });
  assert.deepStrictEqual(rp.reasons, ['knocked_off']); assert.strictEqual(a.plan.step(), 'get_resources');
  a.tick(6000, { hud: { hp: 4 } }); assert.deepStrictEqual(a.checkPlan(6000).reasons, ['low_hp']);
  const ev = [{ t: 1000, type: 'pickup', player: 'G', item: 'iron', count: 16 }, { t: 3000, type: 'purchase', player: 'G', item: 'wool' },
    { t: 5000, type: 'void_death', victim: 'G' }, ...Array.from({ length: 8 }, (_, i) => ({ t: 7000 + i * 100, type: 'block_place', player: 'G' })),
    { t: 9000, type: 'bed_broken', text: 'BED DESTRUCTION > Red Bed was destroyed by G!' }];
  const lh = H.longHorizon(ev, 'G', ['get_resources', 'buy_blocks', { step: 'bridge', n: 8 }, 'break_bed'], a.planLog);
  assert.deepStrictEqual([lh.finished, lh.replans, lh.replanAfterInterruption, lh.milestone], [true, 2, true, true]);
});

test('sleep hooks give day data only: no games at night; a hook that plays is refused', () => {
  assert.strictEqual(A.sleepHooks.nightPlay, false);
  assert.strictEqual(core.sleepHooks.get('bedwars'), A.sleepHooks);
  assert.throws(() => core.registerSleepHook({ game: 'x', play: () => {} }), /never plays/);
  const day = { me: 'G', frames: [{ t: 0 }, { t: 600 }], calls: [{ t: 0, text: 'jc 3' }],
    events: [{ t: 0, type: 'match_start' }, { t: 1000, type: 'hit', attacker: 'G', victim: 'B', crit: true, damage: 6 }, { t: 1500, type: 'purchase', player: 'G', item: 'wool', cost: 4, currency: 'iron' }, { t: 2000, type: 'match_end' }] };
  assert.deepStrictEqual(A.sleepHooks.replayDay(day), { frames: 2, keys: 0, calls: 1, events: 4 });
  assert.deepStrictEqual(A.sleepHooks.labels(day).map((x) => x.ttHitMs), [1000, 400]);
  assert.strictEqual(A.sleepHooks.cards(day)[0].worked, true);
  assert.strictEqual(A.sleepHooks.rewards(day).parts.hits, 1);
  assert.deepStrictEqual(A.sleepHooks.mechanics(day).map((m) => m.kind), ['hit', 'price']);
  assert.strictEqual(A.sleepHooks.mechanics(day)[1].cost, 4);
});

test('harness latency: p95 frame->key against the 30 ms budget', () => {
  const recs = Array.from({ length: 100 }, (_, i) => ({ frameT: i * 50, keyT: i * 50 + (i < 95 ? 20 : 45) }));
  const l = H.latency(recs);
  assert.deepStrictEqual([l.n, l.p50, l.p95, l.max, l.pass], [100, 20, 20, 45, true]);
  assert.strictEqual(l.overBudget, 0.05);
  recs[94].keyT = recs[94].frameT + 31;
  assert.strictEqual(H.latency(recs).pass, false, 'the 95th value is now over 30 ms');
  assert.strictEqual(H.latency([]).pass, null);
});
