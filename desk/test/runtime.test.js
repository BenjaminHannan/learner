'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const crypto = require('crypto');
const { EventEmitter } = require('events');
const C = require('../src/runtime/constants');
const R = require('../src/runtime/releases');
const { downloadFile, sha256File } = require('../src/runtime/download');
const { buildArgs, LlamaServer } = require('../src/runtime/llamaserver');
const { createGateway, diaryRecord, diaryMessages, SseText, mapRequest } = require('../src/gateway');
const { workerCommand, workerEnv, convertCommand, sleepmlxParent, mayStart, WinSleep } = require('../src/sleepwin');
const { shouldAutoSleep } = require('../src/sleep');
const { pipTorchArgs, pipLibsArgs, snapshotArgs, planText } = require('../src/runtime/sleepinstall');
const { SYSTEM_PROMPT, buildTools } = require('../src/prompt');
const Platform = require('../renderer/platform');

const tmp = (n) => fs.mkdtempSync(path.join(os.tmpdir(), n));
const listen = (srv) => new Promise((r) => srv.listen(0, '127.0.0.1', () => r(srv.address().port)));
const close = (srv) => new Promise((r) => { srv.closeAllConnections && srv.closeAllConnections(); srv.close(r); });

// ---- release / file picking --------------------------------------------------------------------------------------
const rel = (tag, at, flavors, extra) => ({ tag_name: tag, published_at: at, draft: false, prerelease: false, assets: flavors.map((f) => ({ name: C.llamaAssetName(tag, f), browser_download_url: 'https://x/' + tag + '/' + f, size: 10, digest: 'sha256:' + 'a'.repeat(64) })), ...(extra || {}) });

test('llama.cpp asset: newest release at or after the LFM3 floor date, Vulkan first, CPU as the fallback flavor', () => {
  const rels = [rel('b9000', '2026-10-27T10:00:00Z', ['vulkan', 'cpu']), rel('b9010', '2026-10-27T16:30:00Z', ['vulkan', 'cpu']), rel('b9020', '2026-10-28T09:00:00Z', ['vulkan', 'cpu'])];
  const v = R.pickLlamaAsset(rels, { flavor: 'vulkan', minTag: 0 });
  assert.strictEqual(v.tag, 'b9020'); assert.strictEqual(v.name, 'llama-b9020-bin-win-vulkan-x64.zip'); assert.strictEqual(v.sha256, 'a'.repeat(64));
  assert.strictEqual(R.pickLlamaAsset(rels, { flavor: 'cpu', minTag: 0 }).name, 'llama-b9020-bin-win-cpu-x64.zip');
  // releases before the floor never qualify, even if they are the only ones
  assert.strictEqual(R.pickLlamaAsset([rels[0]], { flavor: 'vulkan', minTag: 0 }), null);
  // a newest release that lacks the asset falls through to the previous one; drafts and prereleases are skipped
  const odd = [rel('b9030', '2026-10-29T00:00:00Z', ['cpu']), rel('b9020', '2026-10-28T09:00:00Z', ['vulkan']), rel('b9040', '2026-10-30T00:00:00Z', ['vulkan'], { prerelease: true })];
  assert.strictEqual(R.pickLlamaAsset(odd, { flavor: 'vulkan', minTag: 0 }).tag, 'b9020');
  assert.strictEqual(R.pickLlamaAsset(rels, { flavor: 'vulkan', minTag: 9025 }), null);
  assert.ok(Date.parse(C.LLAMA_MIN_PUBLISHED) === Date.parse('2026-10-27T16:06:00Z'));
  // the real floor: tags up to b11937 predate LFM3 support
  assert.strictEqual(R.pickLlamaAsset([rel('b11937', '2026-10-28T01:00:00Z', ['vulkan'])], { flavor: 'vulkan' }), null);
  assert.strictEqual(R.pickLlamaAsset([rel('b11940', '2026-10-28T01:00:00Z', ['vulkan'])], { flavor: 'vulkan' }).tag, 'b11940');
});

test('GGUF pick: the constant file name first, else the q4_0 .gguf in the repo listing; sha comes from the LFS oid', () => {
  const files = [{ type: 'file', path: 'README.md', size: 5 }, { type: 'file', path: 'LFM3-1.7B-Q8_0.gguf', size: 1800, lfs: { oid: 'b'.repeat(64), size: 1800 } }, { type: 'file', path: 'LFM3-1.7B-q4_0-QAD.gguf', size: 1050, lfs: { oid: 'c'.repeat(64), size: 1050 } }, { type: 'file', path: 'mmproj-q4_0.gguf', size: 9 }];
  const p = R.pickGguf(files);
  assert.strictEqual(p.path, 'LFM3-1.7B-q4_0-QAD.gguf'); assert.strictEqual(p.sha256, 'c'.repeat(64)); assert.strictEqual(p.size, 1050);
  const exact = files.concat([{ type: 'file', path: C.MODEL_FILE, size: 1, lfs: { oid: 'd'.repeat(64), size: 1 } }]);
  assert.strictEqual(R.pickGguf(exact).path, C.MODEL_FILE);
  assert.strictEqual(R.pickGguf([{ type: 'file', path: 'a.gguf', size: 1 }]), null);
  assert.strictEqual(R.hfResolveUrl('LiquidAI/LFM3-1.7B-GGUF', 'a b.gguf'), 'https://huggingface.co/LiquidAI/LFM3-1.7B-GGUF/resolve/main/a%20b.gguf');
  assert.match(R.hfTreeUrl(C.MODEL_REPO), /api\/models\/LiquidAI\/LFM3-1\.7B-GGUF\/tree\/main/);
});

test('python-build-standalone pick: newest 3.12 install_only windows build', () => {
  const rels = [{ tag_name: '20260101', published_at: '2026-01-01T00:00:00Z', assets: [{ name: 'cpython-3.12.8+20260101-x86_64-pc-windows-msvc-install_only.tar.gz', browser_download_url: 'u1', size: 1 }] },
    { tag_name: '20260301', published_at: '2026-03-01T00:00:00Z', assets: [{ name: 'cpython-3.13.2+20260301-x86_64-pc-windows-msvc-install_only.tar.gz', browser_download_url: 'u2' }, { name: 'cpython-3.12.10+20260301-x86_64-pc-windows-msvc-install_only.tar.gz', browser_download_url: 'u3', size: 2 }, { name: 'cpython-3.12.10+20260301-x86_64-unknown-linux-gnu-install_only.tar.gz', browser_download_url: 'u4' }] }];
  assert.strictEqual(R.pickPython(rels).url, 'u3');
});

// ---- downloader against a real local HTTP server (Range support) -------------------------------------------------------
function rangeServer(body, opt) {
  opt = opt || {};
  const seen = [];
  const srv = http.createServer((req, res) => {
    seen.push(req.headers.range || '');
    let start = 0; const m = /bytes=(\d+)-/.exec(req.headers.range || '');
    if (m && !opt.noRange) start = Number(m[1]);
    if (start >= body.length) { res.writeHead(416); return res.end(); }
    const slice = body.subarray(start, opt.cutAt && start === 0 ? opt.cutAt : undefined);
    res.writeHead(start && !opt.noRange ? 206 : 200, { 'content-length': (opt.cutAt && start === 0 ? body.length : body.length - start) });
    if (opt.cutAt && start === 0) { res.write(slice); setTimeout(() => res.destroy(), 20); } else res.end(slice);
  });
  return { srv, seen };
}

test('download: plain, with progress and a correct SHA256', async () => {
  const body = crypto.randomBytes(300000); const sha = crypto.createHash('sha256').update(body).digest('hex');
  const { srv } = rangeServer(body); const port = await listen(srv);
  try {
    const d = tmp('dl-'); const prog = [];
    const r = await downloadFile({ url: 'http://127.0.0.1:' + port + '/f', dest: path.join(d, 'f.bin'), sha256: sha, onProgress: (p) => prog.push(p) });
    assert.strictEqual(r.verified, true); assert.strictEqual(r.bytes, 300000); assert.ok(prog.length && prog[prog.length - 1].done === 300000 && prog[0].total === 300000);
    assert.ok(!fs.existsSync(path.join(d, 'f.bin.part')));
    // a finished, verified file is not downloaded again
    const again = await downloadFile({ url: 'http://127.0.0.1:1/never', dest: path.join(d, 'f.bin'), sha256: sha });
    assert.strictEqual(again.cached, true);
  } finally { await close(srv); }
});

test('download: resumes a .part with a Range request and verifies the whole file', async () => {
  const body = crypto.randomBytes(200000); const sha = crypto.createHash('sha256').update(body).digest('hex');
  const { srv, seen } = rangeServer(body); const port = await listen(srv);
  try {
    const d = tmp('dl2-'); const dest = path.join(d, 'm.gguf');
    fs.writeFileSync(dest + '.part', body.subarray(0, 50000));
    const r = await downloadFile({ url: 'http://127.0.0.1:' + port + '/m', dest, sha256: sha });
    assert.strictEqual(seen[0], 'bytes=50000-'); assert.strictEqual(r.resumed, true); assert.strictEqual(r.verified, true);
    assert.strictEqual(await sha256File(dest), sha);
  } finally { await close(srv); }
});

test('download: a server without Range support restarts from zero; a cut connection leaves a resumable .part', async () => {
  const body = crypto.randomBytes(120000);
  const a = rangeServer(body, { noRange: true }); const pa = await listen(a.srv);
  const b = rangeServer(body, { cutAt: 40000 }); const pb = await listen(b.srv);
  try {
    const d = tmp('dl3-');
    fs.writeFileSync(path.join(d, 'x.part'), Buffer.alloc(1000, 1));
    const r = await downloadFile({ url: 'http://127.0.0.1:' + pa + '/x', dest: path.join(d, 'x'), sha256: crypto.createHash('sha256').update(body).digest('hex') });
    assert.strictEqual(r.bytes, 120000);
    const dest2 = path.join(d, 'y');
    await assert.rejects(downloadFile({ url: 'http://127.0.0.1:' + pb + '/y', dest: dest2 }));
    assert.ok(fs.existsSync(dest2 + '.part') && fs.statSync(dest2 + '.part').size > 0 && fs.statSync(dest2 + '.part').size < 120000);
    const r2 = await downloadFile({ url: 'http://127.0.0.1:' + pb + '/y', dest: dest2 });
    assert.strictEqual(r2.bytes, 120000); assert.strictEqual(r2.resumed, true);
  } finally { await close(a.srv); await close(b.srv); }
});

test('download: a wrong checksum deletes the file and says so', async () => {
  const body = crypto.randomBytes(5000);
  const { srv } = rangeServer(body); const port = await listen(srv);
  try {
    const d = tmp('dl4-');
    await assert.rejects(downloadFile({ url: 'http://127.0.0.1:' + port + '/z', dest: path.join(d, 'z'), sha256: '0'.repeat(64) }), /checksum mismatch/);
    assert.ok(!fs.existsSync(path.join(d, 'z')) && !fs.existsSync(path.join(d, 'z.part')));
  } finally { await close(srv); }
});

// ---- llama-server ----------------------------------------------------------------------------------------------------
test('llama-server args: ctx 8192, one slot, --jinja, port 18090, Vulkan offload or CPU, optional --lora', () => {
  const a = buildArgs({ model: 'M.gguf', flavor: 'vulkan' });
  assert.deepStrictEqual(a.slice(0, 2), ['-m', 'M.gguf']);
  const j = a.join(' ');
  assert.match(j, /--host 127\.0\.0\.1/); assert.match(j, /--port 18090/); assert.match(j, /-c 8192/); assert.match(j, /-np 1/); assert.ok(a.includes('--jinja')); assert.match(j, /-ngl 99/); assert.ok(!a.includes('--lora'));
  assert.match(buildArgs({ model: 'M', flavor: 'cpu' }).join(' '), /-ngl 0/);
  const l = buildArgs({ model: 'M', lora: 'C:\\a\\adapter.gguf' }); assert.strictEqual(l[l.indexOf('--lora') + 1], 'C:\\a\\adapter.gguf');
  assert.strictEqual(C.SERVER_PORT, 18090); assert.strictEqual(C.CTX, 8192);
});

function fakeChild() { const c = new EventEmitter(); c.stderr = new EventEmitter(); c.kill = () => { setImmediate(() => c.emit('exit', 0)); }; return c; }

test('llama-server supervisor: waits for /health, restarts after a crash, does not restart after stop()', async () => {
  const kids = []; const states = [];
  const srv = new LlamaServer({ exe: 'x.exe', model: 'm', spawn: () => { const c = fakeChild(); kids.push(c); return c; }, fetch: async () => ({ ok: true }), pollMs: 5, fastRetry: true, onState: (s) => states.push(s) });
  const r = await srv.start();
  assert.strictEqual(r.ok, true); assert.strictEqual(kids.length, 1);
  kids[0].emit('exit', 1);                      // crash
  await new Promise((res) => setTimeout(res, 60));
  assert.strictEqual(kids.length, 2); assert.ok(states.includes('restarting')); assert.strictEqual(srv.state, 'ready');
  srv.stop(); kids[kids.length - 1].emit('exit', 0);
  await new Promise((res) => setTimeout(res, 30));
  assert.strictEqual(kids.length, 2);
});

test('llama-server: exiting before it is healthy is reported (the caller then tries the CPU build)', async () => {
  const srv = new LlamaServer({ exe: 'x.exe', model: 'm', spawn: () => { const c = fakeChild(); setImmediate(() => c.emit('exit', 3)); return c; }, fetch: async () => ({ ok: false }), pollMs: 5 });
  const r = await srv.start();
  assert.strictEqual(r.ok, false); assert.strictEqual(r.exitedEarly, true); assert.match(r.error, /exited \(3\)/);
});

// ---- gateway -------------------------------------------------------------------------------------------------------------
test('diary records: shape, no system prompt, text only', () => {
  const rec = diaryRecord({ ts: Date.UTC(2026, 9, 28, 12, 0, 0), model: 'main', requestBody: { messages: [{ role: 'system', content: 'SECRET PROMPT' }, { role: 'user', content: [{ type: 'text', text: 'hi' }, { type: 'image_url', image_url: {} }] }, { role: 'assistant', content: '' }, { role: 'tool', content: 'result' }] }, content: 'hello' });
  assert.deepStrictEqual(Object.keys(rec), ['ts', 'model', 'messages', 'response']);
  assert.deepStrictEqual(rec.messages, [{ role: 'user', content: 'hi' }, { role: 'tool', content: 'result' }]);
  assert.deepStrictEqual(rec.response, { content: 'hello' }); assert.strictEqual(rec.ts, '2026-10-28T12:00:00.000Z');
  assert.ok(!JSON.stringify(rec).includes('SECRET'));
  assert.deepStrictEqual(diaryMessages([{ role: 'system', content: 'x' }]), []);
  const s = new SseText(); s.push('data: {"choices":[{"delta":{"content":"he"}}]}\n\ndata: {"choices":[{"delta":{"content":"llo"}}]}\n'); s.push('data: [DONE]\n'); assert.strictEqual(s.text, 'hello');
});

test('gateway: maps fast/main/auto to the one model, streams through, writes the diary (not for warm-ups), 503 while the model is down', async () => {
  const seenBodies = [];
  const up = http.createServer((req, res) => {
    if (req.url === '/health') { res.writeHead(200); return res.end('{"status":"ok"}'); }
    let b = ''; req.on('data', (d) => { b += d; }); req.on('end', () => {
      const j = JSON.parse(b); seenBodies.push(j);
      if (j.stream) { res.writeHead(200, { 'content-type': 'text/event-stream' }); res.write('data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'); res.write('data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'); res.end('data: [DONE]\n\n'); }
      else { res.writeHead(200, { 'content-type': 'application/json' }); res.end(JSON.stringify({ choices: [{ message: { role: 'assistant', content: 'plain answer' } }] })); }
    });
  });
  const upPort = await listen(up);
  const diaryDir = path.join(tmp('gw-'), 'diary', 'raw');
  const gw = createGateway({ upstream: 'http://127.0.0.1:' + upPort, diaryDir, now: () => Date.UTC(2026, 9, 28, 3, 0, 0) });
  const port = await gw.listen(0);
  const base = 'http://127.0.0.1:' + port + '/v1';
  try {
    const models = await (await fetch(base + '/models')).json();
    assert.deepStrictEqual(models.data.map((m) => m.id).sort(), ['auto', 'fast', 'main']);
    const msgs = [{ role: 'system', content: 'SYS' }, { role: 'user', content: 'say hello' }];
    const r1 = await fetch(base + '/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model: 'fast', messages: msgs, stream: true }) });
    assert.match(await r1.text(), /Hel[\s\S]*lo/);
    await fetch(base + '/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json', 'X-Premonition-Warm': '1' }, body: JSON.stringify({ model: 'fast', messages: msgs, stream: false, max_tokens: 1 }) });
    const r3 = await fetch(base + '/chat/completions', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ model: 'main', messages: msgs, stream: false }) });
    assert.strictEqual((await r3.json()).choices[0].message.content, 'plain answer');
    assert.deepStrictEqual(seenBodies.map((b) => b.model), ['default', 'default', 'default']); // llama-server gets one fixed name
    const lines = fs.readFileSync(path.join(diaryDir, '2026-10-28.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
    assert.strictEqual(lines.length, 2, 'the warm-up request is not in the diary');
    assert.deepStrictEqual(lines.map((l) => l.response.content), ['Hello', 'plain answer']);
    assert.deepStrictEqual(lines[0].messages, [{ role: 'user', content: 'say hello' }]);
    assert.ok(!fs.readFileSync(path.join(diaryDir, '2026-10-28.jsonl'), 'utf8').includes('SYS'));
  } finally { await gw.close(); await close(up); }
  // model down: /models says 503 so the app shows Offline instead of Ready
  const gw2 = createGateway({ upstream: 'http://127.0.0.1:1', diaryDir });
  const p2 = await gw2.listen(0);
  try { assert.strictEqual((await fetch('http://127.0.0.1:' + p2 + '/v1/models')).status, 503); } finally { await gw2.close(); }
});

// ---- prompt budget ---------------------------------------------------------------------------------------------------------
test('system prompt + tools leave plenty of the 8192-token context (about 3.5 chars per token, with a 3x margin check)', () => {
  const chars = SYSTEM_PROMPT.length + JSON.stringify(buildTools({ diary: true })).length;
  const tokens = Math.ceil(chars / 3.0);
  assert.ok(chars < 9000, 'prompt chars ' + chars);
  assert.ok(tokens <= C.CTX * 0.35, 'prompt tokens ~' + tokens + ' of ' + C.CTX);
  const p = Platform.PRESETS.find((x) => x.id === 'builtin');
  assert.ok(tokens + p.compactTokens + 1024 <= C.CTX, 'history limit + prompt + reply fits the context');
  assert.strictEqual(p.gatewayUrl, C.GATEWAY_URL);
});

// ---- sleep on Windows --------------------------------------------------------------------------------------------------------
test('sleep worker command: python -m sleepmlx.worker with the env contract and the shipped sleepmlx on PYTHONPATH', () => {
  const o = { python: 'C:\\R\\python\\python.exe', home: 'C:\\A\\sleep', outFile: 'C:\\A\\sleep\\chunk_out.json', diaryDir: 'C:\\A\\diary\\raw', sleepmlxParent: 'C:\\App\\resources', hfHome: 'C:\\R\\hf', budgetS: 600, practice: [] };
  const c = workerCommand(o);
  assert.strictEqual(c.cmd, o.python); assert.deepStrictEqual(c.args, ['-m', 'sleepmlx.worker', '--profile', C.SLEEP_PROFILE]);
  const e = workerEnv(o);
  assert.strictEqual(e.SLEEPMODE_BUDGET_S, '600'); assert.strictEqual(e.SLEEPMODE_OUT, o.outFile); assert.strictEqual(e.SLEEPMODE_PRACTICE, '');
  assert.ok(e.PYTHONPATH.startsWith('C:\\App\\resources')); assert.strictEqual(e.SLEEPMLX_DIARY_DIR, o.diaryDir); assert.strictEqual(e.SLEEPMLX_HOME, o.home); assert.strictEqual(e.HF_HUB_OFFLINE, '1');
  assert.strictEqual(sleepmlxParent('R', 'DEV', (p) => p === path.join('R', 'sleepmlx')), 'R');
  assert.strictEqual(sleepmlxParent('R', 'DEV', () => false), 'DEV');
  const cv = convertCommand({ python: 'py', convertScript: 'conv.py', adapterDir: 'ad', hfDir: 'hf', outFile: 'o.gguf' });
  assert.deepStrictEqual(cv.args, ['conv.py', 'ad', '--base', 'hf', '--outfile', 'o.gguf']);
});

test('sleep runtime installer commands: CPU torch from the PyTorch CPU index, HF snapshot of the LFM3 weights', () => {
  assert.ok(pipTorchArgs().includes('https://download.pytorch.org/whl/cpu')); assert.strictEqual(pipTorchArgs().slice(-1)[0], 'torch');
  assert.ok(['transformers', 'peft'].every((x) => pipLibsArgs().includes(x)));
  assert.match(snapshotArgs('C:\\hf').join(' '), /snapshot_download\("LiquidAI\/LFM3-1\.7B"/);
  assert.match(planText(), /3\.4 GB/); assert.match(planText(), /1 GB/);
});

test('schedule and plugged-in logic: night window 01:00-06:00, idle, and never on battery', () => {
  const s = { autoSleep: true, sleepFrom: '01:00', sleepTo: '06:00', sleepIdleMin: 30, sleepOnlyPlugged: true };
  const base = { settings: s, now: new Date(2026, 9, 28, 2, 0), idleMs: 3600000, systemIdleMs: 3600000, available: true, asleep: false, runActive: false, gatewayBusy: false, windowFocused: false, lastKey: null };
  assert.strictEqual(shouldAutoSleep({ ...base, onBattery: false }).sleep, true);
  const b = shouldAutoSleep({ ...base, onBattery: true }); assert.strictEqual(b.sleep, false); assert.strictEqual(b.reason, 'on battery');
  assert.strictEqual(shouldAutoSleep({ ...base, onBattery: true, settings: { ...s, sleepOnlyPlugged: false } }).sleep, true);
  assert.strictEqual(shouldAutoSleep({ ...base, now: new Date(2026, 9, 28, 12, 0) }).sleep, false);
  assert.strictEqual(mayStart({ sleepOnlyPlugged: true }, true).ok, false); assert.match(mayStart({ sleepOnlyPlugged: true }, true).error, /Plug it in/);
  assert.strictEqual(mayStart({ sleepOnlyPlugged: false }, true).ok, true); assert.strictEqual(mayStart({}, false).ok, true); assert.strictEqual(mayStart({}, true).ok, true, 'the Mac default is off');
  assert.deepStrictEqual(Platform.defaultSleepWindow('win32'), ['23:00', '08:00']); assert.deepStrictEqual(Platform.defaultSleepWindow('darwin'), ['23:00', '08:00']);
});

test('WinSleep: asks for the runtime first; then runs chunks, stops the model, converts the adapter, restarts with --lora, keeps the old one as fallback', async () => {
  const root = tmp('ws-'); const events = [];
  const installer = { dir: path.join(root, 'sleep-runtime'), installed: () => inst.ok, pythonExe: () => 'PY', plan: () => ({ text: 'plan' }), state: () => ({ convert: 'conv.py', hfDir: 'HF' }) };
  const inst = { ok: false };
  let chunk = 0; const spawned = []; const ran = []; const resumed = [];
  const spawn = (cmd, args, opts) => {
    spawned.push({ cmd, args, env: opts.env });
    const c = new EventEmitter(); c.stdout = new EventEmitter(); c.stderr = new EventEmitter(); c.kill = () => {};
    setImmediate(() => { chunk++; fs.writeFileSync(opts.env.SLEEPMODE_OUT, JSON.stringify(chunk < 2 ? { quiz: null, steps: 5, interrupted: true } : { quiz: 71, steps: 9, interrupted: false })); if (chunk === 2) { fs.mkdirSync(path.join(root, 'sleep', 'adapter'), { recursive: true }); } c.emit('exit', 0); });
    return c;
  };
  const run = async (cmd, args) => { ran.push([cmd, args]); fs.writeFileSync(args[args.indexOf('--outfile') + 1], 'gguf'); return ''; };
  const ws = new WinSleep({ getSettings: () => ({ sleepOnlyPlugged: true }), root, installer, onBattery: () => false, sleepmlxParent: 'RES', spawn, run, retryMs: 1, hooks: { pauseModel: () => events.push('pause'), resumeModel: async (lora) => { resumed.push(lora); events.push('resume'); return { ok: true }; } } });
  const first = ws.start();
  assert.strictEqual(first.ok, false); assert.strictEqual(first.needsRuntime, true); assert.strictEqual(first.plan.text, 'plan');
  inst.ok = true;
  const onBat = new WinSleep({ getSettings: () => ({ sleepOnlyPlugged: true }), root: tmp('ws2-'), installer, onBattery: () => true, spawn, hooks: {} });
  assert.match(onBat.start().error, /Plug it in/);
  fs.mkdirSync(path.join(root, 'sleep'), { recursive: true }); fs.writeFileSync(path.join(root, 'sleep', 'adapter.gguf'), 'old');
  const r = ws.start();
  assert.strictEqual(r.ok, true); assert.strictEqual(ws.status().sleeping, true);
  assert.strictEqual(ws.start().ok, false);
  for (let i = 0; i < 200 && ws.status().sleeping; i++) await new Promise((x) => setTimeout(x, 10));
  assert.strictEqual(ws.status().sleeping, false);
  assert.strictEqual(spawned.length, 2); assert.deepStrictEqual(spawned[0].args.slice(0, 2), ['-m', 'sleepmlx.worker']);
  assert.strictEqual(events[0], 'pause'); assert.strictEqual(ran.length, 1); assert.deepStrictEqual(ran[0][1].slice(0, 1), ['conv.py']);
  assert.ok(fs.existsSync(path.join(root, 'sleep', 'adapter.prev.gguf')), 'the previous adapter is kept as the fallback');
  assert.strictEqual(fs.readFileSync(path.join(root, 'sleep', 'adapter.gguf'), 'utf8'), 'gguf');
  assert.deepStrictEqual(resumed, [path.join(root, 'sleep', 'adapter.gguf')]);
  assert.strictEqual(ws.status().lastQuiz, 71);
  assert.match(ws.readSummary(), /recall quiz 71%/);
});

test('WinSleep: if the new adapter will not load, the previous one is tried, then the plain model', async () => {
  const root = tmp('ws3-'); fs.mkdirSync(path.join(root, 'sleep'), { recursive: true });
  fs.writeFileSync(path.join(root, 'sleep', 'adapter.gguf'), 'new'); fs.writeFileSync(path.join(root, 'sleep', 'adapter.prev.gguf'), 'prev');
  const tried = [];
  const installer = { dir: root, installed: () => true, pythonExe: () => 'PY', state: () => ({}) };
  const spawn = (cmd, args, opts) => { const c = new EventEmitter(); c.stdout = new EventEmitter(); c.stderr = new EventEmitter(); setImmediate(() => { fs.writeFileSync(opts.env.SLEEPMODE_OUT, JSON.stringify({ quiz: null, steps: 0, message: 'no new diary day to sleep on' })); c.emit('exit', 0); }); return c; };
  const ws = new WinSleep({ getSettings: () => ({}), root, installer, spawn, hooks: { resumeModel: async (l) => { tried.push(path.basename(l)); return l ? { ok: true, loraFailed: true, error: 'bad lora' } : { ok: true }; } } });
  ws.start();
  for (let i = 0; i < 200 && ws.status().sleeping; i++) await new Promise((x) => setTimeout(x, 10));
  assert.deepStrictEqual(tried, ['adapter.gguf', 'adapter.prev.gguf', '']);
  assert.match(ws.readSummary(), /Nothing new to learn/);
});

test('platform: Windows defaults to the built-in model and gets the preset; Mac keeps the gateway', () => {
  assert.strictEqual(Platform.defaultPreset('win32').id, 'builtin'); assert.strictEqual(Platform.defaultPreset('darwin').id, 'premonition');
  assert.deepStrictEqual(Platform.presetsFor('win32').map((x) => x.label), ['Premonition gateway', 'llama.cpp server', 'Built-in (LFM3)']);
  assert.deepStrictEqual(Platform.presetsFor('darwin').map((x) => x.id), ['premonition', 'llamacpp']);
  assert.strictEqual(Platform.features('win32').builtin, true); assert.strictEqual(Platform.features('linux').builtin, false);
});

// ---- review fixes ------------------------------------------------------------------------------------------------------------
const { tarExe } = require('../src/runtime/install');
const { parseNetstat, parseTasklistImage, reclaimPort } = require('../src/runtime/llamaserver');
const { Builtin } = require('../src/runtime/builtin');
const { DEFAULT_SETTINGS } = require('../src/store');

test('sleep worker loads the downloaded snapshot directly and the HF cache vars agree', () => {
  const e = workerEnv({ python: 'p', home: 'h', outFile: 'o', diaryDir: 'd', sleepmlxParent: 'r', hfHome: 'C:\\R\\hf', hfDir: 'C:\\R\\hf\\models--x\\snapshots\\abc' });
  assert.strictEqual(e.SLEEPMLX_MODEL_DIR, 'C:\\R\\hf\\models--x\\snapshots\\abc');
  assert.strictEqual(e.HF_HUB_CACHE, 'C:\\R\\hf'); assert.strictEqual(e.HF_HOME, 'C:\\R\\hf'); assert.strictEqual(e.HF_HUB_OFFLINE, '1');
  assert.strictEqual('SLEEPMLX_MODEL_DIR' in workerEnv({ python: 'p', home: 'h', outFile: 'o', diaryDir: 'd', sleepmlxParent: 'r', hfHome: 'x' }), false);
});

test('Windows extraction uses System32\\tar.exe, not whatever tar is on PATH', () => {
  const real = process.env.SystemRoot; process.env.SystemRoot = 'C:\\WINDOWS';
  try { assert.strictEqual(tarExe('win32'), path.join('C:\\WINDOWS', 'System32', 'tar.exe')); assert.strictEqual(tarExe('linux'), 'tar'); } finally { if (real === undefined) delete process.env.SystemRoot; else process.env.SystemRoot = real; }
});

test('Mac: "only when plugged in" is off by default (Windows only)', () => {
  assert.strictEqual(DEFAULT_SETTINGS.sleepOnlyPlugged, process.platform === 'win32');
  assert.strictEqual(shouldAutoSleep({ settings: { autoSleep: true, sleepFrom: '01:00', sleepTo: '06:00', sleepIdleMin: 1 }, now: new Date(2026, 9, 28, 2, 0), idleMs: 9e7, systemIdleMs: 9e7, available: true, onBattery: true }).sleep, true);
});

test('gateway: when the app disconnects mid-stream the upstream request is cancelled', async () => {
  let upstreamClosed = false;
  const up = http.createServer((req, res) => {
    if (req.url === '/health') { res.writeHead(200); return res.end('{}'); }
    req.resume(); res.writeHead(200, { 'content-type': 'text/event-stream' }); res.write('data: {"choices":[{"delta":{"content":"x"}}]}\n\n');
    res.on('close', () => { upstreamClosed = true; }); // never ends by itself
  });
  const upPort = await listen(up);
  const gw = createGateway({ upstream: 'http://127.0.0.1:' + upPort, diaryDir: tmp('gwa-') }); const port = await gw.listen(0);
  try {
    const ctl = new AbortController();
    const r = await fetch('http://127.0.0.1:' + port + '/v1/chat/completions', { method: 'POST', body: JSON.stringify({ model: 'fast', messages: [{ role: 'user', content: 'hi' }], stream: true }), signal: ctl.signal });
    await r.body.getReader().read();
    ctl.abort();
    for (let i = 0; i < 100 && !upstreamClosed; i++) await new Promise((x) => setTimeout(x, 20));
    assert.strictEqual(upstreamClosed, true);
  } finally { await gw.close(); await close(up); }
});

test('llama-server: two crashes after it was healthy switch to the CPU build; a launch that times out is killed (one server at a time)', async () => {
  const kids = []; const exes = [];
  const mk = () => { const c = fakeChild(); return c; };
  const srv = new LlamaServer({ exe: 'vk.exe', model: 'm', flavor: 'vulkan', spawn: (exe) => { exes.push(exe); const c = mk(); kids.push(c); return c; }, fetch: async () => ({ ok: true }), pollMs: 5, fastRetry: true, reclaim: async () => 0, cpuFallback: async () => ({ exe: 'cpu.exe' }) });
  await srv.start();
  kids[0].emit('exit', 1); await new Promise((r) => setTimeout(r, 40));
  kids[1].emit('exit', 1); await new Promise((r) => setTimeout(r, 60));
  assert.deepStrictEqual(exes.slice(0, 3), ['vk.exe', 'vk.exe', 'cpu.exe']); assert.strictEqual(srv.o.flavor, 'cpu');
  srv.stop();
  let killed = 0;
  const slow = new LlamaServer({ exe: 'x', model: 'm', spawn: () => { const c = fakeChild(); c.kill = () => { killed++; }; return c; }, fetch: async () => ({ ok: false }), pollMs: 5, startTimeoutMs: 30, reclaim: async () => 0 });
  const r = await slow.start(); assert.strictEqual(r.ok, false); assert.ok(killed >= 1, 'the timed-out launch was killed');
});

test('orphaned llama-server on :18090 is found and killed, but only if the image is llama-server.exe', async () => {
  const net = 'Active Connections\r\n  TCP    0.0.0.0:135    0.0.0.0:0    LISTENING    900\r\n  TCP    127.0.0.1:18090    0.0.0.0:0    LISTENING    4321\r\n  TCP    127.0.0.1:18090    127.0.0.1:50000    ESTABLISHED    4321\r\n';
  assert.strictEqual(parseNetstat(net, 18090), 4321); assert.strictEqual(parseNetstat(net, 9999), 0);
  assert.strictEqual(parseTasklistImage('"llama-server.exe","4321","Console","1","900,000 K"\r\n'), 'llama-server.exe');
  const calls = [];
  const ex = (image) => async (cmd, args) => { calls.push(cmd); return cmd === 'netstat' ? net : cmd === 'tasklist' ? '"' + image + '","4321"' : ''; };
  assert.strictEqual(await reclaimPort(18090, ex('llama-server.exe')), 4321); assert.ok(calls.includes('taskkill'));
  calls.length = 0;
  assert.strictEqual(await reclaimPort(18090, ex('chrome.exe')), 0); assert.ok(!calls.includes('taskkill'));
});

test('Builtin pause/resume: no-ops when the preset is not in use, report ok from the real phase, never start while asleep', async () => {
  let wanted = false; const stops = [];
  const b = new Builtin({ root: tmp('bi-'), isWanted: () => wanted });
  b.server = { stop: async () => { stops.push('stop'); }, start: async () => { b.st.phase = 'ready'; return { ok: true }; }, o: {} };
  assert.deepStrictEqual(await b.pauseForSleep(), { ok: true, skipped: true }); assert.deepStrictEqual(stops, []);
  assert.strictEqual((await b.resume('x')).skipped, true);
  wanted = true; b.running = true;
  await b.pauseForSleep(); assert.deepStrictEqual(stops, ['stop']); assert.strictEqual(b.asleep, true);
  assert.strictEqual((await b.start()).phase, 'off', 'a download finishing during sleep cannot start the model');
  const r = await b.resume(''); assert.strictEqual(r.ok, true); assert.strictEqual(b.asleep, false);
  b.server = null; b.running = false; // no server object: resume goes through start() instead of crashing
  b.start = async () => ({ phase: 'error', error: 'boom' });
  assert.deepStrictEqual(await b.resume(''), { ok: false, error: 'boom' });
});

test('WinSleep converts only when adapter_model.safetensors is newer than the GGUF (not the folder mtime)', async () => {
  const root = tmp('wf-'); const home = path.join(root, 'sleep'); const ad = path.join(home, 'adapter'); fs.mkdirSync(ad, { recursive: true });
  const st = path.join(ad, 'adapter_model.safetensors'); fs.writeFileSync(st, 'w'); const g = path.join(home, 'adapter.gguf'); fs.writeFileSync(g, 'g');
  const t0 = Date.now() / 1000;
  fs.utimesSync(st, t0 - 100, t0 - 100); fs.utimesSync(g, t0 - 50, t0 - 50); fs.utimesSync(ad, t0, t0); // the folder is "new" but the weights are old
  let ran = 0;
  const ws = new WinSleep({ getSettings: () => ({}), root, installer: { dir: root, installed: () => true, pythonExe: () => 'PY', state: () => ({ convert: 'c.py', hfDir: 'HF' }) }, run: async (c, a) => { ran++; fs.writeFileSync(a[a.indexOf('--outfile') + 1], 'n'); return ''; }, hooks: {} });
  await ws._convert(); assert.strictEqual(ran, 0);
  fs.utimesSync(st, t0, t0); await ws._convert(); assert.strictEqual(ran, 1);
});

test('gateway: fast and auto turn LFM3 thinking off, main keeps it, an explicit setting wins', () => {
  assert.deepStrictEqual(mapRequest({ model: 'fast', messages: [] }, 'default').chat_template_kwargs, { enable_thinking: false });
  assert.deepStrictEqual(mapRequest({ model: 'auto' }).chat_template_kwargs, { enable_thinking: false });
  assert.strictEqual(mapRequest({ model: 'main' }).chat_template_kwargs, undefined);
  assert.deepStrictEqual(mapRequest({ model: 'auto', chat_template_kwargs: { enable_thinking: true } }).chat_template_kwargs, { enable_thinking: true });
  assert.strictEqual(mapRequest({ model: 'fast' }, 'default').model, 'default');
});

test('bundled CPU engine: used when nothing is installed, source ref is its commit', () => {
  const d = tmp('bund-'); const exe = path.join(d, 'llama-server.exe'); fs.writeFileSync(exe, 'x');
  const { ChatInstaller } = require('../src/runtime/install');
  const i = new ChatInstaller({ dir: path.join(d, 'rt'), bundledExe: exe });
  assert.strictEqual(i.llamaExe('cpu').exe, exe); assert.strictEqual(i.llamaExe('cpu').tag, C.BUNDLED_LLAMA_COMMIT);
  assert.strictEqual(i.llamaExe('vulkan'), null);
  assert.strictEqual(R.llamaSourceUrl(C.BUNDLED_LLAMA_COMMIT), 'https://github.com/ggml-org/llama.cpp/archive/' + C.BUNDLED_LLAMA_COMMIT + '.zip');
  assert.strictEqual(R.llamaSourceUrl('b12000'), 'https://github.com/ggml-org/llama.cpp/archive/refs/tags/b12000.zip');
});

test('userData drives every runtime path (--user-data-dir)', () => {
  const { runtimeRoot, Builtin } = require('../src/runtime/builtin');
  const { WinSleep } = require('../src/sleepwin');
  const path = require('path'); const fs = require('fs');
  const ud = path.resolve('/tmp/custom-ud');
  const root = runtimeRoot(ud); assert.strictEqual(root, ud);
  const b = new Builtin({ root, isWanted: () => false, onState() {} });
  assert.ok(b.dir.startsWith(ud) && b.diaryDir.startsWith(ud));
  const src = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.ok(/runtimeRoot\(app\.getPath\('userData'\)\)/.test(src));
  // appData is only used to find the OLD "Premonition Desk" folder to migrate from
  const uses = src.match(/getPath\('appData'\)/g) || [];
  assert.strictEqual(uses.length, 1);
  assert.ok(/migrateUserData\(app\.getPath\('appData'\), app\.getPath\('userData'\)\)/.test(src));
  assert.ok(typeof WinSleep === 'function');
});

test('gateway: LFM3 reasoning before "</think>" leaves the reply (non-stream and stream, tag split across chunks)', () => {
  const { splitThink, SseThink } = require('../src/gateway');
  assert.deepStrictEqual(splitThink('The user wants hi. </think>\n\nHi!'), { reasoning: 'The user wants hi.', content: 'Hi!' });
  assert.deepStrictEqual(splitThink('Hi!'), { reasoning: '', content: 'Hi!' });
  const ev = (t, extra) => 'data: ' + JSON.stringify({ id: 'x', choices: [{ index: 0, delta: t == null ? {} : { content: t }, finish_reason: null, ...(extra || {}) }] }) + '\n\n';
  const run = (parts) => {
    const s = new SseThink(); let out = '';
    for (const p of parts) out += s.push(p);
    out += s.push('data: [DONE]\n\n') + s.flush();
    const sse = new SseText(); sse.push(out);
    let reasoning = ''; for (const l of out.split('\n')) { if (!l.startsWith('data: {')) continue; const d = JSON.parse(l.slice(6)).choices[0].delta; if (d.reasoning_content) reasoning += d.reasoning_content; }
    return { content: sse.text, reasoning, done: out.includes('[DONE]') };
  };
  const a = run([ev('We need to say hi. '), ev('</thi'), ev('nk>\n\nHel'), ev('lo!'), ev(null, { finish_reason: 'stop' })]);
  assert.strictEqual(a.content, 'Hello!'); assert.strictEqual(a.reasoning, 'We need to say hi. '); assert.ok(a.done);
  const b = run([ev('Hello '), ev('there!'), ev(null, { finish_reason: 'stop' })]); // no tag: the held text is the reply
  assert.strictEqual(b.content, 'Hello there!');
  const long = 'x'.repeat(1300);
  const c = run([ev(long), ev(' more'), ev(null, { finish_reason: 'stop' })]);
  assert.strictEqual(c.content, long + ' more');
});
