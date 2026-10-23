# Generalization gap: plan and pass marks (written 2026-10-23, before any probe or training result)

Problem: v1 FULL D scores 80.1% on DEV (train shards 380-399) but 44.7% on `validation` (REPORT-V1).
The sealed `test` split is never built, read or scored by anything in this line of work.

## What differs between train and validation (shown, from `learnlab/village/scheduler.py` and a regenerated split)
Validation is held out on four item axes (`learnlab.splits.AXES`: name, template, teacher_style, rule_family) **and**
it is also harder by construction:
- question depth: train MAX_DEPTH 3; validation up to 6. Regenerated validation (1,000 visits, 8,675 questions, matches
  REPORT-V1's count): depth 4-6 = 1,558 questions (18.0%); train has none.
- rule combination: train allows <= 1 rule application per answer; validation allows 1 family but many applications.
- new rule family R8 (validation/test only): 383 questions (4.4%) involve it.
- more "deepen" steps (0.35 vs 0.15 per period) and quieter clock lines (0.8 vs 0.5).
- teacher styles: validation uses 2 styles (childlike, plain) never seen in train.
- qtype mix differs (more Q4/Q12/Q13).
So "new names / wording / rules" is only part of the story; "harder questions" (depth, combination) is a fifth axis.

## Phase 1: probe sets (diagnosis, inference only)
Each probe = 1,000 fresh visits generated from the TRAIN split with exactly one thing switched to its validation
setting (fresh seed, so no visit overlaps TRAIN or DEV). Test-split items are never drawn (asserted).
- P0     nothing switched (fresh in-distribution control)
- Pname  validation names
- Pword  validation narrator/question templates
- Pstyle validation teacher styles (and their templates)
- Pdepth validation difficulty knobs (depth <= 6, combination rule, deepen/quiet rates), families R1-R7 only
- Prule  R8 allowed (validation family set), other knobs train
- (validation itself, all switched)
Attribution: drop(X) = acc(P0) - acc(PX). Gap G = acc(P0) - acc(validation).
- **Axis X is "the bottleneck"** if drop(X) >= G/2. **Wrong if** no single drop reaches G/4 (gap spread evenly / interaction).
- Also reported per question: depth, qtype, families, R8, style_status, name_answer.

## Phase 2: one change at a time (D-only, FULL recipe = Muon + S2, no bridge/creative, same steps)
Baseline B = D-only, seed 0 (and seed 1 to measure noise N = |acc_seed0 - acc_seed1| on validation).
Each fix arm changes ONE thing in the training data or recipe:
- F-depth  train visits also carry validation-style difficulty (depth <= 6, combination), still TRAIN names/templates/styles/families.
- F-word   extra TRAIN-only templates and teacher styles (paraphrases written by Claude), validation/test templates untouched.
- F-name   names re-drawn from a large fresh made-up pool each epoch (no validation/test names).
- R3a      (inference only) forced extra think loops at test time, setting picked on DEV.
**Pass** (fixed now): validation >= B + 8 points AND DEV >= B - 2 points AND gain > 2N.
**Wrong if** validation gain < 3 points (not the bottleneck), or the gain is only on qtypes/depths the fix was not aimed at.
A passing fix is then stacked onto the next; stacking is reported separately.
