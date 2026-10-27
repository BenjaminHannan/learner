# 189 — Say-again: verbatim repeat requests on loop138g (Muse)

## Problem

Director probe 09:40 on loop138g: after "Kim's boss is Lee." →
"Saved: Kim's boss is Lee.", the turn "Say it again." → "it again.
(I'm treating that as pretend, so I won't save it.)". The 137d
Say-pretend rule swallowed a plain repeat request. Ben's ruling stands:
"Say X" stays pretend; only genuine repeat requests change.

## The one change

New file `scripts/fable_loop189_agent.py` subclasses the frozen loop138g
stack (`Loop189AgentLoop`, `Loop189Daemon`, `build_agent189`,
`DEFAULT_CONFIG189`). `turn()` checks `is_repeat189` FIRST — before the
unchanged loop138g path, hence before the 137d Say-pretend rule.

Closed list, whole-turn only, case-insensitive with trailing `.?!`
stripped (`norm189`): say it again | say that again | repeat that |
can you repeat that | what did you say | come again | pardon | sorry.
A match replies with `_prev189` — the verbatim reply string of the
latest NON-REPEAT turn (repeats never overwrite it, so back-to-back
repeats echo the same text) — or the one fixed line "I haven't said
anything yet." when nothing was said yet. Never writes (no notebook
event, fact, correction, or self-route; a repeated "Saved:" is an echo
and writes nothing). Never re-runs the previous turn. In-memory only;
nothing persisted.

Why safe: only exact whole-turn shapes divert. "Say Kim's boss is
Lee.", "Say hello.", "Say it in French.", "Say that Lee is kind."
still take the 137d echo path; "Repeat after me: …" and "Again, Kim's
…" never match. Frozen suites contain no whole-turn repeat shape
(nearest: "Sorry, I meant Mira's pet is Rex." — longer than "sorry").

## Evidence

R1 sealed 38-turn session in lockstep with loop138g: 38/38 — 3 noprev
fixed-line, 13 repeats byte-identical to the previous non-repeat reply
with events unchanged (covering Saved echoes, answers, hearsay/hypo
clarifies, pretend echoes, self replies), 10 traps + 12 base turns
byte-identical in reply, triples, facts and events. R2: 0 moves / 0 new
wrong / 0 new writes on redteam136 (145), cases150 (57), f1 (46),
cases139b (101), redteam143 (124), sessions152 (180 turns), bench121
(800 items, 4 splits); marks123 per-case scrubbed-identical with suite
statuses identical (inherited p3-l5z1 FAIL unchanged). Full table in
`artifacts/fable-sayagain189-20260922/RESULTS.md`.

Post-seal note: the R1 driver (`scripts/fable_fix189_sayagain.py`) was
edited after the seal to compare post-turn snapshots on both loops
(triple snapshot: reply + triples + facts + events); the sealed driver
compared against the pre-base snapshot and failed 4 teaches. Reported
in RESULTS.md with the code; all marks re-run in the open. Agent,
config and cases189.json untouched since the seal.

## Limits

Echoes are byte-verbatim (no rephrasing, translating, or summarising).
"Previous reply" is session-local and lost on restart. The 8 shapes are
English-only and exact — "could you say it again please" does not
match. No behaviour change outside the 8 shapes (proven by the 0-move
frozen runs, not by argument).

What it means: "say it again" now repeats exactly what was just said,
with zero side effects.
What it does not mean: no new obedience, memory, or language ability —
"Say X" orders remain pretend per Ben's ruling.
