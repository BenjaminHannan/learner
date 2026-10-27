# Fable ledger audit 82 — PASSMARKS (sealed BEFORE run, 2026-09-22)

Static parser audit of artifacts/fable-predictions-ledger.md. No training, Mac CPU only.

## Marks (all must pass)
- L1: scripts/fable_ledger82_check.py parses the whole ledger and prints every
  prediction id (Pn and Pexp.n styles) with stated probability, outcome
  (TRUE/FALSE/VOID/NOT SCORABLE/MISSING/(open)), and experiment label.
- L2: duplicates report flags the known P234-P239 collisions across
  55b/57/58/59 and the P200 block (exp 45 N4 vs redteam67 P200.1-5).
- L3: --selftest on a small synthetic ledger passes (incl. Brier math,
  duplicate detection, order-violation flag).
- L4: artifacts/fable-ledger82-20260921/ledger_status.json written with
  integer counts, per-experiment Brier + overall Brier, open-stale list,
  order-violation list with line numbers.
- L5: whole check runs < 60 s wall-clock on Mac CPU with
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1, uv offline, no installs.

## Verdict rule
PASS = L1+L2+L3+L4+L5 all hold. Any miss = FAIL, recorded as FAIL, never re-run into pass.

## Reproduce
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ledger82_check.py --ledger artifacts/fable-predictions-ledger.md --out artifacts/fable-ledger82-20260921/ledger_status.json
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_ledger82_check.py --selftest
