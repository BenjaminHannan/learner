'use strict';
// Local speech to text (Mac): LiquidAI LFM3-Audio-2B through stt/lfm_stt.py, a tiny HTTP server on 127.0.0.1 that Desk starts on the
// first call / dictation and keeps for the app's lifetime. deskhelper gets its URL (`deskhelper call --stt http://127.0.0.1:N`).
// No Apple speech recognition and nothing leaves the Mac. Pure Node: spawn / exists / hasMlx are injected so the tests need no Python.
//
// Which Python (first one that can `import mlx_vlm` wins):
//   1. env PREMONITION_STT_PYTHON (+ PREMONITION_STT_HF_HOME)
//   2. ~/learner-ops/stt/.venv/bin/python with HF_HOME=~/learner-ops/stt/hf
//   3. the managed runtime python (sleep installer)
// TODO: install mlx-vlm and download the model through the managed runtime (like the sleep installer) instead of the error below.
// TODO (Windows): same server, with an ONNX / llama.cpp build of the model; the protocol is unchanged.
const fs = require('fs');
const path = require('path');
const os = require('os');
const { execFile, spawn: nodeSpawn } = require('child_process');

const START_MS = 30000;
const MISSING = 'Voice needs the local speech model (mlx-vlm and LFM3-Audio), which is not installed on this Mac yet. Install it, then try again.';

function scriptPath(resourcesPath, devRoot, exists) {
  exists = exists || fs.existsSync;
  const packaged = resourcesPath && path.join(resourcesPath, 'stt', 'lfm_stt.py');
  return packaged && exists(packaged) ? packaged : path.join(devRoot, 'stt', 'lfm_stt.py');
}

// [{python, hfHome}] in priority order
function candidates(o) {
  const env = o.env || process.env, home = o.home || os.homedir(), list = [];
  if (env.PREMONITION_STT_PYTHON) list.push({ python: env.PREMONITION_STT_PYTHON, hfHome: env.PREMONITION_STT_HF_HOME || '' });
  const root = path.join(home, 'learner-ops', 'stt');
  list.push({ python: path.join(root, '.venv', 'bin', 'python'), hfHome: path.join(root, 'hf') });
  const m = o.managedPython && o.managedPython();
  if (m) list.push({ python: m, hfHome: '' });
  return list;
}

function hasMlxReal(python, env) {
  return new Promise((resolve) => execFile(python, ['-I', '-c', 'import mlx_vlm'], { env, timeout: 30000 }, (err) => resolve(!err)));
}

class Stt {
  /** o: {resourcesPath, devRoot, home, env, managedPython(), spawn, exists, hasMlx(python, env)->Promise<bool>} */
  constructor(o) {
    this.o = o || {};
    this.exists = this.o.exists || fs.existsSync;
    this.spawn = this.o.spawn || ((cmd, args, opts) => nodeSpawn(cmd, args, opts));
    this.hasMlx = this.o.hasMlx || hasMlxReal;
    this.child = null; this.pending = null; this.url = null;
  }
  script() { return scriptPath(this.o.resourcesPath, this.o.devRoot || path.join(__dirname, '..'), this.exists); }

  async pick() {
    for (const c of candidates(this.o)) {
      if (!this.exists(c.python)) continue;
      const env = this._env(c);
      if (await this.hasMlx(c.python, env)) return { ...c, env };
    }
    return null;
  }
  _env(c) {
    const e = { ...(this.o.env || process.env), PYTHONUNBUFFERED: '1', PYTHONUTF8: '1', HF_HUB_DISABLE_TELEMETRY: '1' };
    if (c.hfHome) e.HF_HOME = c.hfHome;
    if (!e.PREMONITION_STT_ONLINE) e.HF_HUB_OFFLINE = '1'; // never download behind the user's back
    return e;
  }

  // Resolves to the server URL, starting it if needed; rejects with an Error whose message is shown to the user as is.
  ensure() {
    if (this.url && this.child) return Promise.resolve(this.url);
    if (!this.pending) this.pending = this._start().finally(() => { this.pending = null; });
    return this.pending;
  }

  async _start() {
    const script = this.script();
    if (!this.exists(script)) throw new Error('Voice needs the speech helper script, which is missing from this build.');
    const pick = await this.pick();
    if (!pick) throw new Error(MISSING);
    return new Promise((resolve, reject) => {
      let c, buf = '', err = '', done = false;
      const finish = (fn, v) => { if (done) return; done = true; clearTimeout(t); fn(v); };
      try { c = this.spawn(pick.python, ['-I', script], { env: pick.env, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true }); }
      catch (e) { return reject(new Error('Voice could not start the speech model.')); }
      const t = setTimeout(() => { try { c.kill(); } catch (e) { /* gone */ } finish(reject, new Error('The speech model did not start in time.')); }, this.o.startMs || START_MS);
      c.stdout.on('data', (d) => {
        buf += String(d);
        let i;
        while ((i = buf.indexOf('\n')) >= 0) {
          const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
          let j; try { j = JSON.parse(line); } catch (e) { continue; }
          if (j && Number.isInteger(j.port) && j.port > 0) { this.child = c; this.url = 'http://127.0.0.1:' + j.port; finish(resolve, this.url); }
        }
      });
      if (c.stderr) c.stderr.on('data', (d) => { err = (err + String(d)).slice(-400); });
      if (c.stdin && c.stdin.on) c.stdin.on('error', () => { /* server gone */ });
      c.on('error', () => finish(reject, new Error('Voice could not start the speech model.')));
      c.on('exit', () => {
        if (this.child === c) { this.child = null; this.url = null; } // next ensure() starts a fresh one
        finish(reject, new Error('The speech model stopped before it was ready.' + (err ? ' ' + err.trim().split('\n').pop() : '')));
      });
    });
  }

  // fire and forget: load the model now so the first sentence is not slow
  warm() {
    const url = this.url; if (!url) return;
    try { const http = require('http'); const r = http.request(url + '/warm', { method: 'POST' }, (res) => res.resume()); r.on('error', () => {}); r.end(); } catch (e) { /* best effort */ }
  }

  stop() {
    const c = this.child; this.child = null; this.url = null;
    if (!c) return;
    try { c.stdin && c.stdin.end && c.stdin.end(); } catch (e) { /* closed */ }
    try { c.kill(); } catch (e) { /* gone */ }
  }
}

module.exports = { Stt, scriptPath, candidates, MISSING };
