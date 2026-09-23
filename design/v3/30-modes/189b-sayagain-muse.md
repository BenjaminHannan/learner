# 189b — Say-again grammar widening on loop189 (Muse)

## Problem

Director probe 10:19 on loop189 (after "Ines's boss is Tom."): "Could
you say that again?" and "What?" got the generic don't-know; "Say that
one more time." and "Say again please." fell into the 137d Say-pretend
rule ("one more time. (I'm treating that as pretend...)"). Only the 8
exact closed-list shapes ("Repeat that.", "Say it again.", ...) worked.
Real users ask politely ("could you...?", "please"), briefly ("What?",
"Huh?", "Again?"), or with variants ("one more time", "once more") —
the closed list missed all of these.

## Design: the one change

New file `scripts/fable_loop189b_agent.py` subclasses the frozen
loop189 stack (`Loop189bAgentLoop` / `Loop189bDaemon`, same
`build_agent` / config pattern). `turn()` runs the widened outermost
repeat stage FIRST, then the completely unchanged loop189 path. The 8
loop189 shapes are a strict subset of the new grammar, so W2 lockstep
identity is structural, not luck.

Matcher (`is_repeat189b` + `BARE189B` + `NO_PREV189B`), whole-turn
only, case-insensitive (lowercase, commas dropped, trailing `.?!`
stripped, one leading/trailing "please" stripped):

- (a) bare shapes: again | what | huh | sorry what | come again |
  pardon | pardon me | sorry | what did you say | what did you just
  say | say again;
- (b) grammar: optional politeness (could/can/would/will you) + verb
  (say | repeat) + optional object (what you just said | what you
  said | it | that) + optional marker (again | one more time | once
  more), with at least one of politeness / object / marker / please
  present — bare "say" or "repeat" alone never match.

The key safety rule: a "Say ..." turn is a repeat request ONLY when
everything after "say" comes from the repeat vocabulary (it, that,
again, one more time, once more, please). Any other content keeps
loop189's pretend behaviour untouched (Ben's ruling: "Say X" =
pretend). So "Say that one more time." echoes while "Say that Lee is
kind.", "Say hello.", "Say it in French.", "Say something nice."
pretend; "Repeat after me: ..." and "Again, Kim's ..." never match.

Semantics (inherited from 189): a match replies with `_prev189`, the
verbatim reply string of the latest NON-REPEAT turn (repeats never
overwrite it, so back-to-back repeats echo the same text), or the one
fixed line "I haven't said anything yet." when nothing was said yet.
Never writes (no notebook event, fact, correction, or self-route; a
repeated "Saved:" is an echo and writes nothing). Never re-runs the
previous turn. Session-local and in-memory only.

Why it cannot move frozen suites: only whole-turn repeat shapes
divert, and the frozen suites contain no such turn (verified by the
0-move W3). The grammar's dangerous neighbours ("sorry" vs "Sorry, I
meant Mira's pet is Rex.", "again" vs "Again, Kim's boss is Lee.",
"what" vs "What is Kim's boss?") are all longer turns that fail the
whole-turn match — each is covered by a sealed W1 trap.

## Evidence

Sealed 44-turn W1 session in lockstep with loop189: 44/44 — 2 noprev
fixed-line with 0 writes, 21 repeat phrasings (19 distinct, incl. the
4 director probes) echoing 189b's own previous non-repeat reply
byte-identical with events unchanged, 12 traps + 9 base turns
byte-identical to loop189 in reply, triples, facts and events. W2:
189's sealed 38-turn session 38/38 identical. W3: 0 moves / 0 new
wrong / 0 new writes on redteam136, cases150, f1, cases139b,
redteam143, sessions152, bench121 (800 items), and marks123
per-case scrubbed-identical with identical suite statuses (only the
seal-predicted volatile rt110 daemon-log statuses line; stock rc=1
from the inherited overall FAIL). Full table in
`artifacts/fable-sayagain189b-20260922/RESULTS.md`.

## Limits

Echoes are byte-verbatim (no rephrasing, translating, summarising).
"Previous reply" is session-local, lost on restart. English-only.
Politeness wrappers beyond the listed modals ("would you mind...?",
"can you ... for me?") do not match. No behaviour change outside the
grammar (proven by the 0-move frozen suites, not by argument).
