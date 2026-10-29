'use strict';
// llama-server supervisor: builds the command line, waits until /health says ok, restarts it after a crash (with a back-off)
// and stops it when the app quits. spawn / fetch are injectable for tests.
const { spawn: realSpawn, execFile } = require('child_process');
const C = require('./constants');

// -np 1 matters: by default llama-server splits the context over several slots (4), which would leave 2048 tokens per chat.
function buildArgs(o) {
  const a = ['-m', o.model, '--host', o.host || C.SERVER_HOST, '--port', String(o.port || C.SERVER_PORT), '-c', String(o.ctx || C.CTX), '-np', '1', '--jinja', '--no-webui'];
  a.push('-ngl', o.flavor === 'cpu' ? '0' : '99');
  if (o.lora) a.push('--lora', o.lora);
  if (o.threads) a.push('-t', String(o.threads));
  return a;
}

// ---- an orphaned llama-server from a crashed run may still hold the port (Windows) ----------------------------
// `netstat -ano -p tcp` line: "  TCP    127.0.0.1:18090   0.0.0.0:0   LISTENING   4321"
function parseNetstat(text, port) {
  for (const line of String(text || '').split(/\r?\n/)) {
    const m = /^\s*TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$/i.exec(line);
    if (m && Number(m[1]) === Number(port)) return Number(m[2]);
  }
  return 0;
}
// `tasklist /FI "PID eq N" /FO CSV /NH` -> "llama-server.exe","4321",...
function parseTasklistImage(csv) { const m = /^"([^"]+)"/.exec(String(csv || '').trim()); return m ? m[1] : ''; }
// macOS: `lsof -nP -iTCP:<port> -sTCP:LISTEN -t` prints the pid(s) listening; `ps -p <pid> -o comm=` prints the command path.
const lsofArgs = (port) => ['-nP', '-iTCP:' + port, '-sTCP:LISTEN', '-t'];
const parseLsofPid = (text) => { const m = /^\s*(\d+)\s*$/m.exec(String(text || '')); return m ? Number(m[1]) : 0; };
const isLlamaServerComm = (comm) => /(^|\/)llama-server$/.test(String(comm || '').trim());
const run = (cmd, args) => new Promise((resolve) => execFile(cmd, args, { windowsHide: true, timeout: 8000 }, (e, so) => resolve(e ? '' : String(so))));
// Kills the listener on `port` only when it is a llama-server.exe. Returns the pid killed or 0.
async function reclaimPort(port, exec, platform) {
  exec = exec || run;
  if ((platform || process.platform) === 'darwin') {
    const mpid = parseLsofPid(await exec('/usr/sbin/lsof', lsofArgs(port)));
    if (!mpid || !isLlamaServerComm(await exec('/bin/ps', ['-p', String(mpid), '-o', 'comm=']))) return 0;
    await exec('/bin/kill', [String(mpid)]);
    return mpid;
  }
  const pid = parseNetstat(await exec('netstat', ['-ano', '-p', 'tcp']), port);
  if (!pid) return 0;
  const image = parseTasklistImage(await exec('tasklist', ['/FI', 'PID eq ' + pid, '/FO', 'CSV', '/NH']));
  if (image.toLowerCase() !== 'llama-server.exe') return 0;
  await exec('taskkill', ['/PID', String(pid), '/F']);
  return pid;
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
    this.postHealthyCrashes = 0;
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
      const limit = setTimeout(() => { if (!settled) { this._kill(); fin({ ok: false, error: 'llama-server did not become ready in time' }); } }, this.o.startTimeoutMs || 180000); // never leave a half-started server behind
    });
  }
  // Start (or restart with new options). Resolves {ok, error?}.
  async start(opts) {
    if (opts && 'lora' in opts) this.lora = opts.lora;
    this.wanted = true;
    this._kill();
    if (['win32', 'darwin'].includes(this.o.platform || process.platform) || this.o.reclaim) { try { await (this.o.reclaim || reclaimPort)(this.o.port || C.SERVER_PORT, this.o.exec, this.o.platform); } catch (e) { /* best effort */ } }
    if (!this.wanted) return { ok: false, stopped: true, error: 'stopped' };   // turned off (or sleep began) while the port was being freed: launch nothing
    this.postHealthyCrashes = 0;
    this._set('starting');
    const r = await this._launch();
    if (r.ok) this._set('ready'); else { this._kill(); this._set('error', { error: r.error, exitedEarly: r.exitedEarly }); }
    return r;
  }
  async _crashed(code, wasHealthy) {
    if (wasHealthy) this.postHealthyCrashes++;
    // the graphics build keeps dying after it was running: switch to the CPU build
    if (this.postHealthyCrashes >= 2 && this.o.flavor !== 'cpu' && this.o.cpuFallback) {
      try { const r = await this.o.cpuFallback(); if (r && r.exe) { this.o.exe = r.exe; this.o.cwd = r.cwd || this.o.cwd; this.o.flavor = 'cpu'; this.postHealthyCrashes = 0; this._set('restarting', { code, flavor: 'cpu' }); } } catch (e) { /* keep trying vulkan */ }
    }
    const now = Date.now();
    this.crashes = this.crashes.filter((t) => now - t < 300000); this.crashes.push(now);
    if (this.crashes.length > 5) { this._set('error', { error: 'llama-server keeps crashing (exit ' + code + ')' }); return; }
    this._set('restarting', { code });
    const delay = Math.min(15000, 1000 * 2 ** (this.crashes.length - 1)) * (this.o.fastRetry ? 0.001 : 1);
    clearTimeout(this.timer);
    this.timer = setTimeout(async () => {
      if (!this.wanted) return;
      this._kill(); this.wanted = true; // exactly one server at a time
      const launching = this._launch(), g = this.gen;   // _launch takes the next generation
      const r = await launching;
      if (g !== this.gen) return;   // start() took over while this restart was launching: its server is not a crash
      if (r.ok) this._set('ready'); else if (this.wanted) this._crashed(-1);
    }, delay);
    if (this.timer.unref) this.timer.unref();
  }
  _kill() { clearTimeout(this.timer); const c = this.child; this.child = null; this.healthy = false; this.gen++; if (c) { try { c.kill(); } catch (e) { /* gone */ } } return c; }
  // resolves once the process has really exited (the RAM is free), or after a few seconds
  stop() {
    this.wanted = false;
    const c = this._kill();
    this._set('stopped');
    if (!c || c.exitCode !== undefined && c.exitCode !== null) return Promise.resolve();
    return new Promise((resolve) => { const t = setTimeout(resolve, this.o.stopWaitMs || 8000); if (t.unref) t.unref(); c.once('exit', () => { clearTimeout(t); resolve(); }); });
  }
}

module.exports = { LlamaServer, buildArgs, parseNetstat, parseTasklistImage, reclaimPort, parseLsofPid, lsofArgs, isLlamaServerComm };
