# TTT-2: the heavier recipe (written 2026-10-26 ~05:35Z, after TTT-1's results and before any TTT-2 run)

Labels: shown / suggested / untested. Same model, the same 100 ARC-AGI-1 evaluation tasks, prompt format and scoring as TTT-1. Backbone v2 small
tier only; not the card experiments.

## Why
TTT-1 (RESULTS-ttt1.md) showed the model learns much of each puzzle's rule from its own demos: answer loss 1.10 -> 0.58, lower than the
other-puzzle control on 90 of 100. But it fully solved only 4 of 100 (B 2, C 1). Published recipes train longer, use colour permutations,
and vote over transformed copies at inference (Akyurek et al. 2024; ARChitects). Addendum 1 named these as the next step if T1b passed and
T1 failed. It did.

## Arm H (one arm; each task starts from the base weights)
TTT-1's T recipe with two changes in training and one at inference:
- 144 steps (3x), so each leave-one-out item is seen about 3x more often;
- every pool item also gets its own random permutation of colours 1-9 (0, the background, stays; seed k + 1000);
- inference: a greedy answer under each of the 8 symmetries (the demos and the test input transformed alike), each mapped back, then a
  majority vote (ties go to the earliest symmetry, identity first). The identity answer alone is also recorded ("H greedy").

## Pass marks (fixed now; compared with TTT-1's T on the same 100 tasks, paired exact McNemar)
- **T2 pass:** H vote solves >= 10 of 100 AND p < 0.05 against TTT-1 T (4).
- **Wrong if:** H vote <= 4 (no better than TTT-1 T). Then the lower loss does not turn into solves at this size with these tools.
- Reported: H greedy against T (the training change alone); H vote against H greedy (the vote alone); H's answer loss; seconds per task.
- Not an equal-compute comparison (H spends about 4x the compute of T). It asks whether the published upgrades turn the lower loss into
  solves, not which is cheapest.
- Expectation (not a mark): H vote 6-15.

## Compute
Kaggle 2x T4, two lanes (`run --arms H --shard i/2`), about 6 min a task, about 5 h. Exits well before 11 h. Free.
