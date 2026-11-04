'use strict';
// The little scientist's worlds that answer back: the puzzle generator (port of puzzle school + size/count/shape families) and
// the small rule-simulated games.
const test = require('node:test');
const assert = require('node:assert');
const P = require('../src/games/puzzles');
const { GAMES, play, winnerOf } = require('../src/games');

test('puzzles: every rule of every family makes unambiguous items whose answer its own rule predicts', () => {
  for (const f of P.FAMILIES) for (const rule of P.ALL[f]) {
    let made = 0;
    for (let s = 0; s < 15; s++) {
      const p = P.make(f, rule, s); if (!p) continue; made++;
      assert.strictEqual(p.family, f); assert.strictEqual(p.rule, rule); assert.ok(p.puzzle.length > 10 && p.answer.length > 0);
    }
    assert.ok(made >= 12, f + ' ' + rule + ' made ' + made + '/15');
  }
  assert.deepStrictEqual(P.make('A', 'reverse', 7), P.make('A', 'reverse', 7), 'seeded');
  assert.notDeepStrictEqual(P.make('A', 'reverse', 7), P.make('A', 'reverse', 8));
});

test('puzzles: the ambiguity guard and the train / held-out split match puzzle school (A-D) and add size, count, shape', () => {
  assert.deepStrictEqual(P.TRAIN.A, ['succ_last', 'extend', 'remove_double', 'reverse']);
  assert.deepStrictEqual(P.HELD.D, ['squares', 'fib', 'grow', 'minus_k']);
  for (const f of ['E', 'F', 'G']) { assert.ok(P.TRAIN[f].length >= 2 && P.HELD[f].length >= 2); for (const r of P.TRAIN[f]) assert.ok(!P.HELD[f].includes(r)); }
  // [1,2,3] -> [1,2,4]: succ_last; but extend would say [1,2,3,4]-> no; a shown part that two rules fit with different answers is rejected
  assert.strictEqual(P.ambiguousWith('D', 'plus_k', [2, 4, 6, 8, 10], 12), null);
  assert.strictEqual(P.ambiguousWith('D', 'cycle3', [1, 2, 3, 1, 2], 3), null);
  // count family: two examples pin the rule
  const g = P.make('F', 'count_colors', 3); assert.match(g.puzzle, /Example 2/);
  assert.ok(P.correct('0 0 0 / 0 7 7', '000/077'), 'spaces do not matter'); assert.ok(P.correct(' Answer: c b a.', 'c b a'));
  assert.ok(!P.correct('12', '1 2 3'));
});

test('games: deterministic rule simulators; step never mutates; each game can be won and lost', () => {
  for (const [name, g] of Object.entries(GAMES)) {
    const s = g.init(11), copy = JSON.stringify(s);
    const m = g.moves(s)[0]; const a = g.step(s, m), b = g.step(s, m);
    assert.strictEqual(JSON.stringify(s), copy, name + ': step did not mutate');
    assert.deepStrictEqual(a, b, name + ': deterministic');
    assert.strictEqual(typeof g.render(s), 'string'); assert.strictEqual(typeof g.stateText(a), 'string');
    assert.deepStrictEqual(g.parseMove(s, g.moveText(m)), m, name + ': moveText / parseMove round trip');
    const r = play(g, 3, (st) => g.moves(st)[0]); assert.ok([0, 0.5, 1].includes(r.result));
  }
  assert.strictEqual(winnerOf('XXXOO....'.split('')), 'X');
  assert.strictEqual(GAMES.maze.step({ grid: ['.#', '..'], pos: [0, 0], goal: [1, 1], steps: 0, limit: 5 }, 'right').pos.join(), '0,0', 'a wall: you stay put');
  const n = GAMES.nim.apply({ piles: [0, 0, 2], winner: null, seed: 1, ply: 0 }, { pile: 2, take: 2 }); assert.strictEqual(n.winner, 'me');
  assert.strictEqual(GAMES.nim.replies({ piles: [1, 1, 0], winner: null, seed: 1, ply: 0 }).length, 2);
});
