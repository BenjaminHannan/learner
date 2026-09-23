# PASSMARKS — Experiment 111: Loop102 end-to-end through the real doorway (2026-09-22)

Registered run: `scripts/fable_bench111_run.py --run` (Mac CPU, offline,
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B scripts/fable_bench111_run.py --run`).
Each item runs in a FRESH daemon directory (no leakage); teach sentences in
file order, then the English question; the scored text is the outbox reply
file. Scorer = exp-66 `classify` verbatim (exact normalised match = correct;
abstain-marker with no gold = abstain; else wrong).

Scoring vocabulary: an answer item scores `correct` only on exact match; an
abstain item (gold list empty) can never exact-match, so its right behaviour
is `abstain`. "Right behaviour" below = correct on answer items + abstain on
abstain items.

| Mark | Pass condition |
|---|---|
| E1 Fable-Edit-200 through the doorway | right behaviour ≥ 195 of 200 AND wrong ≤ 2 |
| E2 fresh-200 (exp-103 split) through the doorway | wrong ≤ 2 |
| E3 abstain items (50) | 0 confident wrong answers (wrong == 0) |
| E4 whole registered wave | < 25 min wall-clock Mac CPU (< 1500 s) |

A registered FAIL is recorded as FAIL, never re-run into a pass.
