'use strict';
// The built-in local model, as one object main.js can start and stop: download (first run) -> llama-server -> gateway.
// States: off | downloading | starting | ready | error. Everything slow is async and reports through onState.
const path = require('path');
const C = require('./constants');
const { ChatInstaller } = require('./install');
const { LlamaServer } = require('./llamaserver');
const { createGateway } = require('../gateway');

class Builtin {
  /** o: {root (…/Premonition), fetch, extract, spawn, onState(state), makeServer?} */
  constructor(o) {
    this.o = o;
    this.dir = path.join(o.root, 'runtime');
    this.diaryDir = path.join(o.root, 'diary', 'raw');
    this.st = { phase: 'off', label: '', pct: 0, done: 0, total: 0, error: '', flavor: (o.platform || process.platform) === 'darwin' ? 'metal' : 'vulkan', lora: '' };
    this.platform = o.platform || process.platform;
    this.installer = new ChatInstaller({ dir: this.dir, platform: o.platform, unquarantine: o.unquarantine, bundledExe: o.bundledExe, fetch: o.fetch, extract: o.extract, onProgress: (p) => this._progress(p) });
    this.server = null; this.gw = null; this.running = false; this.asleep = false; this.abort = null; this.cache = {};
  }
  state() { return { ...this.st }; }
  _set(patch) { this.st = { ...this.st, ...patch }; if (this.o.onState) { try { this.o.onState(this.state()); } catch (e) { /* ignore */ } } }
  _progress(p) {
    const pct = p.total ? Math.min(100, Math.round((p.done / p.total) * 100)) : 0;
    this._set({ phase: 'downloading', stage: p.stage, label: p.label, pct, done: p.done, total: p.total });
  }
  needsDownload() { return !C.llamaFlavors(this.platform).some((f) => this.installer.installed(f)); }

  async _launch(flavor, lora) {
    const exe = this.installer.llamaExe(flavor) || await this.installer.ensureLlama(flavor, this.abort && this.abort.signal);
    const model = await this.installer.ensureModel(this.abort && this.abort.signal);
    if (!this.running || this.asleep) return { ok: false, stopped: true, error: 'stopped' };
    this._set({ phase: 'starting', label: 'Starting the model', pct: 0, flavor });
    if (!this.server) {
      this.server = (this.o.makeServer || ((x) => new LlamaServer(x)))({
        exe: exe.exe, model: model.file, flavor, lora, cwd: path.dirname(exe.exe), platform: this.o.platform, spawn: this.o.spawn, fetch: this.o.fetch, fastRetry: this.o.fastRetry,
        port: C.SERVER_PORT, ctx: C.CTX,
        // the graphics build died twice after running: fetch (if needed) and switch to the CPU build
        cpuFallback: async () => { const e = this.installer.llamaExe('cpu') || await this.installer.ensureLlama('cpu', this.abort && this.abort.signal); return { exe: e.exe, cwd: path.dirname(e.exe) }; },
        onState: (s, info) => { if (s === 'ready') this._set({ phase: 'ready', label: 'Ready', pct: 100, error: '' }); else if (s === 'restarting') this._set({ phase: 'starting', label: 'Restarting the model' }); else if (s === 'error' && this.running) this._set({ phase: 'error', error: info.error || 'the model stopped' }); }
      });
    }
    this.server.o.exe = exe.exe; this.server.o.model = model.file; this.server.o.flavor = flavor; this.server.o.cwd = path.dirname(exe.exe);
    return this.server.start({ lora: lora || '' });
  }

  // Download if needed, start llama-server (Vulkan first, the CPU build if that will not start) and the gateway.
  async start(opts) {
    if (this.asleep) return this.state();          // asleep: nothing may start the model (a download finishing, a settings change)
    if (this.running) return this.state();
    this.running = true; this.abort = new AbortController();
    try {
      let r;
      // PREMONITION_LLAMA_FLAVOR=cpu skips the graphics build (testing on a PC whose GPU is busy)
      // macOS has the one Metal build and no CPU fallback
      const mac = this.platform === 'darwin';
      const first = mac ? 'metal' : (process.env.PREMONITION_LLAMA_FLAVOR === 'cpu' ? 'cpu' : 'vulkan');
      try { r = await this._launch(first, opts && opts.lora); } catch (e) { r = { ok: false, error: e.message, download: true }; }
      if (!r.ok && !r.stopped && this.running && !this.asleep && !mac && first !== 'cpu' && (!r.download || this.installer.llamaExe('cpu'))) { // (no Vulkan release yet + a bundled CPU engine also lands here) // Vulkan would not start on this GPU/driver: the CPU build
        this._set({ phase: 'downloading', label: 'The graphics build did not start; getting the CPU build', pct: 0 });
        r = await this._launch('cpu', opts && opts.lora);
      }
      // turned off or put to sleep while it was starting: leave it off (sleep needs the RAM), and do not call that an error
      if (!this.running || this.asleep) {
        if (r.ok) await this.server.stop();
        if (this.asleep) this._set({ phase: 'off', label: 'Asleep', pct: 0 });
        return this.state();
      }
      if (!r.ok) throw new Error(r.error || 'the model did not start');
      if (!this.gw) {
        this.gw = createGateway({ upstream: this.server.url(), diaryDir: this.diaryDir, upstreamModel: 'default', fetch: this.o.gwFetch, skipDiary: this.o.skipDiary });
        await this.gw.listen(this.o.gatewayPort === undefined ? C.GATEWAY_PORT : this.o.gatewayPort, '127.0.0.1');
      }
      this._set({ phase: 'ready', label: 'Ready', pct: 100, error: '' });
    } catch (e) {
      this.running = false;
      this._set({ phase: 'error', error: String(e && e.message || e) });
    }
    return this.state();
  }
  async retry() { if (this.asleep) return this.state(); this.running = false; this._set({ phase: 'off', error: '' }); return this.start(); }

  // Sleep needs the RAM: stop the model while asleep (resolves when the process has really exited), bring it back (optionally
  // with the new adapter) on wake. Both do nothing when this preset is not the one in use (the user chose another server).
  async pauseForSleep() {
    if (this.o.isWanted && !this.o.isWanted()) return { ok: true, skipped: true };
    this.asleep = true;
    if (this.abort) this.abort.abort();
    const stopped = this.server && await this.server.stop();
    if (stopped && stopped.ok === false) { this.asleep = false; return stopped; }
    this._set({ phase: 'off', label: 'Asleep', pct: 0 });
    return { ok: true };
  }
  async resume(lora) {
    if (this.o.isWanted && !this.o.isWanted()) { this.asleep = false; return { ok: true, skipped: true }; }
    this.asleep = false;
    if (!this.running || !this.server) { this.running = false; const st = await this.start({ lora }); return { ok: st.phase === 'ready', error: st.error }; }
    this._set({ phase: 'starting', label: 'Starting the model' });
    const r = await this.server.start({ lora: lora || '' });
    if (!r.ok && lora) { // the new adapter did not load: back to the plain model
      this._set({ error: '' }); const r2 = await this.server.start({ lora: '' });
      return { ok: this.st.phase === 'ready', loraFailed: true, error: r.error };
    }
    return { ok: this.st.phase === 'ready', error: r.ok ? '' : r.error };
  }
  async stop() {
    this.running = false;
    if (this.abort) { try { this.abort.abort(); } catch (e) { /* ignore */ } }
    if (this.server) await this.server.stop();
    if (this.gw) { await this.gw.close(); this.gw = null; }
    this._set({ phase: 'off' });
  }
}

// Every runtime, diary and sleep path hangs off one root, and that root is Electron's userData, so --user-data-dir moves all of it.
const runtimeRoot = (userData) => path.resolve(String(userData));
module.exports = { Builtin, runtimeRoot };
