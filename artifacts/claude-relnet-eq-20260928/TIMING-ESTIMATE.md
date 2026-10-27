# Timing probe and wall-time estimate (suggested, not a result)

Measured with scripts/claude_relnet_eq_timing.py (torch 2.14.0+cpu, fp32, one process; timing-t1.json, timing-t2.json).
The machine was shared with three other helpers (load average 1.6-3.4), so every figure is probably a bit slow.
Losses only; nothing was scored. Seconds.

| item | relnet 1 thr | loop 1 thr | ratio | relnet 2 thr | loop 2 thr | ratio |
|---|---:|---:|---:|---:|---:|---:|
| practice step (64 sums/grids, real round draw, mean of 10) | 3.18 | 0.85 | 3.8x | 1.76 | 0.47 | 3.8x |
| maze batch, 9x9, 32 mazes, 4 updates | 41.3 | 3.42 | 12.0x | 22.7 | 1.74 | 13.0x |
| sleep step | 3.91 | 0.58 | 6.8x | 2.29 | 0.32 | 7.1x |
| 48-round inference, 32 mazes 7x7 | 13.2 | 2.5 | 5.3x | 7.5 | 1.18 | 6.3x |
| same, 9x9 | 55.9 | 4.4 | 12.6x | 31.7 | 2.26 | 14.0x |
| same, 11x11 | 159.4 | 7.0 | 22.9x | 87.6 | 3.65 | 24.0x |

Shown: at the maze sizes the relation net costs 12-13x the loop per maze update, 13-23x for 9x9-11x11 inference. That
is more than the 4-6x that REVIEW.md measured at batch 2-4 (suggested reason: at batch 32 the pair state is
32 x 81 x 81 x 64 floats per tensor, so it is memory-bound).

## (a) Practice, 12,000 steps per seed (suggested)
- 1 thread: 12,000 x 3.18 s = 10.6 h. 2 threads: 12,000 x 1.76 s = 5.9 h.
- Plan: seed 0 on 2 threads, seed 1 on 1 thread (3 cores). Seed 0 ends at about 5.9 h. A detached helper
  (scripts/claude_relnet_eq_rebalance.py) then stops seed 1 just after a checkpoint and resumes it on 3 threads (the
  practice script resumes exactly from resume.pt). By then seed 1 is at about step 6,700; the remaining 5,300 steps at
  about 1.3 s each take about 1.9 h (assuming 3-thread scaling like 2-thread). Estimate: seed 0 about 6 h, seed 1
  about 8 h. Without the hand-over seed 1 would take 10.6 h.

## (b) One dev adapt ladder per run (suggested)
Per run: 8 rungs x 512 maze batches = 4,096 maze batches; 2 sleeps x 512 steps; 11 scoring stages (k=0, 8 rungs, 2
sleeps) on the dev panels (24 7x7, 300 9x9, 300 11x11), plus 5 old-kind scorings of 400 puzzles.
- 1 thread: 4,096 x 41.3 s = 47.0 h; sleeps 1,024 x 3.9 s = 1.1 h; scoring 11 x (24/32 x 13.2 + 300/32 x 55.9 +
  300/32 x 159.4 = 2,030 s) = 6.2 h. **About 54 h per run.**
- 2 threads: 25.8 h + 0.65 h + 3.4 h = **about 30 h per run.**
- Cross-check with the sparse ladders: they took 3.9 h per run at 1 thread; the relation net's maze batch is 12x and its
  9x9/11x11 inference 13-23x the loop's, and the sparse net cost about the loop, so about 12x3.9 = 47 h or more at 1
  thread agrees.
- Four runs (pre and fresh, seeds 0 and 1) = about 216 core-hours. On 3 cores that is about 72 h (3 days) even if
  they run perfectly packed, before the holdout (another 48 + 300 + 300 mazes x 11 stages x 4 runs, about 8 h each at 1
  thread per run, about 32 core-hours).
- The ladders are therefore not feasible in a night on this CPU. Options for the manager (none of them started):
  fewer runs (pre only, seeds 0 and 1, about 108 core-hours = 36 h on 3 cores; fresh copies later), a GPU addendum
  (breaks the $0 rule), or accept the wait. Nothing about the recipe is to be changed to make it faster.
