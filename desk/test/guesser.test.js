'use strict';
// Always-on v2 phase 3: the tiny guesser and Bayesian surprise (KL between beliefs after and before an observation).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const G = require('../src/guesser');

let seed = 7; const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
const t0 = new Date(2026, 10, 4, 0, 0, 0).getTime();   // midnight: hours 0-5 are one part of the day

test('special functions and the Dirichlet KL are right', () => {
  assert.ok(Math.abs(G.lgamma(5) - Math.log(24)) < 1e-9);
  assert.ok(Math.abs(G.lgamma(0.5) - Math.log(Math.sqrt(Math.PI))) < 1e-9);
  assert.ok(Math.abs(G.digamma(1) + 0.5772156649015329) < 1e-9);
  assert.strictEqual(G.klDirichlet([1, 2, 3], [1, 2, 3]), 0);
  assert.ok(G.klDirichlet([2, 1], [1, 1]) > 0);
});

test('a uniform-random stream stops being surprising (< 10% of its first hour) while a new regime spikes it > 5x', () => {
  const g = new G.Guesser({ cooldownMs: 0 });
  const four = ['code', 'browser', 'docs', 'chat'];
  const hourly = [];
  for (let h = 0; h < 5; h++) { let s = 0; for (let i = 0; i < 3600; i++) s += g.observe('app', four[Math.floor(rnd() * 4)], t0 + (h * 3600 + i) * 1000).kl; hourly.push(s / 3600); }
  const first = hourly[0], last = hourly[4];
  assert.ok(last < first * 0.1, 'hour 5 mean ' + last + ' vs hour 1 mean ' + first);
  // the random source is still random: raw prediction error stays high (p of each category ~ 0.25), but surprise ~ 0
  const p = g.predict('app', t0 + 5 * 3600 * 1000); assert.ok(Math.abs(p.code - 0.25) < 0.05, 'still a ~uniform belief');
  // a new regime: games and videos it never saw
  const spike = g.observe('app', 'game', t0 + 5 * 3600 * 1000 + 1).kl;
  assert.ok(spike > 5 * first, 'spike ' + spike + ' vs first-hour mean ' + first);
  assert.ok(spike > 100 * last);
  assert.ok(spike >= G.BIG, 'counts as a big surprise');
});

test('the steady stream crossing into a new part of the day stays unsurprising (backoff borrows the old counts)', () => {
  const g = new G.Guesser({ cooldownMs: 0 });
  const two = ['code', 'browser'];
  for (let i = 0; i < 6 * 3600; i++) g.observe('app', two[Math.floor(rnd() * 2)], t0 + i * 1000);
  let mx = 0; for (let i = 0; i < 600; i++) mx = Math.max(mx, g.observe('app', two[Math.floor(rnd() * 2)], t0 + (6 * 3600 + i) * 1000).kl);
  assert.ok(mx < G.BIG / 5, 'largest surprise after 06:00 = ' + mx);
});

test('big surprises call onBig (wake + file), with a per-stream cooldown; small ones do not', () => {
  let t = t0; const big = [];
  const g = new G.Guesser({ now: () => t, onBig: (s) => big.push(s) });
  for (let i = 0; i < 600; i++) { t += 1000; g.observe('app', 'code'); }
  const n0 = big.length;
  t += 1000; g.observe('app', 'code'); assert.strictEqual(big.length, n0, 'the usual thing is not filed');
  t += 1000; g.observe('app', 'game'); assert.strictEqual(big.length, n0 + 1);
  assert.strictEqual(big[big.length - 1].stream, 'app'); assert.strictEqual(big[big.length - 1].cat, 'game');
  t += 1000; g.observe('app', 'video'); assert.strictEqual(big.length, n0 + 1, 'cooldown: one per minute per stream');
  assert.ok(g.level() > 0.5);
  t += 130000; assert.strictEqual(g.level(), 0, 'the surprise feature fades');
});

test('screen and sound streams, saved state, nightly decay', () => {
  assert.strictEqual(G.screenCategory('TypeError: x is undefined'), 'error');
  assert.strictEqual(G.screenCategory('const a = () => {}'), 'code');
  assert.strictEqual(G.soundCategory('Heard: ♪ la la ♪'), 'music');
  assert.strictEqual(G.soundCategory('Heard: can you pass the salt'), 'speech');
  const g = new G.Guesser();
  for (let i = 0; i < 50; i++) g.observeEntry({ sense: 'screen', text: 'const x = 1;', t: t0 + i * 1000 });
  const g2 = new G.Guesser({ saved: JSON.parse(JSON.stringify(g.toJSON())) });
  assert.deepStrictEqual(g2.predict('screen', t0 + 60000), g.predict('screen', t0 + 60000));
  const before = g2.predict('screen', t0 + 60000).code; g2.decay(0.5);
  assert.ok(g2.predict('screen', t0 + 60000).code <= before);
});

test('fact guesses: a confident wrong guess is a surprise for the wonder list', () => {
  assert.deepStrictEqual(G.factSurprise(0.9, false).wonder, true);
  assert.ok(G.factSurprise(0.9, false).surprise > G.factSurprise(0.9, true).surprise);
  assert.strictEqual(G.factSurprise(0.4, false).wonder, false);
});

test('main ticks the guesser ~1 s on the front app, feeds screen/sound, and big surprises wake a tick and are filed', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /getGuesser\(\)\.observe\('app', SpeakMod\.categorize\(/);
  assert.match(m, /getGuesser\(\)\.observeEntry\(e\)/);
  assert.match(m, /onBig: \(s\) => aoOnSurprise\(s\)/);
  assert.match(m, /aoLoop\.wake\(\)/);
  assert.match(m, /aoState\.addSurprise\(/);
});
