'use strict';
// Imagining ahead. Level 1: the speak-o-meter compares speak now vs wait ~5 min. Level 2: plan-then-act in the sandbox games.
// NOTE: level 2 here tests the PLANNER (propose -> imagine with the rulebook -> score -> act) with a random proposer, not Nanbeige.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const { SpeakOMeter } = require('../src/speakometer');
const I = require('../src/imagine');
const { GAMES } = require('../src/games');

test('imagine L1: defers in a scripted "Ben is about to take a break" case, then re-checks plainly; never defers urgent', () => {
  const m = new SpeakOMeter();
  // Ben is in a game (the meter is quiet there); the guesser expects him to leave the game soon (a break / the browser)
  const ctx = { cat: 'game', act: 'game', minsSinceSay: 240, urges: { share: 1 }, surprise: 0, stuckError: false, stuckPage: false };
  const guesser = { predict: () => ({ browser: 0.7, game: 0.3 }) };
  const fut = I.futures(ctx, { guesser, breakSoon: () => 0.6 });
  assert.ok(Math.abs(fut.reduce((a, f) => a + f.w, 0) - 1) < 1e-9);
  assert.ok(fut.some((f) => f.ctx.brk), 'the break is one of the imagined futures');
  const d = m.decideAhead(ctx, fut);
  assert.strictEqual(d.defer, true, 'wait: p now ' + d.p.toFixed(2) + ' vs later ' + d.pWait.toFixed(2));
  assert.strictEqual(d.speak, false); assert.ok(d.pWait >= d.p + 0.15 && d.pPass >= 0.5); assert.strictEqual(d.waitMs, 300000);
  // the re-check (after the wait) decides plainly: no lookahead, so it cannot defer for ever
  const later = m.decideAhead({ ...ctx, cat: 'code', act: 'active', minsSinceSay: 245 }, fut, { noLookahead: true });
  assert.strictEqual(later.defer, false); assert.strictEqual(later.speak, true);
  // urgent: never deferred, even when waiting looks better
  const u = m.decideAhead({ ...ctx, urgent: true }, fut);
  assert.strictEqual(u.defer, false);
  // nothing better ahead (he stays in the game, no break) -> no defer
  assert.strictEqual(m.decideAhead(ctx, I.futures(ctx, { guesser: { predict: () => ({ game: 1 }) } })).defer, false);
  // a moment that is already good is not delayed by a slightly better one
  const good = { cat: 'code', act: 'active', minsSinceSay: 60, urges: { share: 1 }, stuckError: true };
  assert.strictEqual(m.decideAhead(good, I.futures(good, { guesser: { predict: () => ({ code: 1 }) }, breakSoon: () => 0.5 })).defer, false);
});

test('imagine L2: plan-then-act beats act-at-once by >= 15 points on held-out game seeds (random proposer, rulebook imagination)', () => {
  const rows = [];
  for (const [name, g] of Object.entries(GAMES)) {
    let once = 0, planned = 0; const N = 60;
    for (let s = 7000; s < 7000 + N; s++) {   // held-out seeds: never used by the scientist's practice (seeds >= 100000)
      once += I.playGame(g, s, I.randomProposer(3, s), 'once').win ? 1 : 0;
      planned += I.playGame(g, s, I.randomProposer(3, s), 'plan', { depth: 2 }).win ? 1 : 0;
    }
    rows.push({ name, once: (100 * once) / N, plan: (100 * planned) / N });
  }
  const avg = (k) => rows.reduce((a, r) => a + r[k], 0) / rows.length;
  for (const r of rows) assert.ok(r.plan >= r.once + 15, r.name + ': plan ' + r.plan + '% vs once ' + r.once + '%');
  assert.ok(avg('plan') >= avg('once') + 15);
});

test('imagine L2: two-player imagination does not peek at the opponent (worst reply counts); the learned hook replaces the rulebook', () => {
  const g = GAMES.ttt;
  // X to move on X X . / O O . / . . . : square 3 wins at once, the planner takes it among the proposals
  const s = { board: 'XX.OO....', seed: 1, ply: 4, winner: null };
  const p = I.plan(g, s, [6, 2, 8], { depth: 1 });
  assert.strictEqual(p.move, 2); assert.strictEqual(p.value, 1); assert.strictEqual(p.source, 'rulebook');
  // a move that lets O win next is scored by O's best reply (0), not by what the seeded opponent would actually do
  const s2 = { board: 'X..OO....', seed: 1, ply: 3, winner: null };
  const v = I.moveValue(g, s2, 8, 1, {}); assert.strictEqual(v.v, 0);
  // the learned hook: when it predicts a state, that state is used (and the plan says so)
  let used = 0; const hook = (st, m) => { used++; return { ...st, board: 'XXX' + st.board.slice(3), winner: 'X' }; };
  const q = I.plan(g, s2, [8], { predictAfter: hook });
  assert.ok(used > 0); assert.strictEqual(q.source, 'learned');
});

test('imagine L2: the model proposer parses legal moves only (a fake model here)', async () => {
  const g = GAMES.nim; const s = g.init(4);
  const ask = async () => '{"moves": ["take 1 from pile 1", "take 9 from pile 2", "nonsense", "take 1 from pile 1"]}';
  const r = await I.modelProposer(ask, 3)(s, g);
  assert.deepStrictEqual(r.moves, [{ pile: 0, take: 1 }]);
  const bad = await I.modelProposer(async () => 'no json', 3)(s, g); assert.deepStrictEqual(bad.moves, []);
});

test('main: the speak-o-meter looks ahead before speaking (not for urgent), and the deferred say is re-checked plainly', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /aoMeter\.decideAhead\(/);
  assert.match(m, /function aoDeferredTick\(\)/);
  assert.match(m, /noLookahead: true/);
});
