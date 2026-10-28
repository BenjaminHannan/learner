'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { rate, record } = require('../src/feedback');

test('feedback: marks the matching answer, finds its request, clears with 0; the log is one JSON line per click', () => {
  const t = { items: [{ t: 'user', text: 'plan my week' }, { t: 'assistant', text: 'Plan:\n1. Look' }, { t: 'step' }, { t: 'assistant', text: 'Here is  your week.' },
    { t: 'user', text: 'thanks' }, { t: 'assistant', text: 'Anytime!' }] };
  assert.deepStrictEqual(rate(t, 'Here is your week.', 1), { user: 'plan my week', answer: 'Here is  your week.' });
  assert.strictEqual(t.items[3].fb, 1);
  assert.strictEqual(rate(t, 'Anytime!', -1).user, 'thanks'); assert.strictEqual(t.items[5].fb, -1);
  rate(t, 'Anytime!', 0); assert.ok(!('fb' in t.items[5]));
  assert.strictEqual(rate(t, 'not shown', 1), null);
  assert.strictEqual(rate(t, 'Anytime!', 2), null);
  assert.strictEqual(rate(null, 'x', 1), null);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fb-'));
  record(dir, { fb: 1, user: 'a', answer: 'b' }); record(dir, { fb: 0, user: 'a', answer: 'b' });
  const lines = fs.readFileSync(path.join(dir, 'feedback.jsonl'), 'utf8').trim().split('\n').map((l) => JSON.parse(l));
  assert.deepStrictEqual(lines.map((l) => l.fb), [1, 0]);
});
