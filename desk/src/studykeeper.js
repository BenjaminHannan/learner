'use strict';
// The study keeper (SWITCH-ON 2026-11-05). Ben: "it should always be doing something. If it's just watching you and has nothing to
// contribute, it should just go learn about something interesting and relevant."
//   - kick(): called when an always-on tick ends with nothing said, and once a minute. If the brain is free (o.free(): the Mote gate,
//     the model lock) and no Learn study run is in flight, the current study's next Mote runs at once (back to back, not every 45 min).
//   - Ben's own Learn study always wins: Glim keeps it going but never replaces or stops it.
//   - Glim's own study keeps ONE topic until its Learn quiz plateaus (plateau()), then picks the next by relevance to Ben + interest
//     (choose()), never its previous topic or a near-copy, never "Ben's app-switching / Glim's own observing" meta topics.
//   - sample(): one duty line {free, studying} for the 80 % mark (userData/study-duty.jsonl).
// Pure Node: every app part is injected, so the tests drive it with fakes.
const fs = require('fs');
const path = require('path');

const FILE = 'self-study.json', DUTY = 'study-duty.jsonl';
const MAX_RUNS_NO_QUIZ = 12, MAX_RUNS = 60, KICK_GAP_MS = 20000, EXAM_EVERY_RUNS = 3;
const STOP = new Set('a an the and or of to in on for with by from at as is are was were be been it its this that these those how what why when which who whom about into over under than then so such not no yes your you his her their our my we i me he she they them can could should would will just also more most less very via using use vs etc new one two'.split(' '));
// topics about watching Ben / Glim itself: all 9 topics Glim picked for itself on Nov 4-5 were of this kind
const META = /\b(?:app[- ]?(?:usage|switch\w*)|front[- ]?app|switching patterns?|session (?:context|transition)|screen activity|focus (?:pattern|session)s?|usage[- ]pattern|intent inference|context classification|glim|premonition|always-on|ben'?s (?:screen|activity|habits?|focus))\b/i;
const words = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9+#]+/g, ' ').split(' ').filter((w) => w.length > 2 && !STOP.has(w));
function jaccard(a, b) { const A = new Set(words(a)), B = new Set(words(b)); if (!A.size || !B.size) return 0; let n = 0; for (const x of A) if (B.has(x)) n++; return n / (A.size + B.size - n); }
// newest quiz level: >= 3 scores, the last 3 within 5 points, and the newest one is not a new best
function plateau(quiz, runs) {
  runs = runs | 0;
  if (runs >= MAX_RUNS) return { done: true, why: 'run cap ' + MAX_RUNS };
  const levels = (quiz && quiz.levels) || [];
  if (!quiz || quiz.status === 'failed' || !levels.length) return runs >= MAX_RUNS_NO_QUIZ ? { done: true, why: 'no quiz score after ' + runs + ' runs' } : { done: false, why: 'no quiz yet' };
  if (quiz.levelUpDue) return { done: false, why: 'harder level coming' };
  const top = Math.max(...levels.map((l) => l.level));
  const s = (quiz.scores || []).filter((x) => x.level === top).map((x) => Number(x.pct) || 0);
  if (s.length < 3) return runs >= MAX_RUNS_NO_QUIZ * 2 ? { done: true, why: 'too few quiz scores after ' + runs + ' runs' } : { done: false, why: s.length + ' quiz score(s) on level ' + top };
  const last = s.slice(-3);
  // "no new best": the newest score is not above every earlier score on this level (still climbing, however slowly, = keep going)
  const spread = Math.max(...last) - Math.min(...last), newBest = s[s.length - 1] > Math.max(...s.slice(0, -1));
  return spread <= 5 && !newBest ? { done: true, why: 'quiz flat at ' + last.join('/') + '% on level ' + top } : { done: false, why: 'quiz still moving (' + last.join('/') + '%)' };
}
// candidates [{topic, kind, interest 0..1, why}] + Ben's words -> the best topic or null
function choose(cands, benWords, avoid) {
  const ben = new Set(benWords || []), out = [];
  for (const c of cands || []) {
    const t = String(c.topic || '').replace(/\s+/g, ' ').trim().slice(0, 160);
    if (t.length < 3 || META.test(t)) continue;
    if ((avoid || []).some((a) => jaccard(a, t) >= 0.5)) continue;
    const w = words(t); if (!w.length) continue;
    const rel = w.filter((x) => ben.has(x)).length / w.length;
    const kindBonus = c.kind === 'goal' ? 0.3 : c.kind === 'stuck' ? 0.3 : 0;
    const score = rel + kindBonus + 0.5 * Math.max(0, Math.min(1, Number(c.interest) || 0));
    if (rel === 0 && !kindBonus) continue;   // relevant to Ben, not random
    out.push({ topic: t, kind: c.kind, score: Math.round(score * 100) / 100, rel: Math.round(rel * 100) / 100, why: c.why || '' });
  }
  out.sort((a, b) => b.score - a.score);
  return { best: out[0] || null, ranked: out.slice(0, 8) };
}

class StudyKeeper {
  // o: { dir, now, free() -> {ok, why}, study: { cur() -> {topic, ids, by}|null, start(topic) -> {ok, error}, stop() },
  //      isRunning(ids) -> bool, runNext(ids, turn) -> bool, quiz(topic) -> quiz|null, examDue(topic), candidates() -> [...],
  //      benWords() -> [word], log(...) }
  constructor(o) {
    this.o = o; this.now = o.now || Date.now; this.lastKick = 0;
    this.file = o.dir ? path.join(o.dir, FILE) : null; this.dutyFile = o.dir ? path.join(o.dir, DUTY) : null;
    this.s = { topic: null, since: 0, runs: 0, turn: 0, done: [], proposals: [], started: [] };
    if (this.file) { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (j && typeof j === 'object') this.s = { ...this.s, ...j }; } catch (e) { /* fresh */ } }
  }
  save() { if (!this.file) return; try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); const tmp = this.file + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(this.s)); fs.renameSync(tmp, this.file); } catch (e) { /* in memory */ } }
  log(...a) { try { this.o.log && this.o.log(...a); } catch (e) { /* ignore */ } }
  // the brain's "learn" field: a candidate for the NEXT topic, never a new study on the spot
  propose(topic, why) {
    const t = String(topic || '').trim().slice(0, 160); if (!t) return false;
    this.s.proposals = this.s.proposals.filter((p) => p.topic.toLowerCase() !== t.toLowerCase() && this.now() - p.at < 6 * 3600000).concat([{ topic: t, at: this.now(), why: why || '' }]).slice(-20);
    this.save(); return true;
  }
  studying() { const c = this.o.study.cur(); return !!(c && this.o.isRunning(c.ids || [])); }
  // one duty sample (the measure for Ben's rule): logged every 30 s by main
  sample() {
    const f = this.o.free(), st = this.studying(), c = this.o.study.cur();
    const row = { t: this.now(), free: !!f.ok, why: f.why || null, studying: st, topic: c ? c.topic.slice(0, 80) : null, by: c ? c.by || 'ben' : null };
    if (this.dutyFile) { try { fs.appendFileSync(this.dutyFile, JSON.stringify(row) + '\n'); } catch (e) { /* measure only */ } }
    return row;
  }
  // a study run finished (main: helpers onFinish of a Learn Mote)
  ran(id) {
    const c = this.o.study.cur(); if (!c || !(c.ids || []).includes(id) || c.by !== 'glim') return;
    this.s.runs++; this.save();
    if (this.s.runs % EXAM_EVERY_RUNS === 0) { try { this.o.examDue && this.o.examDue(c.topic); } catch (e) { /* next time */ } }
  }
  kick(why, force) {
    if (!force && this.now() - this.lastKick < KICK_GAP_MS) return { action: 'wait', why: 'just kicked' };
    const f = this.o.free(); if (!f.ok) return { action: 'wait', why: f.why || 'busy' };
    this.lastKick = this.now();
    let cur = this.o.study.cur();
    if (cur && cur.by !== 'glim') {   // Ben's study: keep it going, never replace it
      if (this.o.isRunning(cur.ids || [])) return { action: 'running', topic: cur.topic };
      return this.o.runNext(cur.ids || [], this.s.turn++) ? { action: 'continue', topic: cur.topic, by: 'ben' } : { action: 'wait', why: 'nothing to run' };
    }
    if (cur) {
      const p = plateau(this.o.quiz(cur.topic), this.s.runs);
      if (!p.done) {
        if (this.o.isRunning(cur.ids || [])) return { action: 'running', topic: cur.topic };
        const ok = this.o.runNext(cur.ids || [], this.s.turn++); this.save();
        return ok ? { action: 'continue', topic: cur.topic, why: p.why } : { action: 'wait', why: 'run did not start' };
      }
      if (this.o.isRunning(cur.ids || [])) return { action: 'running', topic: cur.topic, why: 'plateau; finishing this run' };
      this.s.done = this.s.done.concat([{ topic: cur.topic, at: this.now(), runs: this.s.runs, why: p.why }]).slice(-30);
      this.log('study keeper: done with "' + cur.topic + '" (' + p.why + ')');
      this.o.study.stop(); cur = null;
    }
    const avoid = this.s.done.map((d) => d.topic).concat(this.s.topic ? [this.s.topic] : []);
    const cands = (this.o.candidates() || []).concat(this.s.proposals.map((p) => ({ topic: p.topic, kind: 'proposal', interest: 0.2, why: 'the brain suggested it' })));
    const ch = choose(cands, this.o.benWords(), avoid);
    if (!ch.best) return { action: 'wait', why: 'no relevant topic' };
    const r = this.o.study.start(ch.best.topic) || {};
    if (!r.ok) return { action: 'wait', why: r.error || 'could not start' };
    this.s.topic = ch.best.topic; this.s.since = this.now(); this.s.runs = 0;
    this.s.proposals = this.s.proposals.filter((p) => jaccard(p.topic, ch.best.topic) < 0.5);
    this.s.started = this.s.started.concat([{ topic: ch.best.topic, at: this.now(), score: ch.best.score, rel: ch.best.rel, kind: ch.best.kind, why: why || '' }]).slice(-30);
    this.save();
    this.log('study keeper: started "' + ch.best.topic + '" (' + ch.best.kind + ', score ' + ch.best.score + ')');
    return { action: 'start', topic: ch.best.topic, ranked: ch.ranked };
  }
}

module.exports = { StudyKeeper, plateau, choose, jaccard, words, META, MAX_RUNS_NO_QUIZ, KICK_GAP_MS };
