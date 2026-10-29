'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'), os = require('os'), path = require('path');
const S = require('../src/sleepsession');
test('a detached sleep retains its deadline, source and restore obligation on restart', (t) => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'sleep-session-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const file = path.join(dir, 'session.json');
  const run = { startedAt: 100000, wakeAt: 200000, startedAuto: true, assistantOff: true, sleepKey: 'night' };
  S.save(file, run);
  assert.deepEqual(S.reconcile(S.read(file), { sleeping: true, since: 100010 }), { version: 1, ...run });
  assert.equal(S.reconcile(S.read(file), { sleeping: true, since: 150000 }), null);
  assert.equal(S.reconcile(S.read(file), { sleeping: true, since: null }), null);
  assert.equal(S.reconcile(S.read(file), { sleeping: false }).assistantOff, true);
  S.clear(file); assert.equal(S.read(file), null);
});
