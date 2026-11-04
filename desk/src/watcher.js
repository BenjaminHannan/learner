'use strict';
// T6 (2026-11-04): the WATCHER, a tiny neural net beside the guesser (src/guesser.js) that looks at cheap input features every second
// and scores "worth waking the big brain?". It is trained ONLY in sleep, from the day's own logs: each second's features, and whether
// the always-on tick that later read those seconds turned out useful (a say that got 👍 / was used / got a reply, a note that became
// confirmed). Automatic and mathematical: nothing here decides what is stored; the labels come from what happened.
//   day:   observe(row) every second -> score; logged compactly (changed seconds + every 10th quiet one)
//   ticks: tickRead(t0, t1, refs)  after each tick (which seconds it read);  outcome(ref, useful)  when Ben's reaction / a note settles
//   night: nightly() -> replay the last days, train a candidate, SEATBELT (held-out newest day + older days, average precision; the
//          first model must beat the guesser's own surprise), keep or roll back, log the decision. No model = the guesser alone.
//   wake:  wakeNow(score) only with an accepted model, above the threshold fitted at night to the false-wake budget, with a cooldown.
// Toy evidence: premonition-sleeplab-t6 (REPORT.md). Real-Glim benefit: untested until real nights are logged.
const fs = require('fs');
const path = require('path');
const { MLP, rng, sigmoid, softmax, averagePrecision } = require('./tinynet');
const { screenCategory, soundCategory } = require('./guesser');

const APP = ['code', 'browser', 'video', 'game', 'chat', 'docs', 'school', 'other'];
const SCREEN = ['error', 'code', 'video', 'reading', 'chat', 'game', 'quiet', 'other'];
const SOUND = ['speech', 'music', 'video', 'quiet', 'other'];
const N = APP.length + SCREEN.length + SOUND.length + 7 + 3 + 4 + 1;
const ERR = /\b(?:error|exception|traceback|failed|cannot|undefined is not|syntaxerror|typeerror)\b/i;
const DEAD = /\b(?:deadline|due|overdue|appointment|meeting|exam|quiz|tonight|tomorrow|in \d+ ?(?:min|minutes|hours?))\b/i;
const NAME = /\bben\b|@ben\b/i;
const DEFAULTS = { hidden: 16, steps: 1500, batch: 64, posFrac: 0.2, lr: 0.003, auxW: 0.3, tol: 0.02, days: 7, fwPerHour: 12, cooldownS: 10, maxRowsPerDay: 30000, minPos: 5 };
const dayKey = (t) => { const d = new Date(t); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const round = (v) => Math.round(v * 1000) / 1000;
function wordsChanged(a, b) {
  const A = new Set(String(a || '').toLowerCase().split(/\s+/).filter(Boolean)), B = String(b || '').toLowerCase().split(/\s+/).filter(Boolean);
  if (!B.length) return A.size ? 1 : 0; let n = 0; for (const w of B) if (!A.has(w)) n++; return n / B.length;
}
function oneHot(list, v, x, off) { const i = list.indexOf(v); x[off + (i < 0 ? list.length - 1 : i)] = 1; return off + list.length; }

// one second of raw cheap inputs -> the stored row (numbers only; no words are stored)
// raw: {t, app (category), screenText (latest), soundText (latest), level (0..1, 0 if unknown), kl (guesser surprise this second)}
class Featurizer {
  constructor() { this.prevScreen = ''; this.prevRow = null; this.hist = []; this.seenTexts = new Map(); }
  row(raw) {
    const t = raw.t, scr = String(raw.screenText || ''), snd = String(raw.soundText || '');
    const changed = scr !== this.prevScreen;
    const key = scr.slice(0, 300).toLowerCase();
    for (const [k, at] of this.seenTexts) if (t - at > 600000) this.seenTexts.delete(k);
    const seen = changed && key && this.seenTexts.has(key) ? 1 : 0;
    if (changed && key) this.seenTexts.set(key, t);
    const fresh = changed ? scr : '';
    const r = { t, app: APP.includes(raw.app) ? raw.app : 'other', screen: screenCategory(scr), sound: soundCategory(snd),
      diff: changed ? round(wordsChanged(this.prevScreen, scr)) : 0, level: round(Number(raw.level) || 0),
      fErr: ERR.test(fresh) ? 1 : 0, fDead: DEAD.test(fresh) ? 1 : 0, fName: NAME.test(fresh) ? 1 : 0, fQ: /\?/.test(fresh) ? 1 : 0, seen,
      kl: round(Number(raw.kl) || 0) };
    this.prevScreen = scr;
    return r;
  }
}
// rows (consecutive seconds) -> feature vectors (the same list as the toy: watcher/features.js)
function vectors(rows) {
  const out = [];
  for (let t = 0; t < rows.length; t++) {
    const s = rows[t], p = rows[t - 1] || s, x = new Float64Array(N);
    let o = 0; o = oneHot(APP, s.app, x, o); o = oneHot(SCREEN, s.screen, x, o); o = oneHot(SOUND, s.sound, x, o);
    x[o++] = s.diff; x[o++] = s.level; x[o++] = s.fErr; x[o++] = s.fDead; x[o++] = s.fName; x[o++] = s.fQ; x[o++] = s.seen;
    x[o++] = s.app !== p.app ? 1 : 0; x[o++] = s.screen !== p.screen ? 1 : 0; x[o++] = s.level - p.level;
    let md = 0, sw = 0, fl = 0; const ds = new Set();
    for (let k = Math.max(0, t - 9); k <= t; k++) { md += rows[k].diff; ds.add(rows[k].screen); }
    for (let k = Math.max(1, t - 29); k <= t; k++) { if (rows[k].app !== rows[k - 1].app) sw++; fl += rows[k].fErr + rows[k].fDead + rows[k].fName + rows[k].fQ; }
    x[o++] = md / Math.min(10, t + 1); x[o++] = sw / 10; x[o++] = ds.size / 8; x[o++] = fl / 30;
    x[o++] = 1 - Math.exp(-(s.kl || 0));
    out.push(x);
  }
  return out;
}

class Watcher {
  // o: { dir, now, log, cfg }
  constructor(o) {
    this.o = o || {}; this.dir = path.join(this.o.dir || '.', 'watcher'); this.now = this.o.now || Date.now; this.log = this.o.log || (() => {});
    this.cfg = { ...DEFAULTS, ...(this.o.cfg || {}) };
    this.feat = new Featurizer(); this.rows = []; this.lastWake = 0; this.quiet = 0; this.pendingRows = []; this.lastScore = 0;
    this.model = null; this.threshold = Infinity;
    try { fs.mkdirSync(this.dir, { recursive: true }); } catch (e) { /* later */ }
    const j = readJson(path.join(this.dir, 'model.json'));
    if (j && j.net && Number.isFinite(j.threshold)) { try { this.model = MLP.fromJSON(j.net); this.threshold = j.threshold; this.meta = j.meta || {}; } catch (e) { this.model = null; } }
  }
  ready() { return !!this.model; }
  // every second: -> {score (0..1 or null without a model), wake (bool)}
  observe(raw) {
    const r = this.feat.row({ t: this.now(), ...raw });
    this.rows.push(r); if (this.rows.length > 40) this.rows.shift();
    const changed = this.rows.length < 2 || ['app', 'screen', 'sound', 'diff', 'fErr', 'fDead', 'fName', 'fQ', 'seen'].some((k) => r[k] !== this.rows[this.rows.length - 2][k]) || r.kl > 0.05;
    if (changed || ++this.quiet >= 10) { this.quiet = 0; this.pendingRows.push(r); if (this.pendingRows.length >= 60) this.flush(); }
    if (!this.model) return { score: null, wake: false };
    const xs = vectors(this.rows), z = this.model.forward(xs[xs.length - 1]).o[0];
    this.lastScore = sigmoid(z);
    const wake = z >= this.threshold && r.t - this.lastWake >= this.cfg.cooldownS * 1000;
    if (wake) this.lastWake = r.t;
    return { score: this.lastScore, wake };
  }
  flush() {
    if (!this.pendingRows.length) return;
    const f = path.join(this.dir, 'rows-' + dayKey(this.pendingRows[0].t) + '.jsonl');
    try {
      let n = 0; try { n = fs.statSync(f).size / 120; } catch (e) { /* new */ }
      if (n < this.cfg.maxRowsPerDay) fs.appendFileSync(f, this.pendingRows.map((r) => JSON.stringify(r)).join('\n') + '\n');
    } catch (e) { this.log('watcher: rows not saved', e); }
    this.pendingRows = [];
  }
  // a tick read the seconds [t0, t1]; ref links it to a later outcome (a say id or a note text). useful: null = not known yet
  tickRead(t0, t1, ref, useful) { this.append('ticks', { t0, t1, ref: ref == null ? null : String(ref).slice(0, 200), useful: useful == null ? null : !!useful, at: this.now() }); }
  outcome(ref, useful) { if (ref != null) this.append('ticks', { ref: String(ref).slice(0, 200), useful: !!useful, at: this.now(), outcome: true }); }
  append(kind, o) { this.flush(); try { fs.appendFileSync(path.join(this.dir, kind + '-' + dayKey(this.now()) + '.jsonl'), JSON.stringify(o) + '\n'); } catch (e) { this.log('watcher: ' + kind + ' not saved', e); } }

  // ---- night ----------------------------------------------------------------------------------------------------------
  // labelled days: for each day, rows sorted by t with y: 1 = inside a useful tick's window, 0 = inside a settled not-useful window,
  // rows no tick read (or whose tick never settled) are left out.
  labelledDays() {
    let files = []; try { files = fs.readdirSync(this.dir).filter((n) => /^rows-\d{4}-\d{2}-\d{2}\.jsonl$/.test(n)).sort(); } catch (e) { return []; }
    files = files.slice(-this.cfg.days);
    return files.map((f) => {
      const day = f.slice(5, 15), rows = readLines(path.join(this.dir, f)).sort((a, b) => a.t - b.t);
      const ticks = readLines(path.join(this.dir, 'ticks-' + day + '.jsonl'));
      const settled = new Map(); for (const k of ticks) if (k.outcome && k.ref) settled.set(k.ref, k.useful);
      const wins = ticks.filter((k) => !k.outcome && Number.isFinite(k.t0) && Number.isFinite(k.t1)).map((k) => ({ t0: k.t0, t1: k.t1, useful: k.useful != null ? k.useful : k.ref != null && settled.has(k.ref) ? settled.get(k.ref) : null })).filter((w) => w.useful != null);
      const X = vectors(rows), items = [];
      // per row: is it inside any settled window, and inside a useful one? (sweep over windows sorted by start)
      wins.sort((a, b) => a.t0 - b.t0);
      let wi = 0; const open = [];
      rows.forEach((r, i) => {
        while (wi < wins.length && wins[wi].t0 <= r.t) open.push(wins[wi++]);
        for (let k = open.length - 1; k >= 0; k--) if (open[k].t1 < r.t) open.splice(k, 1);
        if (!open.length) return;
        // a useful tick: the seconds that carried something new (changed screen / a flag / a surprise) are the positives
        const useful = open.some((x) => x.useful), carried = r.diff > 0 || r.fErr || r.fDead || r.fName || r.kl > 0.3;
        items.push({ x: X[i], y: useful && carried ? 1 : 0, next: SCREEN.indexOf((rows[i + 1] || r).screen), sur: r.kl, t: r.t });
      });
      return { day, items };
    }).filter((d) => d.items.length);
  }
  nightly(opts) {
    opts = opts || {}; this.flush();
    const days = opts.days || this.labelledDays(), r = rng(Number(String(this.now()).slice(-6)) || 1), cfg = this.cfg;
    const rec = { at: this.now(), kind: 'watcher-nightly', days: days.length };
    if (!days.length) return this.record({ ...rec, kept: false, why: 'no labelled days' });
    const newest = days[days.length - 1].items, split = Math.floor(newest.length * 0.8);
    const latest = newest.slice(split), anchor = [].concat(...days.slice(0, -1).map((d) => d.items.slice(Math.floor(d.items.length * 0.8))));
    const pool = [].concat(...days.slice(0, -1).map((d) => d.items.slice(0, Math.floor(d.items.length * 0.8))), newest.slice(0, split));
    const npos = pool.filter((p) => p.y).length;
    if (npos < cfg.minPos || latest.filter((p) => p.y).length < 1) return this.record({ ...rec, kept: false, why: 'too few useful moments (' + npos + ')' });
    const cand = trainNet(this.model ? this.model.clone() : new MLP(N, cfg.hidden, 1 + SCREEN.length, 7), pool, r, cfg);
    const ap = (scoreFn, set) => averagePrecision(set.map(scoreFn), set.map((i) => i.y));
    const netScore = (net) => (it) => net.forward(it.x).o[0], surScore = (it) => it.sur;
    const cL = ap(netScore(cand), latest), oL = ap(this.model ? netScore(this.model) : surScore, latest);
    const cA = anchor.length ? ap(netScore(cand), anchor) : null, oA = anchor.length ? ap(this.model ? netScore(this.model) : surScore, anchor) : null;
    // the first watcher must beat the guesser's surprise outright; later ones may not lose more than tol to the current watcher
    const latestOk = this.model ? cL >= oL - cfg.tol : cL > oL;
    // seatbelt v2 (toy control MARKS-watcher-seatbelt-v2: caught 60 % poison 3/3 where AP alone caught 2/3): the deployed quantity,
    // recall of labelled useful moments at the false-wake budget on the OLDER held-out days, may not drop by more than 5 points
    const rC = anchor.length ? budgetRecall(anchor, netScore(cand), cfg) : null, rO = anchor.length ? budgetRecall(anchor, this.model ? netScore(this.model) : surScore, cfg) : null;
    const keep = latestOk && (cA == null || cA >= oA - cfg.tol) && (rC == null || rC >= rO - 0.05);
    const out = { ...rec, kept: keep, apLatest: { cand: round(cL), old: round(oL) }, apAnchor: cA == null ? null : { cand: round(cA), old: round(oA) }, recallAnchor: rC == null ? null : { cand: round(rC), old: round(rO) }, against: this.model ? 'previous watcher' : 'guesser surprise', pos: npos, n: pool.length };
    if (!keep) return this.record({ ...out, why: 'seatbelt: candidate not better / worse on held-out; rolled back' });
    // wake threshold: on the held-out seconds, the lowest logit whose false wakes (y=0 scored above it) stay within the budget
    // fitted on the older held-out days when there are enough (today's labels are the least checked), else on today's held-out
    const held = anchor.length >= 600 ? anchor : latest.concat(anchor), ht = held.map((i) => i.t).sort((a, b) => a - b);
    let span = 0; for (let i = 1; i < ht.length; i++) span += Math.min(ht[i] - ht[i - 1], 10000);   // rows are subsampled: use real time
    const hours = Math.max(1 / 6, span / 3600000);
    const neg = held.filter((i) => !i.y).map((i) => cand.forward(i.x).o[0]).sort((a, b) => b - a);
    const allow = Math.max(1, Math.floor(cfg.fwPerHour * hours));
    const threshold = neg.length > allow ? neg[allow - 1] + 1e-9 : (neg.length ? neg[neg.length - 1] : 0);
    const prev = path.join(this.dir, 'model.json');
    try { if (fs.existsSync(prev)) fs.copyFileSync(prev, path.join(this.dir, 'model.prev.json')); } catch (e) { /* first */ }
    writeJson(prev, { net: cand.toJSON(), threshold, meta: { at: this.now(), apLatest: cL, n: pool.length } });
    this.model = cand; this.threshold = threshold;
    return this.record({ ...out, threshold: round(threshold) });
  }
  // put yesterday's model back (manual / test use)
  rollback() { const p = path.join(this.dir, 'model.prev.json'), j = readJson(p); if (!j) return false; writeJson(path.join(this.dir, 'model.json'), j); this.model = MLP.fromJSON(j.net); this.threshold = j.threshold; this.record({ at: this.now(), kind: 'watcher-rollback' }); return true; }
  record(o) { try { fs.appendFileSync(path.join(this.dir, 'nightly.jsonl'), JSON.stringify(o) + '\n'); } catch (e) { /* log only */ } this.log('watcher nightly: ' + JSON.stringify(o)); return o; }
  // old logs beyond the replay window are deleted (numbers only, but keep disk small)
  prune() { try { const keep = new Set(fs.readdirSync(this.dir).filter((n) => /^rows-/.test(n)).sort().slice(-this.cfg.days).map((n) => n.slice(5, 15))); for (const n of fs.readdirSync(this.dir)) { const m = /^(?:rows|ticks)-(\d{4}-\d{2}-\d{2})\.jsonl$/.exec(n); if (m && !keep.has(m[1])) fs.unlinkSync(path.join(this.dir, n)); } } catch (e) { /* next night */ } }
}
// recall of labelled useful moments (runs of y=1 rows) when waking at score >= th with a cooldown, at the best th whose false wakes
// (wakes not within 10 s after a moment's start) stay within cfg.fwPerHour over the items' time span. Items: {t, y}, any day order.
function budgetRecall(items, scoreFn, cfg) {
  const its = items.slice().sort((a, b) => a.t - b.t), sc = its.map(scoreFn), ev = [];
  its.forEach((it, i) => { if (it.y && !(i && its[i - 1].y && it.t - its[i - 1].t <= 2000)) ev.push(it.t); });
  if (!ev.length) return null;
  let span = 0; for (let i = 1; i < its.length; i++) span += Math.min(its[i].t - its[i - 1].t, 10000);
  const allow = cfg.fwPerHour * Math.max(span, 600000) / 3600000;
  const ths = Array.from(new Set(sc.slice().sort((a, b) => b - a).filter((_, i, a) => i % Math.max(1, Math.floor(a.length / 300)) === 0)));
  let best = 0;
  for (const th of ths) {
    let last = -1e15, fw = 0; const hit = new Set();
    for (let i = 0; i < its.length; i++) {
      if (sc[i] < th || its[i].t - last < cfg.cooldownS * 1000) continue; last = its[i].t;
      let k = -1; for (let e = 0; e < ev.length; e++) if (its[i].t >= ev[e] && its[i].t < ev[e] + 10000) { k = e; break; }
      if (k >= 0) hit.add(k); else fw++;
    }
    if (fw <= allow) best = Math.max(best, hit.size / ev.length);
  }
  return best;
}
function trainNet(net, pool, r, cfg) {
  const pos = pool.filter((p) => p.y), neg = pool.filter((p) => !p.y);
  const lossGrad = (o, it) => { const d = new Float64Array(o.length); d[0] = sigmoid(o[0]) - it.y; const p = softmax(o, 1, 1 + SCREEN.length); for (let k = 0; k < SCREEN.length; k++) d[1 + k] = cfg.auxW * (p[k] - (k === it.next ? 1 : 0)); return d; };
  for (let s = 0; s < cfg.steps; s++) {
    const b = []; for (let i = 0; i < cfg.batch; i++) b.push(pos.length && (r() < cfg.posFrac || !neg.length) ? pos[Math.floor(r() * pos.length)] : neg[Math.floor(r() * neg.length)]);
    net.step(b, lossGrad, cfg.lr, 1e-4);
  }
  return net;
}
function readJson(p) { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return null; } }
function writeJson(p, v) { const tmp = p + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(v)); fs.renameSync(tmp, p); }
function readLines(p) { try { return fs.readFileSync(p, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean); } catch (e) { return []; } }

module.exports = { Watcher, Featurizer, vectors, trainNet, budgetRecall, N, APP, SCREEN, SOUND, DEFAULTS };
