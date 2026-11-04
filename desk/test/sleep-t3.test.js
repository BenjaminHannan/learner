'use strict';
// Sleep track T3 (2026-11-04): the learned world model (src/worldmodel.js + imagine o.world), learned shape keys and per-link
// pruning (src/patterns.js). Toy proofs live in ~/learner-ops/premonition-sleeplab-t3; these tests check the app wiring.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const WM = require('../src/worldmodel');
const I = require('../src/imagine');
const P = require('../src/patterns');
const S = require('./synth-days');
const { GAMES, rng } = require('../src/games');
const { Scientist } = require('../src/scientist');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sleep-t3-'));
const DAY = 86400000, T0 = new Date(2026, 9, 5).getTime();
function playLogged(log, g, seed, setNow, day) {
  const r = rng(seed * 31 + 7); let s = g.init(seed), n = 0;
  while (!g.done(s) && n < 80) { const ms = g.moves(s), m = ms[Math.floor(r() * ms.length)]; setNow(T0 + day * DAY + 9 * 3600000 + n * 1000); const s2 = g.step(s, m); log.addStep(g, s, m, s2); s = s2; n++; }
}

test('world model: counts from logs predict the rulebook; imagine plans with it (source learned) and falls back to the rulebook', () => {
  const W = new WM.WorldModel(); let now = 0; const log = new WM.GameLog({ now: () => now });
  for (let d = 1; d <= 16; d++) for (const g of Object.values(GAMES)) playLogged(log, g, 100000 + d, (t) => { now = t; }, d);
  W.learn(log.rows());
  const acc = W.score(WM.fixedChecks(GAMES)).acc; assert.ok(acc >= 0.9, 'fixed-check accuracy ' + acc);
  const g = GAMES.maze, s = g.init(7001), p = I.plan(g, s, g.moves(s), { depth: 2, world: W });
  assert.strictEqual(p.source, 'learned');
  // an empty model has no idea -> the rulebook
  const q = I.plan(g, s, g.moves(s), { depth: 1, world: new WM.WorldModel() }); assert.strictEqual(q.source, 'rulebook');
  // learned planning beats act-at-once on held-out seeds (toy mark: >= 70 % of the rulebook's gain)
  let once = 0, rule = 0, learned = 0;
  for (let sd = 7000; sd < 7040; sd++) {
    once += I.playGame(GAMES.tiles, sd, I.randomProposer(3, sd), 'once').win; rule += I.playGame(GAMES.tiles, sd, I.randomProposer(3, sd), 'plan', { depth: 2 }).win;
    learned += I.playGame(GAMES.tiles, sd, I.randomProposer(3, sd), 'plan', { depth: 2, world: W }).win;
  }
  assert.ok(learned - once >= 0.7 * (rule - once), 'tiles once ' + once + ' rule ' + rule + ' learned ' + learned);
});

test('world model nightly: kept on clean nights, rolled back when the candidate is worse on the held-out day; guard quarantines a poisoned day', () => {
  const dir = tmp(); let now = 0; const log = new WM.GameLog({ dir, now: () => now }); const set = (t) => { now = t; };
  for (let d = 1; d <= 6; d++) { for (const g of Object.values(GAMES)) playLogged(log, g, 100000 + d, set, d); now = T0 + d * DAY + 23 * 3600000; const r = WM.nightly({ dir, log, now: () => now }); if (d > 1) assert.strictEqual(r.kept, true, r.why); assert.match(r.line, /World model: /); }
  assert.ok(fs.existsSync(path.join(dir, 'worldmodel-log.jsonl')));
  // day 7: every logged move gets a wrong next state -> the guard quarantines it, the model on disk is unchanged
  const before = fs.readFileSync(path.join(dir, 'worldmodel.json'), 'utf8');
  for (const g of Object.values(GAMES)) playLogged(log, g, 100007, set, 7);
  const file = path.join(dir, 'game-log.jsonl'); const rows = fs.readFileSync(file, 'utf8').trim().split('\n').map(JSON.parse);
  for (const x of rows) if (x.t >= T0 + 7 * DAY && x.who === 'me') { const g = GAMES[x.game]; const alt = g.moves(x.s).find((m) => JSON.stringify(m) !== JSON.stringify(x.m)); if (alt != null) x.s2 = g.apply ? g.apply(x.s, alt) : g.step(x.s, alt); }
  fs.writeFileSync(file, rows.map((x) => JSON.stringify(x)).join('\n') + '\n');
  now = T0 + 7 * DAY + 23 * 3600000;
  const q = WM.nightly({ dir, log, now: () => now, guard: true });
  assert.ok(q.quarantined, q.why); assert.strictEqual(q.kept, false);
  assert.deepStrictEqual(JSON.parse(fs.readFileSync(path.join(dir, 'worldmodel.json'), 'utf8')).model, JSON.parse(before).model);
  // a candidate learned from bad OLDER days is worse on a clean latest day -> rolled back
  const dir2 = tmp(); let n2 = 0; const log2 = new WM.GameLog({ dir: dir2, now: () => n2 });
  fs.copyFileSync(path.join(dir, 'worldmodel.json'), path.join(dir2, 'worldmodel.json'));
  for (const x of rows.filter((y) => y.t >= T0 + 7 * DAY)) { n2 = x.t - 3 * DAY; log2.add(x); }   // the poisoned rows, as old days
  for (const g of Object.values(GAMES)) playLogged(log2, g, 100008, (t) => { n2 = t; }, 8);
  n2 = T0 + 8 * DAY + 23 * 3600000;
  const rb = WM.nightly({ dir: dir2, log: log2, now: () => n2 });
  assert.strictEqual(rb.kept, false); assert.match(rb.why, /worse/);
});

test('scientist game experiments are logged for the world model', () => {
  let now = T0; const log = new WM.GameLog({ now: () => now });
  const sci = new Scientist({ gameLog: log, now: () => now });
  for (let i = 0; i < 8; i++) sci.task('game:nim', 100000 + i);
  const rows = log.rows(); assert.ok(rows.length >= 8); assert.ok(rows.every((r) => r.game === 'nim' && r.s && r.s2));
});

test('patterns: a "what follows" link that stops coming true is switched off by next-day surprise; the true one stays', () => {
  let now = 0; const tl = new P.Timeline({ now: () => now }); const mk = S.maker(S.rng(5)); const r = S.rng(9);
  for (let d = 0; d < 14; d++) {
    for (let i = 0; i < 25; i++) tl.add({ t: T0 + d * DAY + (7 + r() * 15) * 3600000, text: S.filler(r, mk) });
    const a = T0 + d * DAY + 10 * 3600000, b = T0 + d * DAY + 15 * 3600000;
    tl.add({ t: a, text: 'Bus to ' + mk.name() + ' Station is running late' }); tl.add({ t: a + 20 * 60000, text: mk.name() + ' asked for a ride to ' + mk.name() + ' Mall' });
    tl.add({ t: b, text: 'Phone battery at ' + (5 + d) + ' percent' });
    if (d < 7) tl.add({ t: b + 15 * 60000, text: 'Plugged in the charger at ' + (3 + (d % 8)) + 'pm' });   // the battery routine breaks on day 7
    now = T0 + d * DAY + 23.5 * 3600000; tl.sleep({ shapeKeys: false });
  }
  const bus = tl.whatFollows('Bus to Zorp Station is running late'), bat = tl.patterns.find((p) => /battery/i.test(p.template));
  assert.ok(bus && bus.follow && /ride/.test(bus.follow.template), 'the true link stays');
  assert.ok(bat, 'battery pattern exists'); assert.ok(bat.follows.length && bat.follows.every((f) => f.dropped), JSON.stringify(bat.follows.map((f) => [f.template, f.score])));
  assert.ok(bat.quiet); assert.ok(!tl.patternsFor('Phone battery at 7 percent', { mark: false }).some((x) => x.p === bat));
  assert.ok(tl.lastSleep.links.dropped >= 1);
});

test('patterns: learned shape keys train in sleep with the seatbelt, are saved, and recall uses them', () => {
  const dir = tmp(); const d = S.patternDays(5, { days: 8 }); let now = S.T0 + 7 * S.DAY - 1;
  const tl = new P.Timeline({ dir, now: () => now, saveDelayMs: 0 });
  for (const it of d.items) if (it.t < now) tl.add({ t: it.t, text: it.text });
  assert.strictEqual(tl.sleep().shapeKeys, null, 'off by default');
  const r1 = tl.sleep({ shapeKeys: true }); assert.ok(r1.shapeKeys); assert.ok(r1.shapeKeys.old != null, JSON.stringify(r1.shapeKeys));
  assert.strictEqual(r1.shapeKeys.kept, r1.shapeKeys.new >= r1.shapeKeys.rule + 0.05 && r1.shapeKeys.new >= r1.shapeKeys.old - 0.02, 'seatbelt v3 rule');
  if (r1.shapeKeys.kept) {
    assert.ok(fs.existsSync(path.join(dir, 'shapekeys.json')));
    const tl2 = new P.Timeline({ dir, now: () => now }); assert.ok(tl2.proj, 'loaded on restart');
    const got = tl2.recall(d.planted[0].query, { k: 5 }); assert.ok(got.length > 0);
  }
  // a poisoned training set (every cluster replaced by random records) is rolled back when the check says it is worse
  const r2 = tl.sleep({ shapeKeys: true, mutateGroups: (groups, items) => { const rr = S.rng(3); for (const g of groups) for (let i = 0; i < g.length; i++) g[i] = items[Math.floor(rr() * items.length)]; } });
  assert.strictEqual(r2.shapeKeys.kept, false, 'fully poisoned clusters are rolled back');
});

test('main wires T3: game log to the scientist, the nightly world model, sleep-part diary lines', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /gameLog: aoGameLog\(\)/); assert.match(m, /WorldModelMod\.nightly\(/); assert.match(m, /'sleep-part'/);
  const D = require('../src/diary-ao');
  const txt = D.recap({ activity: [{ t: Date.now(), kind: 'sleep-part', part: 'worldmodel', line: 'World model: kept.' }], now: Date.now() + 1 });
  assert.match(txt, /World model: kept\./);
});
