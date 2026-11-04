'use strict';
// Always-on v2, phase 1: how Glim's unprompted words reach Ben, and the status icon in the notch ear.
// Pure Node (outlets, clocks and "is Ben typing" are injected), so the tests drive it without Electron.
//
//   where:   a notched Mac -> the notch island drops down with the message (a click opens chat);
//            a Mac without a notch -> the floating pill; Settings "Use the notch" OFF -> a macOS notification instead.
//            The words are also kept in the main chat, marked alwaysOn, with 👍 / 👎 "not now" under them.
//   when:    NEVER while Ben is typing. A message that arrives then waits (up to holdMaxMs) and goes out once he has stopped
//            for quietMs; if he keeps typing past holdMaxMs it is dropped, not delivered late.
//   status:  😴 resting · 📚 learning (+ Mote count) · 💭 thinking · 😲 just surprised; hover = a detail line.

const SURPRISE_SHOW_MS = 20000;   // the 😲 face stays this long after a big surprise
const QUIET_MS = 4000;            // Ben must have stopped typing this long before a message goes out
const HOLD_MAX_MS = 120000;       // a message held for typing is dropped after this
const IGNORE_MS = 10 * 60000;     // no reply / button / click within this = "ignored" (a weak no for the speak-o-meter)

// -> 'notch' | 'pill' | 'notification'
function route(o) {
  o = o || {};
  if (o.useNotch === false) return 'notification';
  if (o.notched) return 'notch';
  return o.pillOn === false ? 'notification' : 'pill';
}

// o: { asleep, thinking, learning: {topic, levels: [{level, pct}]} | null, motes: n, surprisedAt, now, gauge: 'green'|'yellow'|'red' }
// -> { icon, state, text (short, shown in the ear), detail (hover line) }
function statusIcon(o) {
  o = o || {};
  const now = o.now || Date.now();
  const motes = Math.max(0, o.motes | 0);
  const moteWord = motes ? motes + ' Mote' + (motes === 1 ? '' : 's') : '';
  const gauge = o.gauge === 'red' ? '🔴 memory tight' : o.gauge === 'yellow' ? '🟡 memory busy' : '';
  const L = o.learning;
  const score = L && Array.isArray(L.levels) && L.levels.length ? L.levels.map((x) => 'Lv' + x.level + ' ' + (x.pct == null ? '–' : Math.round(x.pct) + '%')).join(' · ') : '';
  let icon, state, detail;
  if (o.asleep) { icon = '😴'; state = 'resting'; detail = '😴 sleeping'; }
  else if (o.surprisedAt && now - o.surprisedAt < SURPRISE_SHOW_MS) { icon = '😲'; state = 'surprised'; detail = '😲 that was unexpected' + (o.surpriseWhat ? ': ' + String(o.surpriseWhat).slice(0, 60) : ''); }
  else if (o.thinking) { icon = '💭'; state = 'thinking'; detail = '💭 thinking' + (o.thinkingAbout ? ' about ' + String(o.thinkingAbout).slice(0, 50) : ''); }
  else if (L && L.topic) { icon = '📚'; state = 'learning'; detail = '📚 ' + String(L.topic).slice(0, 50); }
  else if (motes) { icon = '📚'; state = 'learning'; detail = '📚 studying'; }
  else { icon = '😴'; state = 'resting'; detail = '😴 resting'; }
  const parts = [detail];
  if (state === 'learning' && score) parts.push(score);
  if (moteWord && state !== 'resting') parts.push(moteWord);
  if (gauge) parts.push(gauge);
  return { icon, state, text: icon + (state === 'learning' && motes ? ' ' + motes : ''), detail: parts.join(' · ') };
}

let seq = 0;
class Voice {
  // o: { outlets: {notch(msg), pill(msg), notification(msg), chat(msg)}, where() -> 'notch'|'pill'|'notification',
  //      typing() -> bool, now, onOutcome(msg, kind) (kind: 'up'|'down'|'notnow'|'ignored'|'reply'|'used'), log }
  constructor(o) {
    this.o = o || {}; this.now = this.o.now || Date.now; this.log = this.o.log || (() => {});
    this.quietMs = this.o.quietMs || QUIET_MS; this.holdMaxMs = this.o.holdMaxMs || HOLD_MAX_MS; this.ignoreMs = this.o.ignoreMs || IGNORE_MS;
    this.pending = [];   // waiting for Ben to stop typing
    this.sent = [];      // delivered, newest last (kept 50) {id, text, at, where, features, outcome}
    this.lastTypingAt = 0;
    this.stats = { offered: 0, delivered: 0, droppedTyping: 0 };
  }
  typingNow() {
    const t = !!(this.o.typing && this.o.typing());
    if (t) this.lastTypingAt = this.now();
    return t || (this.lastTypingAt && this.now() - this.lastTypingAt < this.quietMs);
  }
  // queue a message; it goes out at once unless Ben is typing. -> the message
  offer(text, extra) {
    const msg = { id: 'say-' + this.now().toString(36) + '-' + (++seq), text: String(text || '').slice(0, 400), offeredAt: this.now(), ...(extra || {}) };
    if (!msg.text) return null;
    this.stats.offered++;
    this.pending.push(msg);
    this.pump();
    return msg;
  }
  // called every second by main (and by offer): deliver what may go out, drop what waited too long
  pump() {
    if (!this.pending.length) return 0;
    const now = this.now();
    this.pending = this.pending.filter((m) => { if (now - m.offeredAt > this.holdMaxMs) { this.stats.droppedTyping++; this.log('voice: dropped (Ben kept typing):', m.text.slice(0, 60)); return false; } return true; });
    if (!this.pending.length || this.typingNow()) return 0;
    let n = 0;
    while (this.pending.length) { const m = this.pending.shift(); this.deliver(m); n++; }
    return n;
  }
  deliver(m) {
    const out = this.o.outlets || {};
    const where = this.o.where ? this.o.where() : 'notification';
    m.at = this.now(); m.where = where; m.outcome = null;
    this.sent.push(m); if (this.sent.length > 50) this.sent.shift();
    this.stats.delivered++;
    try { out.chat && out.chat(m); } catch (e) { this.log('voice: chat outlet failed', e); }
    try { (out[where] || out.notification || (() => {}))(m); } catch (e) { this.log('voice: ' + where + ' outlet failed', e); }
  }
  find(id) { return this.sent.find((m) => m.id === id) || null; }
  // Ben reacted to a message. kind: 'up' (👍), 'down' (👎 not now), 'used' (clicked it / opened chat from it), 'reply'
  feedback(id, kind) {
    const m = id ? this.find(id) : this.latestOpen();
    if (!m || m.outcome) return null;
    m.outcome = kind; m.outcomeAt = this.now();
    try { this.o.onOutcome && this.o.onOutcome(m, kind); } catch (e) { this.log('voice: outcome failed', e); }
    return m;
  }
  latestOpen() { for (let i = this.sent.length - 1; i >= 0; i--) if (!this.sent[i].outcome && this.now() - this.sent[i].at < this.ignoreMs) return this.sent[i]; return null; }
  // Ben's next chat message: "not now / stop / later / shh" = a strong no for the latest open message; any other reply = yes
  onBenChat(text) {
    const m = this.latestOpen();
    if (!m) return null;
    return this.feedback(m.id, NOT_NOW.test(String(text || '')) ? 'notnow' : 'reply');
  }
  // messages nobody touched for ignoreMs become "ignored" (a weak no). Call on the 1 s clock.
  sweep() {
    const now = this.now(); let n = 0;
    for (const m of this.sent) if (!m.outcome && now - m.at >= this.ignoreMs) { this.feedback(m.id, 'ignored'); n++; }
    return n;
  }
}
const NOT_NOW = /\b(?:not\s+now|stop(?:\s+(?:it|that|talking))?|later|shh+|be\s+quiet|quiet|go\s+away|leave\s+me\s+alone|don'?t\s+(?:bother|interrupt)|busy)\b/i;

module.exports = { route, statusIcon, Voice, NOT_NOW, SURPRISE_SHOW_MS, QUIET_MS, HOLD_MAX_MS, IGNORE_MS };
