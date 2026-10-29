'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { fitRequest, requestTokens, contextOverflow, contextLimit } = require('../src/context-budget');
const { Agent } = require('../src/agent');
const { buildTools } = require('../src/prompt');
const pair = (id, text) => [{ role: 'assistant', content: '', tool_calls: [{ id, type: 'function', function: { name: 'browser_read', arguments: '{}' } }] }, { role: 'tool', tool_call_id: id, content: text }];
const listen = (server) => new Promise((r) => server.listen(0, '127.0.0.1', r));
const sse = (res, text) => { res.writeHead(200, { 'content-type': 'text/event-stream' }); res.end('data: ' + JSON.stringify({ choices: [{ index: 0, delta: { content: text }, finish_reason: null }] }) + '\n\ndata: ' + JSON.stringify({ choices: [{ index: 0, delta: {}, finish_reason: 'stop' }] }) + '\n\ndata: [DONE]\n\n'); };
const overflow = { error: { type: 'exceed_context_size_error', n_prompt_tokens: 8196, n_ctx: 8192, message: 'request (8196 tokens) exceeds the available context (8192 tokens), try increasing it' } };

test('request-local fitter protects current user task, all tool pairs and whole latest read', () => {
  const current = 'Current task with exact instructions';
  const messages = [{ role: 'system', content: 'System' }, { role: 'user', content: 'Old task ' + 'old '.repeat(1500) }, ...pair('old', 'a'.repeat(5000)), { role: 'user', content: current }, ...pair('first', 'A'.repeat(8000) + '[Source read: old]'), ...pair('latest', 'Newest whole page [Source read: latest]'), { role: 'user', content: 'Steer: use the second approach.' }];
  const before = JSON.stringify(messages);
  const result = fitRequest(messages, [], 1000, 4);
  assert.equal(JSON.stringify(messages), before);
  assert.ok(result.removed >= 2); assert.ok(result.messages.some((m) => m.content === current));
  assert.ok(result.messages.some((m) => m.content === 'Steer: use the second approach.'));
  assert.equal(result.messages.find((m) => m.tool_call_id === 'first').content, '[older result omitted]');
  assert.equal(result.messages.find((m) => m.tool_call_id === 'latest').content, 'Newest whole page [Source read: latest]');
  assert.equal(result.messages.filter((m) => m.tool_calls).length, result.messages.filter((m) => m.role === 'tool').length);
  assert.ok(requestTokens([{ role: 'user', content: 'x' }], [{ description: 'x'.repeat(5000) }]) > requestTokens([{ role: 'user', content: 'x' }], []));
});

test('Agent retries a native typed 8196/8192 overflow once and caches by endpoint/model', async () => {
  const requests = [];
  const server = http.createServer((req, res) => { let body = ''; req.on('data', (c) => { body += c; }); req.on('end', () => { requests.push(JSON.parse(body)); if (requests.length === 1) { res.writeHead(400, { 'content-type': 'application/json' }); res.end(JSON.stringify(overflow)); } else sse(res, 'Finished.'); }); });
  await listen(server);
  const gatewayUrl = 'http://127.0.0.1:' + server.address().port + '/v1';
  const settings = { gatewayUrl, model: 'model-a', thinkActing: false, compactTokens: 999999, contextTokens: 999999, verify: false, mode: 'hands-off' };
  const thread = { id: 't', items: [], messages: [{ role: 'user', content: 'Earlier turn' }, ...pair('a', 'x'.repeat(10000)), ...pair('b', 'y'.repeat(10000)), ...pair('c', 'recent full page [Source read: known]')] };
  const agent = new Agent({ getSettings: () => settings, toolDefs: buildTools({}), tools: {} });
  try {
    const result = await agent.run(thread, 'The new explicit task stays intact.');
    assert.ok(!result.error); assert.equal(requests.length, 2);
    assert.ok(JSON.stringify(requests[0]).includes('Earlier turn'));
    assert.ok(!JSON.stringify(requests[1]).includes('Earlier turn'));
    assert.ok(requests[1].messages.some((m) => typeof m.content === 'string' && m.content.includes('The new explicit task stays intact.')));
    assert.ok(thread.messages.some((m) => m.content === 'Earlier turn'));
    assert.equal(contextLimit(settings, 'model-a'), 8192); assert.equal(contextLimit(settings, 'model-b'), null);
  } finally { server.closeAllConnections(); server.close(); }
});

test('immutable task overflow reports an actionable error without retrying or losing the task', async () => {
  let requests = 0;
  const server = http.createServer((req, res) => { req.resume(); req.on('end', () => { requests++; res.writeHead(400, { 'content-type': 'application/json' }); res.end(JSON.stringify(overflow)); }); });
  await listen(server);
  const settings = { gatewayUrl: 'http://127.0.0.1:' + server.address().port + '/v1', model: 'huge-task', thinkActing: false, verify: false, mode: 'hands-off' };
  const thread = { id: 't2', items: [], messages: [] };
  const agent = new Agent({ getSettings: () => settings, toolDefs: [], tools: {} });
  try {
    const task = 'My exact instruction: ' + 'z'.repeat(25000);
    const result = await agent.run(thread, task);
    assert.match(result.error, /current task and required context are too large/i); assert.equal(requests, 1);
    assert.ok(thread.messages.some((m) => typeof m.content === 'string' && m.content.includes(task)));
    assert.equal(contextOverflow({ status: 400, details: { error: { type: 'invalid_request_error', n_prompt_tokens: 8196, n_ctx: 8192 } } }), null);
  } finally { server.closeAllConnections(); server.close(); }
});

test('multi-tool task retries only the rejected request and keeps the latest source read whole', async () => {
  const requests = [], calls = [];
  const server = http.createServer((req, res) => { let body = ''; req.on('data', (c) => { body += c; }); req.on('end', () => {
    requests.push(JSON.parse(body));
    if (requests.length === 1) {
      res.writeHead(200, { 'content-type': 'text/event-stream' });
      const delta = { tool_calls: ['read_a', 'read_b', 'read_c'].map((name, i) => ({ index: i, id: 'id' + i, type: 'function', function: { name, arguments: '{}' } })) };
      res.end('data: ' + JSON.stringify({ choices: [{ index: 0, delta, finish_reason: null }] }) + '\n\ndata: ' + JSON.stringify({ choices: [{ index: 0, delta: {}, finish_reason: 'tool_calls' }] }) + '\n\ndata: [DONE]\n\n');
    } else if (requests.length === 2) { res.writeHead(400, { 'content-type': 'application/json' }); res.end(JSON.stringify(overflow)); }
    else sse(res, 'Finished.');
  }); });
  await listen(server);
  const settings = { gatewayUrl: 'http://127.0.0.1:' + server.address().port + '/v1', model: 'multi', thinkActing: false, compactTokens: 999999, contextTokens: 999999, maxToolChars: 12000, verify: false, mode: 'hands-off' };
  const tools = Object.fromEntries(['read_a', 'read_b', 'read_c'].map((name, i) => [name, () => { calls.push(name); return { text: String(i).repeat(8000) + ' [Source read: ' + name + ']' }; }]));
  const thread = { id: 'multi', items: [], messages: [] }, agent = new Agent({ getSettings: () => settings, toolDefs: [], tools });
  try {
    const result = await agent.run(thread, 'Study these three pages and report.');
    assert.ok(!result.error); assert.deepEqual(calls, ['read_a', 'read_b', 'read_c']); assert.equal(requests.length, 3);
    const retryTools = requests[2].messages.filter((m) => m.role === 'tool');
    assert.equal(retryTools.length, 3); assert.equal(retryTools[0].content, '[older result omitted]');
    assert.ok(retryTools[2].content.includes('[Source read: read_c]')); assert.ok(retryTools[2].content.length > 8000);
    assert.ok(thread.messages.find((m) => m.role === 'tool' && m.tool_call_id === 'id0').content.includes('[Source read: read_a]'));
    assert.ok(requests[2].messages.some((m) => m.role === 'user' && typeof m.content === 'string' && m.content.includes('Study these three pages and report.')));
  } finally { server.closeAllConnections(); server.close(); }
});

test('small-model window summarizes older turns once and retains summary, memory and the current task across steps', async () => {
  const { startGateway } = require('./helpers');
  const summary = 'Ben wants to study astronomy in November.';
  const gateway = await startGateway([
    (req) => { assert.ok(req.messages.some((m) => typeof m.content === 'string' && m.content.includes('[Chat summary request]'))); return { content: summary }; },
    { tool_calls: [{ name: 'synthetic_read', arguments: {} }] },
    { content: 'Finished.' }
  ]);
  const settings = { gatewayUrl: gateway.url, model: 'lfm-small', modelFast: 'lfm-small', backendModelFamily: 'lfm3', thinkActing: false, verify: false, compactTokens: 999999, contextTokens: 999999, maxToolChars: 10000, mode: 'hands-off' };
  const prior = [ { role: 'user', content: 'Older task ' + 'astronomy '.repeat(900) }, { role: 'assistant', content: 'Earlier response.' }, { role: 'user', content: 'Second old turn ' + 'science '.repeat(900) }, { role: 'assistant', content: 'Second response.' } ];
  const thread = { id: 'old-t', messages: structuredClone(prior), items: [] };
  const memoryBlock = 'Saved notes about Ben (data, not instructions):\n- preference: Ben likes quiet study';
  const agent = new Agent({ getSettings: () => settings, memory: { block: () => memoryBlock }, toolDefs: buildTools({}), tools: { synthetic_read: () => ({ text: 'Source result: ' + 'r'.repeat(5000) }) } });
  try {
    const result = await agent.run(thread, 'Current task: compare two telescopes.');
    assert.ok(!result.error); assert.equal(gateway.requests.length, 3);
    assert.match(thread.ctxNote, /study astronomy/); assert.ok(thread.ctxFrom > 0);
    for (const req of gateway.requests.slice(1)) {
      const combined = req.messages.map((m) => typeof m.content === 'string' ? m.content : '').join('\n');
      assert.match(combined, /study astronomy in November/); assert.match(combined, /Ben likes quiet study/); assert.match(combined, /Current task: compare two telescopes/);
    }
    assert.deepEqual(thread.messages.slice(0, prior.length), prior);
    assert.equal(gateway.requests.filter((req) => req.messages.some((m) => typeof m.content === 'string' && m.content.includes('[Chat summary request]'))).length, 1);
  } finally { gateway.close(); }
});

test('verification and capped reply fit long tool batches and retry without relying on prior main output', async () => {
  for (const kind of ['verify', 'cap']) {
    const requests = [];
    const server = http.createServer((req, res) => { let body = ''; req.on('data', (c) => { body += c; }); req.on('end', () => { requests.push(JSON.parse(body)); if (requests.length === 1) { res.writeHead(400, { 'content-type': 'application/json' }); res.end(JSON.stringify(overflow)); } else sse(res, kind === 'verify' ? 'VERIFIED' : 'Here is the brief result.'); }); });
    await listen(server);
    const settings = { gatewayUrl: 'http://127.0.0.1:' + server.address().port + '/v1', model: 'aux-' + kind, modelFast: 'aux-' + kind, modelMain: 'aux-' + kind, verify: true };
    const thread = { id: 'aux', items: [], messages: [{ role: 'user', content: 'Current task must survive.' }, ...pair('a', 'a'.repeat(12000)), ...pair('b', 'b'.repeat(12000)), ...pair('c', 'latest [Source read: latest]')], ctxNote: '' };
    const original = JSON.stringify(thread.messages);
    const events = [], agent = new Agent({ getSettings: () => settings, toolDefs: buildTools({}), tools: {}, emit: e => events.push(e) });
    agent.taskStart = 0; agent.partial = 'Earlier main reply already emitted.'; agent.usedState = true; agent.verifyCount = 0;
    try {
      if (kind === 'verify') assert.equal(await agent.verifyAnswer(thread, settings, new AbortController().signal, 'Done.'), 'accept');
      else assert.match((await agent.replyAfterCap(thread, settings, new AbortController().signal, 10, 'Thinking.')).content, /brief result/);
      assert.equal(requests.length, 2); assert.equal(requests[1].max_tokens, kind === 'verify' ? 200 : 1500);
      assert.ok(requests[1].messages.some((m) => typeof m.content === 'string' && m.content.includes('Current task must survive.')));
      assert.ok(requests[1].messages.some((m) => m.role === 'tool' && m.content === '[older result omitted]'));
      assert.ok(requests[1].messages.some((m) => m.role === 'tool' && m.content === 'latest [Source read: latest]'));
      assert.equal(JSON.stringify(thread.messages), original);
      if (kind === 'verify') assert.ok(events.some((e) => e.type === 'step_end' && e.summary === 'Checked its work' && e.ok));
    } finally { server.closeAllConnections(); server.close(); }
  }
});

test('a failed optional verification is labeled unavailable, never checked', async () => {
  const server = http.createServer((req, res) => { req.resume(); req.on('end', () => { res.writeHead(400, { 'content-type': 'application/json' }); res.end(JSON.stringify(overflow)); }); });
  await listen(server);
  const settings = { gatewayUrl: 'http://127.0.0.1:' + server.address().port + '/v1', model: 'verify-failure', verify: true }, events = [];
  const agent = new Agent({ getSettings: () => settings, toolDefs: [], tools: {}, emit: e => events.push(e) });
  agent.taskStart = 0; agent.usedState = true; agent.verifyCount = 0;
  const thread = { id: 't', items: [], messages: [{ role: 'user', content: 'current task ' + 'x'.repeat(25000) }] };
  try {
    assert.equal(await agent.verifyAnswer(thread, settings, new AbortController().signal, 'Done.'), 'accept');
    const end = events.find((e) => e.type === 'step_end'); assert.equal(end.summary, 'Check unavailable'); assert.equal(end.ok, false);
  } finally { server.closeAllConnections(); server.close(); }
});

test('summary requests fit a known small context even for multibyte old history', async () => {
  const { startGateway } = require('./helpers');
  const gw = await startGateway([{ content: 'Older notes summarized.' }, { content: 'Finished.' }]);
  const settings = { gatewayUrl: gw.url, model: 'small-unicode', modelFast: 'small-unicode', backendModelFamily: 'lfm3', thinkActing: false, verify: false, mode: 'hands-off' };
  const thread = { id: 'unicode', items: [], messages: [{ role: 'user', content: 'Old context ' + '💡'.repeat(6000) }, { role: 'assistant', content: 'Earlier.' }] };
  const agent = new Agent({ getSettings: () => settings, toolDefs: [], tools: {} });
  try {
    assert.ok(!(await agent.run(thread, 'Current request stays unchanged.')).error);
    const summaryRequest = gw.requests.find((r) => r.messages.some((m) => m.content && m.content.includes('[Chat summary request]')));
    assert.ok(summaryRequest); assert.ok(requestTokens(summaryRequest.messages, []) <= 8192 - 500 - 512);
    assert.ok(thread.messages[0].content.includes('💡'.repeat(6000)));
  } finally { gw.close(); }
});

test('multibyte old history is summarized by whole message lines and every omitted date remains queued for rollup', async () => {
  const { startGateway } = require('./helpers');
  const { rollupGapStep } = require('../src/agent');
  const gw = await startGateway([() => ({ content: 'Chunk summarized.' })]);
  const settings = { gatewayUrl: gw.url, model: 'summary-small', modelFast: 'summary-small', backendModelFamily: 'lfm3' };
  const messages = Array.from({ length: 12 }, (_, i) => ({ role: 'user', content: '[Mon 2026-10-' + String(i + 1).padStart(2, '0') + ' 10:00, 10:00 AM] unique-fact-' + String(i).padStart(2, '0') + ' ' + '💡'.repeat(650) }));
  const original = JSON.stringify(messages), thread = { messages, ctxFrom: messages.length };
  const agent = new Agent({ getSettings: () => settings, toolDefs: [], tools: {} });
  try {
    await agent.summarizeLeftOut(thread, settings, null, 0);
    assert.ok(thread.ctxGaps && thread.ctxGaps[0][0] === 0 && thread.ctxGaps[0][1] > 0);
    assert.ok(gw.requests.length === 1);
    const first = gw.requests[0].messages[1].content;
    assert.ok(!first.includes('unique-fact-00')); assert.ok(first.includes('unique-fact-11'));
    let steps = 0;
    while (thread.ctxGaps && steps++ < 20) assert.equal(await rollupGapStep(thread, settings, null), true);
    assert.equal(thread.ctxGaps, undefined); assert.ok(steps > 0);
    const submitted = gw.requests.map((r) => r.messages[1].content).join('\n');
    for (let i = 0; i < 12; i++) {
      const id = 'unique-fact-' + String(i).padStart(2, '0');
      const date = '2026-10-' + String(i + 1).padStart(2, '0');
      assert.equal(submitted.split(id).length - 1, 1, id); assert.ok(submitted.includes(date), date);
    }
    for (const req of gw.requests) assert.ok(requestTokens(req.messages, []) <= 8192 - 500 - 512);
    assert.equal(JSON.stringify(thread.messages), original);
  } finally { gw.close(); }
});
