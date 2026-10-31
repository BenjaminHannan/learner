'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs'), os = require('os'), path = require('path');
const { count } = require('../src/feature-usage');
test('counts only permitted events by local day without storing choice text', () => {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'usage-')), 'usage.json');
  const day = new Date(2026, 9, 30, 10);
  assert.equal(count(file, 'followup', day), true);
  count(file, 'followup', day); count(file, 'idea', day);
  assert.equal(count(file, 'private choice', day), false);
  assert.deepEqual(JSON.parse(fs.readFileSync(file)), { '2026-10-30': { followup: 2, idea: 1 } });
});
