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

test('UI2 cleanReply: the "[cut off: ...]" model note never shows (closed, unclosed while streaming, mid-text); other text untouched', () => {
  const { cleanReply } = require('../renderer/doing');
  assert.strictEqual(cleanReply('Let me look at your screen first.\n[cut off: Ben sent a new message]'), 'Let me look at your screen first.');
  assert.strictEqual(cleanReply('Reading the page now.\n[cut off: Ben se'), 'Reading the page now.');
  assert.strictEqual(cleanReply('A [cut off: Ben sent a new message] B'), 'A B');
  assert.strictEqual(cleanReply('plain answer  '), 'plain answer  ');
  assert.strictEqual(cleanReply('the rope was [cut] off'), 'the rope was [cut] off');
  assert.strictEqual(cleanReply(null), '');
});

test('UI2 stripPlan: a reply opening with a plan the plan card already shows loses that block (Ben M3 replies); others untouched', () => {
  const { stripPlan } = require('../renderer/doing');
  const card = ['Read the current page state.', 'Click SSO Login to trigger the Google sign-in flow.', 'Follow the redirect and complete steps as the browser allows.'];
  const m3 = '\n\nLet me re-read the page and then actually click SSO Login.\n\n**Plan:**\n1. Read the current page state.\n2. Click SSO Login to trigger the Google sign-in flow.\n3. Follow the redirect and complete steps as the browser allows.\n\nReading the page now.';
  assert.strictEqual(stripPlan(m3, card), 'Let me re-read the page and then actually click SSO Login.\n\nReading the page now.');
  assert.strictEqual(stripPlan('1. Read the current page\n2. Click SSO Login\n\nOn it.', card), 'On it.');
  assert.strictEqual(stripPlan('**Plan:**\n1. Re-read the page.\n2. Click SSO Login.', card), '');
  // not the card's plan, no card, or a normal numbered answer: left alone
  const other = 'Plan:\n1. Buy milk at the store\n2. Bake bread tonight';
  assert.strictEqual(stripPlan(other, card), other);
  assert.strictEqual(stripPlan(m3, []), m3);
  const ans = 'Your assignments:\n1. Read chapter 4\n2. Lab report due Friday';
  assert.strictEqual(stripPlan(ans, card), ans);
});
