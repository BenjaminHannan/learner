'use strict';
// Minimal stdio MCP client (newline-delimited JSON-RPC) for diary_mcp.py.
// ONE-GLIM (2026-11-05): with the default diary path and opts.glimProbe given, when the one "Glim" process answers with
// parts.diary, the same JSON-RPC messages go to Glim's POST /diary (opts.glimRpc) instead of a Python child of Desk.
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

function resolvePaths(settings) {
  const home = os.homedir();
  const diary = (settings.diaryPath || '').replace(/^~/, home) || path.join(home, 'learner-ops', 'assistant', 'diary_mcp.py');
  let py = (settings.pythonPath || '').replace(/^~/, home);
  if (!py) {
    const win = process.platform === 'win32';
    const venv = win ? path.join(home, 'learner-ops', '.venv', 'Scripts', 'python.exe') : path.join(home, 'learner-ops', '.venv', 'bin', 'python');
    py = fs.existsSync(venv) ? venv : (win ? 'python' : 'python3');
  }
  return { diary, py };
}

class Diary {
  constructor(getSettings, opts) {
    this.getSettings = getSettings;
    this.opts = opts || {};
    this.glim = false;
    this.proc = null;
    this.nextId = 1;
    this.pending = new Map();
    this.buf = '';
    this.ready = null;
  }

  _start() {
    if (this.ready) return this.ready;
    const s = this.getSettings();
    if (this.opts.glimProbe && this.opts.glimRpc && !s.diaryPath) {
      // Glim's diary is stateless (no initialize needed). A Glim that is expected (its pid file exists) but restarting still counts:
      // calls fail until it is back instead of a second diary process starting for the rest of the app's life.
      this.ready = Promise.resolve(this.opts.glimProbe()).catch(() => null).then((parts) => {
        const expected = !!(this.opts.glimExpected && this.opts.glimExpected());
        if (!(parts && parts.diary) && !(parts === null && expected)) { this.ready = null; return this._spawnStart(); }
        this.glim = true;
        return true;
      });
      return this.ready;
    }
    return this._spawnStart();
  }

  _spawnStart() {
    if (this.ready) return this.ready;
    this.glim = false;
    const { diary, py } = resolvePaths(this.getSettings());
    this.ready = new Promise((resolve, reject) => {
      if (!fs.existsSync(diary)) return reject(new Error('diary_mcp.py not found at ' + diary));
      let p;
      try { p = spawn(py, [diary], { stdio: ['pipe', 'pipe', 'ignore'] }); } catch (e) { return reject(e); }
      this.proc = p; this.buf = '';   // a dead process's half line must not be glued onto this one's first reply
      p.stdin.on('error', () => { /* python missing or exited: the 'error'/'exit' handlers report it once */ });
      // an old process that was stopped can exit after a new one started: only the current process may fail the pending calls
      p.on('error', (e) => { if (this.proc === p) this._fail(e); reject(e); });
      p.on('exit', () => { if (this.proc === p) this._fail(new Error('diary process exited')); });
      p.stdout.on('data', (d) => {
        if (this.proc !== p) return;
        this.buf += d;
        let i;
        while ((i = this.buf.indexOf('\n')) >= 0) {
          const line = this.buf.slice(0, i).trim();
          this.buf = this.buf.slice(i + 1);
          if (!line) continue;
          let m; try { m = JSON.parse(line); } catch (e) { continue; }
          const w = m.id !== undefined && this.pending.get(m.id);
          if (w) { this.pending.delete(m.id); m.error ? w.reject(new Error(m.error.message || 'MCP error')) : w.resolve(m.result); }
        }
      });
      this._rpc('initialize', { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'premonition-desk', version: '1.0.0' } }, 15000)
        .then(() => { this._send({ jsonrpc: '2.0', method: 'notifications/initialized' }); resolve(true); })
        .catch(reject);
    });
    this.ready.catch(() => { this.ready = null; this.stop(); });
    return this.ready;
  }

  _fail(err) {
    for (const w of this.pending.values()) w.reject(err);
    this.pending.clear();
    this.proc = null;
    this.ready = null;
  }

  _send(o) {
    if (this.glim) { this.opts.glimRpc(o, 5000).catch(() => { /* a lost notification is harmless */ }); return; }
    this.proc.stdin.write(JSON.stringify(o) + '\n');
  }

  _rpc(method, params, timeoutMs) {
    if (this.glim) {
      const id = this.nextId++;
      return this.opts.glimRpc({ jsonrpc: '2.0', id, method, params }, timeoutMs || 30000).then((m) => {
        if (!m) throw new Error('empty diary reply');
        if (m.error) throw new Error(m.error.message || 'MCP error');
        return m.result;
      });
    }
    return new Promise((resolve, reject) => {
      const id = this.nextId++;
      const t = setTimeout(() => { this.pending.delete(id); reject(new Error('diary timed out')); }, timeoutMs || 30000);
      this.pending.set(id, { resolve: (v) => { clearTimeout(t); resolve(v); }, reject: (e) => { clearTimeout(t); reject(e); } });
      try { this._send({ jsonrpc: '2.0', id, method, params }); } catch (e) { clearTimeout(t); this.pending.delete(id); reject(e); }
    });
  }

  // Decide once at startup whether the diary tool exists.
  async probe() {
    try { await this._start(); return true; } catch (e) { return false; }
  }

  async search(query) {
    try {
      await this._start();
      const r = await this._rpc('tools/call', { name: 'diary_search', arguments: { query: String(query || '') } }, 30000);
      const text = (r && r.content || []).map((c) => c.text || '').join('\n').trim();
      return (text || '(no matches)').slice(0, 4000);
    } catch (e) {
      return 'Error: diary unavailable (' + e.message + ')';
    }
  }

  stop() { this.glim = false; const p = this.proc; if (p) this._fail(new Error('diary stopped')); try { p && p.kill(); } catch (e) { /* ignore */ } }   // its calls fail now, not after their timeout
}

module.exports = { Diary, resolvePaths };
