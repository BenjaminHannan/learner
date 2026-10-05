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

## Added 03:57 UTC, before they ran: arm MX (from the design panel), box A
The design panel (5 designers, 3 judges, 1 synthesizer; plan in `artifacts/ultracode-v4/PANEL-v4.md`) picked MX as the second route to the mark next to SR2, plus a core diagnostic battery (PR, LD, conditional OR / PL / LDD / DS / FZ) and a conditional 6-seed confirmation CF.
- **MX:** `--steps --steps-rich --answer-only-fams seq_cycle --final-lesions`: SR, except seq_cycle's target is just ` # answer` (no steps). One change against SR.
- Marks vs B1-B3: the screen marks (REACHES THE MARK if mean fit >= 272/320 and every seed >= 256). Vs SR1-SR3, paired by seed: "answer-only restores seq_cycle" if seq_cycle's 3-seed fit sum >= 115/172 and the other 7 families' sum is within 15 rows of SR's 706 (SR 3-seed fit 800 minus seq_cycle 94). Flag MEMORISES-SEQ if seq_cycle fit gains >= 20 rows over SR while its held-out gains < 5. Lesions are read with the SL/BL marks above.
- Wrong if: seq_cycle's fit sum stays below 105/172, the other 7 lose more than 15 rows against SR, or mean fit falls below SR's 266.7.
- Prediction (panel): seq_cycle 112-128/172, mean fit ~276 (86%), REACHES with p ~0.6; held-out 78-82%; family-mean lesion within 3 points of intact.

## Calibration SP result (job 15, read 04:01 UTC)
SP1-SP3 at 6k reproduce S1-S3 exactly (259 / 241 / 252). At 9k: 271 / 267 / 259; at 12k: **279 / 274 / 280 of 320 (mean 86.8%; every seed >= 85%)**. Held-out 252 / 246 / 253 (mean 78.9%, +9.1 over 6k: unlike P, the extra practice with steps also lifts held-out). By the marks: **"a practice-budget question"**: with the curriculum's own steps, the step route reaches the mark at 6 passes. (The screen's REACHES THE MARK is defined at 3 passes, so this is not a screen pass.)

## Arm SR2 result (job 21, read 04:36 UTC)
SR2 (SRB1-SRB3) fit **271 / 287 / 269 of 320 (mean 86.1%; seeds 84.7 / 89.7 / 84.1%)** vs paired baseline 214 / 213 / 212: gains +57 / +74 / +57 rows (mean +19.8 points). By the marks: **REACHES THE MARK** (mean >= 85% and every seed >= 80%). Held-out 254 / 267 / 253 (mean 80.6%; +32.5 over baseline, +0.1 over SR). All three runs finished cleanly (rc 0).
- Versus SR, paired: seq_cycle 3-seed fit 94 -> **122 / 172**: one row short of the 123 mark, so "v2 fixes seq_cycle" is **not** met (prediction 125-150 missed; its wrong-if, < 110, did not happen). The other 7 families 706 -> 705 (held). seq_cycle held-out did not move (63 -> 61 / 120), so the seq_cycle fit gain is mostly on practised rows.
- Next by the marks: the 6-seed confirmation CF (seeds 4-9). The panel's rule picks between SR2 and MX by 3-seed mean held-out if both reach; MX1-MX2 are still running.

## Added 04:37 UTC, before they ran: 6-seed confirmation CF of SR2 (seeds 4-9), boxes A and C
SR2 reached the mark on seeds 1-3, so it gets the confirmation now; MX's own 3-seed result is still running. If MX also reaches and has a higher 3-seed mean held-out (the panel's rule), MX gets the same confirmation with the same marks, and the kept arm is the one that confirms (both: the higher confirmation held-out).
- **CF4-CF9** = `--steps --steps-rich --seq-steps-v2 --final-lesions --save-texts`, seeds 4-9 (new fixed rows per seed, same 6,000 updates). No LM weights change, so no English check is needed.
- Marks (fixed now, from the panel): **CONFIRMED** if the mean fit over seeds 4-9 is >= 272/320 (85%) and every seed is >= 256 (80%). Otherwise not kept, and the 9-seed mean is reported.
- Lesions with the SL/BL marks (3-point band = "family switch"; family-mean drop >= 10 points and >= 5 more than BL's = "needs core row content"). Share for Ben = ((CF intact - CF family-mean) - (B intact - B family-mean)) / (CF intact - B intact), with B's drop from BL1-BL3.
- Saved texts feed an offline audit of the wrong chain-family rows: arithmetic slip / wrong operands or ops / final copy / truncated or no '#'.
- Prediction (panel): mean fit 84-88%, every seed >= 80% with p ~0.6; family-mean lesion within 3 points; core-content share < 15%.

## Arm MX result (job 22, read 06:18 UTC)
MX1-MX3 fit **277 / 278 / 273 of 320 (mean 86.25%)**, held-out 255 / 259 / 259 (mean 80.5%). By the screen marks: **REACHES THE MARK**. Versus SR1-SR3, paired: seq_cycle 3-seed fit 94 -> **119 / 172** (>= 115: "answer-only restores seq_cycle"); the other 7 families 706 -> 709 (held). But seq_cycle held-out 63 -> 62 / 120 while its fit gained 25 rows: **MEMORISES-SEQ** is flagged. By the panel's rule SR2 stays the confirmed arm (3-seed mean held-out 258.0 vs MX 257.7), so MX gets no confirmation of its own.

## Core lesion results (SL, BL, MX, CF4-CF6; read 06:18 UTC)
After training, each row's 8 core vectors are replaced by the family mean, by another same-family row's vectors, or by the global mean (positive control); drops in points of 320 rows.

| run | fit intact | family-mean | same-family | global-mean | held intact | family-mean | same-family | global-mean |
|---|---|---|---|---|---|---|---|---|
| BL1 (baseline, re-run) | 214 | -2.2 | -3.8 | -18.1 | 158 | -0.3 | +0.3 | -11.2 |
| BL2 | 213 | -5.9 | -7.2 | -23.8 | 153 | -0.9 | 0.0 | -12.2 |
| BL3 | 212 | -1.2 | -2.8 | -19.7 | 151 | +0.6 | -0.3 | -14.4 |
| SL1 (steps) | 259 | -3.4 | -7.8 | -35.9 | 228 | -0.3 | -2.2 | -28.8 |
| SL2 | 241 | -3.4 | -4.7 | -34.1 | 215 | +1.2 | -1.9 | -25.0 |
| SL3 | 252 | +0.6 | -1.2 | -28.1 | 227 | 0.0 | +0.6 | -25.0 |
| MX1 | 277 | -2.5 | -5.9 | -42.8 | 255 | -0.3 | -2.5 | -36.6 |
| MX2 | 278 | -5.0 | -5.3 | -39.1 | 259 | -1.6 | -2.2 | -42.5 |
| MX3 | 273 | -0.3 | -0.9 | -36.2 | 259 | -1.9 | -2.5 | -33.4 |
| CF4 (SR2 flags) | 269 | -1.9 | -3.1 | -43.4 | 250 | -0.6 | -1.6 | -37.2 |
| CF5 | 262 | -3.1 | -1.6 | -33.4 | 256 | -3.4 | -5.6 | -35.0 |
| CF6 | 278 | -3.8 | -6.9 | -36.2 | 265 | -2.2 | -3.4 | -33.1 |

(BL1 first crashed with out-of-memory; its re-run, added 06:43 UTC, reproduces B1's 214 exactly.)
- "Needs core row content" (family-mean drop >= 10 points and >= 5 more than BL's): **not met on any run** (largest family-mean drop 5.0 points, MX2).
- "Family switch" (family-mean and same-family both within 3 points on fit and held-out): met on SL3, MX3 and CF4; the others miss by up to 4.8 points, nearly all of it on practised rows (fit). On held-out, family-mean costs at most 3.4 points on every steps run.
- Share of the steps lift that needs core row content, paired by seed with BL: S seed 1 ((259-248) - (214-207)) / (259-214) = **+0.09**; seed 2 ((241-230) - (213-194)) / (241-213) = **-0.29**; seed 3 ((252-254) - (212-208)) / (252-212) = **-0.15**. Mean -0.12: the steps lift needs no row content from the core (at most 9% on one seed; on the other two the steps runs lose less to the family-mean lesion than the baseline does).
- The global-mean lesion costs 28-43 points with steps vs 20-24 without: with steps, the core's per-family signal (which format to write) matters more, not less.
- Reading for Ben: the LM does the thinking by writing the steps; the core tells it which kind of puzzle it is. Per the panel's plan, FZ (freeze the core) is skipped, since its result is predictable from these lesions.

## Error audit of CF4-CF6 saved texts (offline, `scripts/cap256_launch/uc_audit_v4.py`, read 06:18 UTC)
Wrong chain-family rows (chain_ops, state_update, chain_story2, var_chain) with intact core vectors, 3 seeds pooled:

| split | wrong rows | misread (extraction) | format | no '#' | arithmetic slip | final copy |
|---|---|---|---|---|---|---|
| fit | 52 | 35 (67%) | 13 | 4 | 0 (0%) | 0 |
| held-out | 73 | 49 (67%) | 14 | 2 | 7 (9.6%) | 1 |

- "An exact tool would remove most chain residuals" (slips >= 50%): **no**. Slips are 0% and 9.6%. Most misses are misreads: a dropped step (e.g. stops after 2 of 3 operations), a wrong operand, the wrong value carried into the last line (state_update adds jar A's old count), or a merged line the parser cannot read.
- So a calculator alone would fix little of what is left; what is left is reading the question.

## CF result: SR2 6-seed confirmation (jobs 24-conf-s4..s9, CF8 re-run as 28-conf-s8-rerun; read 07:50 UTC)
Fit **269 / 262 / 278 / 286 / 265 / 281 of 320** (seeds 4-9): mean **273.5 (85.5%)**, lowest 262 (81.9%). Held-out 250 / 256 / 265 / 266 / 261 / 262: mean 260.0 (81.3%). By the marks: **CONFIRMED** (mean >= 272 and every seed >= 256). With seeds 1-3, the 9-seed mean fit is 274.2 (85.7%). No LM weights change, so no English check is needed. SR2 (`--steps --steps-rich --seq-steps-v2`) is the kept arm.
- Lesions on all six (fit / held-out points; family-mean, same-family, global-mean): CF4 -1.9 / -0.6, -3.1 / -1.6, -43.4 / -37.2; CF5 -3.1 / -3.4, -1.6 / -5.6, -33.4 / -35.0; CF6 -3.8 / -2.2, -6.9 / -3.4, -36.2 / -33.1; CF7 -5.3 / -2.5, -5.9 / -6.2, -46.2 / -34.4; CF8 -1.2 / -0.6, -3.1 / -0.3, -40.0 / -37.5; CF9 -2.5 / -0.3, -0.9 / -1.6, -37.8 / -28.4. "Needs core row content" (family-mean >= 10 points) is not met on any seed, so FZ stays skipped: the confirmed lift is the LM's, and the core is a per-family switch.
- The prediction (mean 84-88%, every seed >= 80% with p ~0.6; family-mean within 3 points; share < 15%) held, except that the family-mean lesion exceeded 3 points on fit for CF5-CF7 (3.1-5.3).

## Added 07:45 UTC, before they ran: arm CR (the thinker's plan route inside the real model), box C
From the plan tests in `DIAG-v4.md` (PLOD: a fresh reader+core trained to output a plan, executed by an exact calculator, answers 86.9% of new chain questions with no LM in the loop). **CR** = SR2 + `--plan-route 17000` (new in `skills_pretrain_v1.py`): before the screen, a separate planner (fresh copies of the reader and core plus pointer and op heads, `--op-attend` design, no LM in its loss) trains on 17,000 distinct chain-family training rows (one pass) and is then frozen. During the screen, each chain_ops / state_update / chain_story2 / var_chain row gets its planner's plan executed by the calculator, and the result is appended after the question as ` = <value>`. That row's LM target becomes ` # answer` (no LM-written steps); the LM only has to say it. The other 4 families keep SR2's targets. `--final-lesions` adds `plan_swap`: each chain row gets another same-family row's ` = <value>`. Seeds 1-3 (CR1-CR3), paired with SR2's SRB1-SRB3. A 30-update smoke (CRSMOKE) runs first on the same box.
- Screen marks vs the baseline: **REACHES THE MARK** if mean fit >= 272/320 and every seed >= 256.
- Vs SR2, chain families (chain_ops, state_update, chain_story2, var_chain), 3-seed sums: held-out SR2 = 417 / 480, fit SR2 = 407 / 436. **"The thinker's route matches the LM's steps"** if the chain held-out sum is within 15 rows of 417; **"beats"** if >= 432. The other 4 families' 3-seed fit sum stays within 15 rows of SR2's (SR2 827 - 407 = 420).
- Attribution: **"the thinker decides each chain answer"** if `plan_swap` lowers the chain families' fit and held-out by >= 50 points (chain rows only) on every seed. The LM speaks the plan if chain-family accuracy (intact) is within 3 points of the planner's own plan-exact on those rows.
- Wrong if: chain held-out sum < 402 (more than 15 rows under SR2), or `plan_swap` costs < 25 points on chain rows.
- Prediction: chain held-out about 87% (the planner's), chain fit 88-92%, overall fit 84-88%; `plan_swap` leaves chain rows near 5%.

## Added 09:12 UTC, before they ran: arm CRD (CR with the decayed planner)
One change from CR: `--plan-cosine` (new in `skills_pretrain_v1.py`): the planner's lr decays from 1e-3 to 0 along a cosine over its one pass of 17,000 chain rows, as in PLCD (`DIAG-v4.md`: 97.6% held-out plan-exact on 6 seeds vs 83.0% without the decay). Seeds 1-3 (CRD1-CRD3), paired with CR1-CR3 and SR2's SRB1-SRB3. Started before CR1-CR3 finish, on the idle boxes (D: seeds 1-2, B: seed 3).
- Same screen and attribution marks as CR: **REACHES THE MARK** if mean fit >= 272/320 and every seed >= 256; chain held-out 3-seed sum **"matches the LM's steps"** within 15 rows of SR2's 417 / 480, **"beats"** if >= 432; other-4 fit sum within 15 rows of 420; **"the thinker decides each chain answer"** if `plan_swap` lowers chain fit and held-out by >= 50 points on every seed; the LM speaks the plan if chain accuracy is within 3 points of the planner's own plan-exact.
- Vs CR (paired): **"the better planner carries through"** if the chain held-out sum rises by >= 20 rows over CR's.
- Wrong if the chain held-out sum is < 432 (the planner's gain does not reach the answers), or CRD's chain accuracy is more than 3 points under its own plan-exact (the LM fails to say the value).
- Prediction: chain held-out about 95% (456 / 480), chain fit 96-98%, overall fit 88-92%; `plan_swap` leaves chain rows near 5%.

## Added 09:48 UTC, before they ran: arm LMDC (the LM's steps on PLCD's data and schedule)
PLS (`DIAG-v4.md`) shows the thinker's plan only ties the LM's steps on the screen's own chain practice (82.8% vs 85.8%), so PLCD's 97.6% vs the LM's 86.8% mixes two changes: the route and 17,000 distinct rows. **LMDC** = SR2's chain step targets (`--steps --steps-rich --seq-steps-v2`) on the 4 chain kinds only (`--families chain_ops,state_update,chain_story2,var_chain`), trained on exactly PLCD's rows in PLCD's order (`--fixed-rows 17000 --passes 1` draws with the same `fixed|seed` RNG as `uc_diag_v4.rows_for`), one pass, lr decaying from 1e-3 to 0 on a cosine (`--lr-final-mult 0`), `--minutes 400` so the 170-minute cap does not cut it. Held-out = the same 160 chain rows. Seeds 1-3, paired with PLCD seeds 1-3 (155 / 159 / 155).
- **"The plan route beats the LM's steps at matched data and schedule"** if PLCD is ahead by >= 5 rows on each of the 3 paired seeds.
- **"The LM's steps catch up with the data"** if LMDC's 3-seed mean held-out is >= 152 / 160 (95%): then PLCD's lead over SR2 was the data, not the route.
- Anything else: the data helps the LM but less than the route (report the paired gaps).
- Prediction: LMDC 140-150 (88-94%); the misreads that make up two thirds of the LM's chain errors shrink with more varied practice but do not vanish.

## CRD partial: seeds 1-2 (jobs 38-crd-s1, 38-crd-s2, read 10:21 UTC)
| run | fit | held-out | chain held (of 160) | planner plan-exact, chain held | other-4 held (of 160) | plan_swap: chain held | SR2 same seed: fit / held / chain held |
|---|---|---|---|---|---|---|---|
| CRD1 | 295 (92.2%) | 288 (90.0%) | 158 | 159 | 130 | 2 | 271 / 254 / 138 |
| CRD2 | 293 (91.6%) | 291 (90.9%) | 152 | 154 | 139 | 2 | 287 / 267 / 141 |

- Lesions (change in rows of 320, fit / held-out): CRD1 family-mean +1 / +3, same-family swap -15 / -4, global-mean -138 / -121, **plan_swap -135 / -156**; CRD2 -6 / -9, -5 / -7, -135 / -126, **plan_swap -136 / -150**. On chain rows, plan_swap takes held-out from 158 to 2 and from 152 to 2: the planner's value decides every chain answer, and the LM says it (chain accuracy within 1-2 rows of the planner's own plan-exact).
- Planner pretrain on this box: 14.3 / 14.6 minutes for the 17,000 rows (cosine to 0, loss 0.15 / 0.23).
- Marks are read when CRD3 is in.

## Added 10:21 UTC, before they ran: CRDC, the 6-seed confirmation of CRD
CRD with seeds 4-9 (jobs 43-crdc-s4..s9; box D seeds 4-6, box B seeds 7-9), paired with CF4-CF9 (SR2 on the same seeds: fit 269 / 262 / 278 / 286 / 265 / 281, held-out 250 / 256 / 265 / 266 / 261 / 262, chain held 133 / 135 / 139 / 142 / 140 / 140).
- **CONFIRMED** (the route model reaches the mark) if the mean fit over seeds 4-9 is >= 272 / 320 and every seed is >= 256.
- **"The thinker's route beats the LM's steps on new chain questions"** if CRDC's chain held-out is ahead of the paired CF seed on >= 5 of 6 seeds with a mean gain >= 5 rows.
- **"The thinker decides each chain answer"** if plan_swap lowers chain held-out by >= 50 rows of 160 on every seed.
- Wrong if the mean fit is < 272, or plan_swap costs < 25 rows on any seed.
- Prediction: fit 288-298, held-out 280-295, chain held 150-159 on every seed, plan_swap leaves chain rows under 6.

## CRD result, 3 seeds (jobs 38-crd-s1..s3, read 11:24 UTC)
| run | fit | held-out | chain fit / held (held of 160) | planner plan-exact, chain held | other-4 fit / held | plan_swap: chain held | SR2 same seed: fit / held / chain held |
|---|---|---|---|---|---|---|---|
| CRD1 | 295 | 288 | 137 / 158 | 159 | 158 / 130 | 2 | 271 / 254 / 138 |
| CRD2 | 293 | 291 | 140 / 152 | 154 | 153 / 139 | 2 | 287 / 267 / 141 |
| CRD3 | 302 | 281 | 153 / 160 | 160 | 149 / 121 | 2 | 269 / 253 / 138 |
| **mean** | **296.7 (92.7%)** | **286.7 (89.6%)** | 3-seed chain held sum **470 / 480** | 473 | other-4 fit sum 460 | 2 | 275.7 / 258.0 / sum 417 |

- By the marks: **REACHES THE MARK** (mean fit 296.7 >= 272, lowest 293 >= 256). Chain held-out sum 470 vs SR2's 417: **"beats"** (>= 432). Other-4 fit sum 460 vs SR2's 420: not "within 15 rows" but 40 rows *higher* (the mark guarded against a loss). **"The thinker decides each chain answer"**: plan_swap takes chain held-out from 158 / 152 / 160 to 2 / 2 / 2 (>= 50 rows on every seed). The LM speaks the plan: chain accuracy is within 2 rows of the planner's own plan-exact on every seed. None of the "wrong" conditions holds.
- Caveat, from LMDC below: the planner trains on 17,000 chain rows the SR2 model never saw, so the gain over SR2 on chain rows is the extra practice, not the route. What the route shows is that the reasoning for chain questions can move from the LM to the thinker with no loss.
- Other lesions (held-out, rows of 320): family-mean +3 / -9 / -2, same-family swap -4 / -7 / 0, global-mean -121 / -126 / -109.

## LMDC partial: seeds 1-2 (jobs 41-lmdc-s1, 41-lmdc-s2, read 11:24 UTC)
The LM writing SR2's chain steps, trained on exactly PLCD's 17,000 rows with the cosine decay: held-out **158 / 160 and 158 / 160** (98.8%); fit 314 / 320 and 317 / 320. Paired with PLCD (plan + calculator, same rows and schedule): 155 and 159, so PLCD is behind by 3 and ahead by 1.
- By the marks (seed 3 still running): **"the LM's steps catch up with the data"** (mean >= 152 already holds unless LMDC3 is below 140), and **not** "the plan route beats the LM's steps at matched data and schedule". PLCD's 97.6% vs SR2's 86.8% was the 17,000 distinct rows and the decay, not the route. The prediction (140-150) was too low.
- So at equal practice the 1.2B LM writing steps and the small thinker's plan are level on these chain kinds (PLS: 82.8 vs 85.8 at the screen's practice; PLCD/LMDC: about 98-99 at 17,000 rows).

## Added 11:29 UTC, before they ran: arm WD (both doors at 2048, Ben's ask)
SR2 plus one change, both doors widened at once: `--reader-hidden 2048` (into the thinker: 2048 -> 2048 -> 256 instead of 2048 -> 32 -> 256) and `--prefix-hidden 2048` (out to the talker: 259 -> 2048 -> 2048 instead of 259 -> 32 -> 2048). Both widenings are function-preserving (new units start with zero output weights), so the run starts exactly at main2. The thinker's middle stays 256 wide. Seeds 1-3 with `--final-lesions`, paired with SR2 seeds 1-3 (fit 271 / 287 / 269, mean 275.7; held-out 254 / 267 / 253, mean 258.0; family-mean lesion on fit -1.9 to -5.3 points on every SR2/CF run). Runs on Ben's PC (`PC-JOB-wd.md`).
- **"The wide doors let the thinker carry each question"** if the family-mean lesion costs >= 10 points of fit on every seed (SR2: <= 5.3).
- **"Wide doors help the score"** if mean fit >= 284 (SR2 + 8 rows); **"hurt"** if <= 268 (SR2 - 8).
- Wrong (the doors are not what keeps the thinker out) if the family-mean lesion stays under 5 points on every seed.
- Prediction: fit within 8 rows of SR2 and the family-mean lesion under 5 points. The talker reads the question itself, so a wider door gives it nothing it needs from the thinker.

## CR result, 3 seeds (jobs 35-cr-s1..s3, constant-lr planner, read 11:30 UTC)
| run | fit | held-out | chain fit / held | planner plan-exact, chain held | other-4 fit / held | plan_swap: chain held | CRD same seed: fit / held / chain held |
|---|---|---|---|---|---|---|---|
| CR1 | 287 | 268 | 124 / 136 | 137 | 163 / 132 | 3 | 295 / 288 / 158 |
| CR2 | 277 | 249 | 126 / 132 | 137 | 151 / 117 | 2 | 293 / 291 / 152 |
| CR3 | 270 | 263 | 128 / 137 | 137 | 142 / 126 | 2 | 302 / 281 / 160 |
| **mean** | **278.0 (86.9%)** | 260.0 (81.3%) | chain held sum **405 / 480** | 411 | other-4 fit sum 456 | 2.3 | 296.7 / 286.7 / sum 470 |

- By the CR marks: **REACHES THE MARK** (mean fit 278 >= 272, lowest 270 >= 256). Chain held-out sum 405 vs SR2's 417: **"matches"** (within 15 rows), not "beats". **"The thinker decides each chain answer"**: plan_swap leaves 2-3 of 160 on every seed. The LM speaks the plan within 3 points on seeds 1 and 3 (1 and 0 rows under plan-exact); seed 2 is 5 rows (3.1 points) under. Not wrong (405 >= 402; plan_swap costs >= 129 rows).
- **CRD vs CR (the CRD mark):** chain held-out +22 / +20 / +23 rows on the paired seeds (sum 470 vs 405, >= 20): **"the better planner carries through"** to the real model's answers.
- Planner pretrain took 84-87 minutes on box C (3 runs plus other jobs sharing one GPU) against 14-23 minutes for CRD on less crowded boxes; the recipe is the same apart from the decay.

## Added 11:32 UTC, before they ran: arm CRT (the talker calls the calculator, Ben's design)
CRD plus one change, `--plan-talk` (being built): on chain rows the thinker no longer hands the talker a finished value. It hands over its plan as a short note in the talker's own tokens (' thinker: 10 - 5 * 5'). The talker is trained to write a calculator call (' calc(10 - 5 * 5)'); at generation the call is intercepted, an exact left-to-right calculator answers (' = 25'; no loss on these tokens, the tool writes them), and the talker continues to ' # 25'. Other kinds keep SR2's targets. Lesions: plan_swap (the note of another same-family question) and note_drop (no note). Seeds 1-3, paired with CRD1-CRD3. Runs on Ben's PC.
- Screen mark as before: **REACHES THE MARK** if mean fit >= 272 and every seed >= 256.
- **"The talker-called calculator works as well as the direct route"** if the chain held-out sum is within 10 rows of CRD's 470 / 480.
- **"The thinker's note drives the call"** if, under plan_swap, chain held-out falls by >= 50 rows of 160 on every seed and the talker's call copies the injected note on >= 90% of chain rows.
- note_drop is reported, not marked: if the talker still answers chain rows well with no note, it can write the call from the question alone.
- Wrong if the chain held-out sum is < 440, or under plan_swap the call copies the injected note on < 70% of chain rows (the talker writes its own call and ignores the thinker).
- Prediction: chain held sum 455-475; plan_swap leaves chain rows under 10 / 160 with the call copying the note on > 95%; note_drop 40-80% (the talker can partly read the question itself).

## Result 12:03 UTC: CRDC, the decayed-planner route on 6 new seeds (marks fixed 10:22 UTC)
SR2 + `--plan-route 17000 --plan-cosine`, seeds 4-9, paired with SR2's confirmation seeds CF4-CF9 (CF8 = its rerun). Fit and held-out are of 320; chain held is the 4 chain families' 160 held-out rows; plan_swap is the lesion that gives each chain row another same-family row's planner value.

| seed | CRDC fit | CRDC held | CRDC chain held | plan_swap chain held | CF fit | CF held | CF chain held | chain gain |
|---|---|---|---|---|---|---|---|---|
| 4 | 303 | 297 | 159 | 3 | 269 | 250 | 133 | +26 |
| 5 | 284 | 277 | 152 | 3 | 262 | 256 | 135 | +17 |
| 6 | 298 | 291 | 156 | 2 | 278 | 265 | 139 | +17 |
| 7 | 309 | 289 | 156 | 2 | 286 | 266 | 142 | +14 |
| 8 | 295 | 287 | 157 | 2 | 265 | 261 | 140 | +17 |
| 9 | 295 | 281 | 158 | 2 | 281 | 262 | 140 | +18 |
| mean | **297.3 (92.9%)** | **287.0 (89.7%)** | 156.3 | 2.3 | 273.5 (85.5%) | 260.0 (81.3%) | 138.2 | **+18.2** |

- **CONFIRMED: reaches the mark** (mean fit 297.3 >= 272, every seed >= 256; lowest 284).
- **"Beats SR2 on chain rows"**: ahead on 6 of 6 seeds, mean gain +18.2 (mark: >= 5 of 6, >= 5). Shown, but confounded as written at 11:24 UTC: the planner practised on 17,000 chain rows that SR2 never saw, and LMDC shows the LM's own steps reach 98.8% with those rows. So this is "more chain practice through the thinker helps the whole model", not "the thinker reasons better than the LM".
- **The thinker decides every chain answer** on every seed: plan_swap takes chain held from 152-159 to 2-3 (drop >= 149 rows; mark >= 50).
- The planner alone gets 154-159 of 160 chain plans right (plan_correct); chain held is within 2 rows of that on every seed, so the talker almost always just says the planner's value.
- Held-out on the other 4 kinds (160 rows): CRDC 130.7 vs CF 121.8 on average (+8.9). Suggested, untested: the core no longer spends capacity on chain rows.
