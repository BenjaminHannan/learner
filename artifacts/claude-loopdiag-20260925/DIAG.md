# Why the loop reasoner doesn't learn: CPU diagnosis (sleep research thread, 2026-09-25)

Ben (00:00 UTC): "Why didn't the loop learn? Can you see if you can detect the issue?"

## Setup (small-width reproduction, CPU)
- scripts: diag_train.py (LoopThinker/PlainThinker from scripts/claude_rsn294_core.py at width 256, same
  copy loss, AdamW lr 3e-4, warmup 300, clip 1.0, random 2-12 passes, 296 generator, batch 64);
  diag_init.py (untrained 30M loop: per-pass state size, gradients).
- The metric is copy-phase action cross-entropy ("ce"), the same number as 294/296's action_ce.
- Width 256, not 1024. The full-size result still needs a GPU run.

## Measured
- Untrained 30M loop: the state size is steady across 12 passes (rms 1.25-1.45), and gradients reach
  the embeddings at 2, 6 and 12 passes (1.0-1.2e-2). No explosion and no vanishing at start.
- The 294 failure reproduces: in 294, the plain arm's ce is 0.03 by step 1,200 and the loop's is still
  about 1.0. Here, at step 599, plain = 0.68 and loop = 1.22.
- Six single changes, seed 1, mean ce over steps 500-599 (lower is better): plain 0.74 | loop 1.51 |
  **no step embedding 0.98** | residual inject 1.07 | fixed 4 passes 1.19 | per-pass loss 1.31 |
  normalise state 1.49 | lr 1e-4 2.06.
- Repeat of the best lead, seeds 2 and 3, 1,000 steps, mean ce over steps 800-999:

| arm | seed 2 | seed 3 |
|---|---|---|
| plain | 0.47 | (not run) |
| loop (as in 294/296) | 1.10 | 1.30 |
| loop without the step embedding | **0.52** | **0.54** |

- The step embedding (a per-pass vector added to every token, `self.step.weight[t]` in
  LoopThinker.forward) is initialised N(0,1): rms 1.0, as large as the word embeddings (0.997). Vectors
  for different passes are unrelated (cosine between pass 2 and pass 12 = -0.04).

## Suggested (not tested)
- Every pass adds a large random vector, a different one each pass. With a random pass count (2-12),
  the output head sees a different big offset every time, and learning to cancel it slows everything.
  A tiny initial step vector (std 0.02) may keep the pass signal without the noise; that is running now.
- Full size (30M, width 1024) and the practice phase are not tested. The loop's extra passes still have
  to be shown to help once it trains.

## Update 01:45 UTC: small step vector (std 0.02 instead of 1.0)
Same setup, seeds 2 and 3, 1,000 steps, mean ce over steps 800-999:

| arm | seed 2 | seed 3 |
|---|---|---|
| loop (as in 294/296, step vector std 1.0) | 1.10 | 1.30 |
| loop without the step embedding | 0.52 | 0.54 |
| loop with a small step vector (std 0.02) | **0.58** | **0.54** |

- Suggested: the problem is the SIZE of the step vector at start, not having a pass signal. A small
  one trains about as well as none (width 256, CPU, copy phase only).
- rsn-353 (full size, no step embedding) is the registered test; it is held until the Mac has disk space.
