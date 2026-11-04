'use strict';
// T5 (2026-11-04): the STUCK list. Problems Glim failed during the day are kept, with their context, so that sleep can try them
// again with related memories ("mix and match until something clicks"; Wagner et al. 2004, "Sleep inspires insight").
// Toy evidence (premonition-sleeplab-t5, MARKS-insight-v1): recall + recombine + verify beat plain retry at the same night budget.
// That is a TOY result; the real Glim gets its own check (insight results in the morning).
//
// Sources (each entry keeps the problem plus its context):
//   scientist   an experiment where ALL K tries were wrong (repeated failure on one item). It carries the executor / puzzle-generator
//               truth as a sha256 of the normalised answer only, so the night prompt can never see the answer: a candidate is
//               stored only if its own answer hashes to the same value (the truth decides, never the model).
//   notsure     an "I'm not sure" claim (checker.js). No truth at night: it stays listed until a day check settles it.
//   ben-error   Ben stuck on the same error 3+ times (speakometer.js Stuck). No truth at night.
//   quiz-miss   a missed Learn-quiz item. The quiz stays LOCKED: only the topic and the item id are kept, never the question or the
//               answer (studiers and sleep must not see them). No truth at night; the next quiz is the check.
// Cap and fading: at most CAP entries; each night an unsolved entry's weight x FADE; below DROP it leaves; the lowest weight is
// evicted first when full; seeing the same problem again restores weight 1. Pure Node; the file is userData/alwayson-stuck.json.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CAP = 50, FADE = 0.7, DROP = 0.2;
const SOURCES = ['scientist', 'notsure', 'ben-error', 'quiz-miss'];
const FILE = 'alwayson-stuck.json';

// the same normalisation as sandbox.js normOut (and sleepmlx insight.norm_out): CRLF -> LF, trailing spaces per line, trailing blank lines
const normOut = (s) => String(s == null ? '' : s).replace(/\r\n/g, '\n').split('\n').map((l) => l.replace(/\s+$/, '')).join('\n').replace(/\n+$/, '');
// puzzles.js correct(): normAns equal, or equal with spaces removed. The space-free form is exactly that test (the first implies it).
const normAns = (s) => String(s == null ? '' : s).toLowerCase().replace(/^\s*(?:answer|output)\s*[:=]\s*/, '').replace(/[`"'.]/g, '').replace(/[\s,]+/g, ' ').trim().replace(/(\d) (?=\d)/g, '$1');
const NORMS = { out: normOut, puzzle: (s) => normAns(s).replace(/ /g, '') };
const normFor = (kind) => (/^(?:puzzle|game):/.test(String(kind || '')) ? 'puzzle' : 'out');
const truthHash = (answer, norm) => crypto.createHash('sha256').update(NORMS[norm || 'out'](answer), 'utf8').digest('hex');
const keyOf = (source, problem) => source + ':' + crypto.createHash('sha1').update(String(problem).trim().toLowerCase()).digest('hex').slice(0, 12);

class StuckList {
  // o: { dir (userData; omit = in memory), now }
  constructor(o) {
    this.o = o || {}; this.now = this.o.now || Date.now;
    this.file = this.o.dir ? path.join(this.o.dir, FILE) : null;
    this.items = []; this.solved = []; this.lastResults = '';
    if (this.file) { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (j && Array.isArray(j.items)) { this.items = j.items; this.solved = Array.isArray(j.solved) ? j.solved : []; this.lastResults = String(j.lastResults || ''); } } catch (e) { /* fresh */ } }
  }
  save() {
    if (!this.file) return;
    try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); const t = this.file + '.tmp'; fs.writeFileSync(t, JSON.stringify(this.view(), null, 1)); fs.renameSync(t, this.file); } catch (e) { /* in memory */ }
  }
  view() { return { v: 1, at: this.now(), cap: CAP, items: this.items, solved: this.solved.slice(-100), lastResults: this.lastResults }; }
  // e: { source, problem, context?, kind?, truth? (plain answer, hashed here and never stored) }
  add(e) {
    if (!e || !SOURCES.includes(e.source) || !String(e.problem || '').trim()) return null;
    const problem = String(e.problem).slice(0, 1500);
    const id = keyOf(e.source, problem), now = this.now();
    let it = this.items.find((x) => x.id === id);
    if (it) { it.seen += 1; it.lastAt = now; it.weight = 1; if (e.context) it.context = String(e.context).slice(0, 1500); this.save(); return it; }
    if (this.solved.some((x) => x.id === id)) return null;   // already clicked once: the sleep card has it
    it = { id, source: e.source, kind: String(e.kind || e.source).slice(0, 60), problem, context: String(e.context || '').slice(0, 1500),
      truth: e.truth != null ? { type: 'sha256', norm: NORMS[e.norm] ? e.norm : 'out', value: truthHash(e.truth, NORMS[e.norm] ? e.norm : 'out') } : { type: 'none' },
      firstAt: now, lastAt: now, seen: 1, nights: 0, weight: 1 };
    this.items.push(it);
    if (this.items.length > CAP) { this.items.sort((a, b) => b.weight - a.weight || b.lastAt - a.lastAt); this.items.length = CAP; }
    this.save();
    return it;
  }
  checkable() { return this.items.filter((x) => x.truth && x.truth.type === 'sha256'); }
  // a day check settled it (e.g. a notsure claim confirmed or found wrong; the quiz item answered right later)
  resolve(id, how) { const i = this.items.findIndex((x) => x.id === id); if (i < 0) return false; const [it] = this.items.splice(i, 1); this.solved.push({ id, at: this.now(), how: how || 'day', source: it.source }); this.save(); return true; }
  // after a night: entries sleep solved (ids from the insight results) leave; the rest fade
  afterNight(solvedIds) {
    const ok = new Set(solvedIds || []); const out = { solved: 0, faded: 0, dropped: 0 };
    this.items = this.items.filter((it) => {
      if (ok.has(it.id)) { this.solved.push({ id: it.id, at: this.now(), how: 'sleep', source: it.source }); out.solved++; return false; }
      it.nights += 1; it.weight = Math.round(it.weight * FADE * 1000) / 1000; out.faded++;
      if (it.weight < DROP) { out.dropped++; return false; }
      return true;
    });
    this.save();
    return out;
  }
  // the morning: one night's insight results (sleepmlx writes alwayson-insight.json), used once. Solved entries leave, the rest fade.
  // -> the line for Ben (only if something NEW clicked), else null
  morning(res) {
    if (!res || !Array.isArray(res.clicked)) return null;
    const stamp = String(res.written_at || '') + '|' + String(res.date || '') + '|' + String(res.night || '');
    if (stamp === '||' || stamp === this.lastResults) return null;
    this.lastResults = stamp;
    this.afterNight(res.clicked.map((c) => c.id));
    return morningLine({ clicked: res.clicked.filter((c) => !c.earlier) });
  }
}

// ---- the day sources -------------------------------------------------------------------------------------------------------------
// scientist.js onStuck({kind, question, truth, tries, guesses}): every try was wrong. The wrong guesses are context (what did not work).
function fromExperiment(x) {
  if (!x || !x.question || x.truth == null || x.kind === 'python-own') return null;   // own programs: the program is the guess, not a problem
  const tried = (x.guesses || []).slice(0, 4).map((g) => JSON.stringify(String(g).slice(0, 80))).join(', ');
  return { source: 'scientist', kind: x.kind, norm: normFor(x.kind), problem: x.question, truth: x.truth,
    context: 'All ' + (x.tries || '?') + ' of my tries were wrong' + (tried ? ': ' + tried : '') + '.' };
}
const fromNotSure = (text, p) => ({ source: 'notsure', kind: 'claim', problem: String(text || ''), context: "I'm not sure (" + (Number(p) || 0).toFixed(2) + ')' });
const fromBenError = (err) => (err && err.n >= 3 ? { source: 'ben-error', kind: 'error', problem: String(err.text || ''), context: 'Ben saw this error ' + err.n + ' times in 30 minutes.' } : null);
// locked: the topic and item id only
const fromQuizMiss = (topic, id) => ({ source: 'quiz-miss', kind: 'quiz', problem: 'weak spot in ' + String(topic || '') + ' (quiz ' + String(id || '') + ')', context: 'missed a Learn-quiz item' });

// ---- the morning: what sleep's insight step reports (sleepmlx insight.py writes it next to the stuck file) -------------------------
const RESULTS = 'alwayson-insight.json';
function readResults(dir) { try { const j = JSON.parse(fs.readFileSync(path.join(dir, RESULTS), 'utf8')); return j && Array.isArray(j.clicked) ? j : null; } catch (e) { return null; } }
// one line for Ben, only if something clicked (null otherwise: Glim says nothing)
function morningLine(res) {
  const c = res && Array.isArray(res.clicked) ? res.clicked : [];
  if (!c.length) return null;
  const ex = String(c[0].problem || '').replace(/\s+/g, ' ').slice(0, 90);
  return 'Something clicked overnight: I solved ' + c.length + ' problem' + (c.length === 1 ? '' : 's') + ' I was stuck on yesterday'
    + (ex ? ' (e.g. "' + ex + '")' : '') + ', checked against the real answer.';
}

module.exports = { StuckList, fromExperiment, fromNotSure, fromBenError, fromQuizMiss, readResults, morningLine, normOut, normAns, normFor, truthHash, CAP, FADE, DROP, FILE, RESULTS, SOURCES };
