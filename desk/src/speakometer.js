'use strict';
// Always-on v2, phase 2: the speak-o-meter. A tiny separate model (logistic regression over hand-made features, plain JS) that
// answers one question: should Glim speak right now? It is never the 3B brain, and it sits ON TOP of the code-enforced limits
// (Ben first, memory pressure, the night window, the 20-minute rate limit); it can only make Glim quieter, never louder than those.
//
// Feedback (strongest first): Ben says "not now / stop / later / shh" (strong no) > 👎 not now (no) > ignored for 10 min (weak no);
// a reply, 👍, or clicking through to the help = yes. Every event is logged with its features (userData/speakometer-events.jsonl),
// learned from at once (one small gradient step), and the whole log is refit each night in the sleep window.
// It starts permissive for "stuck" moments (the same error seen 3+ times, the same page for 10+ min) and quiet otherwise.
const fs = require('fs');
const path = require('path');

// ---- what is on screen, what Ben is doing -------------------------------------------------------------------------
const CATS = ['code', 'browser', 'video', 'game', 'chat', 'docs', 'school', 'other'];
const CAT_RULES = [
  ['video', /\b(?:youtube|netflix|twitch|vlc|quicktime|iina|disney\+?|hulu|prime video|plex|tv)\b/i],
  ['game', /\b(?:minecraft|steam|roblox|lunar client|badlion|fortnite|valorant|league of legends|epic games|game|bedwars|hypixel)\b/i],
  ['school', /\b(?:schoology|canvas|google classroom|khan academy|quizlet|college ?board|ap classroom|desmos|delta math)\b/i],
  ['code', /\b(?:visual studio code|vs ?code|code|cursor|xcode|terminal|iterm2?|warp|ghostty|pycharm|intellij|sublime|vim|t3 code|github)\b/i],
  ['chat', /\b(?:messages|discord|slack|whatsapp|telegram|facetime|zoom|teams|mail|gmail|outlook)\b/i],
  ['docs', /\b(?:pages|word|google docs|notion|obsidian|notes|preview|pdf|keynote|powerpoint|excel|numbers|sheets)\b/i],
  ['browser', /\b(?:safari|chrome|google chrome|firefox|arc|edge|brave|opera)\b/i]
];
// app name (+ window title) -> one of CATS. The title wins for browsers (a YouTube tab in Chrome is "video").
function categorize(app, title) {
  const a = String(app || ''), t = String(title || '');
  for (const [c, re] of CAT_RULES) if (c !== 'browser' && re.test(t) && /safari|chrome|firefox|arc|edge|brave|opera/i.test(a)) return c;
  for (const [c, re] of CAT_RULES) if (re.test(a)) return c;
  return a ? 'other' : 'other';
}
const ACTS = ['typing', 'video', 'game', 'idle', 'active'];
// idleS: seconds since the last key/mouse input on the Mac; typing: Desk's composer or input in the last 2 s
function activity({ idleS, typing, cat }) {
  if (typing) return 'typing';
  if (cat === 'video') return 'video';
  if (cat === 'game') return 'game';
  if (Number(idleS) >= 120) return 'idle';
  return 'active';
}

// ---- stuck signals ---------------------------------------------------------------------------------------------------
const ERROR_LINE = /[^.|;\n]*\b(?:error|exception|traceback|failed|failure|cannot|can't find|not found|undefined is not|segmentation fault|denied|invalid|unexpected token|syntaxerror|typeerror|referenceerror)\b[^.|;\n]*/gi;
const normErr = (s) => String(s).toLowerCase().replace(/\d+/g, '#').replace(/["'`].*?["'`]/g, '"…"').replace(/\s+/g, ' ').trim().slice(0, 120);
class Stuck {
  // the same error text 3+ times (in the last 30 min) / the same front page for 10+ minutes
  constructor(o) { o = o || {}; this.now = o.now || Date.now; this.errs = new Map(); this.page = { key: '', since: 0 }; this.winMs = o.winMs || 30 * 60000; }
  observe(sense, text) {
    const now = this.now(), t = String(text || '');
    if (sense === 'windows') {
      const m = /Front app: ([^.]+)\./.exec(t); const front = m ? m[1].trim() : '';
      const title = front ? (new RegExp('(?:Open: |; )' + front.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ' — ([^;]+?)(?:;|\\.$|$)').exec(t) || [])[1] || '' : '';
      const key = front + ' — ' + title;
      if (key !== this.page.key) this.page = { key, since: now, app: front, title };
    }
    const seenNow = new Set();
    for (const line of t.match(ERROR_LINE) || []) {
      const k = normErr(line); if (k.length < 6 || seenNow.has(k)) continue; seenNow.add(k);
      const e = this.errs.get(k) || { n: 0, times: [], text: line.trim().slice(0, 160) };
      e.times = e.times.filter((x) => now - x < this.winMs); e.times.push(now); e.n = e.times.length; this.errs.set(k, e);
    }
    if (this.errs.size > 200) for (const k of [...this.errs.keys()].slice(0, 100)) this.errs.delete(k);
  }
  error() { let best = null; for (const e of this.errs.values()) { const n = e.times.filter((x) => this.now() - x < this.winMs).length; if (n >= 3 && (!best || n > best.n)) best = { n, text: e.text }; } return best; }
  pageMinutes() { return this.page.since ? (this.now() - this.page.since) / 60000 : 0; }
  front() { return { app: this.page.app || '', title: this.page.title || '' }; }
}

// ---- features -----------------------------------------------------------------------------------------------------------
// ctx: { cat, act, minsSinceSay, urges: {bored, curious, share}, surprise (0..1), stuckError (bool), stuckPage (bool), urgent }
const NAMES = ['bias', ...CATS.map((c) => 'cat_' + c), ...ACTS.map((a) => 'act_' + a), 'since_say', 'urge_share', 'urge_curious', 'urge_bored', 'surprise', 'stuck_error', 'stuck_page', 'urgent'];
function features(ctx) {
  ctx = ctx || {};
  const x = {}; for (const n of NAMES) x[n] = 0;
  x.bias = 1;
  x['cat_' + (CATS.includes(ctx.cat) ? ctx.cat : 'other')] = 1;
  x['act_' + (ACTS.includes(ctx.act) ? ctx.act : 'active')] = 1;
  const mins = ctx.minsSinceSay == null ? 240 : Math.max(0, Number(ctx.minsSinceSay) || 0);
  x.since_say = Math.min(1, Math.log1p(mins) / Math.log1p(240));
  const u = ctx.urges || {};
  x.urge_share = clamp01(u.share); x.urge_curious = clamp01(u.curious); x.urge_bored = clamp01(u.bored);
  x.surprise = clamp01(ctx.surprise);
  x.stuck_error = ctx.stuckError ? 1 : 0; x.stuck_page = ctx.stuckPage ? 1 : 0; x.urgent = ctx.urgent ? 1 : 0;
  return x;
}
const clamp01 = (v) => Math.max(0, Math.min(1, Number(v) || 0));
// The starting weights: quiet by default (bias), permissive when stuck, quieter while typing / gaming / watching.
// Nov 4 (real-path check): with bias -1.2 + since_say 0.8 + surprise 0.6, plain browsing right after start-up (never spoken, a fresh
// guesser surprised by everything) scored p 0.55 and spoke. Now the worst ordinary moment (never spoken, full surprise, code page)
// stays below 0.5: -1.6 + 0.8 + 0.5 + 0.2 = -0.1. Stuck moments and a full share urge still get through.
const PRIOR = Object.freeze({ bias: -1.6, act_typing: -4.0, act_game: -2.0, act_video: -1.2, act_idle: -0.6, act_active: 0, since_say: 0.8, urge_share: 0.8, urge_curious: 0, urge_bored: 0, surprise: 0.5, stuck_error: 3.0, stuck_page: 1.8, urgent: 2.5, cat_code: 0.2, cat_school: 0.2 });
const prior = () => { const w = {}; for (const n of NAMES) w[n] = PRIOR[n] || 0; return w; };
// feedback kind -> label (1 = speak was right) and weight
const FEEDBACK = { notnow: { y: 0, w: 3 }, down: { y: 0, w: 2 }, ignored: { y: 0, w: 0.5 }, up: { y: 1, w: 2 }, reply: { y: 1, w: 1 }, used: { y: 1, w: 1.5 } };
const sig = (z) => 1 / (1 + Math.exp(-z));

class SpeakOMeter {
  // o: { dir (userData; omit for in-memory), now, threshold, lr, l2 }
  constructor(o) {
    o = o || {}; this.o = o; this.now = o.now || Date.now;
    this.threshold = o.threshold == null ? 0.5 : o.threshold; this.lr = o.lr || 0.35; this.l2 = o.l2 == null ? 0.02 : o.l2;
    this.file = o.dir ? path.join(o.dir, 'speakometer.json') : null;
    this.logFile = o.dir ? path.join(o.dir, 'speakometer-events.jsonl') : null;
    this.w = prior(); this.n = 0; this.refitAt = 0;
    if (this.file) { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (j && j.w) { for (const k of NAMES) if (Number.isFinite(j.w[k])) this.w[k] = j.w[k]; this.n = j.n | 0; this.refitAt = j.refitAt || 0; } } catch (e) { /* fresh */ } }
    this.mem = [];   // events, when there is no dir
  }
  score(x) { let z = 0; for (const n of NAMES) z += (this.w[n] || 0) * (x[n] || 0); return sig(z); }
  decide(ctx) { const x = features(ctx); const p = this.score(x); return { p, speak: p >= this.threshold, x }; }
  // Imagining ahead, level 1 (src/imagine.js): "speak now" vs "wait ~5 min". futures = [{w, ctx}] (the guesser's predicted next
  // state, e.g. the chance Ben takes a break soon). Defer when waiting is clearly better: the expected p later is >= p now + margin
  // AND a later moment would itself pass the threshold with >= 50% chance (else the wait would only end in a hold).
  // Never for urgent says; o.noLookahead (the re-check after the wait) decides plainly, so a say is deferred at most once.
  decideAhead(ctx, futures, o) {
    o = o || {};
    const now = this.decide(ctx);
    if ((ctx && ctx.urgent) || o.noLookahead || !Array.isArray(futures) || !futures.length) return { ...now, defer: false, pWait: null };
    let pWait = 0, pPass = 0, tot = 0;
    for (const f of futures) {
      const w = Math.max(0, Number(f.w) || 0); if (!w) continue;
      const pf = this.score(features({ ...ctx, ...f.ctx, urgent: false }));
      pWait += w * pf; if (pf >= this.threshold) pPass += w; tot += w;
    }
    pWait = tot ? pWait / tot : now.p; pPass = tot ? pPass / tot : 0;
    const margin = o.margin == null ? 0.15 : o.margin;
    const defer = pWait >= now.p + margin && pPass >= 0.5;
    return { ...now, speak: defer ? false : now.speak, defer, pWait, pPass, waitMs: o.waitMs || 5 * 60000 };
  }
  // one weighted gradient step on the log loss, with a pull back toward the prior (so one 👎 cannot silence it for ever)
  step(x, y, wt, lr) {
    const p = this.score(x), g = (p - y) * wt, P = prior();
    for (const n of NAMES) this.w[n] -= (lr || this.lr) * (g * (x[n] || 0) + this.l2 * (this.w[n] - P[n]));
  }
  // an outcome for a message that went out with features x. kind: notnow | down | ignored | up | reply | used
  learn(x, kind, extra) {
    const f = FEEDBACK[kind]; if (!f || !x) return null;
    const ev = { t: this.now(), kind, y: f.y, w: f.w, x, ...(extra || {}) };
    this.log(ev);
    this.step(x, f.y, f.w); this.n++; this.save();
    return ev;
  }
  log(ev) {
    if (!this.logFile) { this.mem.push(ev); return; }
    try { fs.mkdirSync(path.dirname(this.logFile), { recursive: true }); fs.appendFileSync(this.logFile, JSON.stringify(ev) + '\n'); } catch (e) { this.mem.push(ev); }
  }
  events(max) {
    let out = this.mem.slice();
    if (this.logFile) { try { out = fs.readFileSync(this.logFile, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean).concat(this.mem); } catch (e) { /* none yet */ } }
    return out.slice(-(max || 3000));
  }
  // nightly: refit from the prior over the whole log (several weighted passes), so the day's online steps are re-balanced
  refit(epochs) {
    const evs = this.events().filter((e) => e && e.x && FEEDBACK[e.kind]);
    this.w = prior();
    for (let ep = 0; ep < (epochs || 30); ep++) for (const e of evs) this.step(e.x, FEEDBACK[e.kind].y, FEEDBACK[e.kind].w, 0.1);
    this.refitAt = this.now(); this.save();
    return { events: evs.length, at: this.refitAt };
  }
  save() { if (!this.file) return; try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); fs.writeFileSync(this.file, JSON.stringify({ w: this.w, n: this.n, refitAt: this.refitAt })); } catch (e) { /* in memory still */ } }
}

module.exports = { SpeakOMeter, Stuck, features, categorize, activity, CATS, ACTS, NAMES, PRIOR, FEEDBACK, prior };
