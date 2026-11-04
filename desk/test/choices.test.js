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

test('a long chip is kept whole (Ben Nov 4: it was cut mid-word at 80 characters) and the chip wraps', () => {
  const { parseChoices } = require('../renderer/choices');
  const long = "Which of these (or others) resonate with you? Pick 1–3 and I'll save each as a goal for you.";
  assert.deepStrictEqual(parseChoices('Some ideas.\n→ ' + long + '\n→ Not now').choices, [long, 'Not now']);
  const runaway = parseChoices('x\n→ ' + 'word '.repeat(80)).choices[0];
  assert.ok(runaway.length <= 241 && runaway.endsWith('…') && !/wor…$/.test(runaway), 'a runaway line is cut at a word');
  const css = require('fs').readFileSync(require('path').join(__dirname, '..', 'renderer/app.css'), 'utf8');
  assert.match(css, /\.choice \{[^}]*white-space:normal;[^}]*overflow-wrap:anywhere/);
});
