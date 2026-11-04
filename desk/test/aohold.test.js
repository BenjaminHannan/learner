'use strict';
// UI2 (Ben Nov 4, M3): only Ben's own typed or dictated words may steer or cut a run; proactive words wait until the task ends.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'), path = require('path');
const { HoldWhileBusy } = require('../src/aohold');
const { Agent } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');

test('HoldWhileBusy: posts at once when idle; while busy it holds (newest 3), flushes oldest first when idle, drops stale ones', () => {
  let busy = false, now = 0; const posted = [];
  const h = new HoldWhileBusy({ busy: () => busy, post: (m) => posted.push(m.text), now: () => now, maxAgeMs: 1000 });
  assert.strictEqual(h.offer({ text: 'a' }), 'posted');
  busy = true;
  for (const x of ['b', 'c', 'd', 'e']) assert.strictEqual(h.offer({ text: x }), 'held');
  assert.strictEqual(h.flush(), 0, 'still busy: nothing goes in');
  busy = false; now = 500;
  assert.strictEqual(h.flush(), 3);
  assert.deepStrictEqual(posted, ['a', 'c', 'd', 'e']);
  busy = true; h.offer({ text: 'old' }); busy = false; now = 5000;
  assert.strictEqual(h.flush(), 0, 'stale: dropped');
  assert.deepStrictEqual(posted, ['a', 'c', 'd', 'e']);
});

test('a proactive message during a run neither cuts nor enters it; it goes into the chat after the run (fake model)', async () => {
  const gw = await startGateway([{ content: 'Looking at your screen.', tool_calls: [{ name: 'screen_look', arguments: {} }] }, { content: 'Chrome is open on Schoology.' }]);
  try {
    const t = { id: 't1', messages: [], items: [] }; const evs = []; let agent; const chat = [];
    const hold = new HoldWhileBusy({ busy: () => agent.running, post: (m) => chat.push(m.text) });
    agent = new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 40, mode: 'hands-off', vision: 'off' }), toolDefs: buildTools({}),
      tools: { screen_look: async () => { assert.strictEqual(hold.offer({ text: 'Ben, I noticed you are working through a Google SSO flow' }), 'held'); return 'App: Google Chrome'; } },
      emit: (e) => evs.push(e), approve: async () => 'once', askUser: async () => '', onEnd: () => setTimeout(() => hold.flush(), 0) });
    await agent.run(t, 'can you just do it on my google chrome browser?');
    assert.ok(!evs.some((e) => e.cut || e.type === 'discard' || (e.type === 'user' && e.steer)), 'nothing cut, nothing steered');
    const reqs = gw.requests.filter((r) => r.messages);
    assert.ok(!JSON.stringify(reqs).includes('Google SSO flow'), 'never reached the model');
    assert.deepStrictEqual(chat, []);
    await new Promise((r) => setTimeout(r, 10));
    assert.deepStrictEqual(chat, ['Ben, I noticed you are working through a Google SSO flow'], 'posted once the task ended');
  } finally { gw.close(); }
});

test('wiring: only the agent:send handler (Ben typed or dictated) can steer; the proactive chat outlet goes through the hold, flushed at run end', () => {
  const src = fs.readFileSync(path.join(__dirname, '../main.js'), 'utf8');
  const start = src.indexOf("h('agent:send'"), end = src.indexOf("\n  h('", start + 10);
  assert.ok(start > 0 && end > start);
  const outside = src.slice(0, start) + src.slice(end);
  assert.ok(!/\bagent\.steer\(|helpers\.steer\(|\.steer\(/.test(outside), 'no steer outside agent:send');
  assert.match(src, /chat: \(m\) => aoHold\.offer\(m\)/);
  assert.match(src, /busy: \(\) => !!\(agent && agent\.running\)/);
  assert.match(src, /setTimeout\(\(\) => \{ try \{ aoHold\.flush\(\); \}/);
  const helpers = fs.readFileSync(path.join(__dirname, '../src/helpers.js'), 'utf8');
  assert.strictEqual((helpers.match(/\.steer\(/g) || []).length, 1, 'helpers.steer only forwards (called from agent:send)');
});
