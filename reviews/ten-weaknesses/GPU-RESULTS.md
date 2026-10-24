# GPU tests of fixes 8-10 (2026-10-24, one seed each, Vast RTX 4090, total ~$1.6)

## #10 HALT target (branch claude/ten-weak-halt, prereg design/halt/PREREG.md), D-only 6k steps, seed 0
| arm | dev acc | val acc | val loops | val halt rate |
|---|---|---|---|---|
| base (correct) | 80.69% | 46.12% | 2.22 | 0.994 |
| halt_evidence (correct AND have_all) | 84.77% | 43.97% | 2.94 | 0.970 |
Validation loops by depth 0-6 rise to 2.78/2.29/2.98/3.26/3.63/3.63/4.04 (base 2.15/2.10/2.24/2.28/2.38/2.33/2.08).
Verdict vs prereg: the loops mark passes (+0.71 >= 0.2). Validation is -2.15 points, which breaks the -1.0 guard. Per the prereg, "more looping hurts" is PROVED WRONG for this seed.
Caveat: the other thread's D-only baseline seeds range 42.6-48.2% validation, so a second seed is needed. Dev rose +4.1.
Results and checkpoints (D-final.pt): /mnt/project-files/results/ten-weaknesses/halt/

## #8/#9 G1 lock (branch claude/ten-weak-g1, prereg design/v1/g1-ablate/PREREG.md), creative-only, seed 0
| arm | harm W1 | harm W2 (points) | first-try W1 | first-try W2 |
|---|---|---|---|---|
| g1_empirical (v1) | 0.5 | 0.5 | 27.7% | 34.4% |
| g1_example (NK30 norm) | 0.0 | 0.0 | 24.6% | 35.9% |
| g1_off | 3.5 | 2.0 | 35.9% | 38.7% |
Verdict: mark 1 passes, so the example norm is acceptable (harm 0 <= 0.5, gap 1.6 points <= 2). Mark 2 fails: G1 buys 1.5 points of retention, below the 2-point bar, so "G1 benefit" is proved wrong on this measure.
G1 also costs about 4 points of first-try. One seed: 1 dev question = 0.39 points, and harm moves in 0.5-point steps, so the reading is suggested only.
Results: /mnt/project-files/results/ten-weaknesses/g1/

## #10 HALT seed 1 (BensPC RTX 5070 Ti, 2026-10-24 09:13-10:32Z)
| arm | dev acc | val acc | val recall@4 | val loops | val halt rate |
|---|---|---|---|---|---|
| base | 70.84% | 42.03% | 0.563 | 2.83 | 0.953 |
| halt_evidence | 75.18% | 42.46% | 0.535 | 3.56 | 0.894 |
Two-seed reading: val diff -2.15 (s0) and +0.43 (s1), mean -0.86. Loops +0.71 and +0.73, dev +4.1 and +4.3.
Mean passes the safety mark (>= -1.0) and the loops mark. The +2 success mark is not met, so the switch stays off.
Seed 1 trained on a different GPU, so its absolute numbers are lower. The comparison within each seed is still fair.
Files: Ben's Mac ~/learner-ops/v1-weights/ten-weaknesses/halt-seed1/.
