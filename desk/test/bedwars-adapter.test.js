'use strict';
// Glim team, Bedwars side: the adapter for I3's two-speed core (same shape as src/games/adapters/sparksquest.js and orchard.js):
// interface, human-equivalent inputs, the hand rule (the reflex until sleep keeps a net), judge, timed targets, practice model.
const test = require('node:test');
const assert = require('node:assert');
const A = require('../src/games/bedwars/adapter');
const T = require('../src/games/bedwars/tactics');
const Timing = require('../src/games/bedwars/timing');
const Truth = require('../src/games/bedwars/truthlog');
const intent = require('../src/games/core/intent');

const call = (s) => intent.parse(A.vocab, s).call;
const obsAt = (o) => ({ t: 0, me: { x: 2, alive: true, hp: 20 }, inv: { iron: 0, gold: 0, wool: 0, shears: 0 }, atBase: true, bridgeLeft: 18, onEnemyIsland: false,
  edgeAhead: null, edgeRun: 0, enemy: null, enemyBed: { alive: true, covered: false }, myBedThreat: false, hits: 0, events: [], ...o });
const enemy = (dist, o) => ({ dist, ahead: true, alive: true, approach: 1, approachFrom: 8, ...o });

test('interface: everything I3\'s loop (core/loop.js) and the live loop (core-iface.js) use', () => {
  for (const k of ['name', 'tickMs', 'maxTicks', 'vocab', 'nIn', 'nA', 'goal']) assert.ok(A[k] != null, k);
  for (const f of ['init', 'observe', 'planner', 'judge', 'fallback', 'fallbackRaw', 'rawFrame', 'features', 'nightLabel', 'timedTargets', 'step', 'done', 'outcome', 'describe',
    'repair', 'urgent', 'interrupted', 'stepsFromCalls']) assert.strictEqual(typeof A[f], 'function', f);
  assert.strictEqual(A.vocab, T.vocab); assert.strictEqual(A.nA, A.MOVES.length); assert.strictEqual(A.tickMs, 50);
  assert.ok(A.frameToKeyMs <= 38, 'no handicap: ~38 ms frame-to-keys is the bar');
  assert.strictEqual(A.CRIT_MID_MS, Timing.CRIT_MID_MS); assert.deepStrictEqual(A.CRIT_WINDOW, Timing.CRIT_WINDOW_MS);
  // the stand-in brain plans with real calls from the vocabulary
  const s = A.init(1), plan = A.planner(A.observe(s, 0), []);
  assert.ok(plan.length >= 3); for (const st of plan) assert.ok(intent.validate(A.vocab, st.call).ok, st.id);
});

test('inputs: human-equivalent only (no minimap, reach display, freelook, coords or truth; FOV <= 110; one view)', () => {
  assert.ok(A.validateObs({ frame: { fov: 100, view: 'first' }, hud: { hp: 20, hotbar: [], scoreboard: [], tnt_timer: 3 }, sound: [], t: 1 }).ok);
  assert.ok(A.validateObs({ frame: { view: 'f5' } }).ok);
  for (const bad of [{ hud: { minimap: 1 } }, { hud: { reach: 3.1 } }, { hud: { freelook: true } }, { hud: { coords: [1, 2, 3] } }, { hud: { radar: [] } },
    { frame: { fov: 120 } }, { frame: { view: 'both' } }, { truth: {} }, { entities: [] }, null]) assert.ok(!A.validateObs(bad).ok, JSON.stringify(bad));
  // what the practice model shows Glim: no positions of the enemy, only my estimate of his distance; never the truth
  const s = A.init(2); s.me.x = 20; const o = A.observe(s, 0);
  assert.ok(!JSON.stringify(o).includes('truth'));
  assert.deepStrictEqual(Object.keys(o.enemy || {}).sort(), o.enemy ? ['ahead', 'alive', 'approach', 'approachFrom', 'dist'] : []);
});

test('rawFrame / features: fixed length, finite, and features never read the truth', () => {
  const s = A.init(3); s.me.x = 20;
  const o = A.observe(s, 0), c = call('BRIDGE'), withTruth = A.rawFrame(o, c, s), plain = A.rawFrame(o, c);
  assert.ok(withTruth.truth && !plain.truth);
  const f1 = A.features(withTruth), f2 = A.features(plain);
  assert.strictEqual(f1.length, A.nIn); assert.ok(f1.every(Number.isFinite)); assert.deepStrictEqual(Array.from(f1), Array.from(f2));
  assert.notDeepStrictEqual(Array.from(A.features(A.rawFrame(o, call('HOME')))), Array.from(f2), 'the call is an input');
});

test('hand rule (the reflex): hits whoever is in reach whatever the call; otherwise does the call; same on logged frames', () => {
  const M = (m) => A.MOVES.indexOf(m);
  const near = obsAt({ me: { x: 15, alive: true, hp: 20 }, atBase: false, inv: { wool: 10 }, enemy: enemy(2.6) });
  for (const c of ['BRIDGE', 'BREAK_BED', 'GET', 'BUY item=wool', 'HOLD', 'DEFEND', 'FIGHT']) assert.strictEqual(A.fallback(near, call(c)), M('attack'), c);
  assert.strictEqual(A.fallback(near, call('RETREAT')), M('back')); assert.strictEqual(A.fallback(near, call('HOME')), M('back'));
  assert.strictEqual(A.fallback(near, null), M('attack'), 'no call yet: still fights back');
  assert.strictEqual(A.fallback(obsAt({ inv: { iron: 8 } }), call('BUY item=wool')), M('buy:wool'));
  assert.strictEqual(A.fallback(obsAt({ me: { x: 10, alive: true, hp: 20 }, atBase: false }), call('GET')), M('back'));
  assert.strictEqual(A.fallback(obsAt({ inv: { wool: 5 } }), call('BRIDGE')), M('bridge'));
  assert.strictEqual(A.fallback(obsAt({ bridgeLeft: 0 }), call('BRIDGE')), M('forward'));
  // FIGHT across an unfinished bridge: keep bridging toward him (walking would stop at the bridge's end)
  assert.strictEqual(A.fallback(obsAt({ me: { x: 21, alive: true, hp: 20 }, atBase: false, bridgeLeft: 3, inv: { wool: 9 }, enemy: enemy(4.5) }), call('FIGHT')), M('bridge'));
  assert.strictEqual(A.fallback(obsAt({ me: { x: 0, alive: false, hp: 0 } }), call('FIGHT')), M('stay'));
  for (const o of [near, obsAt({ inv: { iron: 8 } }), obsAt({ bridgeLeft: 0 })]) for (const c of ['BRIDGE', 'BUY item=wool', 'RETREAT']) assert.strictEqual(A.fallbackRaw(A.rawFrame(o, call(c))), A.fallback(o, call(c)));
});

test('night labeller uses the truth log (hindsight): my estimate said out of reach, the truth said hit', () => {
  const o = obsAt({ me: { x: 15, alive: true, hp: 20 }, atBase: false, inv: { wool: 10 }, enemy: enemy(3.4) });
  const raw = A.rawFrame(o, call('BRIDGE'));
  assert.strictEqual(A.fallbackRaw(raw), A.MOVES.indexOf('bridge'));
  assert.strictEqual(A.nightLabel({ ...raw, truth: { eDist: 2.8 } }), A.MOVES.indexOf('attack'));
  assert.strictEqual(A.nightLabel({ ...raw, truth: { eDist: 3.6 } }), A.MOVES.indexOf('bridge'));
  assert.strictEqual(A.nightLabel({ ...raw, call: null }), null, 'no call: no label');
});

test('timed targets: jump-crit 450 ms ahead of his entering reach; a jump at the end of the finished bridge', () => {
  const far = obsAt({ me: { x: 14, alive: true, hp: 20 }, atBase: false, enemy: enemy(7) });
  const t1 = A.timedTargets(far, call('BRIDGE'));
  assert.deepStrictEqual(t1, [{ id: 'crit:1', action: 'jump_crit', lagMs: Timing.CRIT_MID_MS, gap: 4 }]);
  assert.deepStrictEqual(A.timedTargets(far, call('RETREAT')), [], 'no crit jump while backing off');
  assert.deepStrictEqual(A.timedTargets(obsAt({ enemy: enemy(4, { approachFrom: 1 }) }), call('FIGHT')), [], 'too short an approach to time a jump');
  assert.deepStrictEqual(A.timedTargets(obsAt({ enemy: enemy(2.5) }), call('FIGHT')), [], 'already in reach');
  const edge = obsAt({ me: { x: 21, alive: true, hp: 20 }, atBase: false, bridgeLeft: 0, edgeAhead: 3, edgeRun: 5 });
  for (const c of ['BRIDGE', 'BREAK_BED', 'FIGHT']) assert.deepStrictEqual(A.timedTargets(edge, call(c)), [{ id: 'edge:5', action: 'jump_gap', lagMs: 50, gap: 3 }], c);
  for (const c of ['GET', 'HOME', 'HOLD']) assert.deepStrictEqual(A.timedTargets(edge, call(c)), [], c);
  assert.deepStrictEqual(A.timedTargets({ ...edge, me: { alive: false } }, call('BRIDGE')), []);
});

test('judge: done / going / blocked per step kind, so plan memory advances by itself', () => {
  const st = (k, o) => T.makeStep(k, o);
  assert.strictEqual(A.judge(st('get_resources', { res: 'iron', n: 8 }), obsAt({ inv: { iron: 8 } })).status, 'done');
  assert.strictEqual(A.judge(st('get_resources', { res: 'iron', n: 8 }), obsAt({ inv: { iron: 3 } })).status, 'going');
  assert.strictEqual(A.judge(st('buy_blocks'), obsAt({ events: ['bought:wool'] })).status, 'done');
  assert.strictEqual(A.judge(st('buy', { item: 'shears' }), obsAt({ inv: { iron: 3 } })).status, 'blocked');
  assert.strictEqual(A.judge(st('buy', { item: 'shears' }), obsAt({ inv: { shears: 1 } })).status, 'done', 'a permanent item owned');
  assert.strictEqual(A.judge(st('bridge'), obsAt({ onEnemyIsland: true, bridgeLeft: 0 })).status, 'done');
  assert.strictEqual(A.judge(st('bridge'), obsAt({ me: { x: 12, alive: true, hp: 20 }, atBase: false, bridgeLeft: 8, inv: { wool: 0 } })).status, 'blocked');
  const cov = obsAt({ me: { x: 29, alive: true, hp: 20 }, atBase: false, onEnemyIsland: true, bridgeLeft: 0, enemyBed: { alive: true, covered: true } });
  assert.match(A.judge(st('break_bed'), cov).why, /shears/);
  assert.strictEqual(A.judge(st('break_bed'), { ...cov, enemyBed: { alive: false } }).status, 'done');
  assert.strictEqual(A.judge(st('fight'), obsAt({ enemy: enemy(T.DONE_RANGE + 1) })).status, 'done');
  assert.strictEqual(A.judge(st('fight'), obsAt({ enemy: enemy(2) })).status, 'going');
  assert.deepStrictEqual(A.judge(st('bridge'), obsAt({ me: { x: 2, alive: false, hp: 0 } })), { status: 'going' }, 'dead: no progress number, so no false "stalled"');
  assert.strictEqual(A.interrupted(obsAt({ events: ['hurt', 'died'] })), 'died'); assert.strictEqual(A.interrupted(obsAt()), null);
  const steps = A.stepsFromCalls([call('BUY item=wool'), call('BUY item=wool'), call('BRIDGE')]);
  assert.deepStrictEqual(steps.map((s) => s.id), ['buy_blocks', 'buy_blocks#2', 'bridge']);
});

test('practice model: deterministic; an untimed walk off the bridge falls, a timed jump crosses; death keeps only permanent items', () => {
  const M = (m) => A.MOVES.indexOf(m);
  const run = (seed, moves) => { let s = A.init(seed); for (let i = 0; i < moves.length; i++) s = A.step(s, moves[i], [], i * 50).state; return s; };
  const mv = Array.from({ length: 60 }, (_, i) => (i < 20 ? M('stay') : M('back')));
  assert.deepStrictEqual(run(5, mv), run(5, mv));
  // stand at the end of a finished bridge
  const base = () => { const s = A.init(1, { covered: false }); s.front = A.P.FRONT_DONE; s.me.x = A.P.FRONT_DONE - 1; s.inv = { iron: 5, gold: 0, wool: 9, shears: 1 }; s.enemy.alive = false; s.enemy.respawnAt = 1e9; return s; };
  let s = base(), t = 0, out;
  for (let i = 0; i < 6 && s.me.alive; i++, t += 50) { out = A.step(s, M('forward'), [], t); s = out.state; }
  assert.strictEqual(s.me.alive, false); assert.strictEqual(s.stats.edgeFalls, 1); assert.deepStrictEqual([s.inv.iron, s.inv.wool, s.inv.shears], [0, 0, 1]);
  // the same walk with the jump fired on time crosses
  s = base(); t = 0; let crossed = false;
  for (let i = 0; i < 6; i++, t += 50) {
    const fired = i === 3 ? [{ id: 'edge:0', action: 'jump_gap', atMs: t }] : [];
    out = A.step(s, M('forward'), fired, t); s = out.state; if (out.contacts.length) assert.strictEqual(out.contacts[0].id, 'edge:0');
    if (s.stats.crossings) { crossed = true; break; }
  }
  assert.ok(crossed && s.me.alive && s.me.x >= A.P.ENEMY_EDGE, 'timed jump crossed the gap');
  assert.ok(A.done({ ...s, bedAlive: false }, 0)); assert.strictEqual(A.outcome({ ...s, bedAlive: false }).goalDone, true);
});

test('describe: the picture in words for the slow brain (OWN vs ENEMY spelled out)', () => {
  const d = A.describe(obsAt({ inv: { iron: 4, wool: 16, shears: 1 }, enemy: enemy(6), enemyBed: { alive: true, covered: true } }));
  assert.match(d, /YOUR OWN island/); assert.match(d, /4 iron, 16 wool, shears/); assert.match(d, /Enemy player about 6 blocks ahead/); assert.match(d, /covered in wool/);
  assert.match(A.describe(obsAt({ me: { alive: false, hp: 0, x: 0 } })), /dead/);
});

test('sleep data comes from the truth log only (rewards, hindsight labels, goal score, cards); no night play', () => {
  const ev = [{ t: 1000, type: 'hit', attacker: 'GlimBot', victim: 'B' }, { t: 2000, type: 'hit', attacker: 'B', victim: 'GlimBot' }];
  const day = { events: ev, calls: ['FIGHT'], frames: [{ t: 900 }, { t: 1000 }] };
  assert.strictEqual(A.sleepData.nightPlay, false);
  assert.deepStrictEqual(A.sleepData.rewards(day), Truth.rewards(ev, 'GlimBot'));
  assert.deepStrictEqual(A.sleepData.labels(day), Truth.hindsight([900, 1000], ev, 'GlimBot'));
  assert.deepStrictEqual(A.sleepData.goal(day), Truth.goalScore(ev, 'GlimBot', T.RUSH_PLAN, undefined));
  assert.deepStrictEqual(A.sleepData.cards(day), Truth.cards(['FIGHT'], ev, 'GlimBot'));
});
