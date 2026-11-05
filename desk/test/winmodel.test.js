'use strict';
// Windows brain (Nov 4): Nanbeige4.2-3B GGUF, Q8_0 with >= 12 GB of graphics memory, else Q4_K_M; Glim's chat template beside it.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs'); const os = require('os'); const path = require('path'); const crypto = require('crypto');
const C = require('../src/runtime/constants');
const G = require('../src/runtime/gpu');
const { ChatInstaller } = require('../src/runtime/install');
const { buildArgs } = require('../src/runtime/llamaserver');

const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const tmp = (p) => fs.mkdtempSync(path.join(os.tmpdir(), p));

test('VRAM: nvidia-smi MiB, registry REG_QWORD (BensPC 0x3faf00000) and REG_BINARY parse; the largest adapter wins', () => {
  assert.strictEqual(G.parseNvidiaSmi('16303\r\n'), 16303 * 1024 * 1024);
  assert.strictEqual(G.parseNvidiaSmi('NVIDIA-SMI has failed'), 0);
  const reg = 'HKEY_LOCAL_MACHINE\\...\\0000\r\n    HardwareInformation.qwMemorySize    REG_QWORD    0x3faf00000\r\n\r\nHKEY...\\0001\r\n    HardwareInformation.qwMemorySize    REG_QWORD    0x20000000\r\n';
  assert.strictEqual(G.parseRegQuery(reg), 0x3faf00000);
  assert.strictEqual(G.parseRegQuery('    HardwareInformation.qwMemorySize    REG_BINARY    0000000004000000'), 0x400000000);
  assert.strictEqual(G.parseRegQuery('ERROR: The system was unable to find the specified registry key or value.'), 0);
});

test('VRAM detection order: env override, then nvidia-smi, then the registry, else unknown', async () => {
  const calls = [];
  const exec = (out) => async (cmd) => { calls.push(cmd); return out[cmd] || ''; };
  assert.deepStrictEqual(await G.detectVram({ env: { PREMONITION_VRAM_GB: '8' }, platform: 'win32', exec: exec({}) }), { bytes: 8 * G.GIB, source: 'env' });
  assert.deepStrictEqual(await G.detectVram({ env: {}, platform: 'win32', exec: exec({ 'nvidia-smi': '16303' }) }), { bytes: 16303 * 1048576, source: 'nvidia-smi' });
  // an AMD card: no nvidia-smi
  const amd = await G.detectVram({ env: {}, platform: 'win32', exec: exec({ reg: '    HardwareInformation.qwMemorySize    REG_QWORD    0x3fc000000' }) });
  assert.strictEqual(amd.source, 'registry'); assert.strictEqual(G.quantFor(amd.bytes), 'q8_0');
  assert.deepStrictEqual(await G.detectVram({ env: {}, platform: 'win32', exec: exec({}) }), { bytes: 0, source: 'none' });
});

test('quant: >= 12 GB (with a hair of slack) -> Q8_0; less or unknown -> Q4_K_M', () => {
  assert.strictEqual(G.quantFor(0x3faf00000), 'q8_0');       // 15.9 GiB (5070 Ti)
  assert.strictEqual(G.quantFor(16 * G.GIB), 'q8_0');        // RX 6950 XT
  assert.strictEqual(G.quantFor(11.9 * G.GIB), 'q8_0');      // a 12 GB card reported a little under
  assert.strictEqual(G.quantFor(8 * G.GIB), 'q4_k_m');
  assert.strictEqual(G.quantFor(0), 'q4_k_m');
  assert.match(C.WIN_MODELS.q8_0.file, /Nanbeige4\.2-3B-Q8_0\.gguf$/); assert.match(C.WIN_MODELS.q4_k_m.file, /Q4_K_M\.gguf$/);
  for (const m of Object.values(C.WIN_MODELS)) assert.match(m.sha256, /^[0-9a-f]{64}$/);
});

function winInst(dir, vramGb, seen) {
  const q8 = Buffer.from('GGUF-q8'), q4 = Buffer.from('GGUF-q4');
  const winModels = { q8_0: { file: 'N-Q8_0.gguf', size: q8.length, sha256: sha(q8) }, q4_k_m: { file: 'N-Q4_K_M.gguf', size: q4.length, sha256: sha(q4) } };
  const fetch = async (url) => { seen.push(String(url)); const b = /Q8_0/.test(url) ? q8 : q4; return new Response(b, { status: 200, headers: { 'content-length': String(b.length) } }); };
  return new ChatInstaller({ dir, platform: 'win32', fetch, winModels, detectVram: async () => ({ bytes: vramGb * G.GIB, source: 'test' }) });
}

test('Windows install: a 16 GB card gets Q8_0 from the Nanbeige repo, the template is written, and the choice is kept', async () => {
  const d = tmp('winm-'); const seen = [];
  const m = await winInst(d, 16, seen).ensureModel();
  assert.strictEqual(m.quant, 'q8_0'); assert.strictEqual(m.family, 'nanbeige');
  assert.ok(seen[0].startsWith('https://huggingface.co/' + C.WIN_MODEL_REPO + '/resolve/main/N-Q8_0.gguf'));
  assert.strictEqual(fs.readFileSync(m.file, 'utf8'), 'GGUF-q8');
  assert.ok(m.template && fs.readFileSync(m.template, 'utf8').includes('enable_thinking'), 'Glim\'s chat template sits beside the models');
  assert.strictEqual(JSON.parse(fs.readFileSync(path.join(d, 'state.json'))).vram.source, 'test');
  // a second start: no download, even if the card now reads smaller
  const again = await winInst(d, 4, seen).ensureModel();
  assert.strictEqual(again.quant, 'q8_0'); assert.strictEqual(seen.length, 1);
});

test('Windows install: an 8 GB card gets Q4_K_M; an old LFM3 install is replaced and its file removed', async () => {
  const d = tmp('winm-'); const seen = [];
  const old = path.join(d, 'models', C.MODEL_FILE); fs.mkdirSync(path.dirname(old), { recursive: true }); fs.writeFileSync(old, 'lfm3');
  fs.writeFileSync(path.join(d, 'state.json'), JSON.stringify({ model: { file: old, name: C.MODEL_FILE, sha256: 'a'.repeat(64) } }));
  const m = await winInst(d, 8, seen).ensureModel();
  assert.strictEqual(m.quant, 'q4_k_m'); assert.ok(/N-Q4_K_M\.gguf$/.test(m.file));
  assert.ok(!fs.existsSync(old), 'the LFM3 file is gone');
});

test('llama-server gets Glim\'s chat template file when there is one', () => {
  const a = buildArgs({ model: 'C:\\m\\N.gguf', flavor: 'vulkan', chatTemplate: 'C:\\r\\t.jinja' });
  assert.deepStrictEqual(a.slice(a.indexOf('--chat-template-file'), a.indexOf('--chat-template-file') + 2), ['--chat-template-file', 'C:\\r\\t.jinja']);
  assert.ok(!buildArgs({ model: 'm', flavor: 'vulkan' }).includes('--chat-template-file'));
});

// ---- Windows eyes (Nov 4): llama-server reads pictures through Glim's mmproj; the app only shrinks the screenshot ----------
const EyesMod = require('../src/eyes');

test('PictureWorker shrinks to a JPEG data URL; a look keeps it as a one-shot image_url frame and stores no features', async () => {
  const d = tmp('wineyes-');
  const small = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3]);
  const seen = [];
  const worker = new EyesMod.PictureWorker({ resize: async (b) => { seen.push(b.length); return small; } });
  const eyes = new EyesMod.Eyes({ userData: d, on: () => true, worker, shot: async () => Buffer.from([0xff, 0xd8, 9, 9, 9, 9]) });
  const r = await eyes.look('Weather 75 degrees', 'Front app: Edge.');
  assert.deepStrictEqual({ stored: r.stored, picture: r.picture }, { stored: false, picture: true });
  assert.deepStrictEqual(seen, [6]);
  const part = eyes.framePart();
  assert.deepStrictEqual(part, { type: 'image_url', image_url: { url: 'data:image/jpeg;base64,' + small.toString('base64') } });
  assert.strictEqual(eyes.framePart(), null, 'one-shot');
  assert.strictEqual(eyes.store.days().length, 0, 'no features kept for sense sleep');
  const msgs = EyesMod.withFrame([{ role: 'user', content: 'what is this?' }], part);
  assert.deepStrictEqual(msgs[0].content[1], part);
  // a resize that fails never stores and never throws
  const bad = new EyesMod.Eyes({ userData: d, on: () => true, worker: new EyesMod.PictureWorker({ resize: async () => null }), shot: async () => Buffer.from([0xff, 0xd8, 1, 1]) });
  assert.match((await bad.look('x', '')).error, /could not shrink/);
});

test('llama-server gets --mmproj only when the eyes file exists and the brain is Nanbeige', () => {
  const { Builtin } = require('../src/runtime/builtin');
  const d = tmp('wineyes-'); const f = path.join(d, 'eyes.gguf'); fs.writeFileSync(f, 'x');
  const b = new Builtin({ root: d, platform: 'win32', mmproj: f });
  assert.strictEqual(b._mmproj({ family: 'nanbeige' }), f);
  assert.strictEqual(b._mmproj({ name: C.MODEL_FILE }), '', 'another brain never gets Glim\'s projector');
  assert.strictEqual(new Builtin({ root: d, platform: 'win32', mmproj: path.join(d, 'missing.gguf') })._mmproj({ family: 'nanbeige' }), '');
  const a = buildArgs({ model: 'm', flavor: 'vulkan', mmproj: f });
  assert.deepStrictEqual(a.slice(a.indexOf('--mmproj'), a.indexOf('--mmproj') + 2), ['--mmproj', f]);
});

test('sleep with an unsupported brain: not available, start refuses before any download or model pause', () => {
  const { WinSleep } = require('../src/sleepwin');
  const events = [];
  const ws = new WinSleep({ getSettings: () => ({}), root: tmp('winsleep-'), platform: 'win32', unsupported: () => 'not on this PC yet',
    installer: { state: () => ({}), installed: () => false, plan: () => events.push('plan'), pythonExe: () => 'py' }, hooks: { pauseModel: () => events.push('pause') } });
  assert.deepStrictEqual({ ok: ws.available().ok, reason: ws.available().reason }, { ok: false, reason: 'not on this PC yet' });
  assert.deepStrictEqual(ws.start({}), { ok: false, error: 'not on this PC yet' });
  assert.deepStrictEqual(events, []);
  assert.strictEqual(new WinSleep({ getSettings: () => ({}), root: tmp('winsleep-'), installer: { pythonExe: () => 'py' } }).available().ok, true);
});

// Radeon/Nanbeige build: its own update list and key, so the LFM3 Windows zip ("win", 1.2.4) can never replace it
test('Windows updates read only the "winamd" entry; a local http list is allowed only for tests', () => {
  const { pickAsset, winScript, WINAMD_MANIFEST_URL, MANIFEST_URL } = require('../src/updater');
  const sha = 'a'.repeat(64);
  const m = { version: '9.9.9', win: { url: 'https://x/old-lfm3.zip', sha256: sha }, winamd: { url: 'https://x/new.zip', sha256: sha } };
  assert.notStrictEqual(WINAMD_MANIFEST_URL, MANIFEST_URL);
  assert.strictEqual(pickAsset(m, 'win32', 'x64', { key: 'winamd' }).url, 'https://x/new.zip');
  assert.strictEqual(pickAsset({ version: '9.9.9', win: m.win }, 'win32', 'x64', { key: 'winamd' }), null);
  const local = { winamd: { url: 'http://127.0.0.1:18555/u.zip', sha256: sha } };
  assert.strictEqual(pickAsset(local, 'win32', 'x64', { key: 'winamd' }), null);
  assert.ok(pickAsset(local, 'win32', 'x64', { key: 'winamd', allowLoopback: true }));
  assert.strictEqual(pickAsset({ winamd: { url: 'http://evil.example/u.zip', sha256: sha } }, 'win32', 'x64', { key: 'winamd', allowLoopback: true }), null);
  const w = winScript({ pid: 9, dir: 'C:\\P', staged: 'C:\\t', exe: 'Premonition.exe', args: ['--user-data-dir=C:\\ud', '--evil="x" & calc'] });
  assert.match(w, /start "" "C:\\P[\\/]Premonition\.exe" "--user-data-dir=C:\\ud"\r\n/);
  assert.doesNotMatch(w, /calc/);
  assert.strictEqual(require('../package.json').version.split('.')[0] >= '2', true);
});

test('old update downloads are cleaned from the temp folder', () => {
  const fs = require('fs'), os = require('os'), path = require('path');
  const { Updater } = require('../src/updater');
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'upclean-'));
  const old = path.join(tmp, 'premonition-update-old'), fresh = path.join(tmp, 'premonition-update-new'), other = path.join(tmp, 'keep-me');
  for (const d of [old, fresh, other]) fs.mkdirSync(d);
  const t = (Date.now() - 3600e3) / 1000; fs.utimesSync(old, t, t); fs.utimesSync(other, t, t);
  assert.strictEqual(new Updater({ version: '2.0.0', tmp }).cleanOld(), 1);
  assert.ok(!fs.existsSync(old) && fs.existsSync(fresh) && fs.existsSync(other));
  fs.rmSync(tmp, { recursive: true, force: true });
});
