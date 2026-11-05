'use strict';
// ONE-GLIM: Desk uses the one "Glim" process's speech-to-text and diary when it answers, and spawns its own only without Glim.
const test = require('node:test');
const assert = require('node:assert');
const http = require('node:http');
const { EventEmitter } = require('node:events');
const { Stt } = require('../src/stt');
const { Diary } = require('../src/tools/diary');
const glimside = require('../src/glimside');

function fakeChild() {
  const c = new EventEmitter();
  c.stdout = new EventEmitter(); c.stderr = new EventEmitter();
  c.stdin = { end() {}, on() {} }; c.kill = () => { c.killed = true; };
  return c;
}
function mkStt(o) {
  const spawned = [];
  const stt = new Stt({ home: '/h', devRoot: '/repo', resourcesPath: '', env: {}, exists: () => true, hasMlx: async () => true,
    spawn: (cmd, args) => { const c = fakeChild(); spawned.push({ cmd, args, c }); return c; }, glimUrl: 'http://127.0.0.1:18083', ...o });
  return { stt, spawned };
}

test('stt: Glim answering with parts.stt -> its URL, nothing spawned, stop() kills nothing', async () => {
  const { stt, spawned } = mkStt({ glimProbe: async () => ({ stt: true, diary: true }) });
  assert.strictEqual(await stt.ensure(), 'http://127.0.0.1:18083');
  assert.strictEqual(await stt.ensure(), 'http://127.0.0.1:18083');
  stt.stop();
  assert.strictEqual(spawned.length, 0);
});

test('stt: Glim seen, then restarting -> retry error, still no second speech process', async () => {
  let up = true;
  const { stt, spawned } = mkStt({ glimProbe: async () => (up ? { stt: true } : null) });
  await stt.ensure();
  up = false;
  await assert.rejects(stt.ensure(), /Glim is restarting/);
  up = true;
  assert.strictEqual(await stt.ensure(), 'http://127.0.0.1:18083');
  assert.strictEqual(spawned.length, 0);
});

test('stt: Glim expected (pid file) but not up yet -> retry error, no spawn', async () => {
  const { stt, spawned } = mkStt({ glimProbe: async () => null, glimExpected: () => true });
  await assert.rejects(stt.ensure(), /Glim is restarting/);
  assert.strictEqual(spawned.length, 0);
});

test('stt: no Glim on this Mac -> spawns lfm_stt.py exactly as before', async () => {
  const { stt, spawned } = mkStt({ glimProbe: async () => null, glimExpected: () => false });
  const p = stt.ensure();
  for (let i = 0; i < 5 && !spawned.length; i++) await new Promise((r) => setImmediate(r));
  assert.strictEqual(spawned.length, 1);
  assert.deepStrictEqual(spawned[0].args, ['-I', '/repo/stt/lfm_stt.py']);
  spawned[0].c.stdout.emit('data', '{"port": 4242}\n');
  assert.strictEqual(await p, 'http://127.0.0.1:4242');
});

test('stt: a Glim without speech (parts.stt false) and not expected -> spawns its own', async () => {
  const { stt, spawned } = mkStt({ glimProbe: async () => ({ stt: false, diary: true }) });
  const p = stt.ensure();
  for (let i = 0; i < 5 && !spawned.length; i++) await new Promise((r) => setImmediate(r));
  assert.strictEqual(spawned.length, 1);
  spawned[0].c.stdout.emit('data', '{"port": 5}\n');
  await p;
});

test('diary: Glim mode sends tools/call over glimRpc and returns the text', async () => {
  const sent = [];
  const d = new Diary(() => ({ diaryPath: '' }), { glimProbe: async () => ({ diary: true }), glimRpc: async (m) => { sent.push(m); return { jsonrpc: '2.0', id: m.id, result: { content: [{ type: 'text', text: 'hit 1' }] } }; } });
  assert.strictEqual(await d.probe(), true);
  assert.strictEqual(await d.search('cats'), 'hit 1');
  assert.strictEqual(sent.length, 1);
  assert.strictEqual(sent[0].method, 'tools/call');
  assert.deepStrictEqual(sent[0].params, { name: 'diary_search', arguments: { query: 'cats' } });
  assert.strictEqual(d.proc, null);
});

test('diary: Glim down mid-session -> error text, next call works again', async () => {
  let up = false;
  const d = new Diary(() => ({ diaryPath: '' }), { glimProbe: async () => ({ diary: true }), glimRpc: async (m) => { if (!up) throw new Error('ECONNREFUSED'); return { id: m.id, result: { content: [{ text: 'ok' }] } }; } });
  assert.match(await d.search('x'), /diary unavailable \(ECONNREFUSED\)/);
  up = true;
  assert.strictEqual(await d.search('x'), 'ok');
});

test('diary: Glim expected but not answering -> still Glim mode (probe true), no spawn', async () => {
  const d = new Diary(() => ({ diaryPath: '' }), { glimProbe: async () => null, glimExpected: () => true, glimRpc: async () => { throw new Error('down'); } });
  assert.strictEqual(await d.probe(), true);
  assert.strictEqual(d.proc, null);
});

test('diary: custom diaryPath keeps the stdio child (Glim not asked)', async () => {
  let asked = 0;
  const d = new Diary(() => ({ diaryPath: '/nope/diary_mcp.py' }), { glimProbe: async () => { asked++; return { diary: true }; }, glimRpc: async () => ({}) });
  assert.strictEqual(await d.probe(), false);   // file missing -> the old path's answer
  assert.strictEqual(asked, 0);
});

test('glimside: probe/diaryRpc against a real local server', async () => {
  const srv = http.createServer((req, res) => {
    let b = ''; req.on('data', (d) => { b += d; }); req.on('end', () => {
      if (req.url === '/glim') { res.end(JSON.stringify({ name: 'Glim', pid: 1, parts: { stt: true, diary: true } })); return; }
      if (req.url === '/diary') { const m = JSON.parse(b); if (m.id === undefined) { res.statusCode = 204; res.end(); return; } res.end(JSON.stringify({ id: m.id, result: { ok: 1 } })); return; }
      res.statusCode = 404; res.end();
    });
  });
  await new Promise((r) => srv.listen(0, '127.0.0.1', r));
  const env = { PREMONITION_GLIM_SIDE: 'http://127.0.0.1:' + srv.address().port };
  assert.deepStrictEqual(await glimside.probe(env), { stt: true, diary: true });
  assert.deepStrictEqual(await glimside.diaryRpc({ jsonrpc: '2.0', id: 3, method: 'ping' }, 2000, env), { id: 3, result: { ok: 1 } });
  assert.strictEqual(await glimside.diaryRpc({ jsonrpc: '2.0', method: 'notifications/initialized' }, 2000, env), null);
  srv.close();
  assert.strictEqual(await glimside.probe({ PREMONITION_GLIM_SIDE: 'off' }), null);
  assert.strictEqual(glimside.expected('/h', { PREMONITION_GLIM_SIDE: 'off' }), false);
});

test('eyes: Glim with eyes -> POST /eyes, the spawned worker is stopped and never used; stop() asks Glim to unload', async () => {
  const posts = []; let innerUsed = 0, innerStops = 0;
  const w = new glimside.GlimEyesWorker({ inner: { encode: async () => { innerUsed++; }, stop: () => { innerStops++; } },
    probe: async () => ({ eyes: true }), expected: () => false, post: async (m) => { posts.push(m); return m.unload ? { ok: true } : { id: m.id, ok: true, shape: [64, 768], f16: 'AA==' }; } });
  const r = await w.encode('/tmp/a.jpg');
  assert.deepStrictEqual(r.shape, [64, 768]);
  assert.strictEqual(posts[0].path, '/tmp/a.jpg');
  assert.strictEqual(innerUsed, 0);
  w.stop(); await new Promise((r2) => setImmediate(r2));
  assert.ok(posts.some((m) => m.unload === true));
  assert.ok(innerStops >= 1);
});

test('eyes: no Glim -> the spawned worker, as before; a failed Glim reply is an error', async () => {
  let innerUsed = 0;
  const own = new glimside.GlimEyesWorker({ inner: { encode: async () => { innerUsed++; return { ok: true }; }, stop() {} }, probe: async () => null, expected: () => false, post: async () => { throw new Error('no'); } });
  await own.encode('/x.jpg');
  assert.strictEqual(innerUsed, 1);
  const g = new glimside.GlimEyesWorker({ inner: { encode: async () => { throw new Error('inner'); }, stop() {} }, probe: async () => ({ eyes: true }), expected: () => true, post: async () => ({ ok: false, error: 'FileNotFoundError: x' }) });
  await assert.rejects(g.encode('/x.jpg'), /FileNotFoundError/);
});
