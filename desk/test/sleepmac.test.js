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
const { pipTorchArgs, pythonPath, SleepInstaller } = require('../src/runtime/sleepinstall');
const { WinSleep, workerCommand, sleepProfile, nightLines, loadedLine } = require('../src/sleepwin');

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
  const ws = new WinSleep({ platform: 'darwin', getSettings: () => ({}), root, installer: installer(root), spawn, privateChecker: { ensureIdle: async () => ({ ok: true, processStopped: true }) }, hooks: { resumeModel: async () => ({ ok: true }) } });
  ws.start(); await until(() => !ws.status().sleeping);
  assert.strictEqual(spawn.calls.length, 1);
  assert.match(ws.readSummary(), /Nothing new to learn yet.*only 3 trainable cards/);
});



test('blocked worker stops after one chunk and reports the manual re-check', async () => {
  const root = tmp('mac-blocked-');
  const spawn = fakeSpawn([{ blocked: true, interrupted: true, message: 'A previous finalization needs a manual re-gate.' }]);
  const resumed = [];
  const ws = new WinSleep({ platform: 'darwin', getSettings: () => ({}), root, installer: installer(root), spawn,
    privateChecker: { ensureIdle: async () => ({ ok: true, processStopped: true }) },
    hooks: { resumeModel: async (lora) => { resumed.push(lora); return { ok: true }; } } });
  assert.equal(ws.start().ok, true); await until(() => !ws.status().sleeping);
  assert.equal(spawn.calls.length, 1); assert.deepEqual(resumed, ['']);
  assert.match(ws.readSummary(), /Sleep stopped early: A previous finalization needs a manual re-gate/);
});
