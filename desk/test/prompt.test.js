'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { SYSTEM_PROMPT, buildTools, promptSize } = require('../src/prompt');

test('system prompt + tool schemas stay under 9000 chars', () => {
  const n = SYSTEM_PROMPT.length + JSON.stringify(buildTools({ diary: true })).length;
  console.log('prompt+tools chars:', n, '(system', SYSTEM_PROMPT.length + ', tools ' + JSON.stringify(buildTools({ diary: true })).length + ')');
  assert.ok(n < 9000, 'too big: ' + n);
  assert.strictEqual(promptSize(), n);
});

test('tool list is constant; diary tool only when diary is available', () => {
  const a = buildTools({ diary: true }), b = buildTools({ diary: false });
  assert.strictEqual(a.length, 15); assert.strictEqual(b.length, 14);
  assert.ok(!b.some((t) => t.function.name === 'diary_search'));
  assert.strictEqual(JSON.stringify(buildTools({ diary: true })), JSON.stringify(a));
});

test('prompt has no per-chat content (no digits that look like dates or paths)', () => {
  assert.ok(!/\d{4}-\d{2}-\d{2}/.test(SYSTEM_PROMPT));
  assert.ok(!/\/Users\//.test(SYSTEM_PROMPT));
});
