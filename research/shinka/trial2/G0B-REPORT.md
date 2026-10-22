# G0b report (2026-10-21)

Card: `G0B-CARD.md` (sha256 97ee547f..., commit b3b8b30d). Script `g0b_probe.py`, data `../results/trial2/g0b.json`.
Run exactly as carded: CPU, $0, seeds 110-112, 512 training names, 8 disjoint test names, mark unchanged. No changes after seeing results.

## Result: PASS (controls valid)
| seed | novel-name acc | train-lines acc | held-out train-name acc (C1) | shuffled (C2) |
|---|---|---|---|---|
| 110 | 0.999 | 1.000 | 0.998 | 0.104 |
| 111 | 0.910 | 0.999 | 0.999 | 0.205 |
| 112 | 0.995 | 1.000 | 0.997 | 0.129 |
| mean | **0.968** (mark 0.60) | 0.9996 | 0.998 (mark 0.90) | 0.146 (mark <= 0.20) |

Min seed 0.910 (mark 0.50). Memorisation gap (held-out train-name minus novel): 0.00, 0.09, 0.00; the probe no longer leans on name identity much.
Note: C2 for seed 111 alone is 0.205; the carded control is the mean (0.146), which passes.

## Labels
- **Shown:** with 512 training names, a one-line probe finds the person's position on never-seen-name lines at 97% (chance 10%), passing every carded mark. G0's 43% is therefore mostly a 16-name memorisation effect of that probe, not a missing signal in the reader states.
- **Suggested (not tested):** seed 111's 0.91 vs ~1.0 for the others hints that the 8 test names' random vectors matter a little; with only 8 test names per seed this is not resolved.
- **Untested:** whether a writer trained only on the toy's 16 names (the real risk) can find the person. G0b does not test it. A PASS only lets the coordinator ask Ben about Stage 1 and the money-guard review round.
- Deviation, logged in the card: same-family reader (`n_ent_train=512`), so reader draws differ from G0 at the same seed.
