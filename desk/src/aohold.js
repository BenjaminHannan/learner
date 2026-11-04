'use strict';
// UI2 (Ben Nov 4, M3): Glim's unprompted chat words never land in the chat while a task is running (they could look like an interruption,
// and only Ben's own typed or dictated words may steer or cut a run). They wait, and go in when the task ends; stale ones are dropped.
class HoldWhileBusy {
  // busy(): a task is running; post(m): put it in the chat now; maxAgeMs: older held ones are dropped; max: newest kept
  constructor(o) { this.o = { maxAgeMs: 10 * 60 * 1000, max: 3, now: () => Date.now(), ...o }; this.held = []; }
  offer(m) {
    if (!this.o.busy()) { this.o.post(m); return 'posted'; }
    this.held.push({ m, at: this.o.now() });
    if (this.held.length > this.o.max) this.held.shift();
    return 'held';
  }
  // after a task ends (and whenever else): posts what waited, oldest first, unless a task is running again
  flush() {
    if (this.o.busy() || !this.held.length) return 0;
    const now = this.o.now(), list = this.held.splice(0).filter((h) => now - h.at <= this.o.maxAgeMs);
    for (const h of list) { try { this.o.post(h.m); } catch (e) { /* one bad post must not drop the rest */ } }
    return list.length;
  }
}
module.exports = { HoldWhileBusy };
