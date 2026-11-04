'use strict';
// "Poking vs reading" (ingredients plan step 2): the experiment harness. SET UP, NOT RUN: it needs real nights (real sleeps of the
// real model). Pre-registered plan and pass marks: desk/docs/ingredients-decisions-A.md, section "The experiment set up but not run".
//
//   node tools/poking-vs-reading.js make  --out DIR [--nights 5] [--per-night 40] [--seed 1]
//        writes DIR/plan.json, DIR/eval-heldout.jsonl (what does this print? on held-out seeds + unseen puzzle rules),
//        DIR/night-N-items.jsonl (the SAME practice items for both arms, practice seeds >= 100000, TRAIN rules only)
//   node tools/poking-vs-reading.js cards --out DIR --night N --poke-log scientist-log.jsonl
//        builds the two arms' sleep cards for night N with the SAME card budget:
//          poke  = the night's surprises (its wrong pre-test guesses, with the truth), topped up with its right ones
//          read  = the same number of cards drawn from the same items, shown as worked examples (no guess first)
//   node tools/poking-vs-reading.js score --eval DIR/eval-heldout.jsonl --answers ANSWERS.jsonl
//        ANSWERS rows: {id, answer}. Prints accuracy overall / python / puzzles (exact-output and puzzle-answer matching).
//   node tools/poking-vs-reading.js dry --out DIR
//        a fake-answer smoke test of make + cards + score (no model, no sleep): checks that the harness itself works.
const fs = require('fs');
const path = require('path');
const { program, PRACTICE_SEED0 } = require('../src/scientist');
const Puzzles = require('../src/games/puzzles');
const { normOut } = require('../src/sandbox');
const { rng } = require('../src/games');

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > 0 ? process.argv[i + 1] : d; };
const jsonl = (f, rows) => fs.writeFileSync(f, rows.map((r) => JSON.stringify(r)).join('\n') + '\n');
const readJsonl = (f) => fs.readFileSync(f, 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l));

// held-out evaluation: python programs on seeds 1..9999 (never practised: practice seeds start at 100000) + HELD puzzle rules
function evalSet(n, seed) {
  const r = rng(seed || 1), out = [];
  for (let i = 0; i < n; i++) { const s = 1 + Math.floor(r() * 9998); out.push({ id: 'py-' + s, kind: 'python', seed: s, question: 'What exactly does this Python 3 program print?\n' + program(s), truth: null }); }
  for (const f of Puzzles.FAMILIES) for (const rule of Puzzles.HELD[f]) for (let k = 0; k < Math.max(1, Math.round(n / 20)); k++) {
    const p = Puzzles.make(f, rule, 1 + Math.floor(r() * 9998)); if (p) out.push({ id: 'pz-' + f + '-' + rule + '-' + p.seed, kind: 'puzzle', family: f, rule, held: true, question: p.puzzle, truth: p.answer });
  }
  return out;
}
// the practice items of night N (identical for both arms)
function nightItems(night, perNight) {
  const out = []; const base = PRACTICE_SEED0 + 50000 + night * 1000;
  for (let i = 0; i < perNight; i++) {
    const s = base + i;
    if (i % 2 === 0) out.push({ id: 'n' + night + '-py-' + s, kind: 'python', seed: s, code: program(s) });
    else { const f = Puzzles.FAMILIES[i % Puzzles.FAMILIES.length], rule = Puzzles.TRAIN[f][s % Puzzles.TRAIN[f].length]; const p = Puzzles.make(f, rule, s); if (p) out.push({ id: 'n' + night + '-pz-' + s, kind: 'puzzle', family: f, rule, question: p.puzzle, truth: p.answer }); }
  }
  return out;
}
function make(out, nights, perNight, seed) {
  fs.mkdirSync(out, { recursive: true });
  const ev = evalSet(200, seed);
  jsonl(path.join(out, 'eval-heldout.jsonl'), ev);
  for (let n = 1; n <= nights; n++) jsonl(path.join(out, 'night-' + n + '-items.jsonl'), nightItems(n, perNight));
  const plan = { made: new Date().toISOString(), nights, perNight, evalItems: ev.length, note: 'python truths are filled by running each program in src/sandbox.js before scoring (fillTruths)', passMark: 'poke >= read + 10 points on eval-heldout; general set drop <= 2 points; proven wrong if poke <= read' };
  fs.writeFileSync(path.join(out, 'plan.json'), JSON.stringify(plan, null, 1));
  return plan;
}
// run the held-out python programs in the sandbox once to get their true outputs (needs macOS sandbox-exec)
async function fillTruths(file) {
  const { runPython } = require('../src/sandbox');
  const rows = readJsonl(file);
  for (const r of rows) if (r.kind === 'python' && r.truth == null) { const x = await runPython(program(r.seed)); r.truth = x.ok ? normOut(x.stdout) : null; }
  jsonl(file, rows); return rows.filter((r) => r.truth != null).length;
}
// both arms' sleep cards for one night, the same card budget
function cards(items, pokeEvents, budget) {
  const byItem = {};
  const results = pokeEvents.filter((e) => e.event === 'result'), sur = pokeEvents.filter((e) => e.event === 'surprise');
  const poke = sur.map((e) => ({ kind: 'surprise', text: e.what })).slice(0, budget);
  // top up with right guesses (as plain worked examples), so both arms train on exactly `budget` cards
  for (const it of items) { if (poke.length >= budget) break; byItem[it.id] = it; poke.push({ kind: 'example', text: worked(it) }); }
  const read = items.slice(0, budget).map((it) => ({ kind: 'example', text: worked(it) }));
  return { poke: poke.slice(0, budget), read, results: results.length };
}
const worked = (it) => it.kind === 'python' ? 'This Python program: ' + String(it.code).replace(/\n/g, ' ⏎ ') + ' prints: ' + (it.truth != null ? it.truth : '(run it to see)') : 'Puzzle: ' + String(it.question).replace(/\n/g, ' ') + ' Answer: ' + it.truth;
function score(evalRows, answers) {
  const a = {}; for (const r of answers) a[r.id] = r.answer;
  const ok = (r) => r.truth != null && a[r.id] != null && (r.kind === 'python' ? normOut(a[r.id]) === normOut(r.truth) : Puzzles.correct(a[r.id], r.truth));
  const part = (rows) => ({ n: rows.length, right: rows.filter(ok).length, pct: rows.length ? Math.round(1000 * rows.filter(ok).length / rows.length) / 10 : null });
  const rows = evalRows.filter((r) => r.truth != null);
  return { all: part(rows), python: part(rows.filter((r) => r.kind === 'python')), puzzles: part(rows.filter((r) => r.kind === 'puzzle')) };
}

module.exports = { evalSet, nightItems, make, fillTruths, cards, score };

if (require.main === module) {
  const cmd = process.argv[2], out = arg('out', '');
  (async () => {
    if (cmd === 'make') { console.log(JSON.stringify(make(out, +arg('nights', 5), +arg('per-night', 40), +arg('seed', 1)), null, 1)); console.log('python truths:', await fillTruths(path.join(out, 'eval-heldout.jsonl'))); }
    else if (cmd === 'cards') { const n = +arg('night', 1); const items = readJsonl(path.join(out, 'night-' + n + '-items.jsonl')); const c = cards(items, readJsonl(arg('poke-log')), +arg('budget', 40)); jsonl(path.join(out, 'night-' + n + '-poke-cards.jsonl'), c.poke); jsonl(path.join(out, 'night-' + n + '-read-cards.jsonl'), c.read); console.log('cards', c.poke.length, c.read.length); }
    else if (cmd === 'score') console.log(JSON.stringify(score(readJsonl(arg('eval')), readJsonl(arg('answers'))), null, 1));
    else if (cmd === 'dry') {
      make(out, 2, 10, 1); const ev = readJsonl(path.join(out, 'eval-heldout.jsonl'));
      const fake = ev.map((r, i) => ({ id: r.id, answer: i % 3 === 0 && r.truth ? r.truth : 'no idea' }));
      console.log('dry score (fake answers, puzzles only have truths before fillTruths):', JSON.stringify(score(ev, fake)));
      const c = cards(readJsonl(path.join(out, 'night-1-items.jsonl')), [{ event: 'surprise', what: 'Python check (sandbox): ...' }], 6); console.log('dry cards:', c.poke.length, c.read.length);
    } else console.log('usage: make | cards | score | dry (see the top of this file)');
  })().catch((e) => { console.error(e); process.exitCode = 1; });
}
