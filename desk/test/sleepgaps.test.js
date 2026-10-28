'use strict';
// What the diary gives sleep beyond chat text (tool steps, self-checks, stops) and the Lessons part of the sleep summary.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const { EventEmitter } = require('events');
const { createGateway, diaryRecord, turnSteps } = require('../src/gateway');
const { WinSleep, workerEnv, lessonsSection } = require('../src/sleepwin');
const { SYSTEM_PROMPT } = require('../src/prompt');

const tmp = (n) => fs.mkdtempSync(path.join(os.tmpdir(), n));
const listen = (srv) => new Promise((r) => srv.listen(0, '127.0.0.1', () => r(srv.address().port)));
const close = (srv) => new Promise((r) => srv.close(() => r()));

const call = (id, name, args) => ({ id, type: 'function', function: { name, arguments: JSON.stringify(args) } });

test('diary record: tool steps of the current turn, with ok flags; secrets hidden; self-checks; plain chats keep the old shape', () => {
  const messages = [
    { role: 'system', content: 'SYS' },
    { role: 'user', content: 'earlier question' },
    { role: 'assistant', content: '', tool_calls: [call('o1', 'web_search', { query: 'old' })] },
    { role: 'tool', tool_call_id: 'o1', content: 'old result' },
    { role: 'assistant', content: 'old answer' },
    { role: 'user', content: 'Open my grades' },
    { role: 'assistant', content: '', tool_calls: [call('a', 'browser_go', { url: 'https://canvas.example.edu' }), call('b', 'browser_click', { id: 4 })] },
    { role: 'tool', tool_call_id: 'a', content: 'Opened Canvas' },
    { role: 'tool', tool_call_id: 'b', content: 'Error: element 4 is gone\n[That failed. Before retrying, re-read the page]' },
    { role: 'assistant', content: '', tool_calls: [call('c', 'browser_type', { id: 2, text: 'password hunter2' })] },
    { role: 'tool', tool_call_id: 'c', content: 'Typed' },
    { role: 'assistant', content: 'Done.' },
    { role: 'user', content: '[Self-check] Not done yet: the grades page did not load. Look at the page again.' },
    { role: 'assistant', content: '', tool_calls: [call('d', 'browser_read', {})] },
    { role: 'tool', tool_call_id: 'd', content: '[stopped by user]' }
  ];
  const rec = diaryRecord({ ts: Date.UTC(2026, 9, 28), model: 'main', requestBody: { messages }, content: 'Your grades are up.' });
  assert.deepStrictEqual(rec.tools.map((t) => [t.name, t.ok]), [['browser_go', true], ['browser_click', false], ['browser_type', true], ['browser_read', false]]);
  assert.strictEqual(rec.tools[2].args, '[hidden]');
  assert.ok(!JSON.stringify(rec).includes('hunter2'));
  assert.deepStrictEqual(rec.checks, ['Not done yet: the grades page did not load. Look at the page again.']);
  assert.ok(!JSON.stringify(rec).includes('SYS'));
  assert.strictEqual(rec.stopped, undefined);
  // the old fields are exactly what they were
  assert.deepStrictEqual(Object.keys(rec).slice(0, 4), ['ts', 'model', 'messages', 'response']);
  const plain = diaryRecord({ ts: 0, model: 'main', requestBody: { messages: [{ role: 'user', content: 'hi' }] }, content: 'hello' });
  assert.deepStrictEqual(Object.keys(plain), ['ts', 'model', 'messages', 'response']);
  assert.deepStrictEqual(turnSteps([{ role: 'user', content: 'x' }]), { tools: [], checks: [] });
});

test('gateway: a run Ben stops mid-stream still reaches the diary, marked stopped, with what came before', async () => {
  const up = http.createServer((req, res) => {
    if (req.url === '/health') { res.writeHead(200); return res.end('{}'); }
    req.resume(); res.writeHead(200, { 'content-type': 'text/event-stream' }); res.write('data: {"choices":[{"delta":{"content":"Searching the bus site"}}]}\n\n');
  });
  const upPort = await listen(up);
  const diaryDir = tmp('gws-');
  const gw = createGateway({ upstream: 'http://127.0.0.1:' + upPort, diaryDir, now: () => Date.UTC(2026, 9, 28, 12, 0, 0) }); const port = await gw.listen(0);
  try {
    const ctl = new AbortController();
    const r = await fetch('http://127.0.0.1:' + port + '/v1/chat/completions', { method: 'POST', body: JSON.stringify({ model: 'fast', messages: [{ role: 'user', content: 'bus times please' }], stream: true }), signal: ctl.signal });
    await r.body.getReader().read();
    ctl.abort();
    let lines = [];
    for (let i = 0; i < 100 && !lines.length; i++) { await new Promise((x) => setTimeout(x, 20)); try { lines = fs.readFileSync(path.join(diaryDir, '2026-10-28.jsonl'), 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse); } catch (e) { /* not yet */ } }
    assert.strictEqual(lines.length, 1);
    assert.strictEqual(lines[0].stopped, true);
    assert.deepStrictEqual(lines[0].messages, [{ role: 'user', content: 'bus times please' }]);
  } finally { await gw.close(); await close(up); }
  up.closeAllConnections && up.closeAllConnections();
});

test('sleep worker env: passes the userData folder (saved notes, tracking list) when given', () => {
  const o = { python: 'py', home: 'H', outFile: 'O', diaryDir: 'D', sleepmlxParent: 'P', hfHome: 'HF', practice: [] };
  assert.strictEqual(workerEnv(o).SLEEPMLX_USERDATA, undefined);
  assert.strictEqual(workerEnv({ ...o, userData: 'U' }).SLEEPMLX_USERDATA, 'U');
});

test('sleep summary: the night\'s lessons are listed under Lessons (and marked when the night was undone)', async () => {
  assert.strictEqual(lessonsSection([]), '');
  assert.match(lessonsSection(['Lesson one.', '  Lesson\ntwo. ']), /^Lessons:\n- Lesson one\.\n- Lesson two\.$/);
  assert.match(lessonsSection(['x'], true), /^Lessons \(not kept/);
  const root = tmp('wsl-');
  const installer = { dir: path.join(root, 'rt'), installed: () => true, pythonExe: () => 'PY', plan: () => ({}), state: () => ({}) };
  const envs = [];
  const spawn = (cmd, args, opts) => {
    envs.push(opts.env);
    const c = new EventEmitter(); c.stdout = new EventEmitter(); c.stderr = new EventEmitter(); c.kill = () => {};
    setImmediate(() => { fs.mkdirSync(path.dirname(opts.env.SLEEPMODE_OUT), { recursive: true }); fs.writeFileSync(opts.env.SLEEPMODE_OUT, JSON.stringify({ quiz: 80, steps: 3, interrupted: false, reverted: false, lessons: ['Lesson from 2026-10-27 (Ben corrected Glim): Glim said the wrong answer. Next time: check.'] })); c.emit('exit', 0); });
    return c;
  };
  const ws = new WinSleep({ getSettings: () => ({}), root, installer, spawn, onBattery: () => false, hooks: {} });
  assert.strictEqual(ws.start().ok, true);
  for (let i = 0; i < 100 && ws.active; i++) await new Promise((r) => setTimeout(r, 10));
  const summary = fs.readFileSync(path.join(root, 'sleep', 'summary.md'), 'utf8');
  assert.match(summary, /Lessons:\n- Lesson from 2026-10-27 \(Ben corrected Glim\)/);
  assert.strictEqual(envs[0].SLEEPMLX_USERDATA, root);
});

test('desk system prompt is untouched by the sleep changes: under 9000 chars and the same bytes on every load', () => {
  assert.ok(SYSTEM_PROMPT.length < 9000);
  delete require.cache[require.resolve('../src/prompt')];
  assert.strictEqual(require('../src/prompt').SYSTEM_PROMPT, SYSTEM_PROMPT);
});
