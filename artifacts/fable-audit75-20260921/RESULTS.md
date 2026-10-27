# Audit 75 — independent check of Experiments 29 and 46 (results)

Auditor (Muse) · 21–22 September 2026 · read-only: no existing file touched.
Evidence: `artifacts/fable-audit75-20260921/` (checks, re-run, seals).

## Verdicts

| Experiment | Claim | Verdict |
|---|---|---|
| 29 "new names" (fixed scale 1.2 + 10,000 updates → PASS 3/3) | all numbers trace to saved JSON; seals + order good | CONFIRMED-WITH-CAVEATS |
| 29 arms (6,000-update 1/3, learned-scale 1/3, open-set ~0.6) | same | CONFIRMED-WITH-CAVEATS |
| 46 "harden before gate" (15/15 installs to 4-wrong, 0/120 wrong installs) | all numbers trace to saved JSON; one full seed re-ran bit-identical | CONFIRMED-WITH-CAVEATS |

Integer counts I re-derived myself: Exp 29, 30/30 F cells match RESULTS;
Exp 46, 120/120 rows match (30 installed at each of 0/2/4 wrong, 0 at 20
wrong, 0 wrong installs); re-run seed 4102: 12/12 rows identical, weights
bit-identical (max abs diff 0.0).

## What it means

Both results are real: the files support every headline number, the seals
verify, the pass rules were locked before the runs, and nothing was averaged
or quietly re-run into a pass. Exp 46's sleep recipe genuinely installs the
right word from a teacher who is wrong 1 time in 5, and refuses nonsense.

## What it does not mean

This audit did not retrain Exp 29 (10,000-update runs are too heavy for the
audit box) and re-ran only 1 of Exp 46's 10 seeds. Both results are still toy
worlds, not language. Details and caveat lists: `design/v3/30-modes/75-audit-exp29-exp46-muse.md`.

## Deviations

Ledger predictions for this audit live in our `PASSMARKS.md` (Paudit75.1/75.2),
not the shared predictions ledger: the brief forbids touching the ledger and
this audit is read-only. Both audit predictions came TRUE.

## Reproduce

Re-derive all tables: `export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; python3
scripts/fable_audit75_verify.py; python3 scripts/fable_audit75_openset.py;
python3 scripts/fable_audit75_compare46.py`. Re-run Exp 46 seed 4102:
`cd scripts; export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline
--no-project --python 3.12 --with torch --with numpy python -B
fable_hardgate46.py --seed 4102 --out
../artifacts/fable-audit75-20260921/rerun4102` (~2 min Mac CPU).

## Questions for Ben

None. No decisions needed; audit changes nothing about the live recipe.
