'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const os = require('os');
const path = require('path');
const P = require('../src/morning-prep');
const now = new Date(2026, 9, 30, 8);
test('chooses one due item, preferring today and ignoring finished or distant items', () => {
  const tracked = [{ what: 'tomorrow essay', until: '2026-10-31' }, { what: 'done', until: '2026-10-30', done: '2026-10-30' }, { what: 'later', until: '2026-11-01' }];
  assert.deepEqual(P.pick({ now, tracked, notes: [{ text: 'History assignment due 2026-10-30' }] }), { text: 'History assignment due 2026-10-30', due: '2026-10-30' });
  assert.equal(P.pick({ now, tracked: [{ what: 'later', until: '2026-11-02' }] }), null);
});
test('prepares once and expires the card next day', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'prep-test-')); const file = path.join(dir, 'prep.json');
  try {
    let calls = 0; const args = { file, now, tracked: [{ what: 'essay assignment', until: '2026-10-31' }], generate: async () => { calls++; return 'Outline: introduction and evidence'; } };
    assert.equal((await P.prepare(args)).text, 'Outline: introduction and evidence');
    assert.equal(await P.prepare(args), null); assert.equal(calls, 1);
    assert.equal(P.read(file, new Date(2026, 9, 31, 8)), null);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
test('does not create a card without a dated item or useful draft', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'prep-test-')); const file = path.join(dir, 'prep.json');
  try {
    assert.equal(await P.prepare({ file, now, notes: [{ text: 'has an assignment' }], generate: () => { throw Error('unexpected'); } }), null);
    assert.equal(await P.prepare({ file, now, tracked: [{ what: 'essay assignment', until: '2026-10-30' }], generate: () => '' }), null);
    assert.equal(fs.existsSync(file), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
