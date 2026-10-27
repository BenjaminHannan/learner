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
    this.st = { phase: 'off', label: '', pct: 0, done: 0, total: 0, error: '', flavor: 'vulkan', lora: '' };
    this.installer = new ChatInstaller({ dir: this.dir, fetch: o.fetch, extract: o.extract, onProgress: (p) => this._progress(p) });
    this.server = null; this.gw = null; this.running = false; this.abort = null; this.cache = {};
  }
  state() { return { ...this.st }; }
  _set(patch) { this.st = { ...this.st, ...patch }; if (this.o.onState) { try { this.o.onState(this.state()); } catch (e) { /* ignore */ } } }
  _progress(p) {
    const pct = p.total ? Math.min(100, Math.round((p.done / p.total) * 100)) : 0;
    this._set({ phase: 'downloading', stage: p.stage, label: p.label, pct, done: p.done, total: p.total });
  }
  needsDownload() { return !this.installer.installed('vulkan') && !this.installer.installed('cpu'); }

  async _launch(flavor, lora) {
    const exe = this.installer.llamaExe(flavor) || await this.installer.ensureLlama(flavor, this.abort && this.abort.signal);
    const model = await this.installer.ensureModel(this.abort && this.abort.signal);
    this._set({ phase: 'starting', label: 'Starting the model', pct: 0, flavor });
    if (!this.server) {
      this.server = (this.o.makeServer || ((x) => new LlamaServer(x)))({
        exe: exe.exe, model: model.file, flavor, lora, cwd: path.dirname(exe.exe), spawn: this.o.spawn, fetch: this.o.fetch, fastRetry: this.o.fastRetry,
        port: C.SERVER_PORT, ctx: C.CTX,
        onState: (s, info) => { if (s === 'ready') this._set({ phase: 'ready', label: 'Ready', pct: 100, error: '' }); else if (s === 'restarting') this._set({ phase: 'starting', label: 'Restarting the model' }); else if (s === 'error' && this.running) this._set({ phase: 'error', error: info.error || 'the model stopped' }); }
      });
    }
    this.server.o.exe = exe.exe; this.server.o.model = model.file; this.server.o.flavor = flavor; this.server.o.cwd = path.dirname(exe.exe);
    return this.server.start({ lora: lora || '' });
  }

  // Download if needed, start llama-server (Vulkan first, the CPU build if that will not start) and the gateway.
  async start(opts) {
    if (this.running) return this.state();
    this.running = true; this.abort = new AbortController();
    try {
      let r;
      try { r = await this._launch('vulkan', opts && opts.lora); } catch (e) { r = { ok: false, error: e.message, download: true }; }
      if (!r.ok && !r.download) { // Vulkan would not start on this GPU/driver: the CPU build
        this._set({ phase: 'downloading', label: 'The graphics build did not start; getting the CPU build', pct: 0 });
        r = await this._launch('cpu', opts && opts.lora);
      }
      if (!r.ok) throw new Error(r.error || 'the model did not start');
      if (!this.gw) {
        this.gw = createGateway({ upstream: this.server.url(), diaryDir: this.diaryDir, upstreamModel: 'default', fetch: this.o.gwFetch });
        await this.gw.listen(this.o.gatewayPort === undefined ? C.GATEWAY_PORT : this.o.gatewayPort, '127.0.0.1');
      }
      this._set({ phase: 'ready', label: 'Ready', pct: 100, error: '' });
    } catch (e) {
      this.running = false;
      this._set({ phase: 'error', error: String(e && e.message || e) });
    }
    return this.state();
  }
  async retry() { this.running = false; this._set({ phase: 'off', error: '' }); return this.start(); }

  // Sleep needs the RAM: stop the model while asleep, bring it back (optionally with the new adapter) on wake.
  pauseForSleep() { if (this.server) this.server.stop(); this._set({ phase: 'off', label: 'Asleep', pct: 0 }); }
  async resume(lora) {
    if (!this.running) return this.start({ lora });
    this._set({ phase: 'starting', label: 'Starting the model' });
    const r = await this.server.start({ lora: lora || '' });
    if (!r.ok && lora) { // the new adapter did not load: back to the plain model
      this._set({ error: '' }); const r2 = await this.server.start({ lora: '' });
      return { ...r2, loraFailed: true, error: r.error };
    }
    return r;
  }
  async stop() {
    this.running = false;
    if (this.abort) { try { this.abort.abort(); } catch (e) { /* ignore */ } }
    if (this.server) this.server.stop();
    if (this.gw) { await this.gw.close(); this.gw = null; }
    this._set({ phase: 'off' });
  }
}

module.exports = { Builtin };
