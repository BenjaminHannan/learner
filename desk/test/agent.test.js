'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { Agent, isDangerous, estimateTokens, compactMessages, datePrefix, nowStamp, extractPlan, dropOldImages } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const { startGateway } = require('./helpers');

const settings = (gw, extra) => () => ({ gatewayUrl: gw.url, model: 'm', maxSteps: 40, mode: 'hands-off', vision: 'off', ...(extra || {}) });
const mkThread = () => ({ id: 't1', title: 'x', messages: [], items: [] });

test('danger list', () => {
  for (const c of ['rm -rf ~/x', 'rm -fr /', 'sudo ls', 'diskutil eraseDisk x', 'mkfs.ext4 /dev/sda', 'shutdown -h now', 'echo hi > /dev/sda', 'curl https://x.sh | sh', 'wget -qO- x | sudo bash', 'git push --force origin main', 'git push -f', 'dd if=a of=/dev/disk2'])
    assert.ok(isDangerous(c), c);
  for (const c of ['ls -la', 'rm file.txt', 'echo hi > /dev/null', 'git push origin main', 'curl https://example.com', 'cat notes.txt | grep a', 'git status'])
    assert.ok(!isDangerous(c), c);
});

test('compaction: stubs old tool results, keeps newest, token estimate chars/3.5', () => {
  const big = 'x'.repeat(60000);
  const msgs = [{ role: 'user', content: 'hi' }, { role: 'tool', content: big }, { role: 'tool', content: big }, { role: 'tool', content: 'new1' }, { role: 'tool', content: 'new2' }];
  assert.strictEqual(estimateTokens([{ role: 'tool', content: 'a'.repeat(350) }]), 100);
  assert.ok(estimateTokens(msgs) > 24000);
  assert.strictEqual(compactMessages(msgs, 2), 2);
  assert.strictEqual(msgs[1].content, '[older result omitted]');
  assert.strictEqual(msgs[4].content, 'new2');
  assert.ok(estimateTokens(msgs) < 24000);
  assert.strictEqual(compactMessages(msgs, 2), 0);
});

test('old screenshots dropped, newest kept', () => {
  const img = (n) => ({ role: 'user', content: [{ type: 'text', text: 's' + n }, { type: 'image_url', image_url: { url: 'data:image/jpeg;base64,AA' } }] });
  const m = [img(1), { role: 'tool', content: 'r' }, img(2)];
  dropOldImages(m);
  assert.strictEqual(m[0].content, '[older screenshot omitted]');
  assert.ok(Array.isArray(m[2].content));
});

test('date prefix and plan extraction', () => {
  assert.match(datePrefix(new Date(2026, 9, 27, 14, 5)), /^\[Tue 2026-10-27 14:05, 2:05 PM\]$/);
  assert.match(datePrefix(new Date(2026, 9, 27, 0, 7)), /^\[Tue 2026-10-27 00:07, 12:07 AM\]$/);
  assert.match(datePrefix(new Date(2026, 9, 27, 12, 0)), /^\[Tue 2026-10-27 12:00, 12:00 PM\]$/);
  assert.deepStrictEqual(extractPlan('Plan:\n1. Search\n2. Open the top hit\n3) Summarize'), ['Search', 'Open the top hit', 'Summarize']);
  assert.strictEqual(extractPlan('just text'), null);
});

test('loop end to end: tool call -> result -> final answer, events + history', async () => {
  const gw = await startGateway([
    { reasoning: 'need to search', content: 'Plan:\n1. Search\n2. Answer', tool_calls: [{ name: 'web_search', arguments: { query: 'cats' } }] },
    { content: 'Cats are great.' }
  ]);
  try {
    const events = [];
    const calls = [];
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: { web_search: async (a) => { calls.push(a); return '1. Cats\n   https://cats.example'; } }, emit: (e) => events.push(e), approve: async () => 'once', askUser: async () => 'x' });
    const t = mkThread();
    await agent.run(t, 'tell me about cats');
    assert.deepStrictEqual(calls, [{ query: 'cats' }]);
    const types = events.map((e) => e.type);
    for (const k of ['text', 'reasoning', 'step_start', 'step_end', 'plan', 'assistant_end', 'done']) assert.ok(types.includes(k), 'missing ' + k);
    assert.strictEqual(events.find((e) => e.type === 'step_start').summary, 'Searched “cats”');
    assert.strictEqual(events.at(-1).type, 'done'); assert.strictEqual(events.at(-1).stopped, false);
    assert.deepStrictEqual(t.messages.map((m) => m.role), ['user', 'assistant', 'tool', 'assistant']);
    assert.match(t.messages[0].content, /^\[\w{3} \d{4}-\d\d-\d\d \d\d:\d\d, \d{1,2}:\d\d [AP]M\] \[If this needs tools[^\]]*\] tell me about cats$/);
    assert.strictEqual(t.messages[3].content, 'Cats are great.');
    // second request contained the tool result and the constant system prompt
    const req2 = gw.requests[1].messages;
    assert.strictEqual(req2[0].role, 'system');
    assert.strictEqual(req2.at(-1).role, 'tool');
    assert.strictEqual(gw.requests[0].messages[0].content, req2[0].content);
    assert.ok(t.items.some((i) => i.t === 'step') && t.items.some((i) => i.t === 'plan'));
  } finally { gw.close(); }
});

test('approvals: Ask first gates shell, deny reaches the model; hands-off runs safe commands but gates danger', async () => {
  const gw = await startGateway([
    { tool_calls: [{ name: 'run_shell', arguments: { command: 'touch f' } }] },
    { tool_calls: [{ name: 'run_shell', arguments: { command: 'rm -rf /tmp/x' } }] },
    { content: 'done' }
  ]);
  try {
    const asked = [];
    let ran = 0;
    const mk = (mode, verdicts) => new Agent({ getSettings: settings(gw, { mode }), toolDefs: buildTools({}), tools: { run_shell: async () => { ran++; return 'ok'; } }, emit: () => {}, approve: async (r) => { asked.push(r); return verdicts.shift(); }, askUser: async () => '' });
    // ask-first: deny first command
    let t = mkThread();
    await mk('ask', ['deny', 'deny']).run(t, 'go');
    assert.strictEqual(ran, 0); assert.strictEqual(asked.length, 2);
    assert.match(t.messages.find((m) => m.role === 'tool').content, /denied/i);
  } finally { gw.close(); }
  const gw2 = await startGateway([
    { tool_calls: [{ name: 'run_shell', arguments: { command: 'touch f' } }] },
    { tool_calls: [{ name: 'run_shell', arguments: { command: 'rm -rf /tmp/x' } }] },
    { content: 'done' }
  ]);
  try {
    const asked = []; let ran = 0;
    const a = new Agent({ getSettings: settings(gw2, { mode: 'hands-off' }), toolDefs: buildTools({}), tools: { run_shell: async () => { ran++; return 'ok'; } }, emit: () => {}, approve: async (r) => { asked.push(r); return 'once'; }, askUser: async () => '' });
    await a.run(mkThread(), 'go');
    assert.strictEqual(ran, 2); assert.strictEqual(asked.length, 1); assert.strictEqual(asked[0].danger, true);
  } finally { gw2.close(); }
});

test('"Allow for this task" suppresses later prompts of the same kind', async () => {
  const gw = await startGateway([
    { tool_calls: [{ name: 'screen_key', arguments: { keys: 'cmd+t' } }] },
    { tool_calls: [{ name: 'screen_key', arguments: { keys: 'cmd+w' } }] },
    { content: 'ok' }
  ]);
  try {
    const asked = [];
    const a = new Agent({ getSettings: settings(gw, { mode: 'ask' }), toolDefs: buildTools({}), tools: { screen_key: async () => 'k' }, emit: () => {}, approve: async (r) => { asked.push(r.kind); return 'task'; }, askUser: async () => '' });
    await a.run(mkThread(), 'go');
    assert.deepStrictEqual(asked, ['screen']);
  } finally { gw.close(); }
});

test('typing into a password field is never an approval card: the tool itself hands off to Ben (ctx.waitForBen)', async () => {
  const gw = await startGateway([
    { tool_calls: [{ name: 'browser_type', arguments: { id: 3, text: 'hunter2' } }] },
    { content: 'ok' }
  ]);
  try {
    const asked = []; const states = [];
    let waited = false;
    const t = mkThread();
    const a = new Agent({ getSettings: settings(gw, { mode: 'ask' }), toolDefs: buildTools({}), onState: (s) => states.push(s),
      tools: { browser_type: async (args, ctx) => { await ctx.waitForBen(async () => { waited = true; }); return 'Login needed: Ben is signing in himself. Done.'; } },
      emit: () => {}, approve: async (r) => { asked.push(r.kind); return 'once'; }, askUser: async () => '' });
    await a.run(t, 'go');
    assert.deepStrictEqual(asked, []); assert.ok(waited);
    assert.ok(states.includes('waiting'));
    assert.match(t.messages.find((m) => m.role === 'tool').content, /^Login needed: Ben is signing in himself/);
  } finally { gw.close(); }
});

test('ask_user passes Ben\'s reply back as the tool result', async () => {
  const gw = await startGateway([{ tool_calls: [{ name: 'ask_user', arguments: { question: 'Send it?' } }] }, { content: 'sent' }]);
  try {
    const t = mkThread();
    const a = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async (q) => 'yes: ' + q });
    await a.run(t, 'email bob');
    assert.strictEqual(t.messages.find((m) => m.role === 'tool').content, 'yes: Send it?');
  } finally { gw.close(); }
});

test('steer: queued message is injected before the next model call', async () => {
  const gw = await startGateway([
    { tool_calls: [{ name: 'slow', arguments: {} }] },
    { content: 'final' }
  ]);
  try {
    let agent; const t = mkThread();
    const evs = [];
    agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: { slow: async () => { agent.steer('actually use blue'); return 'done'; } }, emit: (e) => evs.push(e), approve: async () => 'once', askUser: async () => '' });
    await agent.run(t, 'paint it');
    assert.strictEqual(evs.filter((e) => e.type === 'user').length, 1);
    const req2 = gw.requests[1].messages;
    const last = req2.at(-1);
    assert.strictEqual(last.role, 'user'); assert.match(last.content, /actually use blue$/);
    assert.strictEqual(req2.at(-2).role, 'tool');
    assert.strictEqual(agent.steer('late'), false); // not running any more
    // regression: a steer typed once is injected once and announced once (the UI used to add its own bubble AND the event's)
    assert.strictEqual(req2.filter((m) => m.role === 'user' && /actually use blue/.test(m.content)).length, 1);
    assert.strictEqual(t.messages.filter((m) => m.role === 'user' && /actually use blue/.test(m.content)).length, 1);
    assert.strictEqual(t.items.filter((i) => i.t === 'user' && i.text === 'actually use blue').length, 1);
  } finally { gw.close(); }
});

test('stop: aborts a streaming request and a running tool, history stays valid', async () => {
  const gw = await startGateway([{ content: 'thinking out loud', tool_calls: [{ name: 'hang', arguments: {} }] }, { content: 'never' }]);
  try {
    const t = mkThread(); const events = [];
    let agent; let toolStarted;
    const started = new Promise((r) => (toolStarted = r));
    agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: { hang: (a, ctx) => new Promise((res, rej) => { toolStarted(); ctx.signal.addEventListener('abort', () => rej(new Error('aborted'))); }) }, emit: (e) => events.push(e), approve: async () => 'once', askUser: async () => '' });
    const p = agent.run(t, 'go');
    await started; agent.stop(); await p;
    assert.strictEqual(events.at(-1).type, 'done'); assert.strictEqual(events.at(-1).stopped, true);
    assert.strictEqual(gw.requests.length, 1);
    const ids = t.messages.filter((m) => m.tool_calls).flatMap((m) => m.tool_calls.map((c) => c.id));
    const answered = t.messages.filter((m) => m.role === 'tool').map((m) => m.tool_call_id);
    assert.deepStrictEqual(answered, ids);
    assert.strictEqual(agent.running, false);
  } finally { gw.close(); }
});

test('stop during streaming', async () => {
  const gw = await startGateway([{ content: 'blah blah', hang: true }]);
  try {
    const events = []; let agent;
    agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: (e) => { events.push(e); if (e.type === 'text') agent.stop(); }, approve: async () => 'once', askUser: async () => '' });
    await agent.run(mkThread(), 'go');
    assert.strictEqual(events.at(-1).stopped, true);
  } finally { gw.close(); }
});

test('maxSteps ends a runaway loop', async () => {
  const gw = await startGateway([{ tool_calls: [{ name: 'noop', arguments: {} }] }]);
  try {
    const events = [];
    const agent = new Agent({ getSettings: settings(gw, { maxSteps: 3 }), toolDefs: buildTools({}), tools: { noop: async () => 'k' }, emit: (e) => events.push(e), approve: async () => 'once', askUser: async () => '' });
    await agent.run(mkThread(), 'loop');
    assert.strictEqual(gw.requests.length, 3);
    assert.ok(events.some((e) => e.type === 'text' && /step limit/.test(e.delta)));
  } finally { gw.close(); }
});

test('maxSteps 0 means no limit: a task keeps going past the old 40-step cap', async () => {
  const script = Array.from({ length: 45 }, () => ({ tool_calls: [{ name: 'noop', arguments: {} }] })).concat([{ content: 'done' }]);
  const gw = await startGateway(script);
  try {
    const events = [];
    const agent = new Agent({ getSettings: settings(gw, { maxSteps: 0, verify: false }), toolDefs: buildTools({}), tools: { noop: async () => 'k' }, emit: (e) => events.push(e), approve: async () => 'once', askUser: async () => '' });
    await agent.run(mkThread(), 'long job');
    assert.strictEqual(gw.requests.length, 46);
    assert.ok(!events.some((e) => e.type === 'text' && /step limit/.test(e.delta)));
  } finally { gw.close(); }
});

test('reasoning stays private: no reasoning text in events or in the saved thread, only that Glim thought', async () => {
  const gw = await startGateway([{ reasoning: 'SECRET-CHAIN step one', content: 'answer' }]);
  try {
    const events = []; const th = mkThread();
    const agent = new Agent({ getSettings: settings(gw, { verify: false }), toolDefs: buildTools({}), tools: {}, emit: (e) => events.push(e), approve: async () => 'once', askUser: async () => '' });
    await agent.run(th, 'hi');
    assert.ok(!JSON.stringify(events).includes('SECRET-CHAIN'), 'not sent to the window');
    assert.ok(!JSON.stringify(th.items).includes('SECRET-CHAIN'), 'not saved in the thread');
    const it = th.items.find((x) => x.t === 'assistant'); assert.strictEqual(it.thinking, true);
  } finally { gw.close(); }
});

test('vision on: image is appended as a follow-up user message, only the newest kept', async () => {
  const gw = await startGateway([
    { tool_calls: [{ name: 'shot', arguments: {} }] }, { tool_calls: [{ name: 'shot', arguments: {} }] }, { content: 'seen' }
  ]);
  try {
    const t = mkThread();
    const agent = new Agent({ getSettings: settings(gw, { vision: 'on' }), toolDefs: buildTools({}), tools: { shot: async () => ({ text: 'snap', image: 'data:image/jpeg;base64,QQ==' }) }, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    await agent.run(t, 'look');
    const last = gw.requests[2].messages;
    const imgs = last.filter((m) => Array.isArray(m.content));
    assert.strictEqual(imgs.length, 1);
    assert.ok(last.some((m) => m.content === '[older screenshot omitted]'));
  } finally { gw.close(); }
});

// ---- loop guard -----------------------------------------------------------------------------------
test('loop guard: the 3rd identical call in a row is refused with a "stuck" result; the tool is not run again', async () => {
  const call = { name: 'browser_click', arguments: { id: 7 } };
  const gw = await startGateway([{ tool_calls: [call] }, { tool_calls: [call] }, { tool_calls: [call] }, { content: 'giving up' }]);
  try {
    let ran = 0; const t = mkThread();
    const a = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: { browser_click: async () => { ran++; return 'URL: https://x/ | page unchanged'; } }, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    await a.run(t, 'click continue');
    assert.strictEqual(ran, 2);
    const tools = t.messages.filter((m) => m.role === 'tool').map((m) => m.content);
    assert.match(tools[1], /Nothing changed after clicking the same thing twice/); // page unchanged after 2 identical clicks
    assert.match(tools[2], /^Stuck: .*Do NOT repeat/);
  } finally { gw.close(); }
});

test('loop guard: a different call in between resets the count; scrolling is exempt', async () => {
  const c = (n, id) => ({ tool_calls: [{ name: n, arguments: { id } }] });
  const gw = await startGateway([c('browser_click', 1), c('browser_click', 1), c('browser_click', 2), c('browser_click', 1), c('browser_click', 1), { tool_calls: [{ name: 'browser_scroll', arguments: { direction: 'down' } }] }, { tool_calls: [{ name: 'browser_scroll', arguments: { direction: 'down' } }] }, { tool_calls: [{ name: 'browser_scroll', arguments: { direction: 'down' } }] }, { content: 'done' }]);
  try {
    let ran = 0;
    const a = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: { browser_click: async () => { ran++; return 'ok ' + ran; }, browser_scroll: async () => { ran++; return 's'; } }, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    await a.run(mkThread(), 'go');
    assert.strictEqual(ran, 8);
  } finally { gw.close(); }
});

test('loop guard: stuck again after a refusal pauses and asks Ben (onStuck); his answer is the tool result', async () => {
  const call = { name: 'browser_click', arguments: { id: 7 } };
  const gw = await startGateway([{ tool_calls: [call] }, { tool_calls: [call] }, { tool_calls: [call] }, { tool_calls: [call] }, { content: 'ok' }]);
  try {
    let ran = 0; const stuck = []; const states = []; const t = mkThread();
    const a = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), onState: (s) => states.push(s), tools: { browser_click: async () => { ran++; return 'same'; } },
      onStuck: async (info) => { stuck.push(info); return 'Ben completed the sign-in himself.'; }, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    await a.run(t, 'go');
    assert.strictEqual(ran, 2); assert.strictEqual(stuck.length, 1);
    assert.strictEqual(stuck[0].tool, 'browser_click'); assert.ok(states.includes('waiting'));
    const tools = t.messages.filter((m) => m.role === 'tool').map((m) => m.content);
    assert.match(tools[2], /^Stuck:/); assert.strictEqual(tools[3], 'Ben completed the sign-in himself.');
  } finally { gw.close(); }
});

test('time to first token is logged per request on the thread and on the assistant item', async () => {
  const gw = await startGateway([{ content: 'hello', delayMs: 5 }]);
  try {
    const t = mkThread(); const evs = [];
    const a = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: (e) => evs.push(e), approve: async () => 'once', askUser: async () => '' });
    await a.run(t, 'hi');
    assert.strictEqual(t.requests.length, 1);
    assert.ok(t.requests[0].ttftMs >= 0 && t.requests[0].ttftMs < 5000);
    assert.strictEqual(typeof t.items.find((i) => i.t === 'assistant').ttftMs, 'number');
    assert.strictEqual(evs.find((e) => e.type === 'assistant_end').toolCalls, 0);
  } finally { gw.close(); }
});

test('asksForSecret: catches a reply that asks for a password, not one that explains the sign-in hand-off', () => {
  const { asksForSecret } = require('../src/agent');
  assert.ok(asksForSecret('I need the email and password for that specific chess platform.'));
  assert.ok(asksForSecret('Your chess.com username/email and password?'));
  assert.ok(!asksForSecret('I opened the sign-in window; sign in there and click Done.'));
  assert.ok(!asksForSecret('Your password is never seen by me.'));
  assert.ok(!asksForSecret('Done! Opened chess.com.'));
});

test('extractPlan strips markdown marks from plan items', () => {
  const { extractPlan } = require('../src/agent');
  assert.deepStrictEqual(extractPlan('1. **Open** the site\n2. `Type` the query'), ['Open the site', 'Type the query']);
});

test('extractPlan: long numbered items are reasons, not steps, so no plan card', () => {
  const { extractPlan } = require('../src/agent');
  const text = '1. **Login access** - You mentioned "the gmail one" but didn\'t provide the login credentials for your chess account. I need the email and password for that specific chess platform.\n' +
    '2. **Play for you** - I can\'t actually play chess games for you or make strategic moves in a game. Chess requires active participation and decision-making that I can\'t replicate as an agent.';
  assert.strictEqual(extractPlan(text), null);
  assert.deepStrictEqual(extractPlan('1. Open chess.com\n2. Sign in with Google'), ['Open chess.com', 'Sign in with Google']);
});

test('nowStamp: plain stamp on the same day, a new-day warning after an overnight gap', () => {
  const wed = new Date(2026, 9, 28, 8, 5);
  assert.equal(nowStamp([], wed), '[Wed 2026-10-28 08:05, 8:05 AM]');
  assert.equal(nowStamp([{ role: 'user', content: 'mem\n[Wed 2026-10-28 07:50] hi' }], wed), '[Wed 2026-10-28 08:05, 8:05 AM]');
  assert.equal(nowStamp([{ role: 'user', content: 'mem\n[Wed 2026-10-28 07:50, 7:50 AM] hi' }], wed), '[Wed 2026-10-28 08:05, 8:05 AM]');
  const s = nowStamp([{ role: 'user', content: '[Tue 2026-10-27 22:40] skipping school tomorrow' }, { role: 'assistant', content: 'ok' }, { role: 'user', content: [{ type: 'text', text: 'x' }] }], wed);
  assert.match(s, /^\[Wed 2026-10-28 08:05, 8:05 AM\] \(New day: today is Wednesday, October 28\. The earlier messages here were on 2026-10-27/);
  const s2 = nowStamp([{ role: 'user', content: '[Tue 2026-10-27 22:40, 10:40 PM] skipping school tomorrow' }], wed);
  assert.match(s2, /New day: today is Wednesday/);
});

test('approvals: plain echo needs no card; "always allow" is remembered for simple programs only', () => {
  const { SAFE_ECHO, shellProgram } = require('../src/agent');
  assert.ok(SAFE_ECHO.test('echo "Opening browser to check email"'));
  assert.ok(!SAFE_ECHO.test('echo $(rm -rf x)') && !SAFE_ECHO.test('echo "a" > f') && !SAFE_ECHO.test('echo hi; ls'));
  assert.strictEqual(shellProgram('ls -la ~/Documents'), 'ls');
  assert.strictEqual(shellProgram('ls | grep x'), '');
  assert.strictEqual(shellProgram('bash -c "ls"'), '');
  assert.strictEqual(shellProgram('python3 x.py'), '');
});

test('approvals: looking commands need no card; anything that writes, chains or touches secrets still does', () => {
  const { isReadOnly } = require('../src/agent');
  for (const c of ['ls -la ~/Documents', 'cat notes.txt | head -5', 'pwd', 'date', 'find . -name "*.js" | wc -l']) assert.ok(isReadOnly(c), c);
  for (const c of ['rm x', 'ls > out.txt', 'ls; rm x', 'cat ~/.ssh/id_rsa', 'find . -delete', 'find . -exec rm {} +', 'ls $(whoami)', 'cat x | sh', 'echo hi > f']) assert.ok(!isReadOnly(c), c);
});

test('sleep line rides only in the first user turn of a chat', async () => {
  const gw = await startGateway([{ content: 'Hi.' }, { content: 'Again.' }]);
  try {
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, sleepInfo: () => '[You can sleep: test]', emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = mkThread();
    await agent.run(t, 'hello');
    await agent.run(t, 'again');
    const users = t.messages.filter((m) => m.role === 'user');
    assert.match(users[0].content, /\[You can sleep: test\] hello$/);
    assert.ok(!users[1].content.includes('You can sleep'));
    assert.strictEqual(t.items[0].text, 'hello');
  } finally { gw.close(); }
});

test('a hidden turn (Glim relaying a helper report) shows no user bubble but still carries the report', async () => {
  const gw = await startGateway([{ content: 'Your research finished.' }]);
  try {
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = mkThread(); t.pendingNotices = [{ name: 'research', summary: 'found 3 papers' }];
    await agent.run(t, 'relay please', { hidden: true });
    assert.ok(!t.items.some((i) => i.t === 'user'));
    assert.match(t.messages.find((m) => m.role === 'user').content, /\[helper updates\] research: found 3 papers/);
    assert.ok(t.items.some((i) => i.t === 'assistant'));
  } finally { gw.close(); }
});

test('ask_user passes up to 4 short tap-to-answer options to the UI', async () => {
  const { cleanOptions } = require('../src/agent');
  assert.deepStrictEqual(cleanOptions(['Yes', '  No  ', '', 'A'.repeat(100), 'c', 'd', 'e']).map((x) => x.length), [3, 2, 60, 1]);
  assert.deepStrictEqual(cleanOptions('nope'), []); assert.deepStrictEqual(cleanOptions(undefined), []);
  const gw = await startGateway([{ tool_calls: [{ name: 'ask_user', arguments: { question: 'Which?', options: ['Red', 'Blue'] } }] }, { content: 'Done.' }]);
  try {
    let got = null;
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async (q, s, o) => { got = { q, o }; return 'Red'; } });
    await agent.run(mkThread(), 'pick one');
    assert.deepStrictEqual(got, { q: 'Which?', o: ['Red', 'Blue'] });
  } finally { gw.close(); }
});
