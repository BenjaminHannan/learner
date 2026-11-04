'use strict';
// T6 wiring in main.js: the watcher beside the guesser (string checks; the behaviour is in test/watcher.test.js).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

test('main: the watcher sees each second, wakes the loop, gets labels from ticks + outcomes, and trains at night', () => {
  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(main, /aoWatchSecond\(getGuesser\(\)\.observe\('app', SpeakMod\.categorize\(f\.app, f\.title\)\)\)/);
  assert.match(main, /if \(r\.wake && aoLoop && aoLoop\.wake\(\)/);
  assert.match(main, /function aoLoopContext\(fresh\) \{\n  try \{ aoWatchTickStart\(fresh\); \}/);
  assert.match(main, /aoWatchHook\(aoLoop\);/);
  assert.match(main, /if \(m\) aoWatchRef\('say:' \+ m\.id\); return m;/);
  assert.match(main, /aoWatchRef\('note:' \+ String\(text\)\.slice\(0, 200\)\)/);
  assert.match(main, /aoWatcher\(\)\.outcome\('say:' \+ m\.id, \['up', 'used', 'reply'\]\.includes\(kind\)\)/);
  assert.match(main, /aoWatcher\(\)\.outcome\('note:' \+ String\(n\.text\)\.slice\(0, 200\), n\.status === 'confirmed'\)/);
  assert.match(main, /aoNightlyJobs\.push\(\(\) => \{ if \(store\.getSettings\(\)\.watcher === false\) return; const w = aoWatcher\(\); w\.nightly\(\); w\.prune\(\); \}\);/);
});

test('main: the Sparks reflex practises while Ben is away and is distilled at night', () => {
  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(main, /const RealtimeMod = require\('\.\/src\/games\/realtime'\);/);
  assert.match(main, /if \(idleS < 120 \|\| !aoMoteGate\(\)\.budget\) return;/);
  assert.match(main, /aoNightlyJobs\.push\(\(\) => \{ if \(store\.getSettings\(\)\.reflexGames !== false\) aoReflex\(\)\.nightly\(\); \}\);/);
  assert.doesNotMatch(require('fs').readFileSync(path.join(__dirname, '..', 'src', 'games', 'index.js'), 'utf8'), /realtime/, 'Sparks stays out of the turn-based GAMES registry');
});
