# Fable ledger backfill 112 — PASSMARKS (sealed BEFORE run, 2026-09-22)

Bookkeeping only. No training, no experiments, Mac CPU only, offline.
Re-runs the exp-82 static audit logic (read-only on the ledger) on the current
ledger, then backfills outcomes strictly from finished RESULTS.md / results JSON
numbers. The ledger is append-only: no existing line is edited or deleted.

## Marks (all must pass)
- L1: scripts/fable_ledger82_check.py parses the whole ledger and prints every
  prediction id (Pn and Pexp.n styles) with stated probability, outcome
  (TRUE/FALSE/VOID/NOT SCORABLE/MISSING/(open)), and experiment label.
- L2: duplicates report flags the known P234-P237 collisions across 55b/57/58/59
  (plus any new id collisions since exp 82).
- L3: --selftest on the synthetic ledger passes (incl. Brier math,
  duplicate detection, order-violation flag).
- L4: artifacts/fable-ledger112-20260922/fable_ledger112_audit.json written with
  before/after integer counts, per-experiment + overall Brier before/after,
  collision list, and still-open list with line numbers.
- L5: whole check runs < 60 s wall-clock on Mac CPU with
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, uv offline, no installs.

## Backfill rule (decisions, not marks)
For every prediction with no outcome whose experiment has a finished RESULTS.md /
results JSON in artifacts/: decide TRUE / FALSE / VOID strictly from the numbers
in that JSON (quote the JSON key and value as evidence). If the JSON cannot
decide it, mark UNDECIDABLE with the reason — never guess. Running experiments
stay open and are never scored.

## Verdict rule
PASS = L1+L2+L3+L4+L5 all hold. Any miss = FAIL, recorded as FAIL, never re-run into pass.

## Reproduce
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ledger82_check.py --ledger artifacts/fable-predictions-ledger.md --out artifacts/fable-ledger112-20260922/ledger_status_before.json
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ledger82_check.py --selftest
