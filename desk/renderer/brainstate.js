'use strict';
// One source of truth for "is Glim's brain ready?" (SWITCH-ON 2026-11-05). Ben saw the header say "Warming up…" while a message he sent
// was bounced with "I'm off right now": the header read the gateway state, the reply read only "did Ben press Turn on". Both now ask
// phase() below. While the brain is starting or restarting a message is HELD (never bounced) and sent once the brain is ready; when it is
// truly off the message is held too, so Ben never retypes it. Works in the renderer (window.BrainState) and in node tests.
(function (root, make) { if (typeof module === 'object' && module.exports) module.exports = make(); else root.BrainState = make(); })(typeof window !== 'undefined' ? window : this, function () {
  const START_MS = 120000;   // after Turn on, starting for up to 2 minutes
  // s: { gw: {state: 'ready'|'warming'|'down'}, startedAt (ms, Turn on pressed), now, asleep, waking, why: {kind, restarting} }
  function phase(s) {
    s = s || {}; const now = s.now || Date.now();
    if (s.waking) return 'waking';
    if (s.asleep) return 'asleep';
    const st = s.gw && s.gw.state;
    if (st === 'ready') return 'ready';
    if (st === 'warming') return 'starting';
    if (s.startedAt && now - s.startedAt < START_MS) return 'starting';
    if (s.why && s.why.restarting) return 'starting';   // the memory watchdog stopped it and is bringing it back by itself
    return 'off';
  }
  const LABEL = { ready: 'Glimmering', starting: 'Warming up…', off: 'Off', asleep: 'Asleep', waking: 'Waking up…' };
  const label = (p) => LABEL[p] || 'Off';
  // what Glim says in the chat when a message has to wait
  function heldLine(p) {
    if (p === 'starting') return 'I’m warming up. I’ll answer as soon as I’m ready.';
    if (p === 'off') return 'I’m off right now. Press Turn on below and I’ll answer this as soon as I’m on. I kept your message.';
    return '';
  }
  // messages waiting for the brain: {threadId, text}. take(phase) hands them all over once (oldest first) when the phase is ready.
  class Held {
    constructor() { this.items = []; }
    hold(threadId, text) { const t = String(text || '').trim(); if (!t) return false; if (this.items.some((x) => x.threadId === threadId && x.text === t)) return false; this.items.push({ threadId, text: t, at: Date.now() }); return true; }
    take(p) { if (p !== 'ready' || !this.items.length) return []; const out = this.items; this.items = []; return out; }
    count() { return this.items.length; }
  }
  return { phase, label, heldLine, Held, START_MS };
});
