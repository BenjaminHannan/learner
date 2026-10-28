'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { doingLine } = require('../renderer/doing');

test('doing line: the Next line, else the last sentence, never the reasoning before it', () => {
  assert.strictEqual(doingLine("I need to actually read the article content. Let me scroll down.\n\nNext: I'll click on the transformer section."), "I'll click on the transformer section.");
  assert.strictEqual(doingLine('Plan: Open the article, then summarize.\n\n**Next:** I\'ll open the article.'), "I'll open the article.");
  assert.strictEqual(doingLine('I see the article has sections on attention. Let me scroll down to read it.'), 'Let me scroll down to read it.');
  assert.strictEqual(doingLine('Checking your calendar'), 'Checking your calendar');
  assert.strictEqual(doingLine('Plan: Search the web for prices'), 'Search the web for prices');
  assert.strictEqual(doingLine(''), '');
  assert.ok(doingLine('Next: ' + 'x'.repeat(200)).length <= 90);
  assert.strictEqual(doingLine('Plan:\n1. Search prices\n2. Compare'), 'Search prices');
});
