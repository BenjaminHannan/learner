# RESULTS — Experiment 103: one-change follow-ups to the exp-92 FAIL (2026-09-22)

Both of exp 92's named failure mechanisms are confirmed by their minimal
fixes. The exp-92 FAIL stands (never re-run).

## Marks table (sealed `PASSMARKS.md`, sha `8d455d2c…3a8bb3`)

| Mark | Result |
|---|---|
| A1 S4-clean notebook wrong == 0 | **PASS**: 924/924 correct, 0 wrong, 0 miss (n=924; 76 of 1,000 dropped) |
| B1 English S1–S3 wrong <= 3 total | **PASS**: 0 wrong total — S1 199/0/1, S2 190/0/10, S3 198/0/2 |
| B2 S2-fresh English wrong <= 4 of 200 | **PASS**: 193/0/7 (0 wrong, 7 miss) |
| B3 notebook on S2-fresh 200/200 | **PASS**: 200/200 correct, 0 wrong, 0 miss |

Ledger P103.1–P103.5: all 5 TRUE (P103.1 924/924; P103.2 0 wrong;
P103.3 0 wrong; P103.4 200/200; P103.5 wave ~1 min).

## Arm A: S4-clean (the only change is the case list)

21 edited (subject, relation) slots were edited to different values by
different cases (e.g. Nigeria/head_of_government → Buhari vs Döhler).
Dropped 76 cases: 71 that edit a conflicted slot, plus 5 whose chain
passes through one without editing it. Kept 924. Shared notebook on the
kept set: 924/924, reasoner↔contract agree everywhere, 0 teach CONFLICTs,
p50 2.2 ms / p99 6.9 ms. Exp 92's 25 wrongs + 2 misses came from the
dropped set's interference, not the hop loop.

Observable (not a change): 106 S4 edit teaches overwrote a value an
EARLIER *different* case had taught (own-case originals excluded). That
is 106 times a real agent should say "you told me X before; replacing
it with Y" instead of silently superseding.

## Arm B: pattern order only (the only change is try-order)

`TemplateEars103` tries the same pattern set in a new order — exp-73
specifics, then exp-92 extras, then the generic officeholder last (selftest
proves the pattern multiset is identical and the question path is
byte-identical in behavior). No new cue words, no new synonyms.
Exp 92's 41 English wrongs → 0 on S1–S3. Statement-parse failures stayed
0. What remains are honest MISSes (frame None → MISSING_FACT): question
cues tuned on S1–S3 don't cover fresh phrasing ("the faith that the
spouse … adheres to" has no religion cue), so the walk abstains instead
of guessing. S2-fresh (200 new 4-hop cases, seed 10300, case-id overlap
with every exp-92 split = 0, manifest-proved) shows the same shape:
193/0/7 on English, 200/200 on the notebook control.

## What it means

Batch teaching breaks only through contradictory shared slots (drop them
and the shared notebook is perfect); English template parsing breaks only
through pattern shadowing (order specifics first and confident wrongs go
to zero, on old splits and a fresh 200).

## What it does not mean

It does not mean batch teaching is solved (dropping conflicts is
diagnosis, not a design — case isolation is still untested), nor that
English is solved (20 misses remain cue-coverage gaps, and cues were
still tuned looking at S1–S3).

## Deviations / reproduce

Deviation 1: S2-fresh draws from all unused chain-linked 4-hop items
((4,1) had only 24 left of 224; pool of 739 across (4,1–4,4)), not only
single-edit — same `mquake_item` builder logic, new seed 10300.
Deviation 2: one `sorted()` key fix in the Arm-A reporter (pre-run).
No other agent's files touched; nothing committed. Reproduce:
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_bench103_notebook_arm.py --run` (then
`…_english_arm.py --run`; S2-fresh build needs `--with pandas --with
pyarrow`: `scripts/fable_bench103_build_s2fresh.py`). Data:
`data/open/bench103/` (+ read-only `data/open/bench92/`).
Questions for Ben: should cross-case overwrites require a spoken
"you told me X before" confirmation, or is a log line enough?
