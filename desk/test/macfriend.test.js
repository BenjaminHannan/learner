'use strict';
// The built-in Mac (Nov 5, "uncle" build): Nanbeige4.2-3B sized by memory, the bundled Metal engine, an 8 GB Mac told plainly.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const C = require('../src/runtime/constants');
const G = require('../src/runtime/gpu');
const { ChatInstaller } = require('../src/runtime/install');
const GIB = 1024 ** 3;

test('memory picks the brain: >= 24 GB Q8_0, 16 GB Q4_K_M, 8 GB none (too small)', () => {
  assert.strictEqual(G.macQuantFor(32 * GIB), 'q8_0');
  assert.strictEqual(G.macQuantFor(24 * GIB), 'q8_0');
  assert.strictEqual(G.macQuantFor(18 * GIB), 'q4_k_m');
  assert.strictEqual(G.macQuantFor(16 * GIB), 'q4_k_m');
  assert.strictEqual(G.macQuantFor(8 * GIB), '');
  assert.deepStrictEqual(G.macMemory({ env: { PREMONITION_RAM_GB: '8' } }), { bytes: 8 * GIB, source: 'env' });
  assert.strictEqual(G.macMemory({ env: {}, totalmem: () => 16 * GIB }).bytes, 16 * GIB);
  for (const k of ['q8_0', 'q4_k_m', C.MAC_SMALL]) assert.match(C.NB_MODELS[k].sha256, /^[0-9a-f]{64}$/);
});

function fakeFetch(body) {
  return async (url, opts) => {
    const range = opts && opts.headers && opts.headers.range;
    const start = range ? Number(/bytes=(\d+)-/.exec(range)[1]) : 0;
    const chunk = body.subarray(start);
    return { ok: true, status: range ? 206 : 200, headers: new Map([['content-length', String(chunk.length)]]), url,
      body: { getReader: () => { let sent = false; return { read: async () => (sent ? { done: true } : (sent = true, { value: chunk, done: false })) }; } } };
  };
}

test('an 8 GB Mac: a too_small error with plain words, no download; "Try the small brain anyway" then gets IQ3_M', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mf-'));
  const body = Buffer.from('gguf-small');
  const models = { ...C.NB_MODELS, iq3_m: { file: 'small.gguf', size: body.length, sha256: crypto.createHash('sha256').update(body).digest('hex') } };
  let calls = 0; const f = fakeFetch(body);
  const inst = new ChatInstaller({ dir, platform: 'darwin', winModels: models, macMemory: () => ({ bytes: 8 * GIB, source: 'os' }), fetch: (...a) => { calls++; return f(...a); } });
  await assert.rejects(inst.ensureModel(), (e) => e.code === 'too_small' && /8 GB of memory/.test(e.message) && /at least 16 GB/.test(e.message));
  assert.strictEqual(calls, 0, 'nothing downloaded');
  inst.allowSmall();
  const m = await inst.ensureModel();
  assert.strictEqual(m.quant, 'iq3_m'); assert.ok(fs.existsSync(m.file));
  assert.strictEqual(inst.state().vram.source, 'ram:os');
});

test('a 32 GB Mac downloads Q8_0 and keeps the choice', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mf-'));
  const body = Buffer.from('gguf-q8');
  const models = { ...C.NB_MODELS, q8_0: { file: 'q8.gguf', size: body.length, sha256: crypto.createHash('sha256').update(body).digest('hex') } };
  let ram = 32 * GIB;
  const inst = new ChatInstaller({ dir, platform: 'darwin', winModels: models, macMemory: () => ({ bytes: ram, source: 'os' }), fetch: fakeFetch(body) });
  const m = await inst.ensureModel();
  assert.strictEqual(m.quant, 'q8_0'); assert.strictEqual(m.family, 'nanbeige'); assert.ok(m.template.endsWith('nanbeige-chat-template.jinja'));
  ram = 8 * GIB;   // a later odd reading does not swap the brain
  assert.strictEqual((await inst.ensureModel()).quant, 'q8_0');
});

test('the Mac engine comes from inside the app: checksum checked, unpacked, quarantine cleared, no GitHub', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mf-'));
  const arc = path.join(dir, 'llama-b11946-bin-macos-arm64.tar.gz'); fs.writeFileSync(arc, 'tgz');
  const sha = crypto.createHash('sha256').update('tgz').digest('hex');
  let unq = 0;
  const inst = new ChatInstaller({ dir: path.join(dir, 'rt'), platform: 'darwin', bundledArchive: arc, fallbackSha256: { [path.basename(arc)]: sha },
    fetch: () => { throw new Error('no network expected'); },
    extract: async (a, dest) => { fs.mkdirSync(path.join(dest, 'llama-b11946'), { recursive: true }); fs.writeFileSync(path.join(dest, 'llama-b11946', 'llama-server'), ''); },
    unquarantine: async () => { unq++; } });
  const r = await inst.ensureLlama('metal');
  assert.strictEqual(r.tag, 'b11946'); assert.ok(r.exe.endsWith('llama-server')); assert.strictEqual(unq, 1);
  assert.ok(inst.llamaExe('metal'));
  const bad = new ChatInstaller({ dir: path.join(dir, 'rt2'), platform: 'darwin', bundledArchive: arc, fallbackSha256: { [path.basename(arc)]: '0'.repeat(64) } });
  await assert.rejects(bad.ensureLlama('metal'), /damaged/);
});

test('main.js: built-in Mac sleep is off with a plain reason; the Mac has its own update list', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  assert.match(m, /process\.platform === 'darwin' \? MAC_SLEEP_OFF/);
  assert.match(m, /assetKey: 'macnb'/);
  const U = require('../src/updater');
  const man = { version: '9.0.0', mac: { url: 'https://x/a.zip', sha256: 'a'.repeat(64) }, macnb: { url: 'https://x/b.zip', sha256: 'b'.repeat(64) } };
  assert.strictEqual(U.pickAsset(man, 'darwin', 'arm64', { key: 'macnb' }).url, 'https://x/b.zip');
  assert.strictEqual(U.pickAsset({ version: '9.0.0', mac: man.mac }, 'darwin', 'arm64', { key: 'macnb' }), null, 'never the LFM3 "mac" entry');
});

test('Builtin: a too-small Mac ends in phase "blocked" (not a retryable error), and trySmall() goes on with the small brain', async () => {
  const { Builtin } = require('../src/runtime/builtin');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'mf-'));
  const b = new Builtin({ root, platform: 'darwin', macMemory: () => ({ bytes: 8 * GIB, source: 'os' }), privateChecker: { ensureIdle: async () => ({ ok: true, processStopped: true }) } });
  b.installer.llamaExe = () => ({ exe: '/x/llama-server', tag: 't' });
  const st = await b.start();
  assert.strictEqual(st.phase, 'blocked'); assert.ok(st.canTrySmall); assert.match(st.error, /too small/);
  let asked = null; b.installer.ensureModel = async () => { asked = b.installer.state().allowSmall; throw new Error('stop here'); };
  const st2 = await b.trySmall();
  assert.strictEqual(asked, true); assert.strictEqual(st2.phase, 'error');
});

test('a download that goes silent is dropped after stallMs and resumes from the .part file', async () => {
  const { downloadFile } = require('../src/runtime/download');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mf-'));
  const body = Buffer.from('0123456789abcdefghij');
  const sha = crypto.createHash('sha256').update(body).digest('hex');
  let n = 0; const ranges = [];
  const f = async (url, opts) => {
    n++; const range = opts.headers.range; ranges.push(range || '');
    const start = range ? Number(/bytes=(\d+)-/.exec(range)[1]) : 0;
    const first = n === 1;   // attempt 1 sends 8 bytes, then hangs forever
    const chunk = first ? body.subarray(0, 8) : body.subarray(start);
    return { ok: true, status: range ? 206 : 200, headers: new Map([['content-length', String(body.length - start)]]),
      body: { getReader: () => { let k = 0; return { read: () => (k++ === 0 ? Promise.resolve({ value: chunk, done: false }) : first ? new Promise(() => {}) : Promise.resolve({ done: true })) }; } } };
  };
  const retries = [];
  const r = await downloadFile({ url: 'https://x/f', dest: path.join(dir, 'f.bin'), sha256: sha, fetch: f, stallMs: 50, retryDelayMs: 1, onRetry: (e) => retries.push(e.code) });
  assert.strictEqual(fs.readFileSync(r.dest).toString(), body.toString());
  assert.deepStrictEqual(retries, ['stalled']); assert.deepStrictEqual(ranges, ['', 'bytes=8-']);
});
