'use strict';
// Task B wiring in main.js: feeling time + patterns (string checks; the real-path check is test/realpath/drive-time.js).
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');

test('main: time questions get a hidden note only when asked; the loop gets context(); the when-model is on', () => {
  const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(main, /const timeNote = !goals && !learn && !diary \? aoTimeNote\(text\) : '';/);
  assert.match(main, /if \(!aoState \|\| !\(TimeSense\.isTimeAsk\(t\) \|\| PATTERN_ASK\.test\(t\)\)\) return '';/);
  assert.match(main, /context: \(fresh\) => aoLoopContext\(fresh\)/);
  assert.match(main, /new GuesserMod\.Guesser\(\{ saved, when: true,/);
  assert.match(main, /aoNightlyJobs\.push\(\(\) => aoPatternSleep\(\)\);/);
});
