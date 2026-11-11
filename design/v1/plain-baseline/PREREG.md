# Plain-transformer baseline for V1 (pre-registration, written 2026-10-23 BEFORE any code or run)

Labels: shown / suggested / untested. Research report: https://claude.ai/artifact/JnL9CRkskZksidFTK7EiQZ (item R6).

## Why
The project goal (handoff/HANDOFF.md) is to beat an equal-size plain transformer. V1 trained FLOOR and FULL but no plain
baseline, so FULL's 80.1% dev / 44.7% validation cannot yet be called good or bad (shown: design/v1/REPORT-V1.md).

## The one change
Replace D (PremonitionMini, 2,130,516 params, notebook/cards/loops) with a plain decoder-only transformer
(`learnlab.core.Core`, the contender-A family in premonition/contenders.py) sized to 2.13M params +-10% (embeddings counted,
tied head), reading the visit's visible lines in a fixed window, then the question, and generating the answer.
Everything else held fixed: village TRAIN shards 0-379 only, tokenizer premonition-tok-v2, label-free regime, seed 0,
AdamW (betas 0.9/0.99, wd 0.1 on matrices, lr 1e-3, 100 warmup steps), and the same training-token budget as the arms
(12,000 steps x up to 55,000 tokens). No creative module, no sleep, no bridge, no G1, no Muon, no S2.

## Scoring (same questions, same rule)
Exact-match answer accuracy on DEV (shards 380-399, 42,653 questions) and `validation` (8,675 questions). The baseline's
question counts must equal these; a mismatch voids the comparison. The sealed `test` split is never built or read.

## Marks (fixed now)
- Comparator: FULL validation 44.7% (results2, Vast) and, when it lands, the v1full-pc re-run's validation number; both reported.
- M1 "FULL's edge shown": FULL validation - plain validation >= 5.0 points against BOTH comparators.
- M2 "no edge": the difference is under 5.0 points. M3 "plain wins": plain validation >= FULL validation.
- Dev difference reported beside it, not a mark.
- Proves the architecture case wrong (for v1): M3. Then v2 starts from the plain model's result.
- Sanity: plain dev must exceed the 8.95% no-learning baseline by >= 10 points, else the run is a wiring failure, not a result.

## Budget and venue
Vast, one box, cap $5 (PC is busy with v1full-pc). Ben allowed Vast/Modal at the thread's discretion (2026-10-23).
