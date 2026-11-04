'use strict';
// Always-on v2 phase 6: the locked Learn quiz, graded against its sources, never shown to the studiers.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const vm = require('vm');
const Q = require('../src/quiz');
const T = require('../src/truthnotes');
const main = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');

const PAGES = {
  'https://en.wikipedia.org/wiki/Black_hole': '<html><body><p>A black hole is a region of spacetime where gravity is so strong that nothing can escape. The boundary is called the event horizon. ' + 'x '.repeat(200) + '</p></body></html>',
  'https://science.nasa.gov/black-holes': '<html><body><p>The first image of a black hole was released in 2019 by the Event Horizon Telescope. ' + 'y '.repeat(200) + '</p></body></html>',
  'https://www.space.com/bh': '<p>Stellar black holes form when massive stars collapse. Sagittarius A* is the black hole at the center of the Milky Way. ' + 'z '.repeat(200) + '</p>'
};
const fakeSearch = async () => Object.keys(PAGES).map((url) => ({ title: 't', url, snippet: '' }));
const fakeFetch = async (url) => PAGES[url] || '';
const fakeWriter = async (messages) => {
  const page = messages[1].content;
  if (page.includes('wikipedia')) return JSON.stringify([{ q: 'What is the boundary of a black hole called?', answer: 'the event horizon', quote: 'The boundary is called the event horizon.' }, { q: 'Made-up question?', answer: 'not on the page', quote: '' }]);
  if (page.includes('nasa')) return JSON.stringify([{ q: 'In what year was the first image of a black hole released?', answer: '2019', quote: '' }, { q: 'Which telescope took it?', answer: 'Event Horizon Telescope', quote: '' }]);
  return JSON.stringify([{ q: 'What black hole is at the center of the Milky Way?', answer: 'Sagittarius A*', quote: '' }, { q: 'What collapses to form stellar black holes?', answer: 'massive stars', quote: '' }]);
};
async function writeQuiz(dir) {
  const r = await Q.writeLevel('black holes', 1, { search: fakeSearch, fetchPage: fakeFetch, ask: fakeWriter, parseResults: T.parseResults, siteOf: T.siteOf });
  const store = new Q.QuizStore(dir);
  store.save({ topic: 'black holes', status: 'ready', levels: [{ level: 1, questions: r.questions, sources: r.sources }], scores: [] });
  return { r, store };
}

test('the writer builds a quiz from several sites; every answer is on its source page, with the URL', async () => {
  const { r } = await writeQuiz(fs.mkdtempSync(path.join(os.tmpdir(), 'quiz-')));
  assert.strictEqual(r.questions.length, 5, 'the made-up question (answer not on the page) is dropped');
  assert.deepStrictEqual([...new Set(r.questions.map((q) => q.source_site))].sort(), ['nasa.gov', 'space.com', 'wikipedia.org']);
  for (const q of r.questions) assert.ok(Q.pageText(PAGES[q.source_url]).toLowerCase().includes(q.answer.toLowerCase()), q.q);
});

test('grading checks the stored source answer by text, not Glim\'s opinion', () => {
  const q = { answer: 'the event horizon' };
  assert.ok(Q.grade('Event horizon', q)); assert.ok(Q.grade('It is called the event horizon.', q));
  assert.ok(!Q.grade('the photon sphere', q)); assert.ok(!Q.grade('', q));
  assert.ok(Q.grade('2019', { answer: '2019' })); assert.ok(!Q.grade('2018', { answer: '2019' }));
  assert.ok(Q.grade('Sagittarius A*', { answer: 'Sagittarius A*' }));
});

test('the examiner records guess + confidence before grading; a level-up needs 80% on an OFFICIAL (after-sleep) score', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'quiz-'));
  const { store } = await writeQuiz(dir);
  const z = store.load('black holes');
  const right = { 'What is the boundary of a black hole called?': 'event horizon', 'In what year was the first image of a black hole released?': '2019', 'Which telescope took it?': 'Event Horizon Telescope', 'What black hole is at the center of the Milky Way?': 'Sagittarius A*' };
  const ask = async (m) => { const q = m[1].content.split('Question: ')[1]; return JSON.stringify({ answer: right[q] || 'neutron stars', confidence: right[q] ? 0.8 : 0.9 }); };
  const res = await Q.takeLevel(z, 1, { ask, notes: [] });
  assert.strictEqual(res.pct, 80);
  assert.deepStrictEqual(Object.keys(res.guesses[0]), ['id', 'guess', 'confidence', 'correct']);
  const miss = res.guesses.find((g) => !g.correct); assert.strictEqual(miss.guess, 'neutron stars'); assert.strictEqual(miss.confidence, 0.9);
  assert.strictEqual(Q.recordScore(z, res, false).levelUp, false, 'unofficial 80% does not add a level');
  assert.strictEqual(Q.scoreLine(z), 'black holes Lv1 80%*');
  assert.strictEqual(Q.recordScore(z, res, true).levelUp, true, 'official 80% adds a harder level');
  assert.strictEqual(Q.scoreLine(z), 'black holes Lv1 80%');
  assert.deepStrictEqual(Q.scoreLevels(z), [{ level: 1, pct: 80, official: true, n: 5 }]);
  // stopping mid-quiz gives no score
  const ctl = new AbortController(); ctl.abort();
  assert.strictEqual(await Q.takeLevel(z, 1, { ask, signal: ctl.signal }), null);
});

// the studier prompt builders, taken from main.js as they are (MOTE_SYSTEM / MOTE_WHY / aoMotePrompt and the Learn helpers' LEARN_MOTE)
function mainBuilders() {
  const grab = (start, end) => main.slice(main.indexOf(start), main.indexOf(end, main.indexOf(start)));
  const src = grab("const MOTE_SYSTEM = ", "let aoMoteClaims") + '\n' + grab("const LEARN_ANGLES = ", "// Learn mode: \"go learn X\"") + '\nthis.out = { aoMotePrompt, LEARN_MOTE, LEARN_ANGLES };';
  const ctx = {}; vm.runInNewContext(src.replace(/^let /gm, 'var ').replace(/^const /gm, 'var '), ctx);
  return ctx.out;
}

test('studier prompts never contain locked quiz questions (bored Motes, Learn helper Motes, quiz-miss wonder items)', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'quiz-'));
  const { store } = await writeQuiz(dir);
  const qs = store.allQuestions(); assert.strictEqual(qs.length, 5);
  const B = mainBuilders();
  const jobs = [{ kind: 'learn', topic: 'black holes' }, { kind: 'wonder', topic: 'the weak spots of black holes' }, { kind: 'day', topic: 'black holes' }];
  for (const job of jobs) {
    const m = Q.safeStudier(B.aoMotePrompt, job, store);
    const text = JSON.stringify(m);
    for (const q of qs) assert.ok(!text.includes(q), 'a bored Mote prompt contains a quiz question: ' + q);
    assert.ok(!store.leaks(m));
  }
  for (const angle of ['', ...B.LEARN_ANGLES]) { const p = B.LEARN_MOTE('black holes', angle); for (const q of qs) assert.ok(!p.includes(q)); assert.ok(!store.leaks(p)); }
  // even if a question slipped into a job topic, the guard rebuilds the prompt without it
  const bad = { kind: 'wonder', topic: qs[0], base: 'black holes' };
  assert.ok(store.leaks(B.aoMotePrompt(bad)), 'the raw prompt would leak');
  const safe = Q.safeStudier(B.aoMotePrompt, bad, store);
  assert.ok(!store.leaks(safe)); assert.match(JSON.stringify(safe), /Topic: black holes/);
  // quiz misses go on the wonder list as "weak spot in <topic> (quiz id)" and main maps them to the bare topic
  assert.match(main, /aoState\.addWonder\('weak spot in ' \+ z\.topic \+ ' \(quiz ' \+ g\.id \+ '\)'/);
  assert.match(main, /replace\(\/\^weak spot in \(\.\+\?\) \\\(quiz \[\^\)\]\*\\\)\$\/, 'the weak spots of \$1'\)/);
  assert.match(main, /prompt: \(job\) => QuizMod\.safeStudier\(aoMotePrompt, job, aoQuizS\(\)\)/);
});

test('drift guard: a study step that is no longer about the topic is skipped', () => {
  assert.ok(Q.onTopic('Black holes bend light.', 'black holes'));
  assert.ok(Q.onTopic('The event horizon hides the singularity.', 'black holes', ['The event horizon is the boundary of a black hole', 'A singularity is at the center']));
  assert.ok(!Q.onTopic('The best pizza in Chicago is deep dish.', 'black holes', ['The event horizon is the boundary']));
  assert.match(main, /kept = claims\.filter\(\(c\) => QuizMod\.onTopic\(c, job\.topic, vocab\)\)/);
});

test('main: the quiz runs only when the Mote gate is open, chat aborts it, official = after sleep, Ben can view it', () => {
  assert.match(main, /const aoQuizGate = \(\) => aoMoteGate\(\)\.budget > 0;/);
  assert.match(main, /aoStopChecks\(\); aoStopQuiz\(\);/);
  assert.match(main, /if \(aoQuizLastSleep && !sl\.asleep\) aoQuizOfficialDue = true/);
  assert.match(main, /h\('learn:quiz', /);
  assert.match(fs.readFileSync(path.join(__dirname, '..', 'renderer', 'learnbtn.js'), 'utf8'), /desk\.learn\.quiz/);
});
