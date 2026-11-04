'use strict';
// The little scientist (ingredients plan step 2): in bored mode Glim learns by POKING, not only by reading. It plays in sandboxes
// where the world answers back:
//   python      "what exactly does this program print?" (a built-in, seeded bank of tiny programs) -> run it in src/sandbox.js
//   python-own  a Mote writes its own tiny program about a checkable Learn topic, guesses the output, then runs it
//   puzzle:X    the puzzle generator (src/games/puzzles.js) knows the answer (families A-G, TRAIN rules only)
//   game:X      "what is the state after this move?" in maze / Nim / tic-tac-toe / sliding tiles (the rulebook answers)
// Every experiment: K guesses FIRST (each logged with a timestamp), then the test (logged with its timestamp), then
//   - every guess, right or wrong, becomes a free checker label (userData/checker-labels.jsonl; source sandbox, truth executor)
//   - the checker picks among the K tries (the executor method: a verified-correct try wins)
//   - a WRONG pre-test guess is a surprise -> onSurprise() -> the same path the guesser's surprises use (alwayson-state.json
//     surprises -> alwayson-sleep.json -> sleep). Sandbox truth may train: it is executor truth, never a `maybe`.
// Choosing the next experiment: learning progress (the error rate on that kind of task falling: older window minus recent window),
// as in the Sep 21 bored-mode design. NO novelty bonus. A kind needs MIN_TRIES attempts before its progress can be measured, so
// unmeasured kinds are tried first (that is measurement, not a novelty reward). Budgets per bored session.
// It never runs by itself: main.js hands its jobs to the Mote pool from the bored urge, under the memory gauge and Ben-first gate.
// Pure Node apart from the sandbox; ask / check / clocks are injected.
const fs = require('fs');
const path = require('path');
const Sandbox = require('./sandbox');
const Puzzles = require('./games/puzzles');
const { GAMES, rng } = require('./games');
const { factSurprise } = require('./guesser');

const K_TRIES = 4;
const MIN_TRIES = 3, WIN = 5;
const BUDGET = { experiments: 12, python: 8, sandboxMs: 60000, modelCalls: 60, sessionMs: 2 * 3600000 };
const PRACTICE_SEED0 = 100000;   // practice seeds start here; seeds below 100000 are reserved for held-out tests (never practised)

// ---- the program bank: seeded templates of tiny, deterministic programs (standard library only) ----------------------------------
const WORDS = ['banana', 'rocket', 'level', 'python', 'glimmer', 'kayak', 'orange', 'pepper', 'moon', 'apple', 'tomato', 'river', 'noon', 'cactus'];
const ri = (r, lo, hi) => lo + Math.floor(r() * (hi - lo + 1));
const pk = (r, xs) => xs[Math.floor(r() * xs.length)];
const BANK = [
  (r) => 'print(sum(range(' + ri(r, 0, 5) + ', ' + ri(r, 6, 15) + ')))',
  (r) => { const w = pk(r, WORDS); return 's = "' + w + '"\nprint(s[' + ri(r, 0, 2) + ':' + ri(r, 3, 6) + '])'; },
  (r) => { const xs = Array.from({ length: ri(r, 4, 7) }, () => ri(r, 1, 20)); return 'xs = [' + xs.join(', ') + ']\nprint(xs[-' + ri(r, 1, 3) + '], xs[1::2])'; },
  (r) => { const a = ri(r, -20, 30), b = pk(r, [3, 4, 5, 7]); return 'print(' + a + ' // ' + b + ', ' + a + ' % ' + b + ')'; },
  (r) => 'print([x * x for x in range(' + ri(r, 5, 12) + ') if x % ' + ri(r, 2, 4) + ' == 0])',
  (r) => { const w = pk(r, WORDS); return 'print("' + w + '".upper().count("' + w[ri(r, 0, w.length - 1)].toUpperCase() + '"))'; },
  (r) => { const ws = [pk(r, WORDS), pk(r, WORDS), pk(r, WORDS)]; return 'print("-".join("' + ws.join(' ') + '".split()))'; },
  (r) => { const w = pk(r, WORDS); return 'd = {}\nfor ch in "' + w + '":\n    d[ch] = d.get(ch, 0) + 1\nprint(d)'; },
  (r) => { const ws = Array.from({ length: 4 }, () => pk(r, WORDS)); return 'print(sorted([' + ws.map((w) => '"' + w + '"').join(', ') + '], key=len))'; },
  (r) => { const xs = Array.from({ length: ri(r, 5, 9) }, () => ri(r, 1, 5)); return 'print(len(set([' + xs.join(', ') + '])))'; },
  (r) => 'n = ' + ri(r, 3, 27) + '\nsteps = 0\nwhile n != 1:\n    n = n // 2 if n % 2 == 0 else 3 * n + 1\n    steps += 1\nprint(steps)',
  (r) => 'def f(n):\n    return n if n < 2 else f(n - 1) + f(n - 2)\nprint(f(' + ri(r, 5, 14) + '))',
  (r) => 'x = ' + ri(r, 1, 50) + ' / ' + ri(r, 3, 9) + '\nprint(f"{x:.2f}")',
  (r) => { const a = ri(r, 1, 5), b = ri(r, 1, 5); return 'print(True + True * ' + a + ', ' + a + ' > ' + b + ')'; },
  (r) => { const a = pk(r, WORDS), b = pk(r, WORDS); return 'for i, (a, b) in enumerate(zip("' + a + '", "' + b + '")):\n    if a == b:\n        print(i)\nprint("done")'; },
  (r) => { const w = pk(r, ['ab', 'xo', 'la', 'na']); return 'print(("' + w + '" * ' + ri(r, 2, 4) + ').replace("' + w[0] + '", "' + pk(r, ['-', '*', '']) + '"))'; },
  (r) => 'a = [1, 2, 3]\nb = a\nb.append(' + ri(r, 4, 9) + ')\nprint(a, len(b))',
  (r) => { const x = ri(r, 1, 99), y = ri(r, 1, 99); return 'print(int("' + x + '") + int("' + y + '"), "' + x + '" + "' + y + '")'; },
  (r) => 'print(round(' + ri(r, 0, 6) + '.5), round(' + ri(r, 0, 6) + '.5))',
  (r) => { const ws = Array.from({ length: 4 }, () => pk(r, WORDS)); return 'print(max([' + ws.map((w) => '"' + w + '"').join(', ') + '], key=lambda w: w[-1]))'; },
  (r) => { const n = ri(r, 3, 6), stop = ri(r, 4, 15); return 'count = 0\nfor i in range(' + n + '):\n    for j in range(' + n + '):\n        if i * j > ' + stop + ':\n            break\n        count += 1\nprint(count)'; },
  (r) => 'print(list(range(' + ri(r, 10, 20) + ', ' + ri(r, 0, 5) + ', -' + ri(r, 2, 4) + ')))',
  (r) => { const w = pk(r, WORDS); return 'w = "' + w + '"\nprint(w[::-1], w == w[::-1])'; },
  (r) => 'print(pow(' + ri(r, 2, 9) + ', ' + ri(r, 2, 12) + ', ' + ri(r, 5, 13) + '))',
  (r) => { const a = ri(r, 1, 9), b = ri(r, 1, 9), c = ri(r, 1, 9); return 'print(' + a + ' < ' + b + ' < ' + c + ', ' + a + ' < ' + b + ' > ' + c + ')'; }
];
function program(seed) { const r = rng(seed * 2654435761 >>> 0); const t = BANK[seed % BANK.length]; return t(r); }

// ---- kinds -----------------------------------------------------------------------------------------------------------------------
const PUZZLE_KINDS = Puzzles.FAMILIES.map((f) => 'puzzle:' + f);
const GAME_KINDS = Object.keys(GAMES).map((g) => 'game:' + g);
const KINDS = ['python', ...PUZZLE_KINDS, ...GAME_KINDS];
// a Learn topic the sandbox can check (coding -> the Mote writes programs about it; puzzles / logic -> puzzle drills)
const CODE_TOPIC = /\b(?:python|coding|code|program(?:ming|s)?|loops?|lists?|strings?|dictionar(?:y|ies)|recursion|algorithms?|functions?|variables?)\b/i;
const PUZZLE_TOPIC = /\b(?:puzzles?|logic|patterns?|sequences?|arc|iq|riddles?)\b/i;
function checkable(topic) { const t = String(topic || ''); return CODE_TOPIC.test(t) ? 'code' : PUZZLE_TOPIC.test(t) ? 'puzzle' : null; }

const SYSTEM = 'You are Glim\'s little scientist. You GUESS first; then a test shows the truth, so guess honestly. '
  + 'Reply with ONE JSON object and nothing else: {"guess": "your exact answer as text", "confidence": a number from 0 to 1}.';
const OWN_SYSTEM = 'You are Glim\'s little scientist. Write ONE tiny Python 3 program (at most 12 lines; no input(), no files, no network, no imports except math) '
  + 'that tests something about the topic, then GUESS its exact output before it is run. Reply with ONE JSON object and nothing else: '
  + '{"code": "the program", "guess": "its exact output", "confidence": a number from 0 to 1}.';

function parseGuess(text) {
  let s = String(text || '').replace(/<think>[\s\S]*?<\/think>/gi, '').trim();
  const a = s.indexOf('{'), b = s.lastIndexOf('}');
  if (a < 0 || b <= a) return null;
  let j; try { j = JSON.parse(s.slice(a, b + 1)); } catch (e) { return null; }
  if (!j || typeof j !== 'object' || j.guess === undefined || j.guess === null) return null;
  const guess = (typeof j.guess === 'string' ? j.guess : JSON.stringify(j.guess)).replace(/^```\w*\n?|\n?```$/g, '').slice(0, 2000);
  let c = Number(j.confidence); if (!Number.isFinite(c)) c = 0.5; c = Math.max(0, Math.min(1, c > 1 && c <= 100 ? c / 100 : c));
  const code = typeof j.code === 'string' ? j.code.slice(0, 4000) : null;
  return { guess, confidence: c, code };
}
const oneLine = (s, n) => String(s).replace(/\n/g, ' ⏎ ').replace(/\s+/g, ' ').trim().slice(0, n || 200);

class Scientist {
  // o: { dir (userData; omit = in memory), checker (src/checker.js), now, k (tries), budget, sandbox ({runPython, available}),
  //      onSurprise({stream, what, kl, kind}), onActivity(kind, o), log, pythonOk (default: sandbox available) }
  constructor(o) {
    this.o = o || {}; this.now = this.o.now || Date.now; this.log = this.o.log || (() => {});
    this.checker = this.o.checker; this.k = this.o.k || K_TRIES;
    this.sandbox = this.o.sandbox || Sandbox;
    this.budget = { ...BUDGET, ...(this.o.budget || {}) };
    this.file = this.o.dir ? path.join(this.o.dir, 'scientist.json') : null;
    this.logFile = this.o.dir ? path.join(this.o.dir, 'scientist-log.jsonl') : null;
    this.mem = [];
    this.st = { hist: {}, last: {}, seed: PRACTICE_SEED0, n: 0 };
    if (this.file) { try { const j = JSON.parse(fs.readFileSync(this.file, 'utf8')); if (j && j.hist) this.st = { ...this.st, ...j }; } catch (e) { /* fresh */ } }
    this.session = null; this.learnTopic = null;
  }
  save() { if (!this.file) return; try { fs.mkdirSync(path.dirname(this.file), { recursive: true }); const t = this.file + '.tmp'; fs.writeFileSync(t, JSON.stringify(this.st)); fs.renameSync(t, this.file); } catch (e) { /* in memory */ } }
  // one log line, written at once (so a guess is on disk before its test runs)
  event(e) {
    const r = { t: this.now(), ...e };
    if (this.logFile) { try { fs.mkdirSync(path.dirname(this.logFile), { recursive: true }); fs.appendFileSync(this.logFile, JSON.stringify(r) + '\n'); return r; } catch (err) { /* in memory */ } }
    this.mem.push(r); return r;
  }
  events() { let out = []; if (this.logFile) { try { out = fs.readFileSync(this.logFile, 'utf8').split('\n').filter(Boolean).map((l) => { try { return JSON.parse(l); } catch (e) { return null; } }).filter(Boolean); } catch (e) { /* none */ } } return out.concat(this.mem); }
  pythonOk() { return this.o.pythonOk != null ? !!this.o.pythonOk : !!(this.sandbox.available && this.sandbox.available()); }

  // ---- sessions and budgets ------------------------------------------------------------------------------------------------------
  startSession(o) {
    const now = this.now();
    if (this.session && !this.session.ended && now - this.session.at < this.budget.sessionMs) { if (o && o.learnTopic !== undefined) this.learnTopic = o.learnTopic; return this.session; }
    this.session = { id: 's' + now.toString(36), at: now, experiments: 0, python: 0, sandboxMs: 0, modelCalls: 0, ended: false };
    this.learnTopic = (o && o.learnTopic) || null;
    return this.session;
  }
  endSession(why) { if (this.session && !this.session.ended) { this.session.ended = true; this.session.why = why || 'ended'; } }
  left() {
    const s = this.session; if (!s || s.ended) return 0;
    if (this.now() - s.at >= this.budget.sessionMs || s.modelCalls >= this.budget.modelCalls || s.sandboxMs >= this.budget.sandboxMs) return 0;
    return Math.max(0, this.budget.experiments - s.experiments);
  }
  // n Mote jobs for the pool (each runs ONE experiment; its kind is chosen when it starts, from the latest learning progress)
  jobs(n, o) {
    this.startSession(o);
    const k = Math.min(n | 0, this.left());
    return Array.from({ length: Math.max(0, k) }, (_, i) => ({ kind: 'experiment', topic: 'little scientist #' + (i + 1), run: (ctl) => this.runOne(ctl) }));
  }

  // ---- choosing: learning progress, no novelty bonus ----------------------------------------------------------------------------
  available() {
    const py = this.pythonOk(), s = this.session || {};
    return KINDS.filter((k) => k !== 'python' || (py && (s.python || 0) < this.budget.python));
  }
  progress(kind) {
    const h = this.st.hist[kind] || []; if (h.length < MIN_TRIES) return null;
    const w = Math.min(WIN, Math.floor(h.length / 2)); if (w < 1) return null;
    const recent = h.slice(-w), older = h.slice(-2 * w, -w);
    const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
    return { lp: mean(older) - mean(recent), recentErr: mean(recent), n: h.length };
  }
  chooseKind() {
    const kinds = this.available();
    // a checkable Learn topic adds its drills: every other experiment is one about the topic
    const lt = checkable(this.learnTopic);
    if (lt && this.session && this.session.experiments % 2 === 0) {
      if (lt === 'code' && this.pythonOk() && kinds.includes('python')) return { kind: 'python-own', why: 'Learn topic "' + this.learnTopic + '" is checkable in the sandbox' };
      if (lt === 'puzzle') { const ps = kinds.filter((k) => k.startsWith('puzzle:')); if (ps.length) return { kind: ps[(this.st.n | 0) % ps.length], why: 'Learn topic drill' }; }
    }
    const unmeasured = kinds.filter((k) => (this.st.hist[k] || []).length < MIN_TRIES);
    if (unmeasured.length) { unmeasured.sort((a, b) => (this.st.hist[a] || []).length - (this.st.hist[b] || []).length || KINDS.indexOf(a) - KINDS.indexOf(b)); return { kind: unmeasured[0], why: 'not enough tries yet to measure progress' }; }
    // highest learning progress; mastered kinds (no error lately) only when nothing else is left; ties -> practised longest ago
    const scored = kinds.map((k) => ({ k, p: this.progress(k), last: this.st.last[k] || 0 }));
    const learning = scored.filter((x) => x.p && x.p.recentErr > 0);
    const pool = learning.length ? learning : scored;
    pool.sort((a, b) => (b.p ? b.p.lp : -1) - (a.p ? a.p.lp : -1) || a.last - b.last);
    const best = pool[0];
    return { kind: best.k, why: 'learning progress ' + (best.p ? best.p.lp.toFixed(2) : '?') + ' (recent error ' + (best.p ? best.p.recentErr.toFixed(2) : '?') + ')' };
  }

  // ---- one experiment --------------------------------------------------------------------------------------------------------
  // build the task for a kind: { kind, question (shown to the model), test(signal) -> Promise<{ok, truth, void}>, compare(a, truth), lesson(truth, guess), meta }
  task(kind, seed) {
    if (kind === 'python') {
      const code = program(seed);
      return { kind, code, seed, question: 'What exactly does this Python 3 program print? Give the exact output text (use \\n between lines).\n```python\n' + code + '\n```',
        test: (signal) => this.runCode(code, signal), compare: (a, t) => Sandbox.normOut(a) === Sandbox.normOut(t),
        lesson: (t, g) => 'Python check (sandbox): the program `' + oneLine(code, 160) + '` prints "' + oneLine(t, 80) + '", not "' + oneLine(g, 60) + '" as I guessed.' };
    }
    if (kind.startsWith('puzzle:')) {
      const fam = kind.slice(7), rules = Puzzles.TRAIN[fam]; const rule = rules[seed % rules.length];
      const p = Puzzles.make(fam, rule, seed); if (!p) return null;
      return { kind, seed, rule, question: p.puzzle + '\nGive just the answer.', test: async () => ({ ok: true, truth: p.answer }), compare: (a, t) => Puzzles.correct(a, t),
        lesson: (t, g) => 'Puzzle check (generator): ' + oneLine(p.puzzle, 170) + ' Answer: ' + t + ' (I guessed ' + oneLine(g, 40) + ').' };
    }
    if (kind.startsWith('game:')) {
      const g = GAMES[kind.slice(5)]; const r = rng(seed * 977 + 13);
      let s = g.init(seed);
      for (let i = 0, n = ri(r, 0, 3); i < n && !g.done(s); i++) s = g.step(s, pk(r, g.moves(s)));
      if (g.done(s)) s = g.init(seed + 1);
      const m = pk(r, g.moves(s));
      const after = g.apply ? g.apply(s, m) : g.step(s, m);   // two-player games: only our move (the reply is not predictable)
      const truth = g.stateText(after);
      const fmt = g.name === 'maze' ? 'Answer like "row R, column C" (bumping into a wall # means you stay put).' : g.name === 'nim' ? 'Answer like "piles 1 2 3" (or "I win" if you took the last stone).' : g.name === 'ttt' ? 'Answer like "board X../.O./..." (rows top to bottom, . is empty), or "X wins" / "draw".' : 'Answer like "123/45_/786" (rows top to bottom, _ is the blank).';
      return { kind, seed, question: g.render(s) + '\nIf you play: ' + g.moveText(m) + ', what is the state right after your move? ' + fmt,
        test: async () => ({ ok: true, truth }), compare: (a, t) => Puzzles.correct(a, t),
        lesson: (t, gs) => 'Game check (' + g.name + ' rulebook): from ' + oneLine(g.stateText(s), 60) + ', playing ' + g.moveText(m) + ' gives ' + t + ' (I guessed ' + oneLine(gs, 40) + ').' };
    }
    return null;
  }
  async runCode(code, signal) {
    const s = this.session; if (s) s.python++;
    const r = await this.sandbox.runPython(code, { signal });
    if (s) s.sandboxMs += r.ms || 0;
    if (r.aborted) return { ok: false, stopped: true };
    if (r.timedOut || r.memKilled || r.outKilled || (r.why && /^unavailable|spawn failed|no program/.test(r.why))) return { ok: false, void: true, why: r.why };
    // a program that raises: the truth is its output so far + the error's last line (that is what Python prints)
    const errLine = r.exitCode !== 0 ? (String(r.stderr || '').trim().split('\n').pop() || 'error') : '';
    return { ok: true, truth: (r.stdout || '') + (errLine ? (r.stdout && !r.stdout.endsWith('\n') ? '\n' : '') + errLine : ''), ms: r.ms };
  }
  // ctl: { ask(messages, opts) -> text (gate-checked by the pool), signal, gateOk() }. -> the experiment record
  async runOne(ctl) {
    const signal = ctl.signal, ask = ctl.ask, gateOk = ctl.gateOk || (() => true);
    if (!this.session) this.startSession();
    if (this.left() <= 0) return { ran: false, why: 'budget' };
    const ch = this.chooseKind();
    const seed = this.st.seed++; this.st.n++; this.save();
    const id = 'x' + this.now().toString(36) + '-' + seed;
    const own = ch.kind === 'python-own';
    const tk = own ? null : this.task(ch.kind, seed);
    if (!own && !tk) return { ran: false, why: 'no task' };
    const kind = own ? 'python-own' : tk.kind, question = own ? 'Topic: ' + this.learnTopic : tk.question;
    this.event({ id, event: 'start', kind, why: ch.why, seed, session: this.session.id });
    // 1. guesses BEFORE the test (each one logged as soon as it exists)
    const tries = [];
    const k = own ? 1 : this.k;
    for (let i = 0; i < k; i++) {
      if (signal && signal.aborted) break;
      this.session.modelCalls++;
      const msgs = own ? [{ role: 'system', content: OWN_SYSTEM }, { role: 'user', content: 'Topic: ' + this.learnTopic + '\nAnswer with the JSON object only.' }]
        : [{ role: 'system', content: SYSTEM }, { role: 'user', content: question + '\nAnswer with the JSON object only.' }];
      let text = null; try { text = await ask(msgs, { temperature: i === 0 ? 0.2 : 0.8, maxTokens: own ? 400 : 200 }); } catch (e) { break; }
      const g = parseGuess(text); const at = this.now();
      if (!g) { this.event({ id, event: 'guess-unreadable', i, at }); continue; }
      tries.push({ i, guess: g.guess, confidence: g.confidence, code: g.code, at });
      this.event({ id, event: 'guess', i, guess: g.guess.slice(0, 400), confidence: g.confidence, guessAt: at });
    }
    if (signal && signal.aborted) { this.event({ id, event: 'stopped', before: 'test' }); return { ran: false, why: 'stopped', id }; }
    if (!tries.length) { this.event({ id, event: 'void', why: 'no readable guess' }); return { ran: false, why: 'no guess', id }; }
    // the pre-test pick (nothing can be checked yet: agreement among the tries; untested as a picker)
    const guesses = tries.map((t) => t.guess);
    const pre = this.checker ? this.checker.pick(question, guesses, {}) : { index: 0, answer: guesses[0], p_correct: tries[0].confidence, method: 'self' };
    const guessAt = Math.max(...tries.map((t) => t.at));
    // 2. the test (only if Ben-first / the memory gauge still allow it)
    if (!gateOk()) { this.event({ id, event: 'stopped', before: 'test', why: 'gate' }); return { ran: false, why: 'gate', id }; }
    // the test always happens strictly after the last guess (an instant test, e.g. the puzzle generator, could share its millisecond)
    while (this.now() <= guessAt) await new Promise((res) => setTimeout(res, 1));
    let test;
    const ownTask = own ? (tries[0].code ? { kind, code: tries[0].code, compare: (a, t) => Sandbox.normOut(a) === Sandbox.normOut(t), lesson: (t, g) => 'Python check (sandbox, my own program about ' + this.learnTopic + '): `' + oneLine(tries[0].code, 150) + '` prints "' + oneLine(t, 80) + '", not "' + oneLine(g, 60) + '".' } : null) : null;
    if (own && !ownTask) { this.event({ id, event: 'void', why: 'no program written' }); return { ran: false, why: 'no program', id }; }
    const T = own ? ownTask : tk;
    try { test = own ? await this.runCode(T.code, signal) : await T.test(signal); } catch (e) { test = { ok: false, void: true, why: String(e && e.message || e) }; }
    const resultAt = this.now();
    if (test.stopped || (signal && signal.aborted)) { this.event({ id, event: 'stopped', during: 'test' }); return { ran: false, why: 'stopped', id }; }
    if (!test.ok) { this.event({ id, event: 'void', why: test.why || 'test failed', resultAt }); this.session.experiments++; return { ran: false, why: 'void', id }; }
    const truth = test.truth;
    this.event({ id, event: 'result', truth: String(truth).slice(0, 400), resultAt, guessAt });
    // 3. judge: the executor scores every try; labels for all of them; the pick prefers a verified-correct one
    const right = tries.map((t) => !!T.compare(t.guess, truth));
    const final = this.checker ? this.checker.pick(question, guesses, { check: (a) => !!T.compare(a, truth) }) : { index: right.indexOf(true) >= 0 ? right.indexOf(true) : 0 };
    const preRight = right[pre.index];
    if (this.checker) {
      tries.forEach((t, i) => this.checker.label({ question: own ? 'What does this program print?\n' + T.code : question, answer: t.guess, correct: right[i], p: t.confidence, pMethod: 'self', method: 'executor', source: 'sandbox', truth: 'executor', kind, guessAt: t.at, resultAt, expId: id }));
      if (guesses.length > 1) this.checker.calibrate(pre.p_correct, preRight, { method: 'agreement', kind });
    }
    this.event({ id, event: 'label', n: tries.length, right: right.filter(Boolean).length, preRight, pick: final.index, pickRight: right[final.index] });
    // 4. learning-progress history (the pre-test guess counts: that is what Glim believed before poking)
    const h = this.st.hist[kind] || (this.st.hist[kind] = []); h.push(preRight ? 0 : 1); if (h.length > 40) h.splice(0, h.length - 40);
    this.st.last[kind] = this.now(); this.session.experiments++; this.save();
    // 5. a wrong guess is a surprise -> the sleep path
    let surprise = null;
    if (!preRight) {
      const conf = tries[pre.index].confidence;
      surprise = { stream: 'sandbox', what: T.lesson(Sandbox.normOut(truth), pre.answer), kl: factSurprise(conf, false).surprise, kind, source: 'sandbox', truth: 'executor' };
      try { this.o.onSurprise && this.o.onSurprise(surprise); } catch (e) { this.log('scientist: surprise listener failed', e); }
      this.event({ id, event: 'surprise', what: surprise.what, kl: surprise.kl });
    }
    try { this.o.onActivity && this.o.onActivity('experiment', { kind, right: !!preRight, tries: tries.length, anyRight: right.some(Boolean) }); } catch (e) { /* diary only */ }
    return { ran: true, id, kind, guess: pre.answer, truth, right: !!preRight, anyRight: right.some(Boolean), pick: final.index, surprise, guessAt, resultAt };
  }
  // the diary line
  recap(since) {
    const ev = this.events().filter((e) => e.t >= (since || 0));
    const lab = ev.filter((e) => e.event === 'label'); if (!lab.length) return '';
    const right = lab.filter((e) => e.preRight).length, any = lab.filter((e) => e.right > 0).length, sur = ev.filter((e) => e.event === 'surprise').length;
    const kinds = {}; for (const e of ev) if (e.event === 'start') kinds[e.kind] = (kinds[e.kind] || 0) + 1;
    return 'Little scientist: ' + lab.length + ' experiments (' + Object.entries(kinds).map(([k, n]) => k + ' ' + n).join(', ') + '); my first guess was right ' + right + ' times, at least one of my tries ' + any + ' times; ' + sur + ' surprise' + (sur === 1 ? '' : 's') + ' saved for sleep.';
  }
}

module.exports = { Scientist, program, BANK, KINDS, checkable, parseGuess, SYSTEM, OWN_SYSTEM, BUDGET, K_TRIES, PRACTICE_SEED0 };
