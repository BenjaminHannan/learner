'use strict';
// Sleep on the built-in model off Windows (a Mac without Ben's assistant), the adapter records (adapter.gguf.json: which base it was
// trained on), the served check after the adapter is loaded, set-aside of a bad adapter, and the truthful morning summary.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { EventEmitter } = require('events');
const R = require('../src/runtime/releases');
const CK = require('../src/checkin');
const { pipTorchArgs, pythonPath, SleepInstaller } = require('../src/runtime/sleepinstall');
const { WinSleep, workerCommand, sleepProfile, loraFits, readSidecar, nightLines, loadedLine, servedCheckCommand, LORA_BASE } = require('../src/sleepwin');

const tmp = (n) => fs.mkdtempSync(path.join(os.tmpdir(), n));
const until = async (f) => { for (let i = 0; i < 300 && !f(); i++) await new Promise((x) => setTimeout(x, 10)); };
const fakeSpawn = (outs) => {
  let n = 0;
  const spawn = (cmd, args, opts) => {
    spawn.calls.push({ cmd, args, env: opts.env });
    const c = new EventEmitter(); c.stdout = new EventEmitter(); c.stderr = new EventEmitter(); c.kill = () => {};
    setImmediate(() => { const o = outs[Math.min(n++, outs.length - 1)]; if (typeof o === 'function') o(opts); else fs.writeFileSync(opts.env.SLEEPMODE_OUT, JSON.stringify(o)); c.emit('exit', 0); });
    return c;
  };
  spawn.calls = [];
  return spawn;
};
const installer = (root, st) => ({ dir: root, installed: () => true, pythonExe: () => 'PY', plan: () => ({}), state: () => st || {} });

test('Mac sleep runtime: aarch64 Python, bin/python3, the default PyPI torch (MPS), the lfm3_mps recipe', () => {
  const rels = [{ tag_name: '20260301', published_at: '2026-03-01T00:00:00Z', assets: [
    { name: 'cpython-3.12.10+20260301-x86_64-pc-windows-msvc-install_only.tar.gz', browser_download_url: 'win' },
    { name: 'cpython-3.12.10+20260301-aarch64-apple-darwin-install_only.tar.gz', browser_download_url: 'mac' },
    { name: 'cpython-3.12.10+20260301-x86_64-apple-darwin-install_only.tar.gz', browser_download_url: 'intel' }] }];
  assert.strictEqual(R.pickPython(rels, null, 'darwin').url, 'mac');
  assert.strictEqual(R.pickPython(rels).url, 'win', 'Windows stays the default');
  assert.strictEqual(pythonPath('/R', 'darwin'), path.join('/R', 'python', 'bin', 'python3'));
  assert.strictEqual(pythonPath('/R', 'win32'), path.join('/R', 'python', 'python.exe'));
  assert.strictEqual(new SleepInstaller({ root: '/X', platform: 'darwin' }).pythonExe(), path.join('/X', 'sleep-runtime', 'python', 'bin', 'python3'));
  assert.ok(!pipTorchArgs('darwin').includes('--index-url')); assert.strictEqual(pipTorchArgs('darwin').slice(-1)[0], 'torch');
  assert.ok(pipTorchArgs('win32').includes('--index-url'));
  assert.strictEqual(sleepProfile('darwin'), 'lfm3_mps'); assert.strictEqual(sleepProfile('win32'), 'lfm3_cpu');
  const w = workerCommand({ platform: 'darwin', python: 'PY', home: '/h', outFile: '/o', diaryDir: '/d', sleepmlxParent: '/res', hfHome: '/hf' });
  assert.deepStrictEqual(w.args, ['-m', 'sleepmlx.worker', '--profile', 'lfm3_mps']);
  const sc = servedCheckCommand({ python: 'PY', url: 'http://127.0.0.1:18090', cards: '/h/cards.jsonl', sleepmlxParent: '/res' });
  assert.deepStrictEqual(sc.args, ['-m', 'sleepmlx', 'served-check', '--server', 'http://127.0.0.1:18090', '--cards', '/h/cards.jsonl']);
  assert.strictEqual(sc.env.PYTHONPATH, '/res');
});

test('adapter records: an adapter trained on another base is never loaded; an old one with no record still is', () => {
  const home = tmp('fit-');
  const g = path.join(home, 'adapter.gguf'); const p = path.join(home, 'adapter.prev.gguf');
  assert.strictEqual(loraFits(g), false, 'missing file');
  fs.writeFileSync(g, 'x'); assert.strictEqual(loraFits(g), true, 'no record: made by this runner, which only trains ' + LORA_BASE);
  fs.writeFileSync(g + '.json', JSON.stringify({ base_hf_id: 'Qwen/Qwen3.6-35B' })); assert.strictEqual(loraFits(g), false);
  fs.writeFileSync(p, 'y'); fs.writeFileSync(p + '.json', JSON.stringify({ base_hf_id: LORA_BASE }));
  const ws = new WinSleep({ getSettings: () => ({}), root: path.dirname(home), installer: installer(home), hooks: {} });
  ws.home = home; ws.adapterGguf = g; ws.adapterPrev = p;
  assert.strictEqual(ws.currentLora(), p, 'the model starts with the fitting previous adapter');
  assert.strictEqual(CK.checkinAdapter(home, fs.existsSync, (f) => loraFits(f)), p, 'check-ins too');
  assert.strictEqual(CK.checkinAdapter(home, fs.existsSync), g, 'without a fit test: the old behaviour');
});

test('startup keeps the previous adapter while a candidate awaits its persisted served check', (t) => {
  const root = tmp('pending-lora-'), home = path.join(root, 'sleep'); fs.mkdirSync(home, { recursive: true });
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const candidate = path.join(home, 'adapter.gguf'), previous = path.join(home, 'adapter.prev.gguf');
  fs.writeFileSync(candidate, 'candidate'); fs.writeFileSync(previous, 'previous');
  fs.writeFileSync(candidate + '.json', JSON.stringify({ base_hf_id: LORA_BASE, served: { ok: null, pending: true } }));
  fs.writeFileSync(previous + '.json', JSON.stringify({ base_hf_id: LORA_BASE, served: { ok: true } }));
  const ws = new WinSleep({ root, getSettings: () => ({}) });
  assert.strictEqual(loraFits(candidate), false);
  assert.strictEqual(ws.currentLora(), previous);
  fs.writeFileSync(candidate + '.json', JSON.stringify({ base_hf_id: LORA_BASE, served: { ok: true } }));
  assert.strictEqual(ws.currentLora(), candidate);
});

test('wake: a converted adapter gets its record, is loaded, checked in the model server once, and the summary says so', async () => {
  const root = tmp('sm-'); const home = path.join(root, 'sleep');
  const night = { quiz: 50, recall_pre: 0, held_out: 4, general: 95, general_base: 95, reverted: false, status: 'done', date: '2026-10-26', dreamcheck: { available: true, n: 12, supported: 4, unknown: 7, contradicted: 1, unchecked: 0 } };
  const spawn = fakeSpawn([(opts) => { fs.mkdirSync(path.join(home, 'adapter'), { recursive: true }); fs.writeFileSync(path.join(home, 'adapter', 'adapter_model.safetensors'), 'w'); fs.writeFileSync(opts.env.SLEEPMODE_OUT, JSON.stringify(night)); }]);
  const run = async (cmd, args) => { fs.writeFileSync(args[args.indexOf('--outfile') + 1], 'gguf'); return ''; };
  const checks = []; const resumed = [];
  const servedCheck = async (cmd) => { checks.push(cmd); return { ok: true, reasons: [], general_on: 7, general_off: 7, general_n: 8, held_on: 3, held_off: 0, held_n: 4 }; };
  const ws = new WinSleep({ platform: 'darwin', getSettings: () => ({}), root, installer: installer(root, { convert: 'conv.py', hfDir: 'HF' }), spawn, run, servedCheck,
    hooks: { pauseModel: async () => {}, resumeModel: async (l) => { resumed.push(l); return { ok: true }; }, servedUrl: () => 'http://127.0.0.1:18090' } });
  assert.strictEqual(ws.start().ok, true);
  await until(() => !ws.status().sleeping);
  assert.deepStrictEqual(spawn.calls[0].args.slice(-1), ['lfm3_mps']);
  assert.strictEqual(ws.status().mode, 'builtin');
  const rec = readSidecar(path.join(home, 'adapter.gguf'));
  assert.strictEqual(rec.base_hf_id, LORA_BASE); assert.strictEqual(rec.profile, 'lfm3_mps'); assert.strictEqual(rec.served.ok, true);
  assert.deepStrictEqual(resumed, [path.join(home, 'adapter.gguf')]);
  assert.strictEqual(checks.length, 1); assert.ok(checks[0].args.includes('served-check'));
  const s = ws.readSummary();
  assert.match(s, /held-out recall, strict: 4 questions it never trained on\): 0% before -> 50% after/);
  assert.match(s, /Kept: it passed the morning check/);
  assert.match(s, /4 supported, 7 unknown, 1 contradicted \(dropped\)/);
  assert.match(s, /Glim now runs with tonight's adapter \(adapter\.gguf\)\. Checked in the model server: general 7\/8 with it vs 7\/8 without; held-out 3\/4 vs 0\/4/);
  // the next wake does not check the same file again (the record keeps the pass)
  const again = await ws._servedCheck(path.join(home, 'adapter.gguf'));
  assert.strictEqual(again.ok, true); assert.strictEqual(checks.length, 1);
});

test('wake: an adapter that loads but scores worse in the server is set aside (kept, not deleted, not converted again); the previous one runs', async () => {
  const root = tmp('sm2-'); const home = path.join(root, 'sleep'); fs.mkdirSync(path.join(home, 'adapter'), { recursive: true });
  fs.writeFileSync(path.join(home, 'adapter.gguf'), 'prev-good'); fs.writeFileSync(path.join(home, 'adapter.gguf.json'), JSON.stringify({ base_hf_id: LORA_BASE, served: { ok: true } }));
  const night = { quiz: 25, recall_pre: 0, held_out: 4, general: 90, general_base: 92, reverted: false, status: 'done' };
  const spawn = fakeSpawn([(opts) => { const w = path.join(home, 'adapter', 'adapter_model.safetensors'); fs.writeFileSync(w, 'w' + Date.now()); const later = new Date(Date.now() + 5000); fs.utimesSync(w, later, later); // clearly newer than the old GGUF, whatever the filesystem's timestamp resolution
    fs.writeFileSync(opts.env.SLEEPMODE_OUT, JSON.stringify(night)); }]);
  let conversions = 0;
  const run = async (cmd, args) => { conversions++; fs.writeFileSync(args[args.indexOf('--outfile') + 1], 'new-bad'); return ''; };
  const resumed = [];
  const servedCheck = async () => ({ ok: false, reasons: ['general only 0/8 with the adapter (broken adapter?)'] });
  const mk = () => new WinSleep({ platform: 'darwin', getSettings: () => ({}), root, installer: installer(root, { convert: 'conv.py', hfDir: 'HF' }), spawn, run, servedCheck,
    hooks: { pauseModel: async () => {}, resumeModel: async (l) => { resumed.push(path.basename(l)); return { ok: true }; }, servedUrl: () => 'http://127.0.0.1:18090' } });
  const ws = mk();
  ws.start(); await until(() => !ws.status().sleeping);
  assert.deepStrictEqual(resumed, ['adapter.gguf', 'adapter.prev.gguf'], 'the new one, then the previous (already checked) one');
  assert.strictEqual(fs.readFileSync(path.join(home, 'adapter.rejected.gguf'), 'utf8'), 'new-bad');
  assert.strictEqual(readSidecar(path.join(home, 'adapter.rejected.gguf')).served.ok, false);
  assert.strictEqual(fs.existsSync(path.join(home, 'adapter.gguf')), false);
  assert.strictEqual(ws.currentLora(), path.join(home, 'adapter.prev.gguf'), 'the app starts with the previous adapter');
  const s = ws.readSummary();
  assert.match(s, /Glim now runs with the previous adapter \(adapter\.prev\.gguf\)/);
  assert.match(s, /Set aside: adapter\.gguf scored worse in the model server: general only 0\/8/);
  // the same trained adapter is not converted (and rejected) again on the next wake
  await ws._convert();
  assert.strictEqual(conversions, 1);
});

test('wake: no model server address -> the adapter is used and the summary says it was not checked', () => {
  assert.match(loadedLine({ lora: 'adapter.gguf', tried: [], served: { ok: null, reasons: ['not checked: the model server address is unknown'] } }, true), /Not checked in the model server \(not checked: the model server address is unknown\)/);
  assert.match(loadedLine({ lora: '', tried: [{ lora: 'adapter.gguf', why: 'trained on another base (Qwen/Qwen3.6)' }], ok: true }, false), /plain model \(adapter\.gguf trained on another base/);
});

test('morning summary facts: an undone night says why; a missing dream checker is said plainly', () => {
  const t = nightLines({ quiz: 20, recall_pre: 20, held_out: 5, general: 90, general_base: 92, reverted: true, revert_reason: ['recall did not improve (20% -> 20%, needs +1 held-out card)'], dreamcheck: { available: false, reason: "ModuleNotFoundError: No module named 'sleepmode'" } });
  assert.match(t, /Undone: recall did not improve/); assert.match(t, /Glim is as it was before the night/);
  assert.match(t, /Dream check: not available \(ModuleNotFoundError/);
  assert.strictEqual(nightLines(null), '');
});

test('a dry run (too few cards in the day) ends the night at once instead of reloading the model all night', async () => {
  const root = tmp('sm3-');
  const spawn = fakeSpawn([{ quiz: null, steps: 0, status: 'dry_run', message: 'only 3 trainable cards (need 12): cards written, no training tonight' }]);
  const ws = new WinSleep({ platform: 'darwin', getSettings: () => ({}), root, installer: installer(root), spawn, hooks: { resumeModel: async () => ({ ok: true }) } });
  ws.start(); await until(() => !ws.status().sleeping);
  assert.strictEqual(spawn.calls.length, 1);
  assert.match(ws.readSummary(), /Nothing new to learn yet.*only 3 trainable cards/);
});

test('wake: a model that does not start at all (memory, port) is not blamed on the adapter; a check that cannot run keeps it', async () => {
  const root = tmp('sm4-'); const home = path.join(root, 'sleep'); fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, 'adapter.gguf'), 'good');
  const tried = [];
  const ws = new WinSleep({ platform: 'darwin', getSettings: () => ({}), root, installer: installer(root), spawn: fakeSpawn([{ quiz: null, message: 'no new diary day to sleep on' }]),
    hooks: { resumeModel: async (l) => { tried.push(path.basename(l)); return { ok: false, error: 'out of memory' }; } } });
  ws.start(); await until(() => !ws.status().sleeping);
  assert.deepStrictEqual(tried, ['adapter.gguf', ''], 'straight to the plain model, not to the next adapter');
  assert.ok(fs.existsSync(path.join(home, 'adapter.gguf')), 'the adapter is kept'); assert.ok(!fs.existsSync(path.join(home, 'adapter.rejected.gguf')));
  const ws2 = new WinSleep({ platform: 'darwin', getSettings: () => ({}), root, installer: installer(root), spawn: fakeSpawn([{ quiz: null, message: 'no new diary day to sleep on' }]),
    servedCheck: async () => ({ ok: null, reasons: ['not checked: timeout'] }), hooks: { resumeModel: async () => ({ ok: true }), servedUrl: () => 'http://x' } });
  ws2.start(); await until(() => !ws2.status().sleeping);
  assert.strictEqual(ws2.loaded.lora, 'adapter.gguf'); assert.match(ws2.readSummary(), /its newest adapter \(adapter\.gguf\)\. Not checked in the model server \(not checked: timeout\)/);
  assert.ok(fs.existsSync(path.join(home, 'adapter.gguf')));
});

test('an adapter whose record says it scored worse is never loaded again (start-up, check-ins)', () => {
  const home = tmp('fit2-'); const p = path.join(home, 'adapter.prev.gguf');
  fs.writeFileSync(p, 'x'); fs.writeFileSync(p + '.json', JSON.stringify({ base_hf_id: LORA_BASE, served: { ok: false } }));
  assert.strictEqual(loraFits(p), false);
  assert.strictEqual(CK.checkinAdapter(home, fs.existsSync, (f) => loraFits(f)), '');
});

test('wake: when both adapters fail, both are set aside, the plain model runs, and the next app start does not pick the bad previous one', async () => {
  const root = tmp('sm5-'); const home = path.join(root, 'sleep'); fs.mkdirSync(home, { recursive: true });
  fs.writeFileSync(path.join(home, 'adapter.gguf'), 'worse'); fs.writeFileSync(path.join(home, 'adapter.prev.gguf'), 'corrupt');
  const tried = [];
  const ws = new WinSleep({ platform: 'darwin', getSettings: () => ({}), root, installer: installer(root), spawn: fakeSpawn([{ quiz: null, message: 'no new diary day to sleep on' }]),
    servedCheck: async () => ({ ok: false, reasons: ['general only 0/8'] }),
    hooks: { resumeModel: async (l) => { tried.push(path.basename(l)); return path.basename(l) === 'adapter.prev.gguf' ? { ok: false, loraFailed: true, error: 'bad file' } : { ok: true }; }, servedUrl: () => 'http://x' } });
  ws.start(); await until(() => !ws.status().sleeping);
  assert.deepStrictEqual(tried, ['adapter.gguf', 'adapter.prev.gguf', '']);
  assert.strictEqual(ws.loaded.lora, '');
  assert.ok(fs.existsSync(path.join(home, 'adapter.rejected.gguf'))); assert.ok(fs.existsSync(path.join(home, 'adapter.prev.rejected.gguf')));
  assert.strictEqual(ws.currentLora(), '');
  assert.match(ws.readSummary(), /Glim runs on the plain model/);
});
