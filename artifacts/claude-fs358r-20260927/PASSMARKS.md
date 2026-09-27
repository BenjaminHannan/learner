# fs-358r: does a bigger phase-C replay share stop the dense loop losing grids during mazes?
Fix-sleep thread. Registered when this file is committed, before any run. Written 2026-09-27T19:14:59Z from `date -u`.
Asked by the Thread manager (19:13 UTC 09-27). Background: reviews/gpt6pro-forgetting-2026-09-27.md, Table 4.

## Question
In the small loop reasoner, the dense net with replay keeps grids through phase B (sums; 1 grids batch in 10) but
loses about 55-70 of 197 grids5 puzzles during phase C (mazes; 1 grids batch in 20). Is the lower replay share in
C the cause?

## One change
Against rsn-358e4's dense-replayall (scripts/claude_rsn358e4_replayall.py, run unchanged as the baseline):
- baseline: phase C replays 75 grids + 75 sums batches among its 1,500 steps (every 10th step, alternating);
- candidate (scripts/claude_fs358r_creplay.py): phase C replays 150 grids + 150 sums (every 5th step, alternating).
Everything else is 358e4's code: dense loop, 1,646,750 weights, phases A 2,500 / B 2,500 / C 1,500 steps, B replay
250 grids, fresh optimizer per phase, dev sets seed 48000 (reused, not held out). C stays 1,500 steps, so the
candidate practises mazes on 1,200 steps instead of 1,350. That trade is part of the one change.

## Runs
- Seeds 9, 10, 11, 12 (new; 358e runs used 1-8), both arms on each seed, so every comparison is paired.
- This cloud CPU, 1 thread per run, 4 runs at a time (seeds 9-10 first, then 11-12), $0. About 3 hours.
- Scores are dev puzzles fully right out of 200 with the net's own stop ("right" in result.json).

## Marks (fixed now)
Let g = candidate grids5 after C minus baseline grids5 after C, on the same seed; m = the same for maze7 after C.
- **Validity:** the replay counts in result.json must read B 250 grids in both arms, C 75 + 75 for the baseline and
  150 + 150 for the candidate, on all 4 seeds. Otherwise the run is INVALID and not graded.
- **PASS:** mean g >= +25, g > 0 on at least 3 of 4 seeds, and no harm on mazes: mean m >= -15 and m >= -30 on every
  seed.
- **PROVED WRONG:** mean g <= +5. That means doubling C's replay share recovers almost none of the grids lost in C,
  so the share is not the cause.
- **FAIL (trade):** the grids part of PASS holds but the maze no-harm part does not.
- **INCONCLUSIVE:** anything else (mean g between +5 and +25, or g > 0 on fewer than 3 seeds).
- A FAIL or PROVED WRONG stays as registered.

## Reported, not marked
Loss in C per arm (grids5 after B minus after C); grids6, sums4, sums6 after C; T = grids5 + sums4 + maze7 after C;
fixed-16 and any-round scores; minutes.

## Predictions (fixed now)
Mean g about +20, INCONCLUSIVE 45%, PASS 30%, PROVED WRONG 25%. The maze7 cost is small (under 10).

## Limits
4 seeds on a dev set that was read before; one net size; CPU. Table 4's other agent used a learned front end
instead of the kind embedding; this run keeps 358e4's kind embedding, so the two are not directly comparable.
