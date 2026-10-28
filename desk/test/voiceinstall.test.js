'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Stt, candidates } = require('../src/stt');
const { VoiceInstaller, VOICE, pipArgs, venvArgs, snapshotArgs, snapshotEnv } = require('../src/runtime/voiceinstall');

test('voice: candidate order puts <userData>/voice after learner-ops and before the managed python', () => {
  const vd = fs.mkdtempSync(path.join(os.tmpdir(), 'vd-'));
  const c0 = candidates({ home: '/h', env: {}, voiceDir: vd, managedPython: () => '/m/py' });
  assert.deepStrictEqual(c0.map((x) => x.python), ['/h/learner-ops/stt/.venv/bin/python', '/m/py']); // not finished: skipped
  fs.writeFileSync(path.join(vd, 'state.json'), JSON.stringify({ libs: true, model: 'x', done: true }));
  const c = candidates({ home: '/h', env: { PREMONITION_STT_PYTHON: '/p/py' }, voiceDir: vd, managedPython: () => '/m/py' });
  assert.deepStrictEqual(c.map((x) => x.python), ['/p/py', '/h/learner-ops/stt/.venv/bin/python', path.join(vd, '.venv/bin/python'), '/m/py']);
  assert.strictEqual(c[2].hfHome, path.join(vd, 'hf'));
});

test('voice: MISSING error carries needsVoice; other errors do not', async () => {
  const stt = new Stt({ home: '/h', devRoot: '/r', env: {}, exists: () => true, hasMlx: async () => false });
  await assert.rejects(stt.ensure(), (e) => e.needsVoice === true && /local speech model/.test(e.message));
  const noScript = new Stt({ home: '/h', devRoot: '/r', env: {}, exists: () => false, hasMlx: async () => false });
  await assert.rejects(noScript.ensure(), (e) => !e.needsVoice);
});

test('voice: command lines pin mlx-vlm to the commit zip, no git, one model repo, online only for the download', () => {
  assert.deepStrictEqual(venvArgs('/v/.venv'), ['-m', 'venv', '/v/.venv']);
  const a = pipArgs();
  assert.ok(a.includes('https://github.com/Blaizzy/mlx-vlm/archive/230fc308efb577d87446306bfb8a3e9f1a129558.zip'));
  assert.ok(a.includes('soundfile') && a.includes('numpy') && !a.some((x) => /^git\+/.test(x)));
  assert.match(snapshotArgs()[1], /snapshot_download\("LiquidAI\/LFM3-Audio-2B-MLX-4bit"\)/);
  const e = snapshotEnv('/v/hf');
  assert.strictEqual(e.HF_HOME, '/v/hf'); assert.strictEqual(e.HF_HUB_OFFLINE, '0');
});

function mk(o = {}) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'voice-')), runs = [], prog = [];
  const inst = new VoiceInstaller({
    dir, platform: 'darwin', arch: 'arm64', free: () => 50e9, onProgress: (p) => prog.push(p),
    fetch: async (url) => {
      if (/api.github.com/.test(url)) return { ok: true, json: async () => [{ tag_name: 't', published_at: '2026-01-01T00:00:00Z', assets: [{ name: 'cpython-3.12.5+20260101-aarch64-apple-darwin-install_only.tar.gz', browser_download_url: 'https://x/py.tgz', size: 3 }] }] };
      return { ok: true, status: 200, headers: { get: () => '3' }, body: { getReader: () => { let d = false; return { read: async () => (d ? { done: true } : (d = true, { value: Buffer.from('abc') })) }; } } };
    },
    extract: async (arc, dest) => { fs.mkdirSync(path.join(dest, 'python', 'bin'), { recursive: true }); fs.writeFileSync(path.join(dest, 'python', 'bin', 'python3'), ''); },
    run: async (cmd, args, opts) => { runs.push({ cmd, args, opts }); if (args[0] === '-m' && args[1] === 'venv') { fs.mkdirSync(path.join(args[2], 'bin'), { recursive: true }); fs.writeFileSync(path.join(args[2], 'bin', 'python'), ''); } return '/v/hf/hub/models--x/snapshots/abc\n'; },
    ...o
  });
  return { inst, dir, runs, prog };
}

test('voice: refuses with the free space in plain words when under 3 GB', async () => {
  const { inst, runs } = mk({ free: () => 1.3e9 });
  await assert.rejects(inst.install(), /about 3\.0 GB.*1\.3 GB free/);
  assert.strictEqual(runs.length, 0);
});

test('voice: refuses Intel Macs', async () => {
  const { inst } = mk({ arch: 'x64' });
  await assert.rejects(inst.install(), /Apple silicon/);
});

test('voice: full install runs venv, pip, import check, snapshot; second call is a no-op', async () => {
  const { inst, dir, runs, prog } = mk();
  await inst.install();
  assert.deepStrictEqual(runs.map((r) => r.args.slice(0, 2)), [['-m', 'venv'], ['-m', 'pip'], ['-I', '-c'], ['-c', 'from huggingface_hub import snapshot_download; print(snapshot_download("LiquidAI/LFM3-Audio-2B-MLX-4bit"))']]);
  assert.strictEqual(runs[0].cmd, path.join(dir, 'python', 'bin', 'python3'));
  assert.strictEqual(runs[1].cmd, path.join(dir, '.venv', 'bin', 'python'));
  assert.strictEqual(runs[3].opts.env.HF_HUB_OFFLINE, '0');
  assert.strictEqual(prog[prog.length - 1].stage, 'done');
  assert.ok(prog.some((p) => p.stage === 'python') && prog.every((p) => typeof p.label === 'string' && typeof p.pct === 'number'));
  const n = runs.length;
  await inst.install();
  assert.strictEqual(runs.length, n);
});

test('voice: resumes after a failed model download without redoing pip, and rechecks only the model size', async () => {
  let fail = true, free = 50e9;
  const { inst, runs } = mk({ free: () => free, run: async (cmd, args) => { runs.push(args[0]); if (args[1] === 'venv') { fs.mkdirSync(path.join(args[2], 'bin'), { recursive: true }); fs.writeFileSync(path.join(args[2], 'bin', 'python'), ''); } if (args[0] === '-c' && fail) { fail = false; throw new Error('network down'); } return 'x\n'; } });
  await assert.rejects(inst.install(), /network down/);
  assert.ok(inst.state().libs && !inst.state().model);
  const before = runs.length; free = 3e9; // 3 GB is enough for the 1.6 GB left
  await inst.install();
  assert.deepStrictEqual(runs.slice(before), ['-c']);
  assert.strictEqual(inst.state().done, true);
});
