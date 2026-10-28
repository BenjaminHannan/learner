'use strict';
// Self-warm: the gateway caches the prompt prefix (system prompt + tools). Desk's prefix is constant, so one tiny
// request with exactly that prefix makes the first real reply fast (0.15 s warm vs 13 s cold on the M1).
// Also watches the gateway: down -> up triggers a warm-up. Never blocks the UI; all failures are quiet.
const { SYSTEM_PROMPT } = require('./prompt');
const { buildChatBody, chatUrl } = require('./llm');

const WARM_MODEL = 'qwen36-fast';
const WARM_HEADER = 'X-Premonition-Warm';

// Same builder as real requests; only the user text, stream flag and max_tokens differ (all after the tools/system part).
function buildWarmBody(tools, model) {
  return buildChatBody({ model: model || WARM_MODEL, messages: [{ role: 'system', content: SYSTEM_PROMPT }, { role: 'user', content: '.' }], tools, stream: false, maxTokens: 1 });
}

class Warmer {
  /**
   * getSettings(), getTools() -> current tool defs, onState('down'|'warming'|'ready', info), busy() -> true while a run is going
   * downMs / upMs: poll intervals (5 s while down, 30 s while up)
   */
  constructor(o) {
    this.o = o;
    this.state = 'down';
    this.wasUp = false;
    this.need = false;
    this.timer = null;
    this.gen = 0;
    this.stopped = true;
    this.warming = false;
    this.warmCount = 0;
    this.lastWarmMs = null;
    this.lastPingMs = null;
  }
  set(state, info) {
    const key = state + ':' + (info && info.ms);
    if (key === this.lastKey) return; // no repeats while nothing changed
    this.lastKey = key; this.state = state; try { this.o.onState && this.o.onState(state, info || {}); } catch (e) { /* ignore */ } }
  start() { this.stopped = false; this._tick(); }
  stop() { this.stopped = true; clearTimeout(this.timer); this.timer = null; }
  // after a settings change that affects the prefix (model, gateway, tool list)
  rewarm() { this.need = true; if (!this.stopped && !this.warming) { clearTimeout(this.timer); this._tick(); } }
  gatewayMoved() { this.wasUp = false; this.rewarm(); }

  async ping() {
    const base = String(this.o.getSettings().gatewayUrl).replace(/\/+$/, '');
    const f = this.o.fetch || fetch;
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 2500);
    const t0 = Date.now();
    try { const r = await f(base + '/models', { signal: ctl.signal }); this.lastPingMs = Date.now() - t0; return !!r.ok; } catch (e) { return false; } finally { clearTimeout(t); }
  }

  async warm() {
    if (this.warming) return; // never two warm requests at once
    this.warming = true;
    const s = this.o.getSettings();
    const f = this.o.fetch || fetch;
    this.set('warming');
    const t0 = Date.now();
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), this.o.timeoutMs || 180000);
    try {
      const headers = { 'content-type': 'application/json', [WARM_HEADER]: '1' };
      if (s.apiKey) headers.authorization = 'Bearer ' + s.apiKey;
      const r = await f(chatUrl(s.gatewayUrl), { method: 'POST', headers, body: JSON.stringify(buildWarmBody(this.o.getTools(), s.modelFast)), signal: ctl.signal });
      try { await r.text(); } catch (e) { /* body not needed */ }
      // A server that does not know X-Premonition-Warm just ignores it. If it refuses the request anyway (non-2xx), nothing is warm: no count.
      if (r.ok === false) return;
      this.warmCount++;
      this.lastWarmMs = Date.now() - t0;
    } catch (e) { /* the real request will warm it the slow way */ } finally { clearTimeout(t); this.warming = false; }
  }

  async _tick() {
    if (this.stopped) return;
    const gen = ++this.gen;
    clearTimeout(this.timer);
    const up = await this.ping();
    if (this.stopped || gen !== this.gen) return;
    let next = this.o.upMs || 30000;
    if (!up) { this.wasUp = false; this.set('down'); next = this.o.downMs || 5000; }
    else {
      if (!this.wasUp || this.need) {
        this.wasUp = true; this.need = false;
        if (this.o.busy && this.o.busy()) this.set('ready'); // a real request is already warming it
        else await this.warm();
        if (this.stopped || gen !== this.gen) return;
      }
      this.set('ready', { ms: this.lastWarmMs });
    }
    if (this.need) next = 200; // a settings change arrived during the warm-up
    this.timer = setTimeout(() => this._tick(), next);
    if (this.timer.unref) this.timer.unref();
  }
}

module.exports = { Warmer, buildWarmBody, WARM_MODEL, WARM_HEADER };
