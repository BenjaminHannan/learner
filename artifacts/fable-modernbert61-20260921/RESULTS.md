# RESULTS — fable_modernbert61: ModernBERT eager reseal (2026-09-22)

Registered result: **FAIL** (E3 only). Plain words for Ben: our hand-written
ModernBERT code matches the official code *exactly* on 40 brand-new sentences —
but the official code itself has two slightly different attention methods, and
against the second one we measured a bigger gap than our sealed promise allowed.

Snapshot: `answerdotai/ModernBERT-base` (Apache-2.0), rev `8949b90…`, from the Mac
HF cache (no download). Ours: 58's `load()` imported untouched (149,014,272 params,
1.7 s CPU load). Reference: transformers `AutoModel` loaded twice, eager + sdpa,
fp32, CPU. 40 new sentences (20 science-abstract, 20 everyday; longest 95 tokens).

## Marks (sealed in PASSMARKS.md, sha `5caafebf…a3da011`, before the run)

| mark | bar | measured | verdict |
|---|---|---|---|
| E1 token ids match reference | 40/40 | 40/40 exact | PASS |
| E2 max \|ours − eager\| last-hidden | < 1e-4 | 0.00 (bit-exact) | PASS |
| E3 max \|ours − sdpa\| last-hidden | < 1e-3 | 1.59e-03 | **FAIL** |
| E4 char spans cover text (gaps whitespace-only) | 40/40 | 40/40 | PASS |
| E5 padded-batch vs single | < 1e-4 | 6.29e-05 | PASS |

Recorded, no mark: forward 33.5 ms/sentence (batch 1), 30.6 ms/sentence (batch 16);
peak RSS 2560 MB (three 150M-param models in RAM). Predictions: P61.1 TRUE, P61.2
TRUE, P61.3 FALSE, P61.4 TRUE, P61.5 TRUE (ledger).

## Why E3 failed
The sdpa-vs-eager gap grows with length: 3.07e-4 on 58's short sentences, 1.59e-3
here (worst on a long). Ours is bit-exact to eager (E2 = 0.00), so the 1.59e-3 is
the reference disagreeing with itself across backends — kernel accumulation order
over 22 layers — not a loader error. My 1e-3 bar (borrowed from the BERT loader)
was simply too tight for 95-token inputs.

## Deviations
1. First post-seal run used a tiling (no-overlap) span check: E4 19/40, because
subword pieces of one word legitimately repeat that word's span. Fixed to the
union-coverage test the sealed bar actually states; re-ran as the registered run.
E3 was 1.59e-3 in both runs, so the FAIL verdict does not depend on this fix.
2. `torch_dtype` arg drew a transformers deprecation warning (cosmetic; fp32
verified on all three models).

## Reproduce
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy --with transformers python -B
scripts/fable_modernbert61_check.py
$HOME/.cache/huggingface/hub/models--answerdotai--ModernBERT-base/snapshots/8949b909ec900327062f0ebf497f51aef5e6f0c8`
(16.9 s). New files only: `scripts/fable_modernbert61_check.py`,
`artifacts/fable-modernbert61-20260921/`, `design/v3/30-modes/66-…md`. No commits.

## What it means / What it does not mean
It means our loader is verified bit-exact to the eager path on fresh sentences,
with working char spans and batching — all a span-pointer ear needs. It does
**not** mean the check passed: E3 failed as written, and a FAIL stays a FAIL. A
future seal should pin eager for exactness and record sdpa with a length-aware bar.
