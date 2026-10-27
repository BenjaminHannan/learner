'use strict';
const test = require('node:test');
const assert = require('node:assert');
const { streamChat, extractFallbackCalls } = require('../src/llm');
const { startGateway } = require('./helpers');

test('streams content, reasoning and accumulates tool_calls by index', async () => {
  const gw = await startGateway([{ reasoning: 'let me think about it', content: 'Hello there, Ben', tool_calls: [{ name: 'web_search', arguments: { query: 'ramen near me' } }, { name: 'browser_go', arguments: { url: 'https://example.com' } }] }]);
  try {
    let t = '', r = '';
    const out = await streamChat({ gatewayUrl: gw.url, model: 'm', messages: [{ role: 'user', content: 'hi' }], tools: [{ type: 'function', function: { name: 'x', parameters: {} } }], onText: (d) => (t += d), onReasoning: (d) => (r += d) });
    assert.strictEqual(out.content, 'Hello there, Ben');
    assert.strictEqual(t, 'Hello there, Ben');
    assert.strictEqual(out.reasoning, 'let me think about it');
    assert.strictEqual(r, out.reasoning);
    assert.strictEqual(out.toolCalls.length, 2);
    assert.deepStrictEqual(JSON.parse(out.toolCalls[0].arguments), { query: 'ramen near me' });
    assert.strictEqual(out.toolCalls[1].name, 'browser_go');
    assert.strictEqual(out.finishReason, 'tool_calls');
    assert.strictEqual(gw.requests[0].stream, true);
    assert.ok(gw.requests[0].tools.length === 1 && gw.requests[0].model === 'm');
  } finally { gw.close(); }
});

test('accepts delta.reasoning as well as reasoning_content', async () => {
  const http = require('http');
  const s = http.createServer((q, res) => { res.writeHead(200, { 'content-type': 'text/event-stream' }); res.write('data: {"choices":[{"delta":{"reasoning":"abc"}}]}\n\ndata: {"choices":[{"delta":{"content":"ok"},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n'); res.end(); });
  await new Promise((r) => s.listen(0, '127.0.0.1', r));
  try {
    const out = await streamChat({ gatewayUrl: 'http://127.0.0.1:' + s.address().port + '/v1', model: 'm', messages: [] });
    assert.strictEqual(out.reasoning, 'abc'); assert.strictEqual(out.content, 'ok');
  } finally { s.close(); }
});

test('HTTP errors surface as exceptions', async () => {
  const http = require('http');
  const s = http.createServer((q, res) => { res.writeHead(500); res.end('boom'); });
  await new Promise((r) => s.listen(0, '127.0.0.1', r));
  try {
    await assert.rejects(streamChat({ gatewayUrl: 'http://127.0.0.1:' + s.address().port + '/v1', model: 'm', messages: [] }), /500/);
  } finally { s.close(); }
});

test('abort cancels the stream', async () => {
  const gw = await startGateway([{ content: 'start', hang: true }]);
  try {
    const ctl = new AbortController();
    const p = streamChat({ gatewayUrl: gw.url, model: 'm', messages: [], signal: ctl.signal, onText: () => ctl.abort() });
    await assert.rejects(p);
  } finally { gw.close(); }
});

test('XML fallback: <tool_call> JSON', () => {
  const r = extractFallbackCalls('Sure.\n<tool_call>\n{"name":"browser_go","arguments":{"url":"https://a.com"}}\n</tool_call>');
  assert.strictEqual(r.calls.length, 1);
  assert.strictEqual(r.calls[0].name, 'browser_go');
  assert.deepStrictEqual(JSON.parse(r.calls[0].arguments), { url: 'https://a.com' });
  assert.strictEqual(r.content, 'Sure.');
});

test('XML fallback: <function=name><parameter=k>v</parameter>', () => {
  const r = extractFallbackCalls('<tool_call>\n<function=browser_type>\n<parameter=id>\n7\n</parameter>\n<parameter=text>\nhello world\n</parameter>\n<parameter=enter>\ntrue\n</parameter>\n</function>\n</tool_call>');
  assert.strictEqual(r.calls.length, 1);
  assert.deepStrictEqual(JSON.parse(r.calls[0].arguments), { id: 7, text: 'hello world', enter: true });
  assert.strictEqual(r.content, '');
});

test('XML fallback used by streamChat when server sends no tool_calls', async () => {
  const gw = await startGateway([{ content: 'ok <tool_call>{"name":"browser_back","arguments":{}}</tool_call>' }]);
  try {
    const out = await streamChat({ gatewayUrl: gw.url, model: 'm', messages: [] });
    assert.strictEqual(out.toolCalls.length, 1);
    assert.strictEqual(out.toolCalls[0].name, 'browser_back');
  } finally { gw.close(); }
});
