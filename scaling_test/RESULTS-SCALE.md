# Fair scaling on the real recipe: results (5 of 6 seeds; judged C not run)

Marks: `PASS-MARKS-SCALE.md` (pushed before training). Recipe: PR #33/#30 real pipeline, frozen LFM2.5-1.2B, contextual reader, all-words + pointer exit, 8000 generated practice rows per seed, 2000 updates. Only the core's distinct blocks change. Test: NEW-KINDS-S, 192 fresh questions in six new kinds (blind answer check 192/192). Data: `results/`, `ANALYSIS-SCALE.json`, `analyze_scale.py`.

## Deviation from the marks (stated up front)
Seed 0 was not completed. Its first box never finished loading (2 h) and was destroyed; the replacement box trained about 5x slower than the others (L2 at step 200 after 1,050 s, against about 0.9 s per update elsewhere) and was destroyed to stay inside the spend cap. So there are **5 paired seeds (1 to 5), not 6**, the interval uses t = 2.776 (df 4, wider than the 2.571 in the marks), and the bare-LM bar for judged C (`lm_fewshot` ran on the seed 0 box) was **not measured**: **judged C is not run.**

## Accuracy on NEW-KINDS-S (192 fresh questions, exact match, percent)
| size | core params | seed 1 | seed 2 | seed 3 | seed 4 | seed 5 | mean | train fit (96 bank rows) | FRESH-R3 (read) |
|---|---|---|---|---|---|---|---|---|---|
| S1, 2 blocks | 9,007,790 | 67.2 | 66.1 | 62.5 | 67.7 | 62.5 | **65.2** | 94.6 | 92.0 |
| S2, 4 blocks | 17,949,662 | 63.5 | 68.8 | 65.6 | 56.2 | 67.2 | **64.3** | 93.3 | 92.2 |
| S3, 8 blocks | 35,833,406 | 66.1 | 67.2 | 67.2 | 66.7 | 65.1 | **66.5** | 92.5 | 92.3 |

## Judged
- **A (S3 minus S1): IN BETWEEN.** Mean +1.25 points, interval -1.8 to +4.3, 3 of 5 seeds positive. The pass mark (mean >= +5, lower bound > 0) is missed. NOT SCALING needs an upper bound below +3.0, which the interval (4.3) does not meet, so no "does not scale" claim either.
- **B: not applicable** (A is not PASS). S2 minus S1 is -0.94 (interval -9.2 to +7.4), so the three points are not monotone.
- **C: not run** (no bar measured).

## Reads (not judged)
- A 4x larger core gave no measurable gain on new kinds: the three means are within 2.2 points and seed-to-seed spread (up to 12 points for S2) is larger than any size difference.
- Training fit and FRESH-R3 (the six practised kinds, about 92%) do not move with size either. It is not a case of the larger core fitting practice better.
- By kind (mean over seeds, S1 / S2 / S3): sum_of_two_quantities 23.8 / 22.5 / 22.5 (a floor: this recipe has no calculator and these are new arithmetic sums); possession_transfer_result 53.1 / 51.2 / 50.0; superlative_extreme 71.9 / 71.2 / 71.9; exclusion_only_except 77.5 / 73.1 / 75.6; passive_who_did_to_whom 81.2 / 84.4 / 89.4; what_changed_state 83.8 / 83.1 / 89.4. The two kinds that rise with size are the two where the S3 gain is about 6 to 8 points, but with 40 questions per kind and 5 seeds that is suggested only.
- Yes/no and short answers are both about 65%; yes/no has a 50% chance level.
- 44 to 47% of wrong answers are practice answers at every size.
- Time: 2,015 / 2,898 / 3,871 s per run (S3 costs 1.9x S1) on a shared RTX 5090 with three runs at once.
- Learning rate was not retuned per size (lr 1e-3 everywhere). E32 (more experts) was not run.

## What this does and does not show
Shown: at 5 seeds, on this test and recipe, quadrupling the core's distinct blocks does not raise accuracy on never-practised kinds by +5 points; the best estimate is +1.3 with an interval that includes small gains. Suggested: capacity in the core is not what limits new-kinds accuracy here; the fixed interface (32-wide reader, prefix and pointer) or the practice recipe may be. Untested: width or expert scaling, per-size learning rate, more loops, more practice kinds. Nothing here says anything about the own-weights model, and the bare-LM comparison for Ben's 1 to 2B-model goal is still open.
