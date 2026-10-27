# xfer-1 results: how few maze examples the loop needs after sums and grids practice (research-loop thread)

Written 2026-09-27 20:11 UTC. Stopped by Ben at 19:58 UTC after 4 trials. Trial 4 was already running and finished at 20:09.
CPU only, $0. The research branch in the thread's clone has the harness commits; this folder copies its records.

Setup (program.md): the benchmark is scripts/claude_xfer1_bench.py, locked. The nets are small, with no kind label:
loop 2 x 128 (429,710 weights) and plain 8 x 64 (416,829).
- Practice: 6,000 batches of 64 sums and Latin grids.
- New kind: mazes, handed in batches of 32.
- maze_auc: the mean fraction of a fixed panel of 9x9 mazes solved after 1k, 2k, 4k, 8k, 16k, 32k and 64k maze
  examples. Dev has 200 mazes, holdout 300. Mazes are carved as uniform spanning trees, and no panel maze is ever
  handed to a net.

## Calibration: recipe as sealed at the start, 3 seeds (shown)
| arm | dev maze_auc | 11x11 solved after 64k (dev, per seed) |
|---|---|---|
| practised loop | 0.205 +/- 0.011 (holdout 0.163 +/- 0.017) | 0.50, 0.575, 0.705 |
| fresh loop | 0.075 (holdout 0.093) | 0.255, 0.245, 0.145 |
| practised plain | 0.222 +/- 0.013 | 0.29, 0.14, 0.135 |
| fresh plain | 0.162 | 0.135, 0.19, 0.20 |
- Practice reached 95-98% right on 200 four-digit sums plus 200 5x5 grids.
- Noise floor per trial (2 seeds, z = 1): 0.010.

## Trials (keep rule: better than the incumbent beyond noise on seeds 0-1, then again on 2 fresh seeds)
| # | change (one each) | dev maze_auc | verdict |
|---|---|---|---|
| 1 | Loop: every maze batch runs 16 rounds, gradient through all of them (Bansal 2202.05826) | 0.161, seed 0 | DISCARD |
| 2 | Maze-phase learning rate 2e-3 (was 1e-3), all arms | 0.164, seed 0 | DISCARD |
| 3 | Loop: deep supervision (TRM 2510.04871). Each maze batch gets 4 updates. Each update runs 3 rounds without gradient and 2 with, starting from the state the previous update left (detached). | 0.321, 0.301; fresh seeds 0.294, 0.336 | KEEP (0.315) |
| 4 | Simplify trial 3: drop the stop-head loss while learning mazes | 0.372, 0.348; fresh seeds 0.366, 0.372 | KEEP (0.369) |

Notes on the trials:
- **Trial 1:** ahead at 4k-32k examples, but fell at 64k (0.41 vs 0.715), and 11x11 dropped to 0.23.
- **Trial 2:** slower up to 32k examples, better at 64k (0.84).
- **Trial 4, fraction of 9x9 solved at each check (1k to 64k):**
  - seed 0: 0.015, 0.06, 0.165, 0.21, 0.31, 0.845, 1.0;
  - seed 1: 0.005, 0.105, 0.09, 0.035, 0.335, 0.87, 0.995;
  - calibration seed 0, for comparison: 0, 0.005, 0.02, 0.075, 0.13, 0.41, 0.715.
- **Trial 4, 11x11:** 0.94 and 0.94 on the screen seeds; 0.86 and 0.67 on the fresh seeds.
- **Compute:** trials 3-4 spend 13.2-14.0 min learning mazes per run, against 5.2-5.4 min for the base recipe (about
  2.6x per example).

## What is shown, suggested and untested
- **Shown (dev, small nets, 4 seeds per kept change):** with deep supervision and no stop-head loss, the practised
  loop's maze_auc rose from 0.205 to 0.369. It solves 98-100% of new 9x9 mazes after 64k examples, where the sealed
  recipe solved 72-87%.
- **Shown (calibration):** practice on sums and grids helps the loop learn mazes. Practised minus fresh is +0.13 on
  dev and +0.07 on holdout.
- **Untested:**
  - The kept recipe on the holdout. No holdout check ran after trials 3-4, because the harness checks after 3 keeps.
  - Whether the kept recipe helps a fresh loop just as much. If it does, that would be better maze learning, not
    better transfer.
  - The practised plain net with a matched compute control (4 updates per batch).
  - Any claim that the loop now beats the same-size plain net. Plain's 0.222 was measured with the base recipe and
    about 1/2.6 of the compute.
- **Suggested:** trial 4's gain may come from answering at round 48, once the stop head no longer fires early. The
  stop-rule logs were not examined.

## Left unfinished
- The holdout check of the kept recipe.
- Fresh-loop, practised-plain and plain-with-4-updates controls run with the kept recipe, plus plain's lr sweep.
- The remaining cards in hypotheses.md: H3 attention-only carry-over, H4 LP-FT, H6 EMA and others.
- A maze-repeat flaw that affects rsn-358x. The 358m carver gives 14 distinct 7x7 layouts (1,008 mazes) and 322
  distinct 9x9 layouts in 100,000 draws.

## Plain summary for Ben
We taught a tiny looping brain sums and grid puzzles, then showed it mazes one batch at a time and counted how many it
needed.
- Practice helped. The practised loop learned mazes from fewer examples than a loop that never practised.
- One idea from a recent paper made it learn much faster. The idea is to study each batch of mazes 4 times, carrying
  its half-finished thinking from one look to the next. With it, the loop solved almost every new maze after 64,000
  examples, against about 3 in 4 before.
- It spends about 2.6 times more computer time per example.
- We have not yet checked it on the hidden test mazes. We also have not yet given the plain net the same extra study
  time. So we can't yet say the loop beats the plain net.
