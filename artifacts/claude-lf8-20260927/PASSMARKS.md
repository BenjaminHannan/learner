# lf-8 pass marks: does the 8-layer loop forget less than the 2-block loop? (fixed before any run; 2026-09-27 19:40 UTC)

Run by the "Making things up about you" thread for the Thread manager. It is asked for by Ben at 19:35:34 UTC 09-27
("so then do the test", cmsg_01FuvegZXjMmeUzStiEFVnEW2GCUswgRDMfwHGUkGY9TTf). He was answering the Thread manager's note
that the forgetting tests (the 358e line) use a 2-block loop, while his reasoner design is an 8-layer loop.

## Code
- scripts/claude_lf8_run.py runs rsn-358e4's dense-replayall arm. That arm is claude_rsn358e4_replayall.py and its
  imports, unchanged; 358e4's SEAL-addendum-1 still holds for all of them.
- ONE change: the loop has 8 layers instead of 2 (X.SIZES["small"]["layers"]).
- Everything else stays the same:
  - width d256 and 8 heads;
  - code-made data in three phases: A grids, B sums, C mazes;
  - steps 2,500 / 2,500 / 1,500 and batch 64;
  - every earlier kind replayed (every 10th step);
  - the loop schedule;
  - the dev sets (seed 48000, 200 items each);
  - scoring (the net's own stop, 48 rounds).

| arm | loop layers | weights |
|---|---|---|
| loop2 | 2 | 1,646,750 (358e4's arm as written) |
| loop8 | 8 | 6,386,174 (about 3.9x) |

- loop8 has about 3.9x the weights, so this is a depth test, not a same-size one. A gain could come from size as much as
  from depth.
- Seeds are 9 and 10, which no dense-replayall run has used. Each arm runs on both seeds, so the runs pair by seed.
- loop2 is run again here instead of reusing 358e4's seeds 3-8, because this container is a different machine
  (torch 2.14.0+cpu).

## Run
- It runs on this container's CPU, for $0, in two lanes of 2 threads each (4 cores):
  - lane 1: loop8 seed 9, then loop2 seed 9;
  - lane 2: loop8 seed 10, then loop2 seed 10.
- Estimate, from 12 timed steps here (not measured end to end): about 1.1 s per step for loop2 on 1 thread and 1.5 s
  for loop8 on 2 threads. That is about 6 hours in all.

## Marks
Scores are dev items right, out of 200. T = grids5 + sums4 + maze7 after phase C, out of 600, as in 358e4.
- **V** (358e4's validity check): on both seeds and in both arms, grids5 after A must be at least 120 and sums4 after B
  at least 120. Otherwise the result is INCONCLUSIVE.
- **PASS:** mean T8 >= mean T2 + 40, AND T8 > T2 on both seeds.
- **Proved wrong:** T8 <= T2 + 10 on both seeds.
- **FAIL** (no difference shown): anything else.

## Report only
- The parts of T:
  - grids5 after C (keeping the first skill);
  - sums4 after B and after C;
  - maze7 after C (learning the new kind).
- Forgetting:
  - grids5 after A minus after C;
  - sums4 after B minus after C.
- Weights, minutes per run, and replay counts.
- A blind recount of T and the marks, by a fresh worker working only from the result.json files.

## Noise, read before the run
- 358e4's six dense-replayall seeds (s3-s8; same code, another machine) gave T from 393 to 525, mean 470.
- So a 40-point gap in a 2-seed mean is within seed noise. "Higher on both seeds" is the main guard.
- A PASS here means "worth a bigger test", not "shown".

## Prediction (a guess, before any run)
- PASS: 35%.
- Proved wrong: 30%.
- Reason: 3.9x the weights and 4x the depth per round should help learn mazes and keep more, but depth alone has not
  always helped in the 358 line.

## What each outcome means
- **PASS:** a deeper loop keeps skills better at this scale. The forgetting tests should move to the 8-layer loop, and
  a same-size check comes next (8 layers at a width that matches 1.65M weights).
- **Proved wrong:** the 8-layer loop gains little on T despite 3.9x the weights. The 2-block forgetting results likely
  carry over.
- **FAIL:** no difference shown with 2 seeds.
