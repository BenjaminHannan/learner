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

## #8/#9 G1 seed 1 (BensPC, 2026-10-24 10:32-11:30Z)
| arm | harm W1 | harm W2 | FT W1 | FT W2 |
|---|---|---|---|---|
| g1_empirical | 1.0 | 1.0 | 20.70% | 33.98% |
| g1_example | 0.5 | 0.5 | 18.75% | 28.52% |
| g1_off | 4.0 | 3.0 | 36.33% | 39.45% |

Two-seed W2 means:
| arm | harm | first-try |
|---|---|---|
| empirical | 0.75 | 34.2% |
| example | 0.25 | 32.2% |
| off | 2.5 | 39.1% |

- **Mark 1 (example acceptable):** passes on seed 0 and fails on seed 1, where it is 5.47 points worse on first-try. The norm swap is therefore not adopted; the code keeps `none`, and G1 should be described as a variant of NK30 rather than as NK30 itself.
- **Mark 2 (G1 buys retention):** 1.5 points on seed 0 and 2.0 on seed 1, mean 1.75, which sits right at the 2-point bar. G1 costs about 4.3-5.5 points of first-try on both seeds.
- **Next single change:** a lighter lock, for example a lower KL weight or a lower energy threshold, with at least 3 seeds.

## G1 lighter lock (KL weight 30 -> 10), 3 seeds, Kaggle T4, 2026-10-31

Pre-registered in `design/v1/g1-ablate/PREREG-light.md` (commit 8b69bde5). Pass = g1_light mean W2 first-try >= g1_empirical + 2 AND mean W2 harm <= g1_off - 1.

W2 per seed (harm points / first-try %):
| seed | empirical | light | off |
|---|---|---|---|
| 0 | 0.0 / 35.9 | 0.0 / 35.5 | 1.5 / 44.5 |
| 1 | 0.5 / 33.2 | 0.5 / 30.5 | 3.5 / 41.4 |
| 2 | 0.0 / 32.8 | 0.0 / 32.4 | 3.5 / 34.8 |
| **mean** | **0.17 / 34.0** | **0.17 / 32.8** | **2.83 / 40.2** |

- **Verdict: FAILS (shown, 3 seeds).** The first-try gain is -1.2 against a +2 mark, and it is negative on every seed. The harm mark passes (-2.7). Cutting the KL weight to a third changed nothing measurable: the light lock behaves just like the current lock.
- No lock: +6.3 first-try for +2.7 harm points (3 seeds, consistent with the earlier two seeds).
- Side note (suggested, not pre-registered): W1 first-try was higher for light (28.6 vs 23.8 mean), but W2 is the pre-registered mark.
- **Decision:** keep G1 as coded. The trade-off looks all-or-nothing in the KL weight. If anything, the cost comes from the hard K-FAC mask, not from the KL term (untested). The next single change would be "mask off, KL kept", but it is not queued (usage cut until Sat Nov 1).
