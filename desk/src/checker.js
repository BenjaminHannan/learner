'use strict';
// The checker + "I'm not sure" (ingredients plan step 1, app side). ONE interface:
//   score(question, answer, context) -> { p_correct, method, verified }
// Methods, in priority order (the first that applies wins):
//   executor    the world answers: context.check(answer) runs / looks it up in the sandbox, puzzle generator or game rulebook
//               (callers run the test once and pass a checker of the known result). p = 1 or 0. verified.
//   quiz        graded against the source answer by quiz.js grade() (context.quizItem = {answer, aliases}). p = 1 or 0. verified.
//   truthnotes  a note that the 2-site truth check (or Ben) settled: confirmed -> 1, wrong -> 0 (context.truth = TruthNotes). verified.
//   learned     a small head on the brain's hidden states (trained separately, Task C, GPU). OFF by default; it loads weights only
//               when switched on AND its weights file exists, and it needs context.hidden (the app gets text only today).
//   agreement   the fallback for things nothing can check: the share of the K tries that agree with this answer.
//               UNTESTED as a picker: the toy many-tries test (2026-10-17) found vote and self-confidence pickers FAIL. It is shown
//               as "untested", never as reliable.
// Many tries: pick(question, tries, context) scores every try and keeps the best; a verified-correct try always wins.
// "Not sure": the best score below NOT_SURE -> the item goes on the wonder list; anything shared from it says "I'm not sure".
// Calibration: (stated p, later truth) pairs are logged when the truth arrives; ece() is the expected calibration error.
// Free labels: every judged guess is a row in userData/checker-labels.jsonl (the future learned head's training data).
const fs = require('fs');
const path = require('path');

const NOT_SURE = 0.5;
const METHODS = ['executor', 'quiz', 'truthnotes', 'learned', 'agreement'];
const STOP = new Set('the a an of and or to in on at by for with is are was were be been it its this that as from which who what when where how than then into about over has have had not no can will does do did'.split(' '));
const words = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9\s]/g, ' ').split(/\s+/).filter((w) => w.length > 1 && !STOP.has(w));
const norm = (s) => String(s == null ? '' : s).toLowerCase().replace(/\s+/g, ' ').replace(/[.\s]+$/, '').trim();
// two free-text answers "agree" when they are the same after normalising, or share >= 80% of their content words both ways with
// the same numbers (strict on purpose: "the Moon is made of rock" must not match a settled "the Moon is made of cheese")
function similar(a, b) {
  if (norm(a) === norm(b)) return true;
  const A = new Set(words(a)), B = new Set(words(b)); if (!A.size || !B.size) return false;
  const nums = (S) => [...S].filter((w) => /\d/.test(w)).sort().join();
  if (nums(A) !== nums(B)) return false;
  let k = 0; for (const w of A) if (B.has(w)) k++;
  return k / A.size >= 0.8 && k / B.size >= 0.8;
}

// ---- the learned head (slot only; OFF by default) -------------------------------------------------------------------------
// weights file (JSON): { version: 1, kind: "logistic", dim, w: [dim numbers], b, model, layer, trainedOn, note }
class LearnedHead {
  // o: { file, enabled }
  constructor(o) { o = o || {}; this.file = o.file || null; this.enabled = o.enabled === true; this.head = null; this.why = 'off'; if (this.enabled) this.load(); }
  load() {
    this.head = null;
    if (!this.enabled) { this.why = 'off'; return false; }
    if (!this.file || !fs.existsSync(this.file)) { this.why = 'no weights file'; return false; }
    try {
      const j = JSON.parse(fs.readFileSync(this.file, 'utf8'));
      if (!j || j.version !== 1 || j.kind !== 'logistic' || !Array.isArray(j.w) || j.w.length !== j.dim || !j.w.every(Number.isFinite) || !Number.isFinite(j.b)) { this.why = 'bad weights file'; return false; }
      this.head = j; this.why = 'loaded'; return true;
    } catch (e) { this.why = 'unreadable weights file'; return false; }
  }
  loaded() { return !!this.head; }
  // hidden: the brain's last-token hidden state for the answer (array of dim numbers) -> p or null
  score(hidden) {
    if (!this.head || !Array.isArray(hidden) || hidden.length !== this.head.dim) return null;
    let z = this.head.b; for (let i = 0; i < hidden.length; i++) z += this.head.w[i] * (Number(hidden[i]) || 0);
    return 1 / (1 + Math.exp(-z));
  }
}

// ---- calibration ----------------------------------------------------------------------------------------------------------
// pairs: [{p, y}] (y = 1 right, 0 wrong). Equal-width bins over [0,1]; ECE = sum over bins of (n_bin / n) * |mean p - accuracy|.
function ece(pairs, bins) {
  bins = bins || 10;
  const ps = (pairs || []).filter((x) => x && Number.isFinite(x.p) && (x.y === 0 || x.y === 1));
  if (!ps.length) return { n: 0, ece: null, bins: [] };
  const B = Array.from({ length: bins }, (_, i) => ({ lo: i / bins, hi: (i + 1) / bins, n: 0, sp: 0, sy: 0 }));
  for (const x of ps) { const p = Math.max(0, Math.min(1, x.p)); const i = Math.min(bins - 1, Math.floor(p * bins)); B[i].n++; B[i].sp += p; B[i].sy += x.y; }
  let e = 0; for (const b of B) if (b.n) e += (b.n / ps.length) * Math.abs(b.sp / b.n - b.sy / b.n);
  return { n: ps.length, ece: e, accuracy: ps.reduce((s, x) => s + x.y, 0) / ps.length, meanP: ps.reduce((s, x) => s + x.p, 0) / ps.length,
    bins: B.filter((b) => b.n).map((b) => ({ lo: b.lo, hi: b.hi, n: b.n, meanP: b.sp / b.n, acc: b.sy / b.n })) };
}

class Checker {
  // o: { dir (userData; omit = in memory), now, learned: {enabled, file}, notSure }
  constructor(o) {
    o = o || {}; this.o = o; this.now = o.now || Date.now; this.notSure = o.notSure == null ? NOT_SURE : o.notSure;
    this.labelsFile = o.dir ? path.join(o.dir, 'checker-labels.jsonl') : null;
    this.calFile = o.dir ? path.join(o.dir, 'checker-calibration.jsonl') : null;
    this.pendingFile = o.dir ? path.join(o.dir, 'checker-pending.json') : null;
    const lf = (o.learned && o.learned.file) || (o.dir ? path.join(o.dir, 'checker-head.json') : null);
    this.learned = new LearnedHead({ file: lf, enabled: !!(o.learned && o.learned.enabled) });
    this.mem = { labels: [], cal: [] };
    this.pending = {};
    if (this.pendingFile) { try { this.pending = JSON.parse(fs.readFileSync(this.pendingFile, 'utf8')) || {}; } catch (e) { this.pending = {}; } }
  }
  // the one interface
  score(question, answer, context) {
    const c = context || {};
    if (typeof c.check === 'function') {
      let ok = null; try { ok = c.check(answer); } catch (e) { ok = null; }
      if (ok === true || ok === false) return { p_correct: ok ? 1 : 0, method: 'executor', verified: true };
    }
    if (c.quizItem && c.quizItem.answer) {
      const ok = require('./quiz').grade(answer, c.quizItem);
      return { p_correct: ok ? 1 : 0, method: 'quiz', verified: true };
    }
    if (c.truth && c.truth.notes) {
      const n = c.truth.notes.find((x) => (x.status === 'confirmed' || x.status === 'wrong') && similar(x.text, answer));
      if (n) return { p_correct: n.status === 'confirmed' ? 1 : 0, method: 'truthnotes', verified: true, note: n.id };
    }
    if (this.learned.loaded() && c.hidden) { const p = this.learned.score(c.hidden); if (p != null) return { p_correct: p, method: 'learned', verified: false }; }
    const tries = Array.isArray(c.tries) ? c.tries.filter((t) => t != null && String(t).trim()) : [];
    if (tries.length) { const agree = tries.filter((t) => similar(t, answer)).length; return { p_correct: agree / tries.length, method: 'agreement', verified: false, untested: true }; }
    return { p_correct: 0.5, method: 'none', verified: false, untested: true };
  }
  // K tries -> the best one. contextFor(i, answer) may give a per-try context (e.g. hidden states); the shared context adds tries.
  // -> { index, answer, p_correct, method, verified, notSure, scores: [...] }
  pick(question, tries, context, contextFor) {
    const ans = (tries || []).map((t) => (t == null ? '' : String(t)));
    if (!ans.length) return { index: -1, answer: null, p_correct: 0, method: 'none', verified: false, notSure: true, scores: [] };
    const scores = ans.map((a, i) => this.score(question, a, { tries: ans, ...(context || {}), ...((contextFor && contextFor(i, a)) || {}) }));
    // a verified-correct try always wins; then the highest score; ties -> the earliest try (the plain, low-temperature one)
    let best = 0;
    for (let i = 1; i < scores.length; i++) {
      const a = scores[i], b = scores[best];
      const va = a.verified && a.p_correct === 1, vb = b.verified && b.p_correct === 1;
      if ((va && !vb) || (va === vb && a.p_correct > b.p_correct)) best = i;
    }
    const s = scores[best];
    return { index: best, answer: ans[best], ...s, notSure: s.p_correct < this.notSure, scores };
  }
  // K thinking-Mote tries ({claims, question} or null each) -> the try whose claims score best. A claim's score: a settled truth note
  // (verified) if one matches, else its agreement share = how many tries contain a similar claim (untested).
  // -> { index, p_correct (mean over its claims), method, verified, notSure, claims: [{text, p_correct, method}] }
  pickThoughts(topic, parsed, context) {
    const tries = (parsed || []).map((t) => (t && Array.isArray(t.claims) ? t.claims : null));
    const ctx = context || {};
    let best = -1, bestS = null;
    tries.forEach((claims, i) => {
      if (!claims || !claims.length) return;
      const cs = claims.map((c) => {
        const v = ctx.truth ? this.score(topic, c, { truth: ctx.truth }) : null;
        if (v && v.verified) return { text: c, p_correct: v.p_correct, method: v.method, verified: true };
        const agree = tries.filter((t) => t && t.some((x) => similar(x, c))).length;
        return { text: c, p_correct: agree / tries.length, method: 'agreement', verified: false, untested: true };
      });
      const p = cs.reduce((a, c) => a + c.p_correct, 0) / cs.length;
      const s = { index: i, p_correct: p, method: cs.every((c) => c.verified) ? 'truthnotes' : 'agreement', verified: cs.every((c) => c.verified), claims: cs };
      if (!bestS || p > bestS.p_correct) { best = i; bestS = s; }
    });
    if (best < 0) { const i = Math.max(0, tries.findIndex((t) => t)); return { index: i, p_correct: 0, method: 'none', verified: false, notSure: true, claims: [] }; }
    return { ...bestS, notSure: bestS.p_correct < this.notSure };
  }
  // Glim's words for something it is unsure of
  hedge(text, p) { const t = String(text || '').trim(); return p != null && p < this.notSure ? "I'm not sure, but " + t.replace(/^[A-Z](?=[a-z])/, (c) => c.toLowerCase()) : t; }

  // ---- free labels (every judged guess, right or wrong) --------------------------------------------------------------------
  // row: { question, answer, correct, p (stated before the test, if any), pMethod (who stated p: agreement | self | learned),
  //        method (who judged the truth: executor | quiz | truthnotes), source, truth, kind, guessAt, resultAt }
  label(row) {
    const r = { t: this.now(), ...row, question: String(row.question || '').slice(0, 2000), answer: String(row.answer == null ? '' : row.answer).slice(0, 1000) };
    if (this.labelsFile) { try { fs.mkdirSync(path.dirname(this.labelsFile), { recursive: true }); fs.appendFileSync(this.labelsFile, JSON.stringify(r) + '\n'); } catch (e) { this.mem.labels.push(r); } }
    else this.mem.labels.push(r);
    if (Number.isFinite(row.p) && (row.correct === true || row.correct === false)) this.calibrate(row.p, row.correct, { method: row.pMethod || row.method, kind: row.kind });
    return r;
  }
  labels() { return this.readJsonl(this.labelsFile).concat(this.mem.labels); }

  // ---- calibration: (stated p, later truth) ----------------------------------------------------------------------------------
  calibrate(p, correct, meta) {
    const r = { t: this.now(), p: Math.max(0, Math.min(1, Number(p))), y: correct ? 1 : 0, ...(meta || {}) };
    if (this.calFile) { try { fs.appendFileSync(this.calFile, JSON.stringify(r) + '\n'); return r; } catch (e) { /* in memory */ } }
    this.mem.cal.push(r); return r;
  }
  // a stated p for a claim whose truth arrives later (the 2-site truth check); remembered by its words
  expect(text, p, meta) {
    const k = norm(text).slice(0, 200); if (!k) return;
    this.pending[k] = { p: Math.max(0, Math.min(1, Number(p) || 0)), t: this.now(), ...(meta || {}) };
    const keys = Object.keys(this.pending); if (keys.length > 500) for (const x of keys.slice(0, keys.length - 500)) delete this.pending[x];
    this.savePending();
  }
  // the truth arrived for `text` (confirmed -> right, wrong -> wrong): log the pair. -> the pair or null
  settled(text, correct) {
    const k = norm(text).slice(0, 200), e = this.pending[k]; if (!e) return null;
    delete this.pending[k]; this.savePending();
    return this.calibrate(e.p, correct, { method: e.method || 'agreement', kind: e.kind || 'claim', lagMs: this.now() - e.t });
  }
  savePending() { if (!this.pendingFile) return; try { fs.writeFileSync(this.pendingFile, JSON.stringify(this.pending)); } catch (e) { /* in memory */ } }
  pairs(filter) { return this.readJsonl(this.calFile).concat(this.mem.cal).filter((x) => !filter || filter(x)); }
  // the small report for the dashboard / diary: ECE overall and per method
  report() {
    const all = this.pairs(); const out = { overall: ece(all), byMethod: {} };
    for (const m of new Set(all.map((x) => x.method || '?'))) out.byMethod[m] = ece(all.filter((x) => (x.method || '?') === m));
    return out;
  }
  reportLine() {
    const r = this.report(); if (!r.overall.n) return 'Checker: no calibration data yet.';
    const parts = Object.entries(r.byMethod).map(([m, v]) => m + ' ' + v.n + (v.ece != null ? ' (ECE ' + v.ece.toFixed(2) + ')' : '') + (m === 'agreement' ? ' untested' : ''));
    return 'Checker calibration: ' + r.overall.n + ' judged guesses, ECE ' + r.overall.ece.toFixed(2) + ', right ' + Math.round(r.overall.accuracy * 100) + '%. By method: ' + parts.join('; ') + '.';
  }
  readJsonl(f) { if (!f) return []; try { return fs.readFileSync(f, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean); } catch (e) { return []; } }
}

module.exports = { Checker, LearnedHead, ece, similar, NOT_SURE, METHODS };
