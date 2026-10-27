'use strict';
// Minimal stdio MCP client (newline-delimited JSON-RPC) for diary_mcp.py.
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

function resolvePaths(settings) {
  const home = os.homedir();
  const diary = (settings.diaryPath || '').replace(/^~/, home) || path.join(home, 'learner-ops', 'assistant', 'diary_mcp.py');
  let py = (settings.pythonPath || '').replace(/^~/, home);
  if (!py) {
    const venv = path.join(home, 'learner-ops', '.venv', 'bin', 'python');
    py = fs.existsSync(venv) ? venv : 'python3';
  }
  return { diary, py };
}

class Diary {
  constructor(getSettings) {
    this.getSettings = getSettings;
    this.proc = null;
    this.nextId = 1;
    this.pending = new Map();
    this.buf = '';
    this.ready = null;
  }

  _start() {
    if (this.ready) return this.ready;
    const { diary, py } = resolvePaths(this.getSettings());
    this.ready = new Promise((resolve, reject) => {
      if (!fs.existsSync(diary)) return reject(new Error('diary_mcp.py not found at ' + diary));
      let p;
      try { p = spawn(py, [diary], { stdio: ['pipe', 'pipe', 'ignore'] }); } catch (e) { return reject(e); }
      this.proc = p;
      p.on('error', (e) => { this._fail(e); reject(e); });
      p.on('exit', () => { this._fail(new Error('diary process exited')); });
      p.stdout.on('data', (d) => {
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

  _send(o) { this.proc.stdin.write(JSON.stringify(o) + '\n'); }

  _rpc(method, params, timeoutMs) {
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

  stop() { try { this.proc && this.proc.kill(); } catch (e) { /* ignore */ } this.proc = null; }
}

module.exports = { Diary, resolvePaths };
