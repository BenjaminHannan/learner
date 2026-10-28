'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { parseRefusal, parseWatchdog } = require('../src/startlog');

test('startlog: a "not starting" line becomes a memory refusal with the numbers', () => {
  const r = parseRefusal('loading\n2026-10-27 23:25:19 autostart: not starting (only about 14 GB of memory is free, need about 20)\n');
  assert.strictEqual(r.reason, 'memory');
  assert.match(r.error, /^Not enough free memory to start the assistant right now \(about 14 GB free, it needs about 20\)\. Close some apps and try again\.$/);
});

test('startlog: a refusal with another reason still reads plainly; a normal log is not a refusal', () => {
  const r = parseRefusal('2026-10-27 23:25:19 autostart: not starting (another job is running)');
  assert.strictEqual(r.reason, 'other');
  assert.match(r.error, /another job is running/);
  assert.strictEqual(parseRefusal('another serve.sh is already running; not starting a second one.'), null);
  assert.strictEqual(parseRefusal('model loaded\nlistening on 8090'), null);
  assert.strictEqual(parseRefusal(''), null);
  assert.strictEqual(parseRefusal(undefined), null);
});

test('startlog: WATCHDOG_STOPPED gives the time of day', () => {
  const w = parseWatchdog('2026-10-27 22:25:45 stopped by watchdog: pressure 2, swap 3396 MB\n');
  assert.strictEqual(w.at, '22:25');
  assert.match(w.text, /stopped by watchdog/);
  assert.strictEqual(parseWatchdog('2026-10-27 9:05:01 stopped by watchdog').at, '09:05');
  assert.strictEqual(parseWatchdog('stopped by watchdog').at, '');
  assert.strictEqual(parseWatchdog('').at, '');
});
