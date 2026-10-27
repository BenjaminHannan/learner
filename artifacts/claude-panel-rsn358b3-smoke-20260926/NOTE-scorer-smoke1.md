# Scorer check on Benchmarks' smoke 1 (sleep research thread, 2026-09-26 16:26 UTC)

These replies are rival replies on the free smoke panel (seed 36000, never a test panel). They are on builder-outbox at artifacts/claude-bmriv-smoke-20260926/run/.

Three changes to scripts/claude_rsn358b3_panel.py came out of reading them. All three apply to every arm the same way.

1. **The answer is the FINAL grid.** It is the last run of s consecutive rows, not the first s matching lines from anywhere in the reply. Replies echo the puzzle and show working rows before the answer, so the first-match reading could stitch together lines from different places.
2. **Markdown tables are read.** This covers bold cells, |---| rule lines and a leading row-number column. Two correct Qwen (thinking on) grids were only credited after this fix.
3. **Cut-off replies are never right.** A reply cut off at the token cap, or whose thinking never closed, is not counted right on a broken square. A missing reply is not right either. Before this, an empty truncated reply counted as a correct "no square" answer.

Smoke 1 used a 512-token cap (1,024 for the thinking arm's shards). Most replies were cut off, so these counts say nothing about the models. Benchmarks' change to 4,096 new tokens for thinking-off arms and 16,384 for the report-only thinking-on arm is accepted for 358b3.
