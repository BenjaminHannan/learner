'use strict';
// AGENT1 harness changes (src/agentkit.js): flags and the single-sign-on hint.
const test = require('node:test');
const assert = require('node:assert');
const Kit = require('../src/agentkit');

test('agentKit flags: off by default, on by name or "all", unknown names dropped', () => {
  assert.strictEqual(Kit.on({}, 'sso'), false);
  assert.strictEqual(Kit.on({ agentKit: [] }, 'sso'), false);
  assert.strictEqual(Kit.on({ agentKit: ['sso'] }, 'sso'), true);
  assert.strictEqual(Kit.on({ agentKit: ['sso'] }, 'diet'), false);
  assert.strictEqual(Kit.on({ agentKit: 'all' }, 'diet'), true);
  assert.deepStrictEqual(Kit.clean(['sso', 'bogus', 'sso']), ['sso']);
  assert.deepStrictEqual(Kit.clean('sso,diet'), ['sso', 'diet']);
  assert.strictEqual(Kit.clean('all'), 'all');
});

test('sso hint names "Sign in with Google"-style buttons from the newest snapshot, nothing else', () => {
  const lines = ['[1] button "Accept all"', '[10] link "Sign in with Google" -> https://accounts.google.com/o/oauth2/auth?x=1', '[11] link "Sign in with Microsoft" -> /login/microsoft',
    '[12] input(text) "Username" value=""', '[13] input(password) "Password" value=""', '[14] button "Log in"', '[15] button "Continue with Apple"'];
  assert.deepStrictEqual(Kit.ssoLines(lines), [lines[1], lines[2], lines[6]]);
  const t = Kit.ssoNote('portal.example.com', lines);
  assert.match(t, /\[10\] link "Sign in with Google"/);
  assert.doesNotMatch(t, /accounts\.google\.com/);   // the long href is left out
  assert.strictEqual(Kit.ssoNote('x.com', ['[1] button "Log in"', '[2] input(password) "Password" value=""']), '');
  assert.strictEqual(Kit.ssoNote('x.com', ['[3] link "Google sign-in help" -> /help']), '', 'a help link is not a sign-in button');
});

test('diet: web tasks get the 10 web tools with short descriptions; older page views shrink in the request only', () => {
  const { SYSTEM_PROMPT, buildTools } = require('../src/prompt');
  const all = buildTools({ diary: true });
  const d = Kit.dietTools(all);
  assert.deepStrictEqual(d.map((t) => t.function.name), Kit.WEB_TOOLS);
  assert.ok(JSON.stringify(d).length < JSON.stringify(all).length / 2, 'tools at least halved');
  assert.ok(Kit.dietSystem(SYSTEM_PROMPT).length < SYSTEM_PROMPT.length && !/Motes|run_shell/.test(Kit.dietSystem(SYSTEM_PROMPT)));
  assert.strictEqual(Kit.isWebTask("What's due this week on my school portal?"), true);
  assert.strictEqual(Kit.isWebTask('How much is the lamp on shop.test?'), true);
  assert.strictEqual(Kit.isWebTask('list the files on my desktop'), false);
  assert.strictEqual(Kit.isWebTask('remind me at 5 to call mom'), false);
  const snap = (u) => 'URL: https://' + u + ' | Title: T\n[1] link "a" -> /\n[2] button "b"\nText: Price: $34.99 and more';
  const msgs = [{ role: 'user', content: 'go' }, { role: 'assistant', content: '', tool_calls: [{}] }, { role: 'tool', content: snap('a.test') }, { role: 'assistant', content: '', tool_calls: [{}] }, { role: 'tool', content: snap('b.test') }];
  const out = Kit.dietHistory(msgs, 0);
  assert.match(out[2].content, /^URL: https:\/\/a\.test \| Title: T \[older page view/);
  assert.match(out[2].content, /Text: Price: \$34\.99/, 'the old page text start stays (prices read earlier)');
  assert.doesNotMatch(out[2].content, /\[1\] link/);
  assert.strictEqual(out[4].content, msgs[4].content, 'the newest view is whole');
  assert.strictEqual(msgs[2].content, snap('a.test'), 'stored messages untouched');
});

test('pins: Ben\'s own words (earlier turns, the task, corrections) in one block; nothing when it would only repeat the task', () => {
  const { benTurns } = require('../src/agent');
  const msgs = [{ role: 'user', content: '[Wed 2026-11-04 16:00] My school portal is portal.schoolhub.test.' }, { role: 'assistant', content: 'ok' },
    { role: 'user', content: '[Wed 2026-11-04 17:00, 5:00 PM] [If this needs tools: x] Check Dresden Middle.' }, { role: 'assistant', content: '', tool_calls: [] }, { role: 'tool', content: 'URL: x' },
    { role: 'user', content: '[Self-check] Not done' },
    { role: 'user', content: '[Wed 2026-11-04 17:01, 5:01 PM] [If this needs tools: x] (Ben sent this while you were working. What you already did above still stands: take his words into account and carry on from where you are; do not start over or repeat a plan.) No, the high school.' }];
  const t = benTurns(msgs, 0, 2);
  assert.deepStrictEqual(t.map((x) => x.when), ['earlier', 'task', 'correction']);
  const b = Kit.pinBlock(t);
  assert.match(b, /earlier: "My school portal is portal\.schoolhub\.test\."/);
  assert.match(b, /correction while you worked: "No, the high school\."/);
  assert.doesNotMatch(b, /Self-check|Ben sent this while/);
  assert.strictEqual(Kit.pinBlock([{ text: 'Check the site', when: 'task' }]), '');
});

test('pins: websites Ben named get a line even on a one-message task', () => {
  assert.match(Kit.pinBlock([{ text: 'Set my notifications on account.test to weekly', when: 'task' }]), /Websites Ben named \(real sites: open them in your browser\): account\.test\]/);
  assert.strictEqual(Kit.pinBlock([{ text: 'what is 2+2. Thanks.', when: 'task' }]), '');
});

test('stuck: a blank run after an intent line is cut; an intent-only reply is caught at any step; questions and answers are not', () => {
  assert.strictEqual(Kit.blankRun("Let me check what's on your screen." + '\n'.repeat(60)), true);
  assert.strictEqual(Kit.blankRun("Let me check what's on your screen.\n\n"), false);
  assert.strictEqual(Kit.blankRun('  \n'.repeat(80)), true);
  assert.strictEqual(Kit.onlyIntent("Let me check what's on your screen."), true);
  assert.strictEqual(Kit.onlyIntent("I'll cancel the gym clothes reminder agent now."), true);
  assert.strictEqual(Kit.onlyIntent('The lamp costs $34.99.'), false);
  assert.strictEqual(Kit.onlyIntent('Should I buy it?'), false);
  assert.strictEqual(Kit.onlyIntent("I'll wait until you sign in, then let me know."), false);
  assert.strictEqual(Kit.onlyIntent('The Arc lamp is $27.50 and the Lumen 3 is $34.99, so the Arc is cheaper. ' + 'x'.repeat(300)), false);
});
