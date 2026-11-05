'use strict';
// Glim's side server (ONE-GLIM, 2026-11-05): on a Mac where the assistant runs as one process named "Glim"
// (~/learner-ops/assistant/glim/glim_main.py), speech-to-text and the diary live inside it on 127.0.0.1:18083:
//   GET /glim -> {"name": "Glim", "pid": N, "parts": {"stt": true, "diary": true, ...}}
//   POST /transcribe, /warm, GET /health  = the same API as stt/lfm_stt.py
//   POST /diary  = one MCP JSON-RPC message in, its reply out (diary_mcp.py's handler)
//   POST /eyes   = the eyes worker (tools/glim_eyes.py serve): {"id", "path"} -> the same reply; {"unload": true} frees it
// Desk then uses those instead of starting its own Python processes. Without Glim (other Macs, Windows, the old layout),
// nothing answers here and Desk spawns them as before. PREMONITION_GLIM_SIDE overrides the URL; "off" turns the attach off.
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');

const DEFAULT = 'http://127.0.0.1:18083';

function sideUrl(env) {
  const v = String((env || process.env).PREMONITION_GLIM_SIDE || '').trim();
  if (v === 'off' || v === '0') return '';
  return (v || DEFAULT).replace(/\/+$/, '');
}

function request(url, method, body, timeoutMs) {
  return new Promise((resolve, reject) => {
    let r;
    try {
      r = http.request(url, { method, headers: body ? { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } : {} }, (res) => {
        let buf = '';
        res.setEncoding('utf8');
        res.on('data', (d) => { buf += d; });
        res.on('end', () => resolve({ status: res.statusCode, text: buf }));
      });
    } catch (e) { return reject(e); }
    r.setTimeout(timeoutMs || 2000, () => r.destroy(new Error('Glim did not answer in time')));
    r.on('error', reject);
    if (body) r.write(body);
    r.end();
  });
}

// -> the part list ({stt, diary, ...}) when Glim answers, else null. Never throws.
async function probe(env, timeoutMs) {
  const base = sideUrl(env);
  if (!base) return null;
  try {
    const r = await request(base + '/glim', 'GET', null, timeoutMs || 800);
    if (r.status !== 200) return null;
    const j = JSON.parse(r.text);
    return j && j.name === 'Glim' && j.parts && typeof j.parts === 'object' ? j.parts : null;
  } catch (e) { return null; }
}

// POST one JSON object to Glim's side server -> the reply object (null for 204). Throws on transport errors.
async function post(route, msg, timeoutMs, env) {
  const r = await request(sideUrl(env) + route, 'POST', JSON.stringify(msg), timeoutMs || 30000);
  if (r.status === 204) return null;
  if (r.status !== 200) throw new Error('Glim ' + route.slice(1) + ' answered HTTP ' + r.status);
  return JSON.parse(r.text);
}
// One JSON-RPC message to Glim's diary -> its reply object (null for a notification).
function diaryRpc(msg, timeoutMs, env) { return post('/diary', msg, timeoutMs, env); }

// Same interface as eyes.js EyesWorker (encode(file) -> reply, stop()). Asks Glim (re-checked every minute) whether it has eyes;
// with Glim (or Glim expected but restarting) frames go to POST /eyes, else to the inner spawned worker, as before.
class GlimEyesWorker {
  constructor(o) { this.o = o; this.mode = ''; this.at = 0; this.seq = 0; }   // o: {inner, probe, expected, post, now}
  async _mode() {
    const now = (this.o.now || Date.now)();
    if (this.mode && now - this.at < 60000) return this.mode;
    let p = null; try { p = await this.o.probe(); } catch (e) { p = null; }
    this.mode = (p && p.eyes) || (!p && this.o.expected()) ? 'glim' : 'own'; this.at = now;
    if (this.mode === 'glim') this.o.inner.stop();   // never two eyes
    return this.mode;
  }
  async encode(file) {
    if (await this._mode() === 'own') return this.o.inner.encode(file);
    const r = await this.o.post({ id: String(++this.seq), path: file }, 30000);
    if (!r || !r.ok) throw new Error((r && r.error) || 'eyes failed');
    return r;
  }
  stop() {
    this.o.inner.stop();
    if (this.mode === 'glim') { this.mode = ''; Promise.resolve().then(() => this.o.post({ unload: true }, 5000)).catch(() => { /* Glim down: nothing loaded */ }); }
  }
}

// Glim is installed and meant to be running (serve.sh writes this file, stop.sh removes it): while it restarts, wait for it
// instead of starting separate speech / diary processes.
function expected(home, env) {
  if (!sideUrl(env)) return false;
  try { return fs.existsSync(path.join(home || os.homedir(), 'learner-ops', 'assistant', 'run', 'glim.pid')); } catch (e) { return false; }
}

module.exports = { probe, post, diaryRpc, sideUrl, expected, GlimEyesWorker, DEFAULT };
