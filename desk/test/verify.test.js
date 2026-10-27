'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { Agent, CHECK_MARK } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const { browserAfter, screenAfter, AFTER_MAX } = require('../src/tools/after');
const { startGateway } = require('./helpers');

const settings = (gw, extra) => () => ({ gatewayUrl: gw.url, model: 'main-model', maxSteps: 40, mode: 'hands-off', vision: 'off', ...(extra || {}) });
const mkThread = () => ({ id: 't1', title: 'x', messages: [], items: [] });
const isCheck = (req) => { const m = req.messages.at(-1); return m.role === 'user' && typeof m.content === 'string' && m.content.startsWith(CHECK_MARK + ' Compare'); };
const click = { tool_calls: [{ name: 'browser_click', arguments: { id: 1 } }] };
const mk = (gw, extra, tools) => {
  const events = [];
  const agent = new Agent({ getSettings: settings(gw, extra), toolDefs: buildTools({}), tools: tools || { browser_click: async () => 'URL: https://x.test/ | Title: X\nAfter click: URL unchanged.', web_search: async () => '1. r' }, emit: (e) => events.push(e), approve: async () => 'once', askUser: async () => 'x' });
  return { agent, events };
};

test('check turn: not for pure chat, not for non-state-changing tools', async () => {
  const gw = await startGateway([{ content: 'Hi there.' }]);
  try {
    const { agent } = mk(gw);
    await agent.run(mkThread(), 'hello');
    assert.strictEqual(gw.requests.length, 1);
  } finally { gw.close(); }
  const gw2 = await startGateway([{ tool_calls: [{ name: 'web_search', arguments: { query: 'a' } }] }, { content: 'Found it.' }]);
  try {
    const { agent } = mk(gw2);
    await agent.run(mkThread(), 'search');
    assert.strictEqual(gw2.requests.length, 2);
  } finally { gw2.close(); }
});

test('check turn after a state-changing tool: VERIFIED accepts; same system+tools, fast model, short max_tokens, nothing stored', async () => {
  const gw = await startGateway([click, { content: 'Clicked it, done.' }, { content: 'VERIFIED' }]);
  try {
    const { agent, events } = mk(gw);
    const t = mkThread();
    await agent.run(t, 'click it');
    assert.strictEqual(gw.requests.length, 3);
    const [r0, , chk] = gw.requests;
    assert.ok(isCheck(chk));
    assert.strictEqual(chk.model, 'qwen36-fast');
    assert.ok(chk.max_tokens > 0 && chk.max_tokens <= 200);
    assert.strictEqual(chk.messages[0].content, r0.messages[0].content);
    assert.strictEqual(JSON.stringify(chk.tools), JSON.stringify(r0.tools));
    assert.ok(!t.messages.some((m) => typeof m.content === 'string' && m.content.startsWith(CHECK_MARK)));
    assert.strictEqual(t.messages.at(-1).content, 'Clicked it, done.');
    const end = events.filter((e) => e.type === 'step_end' && e.tool === 'verify');
    assert.strictEqual(end.length, 1);
    assert.strictEqual(end[0].summary, 'Checked its work');
  } finally { gw.close(); }
});

test('NOT DONE continues the loop with a steer; then a second check can verify', async () => {
  const gw = await startGateway([click, { content: 'Done.' }, { content: 'NOT DONE: no sign the form was submitted' }, click, { content: 'Submitted, confirmed on the page.' }, { content: 'VERIFIED' }]);
  try {
    const { agent, events } = mk(gw);
    const t = mkThread();
    await agent.run(t, 'submit');
    assert.strictEqual(gw.requests.length, 6);
    const steer = gw.requests[3].messages.at(-1);
    assert.strictEqual(steer.role, 'user');
    assert.match(steer.content, /Not done yet: no sign the form was submitted/);
    assert.ok(events.some((e) => e.type === 'step_end' && e.tool === 'verify' && /^Re-checking: no sign the form/.test(e.summary)));
    assert.strictEqual(t.messages.at(-1).content, 'Submitted, confirmed on the page.');
  } finally { gw.close(); }
});

test('at most 2 check turns per task, then the answer is accepted', async () => {
  const gw = await startGateway([click, { content: 'a1' }, { content: 'NOT DONE: x' }, { content: 'a2' }, { content: 'NOT DONE: y' }, { content: 'a3' }, { content: 'NOT DONE: z' }]);
  try {
    const { agent } = mk(gw);
    const t = mkThread();
    const r = await agent.run(t, 'go');
    assert.strictEqual(gw.requests.filter(isCheck).length, 2);
    assert.strictEqual(gw.requests.length, 6);
    assert.strictEqual(t.messages.at(-1).content, 'a3');
    assert.strictEqual(r.stopped, false);
  } finally { gw.close(); }
});

test('verify setting off skips the check; unclear verdict is accepted', async () => {
  const gw = await startGateway([click, { content: 'Done.' }]);
  try {
    const { agent } = mk(gw, { verify: false });
    await agent.run(mkThread(), 'go');
    assert.strictEqual(gw.requests.length, 2);
  } finally { gw.close(); }
  const gw2 = await startGateway([click, { content: 'Done.' }, { content: 'hmm maybe' }]);
  try {
    const { agent } = mk(gw2);
    await agent.run(mkThread(), 'go');
    assert.strictEqual(gw2.requests.length, 3);
  } finally { gw2.close(); }
});

test('after a tool error the result tells the model to re-read before retrying', async () => {
  const gw = await startGateway([click, { content: 'ok' }]);
  try {
    const { agent } = mk(gw, { verify: false }, { browser_click: async () => ({ text: 'Error: no element [1]', error: true }) });
    await agent.run(mkThread(), 'go');
    const tool = gw.requests[1].messages.at(-1).content;
    assert.match(tool, /^Error: no element/);
    assert.match(tool, /re-read the page or screen/);
  } finally { gw.close(); }
});

// ---- after-observation (pure) ----
const snap = (o) => ({ url: 'https://a.test/', title: 'A', text: 'hello', lines: ['[1] button "Go"', '[2] input(text) "Q" value=""'], focus: '', alerts: [], ...o });

test('after: marks a click with no effect plainly', () => {
  const n = browserAfter(snap(), snap({ lines: ['[5] button "Go"', '[6] input(text) "Q" value=""'] }), 'click');
  assert.match(n, /Nothing changed on the page after this click/);
});

test('after: URL, new elements, alerts and focus are reported, within the size budget', () => {
  const cur = snap({ url: 'https://a.test/next?x=1', title: 'Next', lines: ['[1] button "Pay"', '[2] link "Back" -> /'], alerts: ['Invalid email address'], focus: '[2] input(text) "Email" value="bob"' });
  const n = browserAfter(snap(), cur, 'click');
  assert.match(n, /URL now a\.test\/next/);
  assert.match(n, /Pay/);
  assert.match(n, /Alert on page: "Invalid email address"/);
  assert.match(n, /Focus: .*Email/);
  assert.doesNotMatch(n, /Nothing changed/);
  const big = snap({ lines: Array.from({ length: 80 }, (_, i) => '[' + i + '] button "Item number ' + i + ' with a long label"'), alerts: ['x'.repeat(300), 'y'.repeat(300)] });
  assert.ok(browserAfter(snap(), big, 'click').length <= AFTER_MAX);
});

test('after: password and payment values are masked', () => {
  const cur = snap({ lines: ['[1] input(password) "Password" value="hunter2"', '[2] input(text,payment) "Card" value="4111111111111111"'], focus: '[1] input(password) "Password" value="hunter2"' });
  const n = browserAfter(snap(), cur, 'type');
  assert.doesNotMatch(n, /hunter2|4111/);
  assert.match(n, /••••/);
});

test('after (screen): no-effect marker, changed values, secure fields masked', () => {
  const look = (els, app) => ({ app: app || 'Notes', windows: [{ title: 'W' }], elements: els });
  const base = [{ id: 1, role: 'AXButton', title: 'Save' }, { id: 2, role: 'AXTextField', title: 'Name', value: '' }];
  const { lookSummary } = require('../src/tools/after');
  assert.match(screenAfter(lookSummary(look(base)), look(base), 'click'), /Nothing changed on the screen after this click/);
  const typed = [base[0], { id: 2, role: 'AXTextField', title: 'Name', value: 'Ben' }];
  assert.match(screenAfter(lookSummary(look(base)), look(typed), 'type'), /values changed: TextField "Name" value="Ben"/);
  const sec = [base[0], { id: 3, role: 'AXSecureTextField', title: 'Pass', value: 'abc' }];
  const n = screenAfter(lookSummary(look(base)), look(sec), 'type');
  assert.doesNotMatch(n, /abc/);
  assert.match(screenAfter(lookSummary(look(base)), look(base, 'Finder'), 'open', 'WARNING: front app is "Finder"'), /WARNING/);
});

test('verify: parseCheckLoose finds the last verdict in thinking text (empty content)', () => {
  const { parseCheckLoose } = require('../src/agent');
  assert.deepStrictEqual(parseCheckLoose('hmm, checking... the order shows. VERIFIED'), { ok: true });
  assert.strictEqual(parseCheckLoose('Maybe NOT DONE: no total.\nOn reflection VERIFIED').ok, true);
  const r = parseCheckLoose('thinking\nNOT DONE: the total is missing'); assert.strictEqual(r.ok, false); assert.match(r.reason, /total/);
  assert.strictEqual(parseCheckLoose('just rambling'), null);
});
