'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { guardHandsConsent } = require('../src/computer-control/consent');
const { Agent } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');
const { Hands, InputWatch } = require('../src/hands');
const { SafetyLevels } = require('../src/safety-levels');

test('unanswered, rejected, aborted and unclear hands prompts never run the action', async () => {
  for (const answer of [undefined, null, '', 'no', 'yes but no', 'always maybe']) {
    let calls = 0;
    const signal = new AbortController().signal;
    const guard = guardHandsConsent({ hands: { o: { levels: { level: () => 'ask' } } }, signal, askUser: async () => answer, run: () => { calls++; } });
    await guard.ask('?', new AbortController().signal, []);
    assert.equal(guard.guardedRun({}, {}).error, true, String(answer));
    assert.equal(calls, 0);
  }
  let calls = 0;
  const task = new AbortController(), prompt = new AbortController();
  const guard = guardHandsConsent({ hands: { o: { levels: { level: () => 'ask' } } }, signal: task.signal, askUser: async () => 'yes', run: () => { calls++; } });
  prompt.abort();
  await guard.ask('?', prompt.signal, []);
  assert.equal(guard.guardedRun({}, {}).error, true);
  assert.equal(calls, 0);
});

test('explicit yes is scoped to its task; free is an existing standing grant', async () => {
  let calls = 0;
  const hands = { o: { levels: { level: () => 'ask' } } }, signal = new AbortController().signal;
  const make = (s) => guardHandsConsent({ hands, signal: s, askUser: async () => 'Yes', run: () => ++calls });
  const first = make(signal);
  await first.ask('?', new AbortController().signal, []);
  assert.equal(first.guardedRun({}, {}), 1);
  assert.equal(make(signal).guardedRun({}, {}), 2);
  assert.equal(make(new AbortController().signal).guardedRun({}, {}).error, true);
  hands.o.levels.level = () => 'free';
  assert.equal(make(new AbortController().signal).guardedRun({}, {}), 3);
});

test('the real legacy hands timeout cannot send an unanswered action through the chat guard', async () => {
  let time = Date.now(), calls = 0;
  const now = () => time;
  const levels = new SafetyLevels({ now });
  const input = new InputWatch({ now });
  const hands = new Hands({ input, levels, now, sleep: async ms => { time += ms; await null; } });
  const signal = new AbortController().signal;
  const guard = guardHandsConsent({ hands, signal, askUser: (q, s) => new Promise(resolve => s.addEventListener('abort', () => resolve(''))), run: () => { calls++; return 'typed'; } });
  const result = await hands.act('screen_type', { text: 'hello' }, { signal, summary: 'type hello', askUser: guard.ask }, guard.guardedRun);
  assert.equal(result.error, true);
  assert.match(result.text, /no clear permission/i);
  assert.equal(calls, 0);
});

test('chat does not execute when the legacy hands tries to proceed without an answer', async () => {
  const gw = await startGateway([{ tool_calls: [{ name: 'screen_type', arguments: { text: 'hello' } }] }, { content: 'stopped' }]);
  try {
    let calls = 0;
    const hands = { o: { levels: { level: () => 'ask' } }, isHands: () => true, act: async (n, a, ctx, run) => run(a, ctx) };
    const agent = new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 4, mode: 'hands-off', vision: 'off', verify: false }), toolDefs: buildTools({}), tools: { screen_type: () => { calls++; return 'typed'; } }, hands, emit: () => {}, approve: async () => 'once', askUser: async () => undefined });
    const thread = { id: 't', title: 'x', messages: [], items: [] };
    await agent.run(thread, 'type hello');
    assert.equal(calls, 0);
    assert.match(thread.messages.find(m => m.role === 'tool').content, /no clear permission/i);
  } finally { gw.close(); }
});

test('an unanswered approval card does not run a screen action', async () => {
  const gw = await startGateway([{ tool_calls: [{ name: 'screen_key', arguments: { keys: 'enter' } }] }, { content: 'stopped' }]);
  try {
    let calls = 0;
    const agent = new Agent({ getSettings: () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 4, mode: 'ask', vision: 'off', verify: false }), toolDefs: buildTools({}), tools: { screen_key: () => { calls++; return 'pressed'; } }, emit: () => {}, approve: async () => undefined, askUser: async () => '' });
    const thread = { id: 't', title: 'x', messages: [], items: [] };
    await agent.run(thread, 'press enter');
    assert.equal(calls, 0);
    assert.match(thread.messages.find(m => m.role === 'tool').content, /not allowed/i);
  } finally { gw.close(); }
});

test('Mac chat cannot fall back to an unguarded desktop send while the checked path is unavailable', async () => {
  if (process.platform !== 'darwin') return;
  const previous = Object.getOwnPropertyDescriptor(process.versions, 'electron');
  Object.defineProperty(process.versions, 'electron', { value:'test', configurable:true });
  const gw = await startGateway([{ tool_calls: [{ name:'screen_type', arguments:{ text:'hello' } }] }, { content:'stopped' }]);
  try {
    let calls = 0;
    const agent = new Agent({ getSettings:() => ({ gatewayUrl:gw.url, model:'m', maxSteps:4, mode:'hands-off', vision:'off', verify:false }), toolDefs:buildTools({}), tools:{ screen_type:() => { calls++; } }, emit:() => {}, approve:async () => 'once' });
    const thread = { id:'t', title:'x', messages:[], items:[] };
    await agent.run(thread, 'type hello');
    assert.equal(calls, 0);
    assert.match(thread.messages.find(m => m.role === 'tool').content, /checked screen/i);
  } finally {
    gw.close();
    if (previous) Object.defineProperty(process.versions, 'electron', previous); else delete process.versions.electron;
  }
});
