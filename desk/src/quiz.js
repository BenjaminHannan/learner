'use strict';
// Always-on v2, phase 6: an honest score for each Learn topic.
//   writer:   when a topic starts, a separate "writer" pass reads several websites and writes a LOCKED quiz (~20 questions), each
//             with a source-backed answer (the words appear in the page) and the source URL. It is stored apart from everything the
//             studiers see (userData/learn-quiz/<topic>.json); studier prompts are checked so they never contain a quiz question.
//   examiner: Glim answers each question (recording its guess + confidence BEFORE checking); grading compares the answer with the
//             stored source answer by text, never by Glim's opinion. A confident miss is a surprise and goes on the wonder list.
//   score:    "black holes Lv1 81% · Lv2 30%". The official score is the first one taken after the nightly sleep. A harder level is
//             added once Lv1 (or the newest level) reaches 80% officially. Ben can view the quiz.
//   drift:    every study step is checked "is this still about my topic?" and skipped when it is not.
// Pure Node: search / fetch / ask are injected.
const fs = require('fs');
const path = require('path');

const TARGET = 20, LEVEL_UP = 80;
const slug = (t) => String(t || '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'topic';
const norm = (s) => String(s || '').toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9.*\s-]/g, ' ').replace(/\.(?!\d)/g, ' ').replace(/\b(?:the|a|an)\b/g, ' ').replace(/\s+/g, ' ').trim();
const STOP = new Set('the a an of and or to in on at by for with is are was were be been it its this that as from which who what when where how than then into about over has have had not no can will does do did'.split(' '));
const stems = (s) => norm(s).split(/\s+/).filter((w) => w.length > 2 && !STOP.has(w)).map((w) => w.replace(/(?:ies|es|s)$/, '').slice(0, 7));

// ---- grading: against the stored source answer, by text ---------------------------------------------------------------
function grade(given, q) {
  const g = norm(given), answers = [q.answer].concat(q.aliases || []).map(norm).filter(Boolean);
  if (!g) return false;
  for (const a of answers) {
    if (g === a) return true;
    const na = parseFloat(a.replace(/,/g, '')), ng = parseFloat(g.replace(/,/g, ''));
    if (/^[\d.,\s-]+[a-z%]*$/.test(a) && Number.isFinite(na) && Number.isFinite(ng)) { if (/\d\.\d/.test(a) ? Math.abs(na - ng) <= Math.abs(na) * 0.02 : na === ng) return true; continue; }   // whole numbers (years, counts) must match exactly
    // a short answer must appear whole; a longer one must share most of its content words
    if (a.length <= 24 ? new RegExp('(?:^|\\s)' + a.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '(?:\\s|$)').test(g) : (() => { const as = stems(a), gs = new Set(stems(g)); return as.length && as.filter((w) => gs.has(w)).length / as.length >= 0.75; })()) return true;
  }
  return false;
}

// ---- drift guard --------------------------------------------------------------------------------------------------------
// on topic = shares a word with the topic, or 2+ words with what Glim already confirmed about it
function onTopic(text, topic, vocab) {
  const ts = new Set(stems(topic)), ws = stems(text);
  if (ws.some((w) => ts.has(w))) return true;
  const v = vocab instanceof Set ? vocab : new Set(stems((vocab || []).join(' ')));
  return ws.filter((w) => v.has(w) && !ts.has(w)).length >= 2;
}

// ---- page text ------------------------------------------------------------------------------------------------------------
function pageText(html) {
  return String(html || '').replace(/<script[\s\S]*?<\/script>|<style[\s\S]*?<\/style>|<nav[\s\S]*?<\/nav>|<footer[\s\S]*?<\/footer>/gi, ' ')
    .replace(/<[^>]+>/g, ' ').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;|&#x27;/g, "'")
    .replace(/\s+/g, ' ').trim();
}
function parseQuestions(text) {
  const s = String(text || '').replace(/<think>[\s\S]*?<\/think>/gi, '');
  const a = s.indexOf('['), b = s.lastIndexOf(']');
  if (a < 0 || b <= a) return [];
  try { const j = JSON.parse(s.slice(a, b + 1)); return Array.isArray(j) ? j.filter((x) => x && typeof x.q === 'string' && typeof x.answer === 'string') : []; } catch (e) { return []; }
}
const WRITER_SYSTEM = 'You write quiz questions from ONE web page. Every answer must be stated in the page text. Reply with a JSON array and nothing else: '
  + '[{"q": "a short question", "answer": "a short answer, 1 to 6 words, copied from the page", "quote": "the sentence from the page that states the answer"}]. Up to 4 questions. No yes/no questions.';

class QuizStore {
  constructor(dir) { this.dir = path.join(dir, 'learn-quiz'); }
  file(topic) { return path.join(this.dir, slug(topic) + '.json'); }
  load(topic) { try { return JSON.parse(fs.readFileSync(this.file(topic), 'utf8')); } catch (e) { return null; } }
  save(quiz) { fs.mkdirSync(this.dir, { recursive: true }); const f = this.file(quiz.topic), tmp = f + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(quiz, null, 1)); fs.renameSync(tmp, f); return quiz; }
  list() { try { return fs.readdirSync(this.dir).filter((f) => f.endsWith('.json')).map((f) => { try { return JSON.parse(fs.readFileSync(path.join(this.dir, f), 'utf8')); } catch (e) { return null; } }).filter(Boolean); } catch (e) { return []; } }
  // every question text of every quiz, for the leak check
  allQuestions() { const out = []; for (const z of this.list()) for (const L of z.levels || []) for (const q of L.questions || []) out.push(q.q); return out; }
  // does this prompt (studier messages or text) contain any locked question?
  leaks(prompt) {
    const t = norm(typeof prompt === 'string' ? prompt : JSON.stringify(prompt));
    return this.allQuestions().some((q) => { const n = norm(q); return n.length > 12 && t.includes(n); });
  }
}

// the writer pass: -> {questions, sources} for one level
// o: { search(query, signal) -> [{title,url,snippet}] | text, fetchPage(url, signal) -> html, ask(messages, signal) -> text, parseResults, siteOf, signal, n, gate() }
async function writeLevel(topic, level, o) {
  const n = o.n || TARGET, signal = o.signal;
  const queries = level <= 1 ? [topic, topic + ' facts', topic + ' explained', 'what is ' + topic] : [topic + ' advanced', topic + ' in depth', topic + ' detailed explanation', topic + ' research'];
  const seenSites = new Set(), seenQ = new Set(o.avoid || []), questions = [], sources = [];
  for (const query of queries) {
    if (questions.length >= n || (signal && signal.aborted)) break;
    let results = []; try { results = o.parseResults(await o.search(query, signal)); } catch (e) { if (signal && signal.aborted) break; }
    for (const r of results.slice(0, 5)) {
      if (questions.length >= n || (signal && signal.aborted)) break;
      const site = o.siteOf(r.url); if (!site || seenSites.has(site)) continue;
      if (o.gate && !o.gate()) throw Object.assign(new Error('paused'), { paused: true });
      let text = ''; try { text = pageText(await o.fetchPage(r.url, signal)).slice(0, 6000); } catch (e) { if (signal && signal.aborted) break; }
      if (text.length < 300) continue;
      seenSites.add(site);
      let qs = []; try { qs = parseQuestions(await o.ask([{ role: 'system', content: WRITER_SYSTEM }, { role: 'user', content: 'Topic: ' + topic + (level > 1 ? ' (harder questions, level ' + level + ')' : '') + '\nPage (' + r.url + '):\n' + text + '\nAnswer with the JSON array only.' }], signal)); } catch (e) { if (signal && signal.aborted) break; }
      const page = norm(text); let used = 0;
      for (const x of qs.slice(0, 4)) {
        const q = String(x.q).trim().slice(0, 240), ans = String(x.answer).trim().slice(0, 80), k = norm(q);
        if (!q || !ans || seenQ.has(k) || !page.includes(norm(ans))) continue;   // source-backed: the answer must be on the page
        seenQ.add(k); used++;
        questions.push({ id: 'L' + level + 'q' + (questions.length + 1), q, answer: ans, quote: String(x.quote || '').slice(0, 300), source_url: r.url, source_site: site });
        if (questions.length >= n) break;
      }
      if (used) sources.push({ url: r.url, site });
    }
  }
  return { questions, sources };
}

// the examiner: Glim answers each question, guess + confidence first, then the grade against the source answer
// o: { ask(messages, signal) -> text, notes: [string] (what Glim learned about the topic), signal, gate() }
const EXAM_SYSTEM = 'Answer the question from what you know and the notes given. Reply with ONE JSON object and nothing else: {"answer": "a short answer, 1 to 6 words", "confidence": a number from 0 to 1}.';
async function takeLevel(quiz, level, o) {
  const L = (quiz.levels || []).find((x) => x.level === level); if (!L || !L.questions.length) return null;
  const guesses = [];
  for (const q of L.questions) {
    if (o.signal && o.signal.aborted) return null;
    if (o.gate && !o.gate()) return null;
    const notes = (o.notes || []).slice(-15).map((n) => '- ' + n).join('\n');
    let text = ''; try { text = await o.ask([{ role: 'system', content: EXAM_SYSTEM }, { role: 'user', content: (notes ? 'Notes:\n' + notes + '\n' : '') + 'Question: ' + q.q }], o.signal); } catch (e) { if (o.signal && o.signal.aborted) return null; }
    let ans = '', conf = 0.5;
    try { const s = String(text), a = s.indexOf('{'), b = s.lastIndexOf('}'); const j = JSON.parse(s.slice(a, b + 1)); ans = String(j.answer || ''); conf = Math.max(0, Math.min(1, Number(j.confidence))); if (!Number.isFinite(conf)) conf = 0.5; } catch (e) { ans = String(text || '').slice(0, 80); }
    // the guess is recorded BEFORE it is checked
    const g = { id: q.id, guess: ans.slice(0, 80), confidence: conf };
    g.correct = grade(g.guess, q);
    guesses.push(g);
  }
  const pct = Math.round(100 * guesses.filter((g) => g.correct).length / guesses.length);
  return { level, pct, guesses, n: guesses.length };
}

// the score line, e.g. "black holes Lv1 81% · Lv2 30%" (official scores; unofficial ones marked with *)
function scoreLevels(quiz) {
  return (quiz && quiz.levels || []).map((L) => {
    const off = (quiz.scores || []).filter((s) => s.level === L.level && s.official).slice(-1)[0];
    const any = (quiz.scores || []).filter((s) => s.level === L.level).slice(-1)[0];
    return { level: L.level, pct: off ? off.pct : any ? any.pct : null, official: !!off, n: L.questions.length };
  });
}
function scoreLine(quiz) {
  if (!quiz) return '';
  const lv = scoreLevels(quiz);
  return quiz.topic + ' ' + (lv.length ? lv.map((x) => 'Lv' + x.level + ' ' + (x.pct == null ? '–' : x.pct + '%' + (x.official ? '' : '*'))).join(' · ') : 'writing quiz…');
}
// record a score; returns {quiz, levelUp} (a harder level is due once the newest level reaches 80% officially)
function recordScore(quiz, result, official, now) {
  quiz.scores = (quiz.scores || []).concat([{ level: result.level, pct: result.pct, n: result.n, official: !!official, at: now || Date.now() }]).slice(-200);
  const newest = Math.max(...quiz.levels.map((l) => l.level));
  const levelUp = !!official && result.level === newest && result.pct >= LEVEL_UP;
  return { quiz, levelUp };
}

// Studier prompts are built WITHOUT the quiz; this check runs on every one anyway. A prompt that contains a locked question (e.g. a
// wonder-list item that came from a quiz miss) is rebuilt from the bare topic. -> messages
function safeStudier(build, job, store) {
  const m = build(job);
  if (!store || !store.leaks(m)) return m;
  return build({ ...job, topic: job.base || 'a new angle of ' + String(job.kind || 'the topic'), kind: 'learn' });
}

module.exports = { safeStudier, QuizStore, writeLevel, takeLevel, grade, onTopic, scoreLine, scoreLevels, recordScore, pageText, parseQuestions, slug, stems, TARGET, LEVEL_UP, WRITER_SYSTEM, EXAM_SYSTEM };
