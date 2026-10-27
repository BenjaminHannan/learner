# 351: the 3x reasoner with a slower learning rate

Sleep research thread, 2026-09-25. Follows rsn-350 (registered FAIL, VERIFY.md). Ben (23:59 UTC 09-24):
"Logically, a 3x bigger model would score better than lower. So why didn't it?"

## What 350's logs showed (measured)
- After the copy phase, both sizes were level on the fresh panel (90M 175/180, 30M 167/181).
- The whole gap came from the practice phase. 30M gained +58 and +36; 90M gained +36 and +29.
- 90M's practice reward plateaued around 0.83 (means over each 1,000 steps: 0.77 → 0.84), while 30M
  ended at 0.93 and 0.98. Counting learned in practice: 30M 12/30, 90M 4/30.

## The one change
rsn-350 exactly (91,588,629 numbers, same generator, steps, batches, reward, seeds, eval), with the
learning rate 1e-4 instead of 3e-4 (`--lr 1e-4`, an existing flag of claude_rsn294_run.py; no new code).
Hypothesis (a guess): 3e-4 is too fast for the bigger net under noisy trial-and-error practice.

**Twins:** rsn-350 (same size, lr 3e-4) and 296 plain (30M, lr 3e-4), same seeds, same panels and scorer.

## 10x rule
Unchanged from 350: 10x only if Y1 passes on both seeds, after checking the director's total.

Pass marks: artifacts/claude-rsn351-20260925/PASSMARKS.md. Cost ≈ rsn-350's $0.96; $4 cap.
