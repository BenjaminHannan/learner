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

test('steer while the model is writing: the half-written reply stays (cut off) and his message is read at once', async () => {
  const gw = await startGateway([{ content: 'a long reply that is still being written', hang: true }, { content: 'got it, blue' }]);
  try {
    let agent; const t = mkThread(); const evs = [];
    agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: (e) => evs.push(e), approve: async () => 'once', askUser: async () => '' });
    const done = agent.run(t, 'paint it');
    const t0 = Date.now();
    while (!evs.some((e) => e.type === 'text')) await new Promise((r) => setTimeout(r, 10));   // the first reply is streaming
    assert.strictEqual(agent.steer('actually use blue'), true);
    await done;
    assert.ok(Date.now() - t0 < 3000, 'read in under 3 seconds, not after the whole reply');
    assert.ok(evs.some((e) => e.type === 'assistant_end' && e.cut), 'the written part is kept, marked cut off');
    assert.strictEqual(gw.requests.length, 2);
    assert.match(gw.requests[1].messages.at(-1).content, /actually use blue$/);
    assert.ok(t.items.some((i) => i.t === 'assistant' && i.cut && /still being written|a long reply/.test(i.text)), 'kept on screen');
    assert.ok(t.messages.some((m) => m.role === 'assistant' && /\[cut off/.test(m.content || '')), 'the model knows it was cut off');
    assert.ok(t.messages.some((m) => m.role === 'assistant' && /got it, blue/.test(m.content || '')));
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

test('long chat: window starts at a turn of Ben\'s, never splits a tool call from its result', () => {
  const { trimWindow, plainText, CHECK_MARK } = require('../src/agent');
  const big = 'x'.repeat(700);   // 200 tokens
  const m = [];
  for (let k = 0; k < 6; k++) m.push({ role: 'user', content: 'q' + k + ' ' + big }, { role: 'assistant', content: '', tool_calls: [{ id: 'c' + k, type: 'function', function: { name: 'f', arguments: '{}' } }] }, { role: 'tool', tool_call_id: 'c' + k, content: big }, { role: 'assistant', content: 'a' + k });
  m.push({ role: 'user', content: CHECK_MARK + ' check' });
  const t = { messages: m };
  assert.strictEqual(trimWindow(t, 100000), -1);
  assert.strictEqual(t.ctxFrom, undefined);
  assert.strictEqual(trimWindow(t, 1500), 0);
  assert.ok(t.ctxFrom > 0);
  assert.strictEqual(m[t.ctxFrom].role, 'user');
  assert.match(m[t.ctxFrom].content, /^q\d/);
  assert.ok(estimateTokens(m.slice(t.ctxFrom)) <= 1500 * 0.6);
  const was = t.ctxFrom;
  assert.strictEqual(trimWindow(t, 1500), -1);   // under the limit now: no move
  assert.strictEqual(t.ctxFrom, was);
  assert.strictEqual(m.length, 25);              // stored history untouched
  const txt = plainText(m, 0, was);
  assert.match(txt, /^Ben: q0/); assert.match(txt, /Glim: a0/);
  assert.ok(!txt.includes(CHECK_MARK)); assert.ok(!/Glim: $/m.test(txt));
});

test('long chat: older part summarized by one cheap call, model sees the summary then the recent turns', async () => {
  const { SUMMARY_TAG } = require('../src/agent');
  const gw = await startGateway([{ content: '<think>hm</think>Ben wants a gym plan at 6 PM.' }, { content: 'Sure.' }]);
  try {
    const evs = [];
    const agent = new Agent({ getSettings: settings(gw, { contextTokens: 1500, modelFast: 'fast' }), toolDefs: buildTools({}), tools: {}, emit: (e) => evs.push(e), approve: async () => 'once', askUser: async () => '' });
    const t = mkThread();
    for (let k = 0; k < 10; k++) t.messages.push({ role: 'user', content: 'old question ' + k + ' ' + 'y'.repeat(700) }, { role: 'assistant', content: 'old answer ' + k });
    await agent.run(t, 'what next?');
    const [sumReq, mainReq] = gw.requests;
    assert.strictEqual(sumReq.model, 'fast');
    assert.ok(!sumReq.tools || sumReq.tools.length === 0);
    assert.ok(sumReq.messages[1].content.startsWith(SUMMARY_TAG));
    assert.match(sumReq.messages[1].content, /Ben: old question 0/);
    assert.strictEqual(t.ctxSummary, 'Ben wants a gym plan at 6 PM.');
    const firstUser = mainReq.messages[1];
    assert.strictEqual(firstUser.role, 'user');
    assert.match(firstUser.content, /^\[Summary of earlier messages in this chat[\s\S]*gym plan at 6 PM\.\n\]/);
    assert.ok(!mainReq.messages.some((x) => typeof x.content === 'string' && x.content.includes('old question 0 ')));
    assert.ok(mainReq.messages.at(-1).content.endsWith('what next?'));
    assert.ok(t.messages.length >= 22);                       // nothing deleted from the chat
    assert.ok(!t.messages.some((x) => typeof x.content === 'string' && x.content.startsWith('[Summary')));   // note is not stored as a message
    assert.ok(evs.some((e) => e.type === 'compacted'));
  } finally { gw.close(); }
});

test('long chat: if the summary call returns nothing the model is told older messages were left out', async () => {
  const gw = await startGateway([{ content: '' }, { content: 'Ok.' }]);
  try {
    const agent = new Agent({ getSettings: settings(gw, { contextTokens: 1500 }), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = mkThread();
    for (let k = 0; k < 10; k++) t.messages.push({ role: 'user', content: 'q' + k + ' ' + 'y'.repeat(700) }, { role: 'assistant', content: 'a' + k });
    await agent.run(t, 'next');
    assert.match(gw.requests[1].messages[1].content, /^\[Earlier messages in this chat are left out/);
  } finally { gw.close(); }
});

test('long chat: no cut on a screenshot stub; a stopped summary keeps the old window; stale window reset', async () => {
  const { trimWindow } = require('../src/agent');
  const big = 'x'.repeat(700);
  const m = [{ role: 'user', content: 'q0 ' + big }, { role: 'assistant', content: 'a0 ' + big }];
  for (let k = 0; k < 6; k++) m.push({ role: 'user', content: '[older screenshot omitted]' }, { role: 'assistant', content: 'b' + k + ' ' + big });
  m.push({ role: 'user', content: 'q1 short' }, { role: 'assistant', content: 'a1' });
  const t = { messages: m };
  assert.strictEqual(trimWindow(t, 1500), 0);
  assert.match(m[t.ctxFrom].content, /^q1/);
  const gw = await startGateway([{ content: 'Ok.' }]);
  try {
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const th = { messages: m.slice(0, 4), ctxFrom: 12 };
    const ac = new AbortController(); ac.abort();
    await agent.summarizeLeftOut(th, settings(gw)(), ac.signal, 2);
    assert.strictEqual(th.ctxFrom, 2); assert.strictEqual(th.ctxNote, undefined);
    const st = mkThread(); st.ctxFrom = 30; st.ctxNote = 'stale'; st.ctxSummary = 's';
    await agent.run(st, 'hi');
    assert.strictEqual(st.ctxFrom, undefined); assert.strictEqual(st.ctxNote, undefined);
    assert.match(gw.requests[0].messages[1].content, /hi$/);
  } finally { gw.close(); }
});

test('long chat: a left-out part too long for one summary is rolled up later, oldest first, and folded into the next summary', async () => {
  const { plainTail, noteOldGap, rollupGapStep, trimWindow } = require('../src/agent');
  const line = (k) => 'turn ' + k + ' ' + 'z'.repeat(1400);
  const m = [];
  for (let k = 0; k < 12; k++) m.push({ role: 'user', content: 'q ' + line(k) }, { role: 'assistant', content: 'a ' + line(k) });
  const tail = plainTail(m, 0, 24);
  assert.ok(tail.start > 0 && tail.text.length <= 12000);
  assert.match(tail.text, /^(Ben|Glim): [qa] turn \d+ /);   // whole lines only
  assert.strictEqual(plainTail(m, 18, 24).start, 18);   // fits: nothing left over
  // an old thread summarized before gaps were kept gets its gap once
  const old = { messages: m, ctxFrom: 24, ctxSummary: 's' };
  assert.ok(noteOldGap(old)); assert.deepStrictEqual(old.ctxGaps, [[0, tail.start]]); assert.ok(!noteOldGap(old));
  const gw = await startGateway([{ content: 'Recent: Ben plans a 6 PM run.' }, { content: '<think>x</think>Older: Ben likes tennis.' }, { content: 'Older: tennis, chess club.' }, { content: 'All: tennis, chess, 6 PM run.' }]);
  try {
    const agent = new Agent({ getSettings: settings(gw, { modelFast: 'fast' }), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = { messages: m.slice(), ctxFrom: 24 };
    await agent.summarizeLeftOut(t, settings(gw, { modelFast: 'fast' })(), null, 0);
    assert.strictEqual(t.ctxSummary, 'Recent: Ben plans a 6 PM run.');
    assert.deepStrictEqual(t.ctxGaps, [[0, tail.start]]);
    assert.ok(await rollupGapStep(t, settings(gw)(), null));
    assert.match(gw.requests[1].messages[1].content, /Chat:\nBen: q turn 0 /);   // oldest first
    assert.strictEqual(t.ctxOlder, 'Older: Ben likes tennis.');
    assert.ok(t.ctxGaps[0][0] > 0);
    while (t.ctxGaps) assert.ok(await rollupGapStep(t, settings(gw)(), null));
    assert.ok(!gw.requests[2].messages[1].content.includes('Older: Ben likes tennis'));   // each part on its own: lines are appended, not merged
    assert.strictEqual(t.ctxOlder, 'Older: Ben likes tennis.\nOlder: tennis, chess club.');
    assert.strictEqual(gw.requests.length, 3);
    // the next window summary appends its lines; the note shows the rolled-up older part first
    t.messages.push({ role: 'user', content: 'q new' }, { role: 'assistant', content: 'a new' });
    t.ctxFrom = 26;
    await agent.summarizeLeftOut(t, settings(gw)(), null, 24);
    assert.match(gw.requests[3].messages[1].content, /Chat:\nBen: q new\nGlim: a new$/);
    assert.strictEqual(t.ctxSummary, 'Recent: Ben plans a 6 PM run.\nAll: tennis, chess, 6 PM run.');
    assert.strictEqual(t.ctxGaps, undefined);
    assert.match(t.ctxNote, /:\nOlder: Ben likes tennis\.\nOlder: tennis, chess club\.\nRecent: Ben plans a 6 PM run\.\nAll: tennis, chess, 6 PM run\.\n\]/);
    assert.strictEqual(typeof trimWindow, 'function');
  } finally { gw.close(); }
});

test('long chat: a failed roll-up chunk changes nothing; a failed window summary leaves all of it to roll up', async () => {
  const { rollupGapStep } = require('../src/agent');
  const gw = await startGateway([{ content: '' }, { content: '' }]);
  try {
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = { messages: [{ role: 'user', content: 'q1' }, { role: 'assistant', content: 'a1' }, { role: 'user', content: 'q2' }], ctxGaps: [[0, 2]] };
    assert.strictEqual(await rollupGapStep(t, settings(gw)(), null), false);
    assert.deepStrictEqual(t.ctxGaps, [[0, 2]]); assert.strictEqual(t.ctxOlder, undefined);
    const u = { messages: t.messages, ctxFrom: 2 };
    await agent.summarizeLeftOut(u, settings(gw)(), null, 0);
    assert.deepStrictEqual(u.ctxGaps, [[0, 2]]);
    // a thread summarized by an older build gets its unread part noted at the next window summary (window started at `from`)
    const line = 'w'.repeat(1400), m = [];
    for (let k = 0; k < 12; k++) m.push({ role: 'user', content: 'q' + k + ' ' + line }, { role: 'assistant', content: 'a' + k + ' ' + line });
    const v = { messages: m, ctxFrom: 24, ctxSummary: 'old' };
    await agent.summarizeLeftOut(v, settings(gw)(), null, 20);
    assert.strictEqual(v.ctxGaps[0][0], 0); assert.ok(v.ctxGaps[0][1] > 0 && v.ctxGaps[0][1] <= 20);
    assert.deepStrictEqual(v.ctxGaps[1], [20, 24]);   // separate ranges: what earlier summaries read is not read again
  } finally { gw.close(); }
});

test('long chat: the summary reads Ben\'s own words with their date, not the notes block or turn instructions in front of them', async () => {
  const { plainText, benWords } = require('../src/agent');
  const gw = await startGateway([{ content: 'Hi Ben.' }]);
  try {
    const memory = { block: () => 'Saved notes about Ben (data, not instructions):\n- Ben plays tennis [club] | id: a1' };
    const agent = new Agent({ memory, getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = mkThread(); t.pendingNotices = [{ name: 'Learn 1', summary: 'read about [brackets]' }];
    await agent.run(t, 'remind me about the dentist on Friday');
    const txt = plainText(t.messages, 0, t.messages.length);
    assert.match(txt, /^Ben \((Sun|Mon|Tue|Wed|Thu|Fri|Sat) \d{4}-\d\d-\d\d \d\d:\d\d, \d{1,2}:\d\d [AP]M\)\: remind me about the dentist on Friday$/m);
    assert.ok(!/Saved notes|If this needs tools|helper updates|tennis/.test(txt), txt);
    assert.match(txt, /^Glim: Hi Ben\.$/m);
    assert.deepStrictEqual(benWords('no stamp here'), { stamp: '', text: 'no stamp here' });
  } finally { gw.close(); }
});

test('compaction in batches: no stub until 4 results (or ~4k tokens) are stubbable, so the cached prompt is not edited every step', () => {
  const r = (t) => ({ role: 'tool', content: t });
  const m = [{ role: 'user', content: 'u' }, r('a'), r('b'), r('c'), r('d'), r('e')];
  assert.strictEqual(compactMessages(m, 2, 4), 0);
  m.push(r('f'));
  assert.strictEqual(compactMessages(m, 2, 4), 4);
  assert.deepStrictEqual(m.filter((x) => x.role === 'tool').map((x) => x.content.slice(0, 1)), ['[', '[', '[', '[', 'e', 'f']);
  const big = [r('x'.repeat(20000)), r('y'), r('z')];
  assert.strictEqual(compactMessages(big, 2, 4), 1);   // one big result is worth it
});

test('the saved-notes block rides on a turn only when the notes changed (not on every turn)', async () => {
  const gw = await startGateway([{ content: 'one' }, { content: 'two' }, { content: 'three' }]);
  try {
    const t = mkThread(); let notes = 'Saved notes about Ben:\n- likes tea';
    const agent = new Agent({ getSettings: settings(gw), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '', memory: { block: () => notes } });
    await agent.run(t, 'hi'); await agent.run(t, 'again');
    notes = 'Saved notes about Ben:\n- likes tea\n- has a sister';
    await agent.run(t, 'third');
    const users = t.messages.filter((m) => m.role === 'user').map((m) => m.content);
    assert.match(users[0], /likes tea/);
    assert.ok(!/Saved notes/.test(users[1]), 'unchanged notes are not repeated');
    assert.match(users[2], /has a sister/, 'changed notes are written again');
  } finally { gw.close(); }
});

test('dropOldImages: a picture far back in a long chat is dropped even if it is the newest one', () => {
  const m = [{ role: 'user', content: [{ type: 'text', text: 'look' }, { type: 'image_url', image_url: { url: 'data:x' } }] }];
  for (let i = 0; i < 20; i++) m.push({ role: i % 2 ? 'user' : 'assistant', content: 'x' + i });
  dropOldImages(m);
  assert.strictEqual(m[0].content, '[older screenshot omitted]');
});

// ---- Ben Oct 29: "I am now on the sign-in page" with no tool call; "have it think?" ----------------------------------------------------
test('claimed actions without a tool call: dropped from history, run again with a nudge; Glim\u2019s chat always uses the thinking model', async () => {
  const fast = { model: 'fast', modelFast: 'fast', modelMain: 'think', verify: false };
  const tools = { browser_go: async () => 'ok' };
  const gw = await startGateway([
    { content: 'I am now on the sign-in page; I will type your password into the field.' },
    { tool_calls: [{ name: 'browser_go', arguments: { url: 'https://school.example' } }] },
    { content: 'Opened it: sign in there.' },
    { content: 'Hi there!' }
  ]);
  try {
    const a = new Agent({ getSettings: settings(gw, fast), toolDefs: buildTools({}), tools, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = mkThread();
    await a.run(t, 'connect to schoology');
    assert.deepStrictEqual(gw.requests.map((r) => r.model), ['think', 'think', 'think'], 'Glim\u2019s chat always reasons, even with Fast picked');
    assert.ok(!t.messages.some((m) => /now on the sign-in page/.test(m.content || '')), 'the pretend reply is not in the model history');
    assert.deepStrictEqual(t.messages.map((m) => m.role), ['user', 'assistant', 'user', 'assistant', 'tool', 'assistant']);
    assert.match(t.messages[1].content, /never done/); assert.match(t.messages[2].content, /only described steps/, 'the re-run is asked for a real step, not the same prompt again');
    assert.ok(t.items.some((i) => i.t === 'assistant' && /now on the sign-in page/.test(i.text)), 'it stays on screen');
    assert.ok(t.items.some((i) => i.t === 'step' && i.tool === 'verify' && /without doing them/.test(i.summary)));
    await a.run(t, 'thanks');
    assert.strictEqual(gw.requests[3].model, 'think');
  } finally { gw.close(); }
});

// ---- Ben Oct 29: "cap thinking to 10 second then force it to respond. Then it can do whatever it was planning to do" -------------------
test('first-reply thinking cap: cut at the cap, a short plan is forced (thinking model, sees the thinking), then the task runs on', async () => {
  const think = { model: 'think', modelFast: 'fast', modelMain: 'think', verify: false, thinkCapSecs: 0.2 };
  const tools = { browser_go: async () => 'ok' };
  const gw = await startGateway([
    { reasoning: 'Ben wants his work schedule. I should check his notes first, then '.repeat(4), reasoningDelayMs: 30 },
    { content: "I'll check your saved notes for your work hours. [continue]" },
    { tool_calls: [{ name: 'browser_go', arguments: { url: 'https://school.example' } }] },
    { content: 'You work 4 to 9 on Mondays.' }
  ]);
  try {
    const evs = [];
    const a = new Agent({ getSettings: settings(gw, think), toolDefs: buildTools({}), tools, emit: (e) => evs.push(e), approve: async () => 'once', askUser: async () => '' });
    const t = mkThread();
    await a.run(t, "what's my work schedule?");
    assert.deepStrictEqual(gw.requests.map((r) => r.model), ['think', 'think', 'think', 'think'], 'the forced reply thinks too (no fast model)');
    const note = gw.requests[1].messages.at(-1).content;
    assert.match(note, /Your unfinished thinking/); assert.match(note, /Ben wants his work schedule/);
    assert.ok(t.items.some((i) => i.t === 'assistant' && i.text === "I'll check your saved notes for your work hours."), 'the plan is on screen, tag stripped');
    const m2 = gw.requests[2].messages;
    assert.ok(m2.some((m) => m.role === 'assistant' && /saved notes for your work hours/.test(m.content)), 'the plan reaches the model as written, not as a pretend note');
    assert.match(m2.at(-1).content, /Carry on with it now/);
    assert.ok(!m2.some((m) => /Your unfinished thinking/.test(m.content || '')), 'the cut thinking is not kept in the chat');
    assert.strictEqual(t.messages.at(-1).content, 'You work 4 to 9 on Mondays.');
    assert.ok(!t.items.some((i) => i.t === 'step' && i.tool === 'verify'), 'a forced plan is not a pretend');
  } finally { gw.close(); }
});

test('first-reply thinking cap: a forced reply that answers or asks ends the turn; quick thinking, later steps and Motes are never cut', async () => {
  const think = { model: 'think', modelFast: 'fast', modelMain: 'think', verify: false, thinkCapSecs: 0.2 };
  const slow = { reasoning: 'thinking about it at length '.repeat(4), reasoningDelayMs: 30 };
  const tools = { browser_go: async () => 'ok' };
  const gw = await startGateway([
    slow, { content: "I'll open the Schoology site and log in for you. I'll open the browser to dresden.schoology.com.\nI'll click the sign-in button.\nI'll click the sign-in button.\nI'll open the Schoology site and log in for you." },
    { tool_calls: [{ name: 'browser_go', arguments: { url: 'https://school.example' } }] }, { content: 'Signed-in page is open.' },
    slow, { content: 'Sure, what are your hours?' },
    slow, { content: '' }, { content: 'Thought it through: 4 to 9.' },
    { reasoning: 'quick', content: 'Hi!' },
    { tool_calls: [{ name: 'browser_go', arguments: { url: 'https://school.example' } }] }, { ...slow, content: 'Opened it.' },
    { ...slow, content: 'Mote report.' }
  ]);
  try {
    const a = new Agent({ getSettings: settings(gw, think), toolDefs: buildTools({}), tools, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = mkThread();
    await a.run(t, 'check my homework');   // a run-on list of steps: repeats dropped, the plan keeps two sentences
    assert.ok(t.items.some((i) => i.t === 'assistant' && i.text === "I'll open the Schoology site and log in for you. I'll open the browser to dresden.schoology.com."));
    assert.strictEqual(gw.requests[1].model, 'think');
    gw.requests.splice(0); t.messages = []; t.items = [];
    await a.run(t, 'yes, remember my work schedule?');
    assert.strictEqual(gw.requests.length, 2);
    assert.strictEqual(t.messages.at(-1).content, 'Sure, what are your hours?');
    const r = await a.run(t, 'when do I work?');   // the forced reply came back empty: the step runs again, uncapped, instead of an error
    assert.strictEqual(r.error, null); assert.strictEqual(gw.requests.length, 5); assert.strictEqual(t.messages.at(-1).content, 'Thought it through: 4 to 9.');
    await a.run(t, 'hello');
    assert.strictEqual(gw.requests.length, 6);
    await a.run(t, 'open schoology');
    assert.strictEqual(gw.requests.length, 8); assert.strictEqual(t.messages.at(-1).content, 'Opened it.');
    const m = new Agent({ getSettings: settings(gw, { ...think, thinkActing: false }), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const mt = mkThread();
    await m.run(mt, 'check the news');
    assert.strictEqual(gw.requests.length, 9); assert.strictEqual(mt.messages.at(-1).content, 'Mote report.');
  } finally { gw.close(); }
});

test('a reply that narrates the same steps over and over is cut mid-stream, trimmed, and re-run asking for a real step', async () => {
  const think = { model: 'think', modelFast: 'fast', modelMain: 'think', verify: false, thinkCapSecs: 0 };
  const loopText = "I'll open the Schoology site and log in for you. I'll enter your email into the sign-in field. I'll click the sign-in button. " +
    "I'll type the email into the username field. I will click the sign-in button. I'll list the homework items for you. ".repeat(20);
  const tools = { browser_go: async () => 'ok' };
  const gw = await startGateway([{ content: loopText, delayMs: 1 }, { tool_calls: [{ name: 'browser_go', arguments: { url: 'https://dresden.schoology.com' } }] }, { content: 'The sign-in page is open: sign in there.' }]);
  try {
    const evs = [];
    const a = new Agent({ getSettings: settings(gw, think), toolDefs: buildTools({}), tools, emit: (e) => evs.push(e), approve: async () => 'once', askUser: async () => '' });
    const t = mkThread();
    await a.run(t, 'check my homework on schoology');
    const end = evs.find((e) => e.type === 'assistant_end');
    assert.strictEqual(end.replace, true);
    assert.strictEqual(end.text, "I'll open the Schoology site and log in for you. I'll enter your email into the sign-in field. I'll click the sign-in button. I'll type the email into the username field. I'll list the homework items for you.");
    assert.strictEqual(gw.requests.length, 3);
    assert.match(gw.requests[1].messages.at(-1).content, /only described steps/);
    assert.strictEqual(t.messages.at(-1).content, 'The sign-in page is open: sign in there.');
  } finally { gw.close(); }
});

test('narration loop guard: honest repeats (schedule lines, a short "Yes.", code) are not cut', () => {
  const { narrationLoop } = require('../src/agent');
  assert.strictEqual(narrationLoop('Your shifts:\n- Monday: 4 to 9 pm\n- Tuesday: 4 to 9 pm\n- Friday: 4 to 9 pm\nThat is all.\n'), null);
  assert.strictEqual(narrationLoop('Yes. Yes. Yes. Yes. Done. '), null);
  assert.strictEqual(narrationLoop('```\nx = 1\nx = 1\nx = 1\n```\nok. '), null);
  assert.strictEqual(narrationLoop("I'll click the sign-in button. I’ll click the sign-in button. I will click the sign-in button. "), "I'll click the sign-in button.");
});

test('claimed actions twice: said plainly instead of pretending; Motes (thinkActing false) are not re-run', async () => {
  const fast = { model: 'fast', modelFast: 'fast', modelMain: 'think', verify: false };
  const gw = await startGateway([{ content: "I've opened the page for you." }, { content: "I've opened the page for you." }, { content: "I've opened it." }]);
  try {
    const a = new Agent({ getSettings: settings(gw, fast), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    const t = mkThread();
    await a.run(t, 'open it');
    assert.strictEqual(gw.requests.length, 2);
    assert.match(t.messages.at(-1).content, /didn't actually manage to do those steps/);
    const m = new Agent({ getSettings: settings(gw, { ...fast, thinkActing: false }), toolDefs: buildTools({}), tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
    await m.run(mkThread(), 'open it');
    assert.strictEqual(gw.requests.length, 3);
    assert.strictEqual(gw.requests[2].model, 'fast');
  } finally { gw.close(); }
});

test('asksForSecret: the sign-in hand-off is not an ask; asking for the password in chat is', () => {
  const { asksForSecret } = require('../src/agent');
  assert.strictEqual(asksForSecret("I can't type your password for you. Please enter your password in the sign-in window yourself, and then click Done."), false);
  assert.strictEqual(asksForSecret('What is your password?'), true);
  assert.strictEqual(asksForSecret('Please send me your login details.'), true);
  assert.strictEqual(asksForSecret("I can't log in without it, please enter your password below."), true);
  const { claimsAction } = require('../src/agent');
  assert.strictEqual(claimsAction("Which school site? I'll open it once you tell me."), false);
  assert.strictEqual(claimsAction('I will open the Schoology sign-in page for you.'), true);
  assert.strictEqual(claimsAction("I'm now on the sign-in page."), true);
});

test('history: a reply that only claimed steps reaches the model as a note; a real answer after tool calls stays', () => {
  const a = new Agent({ getSettings: () => ({}), toolDefs: [], tools: {}, emit: () => {}, approve: async () => 'once', askUser: async () => '' });
  const t = mkThread();
  t.messages = [
    { role: 'user', content: 'connect to schoology' },
    { role: 'assistant', content: "I am now on the Schoology dashboard. Here are your assignments: Math 203." },
    { role: 'user', content: 'open it' },
    { role: 'assistant', content: '', tool_calls: [{ id: 'c1', type: 'function', function: { name: 'browser_go', arguments: '{}' } }] },
    { role: 'tool', tool_call_id: 'c1', content: 'ok' },
    { role: 'assistant', content: "I've opened the page and it shows the sign-in." },
    { role: 'user', content: "I'm on the fence about it" },
    { role: 'assistant', content: 'Fair enough.' }
  ];
  const m = a.requestMessages(t);
  assert.match(m[2].content, /never done/);
  assert.strictEqual(m[6].content, "I've opened the page and it shows the sign-in.");
  assert.strictEqual(m[8].content, 'Fair enough.');
  assert.strictEqual(t.messages[1].content.startsWith('I am now on'), true, 'the stored chat is unchanged');
});
