# Experiment 56 pass marks (sealed before the registered run, 2026-09-21)

Registered run:
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_qual56_conformance.py --out artifacts/fable-qual56-20260921
  plus: reasoner50 selftest unchanged
  (uv run ... python -B scripts/fable_reasoner50.py --selftest)

| id | mark | pass bar |
|----|------|----------|
| Q1 | wrapper conformance | 24/24 reasoner cases (status + answer + reason) |
| Q2 | naive control (plain reasoner50, identical questions) fails | >= 6 of the 24 |
| Q3 | reasoner50 --selftest still passes unchanged | PASS, 0 disagreements |
| Q4 | wrong answers over the 24 (OK-where-MISSING or wrong OK value) | 0 |

Miner filter (reported, not gated): 6/6 checks (drop qualified-chain
ask/correct, keep the rest, input untouched, walk detector exact).

Predictions: ledger P240 (Q1), P241 (Q2), P242 (Q3), P243 (Q4).
A registered FAIL is recorded as FAIL, never re-run into a pass.
