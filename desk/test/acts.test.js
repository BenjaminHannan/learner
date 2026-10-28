'use strict';
const test = require('node:test');
const assert = require('node:assert');
const Acts = require('../renderer/acts');

test('stored fold choice: collapsed by default, only an explicit 0/false expands', () => {
  assert.strictEqual(Acts.parse('0'), false);
  assert.strictEqual(Acts.parse('false'), false);
  for (const v of [null, undefined, '', '1', 'true', 'junk']) assert.strictEqual(Acts.parse(v), true);
});

test('body attribute round-trips with the collapsed flag', () => {
  assert.strictEqual(Acts.attr(true), 'closed');
  assert.strictEqual(Acts.attr(false), 'open');
  assert.strictEqual(Acts.isCollapsed(Acts.attr(true)), true);
  assert.strictEqual(Acts.isCollapsed(Acts.attr(false)), false);
  assert.strictEqual(Acts.isCollapsed(undefined), false);
});
