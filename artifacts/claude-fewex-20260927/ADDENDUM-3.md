# Source qualification after the 6,000-step guard failed

Written 2026-09-27 23:27 UTC, before any maze adaptation or maze panel score. The original pass marks and maze ladder do not change.

**Shown, original source runs:** loop seeds 0/1 scored sums 200/200 each and grids 197/200, 199/200; plain seeds 0/1 scored sums 200/200 each and grids 176/200, 167/200. Thus original V1 failed. The original checkpoints and JSON are retained under `runs/{arm}-s{seed}/` for audit, but are not used for the maze baselines.

Source-only pilots were run on plain seed 0, without maze data: a 1,000-step continuation at 2e-4 did not improve grid accuracy on source dev; a fresh 6,000-step run at 5e-4 reached 136/200 grids; a fresh run with the original 1e-3 learning rate, the original puzzle stream and a 12,000-step cosine schedule reached 179/200 grids at step 6,000, 190/200 at 8,000, and 197/200 at 10,000 and 12,000 on source dev seed `SOURCE_SEED+200`. These are development results, not guard results.

**Qualified source recipe, fixed now:** train **both** architectures, seeds 0 and 1, for 12,000 batches of 64 source puzzles, from scratch with the original 1e-3 warm-up/cosine recipe and the same source generator/seed per paired arm. Choose the loop's fixed depth and the plain maze learning rate on source dev seed `SOURCE_SEED+100` as before. V1 is judged once on a new, untouched 200-sum/200-grid source guard seed `SOURCE_SEED+300`. V2 is checked on these qualified models. If any qualified model fails V1 or V2, report invalid and do not open the maze holdout.

The completed plain seed-0 pilot at 12,000 steps is exactly the qualified recipe (same model seed and source-example RNG); intermediate source-dev evaluations did not update weights. Reuse its saved checkpoint to avoid an identical training run. `claude_fewex_source_qualify.py` performs the new guard, depth selection, sweep, gradient check, and JSON write. Other three qualified models train from scratch. All maze examples, supports, panels, adaptation updates, sleep, and marks are unchanged. The qualified source models have matched source-example counts per seed and architecture.

Reused checkpoint SHA-256: `dafa4f3a1b4af6fa184e2abda13b4c1d5ee9f6cf0d758197da05ade378aae7b1` (`runs/pilot-plain-12k-s0-12000.pt`).
