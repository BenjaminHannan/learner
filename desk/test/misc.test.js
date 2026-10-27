'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'); const os = require('os'); const path = require('path');
const { Store } = require('../src/store');
const { runShell } = require('../src/tools/shell');
const { parseDDG, webSearch } = require('../src/tools/web');
const { createScreen, formatLook } = require('../src/tools/screen');
const { Diary } = require('../src/tools/diary');

test('store: threads and settings round trip', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'store-'));
  const s = new Store(dir);
  assert.strictEqual(s.getSettings().model, 'qwen36-auto');
  s.saveSettings({ maxSteps: 7 });
  assert.strictEqual(new Store(dir).getSettings().maxSteps, 7);
  const t = s.newThread(); t.title = 'hello'; s.saveThread(t);
  assert.strictEqual(s.listThreads()[0].title, 'hello');
  s.renameThread(t.id, 'renamed'); assert.strictEqual(s.loadThread(t.id).title, 'renamed');
  s.deleteThread(t.id); assert.strictEqual(s.listThreads().length, 0);
});

test('shell: output, exit code, trimming, timeout', async () => {
  assert.match(await runShell('echo hi'), /^hi/);
  assert.match(await runShell('exit 3'), /\[exit 3\]/);
  const long = await runShell('head -c 20000 /dev/zero | tr "\\0" a');
  assert.ok(long.length < 4100);
  assert.match(await runShell('sleep 5', { timeoutMs: 300 }), /timed out/);
});

test('web: parses DuckDuckGo html', () => {
  const html = `<div class="result"><h2><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fa%3Fx%3D1&amp;rut=abc">Example &amp; <b>One</b></a></h2><a class="result__snippet" href="x">First <b>snippet</b> here</a></div>
  <div class="result"><a class="result__a" href="https://two.example/">Two</a><a class="result__snippet" href="y">Second</a></div>`;
  const r = parseDDG(html, 8);
  assert.strictEqual(r.length, 2);
  assert.deepStrictEqual(r[0], { title: 'Example & One', url: 'https://example.com/a?x=1', snippet: 'First snippet here' });
  assert.strictEqual(r[1].url, 'https://two.example/');
});

test('web: webSearch formats results via injected fetch', async () => {
  const out = await webSearch('x', { fetch: async () => ({ ok: true, text: async () => '<a class="result__a" href="https://a.com">A</a><a class="result__snippet">s</a>' }) });
  assert.match(out, /1\. A\n\s+https:\/\/a\.com\/\n\s+s/);
});

test('screen: missing helper gives a clear error string', async () => {
  const sc = createScreen(() => ({ helperPath: '/nonexistent/deskhelper' }), '/nonexistent');
  if (sc.findHelper()) return; // a real helper exists in this checkout; skip
  const r = await sc.tools.screen_look({});
  assert.strictEqual(r.text, 'Error: screen control helper not installed');
});

test('screen: drives a helper binary and parses JSON', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'helper-'));
  const bin = path.join(dir, 'deskhelper');
  fs.writeFileSync(bin, '#!/bin/sh\ncase "$1" in look) echo \'{"app":"Notes","pid":5,"windows":[{"title":"W","frame":[0,0,10,10]}],"elements":[{"id":1,"role":"AXButton","title":"New","frame":[1,2,3,4]}]}\';; check) echo \'{"accessibility":true,"screenRecording":false}\';; *) echo \'{"ok":true}\';; esac\n', { mode: 0o755 });
  const sc = createScreen(() => ({ helperPath: bin }), null);
  const r = await sc.tools.screen_look({ app: 'Notes' });
  assert.match(typeof r === 'string' ? r : r.text, /App: Notes[\s\S]*\[1\] AXButton "New"/);
  assert.deepStrictEqual(await sc.check(), { accessibility: true, screenRecording: false });
  assert.strictEqual(await sc.tools.screen_key({ keys: 'cmd+t' }), 'Pressed cmd+t.');
  assert.match(formatLook({ error: 'x' }), /Error: x/);
});

test('diary: talks MCP over stdio to a fake server; missing file means unavailable', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'diary-'));
  const srv = path.join(dir, 'diary_mcp.js');
  fs.writeFileSync(srv, `
let b='';process.stdin.on('data',d=>{b+=d;let i;while((i=b.indexOf('\\n'))>=0){const l=b.slice(0,i);b=b.slice(i+1);if(!l.trim())continue;const m=JSON.parse(l);
if(m.method==='initialize')console.log(JSON.stringify({jsonrpc:'2.0',id:m.id,result:{protocolVersion:'2024-11-05',capabilities:{},serverInfo:{name:'f',version:'1'}}}));
else if(m.method==='tools/call')console.log(JSON.stringify({jsonrpc:'2.0',id:m.id,result:{content:[{type:'text',text:'found: '+m.params.arguments.query}]}}));}});`);
  const d = new Diary(() => ({ pythonPath: process.execPath, diaryPath: srv }));
  assert.strictEqual(await d.probe(), true);
  assert.strictEqual(await d.search('village'), 'found: village');
  d.stop();
  const bad = new Diary(() => ({ pythonPath: process.execPath, diaryPath: path.join(dir, 'nope.py') }));
  assert.strictEqual(await bad.probe(), false);
});
