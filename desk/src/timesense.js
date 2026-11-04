'use strict';
// Ingredient "feeling time" (ingredients-plan.md step 3, app side). Pure Node, no model, no network.
//   - words for time: the clock line Nanbeige sees each tick, and "N min ago" for recalled notes and observations
//   - the WHEN guesser: per hour-of-week Dirichlet counts of the app category (like guesser.js), with backoff
//     hour-of-week -> hour-of-day -> any time. It answers "what is likely at this time" and gives TIME-SURPRISE:
//     the Bayesian surprise KL(Dir(after) || Dir(before)) of seeing this category in this hour-of-week bucket.
//     Something at an unusual time moves the bucket's beliefs a lot (high KL); the same thing at its usual time barely does.
//   - simple time questions from timestamped records: "how long ago did I ...?", "what happened right before ...?"
// Records with no timestamp are "time unknown": they are shown as such and skipped by time questions, never a crash.
// guesser.js requires this file, so its KL is looked up lazily (no circular-require surprise)
const klDirichlet = (a, b) => require('./guesser').klDirichlet(a, b);

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const validT = (t) => typeof t === 'number' && Number.isFinite(t) && t > 0;
// an old record's time: a number of ms, or null ("unknown"). Accepts ISO strings too (old files).
function timeOf(x) {
  if (x == null) return null;
  const v = typeof x === 'object' ? (x.t != null ? x.t : x.at != null ? x.at : x.settledAt) : x;
  if (validT(v)) return v;
  if (typeof v === 'string' && v) { const p = Date.parse(v); return Number.isFinite(p) && p > 0 ? p : null; }
  return null;
}
const pad = (n) => String(n).padStart(2, '0');
const hhmm = (t) => { const d = new Date(t); return pad(d.getHours()) + ':' + pad(d.getMinutes()); };
// "Wed 4 Nov, 14:05" (local time)
function clockWords(t) { const d = new Date(t); return DAYS[d.getDay()] + ' ' + d.getDate() + ' ' + MONTHS[d.getMonth()] + ', ' + hhmm(t); }
// "just now", "4 min ago", "2 h ago", "3 days ago"; null/invalid -> "time unknown"; a future time (clock change) -> "just now"
function ago(t, now) {
  if (!validT(t)) return 'time unknown';
  const m = Math.max(0, ((now || Date.now()) - t) / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return Math.round(m) + ' min ago';
  const h = m / 60;
  if (h < 24) return (h < 10 ? Math.round(h * 2) / 2 : Math.round(h)) + ' h ago';
  const d = Math.round(h / 24);
  return d + ' day' + (d === 1 ? '' : 's') + ' ago';
}
// "[14:05, 3 min ago]" or "[time unknown]"
const stampWords = (t, now) => (validT(t) ? hhmm(t) + ', ' + ago(t, now) : 'time unknown');
const hourOfWeek = (t) => { const d = new Date(t); return d.getDay() * 24 + d.getHours(); };
const dayKey = (t) => { const d = new Date(t); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); };

// ---- the WHEN guesser ---------------------------------------------------------------------------------------------------
const PRIOR_TOTAL = 0.5;    // pseudo-counts of a brand-new model, spread over the categories
const BACKOFF_MAX = 6;      // a new bucket borrows at most this many counts from the coarser model (small: time-specific evidence wins fast)
const DWELL_MS = 10 * 60000; // staying in the same category is counted again only every 10 minutes (the app is re-read every second)

class WhenModel {
  constructor(cats, saved) {
    this.cats = cats.slice(); this.how = {}; this.hod = {}; this.all = null; this.last = null;
    if (saved && Array.isArray(saved.cats) && saved.cats.join() === this.cats.join()) {
      const ok = (m) => (m && typeof m === 'object' ? m : {});
      this.how = ok(saved.how); this.hod = ok(saved.hod); this.all = Array.isArray(saved.all) && saved.all.length === this.cats.length ? saved.all : null;
      this.last = saved.last && validT(saved.last.t) ? saved.last : null;
    }
  }
  fresh() { return this.cats.map(() => PRIOR_TOTAL / this.cats.length); }
  borrow(from) {
    const b = from || this.fresh(); let tot = 0; for (const v of b) tot += v;
    const s = Math.min(1, BACKOFF_MAX / tot), f = this.fresh();
    return b.map((v, i) => Math.max(f[i], v * s));
  }
  // counts of the hour-of-week bucket of time t (made from the coarser models the first time; not stored until observed)
  bucket(t) {
    const w = String(hourOfWeek(t)), h = String(new Date(t).getHours());
    if (this.how[w]) return this.how[w];
    return this.borrow(this.hod[h] || this.borrow(this.all));
  }
  // what is likely at time t: {cat: p} and how much evidence that hour-of-week has (counts beyond the prior)
  predict(t) {
    const c = this.bucket(t); let tot = 0; for (const v of c) tot += v;
    const out = {}; this.cats.forEach((k, i) => { out[k] = c[i] / tot; });
    return { p: out, n: this.how[String(hourOfWeek(t))] ? tot : 0 };
  }
  // observe category cat at time t -> {kl, p, cat, hour} or null when it is the same category within the dwell time
  observe(cat, t) {
    let i = this.cats.indexOf(cat); if (i < 0) { i = this.cats.indexOf('other'); if (i < 0) i = this.cats.length - 1; }
    cat = this.cats[i];
    if (!validT(t)) return null;
    if (this.last && this.last.cat === cat && t - this.last.t < DWELL_MS && t >= this.last.t) return null;
    const w = String(hourOfWeek(t)), h = String(new Date(t).getHours());
    const before = this.bucket(t), after = before.slice(); after[i] += 1;
    let tot = 0; for (const v of before) tot += v;
    const kl = klDirichlet(after, before), p = before[i] / tot;
    this.how[w] = after;
    const hd = this.hod[h] || (this.hod[h] = this.borrow(this.all)); hd[i] += 1;
    const al = this.all || (this.all = this.fresh()); al[i] += 1;
    this.last = { cat, t };
    return { kl, p, cat, hour: Number(w) };
  }
  likely(t, k) {
    const { p, n } = this.predict(t);
    return { n, top: Object.entries(p).sort((a, b) => b[1] - a[1]).slice(0, k || 2) };
  }
  decay(keep) {
    const f = this.fresh();
    for (const m of [this.how, this.hod]) for (const k of Object.keys(m)) m[k] = m[k].map((v, i) => Math.max(f[i], v * keep));
    if (this.all) this.all = this.all.map((v, i) => Math.max(f[i], v * keep));
  }
  toJSON() { return { cats: this.cats, how: this.how, hod: this.hod, all: this.all, last: this.last }; }
}

// "Usually at this time: code 62%." (only once that hour-of-week has some evidence of its own), else ''
function likelyWords(model, t) {
  if (!model) return '';
  const { n, top } = model.likely(t, 2);
  if (n < 3 || !top.length || top[0][1] < 0.35) return '';
  return 'Usually at this time: ' + top.filter((x, i) => i === 0 || x[1] >= 0.2).map(([c, p]) => c + ' ' + Math.round(p * 100) + '%').join(', ') + '.';
}

// ---- simple time questions -----------------------------------------------------------------------------------------------
const ASK = /\bhow\s+long\s+ago\b|\bhow\s+long\s+(?:has\s+it\s+been|since)\b|\bwhen\s+did\s+(?:i|you|we)\b|\bwhat\s+(?:happened|did\s+i\s+do|was\s+i\s+doing|came)\s+(?:right\s+|just\s+|straight\s+)?(?:before|after)\b|\bwhat\s+was\s+(?:i\s+doing\s+)?(?:right\s+|just\s+)?before\b/i;
const isTimeAsk = (text) => ASK.test(String(text || ''));
const QSTOP = new Set('how long ago since has it been when did what happened was doing do came right just straight before after the a an i me my you we did to of at on in it is was were be for and or that this glim'.split(' '));
const qwords = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter((w) => w.length > 1 && !QSTOP.has(w));
const stem = (w) => w.replace(/(?:ing|ed|es|s)$/, '');
function matchScore(q, text) {
  const Q = [...new Set(qwords(q).map(stem))]; if (!Q.length) return 0;
  const T = new Set(qwords(text).map(stem));
  let n = 0; for (const w of Q) if (T.has(w)) n++;
  return n / Q.length;
}
// records: [{t, text, kind?}] (any order; records without a time are skipped). -> {kind, answer, target, before?, after?} or null
function answerTimeQuestion(question, records, now) {
  now = now || Date.now();
  const q = String(question || '');
  const recs = (records || []).filter((r) => r && validT(r.t) && typeof r.text === 'string' && r.text.trim()).sort((a, b) => a.t - b.t);
  if (!recs.length) return null;
  const m = /\b(before|after)\b\s+(.*)$/i.exec(q);
  const dir = m && /\bwhat\b/i.test(q.slice(0, m.index)) ? m[1].toLowerCase() : null;
  const about = dir ? m[2] : q;
  // the best match; ties go to the most recent one
  let best = null, bs = 0;
  for (const r of recs) { const s = matchScore(about, r.text); if (s > 0 && s >= bs) { bs = s; best = r; } }
  if (!best || bs < 0.5) return null;
  if (dir === 'before' || dir === 'after') {
    const same = (r) => r.text.trim().toLowerCase() === best.text.trim().toLowerCase();
    let other = null;
    if (dir === 'before') { for (const r of recs) if (r.t < best.t && !same(r)) other = r; }
    else other = recs.find((r) => r.t > best.t && !same(r)) || null;
    if (!other) return { kind: dir, target: best, answer: 'I have nothing recorded ' + dir + ' "' + best.text.slice(0, 80) + '" (' + clockWords(best.t) + ').' };
    const gap = Math.round(Math.abs(best.t - other.t) / 60000);
    return { kind: dir, target: best, [dir]: other, answer: 'Right ' + dir + ' "' + best.text.slice(0, 80) + '" (' + clockWords(best.t) + '), ' + (gap < 1 ? 'less than a minute ' + (dir === 'before' ? 'earlier' : 'later') : gap + ' min ' + (dir === 'before' ? 'earlier' : 'later')) + ': "' + other.text.slice(0, 120) + '" (' + clockWords(other.t) + ').' };
  }
  return { kind: 'ago', target: best, answer: 'That was ' + ago(best.t, now) + ' (' + clockWords(best.t) + '): "' + best.text.slice(0, 120) + '".' };
}

module.exports = { timeOf, validT, clockWords, ago, stampWords, hhmm, hourOfWeek, dayKey, WhenModel, likelyWords, isTimeAsk, answerTimeQuestion, matchScore, DWELL_MS, BACKOFF_MAX };
