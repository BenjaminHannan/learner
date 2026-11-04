'use strict';
// The little scientist, wired like main.js does it: bored urge -> Mote pool -> experiment (guesses first, then the test) ->
// checker labels + a surprise on the existing sleep path. Fake model; a fake sandbox where noted, the real one where noted.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { Scientist, KINDS, checkable, parseGuess, program, BANK } = require('../src/scientist');
const { Checker } = require('../src/checker');
const { MotePool } = require('../src/motepool');
const M = require('../src/memgauge');
const S = require('../src/senses');
const DiaryAO = require('../src/diary-ao');
const { TruthNotes } = require('../src/truthnotes');
const Sandbox = require('../src/sandbox');
const Puzzles = require('../src/games/puzzles');

const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'sci-'));
const tick = () => new Promise((r) => setImmediate(r));
async function idle(pool) { for (let i = 0; i < 400 && pool.count(); i++) await new Promise((r) => setTimeout(r, 5)); }

// a fake sandbox: every program "prints" TRUTH (so the test controls which guesses are right)
const fakeBox = (o) => ({ available: () => true, runPython: async (code, opt) => { if (o && o.wait) await new Promise((res) => { opt.signal.addEventListener('abort', res); }); if (opt && opt.signal && opt.signal.aborted) return { ok: false, aborted: true, ms: 1 }; return { ok: true, stdout: 'TRUTH\n', stderr: '', exitCode: 0, ms: 3 }; } });

function rig(o) {
  o = o || {};
  const dir = tmp(); let t = 1e12; const now = () => (t += 7);
  const state = new S.AlwaysOnState(dir, { now });
  const checker = new Checker({ dir, now });
  const surprises = [];
  const sci = new Scientist({ dir, checker, now, k: o.k || 4, sandbox: o.sandbox || fakeBox(), pythonOk: o.pythonOk, budget: o.budget,
    onSurprise: (s) => { surprises.push(s); state.addSurprise({ stream: s.stream, what: s.what, kl: s.kl }); } });
  const gate = { budget: 4, why: null }; const calls = [];
  const answer = o.answer || ((msgs, n) => JSON.stringify({ guess: n % 2 ? 'TRUTH' : 'wrong', confidence: 0.8 }));
  const pool = new MotePool({ gate: () => ({ budget: gate.budget, why: gate.why }), prompt: () => [], log: () => {},
    ask: (msgs, signal, opts) => { calls.push({ msgs, signal, opts }); return o.hold ? new Promise((res, rej) => { signal.addEventListener('abort', () => rej(new Error('aborted'))); }) : Promise.resolve(answer(msgs, calls.length)); } });
  return { dir, state, checker, sci, pool, gate, calls, surprises, now };
}

test('scientist: bored -> experiments run through the Mote pool, guesses first; wrong guesses reach the sleep handoff; labels written', async () => {
  const r = rig();
  // python first (fake sandbox), then each puzzle family: whatever the kind, the fake model alternates right / wrong guesses
  const n = r.pool.startBatch(r.sci.jobs(3));
  assert.strictEqual(n, 3);
  await idle(r.pool);
  const ev = r.sci.events();
  const ids = [...new Set(ev.filter((e) => e.event === 'start').map((e) => e.id))];
  assert.strictEqual(ids.length, 3, 'three experiments ran');
  assert.strictEqual(r.calls.length, 12, 'K = 4 guesses each, back-to-back through the pool');
  for (const id of ids) {
    const mine = ev.filter((e) => e.id === id);
    const guesses = mine.filter((e) => e.event === 'guess'), res = mine.find((e) => e.event === 'result');
    assert.ok(res, 'a result for ' + id);
    assert.ok(guesses.length >= 1);
    for (const g of guesses) assert.ok(g.guessAt < res.resultAt, 'guess stamped before the result');
    assert.ok(mine.indexOf(guesses[guesses.length - 1]) < mine.indexOf(res), 'and written before it');
  }
  // the python experiment (fake box prints TRUTH): first try 'wrong' (temperature 0.2) ... agreement pick 2-2 -> the earliest try
  const labels = fs.readFileSync(path.join(r.dir, 'checker-labels.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
  assert.strictEqual(labels.length, 12, 'every guess, right or wrong, is a checker label');
  assert.ok(labels.every((l) => l.source === 'sandbox' && l.truth === 'executor' && l.method === 'executor' && typeof l.correct === 'boolean'));
  assert.ok(labels.some((l) => l.correct) && labels.some((l) => !l.correct));
  assert.ok(labels.every((l) => l.guessAt < l.resultAt));
  // wrong pre-test guesses -> surprises on the SAME path as the guesser's (alwayson-state surprises -> alwayson-sleep.json)
  assert.ok(r.surprises.length >= 1);
  assert.ok(r.surprises.every((s) => s.stream === 'sandbox' && s.truth === 'executor' && s.source === 'sandbox'));
  const truth = new TruthNotes({ dir: r.dir }); truth.add('A maybe note that must never train.', { from: 'mote:day' });
  const f = DiaryAO.writeHandoff(r.dir, DiaryAO.sleepHandoff({ truth, surprises: r.state.surprises }));
  const h = JSON.parse(fs.readFileSync(f, 'utf8'));
  assert.ok(h.surprises.some((s) => s.stream === 'sandbox' && /check/.test(s.text)), 'the sandbox surprise is in the sleep handoff');
  assert.ok(!JSON.stringify(h).includes('must never train'), 'a maybe note never reaches sleep');
  assert.ok(h.surprises.every((s) => !('status' in s)), 'sandbox surprises carry no maybe status');
});

test('scientist: Ben chatting stops it at once (in a guess, and in the test), nothing is labelled or filed', async () => {
  const r = rig({ hold: true });
  r.pool.startBatch(r.sci.jobs(2));
  await tick();
  assert.strictEqual(r.calls.length, 1);
  r.gate.budget = 0; r.gate.why = 'chat'; r.pool.stopAll('chat');   // what main does on agent:send / a typing ping
  assert.ok(r.calls[0].signal.aborted, 'the request in flight was aborted');
  assert.strictEqual(r.pool.count(), 0);
  await tick(); await tick();
  assert.strictEqual(r.calls.length, 1, 'no further model call');
  const ev = r.sci.events();
  assert.ok(!ev.some((e) => e.event === 'result' || e.event === 'label'), 'no result, no label');
  assert.strictEqual(r.surprises.length, 0);
  assert.ok(!fs.existsSync(path.join(r.dir, 'checker-labels.jsonl')));
  // stopped while the sandbox runs
  const r2 = rig({ sandbox: fakeBox({ wait: true }), k: 1 });
  r2.pool.startBatch(r2.sci.jobs(1));
  for (let i = 0; i < 50 && !r2.sci.events().some((e) => e.event === 'guess'); i++) await tick();
  r2.pool.stopAll('chat'); await idle(r2.pool); await tick();
  const ev2 = r2.sci.events();
  assert.ok(ev2.some((e) => e.event === 'stopped'), 'logged as stopped');
  assert.ok(!ev2.some((e) => e.event === 'result'));
});

test('scientist: the memory gauge 🔴 stops it, and nothing starts under 🔴', async () => {
  const r = rig({ hold: true });
  r.pool.startBatch(r.sci.jobs(3)); await tick();
  r.gate.budget = M.budget({ gauge: M.gauge({ pressure: 4 }), away: true, onAC: true }); r.gate.why = 'memory';
  r.pool.tick();
  assert.strictEqual(r.pool.count(), 0); assert.ok(r.calls[0].signal.aborted);
  assert.strictEqual(r.pool.startBatch(r.sci.jobs(2)), 0, 'nothing starts under 🔴');
  // a gate that closes between the guesses and the test: the test does not run
  const r2 = rig({ k: 1 }); let open = true;
  const pool2 = new MotePool({ gate: () => ({ budget: open ? 2 : 0 }), prompt: () => [], ask: async () => { open = false; return JSON.stringify({ guess: 'x', confidence: 0.5 }); } });
  pool2.startBatch(r2.sci.jobs(1)); await idle(pool2);
  assert.ok(r2.sci.events().some((e) => e.event === 'stopped' && e.why === 'gate'));
});

test('scientist: picks the next experiment by learning progress (no novelty bonus) and keeps a per-session budget', () => {
  const r = rig({ pythonOk: false });
  // unmeasured kinds first (fewest tries), in a fixed order
  assert.strictEqual(r.sci.chooseKind().kind, 'puzzle:A');
  for (const k of KINDS) r.sci.st.hist[k] = [0, 0, 0, 0, 0, 0];   // everything measured and mastered
  r.sci.st.hist['puzzle:C'] = [1, 1, 1, 1, 1, 0, 1, 0, 0, 0];      // error falling fast -> learning progress 0.8
  r.sci.st.hist['puzzle:D'] = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1];      // always wrong, no progress (a "noisy TV")
  r.sci.st.hist['game:nim'] = [1, 0, 1, 0, 1, 1, 0, 1, 0, 1];      // flat
  r.sci.startSession();
  const c = r.sci.chooseKind(); assert.strictEqual(c.kind, 'puzzle:C'); assert.match(c.why, /learning progress 0\.80/);
  assert.ok(r.sci.progress('puzzle:D').lp === 0 && r.sci.progress('puzzle:D').recentErr === 1);
  assert.ok(!r.sci.available().includes('python'), 'no python kind when the sandbox is unavailable');
  // budgets
  const b = rig({ budget: { experiments: 2 } });
  assert.strictEqual(b.sci.jobs(5).length, 2);
  b.sci.session.experiments = 2; assert.strictEqual(b.sci.jobs(3).length, 0, 'budget spent: no more jobs this session');
  b.sci.endSession('chat'); assert.strictEqual(b.sci.jobs(3).length, 2, 'a new bored session gets a fresh budget');
});

test('scientist: held-out puzzle rules are never practised; practice seeds stay above the held-out range', () => {
  const r = rig({ pythonOk: false });
  for (let s = 100000; s < 100200; s++) for (const f of Puzzles.FAMILIES) { const t = r.sci.task('puzzle:' + f, s); if (t) assert.ok(Puzzles.TRAIN[f].includes(t.rule)); }
  assert.ok(r.sci.st.seed >= 100000);
});

test('scientist: checkable Learn topics add sandbox drills; parseGuess is strict', () => {
  assert.strictEqual(checkable('python loops'), 'code'); assert.strictEqual(checkable('logic puzzles'), 'puzzle'); assert.strictEqual(checkable('black holes'), null);
  const r = rig(); r.sci.startSession({ learnTopic: 'python lists' });
  assert.strictEqual(r.sci.chooseKind().kind, 'python-own');
  assert.deepStrictEqual(parseGuess('<think>hm</think>{"guess": 45, "confidence": 80}'), { guess: '45', confidence: 0.8, code: null });
  assert.strictEqual(parseGuess('no json'), null); assert.strictEqual(parseGuess('{"confidence": 1}'), null);
  assert.strictEqual(BANK.length >= 20, true); assert.strictEqual(program(100007), program(100007), 'programs are seeded');
});

const real = process.platform !== 'darwin' || !Sandbox.available() ? 'needs the macOS sandbox' : false;
test('scientist (real sandbox): a python experiment runs for real; a wrong guess is a surprise with the true output', { skip: real }, async () => {
  const r = rig({ sandbox: Sandbox, k: 2, answer: () => JSON.stringify({ guess: 'definitely not the output', confidence: 0.9 }) });
  r.sci.startSession();
  const out = await r.sci.runOne({ ask: async (m) => r.pool.o.ask(m, new AbortController().signal), signal: new AbortController().signal, gateOk: () => true });
  assert.strictEqual(out.ran, true); assert.strictEqual(out.kind, 'python'); assert.strictEqual(out.right, false);
  const code = r.sci.events().find((e) => e.event === 'start');
  assert.ok(out.surprise && out.surprise.what.includes(Sandbox.normOut(out.truth).split('\n')[0].slice(0, 20)), out.surprise && out.surprise.what);
  assert.ok(code);
  // a Mote-written program about a checkable Learn topic
  const r2 = rig({ sandbox: Sandbox, answer: () => JSON.stringify({ code: 'xs = [3, 1, 2]\nxs.sort()\nprint(xs)', guess: '[1, 2, 3]', confidence: 0.7 }) });
  r2.sci.startSession({ learnTopic: 'python lists' });
  const o2 = await r2.sci.runOne({ ask: async (m) => r2.pool.o.ask(m, new AbortController().signal), signal: new AbortController().signal, gateOk: () => true });
  assert.strictEqual(o2.kind, 'python-own'); assert.strictEqual(o2.right, true); assert.strictEqual(Sandbox.normOut(o2.truth), '[1, 2, 3]');
});

test('main: experiments start ONLY from the bored urge through the Mote pool; chat ends the session; checker picks K tries', () => {
  const m = fs.readFileSync(path.join(__dirname, '..', 'main.js'), 'utf8');
  const uses = m.split('aoScientist().jobs(').length - 1;
  assert.strictEqual(uses, 1, 'one place makes experiment jobs');
  const urge = m.slice(m.indexOf('function aoUrgeTick()'), m.indexOf('function aoMaybeShare()'));
  assert.match(urge, /aoUrges\.isBored\(\) && !aoPool\.count\(\)/);
  assert.match(urge, /const g = aoMoteGate\(\);\s*if \(g\.budget > 0\)/);
  assert.match(urge, /aoScientist\(\)\.jobs\(nSci/); assert.match(urge, /aoPool\.startBatch\(topics\.concat\(sci\)\)/);
  assert.match(m, /aoPool\.stopAll\('chat'\); aoStopChecks\(\); aoStopQuiz\(\); aoSciEnd\('chat'\);/);
  assert.match(m, /tries: \(\) => aoTries\(\), pick: \(job, parsed\) => aoPickThought\(job, parsed\)/);
  assert.match(m, /onSurprise: \(x\) => \{ if \(aoState\) \{ aoState\.addSurprise\(\{ stream: x\.stream, what: x\.what, kl: x\.kl \}\)/, 'the same surprise path as the guesser');
  assert.match(m, /aoChecker\(\)\.settled\(n\.text, n\.status === 'confirmed'\)/, 'calibration pairs when the truth check settles');
  assert.match(m, /checkerLearned === true/, 'the learned head is opt-in');
});
