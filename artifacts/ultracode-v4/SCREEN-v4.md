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
B1-B3 fit 214 / 213 / 212 of 320 (mean 66.6%), held-out 158 / 153 / 151 (mean 48.3%); fit was still rising from 3k to 6k updates (+20 rows per seed).

## Added 02:29 UTC, before it ran: calibration P (more practice), box B
- **P (6 passes):** the baseline continued to 12,000 updates on the same 2,000 rows (`--passes 6 --updates 12000`; the first 6,000 updates are the baseline's own order). Evals at 3k, 6k, 9k, 12k. This is a budget calibration, not a 6k screen arm, so it is judged on its own marks:
  - "the mark is a practice-budget question" if 12k fit >= 85% (272/320) on all 3 seeds;
  - "more practice alone will not reach it soon" if mean 12k fit < 75% (240/320);
  - otherwise "in between", and the 9k-to-12k slope is reported.
  - Held-out at 12k is reported; if fit rises 10+ points over 6k while held-out rises < 3, it is flagged MEMORISES.
