'use strict';
// Sandbox input only. Production OS input is deliberately not a backend here.
const { randomUUID } = require('node:crypto');
const now = () => Number(process.hrtime.bigint()) / 1e6;
const KEYS = new Set(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space','Backspace','Enter','Tab']);
class Lease {
  constructor({ apply, clock = now, watchdog = true } = {}) {
    if (typeof apply !== 'function') throw Error('sandbox input receiver required');
    this.apply = apply; this.clock = clock; this.keys = new Set(); this.buttons = new Set();
    this.id = null; this.generation = 0; this.blocked = 'not armed'; this.deadline = 0;
    this.watch = watchdog ? setInterval(() => this.expire(), 2) : null;
    if (this.watch) this.watch.unref();
  }
  grant({ windowId, intentVersion, sandbox, watcherReady }) {
    this.revoke('new lease');
    if (sandbox !== true || watcherReady !== true || !windowId || !Number.isSafeInteger(intentVersion)) throw Error('sandbox and watcher required');
    this.id = randomUUID(); this.windowId = windowId; this.version = intentVersion;
    this.blocked = null; this.deadline = this.clock() + 50; return { leaseId: this.id, intentVersion, windowId };
  }
  revoke(reason = 'takeover') {
    this.id = null; this.generation++; this.blocked = reason; this.deadline = 0;
    const released = { keys: [...this.keys], buttons: [...this.buttons] };
    this.keys.clear(); this.buttons.clear();
    if (released.keys.length || released.buttons.length) this.apply({ release: released, receivedMs: this.clock(), generation: this.generation });
    return { revokedMs: this.clock(), released };
  }
  expire() { if (this.id && this.clock() >= this.deadline) this.revoke('expired'); }
  packet(p) {
    this.expire(); const t = this.clock();
    if (!this.id || p.leaseId !== this.id || p.intentVersion !== this.version || p.windowId !== this.windowId) return { ok: false, reason: this.blocked || 'stale packet' };
    const keys = p.keys || [], buttons = p.buttons || [];
    if (!Array.isArray(keys) || !Array.isArray(buttons) || keys.some(k => !KEYS.has(k)) || buttons.some(b => !['left','right'].includes(b)) || new Set(keys).size !== keys.length || new Set(buttons).size !== buttons.length) return { ok:false, reason:'bad held state' };
    if (![p.dx || 0,p.dy || 0,p.wheel || 0,p.expiresMs,p.holdMs].every(Number.isFinite) || p.expiresMs < t || p.holdMs <= 0 || p.holdMs > 50 || p.expiresMs > t + 50 || Math.abs(p.dx || 0)>320 || Math.abs(p.dy || 0)>180 || Math.abs(p.wheel || 0)>120) return { ok:false, reason:'bad bounds/expiry' };
    if (p.character != null && ([...p.character].length !== 1 || /[\u0000-\u001f\u007f]/u.test(p.character))) return { ok:false, reason:'bad character' };
    // No await between the final lease check and the sandbox receiver.
    this.keys = new Set(keys); this.buttons = new Set(buttons); this.deadline = Math.min(p.expiresMs,t+p.holdMs);
    this.apply({ ...p, receivedMs:t, generation:this.generation }); return { ok:true, receivedMs:t };
  }
  userInput() { return this.revoke('Ben input'); }
  close() { if(this.watch) clearInterval(this.watch); this.revoke('closed'); }
}
module.exports = { Lease, now, KEYS };
