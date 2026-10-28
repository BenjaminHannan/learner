'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { parseChoices } = require('../renderer/choices');

test('choices: trailing arrow lines become chips, the text keeps the rest', () => {
  const r = parseChoices('Your order is late.\n\n→ Check the tracking\n-> Email the seller\n→ Leave it\n');
  assert.deepStrictEqual(r.choices, ['Check the tracking', 'Email the seller', 'Leave it']);
  assert.strictEqual(r.text, 'Your order is late.');
});
test('choices: an arrow line in the middle stays text', () => {
  const raw = 'Steps:\n→ first thing\nThen more words.';
  const r = parseChoices(raw);
  assert.deepStrictEqual(r.choices, []);
  assert.strictEqual(r.text, raw);
});
test('choices: at most 4, none for empty or a lone arrow', () => {
  assert.strictEqual(parseChoices('x\n→ a\n→ b\n→ c\n→ d\n→ e').choices.length, 4);
  assert.deepStrictEqual(parseChoices(''), { text: '', choices: [] });
  assert.deepStrictEqual(parseChoices(null).choices, []);
  assert.deepStrictEqual(parseChoices('hi\n→').choices, []);
});
