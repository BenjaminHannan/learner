# Research loop status  (2026-09-27T20:09:31)
Goal: After practising sums and grids, the looping reasoner learns a new kind of puzzle (mazes) from as few examples as possible; compared with a fresh loop and a same-size plain net with the same practice; no caller-given kind labels
Metric: maze_auc (max) | dev seeds/trial 2 | noise sigma 0.01688 | min detectable delta 0.01688
Guards: practice_acc>=baseline-0.05; learn_min<=baseline*4
Segment 1 | phase running | branch research/after-practising-sums-and-grids-the-loop-20260927-1445
Baseline: dev 0.2048 +/- 0.0114 | holdout 0.1625 +/- 0.0171
References (dev): fresh-loop 0.0745 | plain-practised 0.2224 | fresh-plain 0.1619
Incumbent: dev 0.3689 (trial #4, 638fe399) | +0.1642 vs baseline
Last holdout-confirmed: #base 07f58ec0 holdout 0.1625 (+0.0000 vs baseline) | holdout calls 0/12
Trials 4 | keep 2 | near-miss 0 | discard 2 | crash 0 | runtime 4.13 h / 12.0 h
Arms (kept/tried): literature 0/1 | tune 0/1 | bold 1/1 | simplify 1/1 | combine 0/0
Due: nothing

Last trials (newest last):
  #    arm         outcome     delta     hypothesis
  1    literature  discard     -0.0440   Loop maze learning: every batch runs 16 rounds with gradient through a
  2    tune        discard     -0.0405   Maze-phase learning rate 2e-3 (was 1e-3), shared by all arms
  3    bold        keep        +0.1102   Loop maze learning with deep supervision (TRM): each batch gets 4 upda
  4    simplify    keep        +0.0539   Simplify: drop the stop-head loss during maze deep supervision (CE onl
