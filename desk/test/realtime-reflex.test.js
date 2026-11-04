'use strict';
// T6: the real-time sandbox game (src/games/realtime.js) and its reflex fast path, distilled nightly from the slow planner.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const RT = require('../src/games/realtime');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'reflex-'));

test('sparks: deterministic per seed; the untimed planner beats the same planner arriving 8 frames late', () => {
  const a = RT.play(11, () => 0), b = RT.play(11, () => 0);
  assert.strictEqual(a.score, b.score);
  assert.ok(a.score >= 0 && a.score <= 100);
  let untimed = 0, late = 0;
  for (const sd of [1, 2, 3]) { untimed += RT.play(sd, (s) => RT.plan(s)).score; late += RT.play(sd, RT.latePlanner(8)).score; }
  assert.ok(untimed > late + 30, 'untimed ' + untimed / 3 + ' vs late ' + late / 3);
});

test('the 8 symmetries move the player exactly like the game does (labels can be replayed rotated / mirrored)', () => {
  let s = RT.sparks.init(5); for (let i = 0; i < 25; i++) s = RT.sparks.step(s, i % 5);
  for (let k = 0; k < 8; k++) for (let a = 0; a < 5; a++) {
    const t = RT.transform(s, a, k);
    assert.deepStrictEqual(RT.sparks.step(t.s, t.a).me, RT.transform(RT.sparks.step(s, a), 0, k).s.me);
    assert.ok(t.s.sparks.every((p) => p.h >= 0));
  }
});

test('reflex: no model = the late planner plays and frames are logged; a night distills a reflex that beats it; poison is rolled back', () => {
  const dir = tmp(); let now = new Date(2026, 10, 4, 14).getTime();
  const R = new RT.Reflex({ dir, now: () => now, cfg: { steps: 1500, valGames: 4 } });
  assert.strictEqual(R.ready(), false);
  for (let g = 0; g < 10; g++) R.playDay(100 + g);
  now += 86400000; for (let g = 0; g < 10; g++) R.playDay(200 + g);
  const n1 = R.nightly({ seed: 3 });
  assert.strictEqual(n1.kept, true, JSON.stringify(n1));
  assert.strictEqual(n1.against, 'late planner');
  assert.ok(n1.candVal > n1.curVal);
  assert.ok(R.ready() && new RT.Reflex({ dir, now: () => now }).ready(), 'the kept reflex is saved and reloads');
  // the reflex decides fast (the planner is the slow part)
  const s = RT.sparks.init(1), pol = R.policy(), t0 = process.hrtime.bigint(); for (let i = 0; i < 500; i++) pol(s);
  assert.ok(Number(process.hrtime.bigint() - t0) / 1e6 / 500 < 5, 'under 5 ms a decision');
  // a night whose new labels are ALL wrong is never kept
  now += 86400000; for (let g = 0; g < 10; g++) R.playDay(300 + g);
  const before = JSON.stringify(R.net.toJSON());
  const bad = R.nightly({ seed: 4, poison: 1 });
  assert.strictEqual(bad.kept, false, JSON.stringify(bad));
  assert.strictEqual(JSON.stringify(R.net.toJSON()), before);
  const log = fs.readFileSync(path.join(dir, 'reflex', 'nightly.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.strictEqual(log.length, 2);
  assert.ok(log[1].anchorAgree && log[1].anchorAgree.cand < log[1].anchorAgree.old);
});
