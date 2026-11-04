'use strict';
// Always-on v2, phase 3: the tiny guesser. A cheap, always-running predictor (no LLM) that keeps a PROBABILITY DISTRIBUTION over
//   (a) the next frontmost app category, ticked about once a second on the latest windows-sense reading, and
//   (b) the next screen / sound category, ticked on each screen or hearing observation.
// Each stream is a Dirichlet-count model conditioned on (previous category, part of the day). A context seen for the first time
// borrows its starting counts from the same stream's previous-category model (backoff), so a new part of the day starts informed.
//
// Surprise is BAYESIAN surprise: KL( Dir(after) || Dir(before) ), how far one observation moves the guesser's beliefs, in nats.
// It is NOT raw prediction error: a steadily random source (static, shuffle, ads) stops moving the counts once they are large, so it
// stops being surprising, while a new regime (a category it never saw here) moves them a lot.
//   big surprise -> wake an always-on tick early and file the moment as a "surprise" observation; small -> nothing is saved.
// (c) facts: Learn quizzes record Glim's guess and confidence before checking; factSurprise() scores a confident miss.

const PRIOR_TOTAL = 0.5;      // pseudo-counts of a brand-new stream, spread over its categories
const BACKOFF_MAX = 50;       // a new (prev, part-of-day) context starts with at most this many borrowed counts
const BIG = 1.0;              // nats: a "big" surprise (wake + file)
const COOLDOWN_MS = 60000;    // at most one filed surprise per stream per minute

// ---- special functions ------------------------------------------------------------------------------------------------
// log Gamma (Lanczos, g=7) and digamma (recurrence + asymptotic series); accurate to ~1e-10 for x > 0
const LG = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313, -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7];
function lgamma(x) {
  if (x < 0.5) return Math.log(Math.PI / Math.abs(Math.sin(Math.PI * x))) - lgamma(1 - x);
  x -= 1; let a = LG[0]; const t = x + 7.5;
  for (let i = 1; i < 9; i++) a += LG[i] / (x + i);
  return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(a);
}
function digamma(x) {
  let r = 0;
  while (x < 6) { r -= 1 / x; x += 1; }
  const f = 1 / (x * x);
  return r + Math.log(x) - 0.5 / x - f * (1 / 12 - f * (1 / 120 - f * (1 / 252 - f * (1 / 240 - f / 132))));
}
// KL( Dir(a) || Dir(b) ) for two count vectors over the same categories
function klDirichlet(a, b) {
  let a0 = 0, b0 = 0; for (let i = 0; i < a.length; i++) { a0 += a[i]; b0 += b[i]; }
  let kl = lgamma(a0) - lgamma(b0);
  const da0 = digamma(a0);
  for (let i = 0; i < a.length; i++) kl += lgamma(b[i]) - lgamma(a[i]) + (a[i] - b[i]) * (digamma(a[i]) - da0);
  return Math.max(0, kl);
}

const partOfDay = (t) => Math.floor(new Date(t).getHours() / 6);   // 0 night, 1 morning, 2 afternoon, 3 evening

class Stream {
  // cats: the fixed category list of this stream
  constructor(name, cats, saved) {
    this.name = name; this.cats = cats.slice(); this.prev = null;
    this.ctx = {};     // "prev|part" -> counts[]
    this.back = {};    // "prev" -> counts[] (the backoff model, no part of day)
    if (saved && saved.cats && saved.cats.join() === this.cats.join()) { this.ctx = saved.ctx || {}; this.back = saved.back || {}; this.prev = saved.prev || null; }
  }
  fresh() { return this.cats.map(() => PRIOR_TOTAL / this.cats.length); }
  counts(key, backKey) {
    if (this.ctx[key]) return this.ctx[key];
    const b = this.back[backKey] || this.fresh();
    let tot = 0; for (const v of b) tot += v;
    const scale = Math.min(1, BACKOFF_MAX / tot);
    // borrowed counts are scaled down, and never below the brand-new prior (so nothing has probability ~0)
    return (this.ctx[key] = b.map((v, i) => Math.max(this.fresh()[i], v * scale)));
  }
  // the current belief about the next category: {cat: probability}
  predict(t) {
    const c = this.counts(String(this.prev) + '|' + partOfDay(t), String(this.prev));
    let tot = 0; for (const v of c) tot += v;
    const out = {}; this.cats.forEach((k, i) => { out[k] = c[i] / tot; });
    return out;
  }
  // observe a category at time t -> {kl, p (its predicted probability before), cat}
  observe(cat, t) {
    let i = this.cats.indexOf(cat); if (i < 0) { i = this.cats.indexOf('other'); if (i < 0) i = this.cats.length - 1; cat = this.cats[i]; }
    const pk = String(this.prev), key = pk + '|' + partOfDay(t);
    const before = this.counts(key, pk), after = before.slice(); after[i] += 1;
    let tot = 0; for (const v of before) tot += v;
    const kl = klDirichlet(after, before), p = before[i] / tot;
    this.ctx[key] = after;
    const b = this.back[pk] || (this.back[pk] = this.fresh()); b[i] += 1;
    this.prev = cat;
    return { kl, p, cat };
  }
  // nightly retune: old habits fade a little (counts x keep), so it can follow new routines; tiny contexts are dropped
  decay(keep) {
    for (const m of [this.ctx, this.back]) for (const k of Object.keys(m)) {
      m[k] = m[k].map((v) => Math.max(PRIOR_TOTAL / this.cats.length, v * keep));
    }
  }
  toJSON() { return { cats: this.cats, ctx: this.ctx, back: this.back, prev: this.prev }; }
}

const APP_CATS = ['code', 'browser', 'video', 'game', 'chat', 'docs', 'school', 'other'];
const SCREEN_CATS = ['error', 'code', 'video', 'reading', 'chat', 'game', 'quiet', 'other'];
const SOUND_CATS = ['speech', 'music', 'video', 'quiet', 'other'];

// screen words / heard words -> a category (cheap keyword rules; no model)
function screenCategory(text) {
  const t = String(text || '');
  if (!t.trim()) return 'quiet';
  if (/\b(?:error|exception|traceback|failed|cannot|undefined is not|syntaxerror|typeerror)\b/i.test(t)) return 'error';
  if (/\b(?:youtube|netflix|twitch|subscribe|views|watch later)\b/i.test(t)) return 'video';
  if (/\b(?:minecraft|bedwars|hypixel|health|inventory|respawn)\b/i.test(t)) return 'game';
  if (/[{};]|=>|\bfunction\b|\bconst\b|\bdef\b|\bimport\b|\breturn\b/.test(t)) return 'code';
  if (/\b(?:message|reply|sent|delivered|typing…|discord|imessage)\b/i.test(t)) return 'chat';
  if (t.split(/\s+/).length > 40) return 'reading';
  return 'other';
}
function soundCategory(text) {
  const t = String(text || '').replace(/^Heard:\s*/i, '');
  if (!t.trim()) return 'quiet';
  if (/♪|\[music\]|\(music\)|\blyrics?\b/i.test(t)) return 'music';
  if (/\b(?:subscribe|like and subscribe|this video|episode)\b/i.test(t)) return 'video';
  return 'speech';
}

class Guesser {
  // o: { now, saved (from toJSON), big (nats), cooldownMs, onBig({stream, cat, kl, p, t}) }
  constructor(o) {
    o = o || {}; this.o = o; this.now = o.now || Date.now; this.big = o.big || BIG; this.cooldownMs = o.cooldownMs == null ? COOLDOWN_MS : o.cooldownMs;
    const s = o.saved || {};
    this.streams = { app: new Stream('app', APP_CATS, s.app), screen: new Stream('screen', SCREEN_CATS, s.screen), sound: new Stream('sound', SOUND_CATS, s.sound) };
    // feeling time (src/timesense.js): with o.when, app observations also feed a per hour-of-week model of the app category.
    // Its Bayesian surprise is ADDED to the app stream's (two independent belief sets: the information gains add), so an app at an
    // unusual hour is a bigger surprise than the same app at its usual hour. Off by default (older callers and tests unchanged).
    this.when = o.when ? new (require('./timesense').WhenModel)(APP_CATS, s.when) : null;
    this.lastBig = {}; this.last = { kl: 0, at: 0, stream: null };
    this.recent = [];   // last ~120 surprises (for the speak-o-meter's 0..1 feature)
  }
  // feed one observation; returns {kl, p, cat, big}
  observe(stream, cat, t) {
    t = t || this.now();
    const s = this.streams[stream]; if (!s) return null;
    const r = s.observe(cat, t);
    if (this.when && stream === 'app') {
      const w = this.when.observe(r.cat, t);
      r.seqKl = r.kl; r.whenKl = w ? w.kl : 0; r.kl += r.whenKl;
      r.unusualTime = !!w && r.whenKl >= 0.5 && r.whenKl >= 0.4 * r.kl;   // a real part of the surprise is about WHEN
    }
    r.big = r.kl >= this.big && (!this.lastBig[stream] || t - this.lastBig[stream] >= this.cooldownMs);
    this.last = { kl: r.kl, at: t, stream, cat: r.cat };
    this.recent.push(r.kl); if (this.recent.length > 120) this.recent.shift();
    if (r.big) { this.lastBig[stream] = t; try { this.o.onBig && this.o.onBig({ stream, cat: r.cat, kl: r.kl, p: r.p, t, ...(r.unusualTime ? { unusualTime: true, whenKl: r.whenKl } : {}) }); } catch (e) { /* listener */ } }
    return r;
  }
  // an always-on observation {sense, text} -> the right streams
  observeEntry(e, front) {
    if (e.sense === 'screen') return this.observe('screen', screenCategory(e.text), e.t);
    if (e.sense === 'hearing') return this.observe('sound', soundCategory(e.text), e.t);
    return null;
  }
  predict(stream, t) { const s = this.streams[stream]; return s ? s.predict(t || this.now()) : null; }
  // the newest surprise squashed to 0..1 (a speak-o-meter feature): 1 - exp(-kl), fading over 2 minutes
  level() { const age = this.now() - this.last.at; if (!this.last.at || age > 120000) return 0; return (1 - Math.exp(-this.last.kl)) * (1 - age / 120000); }
  // what is likely at this hour of the week (feeling time); null without the when model
  likelyNow(t) { return this.when ? this.when.likely(t || this.now(), 2) : null; }
  decay(keep) { for (const s of Object.values(this.streams)) s.decay(keep == null ? 0.8 : keep); if (this.when) this.when.decay(keep == null ? 0.8 : keep); }
  toJSON() { const j = { app: this.streams.app.toJSON(), screen: this.streams.screen.toJSON(), sound: this.streams.sound.toJSON() }; if (this.when) j.when = this.when.toJSON(); else if (this.o.saved && this.o.saved.when) j.when = this.o.saved.when; return j; }
}

// (c) a fact guess made before checking: Bayesian-style surprise of the truth under the guess, in nats.
// A confident miss (confidence >= 0.7) belongs on the wonder list.
function factSurprise(confidence, correct) {
  const c = Math.max(0.01, Math.min(0.99, Number(confidence) || 0.5));
  const s = correct ? -Math.log(c) : -Math.log(1 - c);
  return { surprise: s, wonder: !correct && c >= 0.7 };
}

module.exports = { Guesser, Stream, klDirichlet, lgamma, digamma, factSurprise, screenCategory, soundCategory, partOfDay, APP_CATS, SCREEN_CATS, SOUND_CATS, BIG };
