# Fair scaling on the real recipe: results (6 paired seeds, all three judged marks run)

Marks: `PASS-MARKS-SCALE.md` (pushed before training). Recipe: PR #33/#30 real pipeline, frozen LFM2.5-1.2B, contextual reader, all-words + pointer exit, 8000 generated practice rows per seed, 2000 updates. Only the core's distinct blocks change. Test: NEW-KINDS-S, 192 fresh questions in six new kinds (blind answer check 192/192). Data: `results/`, `ANALYSIS-SCALE.json`, `analyze_scale.py`. Seed 0 was re-run after two failed boxes (see LEDGER.md); its code and settings are identical to seeds 1 to 5. An earlier version of this file reported 5 seeds; this one replaces it.

## Accuracy on NEW-KINDS-S (192 fresh questions, exact match, percent)
| size | core params | s0 | s1 | s2 | s3 | s4 | s5 | mean | train fit | FRESH-R3 (read) |
|---|---|---|---|---|---|---|---|---|---|---|
| S1, 2 blocks | 9,007,790 | 60.4 | 67.2 | 66.1 | 62.5 | 67.7 | 62.5 | **64.4** | 94.6 | 92.3 |
| S2, 4 blocks | 17,949,662 | 70.3 | 63.5 | 68.8 | 65.6 | 56.2 | 67.2 | **65.3** | 93.9 | 92.6 |
| S3, 8 blocks | 35,833,406 | 65.6 | 66.1 | 67.2 | 67.2 | 66.7 | 65.1 | **66.3** | 92.7 | 92.6 |
| bare LFM2.5-1.2B, 8 examples | 0 trained | | | | | | | **62.5** | | 75.0 |

## Judged
- **A (S3 minus S1): IN BETWEEN.** Mean +1.91 points, 95% interval -0.95 to +4.77, 4 of 6 seeds positive. The pass mark (mean >= +5, lower bound > 0, >= 5 of 6 seeds positive) is missed; NOT SCALING needs an upper bound below +3.0, which 4.77 does not meet. No scaling claim, and no "does not scale" claim.
- **B: not applicable** (A is not PASS). S2 minus S1 is +0.86 (interval -6.9 to +8.7); the three means do rise in order (64.4, 65.3, 66.3), the steps are far smaller than the seed spread.
- **C (S3 against the bare 1.2B LM shown the same 8 examples): PASS.** S3 minus bar is +3.8 points (interval +2.9 to +4.7), lower bound above 0. The bar is one deterministic run (62.5%), so the interval reflects seed variation of the trained model only. On the six practised kinds the bare model scores 75.0%, the trained model about 92.6% (from PR #30, similar here).

## Reads (not judged)
- Size changes accuracy little compared with seed-to-seed spread (S2 ranges 56.2 to 70.3). Training fit and the practised-kinds score do not rise with size either, so the larger core is not simply fitting practice better.
- By kind (mean over seeds, S1 / S2 / S3; bare LM in brackets): exclusion_only_except 77.1 / 74.0 / 75.5 [81.3]; passive_who_did_to_whom 81.8 / 85.4 / 90.1 [87.5]; what_changed_state 83.3 / 84.9 / 88.5 [78.1]; superlative_extreme 69.3 / 72.4 / 71.9 [59.4]; possession_transfer_result 50.5 / 51.6 / 50.5 [43.8]; sum_of_two_quantities 24.5 / 23.4 / 21.4 [25.0]. The sums are a floor for both: the recipe has no calculator. The kinds that rise with size (passive, what_changed) rise about 5 to 9 points; with 32 questions per kind this is suggested only.
- Yes/no and short answers: S1 64.9 / 63.9, S2 66.0 / 64.6, S3 67.7 / 64.9 (yes/no chance is 50%).
- 44 to 47% of wrong answers are practice answers at every size.
- Run time: 2,118 / 3,027 / 4,127 s per run (S3 costs 1.9x S1) on a shared RTX 5090, three runs at once.
- Learning rate was not retuned per size (lr 1e-3 everywhere). E32 (more experts) was not run.
- The lesion check (zero the pooled core vectors at test) drops FRESH-R3 accuracy to 0% at every size, so answers still depend on the core's state; the pointer path alone does not produce them.

## What this does and does not show
Shown: with 6 paired seeds, on this test and recipe, the trained system beats the bare 1.2B LM on never-practised kinds by about 4 points (the whole-model comparison Ben counts, 1.2B + about 10 to 37M trained), and quadrupling the core's distinct blocks adds about +1.9 points with an interval that includes both 0 and the +5 mark. Suggested: core capacity is not the main limit on new-kinds accuracy here; the fixed 32-wide interface or the practice recipe may be. Untested: width or expert scaling, per-size learning rate, more loops, wider interface, more practice kinds, larger models. The whole-model comparison used one bare-LM prompt format (8 fixed examples), not a tuned prompt. Nothing here says anything about the own-weights model.
