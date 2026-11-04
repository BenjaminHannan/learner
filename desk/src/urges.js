'use strict';
// Always-on v2, phase 4a: urges. Three meters (0..1) that fill over time and persist in alwayson-state.json:
//   🥱 bored   fills while nothing new arrives and Ben is not chatting -> start thinking / learning Motes
//   🤔 curious fills when Glim meets something it does not understand (each item goes on the wonder list)
//   📣 share   fills when it has something worth telling (a confirmed note, a quiz level-up, a big surprise) -> asks the speak-o-meter
// Pure Node.

const BORED_FILL_MS = 30 * 60000;   // a quiet half hour fills "bored" from 0 to 1
const SHARE_FADE_MS = 2 * 3600000;  // an untold thing stops pressing after ~2 hours
const BORED_AT = 0.6;

const clamp = (v) => Math.max(0, Math.min(1, Number(v) || 0));

class Urges {
  // o: { now, saved: {bored, curious, share, at} }
  constructor(o) {
    o = o || {}; this.now = o.now || Date.now;
    const s = o.saved || {};
    this.bored = clamp(s.bored); this.curious = clamp(s.curious); this.share = clamp(s.share);
    this.at = Number(s.at) || this.now();
  }
  // advance the clock. ctx: { fresh: new observations since the last tick, chatting: Ben chatted recently, wonder: wonder-list size }
  tick(ctx) {
    ctx = ctx || {};
    const now = this.now(), dt = Math.max(0, Math.min(now - this.at, 3600000)); this.at = now;
    if (ctx.chatting) this.bored = Math.max(0, this.bored - dt / (BORED_FILL_MS / 4));
    else if (ctx.fresh) this.bored = Math.max(0, this.bored - 0.1);
    else this.bored = clamp(this.bored + dt / BORED_FILL_MS);
    // curiosity follows the unread part of the wonder list (each open question presses a little)
    if (ctx.wonder != null) this.curious = clamp(Math.max(this.curious * Math.exp(-dt / (6 * 3600000)), Math.min(1, ctx.wonder * 0.15)));
    this.share = clamp(this.share * Math.exp(-dt / SHARE_FADE_MS));
    return this.view();
  }
  wonder() { this.curious = clamp(this.curious + 0.25); }      // it met something it does not understand
  worthTelling(w) { this.share = clamp(this.share + (w == null ? 0.4 : w)); }
  spoke() { this.share = 0; }
  studied(n) { this.bored = clamp(this.bored - 0.5); this.curious = clamp(this.curious - 0.1 * (n || 1)); }
  isBored() { return this.bored >= BORED_AT; }
  view() { const r = (x) => Math.round(x * 100) / 100; return { bored: r(this.bored), curious: r(this.curious), share: r(this.share), at: this.at }; }
}

// What a bored Glim thinks about: (a) Ben's Learn topics, then (b) his day (an error he keeps hitting, surprising moments,
// what he was working on), then (c) the wonder list (its own mistakes and unknowns). Topics studied in the last `freshMs` are skipped.
// src: { learn: [topic], day: [text], wonder: [text], recent: {topicLower: t} } -> [{kind, topic}] (at most n)
function chooseTopics(src, n, now, freshMs) {
  src = src || {}; now = now || Date.now(); freshMs = freshMs == null ? 30 * 60000 : freshMs;
  const recent = src.recent || {};
  const seen = new Set(), out = [];
  const push = (kind, topic) => {
    const t = String(topic || '').replace(/\s+/g, ' ').trim().slice(0, 160); const k = t.toLowerCase();
    if (!t || seen.has(k) || (recent[k] && now - recent[k] < freshMs)) return;
    seen.add(k); out.push({ kind, topic: t });
  };
  for (const t of src.learn || []) push('learn', t);
  for (const t of src.day || []) push('day', t);
  for (const t of src.wonder || []) push('wonder', t);
  return out.slice(0, Math.max(0, n | 0));
}

module.exports = { Urges, chooseTopics, BORED_AT, BORED_FILL_MS };
