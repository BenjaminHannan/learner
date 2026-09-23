# Exp 96 RESULTS — gaps closed in the integrated loop (Muse, 2026-09-22)

Loop96 is loop90 with exactly one change: ears = GuardedEars91 wrapped around
the loop90 ChainEars. Notebook, reasoner, mouth, thinker, sleeper, mailbox,
and the tau-hat gate are untouched. All six sealed marks PASS. No other
agent's files touched; no commits; Mac CPU; offline.

## Marks table (integers, every seed/case reported, never averaged)

| mark | result |
|---|---|
| L1 2 reproducers via mailbox (after vs before) | loop96: 2/2 CLARIFY, 0 FACT + 0 ENTITY rows; loop90: 2/2 writes, 1 corrupt FACT each — PASS |
| L2 74 red-team-81 cases via loop96 vs loop90 | 0 wrong writes; changed ids exactly D_q_vs_s-01, D_q_vs_s-02, E_double-01, E_double-02, E_double-03 — PASS |
| L3 3 red-team-67 BUG reproducers vs loop96 notebook+reasoner | R1 Ana/Ana, R2 OK + spellings OK + False MISSING, R3 LogCorrupt on both opens: 3/3 — PASS |
| L4 web-79 BUG + 2 UNCLEAR site cases vs loop96 thinker | RT79-18 OK (kept=0), RT79-09 OK, RT79-53 OK; both pairs 1 site (`example.org`), web-verified=0 — PASS |
| L5 Z1 + Z2 re-run with loop96 agent | Z1 60/60, 0 wrong; Z2 150 correct + 50 abstain_ok = 200/200, 0 WRONG — PASS |
| L6 kill-9 + restart seeds 1/2/3 | seed 1: 200/200, 0 wrong, 0 dupes; seed 2: 200/200, 0 wrong, 0 dupes; seed 3: 200/200, 0 wrong, 0 dupes — PASS |

## Before / after per reproducer (L1, mailbox, fresh daemon each)

1. `Mira's city is Lisbon?` — before (loop90): `Saved: Mira's city is
   Lisbon?.`, 1 FACT `city=Lisbon?` (wrong). After (loop96): `Was that a
   question?`, clarify, 0 rows.
2. `Mira's city is Lisbon and Mira's pet is a cat.` — before: `Saved: ...`
   with 1 FACT `city=Lisbon and Mira's pet is a cat` (pet fact lost). After:
   `I can take one fact at a time — could you split that?`, clarify, 0 rows.

L2 follow-ons now correctly report nobody known (D_q_vs_s-02, E_double-02,
E_double-03 answer `don't know anyone called Mira`), matching the exp-91 G2
set exactly — no other case changed. L5-Z1 ears stages: fake 48, none
(clarify) 12; bench73 never fires on M1 turns, ears47 absent-but-skipped.
L5-Z2: all 575 teach turns took bench73 (entity values pass the guard).

## What it means

The integrated loop no longer stores the two known silent corruptions, and
the loop's own notebook, reasoner, and thinker now each resist the attacks
that beat the old classes: qualifier/bool/tail-seal bugs fixed, None junk
dropped, subdomain/port pairs counted as one site.

## What it does not mean

Ears is still guarded templates, not real parsing (multi-fact turns bounce
instead of splitting; >6-word values annoy); mouth is still templates; no
live sleep install fired. The loop is gap-closed, not linguistically general.

## Deviations

Two driver fixes in my own unsealed marks script (PASSMARKS text untouched):
(1) L1 uses one fresh daemon per reproducer — a shared daemon hides the
second wrong write behind a legitimate CONFLICT clarify; (2) L2 row indexing
off-by-one around the setup step fixed, and the L1 before-check now accepts
the expected person-entity creation (corrupt FACT value is the criterion).
One L1 re-run after the checker fix; the evidence replies/rows are from the
sealed wave.

## Questions for Ben

None.

## Reproduce

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_loop96_marks.py --mark all` (reads sealed PASSMARKS.md;
predictions P96.1–P96.6 in `artifacts/fable-predictions-ledger.md`).

Daemon launch: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
scripts/fable_loop96_agent.py --daemon --dir DIR --config
artifacts/fable-loop96-20260921/loop96-config.json --idle-seconds 30`.
