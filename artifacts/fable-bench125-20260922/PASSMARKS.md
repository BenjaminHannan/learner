# PASSMARKS — Experiment 125: same-metric SmolLM2 vs joined-up agent (2026-09-22)

Borrowed SmolLM2-360M (exp 66 baseline) vs our joined-up agent (loop102 /
loop113 / loop113b, read from existing JSONs, NOT re-run), on BOTH splits
with ONE scorer: exp 113 scorer v2 (value extraction + word-boundary
abstain) plus the "contains gold" column.

Registered run (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1; uv run --offline --no-project --python
3.12 --with torch --with numpy --with transformers python -B ...`):
  scripts/fable_bench125_run.py --run   (full 200+200; no --limit:
  pre-registration timing smoke on 10 four-hop items measured 0.44 s/item
  -> 400 fresh generations project ~175 s, far below the 30 min budget)

SmolLM2 Fable-Edit-200 rows are RE-SCORED from exp 66's saved answer
strings (no re-run). SmolLM2 4-hop rows are FRESH runs (same prompts,
same greedy <= 16 tokens, model files already downloaded,
local_files_only=True, no downloads).

Predictions (honest point estimates; abstain golds on Fable-Edit are []
so scorer v2 — whose abstain list is the loop's own decline forms, not
"unknown" — will call almost every SmolLM2 abstain-item reply wrong;
contains-gold on Fable-Edit is deterministic under re-score: 67 / 58):
  SmolLM2 in-context / Fable-Edit-200: correct 54, abstain 1, wrong 145
  SmolLM2 RAG-lite   / Fable-Edit-200: correct 40, abstain 1, wrong 159
  SmolLM2 in-context / fresh 4-hop:    correct 20, abstain 1, wrong 179
  SmolLM2 RAG-lite   / fresh 4-hop:    correct 12, abstain 1, wrong 187

| Mark | Pass condition |
|---|---|
| C1 scorer sanity | scorer-v2 re-score of exp 66's in-context arm on Fable-Edit answer items is within ±3 of its "contains gold" count (67) |
| C2 wall-clock | full registered run < 30 min (< 1800 s) Mac CPU, no --limit subset |

A registered FAIL is recorded as FAIL, never re-run into a pass.
Every seed/case reported, never averaged. Claims never exceed evidence.
