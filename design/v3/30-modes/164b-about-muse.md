# 164b — "About" stage, fresh registration on loop138h

## Problem
On loop138h, "Tell me about Kim." and "What do you know about Kim?" fall
through to the long fallback even when Kim has stored facts. Exp 164 built
exactly this feature on loop150 and the director's probe showed it works, but
164 is a registered FAIL (sealed files edited after the seal) and was never
merged. 164b ports the current 164 about-stage onto the current base loop138h
and registers it cleanly. One change only.

## Design
`scripts/fable_loop164b_agent.py` (new file; 138h and 164 files imported
read-only, never edited):

- `About164bMixin.hear()` runs FIRST against the notebook, read-only. It
  reuses 164's rule body verbatim (`match_about`, `fact_sentences`,
  `summary_reply`, `unknown_reply` from `scripts/fable_fix164_about.py`):
  P0 bare summary (`"What do you know?"` -> `"I have N facts about M
  people…"`); P1–P4 (`"What do you know about X?"`, `"Tell me about X"`,
  `"What have I told you about X?"`, `"Anything about X?"`) -> every active
  taught fact with X as subject then as value, max 8 then `"and N more."`;
  unknown X -> the existing unknown-entity reply; zero-fact/ambiguous/error
  -> delegate. Only clarify actions: 0 writes, 0 web, 0 inference.
- Anything unclaimed falls through `super().hear()`, so the whole 138h chain
  (typo, value-screen, verb, name, me, plural, reasoner, sleep, thinker) is
  byte-identical.
- `Loop164bAgentLoop` keeps the 138h act path and tick, plus an idempotent
  raw-USER safety net on about-claimed turns (normally a no-op).

Two disclosed deltas vs 164 (the 138h base requires both): (a) fact sentences
use 138h's USER templates (`"Your sister is Ada."`, value-`"you"`, stored
casing otherwise); (b) bare `"me"` as X reads the reserved USER entity, so
"What do you know about me?" lists the user's facts. Zero USER facts
delegates with no invented strings.

## Why it is safe
Read-only: the stage only calls `nb.resolve`, `nb.facts`/`nb.active`, and
`nb.entities` — the same accessors the reasoner uses. Retracted/superseded
facts never appear (`nb.active`); non-taught sources never appear. X shapes
exclude possessive chains, compounds, and pronouns (except bare "me"), so
teaches and question frames pass through untouched. Pre-seal literal scan:
no about/summary full-turn shape occurs in any bench text (6175), session152
turn (180), or suite case literal (473) outside this experiment's files —
hence the sealed EMPTY move prediction, confirmed by the runs.

## Marks (registered, sealed)
A1 50/50 dialogues OK (38 must-cases exact, 12 near-misses byte-identical,
0 writes on every about-turn). A2 frozen suites byte-identical to 138h
(redteam136 145, cases150 57, f1 46, cases139b 101, redteam143 124,
sessions152 180 turns; 0 new wrong/write). A3 marks123 per-case identical
(0 case-moves; p3-l5z1/p4-1-nonpass/rt81 FAILs inherited). Bench 4x200:
0 moves, 0 new wrong. Max run 278.5 s.

## Limits / non-goals
Only exact full-turn shapes fire ("What do you know about Jonas? Just
kidding." delegates). Multi-word subjects depend on the base teach path.
"About me" with no stored USER facts delegates to the old fallback rather
than saying "nothing stored".

## Reproduce
Seal: `shasum -a 256 -c artifacts/fable-about164b-20260922/SEAL.sha256.txt`.
Then the seven commands in PASSMARKS.md (probe, junk, rt143, sessions, bench,
marks123_all, marksdiff), one at a time, `OMP_NUM_THREADS=1
MKL_NUM_THREADS=1`, `uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B …`.
