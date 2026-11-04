'use strict';
// I3 two-speed core, part 6: the REAL slow brain's side of the intent channel (prompt + reply parsing). Game-agnostic.
// The model (Nanbeige) is shown the adapter's vocabulary, the scene in words, the goal and the plan memory (done / remaining), and
// replies with tactical calls, one per line. Replies are parsed by core/intent.js; anything not in the vocabulary is rejected.
// Not wired into the live loop yet (the app's two-speed practice uses the stand-in brain in simulated time); real-model numbers
// (validity, seconds per call) come from premonition-sleeplab-i3/real/.
const { describe, parse } = require('./intent');

// need: 'call' (the one next tactical call) | 'plan' (the remaining steps, in order)
function buildPrompt(adapter, obs, view, need) {
  const sys = 'You control a game character through short command codes. Use ONLY these codes, written exactly like this:\n' + describe(adapter.vocab) +
    '\nAnswer with code lines only: no other words.';
  const memory = view && view.done && view.done.length ? 'Already done (you cannot see this on screen): ' + view.done.join(', ') + '.' : 'Nothing done yet.';
  const user = 'Goal: ' + adapter.goal + '.\n' + memory + '\nNow: ' + adapter.describe(obs) + (view && view.surprise ? '\nSurprise: ' + view.surprise + '.' : '') +
    (need === 'plan' ? '\nWrite the remaining steps, one code per line, in order.' : '\nWrite the ONE next code.');
  return { system: sys, user };
}
function parseCalls(vocab, text, max) {
  const out = [], bad = [];
  for (const line of String(text || '').split('\n').map((l) => l.trim()).filter(Boolean).slice(0, max || 12)) { const r = parse(vocab, line); if (r.ok) out.push(r.call); else bad.push(line.slice(0, 80)); }
  return { calls: out, bad };
}

module.exports = { buildPrompt, parseCalls };
