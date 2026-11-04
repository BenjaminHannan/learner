'use strict';
// The idle / break stream of the when-model (sleep track T1, 2026-11-04): "will Ben take a break in the next 5 minutes?"
// A break = no keyboard/mouse input for 2+ minutes. Beta counts per (hour of day, minutes into the current active stretch, 2-minute
// buckets), backing off to the stretch bucket alone and then to the overall rate. Pure counting, no model. Old habits fade at night
// by a keep that sleep LEARNS (src/sleepjudges.js), not a fixed 0.8. It feeds imagine.js breakSoon (null before it has data).
// Toy result (premonition-sleeplab-t1, v1): part of the guesser part that passed 3/3 seeds; real-Glim effect untested.
const SB = 2, SMAX = 60;            // 2-minute buckets, up to 2 hours of activity
const PRIOR_W = 2;                  // pseudo-counts borrowed from the coarser level
const IDLE_S = 120, SOON_MS = 5 * 60000;
const PRIVATE_WINDOW = /\b(?:private\s+browsing|incognito|inprivate|private\s+window)\b|\b(?:1password|bitwarden|lastpass|keychain\s+access|passwords)\b/i;
function privateRaw(raw) {   // lazy require: senses pulls in agent.js; if it cannot load, treat the window as private (keep nothing)
  const text = String(raw.app || '') + ' ' + String(raw.title || '');
  if (PRIVATE_WINDOW.test(text)) return true;
  try { return !!require('./senses').isPrivate(text); } catch (e) { return true; }
}
const sbucket = (sessMin) => Math.min(SMAX, Math.max(0, Math.floor((Number(sessMin) || 0) / SB)));
class BreakModel {
  constructor(saved) {
    this.ctx = {}; this.back = {}; this.all = [0, 0];
    if (saved && typeof saved === 'object') { this.ctx = saved.ctx || {}; this.back = saved.back || {}; this.all = Array.isArray(saved.all) ? saved.all.slice(0, 2) : [0, 0]; }
  }
  n() { return this.all[0] + this.all[1]; }
  // p(break starts in the next 5 min | hour, minutes into this active stretch)
  p(hour, sessMin) {
    const s = sbucket(sessMin), g = (this.all[0] + 0.1) / (this.all[0] + this.all[1] + 1);
    const b = this.back[s] || [0, 0], pb = (b[0] + PRIOR_W * g) / (b[0] + b[1] + PRIOR_W);
    const c = this.ctx[hour + '|' + s] || [0, 0];
    return (c[0] + PRIOR_W * pb) / (c[0] + c[1] + PRIOR_W);
  }
  observe(hour, sessMin, y) {
    const s = sbucket(sessMin), i = y ? 0 : 1;
    (this.ctx[hour + '|' + s] || (this.ctx[hour + '|' + s] = [0, 0]))[i] += 1;
    (this.back[s] || (this.back[s] = [0, 0]))[i] += 1;
    this.all[i] += 1;
  }
  decay(keep) {
    const k = Number(keep); if (!(k > 0 && k <= 1)) return;
    for (const m of [this.ctx, this.back]) for (const key of Object.keys(m)) m[key] = m[key].map((v) => v * k);
    this.all = this.all.map((v) => v * k);
  }
  toJSON() { return { ctx: this.ctx, back: this.back, all: this.all }; }
}

// One tick per minute with the Mac's idle seconds and the front app category. A minute's "break soon" label is known 5 min later;
// then the model learns it (online) and the row goes to onRow (the nightly replay log: {t, cat, work, sess, hour, soon}).
class BreakTracker {
  // o: { saved, onRow(row) }
  constructor(o) {
    o = o || {}; this.o = o; this.model = new BreakModel(o.saved && o.saved.model);
    this.since = (o.saved && o.saved.since) || null;    // start of the current active stretch (ms) or null while on a break
    this.q = [];                                          // active minutes waiting for their label
  }
  // raw: optional {app, title} the category was computed from (kept on the row so the night's truth check can recompute it)
  tick(t, idleS, cat, raw) {
    const active = Number(idleS) < IDLE_S, hour = new Date(t).getHours();
    if (active && this.since == null) this.since = t;
    if (!active && this.since != null) {                  // a break started (input stopped ~idleS ago)
      const tb = t - Number(idleS) * 1000;
      for (const r of this.q) if (tb > r.t && tb - r.t <= SOON_MS) r.soon = 1;
      this.since = null;
    }
    // resolve rows whose 5 minutes have passed (or all of them once a break started)
    while (this.q.length && (t - this.q[0].t >= SOON_MS || this.since == null)) this.emit(this.q.shift());
    // lead 2026-11-04: a private, incognito or password-type window keeps NO raw (the row is then just "unchecked" for the truth check)
    const rw = raw && (raw.app || raw.title) && !privateRaw(raw) ? { raw: { app: String(raw.app || '').slice(0, 60), title: String(raw.title || '').slice(0, 80) } } : {};
    if (active) this.q.push({ t, cat: cat || 'other', work: true, sess: Math.round((t - this.since) / 60000), hour, soon: 0, ...rw });
    else this.emit({ t, cat: cat || 'other', work: false, sess: -1, hour, soon: 0, ...rw });
  }
  emit(r) { if (r.work) this.model.observe(r.hour, r.sess, r.soon); try { this.o.onRow && this.o.onRow(r); } catch (e) { /* log only */ } }
  // the chance of a break in the next 5 min right now; null while unknown (on a break, or no data yet)
  breakSoon(t) { if (this.since == null || this.model.n() < 30) return null; return this.model.p(new Date(t).getHours(), (t - this.since) / 60000); }
  toJSON() { return { model: this.model.toJSON(), since: this.since }; }
}

module.exports = { BreakModel, BreakTracker, sbucket, IDLE_S };
