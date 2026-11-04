'use strict';
// Glim team, Bedwars side: the tactical vocabulary (src/games/bedwars/tactics.js) and plan-level replan triggers.
const test = require('node:test');
const assert = require('node:assert');
const T = require('../src/games/bedwars/tactics');

test('every code round-trips: canonical text -> parse -> the same call -> the same text', () => {
  const samples = { st: [{ dir: 'l', wtap: true }, { dir: 'r', wtap: false }], wt: [{}], stap: [{}], jc: [{ at: 3 }, { at: 2.5 }], jr: [{}], bh: [{}], hs: [{}], cb: [{}],
    bo: [{ d: 4 }], br: [{ n: 2 }, { n: 64 }], jg: [{}], rb: [{}], buy: T.ITEMS.map((item) => ({ item })), get: T.RESOURCES.map((res) => ({ res, n: 24 })), bb: [{}], db: [{}] };
  assert.deepStrictEqual(Object.keys(samples).sort(), T.CODES.slice().sort(), 'every code has a sample');
  for (const [code, list] of Object.entries(samples)) for (const params of list) {
    const v = T.validate({ code, params }); assert.ok(v.ok, code + ' ' + JSON.stringify(params) + ': ' + v.error);
    const text = T.toText(v.call), back = T.parse(text);
    assert.ok(back.ok, text + ': ' + back.error);
    assert.deepStrictEqual(back.calls, [v.call]);
    assert.strictEqual(T.lineText(back.calls), text);
    assert.ok(text.split(' ').length <= 3, 'a few tokens: ' + text);
  }
});

test('long names and plan wording parse to the same short codes; chains keep their order', () => {
  const same = [['strafe left wtap', 'st l w'], ['jump_crit(3)', 'jc 3'], ['jump-crit 3 blocks', 'jc 3'], ['block_hit', 'bh'], ['sprint_reset', 'wt'],
    ['bridge 2 then jump_gap', 'br 2; jg'], ['br 2; jg', 'br 2; jg'], ['get gold', 'get gold 16'], ['back_off', 'bo 3'], ['BUY Wool', 'buy wool']];
  for (const [a, b] of same) { const p = T.parse(a); assert.ok(p.ok, a + ': ' + p.error); assert.strictEqual(T.lineText(p.calls), b, a); }
});

test('validation refuses bad calls with a plain reason', () => {
  const bad = { '': /empty/, 'fly up': /unknown code/, 'br 0': /1\.\.64/, 'br 2.5': /whole number/, 'br x': /number/, 'buy rod': /item must be/, 'st up': /dir/,
    'jc 9': /0\.5\.\.6/, 'bh 3': /too many/, 'br 1; br 1; br 1; br 1': /at most 3/ };
  for (const [s, re] of Object.entries(bad)) { const p = T.parse(s); assert.strictEqual(p.ok, false, s); assert.match(p.error, re, s); }
  assert.strictEqual(T.validate({ code: 'br', params: {} }).ok, false, 'missing required n');
  assert.strictEqual(T.validate({ code: 'st', params: { dir: 'l', speed: 2 } }).ok, false, 'unknown param');
  assert.throws(() => T.toText({ code: 'nope' }));
});

test('the prompt card lists every code once and stays short', () => {
  const card = T.promptCard();
  for (const c of T.CODES) assert.ok(card.split('\n').some((l) => l.startsWith(c + ' ') || l.startsWith(c + ' =')), c);
  assert.ok(card.length < 1400, 'card length ' + card.length);
  assert.strictEqual(T.promptCard(), card, 'stable text (caches)');
});

test('plan steps map to calls; replan triggers fire on knock-off, low HP, bed attack and step timeout', () => {
  assert.deepStrictEqual(T.RUSH_PLAN, ['get_resources', 'buy_blocks', 'bridge', 'break_bed']);
  for (const s of T.RUSH_PLAN) assert.ok(T.validate(T.PLAN_STEPS[s].call()).ok, s);
  assert.deepStrictEqual(T.replanTriggers({ hp: 20, step: 'bridge', stepStartedAt: 0, now: 1000 }), []);
  assert.deepStrictEqual(T.replanTriggers({ knockedOff: true }), ['knocked_off']);
  assert.deepStrictEqual(T.replanTriggers({ hp: 5 }), ['low_hp']);
  assert.deepStrictEqual(T.replanTriggers({ bedUnderAttack: true }), ['bed_under_attack']);
  assert.deepStrictEqual(T.replanTriggers({ step: 'bridge', stepStartedAt: 0, now: 60001 }), ['step_timeout']);
  assert.deepStrictEqual(T.replan(['bed_under_attack'], 'bridge').slice(0, 2), ['return_base', 'defend_bed']);
  assert.deepStrictEqual(T.replan(['knocked_off'], 'bridge'), T.RUSH_PLAN);
  assert.deepStrictEqual(T.replan(['step_timeout'], 'bridge'), ['buy_blocks', 'bridge', 'break_bed']);
  assert.strictEqual(T.replan([], 'bridge'), null);
});

// I3's core (src/games/core/intent.js) is built in parallel; when it is there, its own validator must accept every canonical call
const fs = require('fs');
const path = require('path');
const I3 = path.join(__dirname, '..', 'src', 'games', 'core', 'intent.js');
test('the vocabulary in the I3 core format: its validator accepts every canonical call', { skip: !fs.existsSync(I3) && 'I3 core not present' }, () => {
  const { validate } = require(I3), vocab = T.coreVocab();
  for (const line of ['st l w', 'st r', 'wt', 'jc 2.5', 'bh', 'bo 4', 'br 12', 'jg', 'buy iron_sword', 'get emerald 2', 'bb', 'db']) {
    const c = T.parse(line).calls[0], r = validate(vocab, T.toCoreCall(c));
    assert.ok(r.ok, line + ': ' + r.why);
    assert.deepStrictEqual(r.call, T.toCoreCall(c), line);
  }
  assert.strictEqual(validate(vocab, { code: 'br', args: { n: 0 } }).ok, false);
});
