# Research program (xfer-1, research-loop thread, started 2026-09-27 14:45 UTC)

## Goal
After practising sums and grids, the looping reasoner learns a new kind of puzzle (mazes) from as few examples as possible; compared with a fresh loop and a same-size plain net with the same practice; no caller-given kind labels.
Source: Ben's goals page, design/v3/30-modes/ben-goals-2026-09-26.md:24-26 ("the main measure is how few examples a new kind takes to learn, given what it already knows").

## The goal as an experimental question
A small loop net practises 3,000 batches of 64 sums/Latin grids. Then it is handed fresh mazes in batches of 32. After 512, 1k, 2k, 4k, 8k, 16k and 32k mazes, how many fresh 9x9 mazes does it solve? Higher area under that curve = fewer examples needed. Same question for a fresh loop (no practice) and for the plain 8-layer net of the same size with the same practice.

## Benchmark
- Primary metric: maze_auc (max) = the practised loop's mean fraction right on 200 dev 9x9 mazes over the 7 checks.
- Guard: practice_acc >= baseline - 0.05 (practised loop on 200 fresh 4-digit sums + 200 fresh 5x5 grids, before mazes).
- Reported every trial: fresh_auc (fresh loop, same maze stream and recipe), transfer = maze_auc - fresh_auc, examples_to_bar (first count with >= 75% right), cold (0 examples), big11 (200 11x11 mazes at the end).
- Dev: panel seed 6270701 (200 9x9), maze streams 6300000+seed, practice seeds 0-5. Holdout: panel seed 6270702 (300 9x9), streams 6400000+seed, practice seeds 500+. Same generator and difficulty; only the harness runs the holdout.
- Per trial: 2 seeds; about 5 min per seed (practised and fresh loop in parallel, 2 threads each, 4 CPU cores); about 11 min more per seed when practice code changes (practised nets are cached by the net file's hash, outside the repo in ~/xfer1-cache).
- References: fresh loop (floor), plain net with the same practice (the rival), plain fresh. No natural ceiling (1.0 is the maximum).

## Constraints
- Hardware: 4 CPU cores, 15 GB RAM, no GPU. $0. Vast only if the CPU benchmark cannot rank methods (then one card through the Director, <= $4).
- Files that may change: scripts/claude_xfer1_net.py (nets and practice recipe), scripts/claude_xfer1_adapt.py (learning a new kind and answering).
- Must not touch: scripts/claude_xfer1_bench.py (locked), scripts/claude_rsn358a_envs.py, scripts/claude_rsn358m_maze.py, anything of rsn-358x (sleep research's sealed test), repo-root notebook/.
- Rules: no kind label or kind-specific switch given by the caller; practice stays sums and grids only, same number of puzzles; the loop thinks at most 48 rounds per answer; training data is code-made only.
- Fairness: any change a plain net can also use lives in shared code, so plain gets it too in the final comparison. Plain gets a small learning-rate sweep at the end, because the loop's recipe was tuned over many trials and plain's was not.

## Assumptions made without asking the user
- Small nets (loop 2 x 128 = 429,710 weights; plain 8 x 64 = 416,829) instead of the 6.4M rsn-358i3 nets, so trials fit on CPU. Results are about this small scale.
- Mazes are 7x7 and 9x9 in learning, 9x9 in the test, because only 13,824 different 7x7 mazes exist.
- The 358m depth-first carver gives only about 322 different 9x9 layouts, so mazes are carved by Wilson's algorithm (uniform spanning trees) in the same item format and with the same checker.
- "Examples" = mazes handed to the learner, each batch fresh; the learner may reuse what it has already been handed.
- Budget: until 40 trials or 12 hours of loop time, whichever comes first.

## Benchmark changes (every relock, with reason)
- 2026-09-27 16:00 UTC, before calibration: compute guard learn_min raised from 2x to 4x baseline, because the main loop ideas (full-depth loss, deep supervision) cost 2-4x per example; if a kept recipe uses more compute per example, the final plain comparison adds a plain arm that reuses each batch for the same number of updates.
