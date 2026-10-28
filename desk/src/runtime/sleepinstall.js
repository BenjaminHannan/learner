'use strict';
// The sleep runtime, downloaded the first time sleep is turned on: a portable Python (python-build-standalone), PyTorch (CPU build on
// Windows; the default macOS wheel, which trains on the Apple GPU through MPS) +
// transformers + peft, llama.cpp's convert_lora_to_gguf.py (from the llama.cpp source of the same tag as the engine) and the
// LFM3 weights from Hugging Face. About 4.5 GB in all. Every external action goes through injected functions so it is testable.
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const C = require('./constants');
const R = require('./releases');
const { downloadFile, getJson } = require('./download');
const { findFile, defaultExtract } = require('./install');

const defaultRun = (cmd, args, opts) => new Promise((resolve, reject) => {
  execFile(cmd, args, { windowsHide: true, maxBuffer: 16 * 1024 * 1024, env: { ...process.env, ...((opts && opts.env) || {}) }, cwd: opts && opts.cwd }, (err, so, se) => (err ? reject(new Error(path.basename(cmd) + ' ' + args.slice(0, 3).join(' ') + ' failed: ' + String(se || so || err.message).trim().split('\n').slice(-3).join(' | '))) : resolve(String(so))));
});

// ---- pure builders (tested) ----------------------------------------------------------------------------------------
const pipTorchArgs = (platform) => (platform === 'darwin' ? ['-m', 'pip', 'install', '--no-warn-script-location', 'torch']
  : ['-m', 'pip', 'install', '--no-warn-script-location', '--index-url', C.TORCH_CPU_INDEX, '--extra-index-url', 'https://pypi.org/simple', 'torch']);
// the portable Python's interpreter inside the unpacked "python" folder
const pythonPath = (dir, platform) => (platform === 'win32' ? path.join(dir, 'python', 'python.exe') : path.join(dir, 'python', 'bin', 'python3'));
const pipLibsArgs = () => ['-m', 'pip', 'install', '--no-warn-script-location'].concat(C.SLEEP_PIP);
const pipGgufArgs = (ggufPyDir) => ['-m', 'pip', 'install', '--no-warn-script-location', ggufPyDir];
const snapshotArgs = (dest) => ['-c', 'from huggingface_hub import snapshot_download; print(snapshot_download(' + JSON.stringify(C.SLEEP_HF_REPO) + ', cache_dir=' + JSON.stringify(dest) + '))'];
const planText = () => 'To sleep on this computer Premonition needs to download a few things once: a small private copy of Python (about ' + C.SLEEP_SIZES.python + '), the learning libraries (about ' + C.SLEEP_SIZES.libs + ') and the language model\'s full-size weights (about ' + C.SLEEP_SIZES.weights + '). That is roughly 4.5 GB. They stay on this computer.';

const dirSize = (d) => { let n = 0; try { for (const e of fs.readdirSync(d, { withFileTypes: true })) { const p = path.join(d, e.name); try { n += e.isDirectory() ? dirSize(p) : fs.statSync(p).size; } catch (x) { /* gone */ } } } catch (e) { /* missing */ } return n; };

class SleepInstaller {
  /** o: {root, platform, fetch, run, extract, onProgress({stage,label,pct}), llamaTag(): the engine's tag, weightsBytes} */
  constructor(o) { this.o = o; this.platform = o.platform || process.platform; this.dir = path.join(o.root, 'sleep-runtime'); this.f = o.fetch || fetch; this.run = o.run || defaultRun; this.extract = o.extract || defaultExtract; this.stateFile = path.join(this.dir, 'state.json'); }
  state() { try { return JSON.parse(fs.readFileSync(this.stateFile, 'utf8')); } catch (e) { return {}; } }
  _save(p) { fs.mkdirSync(this.dir, { recursive: true }); fs.writeFileSync(this.stateFile, JSON.stringify({ ...this.state(), ...p }, null, 2)); }
  _p(stage, label, pct) { if (this.o.onProgress) this.o.onProgress({ stage, label, pct: pct == null ? 0 : pct }); }
  pythonExe() { return pythonPath(this.dir, this.platform); }
  installed() { const s = this.state(); return !!(s.done && s.hfDir && fs.existsSync(this.pythonExe()) && s.convert && fs.existsSync(s.convert)); }
  plan() { return { sizes: C.SLEEP_SIZES, text: planText(), installed: this.installed() }; }

  async install(signal) {
    fs.mkdirSync(this.dir, { recursive: true });
    const st = this.state();
    // 1. portable Python
    if (!fs.existsSync(this.pythonExe())) {
      this._p('python', 'Downloading Python', 0);
      const rel = await getJson('https://api.github.com/repos/' + C.PBS_REPO + '/releases?per_page=6', this.f);
      const a = R.pickPython(rel, null, this.platform);
      if (!a) throw new Error('No portable Python for ' + (this.platform === 'darwin' ? 'this Mac' : 'Windows') + ' was found in ' + C.PBS_REPO + '.');
      const arc = path.join(this.dir, a.name);
      await downloadFile({ url: a.url, dest: arc, sha256: a.sha256, fetch: this.f, signal, onProgress: (p) => this._p('python', 'Downloading Python', p.total ? Math.round((p.done / p.total) * 100) : 0) });
      this._p('python', 'Unpacking Python', 0);
      await this.extract(arc, this.dir);
      try { fs.rmSync(arc, { force: true }); } catch (e) { /* keep */ }
      if (!fs.existsSync(this.pythonExe())) throw new Error(path.basename(this.pythonExe()) + ' was not inside ' + a.name);
      if (this.platform === 'darwin') { try { fs.chmodSync(this.pythonExe(), 0o755); } catch (e) { /* tar kept the mode */ } }
    }
    const py = this.pythonExe();
    // 2. libraries (pip prints its own progress; we show a busy bar)
    if (!st.libs) {
      this._p('libs', this.platform === 'darwin' ? 'Installing PyTorch' : 'Installing PyTorch (CPU)', 0);
      await this.run(py, pipTorchArgs(this.platform));
      this._p('libs', 'Installing the learning libraries', 50);
      await this.run(py, pipLibsArgs());
      this._save({ libs: true });
    }
    // 3. llama.cpp's converter, from the source of the same tag as the engine
    if (!this.state().convert || !fs.existsSync(this.state().convert)) {
      const tag = (this.o.llamaTag && this.o.llamaTag()) || null;
      if (!tag) throw new Error('The model engine must be installed first (no llama.cpp tag known).');
      this._p('convert', 'Downloading the adapter converter', 0);
      const zip = path.join(this.dir, 'llama-src-' + tag + '.zip');
      await downloadFile({ url: R.llamaSourceUrl(tag), dest: zip, fetch: this.f, signal });
      const src = path.join(this.dir, 'llama-src');
      fs.rmSync(src, { recursive: true, force: true });
      await this.extract(zip, src);
      try { fs.rmSync(zip, { force: true }); } catch (e) { /* keep */ }
      const conv = findFile(src, 'convert_lora_to_gguf.py');
      if (!conv) throw new Error('convert_lora_to_gguf.py was not in the llama.cpp source ' + tag);
      const ggufPy = path.join(path.dirname(conv), 'gguf-py');
      if (fs.existsSync(ggufPy)) await this.run(py, pipGgufArgs(ggufPy)); else await this.run(py, ['-m', 'pip', 'install', '--no-warn-script-location', 'gguf']);
      this._save({ convert: conv, llamaTag: tag });
    }
    // 4. LFM3 weights
    if (!this.state().hfDir || !fs.existsSync(this.state().hfDir)) {
      const cache = path.join(this.dir, 'hf');
      const total = this.o.weightsBytes || 3.4e9;
      const t = setInterval(() => this._p('weights', 'Downloading the language model weights', Math.min(99, Math.round((dirSize(cache) / total) * 100))), 2000);
      if (t.unref) t.unref();
      try {
        const out = await this.run(py, snapshotArgs(cache), { env: { HF_HOME: cache, HF_HUB_DISABLE_TELEMETRY: '1' } });
        const dir = out.trim().split('\n').pop().trim();
        this._save({ hfDir: dir });
      } finally { clearInterval(t); }
    }
    this._save({ done: true });
    this._p('done', 'Ready', 100);
    return this.state();
  }
}

module.exports = { defaultRun, SleepInstaller, pipTorchArgs, pythonPath, pipLibsArgs, pipGgufArgs, snapshotArgs, planText, dirSize };
