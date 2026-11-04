'use strict';
// Sleep for the small judges (sleep track T1, 2026-11-04; plan: docs/sleep-improves-everything.md). ONE engine for every part:
//   replay the logged (prediction, truth) days -> update -> seatbelt -> keep or roll back, with a log line either way.
// Night D (the day that just ended is HELD OUT; older ADMITTED days train):
//   1. a day that looked suspicious on its night is admitted only if the next logged day ALSO contradicts the current model (the
//      world really changed); otherwise it was a bad log and is quarantined for good (never trains).
//   2. candidates = refit on the admitted days; the best on the held-out day.
//   3. suspicious = the candidate and the current model (once fitted) are both anti-predictive on the held-out day (their INVERTED
//      predictions win on more events than they do, frozen pass; a category stream: worse than knowing nothing) -> HOLD.
//   4. else keep the candidate only if its held-out loss <= the current model's; otherwise roll back.
// Automatic and mathematical: nothing here decides what is stored or learned beyond these fixed rules. No model calls.
// Parts here = the ones that PASSED the toy test (premonition-sleeplab-t1 v1, 3/3 seeds): the guesser's fade rates (app stream,
// when-model, idle/break stream), the think-longer threshold, where to look. Toy claims only; real-Glim effect untested.
// Toy limits: a flipped day is caught; a PARTIALLY wrong day (30%, 60% wrong labels) is not reliably caught by this held-out test.
// Partial poison: run(part, live, {truthcheck}) drops labels that fail a real truth first (src/truthcheck.js; guesser rows only).
const fs = require('fs');
const path = require('path');

const clip = (p, e) => Math.max(e || 1e-4, Math.min(1 - (e || 1e-4), p));
const bce = (p, y) => (y ? -Math.log(clip(p)) : -Math.log(clip(1 - p)));
const side = (l, li) => Math.sign(l - li);
const J = (x) => JSON.parse(JSON.stringify(x));
const mean = (xs) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : 0);
const dayIndex = (t) => { const d = new Date(t); return Math.round((new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime() - new Date(2026, 0, 1).getTime()) / 86400000); };
const MAX_DAYS = 40;

// ---- the engine (same rules as the toy lab's lab/engine.js) ---------------------------------------------------------------------
function best(part, cands, held) {
  let out = null;
  for (const c of cands || []) { const s = part.score(J(c.model), held); if (!out || s.loss < out.s.loss) out = { c, s }; }
  return out;
}
// st: {admitted, quarantined, pending, fitted, start}; logs: {day: rows}; live: today's live model (JSON). -> {rec, model}
function night(part, st, logs, D, live) {
  const rec = { day: D, part: part.name };
  st.admitted = st.admitted || []; st.quarantined = st.quarantined || []; st.pending = st.pending || [];
  const start = st.start || live;
  const old = part.score(J(start), logs[D]);
  rec.oldLoss = old.loss;
  for (const p of st.pending.filter((d) => d < D)) {
    const ok = old.gap > 0;
    st.pending = st.pending.filter((d) => d !== p);
    (ok ? st.admitted : st.quarantined).push(p);
    rec.decided = { day: p, admitted: ok };
  }
  st.admitted = st.admitted.filter((d) => logs[d]).sort((a, b) => a - b);
  const train = st.admitted.filter((d) => d < D);
  let model = live;
  if (!train.length) { st.admitted.push(D); rec.action = 'first day'; }
  else {
    const b = best(part, part.candidates(train.map((d) => logs[d]), logs[D], { days: train, D }), logs[D]);
    if (!b) { st.admitted.push(D); rec.action = 'no candidate'; }
    else {
      rec.newLoss = b.s.loss; rec.tag = b.c.tag; rec.trainDays = train.length;
      if (b.s.gap > 0 && (!st.fitted || old.gap > 0)) { st.pending.push(D); rec.action = 'hold'; }
      else {
        st.admitted.push(D);
        if (b.s.loss <= old.loss) { rec.action = 'kept'; model = part.deploy(b.c, live, logs[D], b.s); st.fitted = true; }
        else rec.action = 'rolled back';
      }
    }
  }
  st.start = J(model);
  return { rec, model };
}

// ---- part 1: the guesser's fade rates (app stream, when-model, idle stream), learned per stream from a small grid ------------------
const KEEPS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0];
function guesserPart() {
  const G = require('./guesser'), TS = require('./timesense'), { BreakModel } = require('./breaks');
  const make = (j) => ({ app: new G.Stream('app', G.APP_CATS, j && j.app), when: new TS.WhenModel(G.APP_CATS, j && j.when), idle: new BreakModel(j && j.idle) });
  const toJ = (m, k) => J({ app: m.app.toJSON(), when: m.when.toJSON(), idle: m.idle.toJSON(), k: k || { app: 1, when: 1, idle: 1 } });
  const decayAll = (m, k) => { m.app.decay(k.app); m.when.decay(k.when); m.idle.decay(k.idle); };
  function run(m, mins, frozen) {
    let la = 0, na = 0, lw = 0, nw = 0, li = 0, sg = 0, ni = 0; const q = [];
    for (const x of mins) {
      const P = m.app.predict(x.t); la += -Math.log(clip(P[x.cat] || 0)); na++; if (frozen) m.app.prev = x.cat; else m.app.observe(x.cat, x.t);
      const last = m.when.last;
      if (!(last && last.cat === x.cat && x.t - last.t < TS.DWELL_MS && x.t >= last.t)) { lw += -Math.log(clip(m.when.predict(x.t).p[x.cat] || 0)); nw++; if (frozen) m.when.last = { cat: x.cat, t: x.t }; else m.when.observe(x.cat, x.t); }
      while (!frozen && q.length && q[0].t + 5 * 60000 <= x.t) { const r = q.shift(); m.idle.observe(r.hour, r.sess, r.soon); }
      if (x.work) { const p = m.idle.p(x.hour, x.sess); li += bce(p, x.soon); sg += side(bce(p, x.soon), bce(1 - p, x.soon)); ni++; q.push(x); }
    }
    if (!frozen) for (const r of q) m.idle.observe(r.hour, r.sess, r.soon);
    const sub = { app: la / Math.max(1, na), when: lw / Math.max(1, nw), idle: li / Math.max(1, ni) };
    // suspicion: app stream vs uniform, idle stream by the sign test (NOT the when-model: one sample per hour-of-week per week)
    return { loss: (sub.app + sub.when + sub.idle) / 3, sub, gap: Math.max(sub.app - Math.log(G.APP_CATS.length), sg / Math.max(1, ni)), m };
  }
  return {
    name: 'guesser',
    score(mj, log) { const f = run(make(mj), log, true), r = run(make(mj), log); return { loss: r.loss, sub: r.sub, gap: f.gap, model: toJ(r.m, mj.k) }; },
    candidates(train, held, ctx) {
      const per = KEEPS.map((k) => {
        const m = make(null); let last = null;
        ctx.days.forEach((d, i) => { if (last != null) decayAll(m, { app: k ** (d - last), when: k ** (d - last), idle: k ** (d - last) }); run(m, train[i]); last = d; });
        decayAll(m, { app: k ** (ctx.D - last), when: k ** (ctx.D - last), idle: k ** (ctx.D - last) });
        return { k, j: toJ(m), s: run(make(toJ(m)), held) };
      });
      const pick = (st) => per.reduce((a, b) => (b.s.sub[st] < a.s.sub[st] - 1e-12 ? b : a), per[per.length - 1]);
      const pa = pick('app'), pw = pick('when'), pi = pick('idle');
      return [{ model: { app: pa.j.app, when: pw.j.when, idle: pi.j.idle, k: { app: pa.k, when: pw.k, idle: pi.k } }, tag: 'keep app ' + pa.k + ', when ' + pw.k + ', idle ' + pi.k }];
    },
    // the replay only CHOSE the rates: the live model fades by them (main applies c.k to the live guesser + break tracker)
    deploy: (c, live) => ({ ...J(live), k: { ...c.model.k } }),
    // truth: recompute the app category from the raw app name + title kept on the row (no raw: no truth)
    verify: require('./truthcheck').verifiers.category(require('./speakometer').categorize)
  };
}

// ---- part 2: the think-longer threshold (bored-mode experiments: extra tries only when the first try's confidence < theta) ------
const THETAS = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];
const EPS = 0.1, COST = 0.3;   // 10% exploration above theta (keeps the what-if data); 0.1 per extra try x 3 extra tries
const p1Of = (m, c) => { if (!m.p1) return 0.5; const b = m.p1[Math.min(9, Math.max(0, Math.floor(c * 10)))]; return (b[0] + 1) / (b[0] + b[1] + 2); };
// inverse-propensity estimate of a policy's mean loss (final answer wrong + extra-try cost) from logged rows {c, r1, extra, rK, pi}
function thLoss(theta, explore, log) {
  let L = 0;
  for (const it of log) { const f = it.extra ? ((1 - it.rK) + COST) / it.pi : 0; L += it.c < theta ? f : (explore ? (1 - EPS) * (1 - it.r1) + EPS * f : (1 - it.r1)); }
  return L / Math.max(1, log.length);
}
const thinkPart = () => ({
  name: 'think-longer',
  init: () => ({ theta: 1.0, explore: false, p1: null }),
  score(m, log) { return { loss: thLoss(m.theta, m.explore, log), gap: m.p1 ? mean(log.map((x) => side(bce(p1Of(m, x.c), x.r1), bce(1 - p1Of(m, x.c), x.r1)))) : 0, model: m }; },
  candidates(train) {
    const all = [].concat(...train);
    let b = null; for (const t of THETAS) { const L = thLoss(t, true, all); if (!b || L < b.L - 1e-12) b = { t, L }; }
    const p1 = Array.from({ length: 10 }, () => [0, 0]); for (const x of all) p1[Math.min(9, Math.max(0, Math.floor(x.c * 10)))][x.r1 ? 0 : 1]++;
    return [{ model: { theta: b.t, explore: true, p1 }, tag: 'theta ' + b.t }];
  },
  deploy: (c, live, held, s) => s.model
});
// should this experiment make its extra tries? (c = the first try's stated confidence; rnd = Math.random)
function thinkMore(m, c, rnd) { m = m || {}; const th = m.theta == null ? 1 : m.theta; if (c < th) return { extra: true, pi: 1 }; return { extra: !!m.explore && (rnd || Math.random)() < EPS, pi: EPS }; }

// ---- part 3: where to look: per-region surprise rate (Beta counts), the early-wake budget spent in proportion -----------------------
const R0 = [0.5, 4.5], RKEEPS = [0.5, 0.7, 0.8, 0.9, 0.95, 1.0], WAKE_BUDGET = 60, FLOOR = 2;
const rP = (m, r) => ((m.a[r] || 0) + R0[0]) / ((m.a[r] || 0) + (m.b[r] || 0) + R0[0] + R0[1]);
function rRun(m, reads, frozen) {
  let L = 0, S = 0;
  for (const x of reads) { const p = rP(m, x.r); L += bce(p, x.y); S += side(bce(p, x.y), bce(1 - p, x.y)); if (!frozen) { const k = x.y ? 'a' : 'b'; m[k][x.r] = (m[k][x.r] || 0) + 1; } }
  return { loss: L / Math.max(1, reads.length), sg: S / Math.max(1, reads.length), m };
}
const wherePart = () => ({
  name: 'where-to-look',
  init: () => ({ a: {}, b: {} }),
  score(m, log) { const f = rRun(J(m), log, true), r = rRun(J(m), log); return { loss: r.loss, gap: f.sg, model: r.m }; },
  candidates(train, held, ctx) {
    return RKEEPS.map((k) => { const m = { a: {}, b: {} };
      train.forEach((log, j) => { const w = k ** (ctx.D - ctx.days[j]); for (const x of log) { const key = x.y ? 'a' : 'b'; m[key][x.r] = (m[key][x.r] || 0) + w; } });
      return { model: m, tag: 'keep ' + k }; });
  },
  deploy: (c, live, held, s) => s.model
});
// a region's share of today's early-wake budget: FLOOR each, the rest in proportion to the learned surprise rates of the regions seen
function wakeAllowance(m, regions, budget) {
  const rs = [...new Set(regions)]; if (!rs.length) return {};
  const B = budget == null ? WAKE_BUDGET : budget, left = Math.max(0, B - FLOOR * rs.length), ps = rs.map((r) => rP(m, r)), tot = ps.reduce((a, b) => a + b, 0) || 1;
  const out = {}; rs.forEach((r, i) => { out[r] = FLOOR + left * ps[i] / tot; }); return out;
}

// ---- the store: per-part day logs (userData/judge-logs/<part>.jsonl), engine state (userData/sleep-judges.json), night lines --------
class SleepJudges {
  // o: { dir (userData; omit = in memory), now }
  constructor(o) {
    o = o || {}; this.now = o.now || Date.now; this.dir = o.dir ? path.join(o.dir, 'judge-logs') : null;
    this.stFile = o.dir ? path.join(o.dir, 'sleep-judges.json') : null;
    this.mem = {}; this.st = { parts: {}, nights: [] };
    if (this.stFile) { try { const j = JSON.parse(fs.readFileSync(this.stFile, 'utf8')); if (j && j.parts) this.st = { nights: [], ...j }; } catch (e) { /* fresh */ } }
  }
  save() { if (!this.stFile) return; try { fs.mkdirSync(path.dirname(this.stFile), { recursive: true }); const t = this.stFile + '.tmp'; fs.writeFileSync(t, JSON.stringify(this.st)); fs.renameSync(t, this.stFile); } catch (e) { /* in memory */ } }
  file(part) { return this.dir ? path.join(this.dir, part + '.jsonl') : null; }
  // one logged (prediction, truth) row; day = the local day of row.t (or now)
  record(part, row) {
    const r = { d: dayIndex(row.t || this.now()), ...row }, f = this.file(part);
    if (f) { try { fs.mkdirSync(this.dir, { recursive: true }); fs.appendFileSync(f, JSON.stringify(r) + '\n'); return r; } catch (e) { /* memory */ } }
    (this.mem[part] || (this.mem[part] = [])).push(r); return r;
  }
  rows(part) {
    let out = []; const f = this.file(part);
    if (f) { try { out = fs.readFileSync(f, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean); } catch (e) { /* none */ } }
    return out.concat(this.mem[part] || []);
  }
  days(part) { const by = {}; for (const r of this.rows(part)) (by[r.d] || (by[r.d] = [])).push(r); return by; }
  // keep the last MAX_DAYS logged days of a part
  prune(part) {
    const by = this.days(part), keep = Object.keys(by).map(Number).sort((a, b) => a - b).slice(-MAX_DAYS), f = this.file(part);
    if (!f || Object.keys(by).length <= MAX_DAYS) return;
    try { fs.writeFileSync(f, keep.map((d) => by[d].map((r) => JSON.stringify(r)).join('\n')).join('\n') + '\n'); } catch (e) { /* next night */ }
  }
  state(part) { return this.st.parts[part] || (this.st.parts[part] = {}); }
  // run one part's night on the day that just ended. live: the part's current live model (JSON). -> {rec, model, line} or null
  run(part, live, o) {
    o = o || {};
    const logs = this.days(part.name), D = o.day != null ? o.day : dayIndex(this.now());
    if (!logs[D] || !logs[D].length) return null;                      // nothing logged today: nothing to judge
    const st = this.state(part.name);
    if (st.lastNight === D && !o.force) return null;
    // truth check (track I2): o.truthcheck = a src/truthcheck TruthCheck; parts with a real truth carry part.verify. Source = day:hour.
    if (o.truthcheck && part.verify) {
      try {
        const all = [].concat(...Object.values(logs));
        const tc = o.truthcheck.run(part.name, all, { verify: part.verify, sourceOf: (r) => r.d + ':' + new Date(r.t).getHours() });
        const keep = new Set(tc.kept); for (const d of Object.keys(logs)) logs[d] = logs[d].filter((r) => keep.has(r));
        if (!logs[D].length) return { rec: { part: part.name, action: 'no checked labels' }, model: live, line: part.name + ': no labels passed the truth check today, nothing changed' };
      } catch (e) { /* the check never ends the night: unchecked */ }
    }
    let out;
    try { out = night(part, st, logs, D, J(live)); } catch (e) { return { rec: { part: part.name, action: 'error', why: String(e && e.message || e) }, model: live, line: part.name + ': error, nothing changed' }; }
    st.lastNight = D; out.line = lineOf(out.rec);
    this.st.nights.push({ t: this.now(), ...out.rec }); if (this.st.nights.length > 300) this.st.nights.splice(0, this.st.nights.length - 300);
    this.save(); this.prune(part.name);
    return out;
  }
}
// "guesser: kept (keep app 0.8, when 0.9, idle 0.7), held-out loss 0.85 -> 0.82"
function lineOf(r) {
  const f = (x) => (Number.isFinite(x) ? x.toFixed(2) : '?');
  if (r.action === 'first day' || r.action === 'no candidate') return r.part + ': first night, learning only';
  const what = r.action === 'kept' ? 'kept' : r.action === 'hold' ? 'held (today contradicts what I knew; checked again tomorrow)' : r.action === 'rolled back' ? 'rolled back (the update scored worse on today)' : r.action;
  return r.part + ': ' + what + (r.tag ? ' [' + r.tag + ']' : '') + ', held-out ' + f(r.oldLoss) + ' -> ' + f(r.newLoss) + (r.decided ? '; day ' + r.decided.day + (r.decided.admitted ? ' admitted' : ' quarantined') : '');
}

module.exports = { SleepJudges, night, guesserPart, thinkPart, wherePart, thinkMore, wakeAllowance, thLoss, dayIndex, lineOf, KEEPS, THETAS, EPS };
