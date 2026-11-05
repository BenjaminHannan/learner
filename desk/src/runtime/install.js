'use strict';
// First-run download of the chat runtime: a llama.cpp build for Windows and the LFM3 GGUF. Resumable, checksummed where the
// server tells us the hash, and idempotent (a finished install is detected from disk and costs no network).
const fs = require('fs');
const path = require('path');
const { execFile } = require('child_process');
const C = require('./constants');
const R = require('./releases');
const { downloadFile, getJson } = require('./download');

function findFile(dir, name) {
  let hit = null;
  const walk = (d, depth) => {
    if (hit || depth > 4) return;
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      if (e.isFile() && e.name.toLowerCase() === name.toLowerCase()) { hit = path.join(d, e.name); return; }
      if (e.isDirectory()) walk(path.join(d, e.name), depth + 1);
    }
  };
  try { walk(dir, 0); } catch (e) { /* missing */ }
  return hit;
}
// Windows 10+ ships bsdtar as tar.exe, which reads .zip and .tar.gz
// the Windows system tar (bsdtar): a tar.exe from Git or MSYS earlier on PATH may not read zip files
// macOS: /usr/bin/tar (bsdtar) reads the .tar.gz release; the full path avoids a different tar from Homebrew or the PATH
const tarExe = (platform) => { const p = platform || process.platform; return p === 'win32' ? path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'tar.exe') : (p === 'darwin' ? '/usr/bin/tar' : 'tar'); };
const tarArgs = (archive, dest) => ['-xf', archive, '-C', dest];
const defaultExtract = (archive, dest) => new Promise((resolve, reject) => {
  fs.mkdirSync(dest, { recursive: true });
  execFile(tarExe(), tarArgs(archive, dest), { windowsHide: true }, (err, so, se) => (err ? reject(new Error('could not unpack ' + path.basename(archive) + ': ' + (se || err.message))) : resolve()));
});

// macOS: the unpacked folder must be runnable. A download made by Node carries no com.apple.quarantine, but strip it anyway
// (belt and braces) and make sure the binary is executable. Best effort: a failure here shows up later as a start error.
const defaultUnquarantine = (dir, exe) => new Promise((resolve) => {
  try { fs.chmodSync(exe, 0o755); } catch (e) { /* tar already set it */ }
  execFile('/usr/bin/xattr', ['-dr', 'com.apple.quarantine', dir], () => resolve());
});

class ChatInstaller {
  /** o: {dir (…/runtime), fetch, extract, onProgress({stage,label,done,total}), apiBase} */
  constructor(o) { this.o = o; this.f = o.fetch || fetch; this.extract = o.extract || defaultExtract; this.platform = o.platform || process.platform; this.unquarantine = o.unquarantine || defaultUnquarantine; this.stateFile = path.join(o.dir, 'state.json'); }
  state() { try { return JSON.parse(fs.readFileSync(this.stateFile, 'utf8')); } catch (e) { return {}; } }
  _save(patch) { const s = { ...this.state(), ...patch }; fs.mkdirSync(this.o.dir, { recursive: true }); fs.writeFileSync(this.stateFile, JSON.stringify(s, null, 2)); return s; }
  _prog(stage, label) { return (p) => { if (this.o.onProgress) this.o.onProgress({ stage, label, done: p.done, total: p.total }); }; }

  llamaExe(flavor) {
    const s = this.state(); const d = s.llama && s.llama[flavor];
    if (d && d.exe && fs.existsSync(d.exe)) return d;
    // the CPU engine shipped inside the app (no download needed)
    if (flavor === 'cpu' && this.o.bundledExe && fs.existsSync(this.o.bundledExe)) return { tag: C.BUNDLED_LLAMA_COMMIT, flavor: 'cpu', exe: this.o.bundledExe, bundled: true };
    return null;
  }
  async ensureLlama(flavor, signal) {
    const mac = this.platform === 'darwin';
    flavor = flavor || (mac ? 'metal' : 'vulkan');
    const have = this.llamaExe(flavor);
    if (have) return have;
    // The release list picks the newest build. If GitHub will not give it (rate limit, network, nothing usable), download the pinned one.
    const url = 'https://api.github.com/repos/' + C.LLAMA_REPO + '/releases?per_page=30';
    let rel = null; let why = '';
    const sleep = (ms) => new Promise((resolve, reject) => {
      const t = setTimeout(resolve, ms);
      if (signal) signal.addEventListener('abort', () => { clearTimeout(t); reject(new Error('cancelled')); }, { once: true });
    });
    for (let attempt = 0; attempt < 2 && !Array.isArray(rel); attempt++) {
      if (signal && signal.aborted) throw new Error('cancelled');
      if (attempt) await sleep(this.o.retryDelayMs == null ? 1500 : this.o.retryDelayMs);
      why = '';
      try { rel = await getJson(url, this.f, null, signal); if (!Array.isArray(rel)) why = (rel && rel.message) || 'unexpected reply from GitHub'; } catch (e) { if (signal && signal.aborted) throw e; why = e.message; }
    }
    let a = R.pickLlamaAsset(rel, { flavor, platform: this.platform });
    const pinned = !a;
    if (pinned) {
      const name = C.llamaAssetName(C.LLAMA_FALLBACK_TAG, flavor, this.platform);
      a = { tag: C.LLAMA_FALLBACK_TAG, name, url: 'https://github.com/' + C.LLAMA_REPO + '/releases/download/' + C.LLAMA_FALLBACK_TAG + '/' + name, sha256: (this.o.fallbackSha256 || C.LLAMA_FALLBACK_SHA256)[name] || null };
    }
    const friendly = (e) => new Error('Could not download the model engine from GitHub (' + (why ? why + '; then ' : '') + e.message + '). Check the internet connection and press Try again.');
    const zip = path.join(this.o.dir, a.name);
    const dest = path.join(this.o.dir, 'llama-' + a.tag + '-' + flavor);
    try {
      await downloadFile({ url: a.url, dest: zip, sha256: a.sha256, fetch: this.f, signal, onProgress: this._prog('llama', 'Downloading the model engine') });
      if (pinned && fs.statSync(zip).size < (this.o.minEngineBytes == null ? 1048576 : this.o.minEngineBytes)) throw new Error('the file is too small to be the engine');
    } catch (e) {
      if (pinned) try { fs.rmSync(zip, { force: true }); } catch (e2) { /* keep */ }
      if (!pinned || (signal && signal.aborted)) throw e;
      throw friendly(e);
    }
    fs.rmSync(dest, { recursive: true, force: true });
    if (this.o.onProgress) this.o.onProgress({ stage: 'llama', label: 'Unpacking the model engine', done: 0, total: 0 });
    try { await this.extract(zip, dest); } catch (e) {
      try { fs.rmSync(zip, { force: true }); fs.rmSync(dest, { recursive: true, force: true }); } catch (e2) { /* keep */ }
      if (!pinned) throw e;
      throw friendly(e);
    }
    const exeName = C.llamaExeName(this.platform);
    const exe = findFile(dest, exeName);
    if (!exe) throw new Error(exeName + ' was not inside ' + a.name);
    if (mac) await this.unquarantine(dest, exe);
    try { fs.rmSync(zip, { force: true }); } catch (e) { /* keep */ }
    const cur = this.state();
    this._save({ llama: { ...(cur.llama || {}), [flavor]: { tag: a.tag, flavor, exe } } });
    return { tag: a.tag, flavor, exe };
  }
  // Turn on pressed twice while the download runs must share one download: two writers appended to the same .part and corrupted it.
  ensureModel(signal) {
    if (!this._modelJob) this._modelJob = this._ensureModel(signal).finally(() => { this._modelJob = null; });
    return this._modelJob;
  }
  async _ensureModel(signal) {
    if (this.platform === 'win32') return this._ensureWinModel(signal);
    const s = this.state();
    if (s.model && s.model.file && fs.existsSync(s.model.file)) return s.model;
    const files = await getJson(R.hfTreeUrl(C.MODEL_REPO), this.f);
    const pick = R.pickGguf(files, C.MODEL_FILE);
    if (!pick) throw new Error('No q4_0 .gguf was found in ' + C.MODEL_REPO + '.');
    const dest = path.join(this.o.dir, 'models', path.basename(pick.path));
    await downloadFile({ url: R.hfResolveUrl(C.MODEL_REPO, pick.path), dest, sha256: pick.sha256, fetch: this.f, signal, onProgress: this._prog('model', 'Downloading the language model') });
    const m = { file: dest, name: pick.path, sha256: pick.sha256 };
    this._save({ model: m });
    return m;
  }
  // Windows: Nanbeige4.2-3B, Q8_0 on a graphics card with >= 12 GB, else Q4_K_M (detected once, then kept in state.json so a
  // later driver hiccup cannot swap the brain). An older install of another model (LFM3) is replaced, and its file removed.
  async _ensureWinModel(signal) {
    const s = this.state(); const models = this.o.winModels || C.WIN_MODELS;
    let quant = s.model && s.model.family === 'nanbeige' && models[s.model.quant] ? s.model.quant : '';
    let vram = s.vram || null;
    if (!quant) {
      vram = await (this.o.detectVram || require('./gpu').detectVram)({ platform: this.platform });
      quant = require('./gpu').quantFor(vram.bytes);
    }
    const want = models[quant];
    const dir = path.join(this.o.dir, 'models');
    const dest = path.join(dir, want.file);
    const template = this._writeTemplate();
    if (s.model && s.model.file === dest && s.model.quant === quant && fs.existsSync(dest)) return { ...s.model, template };
    await downloadFile({ url: R.hfResolveUrl(C.WIN_MODEL_REPO, want.file), dest, sha256: want.sha256, fetch: this.f, signal, onProgress: this._prog('model', 'Downloading Glim\'s brain') });
    if (s.model && s.model.file && s.model.file !== dest && path.dirname(s.model.file) === dir) { try { fs.rmSync(s.model.file, { force: true }); } catch (e) { /* keep */ } }
    const m = { file: dest, name: want.file, sha256: want.sha256, family: 'nanbeige', quant };
    this._save({ model: m, vram: vram && { bytes: vram.bytes, source: vram.source } });
    return { ...m, template };
  }
  // llama-server cannot read inside app.asar: copy Glim's chat template next to the models (same text = no rewrite)
  _writeTemplate() {
    try {
      const src = this.o.templateSrc || path.join(__dirname, '..', '..', 'assets', C.WIN_CHAT_TEMPLATE);
      const text = fs.readFileSync(src, 'utf8');
      const out = path.join(this.o.dir, C.WIN_CHAT_TEMPLATE);
      let cur = null; try { cur = fs.readFileSync(out, 'utf8'); } catch (e) { /* new */ }
      if (cur !== text) { fs.mkdirSync(this.o.dir, { recursive: true }); fs.writeFileSync(out, text); }
      return out;
    } catch (e) { return ''; }   // no template file: llama-server uses the GGUF's own (one rstrip different)
  }
  installed(flavor) { const s = this.state(); return !!(this.llamaExe(flavor || C.llamaFlavors(this.platform)[0]) && s.model && fs.existsSync(s.model.file)); }
}

module.exports = { ChatInstaller, findFile, defaultExtract, tarExe, tarArgs };
