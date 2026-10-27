'use strict';
// llama-server supervisor: builds the command line, waits until /health says ok, restarts it after a crash (with a back-off)
// and stops it when the app quits. spawn / fetch are injectable for tests.
const { spawn: realSpawn } = require('child_process');
const C = require('./constants');

// -np 1 matters: by default llama-server splits the context over several slots (4), which would leave 2048 tokens per chat.
function buildArgs(o) {
  const a = ['-m', o.model, '--host', o.host || C.SERVER_HOST, '--port', String(o.port || C.SERVER_PORT), '-c', String(o.ctx || C.CTX), '-np', '1', '--jinja', '--no-webui'];
  a.push('-ngl', o.flavor === 'cpu' ? '0' : '99');
  if (o.lora) a.push('--lora', o.lora);
  if (o.threads) a.push('-t', String(o.threads));
  return a;
}

class LlamaServer {
  constructor(o) {
    this.o = o;
    this.spawn = o.spawn || realSpawn;
    this.fetch = o.fetch || fetch;
    this.child = null;
    this.wanted = false;
    this.healthy = false;
    this.crashes = [];
    this.timer = null;
    this.gen = 0;
    this.state = 'stopped';
  }
  _set(state, info) { this.state = state; if (this.o.onState) { try { this.o.onState(state, info || {}); } catch (e) { /* ignore */ } } }
  url() { return 'http://' + (this.o.host || C.SERVER_HOST) + ':' + (this.o.port || C.SERVER_PORT); }
  args() { return buildArgs({ ...this.o, lora: this.lora !== undefined ? this.lora : this.o.lora }); }

  async _health() {
    try { const r = await this.fetch(this.url() + '/health'); return r.ok; } catch (e) { return false; }
  }
  // spawn once and wait for health. Resolves {ok, error?, exitedEarly?}
  _launch() {
    const gen = ++this.gen;
    return new Promise((resolve) => {
      let child;
      let settled = false;
      const fin = (r) => { if (settled) return; settled = true; clearInterval(poll); clearTimeout(limit); resolve(r); };
      try { child = this.spawn(this.o.exe, this.args(), { cwd: this.o.cwd, windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] }); } catch (e) { return resolve({ ok: false, error: String(e.message || e), exitedEarly: true }); }
      this.child = child; this.healthy = false;
      let err = '';
      if (child.stderr) child.stderr.on('data', (d) => { err = (err + d).slice(-2000); if (this.o.log) this.o.log(String(d)); });
      child.on('error', (e) => fin({ ok: false, error: String(e.message || e), exitedEarly: true }));
      child.on('exit', (code) => {
        const was = this.healthy;
        this.healthy = false;
        if (this.child === child) this.child = null;
        if (!settled) fin({ ok: false, error: 'llama-server exited (' + code + '): ' + err.split('\n').filter(Boolean).slice(-2).join(' | '), exitedEarly: true });
        else if (this.wanted && gen === this.gen) this._crashed(code, was);
      });
      const poll = setInterval(async () => { if (await this._health()) { this.healthy = true; fin({ ok: true }); } }, this.o.pollMs || 500);
      const limit = setTimeout(() => fin({ ok: false, error: 'llama-server did not become ready in time' }), this.o.startTimeoutMs || 180000);
    });
  }
  // Start (or restart with new options). Resolves {ok, error?}.
  async start(opts) {
    if (opts && 'lora' in opts) this.lora = opts.lora;
    this.wanted = true;
    this._kill();
    this._set('starting');
    const r = await this._launch();
    if (r.ok) this._set('ready'); else { this._kill(); this._set('error', { error: r.error, exitedEarly: r.exitedEarly }); }
    return r;
  }
  _crashed(code) {
    const now = Date.now();
    this.crashes = this.crashes.filter((t) => now - t < 300000); this.crashes.push(now);
    if (this.crashes.length > 5) { this._set('error', { error: 'llama-server keeps crashing (exit ' + code + ')' }); return; }
    this._set('restarting', { code });
    const delay = Math.min(15000, 1000 * 2 ** (this.crashes.length - 1)) * (this.o.fastRetry ? 0.001 : 1);
    clearTimeout(this.timer);
    this.timer = setTimeout(async () => {
      if (!this.wanted) return;
      const r = await this._launch();
      if (r.ok) this._set('ready'); else if (this.wanted) this._crashed(-1);
    }, delay);
    if (this.timer.unref) this.timer.unref();
  }
  _kill() { clearTimeout(this.timer); const c = this.child; this.child = null; this.healthy = false; this.gen++; if (c) { try { c.kill(); } catch (e) { /* gone */ } } }
  stop() { this.wanted = false; this._kill(); this._set('stopped'); }
}

module.exports = { LlamaServer, buildArgs };
