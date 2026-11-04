'use strict';
// Glim team, Bedwars side: the truth log -> rewards (Ben's rules), hindsight labels, the long-horizon goal scorer, worked/failed cards.
const test = require('node:test');
const assert = require('node:assert');
const L = require('../src/games/bedwars/truthlog');
const H = require('../src/games/bedwars/harness');

const near = (a, b, msg) => assert.ok(Math.abs(a - b) < 1e-9, (msg || '') + ' got ' + a + ' want ' + b);
const hit = (t, a, v, x) => ({ t, type: 'hit', attacker: a, victim: v, ...(x || {}) });

test('rewards: +1 hit, -1 taken, +5 kill, -5 death; a kill line and a death line for one death count once', () => {
  const ev = [{ t: 0, type: 'match_start' }, hit(500, 'G', 'B'), hit(700, 'B', 'G'), hit(900, 'G', 'B'),
    { t: 1500, type: 'death', victim: 'B', killer: 'G', cause: 'melee' }, { t: 1500, type: 'kill', killer: 'G', victim: 'B' }, { t: 4000, type: 'match_end' }];
  const g = L.rewards(ev, 'G');
  assert.deepStrictEqual(g.parts, { hits: 2, taken: -1, kills: 5, deaths: 0, idle: 0 });
  near(g.total, 6);
  const b = L.rewards(ev, 'B');
  assert.deepStrictEqual(b.parts, { hits: 1, taken: -2, kills: 0, deaths: -5, idle: 0 });
  near(b.total, -6);
});

test('void death = a kill for the opponent only if they hit the victim within the last 10 s (inclusive); server credit ignored', () => {
  const base = (dt, extra) => [{ t: 0, type: 'match_start' }, hit(1000, 'G', 'B'), { t: 1000 + dt, type: 'void_death', victim: 'B' }, ...(extra || []), { t: 1000 + dt, type: 'match_end' }];
  assert.strictEqual(L.rewards(base(9999), 'G').parts.kills, 5, '9.999 s');
  assert.strictEqual(L.rewards(base(10000), 'G').parts.kills, 5, 'exactly 10 s');
  assert.strictEqual(L.rewards(base(10001), 'G').parts.kills, 0, '10.001 s');
  assert.strictEqual(L.rewards(base(10001, [{ t: 11001, type: 'kill', killer: 'G', victim: 'B' }]), 'G').parts.kills, 0, 'the server credited G, but the hit was > 10 s before');
  assert.strictEqual(L.rewards(base(10001), 'B').parts.deaths, -5, 'the victim pays -5 either way');
  // a death line with a void cause counts as void (Paper says outOfWorld)
  const c = [{ t: 0, type: 'match_start' }, hit(1000, 'G', 'B'), { t: 4000, type: 'death', victim: 'B', cause: 'outOfWorld' }];
  assert.strictEqual(L.rewards(c, 'G').parts.kills, 5);
  // one kill, never two: void_death + death + kill lines for the same fall
  const d = [{ t: 0, type: 'match_start' }, hit(1000, 'G', 'B'), { t: 4000, type: 'void_death', victim: 'B' }, { t: 4000, type: 'death', victim: 'B', cause: 'void' }, { t: 4010, type: 'kill', killer: 'G', victim: 'B' }];
  assert.strictEqual(L.rewards(d, 'G').parts.kills, 5);
  assert.strictEqual(L.rewards(d, 'B').parts.deaths, -5);
  // the other way round: B knocks G off; G gets no kill for its own fall
  const e = [{ t: 0, type: 'match_start' }, hit(2000, 'B', 'G'), { t: 5000, type: 'void_death', victim: 'G' }];
  assert.deepStrictEqual([L.rewards(e, 'B').parts.kills, L.rewards(e, 'G').parts.kills, L.rewards(e, 'G').parts.deaths], [5, 0, -5]);
  // a hit from before the match start still counts for the 10 s look-back (but is not itself rewarded); ISO times work
  const iso = (ms) => new Date(Date.UTC(2026, 10, 4, 15, 0, 0) + ms).toISOString();
  const f = [hit(iso(-500), 'G', 'B'), { t: iso(0), type: 'match_start' }, { t: iso(9000), type: 'void_death', victim: 'B' }];
  assert.deepStrictEqual([L.rewards(f, 'G').parts.kills, L.rewards(f, 'G').parts.hits], [5, 0]);
});

test('idle: -0.02 for each whole second from the start with no hit landed by me, only while both are alive', () => {
  const ev = [{ t: 0, type: 'match_start' }, hit(1200, 'G', 'B'), { t: 5000, type: 'match_end' }];
  const g = L.rewards(ev, 'G'); near(g.parts.idle, -0.08); near(g.total, 0.92);
  const b = L.rewards(ev, 'B'); near(b.parts.idle, -0.1); near(b.total, -1.1);
  assert.strictEqual(g.timeline.filter((x) => x.why === 'no hit this second').length, 4);
  // a death pauses it: seconds that touch [death, death + respawn) are not charged; a final death stops it for good
  const dead = [{ t: 0, type: 'match_start' }, { t: 2500, type: 'death', victim: 'B' }, { t: 10000, type: 'match_end' }];
  near(L.rewards(dead, 'G', { opp: 'B', respawnMs: 5000 }).parts.idle, -0.02 * 4, 'seconds 0,1 and 8,9');
  const fin = [{ t: 0, type: 'match_start' }, { t: 2500, type: 'death', victim: 'B', final: true }, { t: 10000, type: 'match_end' }];
  near(L.rewards(fin, 'G', { opp: 'B' }).parts.idle, -0.04);
});

test('hindsight labels: time-to-hit, time-to-taken-hit, time-to-edge, crit windows', () => {
  const ev = [hit(1000, 'G', 'B'), hit(1700, 'B', 'G'), { t: 3000, type: 'edge', player: 'G' }];
  const lab = L.hindsight([0, 550, 600, 1000, 3500], ev, 'G');
  assert.deepStrictEqual(lab.map((x) => x.ttHitMs), [1000, 450, 400, 0, null]);
  assert.deepStrictEqual(lab.map((x) => x.ttTakenMs), [1700, 1150, 1100, 700, null]);
  assert.deepStrictEqual(lab.map((x) => x.ttEdgeMs), [null, null, null, 2000, null]);
  assert.deepStrictEqual(lab.map((x) => x.critNow), [false, true, true, false, false], 'a jump now puts the hit 350..550 ms later');
  assert.deepStrictEqual(lab.map((x) => x.critJumpTtgMs), [550, 0, null, null, null]);
});

test('goal scorer: steps in order, a knock-off resets the step in progress, replans are counted', () => {
  const ev = [{ t: 0, type: 'match_start' },
    { t: 1000, type: 'pickup', player: 'G', item: 'iron_ingot', count: 8 }, { t: 2000, type: 'pickup', player: 'G', item: 'iron_ingot', count: 8 },
    { t: 3000, type: 'purchase', player: 'G', item: 'wool' },
    ...[4000, 4100, 4200].map((t) => ({ t, type: 'block_place', player: 'G' })),
    { t: 5000, type: 'void_death', victim: 'G' },
    ...Array.from({ length: 8 }, (_, i) => ({ t: 12000 + 100 * i, type: 'block_place', player: 'G' })),
    { t: 20000, type: 'bed_broken', team: 'red', by: 'G' }];
  const plan = ['get_resources', 'buy_blocks', { step: 'bridge', n: 8 }, 'break_bed'];
  const g = L.goalScore(ev, 'G', plan, [{ t: 5200, type: 'replan', reason: 'knocked_off' }]);
  assert.deepStrictEqual(g.steps.map((s) => [s.step, s.done, s.t]), [['get_resources', true, 2000], ['buy_blocks', true, 3000], ['bridge', true, 12700], ['break_bed', true, 20000]]);
  assert.strictEqual(g.finished, true); assert.strictEqual(g.replans, 1); assert.strictEqual(g.interruptions, 1); assert.strictEqual(g.replanAfterInterruption, true);
  assert.strictEqual(H.longHorizon(ev, 'G', plan, [{ t: 5200, type: 'replan', reason: 'knocked_off' }]).milestone, true);
  assert.strictEqual(H.longHorizon(ev, 'G', plan, []).milestone, false, 'no replan -> not the milestone');
  // only 3 blocks before the fall + 5 after = not enough: the fall reset the count
  const short = ev.filter((e) => !(e.type === 'block_place' && e.t >= 12500));
  assert.deepStrictEqual(L.goalScore(short, 'G', plan, []).steps.map((s) => s.done), [true, true, false, false]);
  // out of order: the bed broken before any bridging does not count
  const early = [{ t: 0, type: 'bed_broken', by: 'G' }, ...ev.filter((e) => e.type !== 'bed_broken')];
  assert.strictEqual(L.goalScore(early, 'G', plan, []).steps[3].done, false);
  // someone else's progress does not count
  assert.strictEqual(L.goalScore(ev.map((e) => ({ ...e, player: e.player && 'B', by: e.by && 'B' })), 'G', plan, []).completed, 0);
});

test('cards: call -> outcome text from the truth log only (no grader fields)', () => {
  const ev = [hit(500, 'G', 'B', { crit: true }), ...[2100, 2200, 2300, 2400].map((t) => ({ t, type: 'block_place', player: 'G' })),
    hit(30100, 'B', 'G'), hit(30200, 'B', 'G'), hit(30300, 'G', 'B')];
  const calls = [{ t: 0, text: 'jc 3' }, { t: 2000, text: 'br 4' }, { t: 2500, text: 'br 4' }, { t: 9000, text: 'buy wool' }, { t: 30000, text: 'st l w' }, { t: 33000, text: 'rb' }, { t: 34000, text: 'not a call' }];
  const cs = L.cards(calls, ev, 'G');
  assert.deepStrictEqual(cs.map((c) => [c.call, c.worked]), [['jc 3', true], ['br 4', true], ['buy wool', false], ['st l w', false]]);
  assert.match(cs[0].text, /^I called "jc 3" -> it worked: the crit landed/);
  assert.match(cs[1].text, /placed 4\/4/);
  assert.match(cs[3].text, /I got hit first: 1 landed, 2 taken/);
  for (const c of cs) assert.deepStrictEqual(Object.keys(c).sort(), ['call', 't', 'text', 'worked']);
});

test('GlimTruthKit shapes: VOID_FINAL_KILL is a void death, shop ids stone/glass are blocks, track() reads tick rows', () => {
  // one final void death: death + kill + void_death lines with the same ms (as GlimTruthKit writes them) count once
  const ev = [{ ms: 1000, t: '2026-11-04T10:00:01.000-05:00', type: 'hit', attacker: 'G', victim: 'B', damage: 1, crit: false, via: 'melee' },
    { ms: 2000, t: 2000, type: 'death', victim: 'B', killer: 'G', cause: 'VOID_FINAL_KILL', final: true, void: true },
    { ms: 2000, t: 2000, type: 'kill', victim: 'B', killer: 'G', cause: 'VOID_FINAL_KILL', final: true, void: true },
    { ms: 2000, t: 2000, type: 'void_death', victim: 'B', killer: 'G', final: true }];
  const d = L.deaths(ev);
  assert.strictEqual(d.length, 1);
  assert.strictEqual(d[0].void, true);
  assert.strictEqual(L.rewards(ev, 'G').parts.kills, 5);
  assert.strictEqual(L.rewards(ev, 'B').parts.deaths, -5);
  // a cause-only void (no void flag) is still void
  assert.strictEqual(L.deaths([{ t: 0, type: 'death', victim: 'B', cause: 'VOID_FINAL_KILL' }])[0].void, true);
  // the shop's end stone id is "stone"; glass counts too
  const plan = ['buy_blocks'];
  for (const item of ['stone', 'glass', 'wool']) assert.strictEqual(L.goalScore([{ t: 0, type: 'purchase', player: 'G', item }], 'G', plan, []).completed, 1, item);
  assert.strictEqual(L.goalScore([{ t: 0, type: 'purchase', player: 'G', item: 'stone_sword' }], 'G', plan, []).completed, 0);
  // per-tick rows
  const ticks = [{ t: 100, type: 'tick', arena: 'duel', tick: 1, p: [{ n: 'G', x: 1, y: 64, z: 2, vx: 4.3, vy: 0, vz: 0, og: 1, alive: 1, hp: 20 }, { n: 'B', x: 9, y: 64, z: 2, og: 0, alive: 1 }] },
    { t: 150, type: 'tick', arena: 'duel', tick: 2, p: [{ n: 'B', x: 9, y: 64, z: 2, og: 1, alive: 1 }] }];
  const tr = L.track(ticks, 'G');
  assert.strictEqual(tr.length, 1);
  assert.deepStrictEqual([tr[0].t, tr[0].x, tr[0].vx, tr[0].og, tr[0].alive, tr[0].hp], [100, 1, 4.3, true, true, 20]);
  assert.deepStrictEqual(L.track(ticks, 'B').map((r) => r.og), [false, true]);
});
