'use strict';
const test = require('node:test');
const assert = require('node:assert');
const Acts = require('../renderer/acts');

test('stored fold choice: only an explicit 1/true collapses', () => {
  assert.strictEqual(Acts.parse('1'), true);
  assert.strictEqual(Acts.parse('true'), true);
  for (const v of [null, undefined, '', '0', 'false', 'junk']) assert.strictEqual(Acts.parse(v), false);
});

test('body attribute round-trips with the collapsed flag', () => {
  assert.strictEqual(Acts.attr(true), 'closed');
  assert.strictEqual(Acts.attr(false), 'open');
  assert.strictEqual(Acts.isCollapsed(Acts.attr(true)), true);
  assert.strictEqual(Acts.isCollapsed(Acts.attr(false)), false);
  assert.strictEqual(Acts.isCollapsed(undefined), false);
});
