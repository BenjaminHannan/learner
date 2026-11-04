'use strict';
// Glim team, Bedwars side: timed actions ("baseball"): tau estimates, the fire-at-tick rule, 1.8 crit physics, timing error in ms.
const test = require('node:test');
const assert = require('node:assert');
const M = require('../src/games/bedwars/timing');
const core = require('../src/games/bedwars/core-iface');

test('tau = distance / closing speed (ms); not closing = never', () => {
  assert.strictEqual(M.tau(4, 8), 500);
  assert.strictEqual(M.tau(0, 5), 0);
  assert.strictEqual(M.tau(-1, 5), 0, 'already there');
  assert.strictEqual(M.tau(3, 0), Infinity);
  assert.strictEqual(M.tau(3, -2), Infinity, 'moving apart');
  assert.ok(Math.abs(M.SKILLS.jump_at_edge({ edgeDist: 1.4, speed: 5.6 }) - 250) < 1e-9);
  assert.strictEqual(M.SKILLS.jump_at_edge({ edgeDist: 1.4, speed: 0 }), null, 'standing still: cancel');
  assert.strictEqual(M.SKILLS.block_at_hit({ dist: 5, closing: 4 }), 550, 'reach in 500 ms + 1 tick');
  assert.strictEqual(M.SKILLS.block_at_hit({ hitAgoMs: 20 }), 30, 'the hit just landed: block next tick');
  assert.strictEqual(M.SKILLS.crit_on_fall({ dist: 6, closing: 4 }), 750 - M.CRIT_MID_MS);
});

test('1.8 jump physics: falling ticks 7..11 after the jump -> crit window 350..550 ms, aim 450 ms', () => {
  assert.deepStrictEqual(M.ARC.filter((x) => x.falling).map((x) => x.k), [7, 8, 9, 10, 11]);
  assert.deepStrictEqual(M.CRIT_WINDOW_MS, { from: 350, to: 550 });
  assert.strictEqual(M.CRIT_MID_MS, 450);
  assert.ok(Math.abs(Math.max(...M.ARC.map((x) => x.y)) - 1.2522) < 1e-3, 'apex ~1.25 blocks');
});

test('fire rule: the tick nearest the moment fires; late by > 2 ticks cancels', () => {
  assert.strictEqual(M.decide(120), 'wait');
  assert.strictEqual(M.decide(26), 'wait');
  assert.strictEqual(M.decide(25), 'fire');
  assert.strictEqual(M.decide(0), 'fire');
  assert.strictEqual(M.decide(-80), 'fire', 'a little late: fire now');
  assert.strictEqual(M.decide(-101), 'cancel');
  assert.strictEqual(M.decide(null), 'cancel');
  assert.deepStrictEqual([M.bestTick(120), M.bestTick(74), M.bestTick(76), M.bestTick(10)], [2, 1, 2, 0]);
});

test('schedule (the real I3 core via core-iface): the jump is re-estimated every tick, moves later when he slows, fires once within a tick; a vanished target is cancelled', () => {
  // timing.timedTargets() feeds core ActionSchedule.tick(nowMs, [{id, action, lagMs, gap}]) -> [{id, action, atMs}]
  const s = new core.ActionSchedule({ tickMs: M.TICK_MS });
  let speed = 5.6; const edge0 = 0.672;   // 120 ms at 5.6 blocks/s
  const pos = (t) => edge0 - 5.6 * Math.min(t, 50) / 1000 - (t > 50 ? speed * (t - 50) / 1000 : 0);
  const at = (t) => s.tick(t, M.timedTargets({ edgeDist: pos(t) }, ['jump_at_edge']));
  assert.deepStrictEqual(at(0), []);
  assert.deepStrictEqual(at(50), []);
  speed = 2.8;   // he slows down after 50 ms
  assert.deepStrictEqual(at(100), []);
  const fired = [].concat(at(150), at(200));
  assert.strictEqual(fired.length, 1, 'an id fires once');
  assert.strictEqual(fired[0].id, 'jump_at_edge');
  // true moment: 50 ms at 5.6 (0.28 blocks) leaves 0.392 at 2.8 b/s = 140 ms -> 190 ms
  const err = s.contact('jump_at_edge', 190);
  assert.ok(Math.abs(err) <= M.TICK_MS, 'within one tick of the true moment, got ' + err + ' ms');
  const ttg = s.items.get('jump_at_edge').ttgLog.slice(1);   // the planned moment (tick + time-to-go) moved later as he slowed
  assert.ok(50 + ttg[0] < 100 + ttg[1], 'it moved later: ' + JSON.stringify(ttg));
  assert.deepStrictEqual([s.report().fired, s.report().misses], [1, 0]);
  // cancel: the target is missing from a tick (the edge went away) -> cancelled, not a timing miss
  const s2 = new core.ActionSchedule({ tickMs: M.TICK_MS });
  assert.deepStrictEqual(s2.tick(0, M.timedTargets({ edgeDist: 1.4 }, ['jump_at_edge'])), []);
  assert.deepStrictEqual(s2.tick(50, M.timedTargets({}, ['jump_at_edge'])), []);
  assert.strictEqual(s2.cancelled, 1);
  assert.strictEqual(s2.contact('jump_at_edge', 300), null);
  assert.deepStrictEqual([s2.report().misses, s2.report().dropped], [0, 1]);
});

test('timing error in ms vs the ideal moment from the truth log (one-to-one pairing; + = late)', () => {
  const ev = [{ t: 1000, type: 'hit', attacker: 'G', victim: 'B' }, { t: 2000, type: 'hit', attacker: 'G', victim: 'B' }, { t: 1500, type: 'hit', attacker: 'B', victim: 'G' },
    { t: 5000, type: 'edge', player: 'G' }, { t: 7000, type: 'edge', player: 'B' }];
  const ideal = M.idealMoments(ev, 'G');
  assert.deepStrictEqual(ideal, { block_at_hit: [1050, 2050], crit_on_fall: [550, 1550], jump_at_edge: [5000] });
  const acts = [{ skill: 'block_at_hit', t: 1100 }, { skill: 'block_at_hit', t: 2040 }, { skill: 'block_at_hit', t: 9000 },
    { skill: 'crit_on_fall', t: 500 }, { skill: 'jump_at_edge', t: 5075 }];
  const rep = M.timingReport(acts, ev, 'G');
  assert.deepStrictEqual(rep.block_at_hit.errs.map((e) => e.errMs), [50, -10]);
  assert.strictEqual(rep.block_at_hit.medianAbsMs, 30);
  assert.strictEqual(rep.block_at_hit.meanSignedMs, 20);
  assert.strictEqual(rep.block_at_hit.extra, 1, 'the 9000 ms block matches no hit');
  assert.strictEqual(rep.block_at_hit.withinTick, 1);
  assert.deepStrictEqual([rep.crit_on_fall.matched, rep.crit_on_fall.missed, rep.crit_on_fall.errs[0].errMs], [1, 1, -50]);
  assert.deepStrictEqual([rep.jump_at_edge.errs[0].errMs, rep.jump_at_edge.withinTick], [75, 0]);
  // GlimTruthKit edges carry last_supported_ms: the ideal jump is midway between the last supported tick and the first unsupported one
  assert.deepStrictEqual(M.idealMoments([{ t: 5000, type: 'edge', player: 'G', last_supported_ms: 4950 }], 'G').jump_at_edge, [4975]);
  assert.deepStrictEqual(M.idealMoments([{ t: 5000, type: 'edge', player: 'G', last_supported_ms: 3000 }], 'G').jump_at_edge, [5000], 'a stale last_supported_ms is ignored');
  // pairing is one-to-one and closest-first
  const p = M.pairErrors([100, 110], [105], 300);
  assert.deepStrictEqual([p.errs.length, p.extra, p.missed, Math.abs(p.errs[0].errMs)], [1, 1, 0, 5]);
});
