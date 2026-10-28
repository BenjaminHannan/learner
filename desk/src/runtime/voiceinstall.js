'use strict';
// "Get voice": the local speech model (mlx-vlm + LFM3-Audio) for Macs without ~/learner-ops/stt. Lives in <userData>/voice:
//   python/   portable Python (same python-build-standalone download as the sleep runtime)
//   .venv/    mlx-vlm pinned to the commit Ben's own stt venv uses, plus its helpers
//   hf/       HF_HOME with the one model repo (about 1.6 GB)
//   state.json
// Idempotent and resumable: finished steps are skipped, downloads continue. Everything external is injected for the tests.
const fs = require('fs');
const path = require('path');
const C = require('./constants');
const R = require('./releases');
const { downloadFile, getJson } = require('./download');
const { defaultExtract } = require('./install');
const { defaultRun, pythonPath, dirSize } = require('./sleepinstall');

const VOICE = {
  repo: 'LiquidAI/LFM3-Audio-2B-MLX-4bit',
  // mlx-vlm 0.7.11 from git main, the exact commit of ~/learner-ops/stt/.venv. A zip of the commit: friends have no git.
  mlxVlmCommit: '230fc308efb577d87446306bfb8a3e9f1a129558',
  pins: ['mlx==0.32.4', 'transformers==5.21.0', 'huggingface_hub==2.3.0', 'numpy', 'soundfile'],
  needBytes: 3e9, modelBytes: 1.6e9
};
VOICE.mlxVlmUrl = 'https://github.com/Blaizzy/mlx-vlm/archive/' + VOICE.mlxVlmCommit + '.zip';

const GB = (n) => (n / 1e9).toFixed(1) + ' GB';
const venvArgs = (venv) => ['-m', 'venv', venv];
const pipArgs = () => ['-m', 'pip', 'install', '--no-warn-script-location', '--disable-pip-version-check', VOICE.mlxVlmUrl].concat(VOICE.pins);
const checkArgs = () => ['-I', '-c', 'import mlx_vlm, soundfile, numpy'];
const snapshotArgs = () => ['-c', 'from huggingface_hub import snapshot_download; print(snapshot_download(' + JSON.stringify(VOICE.repo) + '))'];
// the model download is the only thing allowed online; HF_HOME keeps it inside the voice folder
const snapshotEnv = (hf) => ({ HF_HOME: hf, HF_HUB_OFFLINE: '0', HF_HUB_DISABLE_TELEMETRY: '1', PYTHONUTF8: '1' });
const venvPython = (dir) => path.join(dir, '.venv', 'bin', 'python');

function freeBytes(dir) {
  let d = dir;
  for (let i = 0; i < 8 && !fs.existsSync(d); i++) d = path.dirname(d);
  try { const s = fs.statfsSync(d); return Number(s.bavail) * Number(s.bsize); } catch (e) { return null; }
}

class VoiceInstaller {
  /** o: {dir (<userData>/voice), platform, arch, fetch, run, extract, free(dir)->bytes|null, onProgress({stage,label,pct})} */
  constructor(o) {
    this.o = o; this.dir = o.dir; this.platform = o.platform || process.platform; this.arch = o.arch || process.arch;
    this.f = o.fetch || fetch; this.run = o.run || defaultRun; this.extract = o.extract || defaultExtract; this.free = o.free || freeBytes;
    this.stateFile = path.join(this.dir, 'state.json'); this.busy = null;
  }
  state() { try { return JSON.parse(fs.readFileSync(this.stateFile, 'utf8')); } catch (e) { return {}; } }
  _save(p) { fs.mkdirSync(this.dir, { recursive: true }); fs.writeFileSync(this.stateFile, JSON.stringify({ ...this.state(), ...p }, null, 2)); }
  _p(stage, label, pct) { if (this.o.onProgress) this.o.onProgress({ stage, label, pct: pct == null ? 0 : pct }); }
  pythonExe() { return venvPython(this.dir); }
  installed() { return !!(this.state().done && fs.existsSync(this.pythonExe())); }

  // Throws a plain-English Error when there is not enough room. Already-finished installs need nothing.
  checkDisk() {
    const st = this.state();
    const need = st.libs ? (st.model ? 0 : VOICE.modelBytes) : VOICE.needBytes;
    if (!need) return;
    const free = this.free(this.dir);
    if (free != null && free < need) throw new Error('Not enough free space for the speech model: it needs about ' + GB(VOICE.needBytes) + ' and this Mac has ' + GB(free) + ' free. Free up some space and try again.');
  }

  install(signal) { return this.busy || (this.busy = this._install(signal).finally(() => { this.busy = null; })); }

  async _install(signal) {
    if (this.platform !== 'darwin' || this.arch !== 'arm64') throw new Error('Voice needs a Mac with Apple silicon (M1 or later).');
    this.checkDisk();
    fs.mkdirSync(this.dir, { recursive: true });
    const base = pythonPath(this.dir, this.platform), py = this.pythonExe(), hf = path.join(this.dir, 'hf');
    // 1. portable Python (same download as the sleep runtime)
    if (!this.state().libs && !fs.existsSync(base)) {
      this._p('python', 'Downloading Python', 0);
      const rel = await getJson('https://api.github.com/repos/' + C.PBS_REPO + '/releases?per_page=6', this.f);
      const a = R.pickPython(rel, null, this.platform);
      if (!a) throw new Error('No portable Python for this Mac was found.');
      const arc = path.join(this.dir, a.name);
      await downloadFile({ url: a.url, dest: arc, sha256: a.sha256, fetch: this.f, signal, onProgress: (p) => this._p('python', 'Downloading Python', p.total ? Math.round((p.done / p.total) * 100) : 0) });
      this._p('python', 'Unpacking Python', 0);
      await this.extract(arc, this.dir);
      try { fs.rmSync(arc, { force: true }); } catch (e) { /* keep */ }
      if (!fs.existsSync(base)) throw new Error('Python was not inside ' + a.name);
      try { fs.chmodSync(base, 0o755); } catch (e) { /* tar kept the mode */ }
    }
    // 2. venv + mlx-vlm (a half-made venv is rebuilt)
    if (!this.state().libs) {
      this._p('libs', 'Setting up the speech engine', 10);
      fs.rmSync(path.join(this.dir, '.venv'), { recursive: true, force: true });
      await this.run(base, venvArgs(path.join(this.dir, '.venv')));
      this._p('libs', 'Installing the speech engine', 30);
      await this.run(py, pipArgs());
      await this.run(py, checkArgs());
      this._save({ libs: true });
    }
    // 3. the model: one repo, online only for this call
    if (!this.state().model) {
      const total = this.o.modelBytes || VOICE.modelBytes;
      const t = setInterval(() => this._p('model', 'Downloading the speech model', Math.min(99, Math.round((dirSize(hf) / total) * 100))), 2000);
      if (t.unref) t.unref();
      try { const out = await this.run(py, snapshotArgs(), { env: snapshotEnv(hf) }); this._save({ model: out.trim().split('\n').pop().trim() }); } finally { clearInterval(t); }
    }
    this._save({ done: true });
    this._p('done', 'Voice is ready', 100);
    return this.state();
  }
}

module.exports = { VoiceInstaller, VOICE, venvArgs, pipArgs, checkArgs, snapshotArgs, snapshotEnv, venvPython, freeBytes, GB };
