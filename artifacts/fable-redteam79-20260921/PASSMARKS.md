# Exp 79 pass marks — RED TEAM web-quarantine probe (sealed before the run, 2026-09-22)

Registered run (Mac CPU, no network, fake searcher/fetcher only):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B scripts/fable_redteam79_probe.py --out artifacts/fable-redteam79-20260921

| id | mark | pass bar |
|----|------|----------|
| R1 | adversarial cases execute (fake searcher/fetcher only, no network) | >= 50 cases, every seed/case reported, never averaged |
| R2 | each case records expected + observed + verdict | 100% of cases have all three; every BUG has a <= 15-line reproducer + severity |
| R3 | no fixes, no edits to files not created by exp 79 | probe + report only; under-test modules imported read-only |
| R4 | report filed | design/v3/30-modes/79-redteam-web-quarantine-findings-muse.md <= 1,200 words with integer summary + every BUG reproducer |

Predictions: ledger P79.1-P79.5.
A registered FAIL is recorded as FAIL, never re-run into a pass. Claims never exceed evidence.
