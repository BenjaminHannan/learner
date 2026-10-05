# Fit screen v4 (ultracode): marks, written before any arm ran

Written 2026-10-05 02:13 UTC (10:13 PM ET Oct 4). Fast lane. Boxes: Vast RTX 5090 A (queue/) and B (queue/b/).

## What changed since screens v1-v3
- Every eval now uses `--gen-fix`: generation sees the training layout `[pooled][prompt][BOS]`. Before, generation saw the prompt twice. Shown in job 06: main2 worst-8 trainfit 121 -> 161 / 320, held-out 89 -> 123 / 320, all 1,360 in_dist 68.5% -> 74.6%.
- Shown in job 06: with the fix, swapping in another same-family question's 8 core vectors leaves in_dist at 74.4% (1,012 vs 1,014 / 1,360; per family within a few rows). The core's vectors carry no question-specific information today.
- Shown in jobs 03-05: reader + core with a direct answer-class head (no LM in the loss, 6,000 batch-1 updates) fits only 43-49 / 320 trainfit rows, almost all of them group_induct (a binary family); computed-number families stay near 0.

## Setup (unchanged from v1-v3 except --gen-fix)
main2, `--copy-path --gen-fix`, worst-8 families, 2,000 fixed rows x 3 passes = 6,000 updates, batch 1, seeds 1-3; fit = 320 of the training rows, held-out = the 320 in_dist rows of the 8 families. **Baseline B1-B3** = the same with no other change (box B, job 11). Every arm is paired with the baseline of the same seed.

## Marks (fixed now, for every arm in this screen)
- **REACHES THE MARK** if mean fit >= 85% (272/320) and every seed >= 80%.
- **FIXES FIT** if mean fit gain >= +15 points over the paired baseline and all 3 seeds gain.
- **HELPS** if the mean gain is +5 to +15 with all 3 seeds positive. **NO EFFECT** otherwise; **HURTS** if the mean gain is -5 or worse.
- Held-out gain is reported for every arm; an arm that fixes fit but loses 5+ held-out points is flagged MEMORISES.
- A winner is not kept until a 6-seed confirmation (own marks, written before it runs) reproduces it; any arm that changes LM weights also needs the English check (92.6% bar).

## Arms
- **S (worked steps):** `--steps`: target = the row's steps + " # " + answer; scored on the text after the last "#". Steps carry intermediate values for chain_ops, state_update, chain_story2 and var_chain only (labels for the others). Prediction: the 4 chain families gain most (the bare LM with worked steps gets 77-87% on them, `results/01-diag-bare`). Wrong if NO EFFECT on those 4.
- Further arms are added below with their own timestamp, before they run.

## Baseline result (job 11, read 02:27 UTC)
B1-B3 fit 214 / 213 / 212 of 320 (mean 66.6%), held-out 158 / 153 / 151 (mean 48.1%); fit was still rising from 3k to 6k updates (+20 rows per seed).

## Added 02:30 UTC, before it ran: calibration P (more practice), box B
- **P (6 passes):** the baseline continued to 12,000 updates on the same 2,000 rows (`--passes 6 --updates 12000`; the first 6,000 updates are the baseline's own order). Evals at 3k, 6k, 9k, 12k. This is a budget calibration, not a 6k screen arm, so it is judged on its own marks:
  - "the mark is a practice-budget question" if 12k fit >= 85% (272/320) on all 3 seeds;
  - "more practice alone will not reach it soon" if mean 12k fit < 75% (240/320);
  - otherwise "in between", and the 9k-to-12k slope is reported.
  - Held-out at 12k is reported; if fit rises 10+ points over 6k while held-out rises < 3, it is flagged MEMORISES.

## Arm S result (job 12, read 02:56 UTC)
S1-S3 fit 259 / 241 / 252 of 320 (mean 78.3%) vs paired baseline 214 / 213 / 212: gains +45 / +28 / +40 rows, mean **+11.8 points, all 3 seeds positive -> HELPS** (not FIXES FIT, not REACHES THE MARK: seeds 80.9 / 75.3 / 78.8%). Held-out 228 / 215 / 227 vs 158 / 153 / 151: **+21.7 points** (no MEMORISES flag). The prediction held: the 4 chain families gained most (3-seed fit sums, baseline -> S: chain_ops 42 -> 92 / 96, chain_story2 77 -> 102 / 103, state_update 61 -> 102 / 118, var_chain 66 -> 110 / 119). The 4 families whose curriculum "steps" are only labels lost fit: cipher_map 77 -> 63 / 105, fewshot_number_rule 70 -> 41 / 108; group_induct 123 -> 125 / 139, seq_cycle 123 -> 117 / 172.

## Added 02:56 UTC, before they ran: arm SR (rich steps, box A) and calibration SP (steps + 6 passes, box B)
- **SR (rich steps):** `--steps --steps-rich`: the same as S, except cipher_map, fewshot_number_rule, group_induct and seq_cycle get worked steps built from each row's own meta (e.g. cipher encode `d=7 ; a=6 ; a=6`, fewshot add `37 - 23 = 14 ; rule: add 14 ; 12 + 14 = 26`, group parity `A even, B odd ; 58 is even`, seq_cycle `cycle y f, length 2 ; (7-1) mod 2 = 0 ; item 0 = y`). Checked on all 21,807 training rows of those families: the last step implies the row's answer every time; longest target 31 tokens (generation limit 48). The 4 chain families keep their curriculum steps.
  - Paired against the baseline B1-B3 with the screen's marks above (REACHES THE MARK / FIXES FIT / HELPS / NO EFFECT / HURTS).
  - Also paired against S1-S3: "rich steps fix the label families" if the 4 families' 3-seed fit sum rises by 60+ rows over S (from 346 / 524) and the 4 chain families stay within 15 rows of S (406 / 436).
  - Prediction: mean fit 84-90%; wrong if the 4 label families gain fewer than 20 rows over S.
- **SP (steps, 6 passes):** S continued to 12,000 updates on the same rows (`--steps --passes 6 --updates 12000`). Calibration with P's marks: "a practice-budget question" if 12k fit >= 85% on all 3 seeds; "more practice alone will not reach it soon" if mean 12k fit < 75%; otherwise in between. Its first 6,000 updates repeat S exactly.

## Calibration P result (job 13, read 03:12 UTC)
P1-P3 at 6k reproduce B1-B3 exactly (214 / 213 / 212). At 9k: 230 / 222 / 220; at 12k: 230 / 230 / 235 of 320 (mean 72.4%), held-out 157 / 152 / 165 (mean 49.4%, +1.3 over 6k). Mean 12k fit < 75% -> **"more practice alone will not reach it soon"**; the extra fit is mostly memorised (held-out flat).

## Added 03:14 UTC, before they ran: core lesions SL (S + lesions) and BL (baseline + lesions)
Asked through the coordinator (Ben wants the reasoner, not the LM, doing the reasoning): how much of S's lift needs the core? S and B ran without checkpoints, so both are re-run exactly (P showed re-runs are deterministic: P1-P3 at 6k = B1-B3) with `--final-lesions`: after training, trainfit and held-out are scored again by generation with each row's 8 pooled core vectors replaced by (i) its family's mean, (ii) another same-family row's vectors, (iii) the global mean.
- **SL1-SL3** = `--steps --final-lesions`, seeds 1-3 (box A); **BL1-BL3** = `--final-lesions`, seeds 1-3 (box B). Their intact scores must equal S1-S3 / B1-B3 (else the lesion runs are not the same models, and this is reported).
- Marks, on the 3-seed means: **"the core is still only a family switch"** if S's family-mean and same-family lesions are both within 3 points of S intact on trainfit and on held-out. **"S's lift needs the core's row content"** if S's family-mean lesion drops trainfit by 10+ points AND by 5+ points more than B's own family-mean drop. In between: reported as is.
- Reported for Ben: the share of the S lift that needs row content from the core = ((S intact - S family-mean) - (B intact - B family-mean)) / (S intact - B intact), on trainfit and on held-out.

## Arm SR result (job 14, read 03:40 UTC)
All three runs finished training and their 6,000-update eval, then crashed in the extra end-of-run dev splits (`KeyError: 'xs'`: the "variant" dev split has fewshot/group/seq variants with other meta). Scores below are from each run's 6,000-update `skills-eval` event, the same eval every other arm is judged on. Fixed since (rich_steps falls back to the curriculum steps when a row's meta does not fit).
- SR1-SR3 fit 253 / 274 / 273 of 320 (mean **83.3%**; seeds 79.1 / 85.6 / 85.3%) vs paired baseline 214 / 213 / 212: gains +39 / +61 / +61 rows, mean **+16.8 points, all seeds -> FIXES FIT**. Not REACHES THE MARK (mean < 85% and seed 1 < 80%). Held-out 251 / 260 / 262 (mean **80.5%**, +32.4 over baseline, +10.7 over S).
- Versus S: the 4 label families' 3-seed fit sum 346 -> 394 / 524 (+48: below the +60 mark for "rich steps fix the label families"; the prediction's wrong-if (< +20) did not happen). Chain families 406 -> 406 / 436 (within 15 rows: held). By family (fit, 3 seeds): cipher_map 63 -> 92 / 105, fewshot_number_rule 41 -> 88 / 108, group_induct 125 -> 120 / 139, **seq_cycle 117 -> 94 / 172** (the rich seq_cycle steps hurt).

## Added 03:42 UTC, before they ran: arm SR2 (seq_cycle steps v2), box A
- **SR2:** `--steps --steps-rich --seq-steps-v2`: identical to SR except seq_cycle. next_letter steps no longer need the number of shown items: `cycle e h l f a ; last is e ; after e comes h`. kth_letter steps index the cycle and write the remainder as a division: `cycle 0=y 1=f ; 7-1 = 6 = 2*3 + 0 ; 0=y`. Checked on all 6,849 training rows: the last step gives the answer every time; longest target 45 tokens (limit 48).
- Marks vs baseline B1-B3: the screen marks above. Marks vs SR1-SR3: "v2 fixes seq_cycle" if seq_cycle's 3-seed fit sum is >= 123 / 172 (the baseline's level) and the other 7 families stay within 15 rows of SR in total.
- Prediction: seq_cycle 125-150 / 172; mean fit 85-89%. Wrong if seq_cycle stays under 110.
- If SR2 REACHES THE MARK, its 6-seed confirmation (seeds 4-9, own marks written first, with --final-lesions) follows, and since the LM weights do not change, no English check is needed. Whether the core or the LM does the work is measured by the lesions (SL/BL now, and the confirmation's own).
