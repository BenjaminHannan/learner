# Fresh-data (never-repeating) reasoner test: results, 2026-10-03

Question: does training on never-repeating problems stop "right calculator call, wrong final number" on answers never seen in training?

**Answer: no. Marks were fixed in `PASS-MARKS.md` and sealed in `SEAL.json` (commit 9b27533a8) before training. The FALSIFIED rule fired: arm B unseen-answer accuracy was <= 15% on both seeds.**

## Setup (a reimplementation, not the PC pipeline)
Frozen LFM2.5-1.2B-Instruct, contextual reader (LN, 2048-32-256), 9.23M-param core (2 shared blocks, 8 experts top-2, 4 loops), calculator call read from h+e at the top of each loop (value/status notebook slots), question positions mapped 256-32-LM width and average-pooled to 8 prefix vectors, frozen LM reads BOS + 8 prefix and emits the answer token. The PC pipeline code and checkpoints are not in the repo, so the data, the call/readout code and the TRAIN rows are re-created here (`model.py`, `train.py`, `gen.py`). Treat results as about this recipe family, not as a re-run of the 128-output pipeline.
- Answers are two-digit (one LM token). 90 possible answers split once by fixed seed: 60 train answers T, 30 held-out answers H. No training problem (either arm) has an answer in H, and no eval operand pair is in any training stream.
- Arm A: a fixed pool of 256 questions repeated (~187 times each). Arm B: 48,000 distinct questions. Both 3000 updates x batch 16, lr 1e-3 (picked by train fit on a separate probe seed; both LRs fit 100%), 2 seeds.
- Eval: 96 matched ADD/SUB pairs (192 questions), sealed; authored by one subagent, checked by an independent one (`EVAL-CHECK-REPORT.md`, PASS). Cells: answers unseen/seen x train wording/new wording, 24 pairs each. Score = the model's own call (no gold), frozen LM's first token equals the answer.

## Numbers (final-answer accuracy; right-call rate in brackets)
| run | unseen answers (96 q) | seen answers (96 q) | pairs both right unseen / seen | wrong unseen answers that equal a training answer | train fit (192) |
|---|---|---|---|---|---|
| A seed 0 | 0.0% (call 88.5%) | 86.5% | 0/48 / 35/48 | 95/96 | 100% |
| A seed 1 | 3.1% (call 90.6%) | 91.7% | 0/48 / 40/48 | 93/93 | 100% |
| B seed 0 | 0.0% (call 94.8%) | 90.6% | 0/48 / 39/48 | 96/96 | 100% |
| B seed 1 | 4.2% (call 90.6%) | 85.4% | 0/48 / 34/48 | 91/92 | 100% |

Per cell, unseen answers: A0 0/0 (train/new wording), A1 6%/0%, B0 0/0, B1 4%/4%. Seen answers on train wording: 98-100%; on new wording 71-85%.

Marks: PASS needed B unseen >= 50%, >= A+25 points, >= 70% of B seen. Not met. FALSIFIED (B <= 15% on both seeds) met.

## What it means
- The calculator step works: the right operation and operands are chosen ~90% of the time and the result is exact. The failure is after the call: the final number comes out as a number from the training answers (every wrong unseen answer, 375/377 across runs, is a training answer).
- Never-repeating questions did not help. In both arms the output path behaves like a lookup over the 60 answers it was trained to emit, not a copy of the calculator's result. The talker (8 averaged prefix vectors into a frozen LM) learned a closed set.
- Caveat on the test itself: a held-out answer is also a token that was never an output target, so this also asks whether the talker can emit a token it never trained on. That is the point of the original 0/64 observation, and it still holds here. Whether any fix (answer registers read 1:1, C2a in the reasoner design, or letting the LM copy the result token) removes it is untested.
- Not shown: anything about scale, other task kinds, or the PC pipeline.

## Suggested next single change (untested)
Give the result a direct path to the output (e.g. the talker reads the calculator's result slot 1:1, no pooling), same eval, same marks.

## Known problems / provenance
- Per-question rows were printed to the box log but truncated by the log service, and the box was destroyed before I confirmed the copy-back (my error: the rule was to check first). Aggregates above come from the intact summary lines in `results/box-log-excerpt.txt`; per-question rows are lost. A re-run (about 20 minutes on one RTX 3090) would regenerate them.
- Cost ledger: box 54028432 (RTX 3090, $0.163/h) 15:14-16:02 UTC, no output (stuck, destroyed): ~$0.13. Box 54032774 (same type) ~16:03-16:27 UTC: ~$0.07. Total about $0.20 of the $14.71 credit.

---
# Follow-up: direct copy path (2026-10-03, marks in `PASS-MARKS-2.md`, fixed before training)

One change: arm C = arm B plus the frozen LM's own embedding of the calculator's result token as a 9th prefix vector (zeros if the call was invalid). Compared with a re-run of arm B (it reproduced the first run's numbers exactly). Same sealed eval form, 3000 x 16 updates, lr 1e-3, seeds 0 and 1. All 768 per-question rows were copied back and counted before the box was destroyed (`results/*-rows.json`, `results/SUMMARY-copy-test.json`).

| run | unseen answers | seen answers | right call (unseen / seen) | pairs both right unseen / seen | wrong unseen = training answer |
|---|---|---|---|---|---|
| B pooled, seed 0 | 0.0% | 90.6% | 94.8% / 90.6% | 0/48 / 39/48 | 96/96 |
| B pooled, seed 1 | 4.2% | 85.4% | 90.6% / 85.4% | 0/48 / 34/48 | 91/92 |
| C copy, seed 0 | 89.6% | 84.4% | 89.6% / 84.4% | 38/48 / 33/48 | 0/10 |
| C copy, seed 1 | 84.4% | 80.2% | 84.4% / 80.2% | 33/48 / 29/48 | 0/15 |

Marks: unseen >= 50% (met both seeds), beats B by >= 25 points (met), unseen >= 70% of seen (met; unseen is higher than seen), and C seen not more than 5 points below B seen (**missed**: 6.2 and 5.2 points down). Not falsified. Strictly that is not a full PASS; read it as: the copy path removes the lookup, and costs about 5-6 points on seen answers in new wording.

What it means:
- With the copy path, final accuracy equals the right-call rate exactly (unseen 89.6% = call 89.6%, and so on). Every remaining error is a wrong call, none is a wrong readout. The wrong unseen answers are no longer training answers (0 of 25).
- So the pooled exit was the whole problem for unseen answers, in this recipe. The next limit is the call itself: 80-90% overall, and on new wording the seen-answer call rate is only 60-69% for C (71-81% for B).
- Not shown: that this holds for other tasks, bigger numbers, multi-step answers, or the PC pipeline. The copy only works because a calculator hands over the exact token; it removes the need for the model to compute it.
- Suggested next single change: improve the call on new wording (operation/operand choice after thinking, "think before calling" in the shortlist), since that is now the only error source.

Cost: box 54035873 (stopped at once, relaunch after a log fix) ~$0.00; box 54035893 (RTX 3090, $0.163/h) ~16:29-16:52 UTC ~$0.08. Running total for this thread about $0.30.

---
# Follow-up 2: think before calling (2026-10-03, marks in `PASS-MARKS-3.md`, fixed before training)

One change on the copy-path base: the calculator is blocked in loops 0 and 1, so the first call is read after 2 core advances (loop 2). Baseline: copy-path arm (call at loop 0). Seeds 0, 1, 2 each, same sealed eval, 3000 x 16 updates. All 1152 per-question rows were copied back, counted and checked against the eval form before the box was destroyed (`results/*-rows.json`, `results/SUMMARY-delay-test.json`).

Headline: right-call rate on new-wording questions (96 per seed).

| seed | copy only (call at loop 0) | call after 2 rounds | change |
|---|---|---|---|
| 0 | 73.96% | 93.75% | +19.8 |
| 1 | 64.58% | 100.0% | +35.4 |
| 2 | 98.96% | 85.42% | -13.5 |
| mean | 79.2% | 93.1% | +13.9 |

Right-call rate on train wording is 100% in all six runs. Final accuracy (all 192 questions): copy only 87.0 / 82.3 / 99.5%, delay 96.9 / 100 / 92.7%. Unseen-answer accuracy: copy only 89.6 / 84.4 / 100%, delay 96.9 / 100 / 91.7%; no wrong unseen answer is a training answer in any of the six runs.

Marks: PASS needed >= +4 points on all 3 seeds AND >= +8 on average AND train-wording call not >3 points lower. Mean (+13.9) and train wording are fine, but **seed 2 went down 13.5 points, so the all-seeds condition is missed: no full PASS.** FALSIFIED needed mean < +3 or negative on 2 of 3 seeds: not met. Result: in between.

What it means:
- The seed spread is huge. The copy-only baseline's new-wording call rate ranges 65% to 99% across seeds, so the earlier "seen-answer drop of 5-6 points" for the copy arm was seed noise (its seen accuracy is 84 / 80 / 99% over three seeds, mean 88%, against the pooled arm's 91 / 85).
- Blocking the call for 2 rounds looks helpful on average (+14 points; 2 of 3 seeds up by 20-35) and narrows the spread (85-100% vs 65-99%), but with 3 seeds and one seed worse, this is suggested, not shown.
- Not shown: that the effect holds with other wording families, other tasks, or beyond the 4-loop budget.
- Suggested next: more seeds (e.g. 6 per arm) on the same eval to settle whether the delay helps or the baseline's seed luck dominates. Each extra run is about $0.02.

Cost: box 54038731 (RTX 3090, $0.163/h) ~16:58-17:30 UTC ~$0.09. Running total for this thread about $0.40 of the credit.

---
# Follow-up 3: 6 seeds of "think before calling" (rule in `PASS-MARKS-4.md`, fixed before seeds 3-5)

Seeds 0-2 came from follow-up 2 (exploratory); seeds 3-5 are new runs of the same code. All 1152 rows checked against the eval form before the box was destroyed (`results/*-rows.json`, `results/SUMMARY-6seed.json`).

Right-call rate on new-wording questions (96 per run):

| seed | copy only | call after 2 rounds | gain |
|---|---|---|---|
| 0 | 74.0% | 93.8% | +19.8 |
| 1 | 64.6% | 100.0% | +35.4 |
| 2 | 99.0% | 85.4% | -13.5 |
| 3 | 87.5% | 86.5% | -1.0 |
| 4 | 79.2% | 62.5% | -16.7 |
| 5 | 85.4% | 72.9% | -12.5 |

Paired mean gain **+1.9 points** (SD 21.2, 95% t-interval for n=6: -20.3 to +24.1). Clean seeds 3-5 alone: mean gain **-10.1**.

Rule: PASS needed mean >= +4 with the interval above 0 and the clean seeds above 0; FALSIFIED if the 6-seed mean gain < +2. The mean is +1.9, so **FALSIFIED** (narrowly on the mean, clearly on the clean seeds). The +14 from three seeds was seed luck, not an effect of the delay.

Standing numbers for future marks (6 seeds, same recipe, same eval; right-call rate on new wording is the noisy one):
- Copy-only arm: new-wording right-call mean 81.6%, SD 11.9 points (range 64.6-99.0). Final accuracy over all 192 questions mean 90.8%, SD 5.9 (range 82.3-99.5). Unseen-answer final accuracy mean 92.5%, SD 5.3 (range 84.4-100).
- Delay arm: new-wording right-call mean 83.5%, SD 13.7 (62.5-100). Final all 91.8%, SD 6.9. Unseen-answer final 91.8%, SD 6.7.
- A single-seed difference under about 25 points on new-wording calls, or about 12 points on overall accuracy, cannot be told from seed noise at 2-3 seeds; marks for future single changes should be paired over at least 6 seeds.
- Train-wording right-call rate is 100% in every run of both arms; the variation is entirely in generalising to new wording.
- No wrong unseen answer is a training answer in any of the 12 runs, so the copy path result stands across all of them.

What it means: the unseen-answer problem is solved by the copy path in all 12 runs (unseen final 81-100%). The remaining error is call quality on new wording, and it is mostly seed luck: delaying the call does not fix it. Suggested next: a change aimed at wording generalisation itself (more varied training wording, since the training stream has only 4 templates), measured paired over 6 seeds.

Cost: box 54041927 (RTX 3090, $0.163/h) ~17:33-18:10 UTC ~$0.10. Total for this thread about $0.50; credit about $14.0.

---
# Follow-up 4: varied training wording (rule in `PASS-MARKS-5.md`, fixed before training)

One change on the copy-path base: the training stream is half the old 4 templates and half 180 procedurally composed frames (`gen2.py`) instead of the 4 old templates only. Baseline: the copy-only runs for seeds 0-5 (the pipeline is deterministic per seed; the exact re-run of pooled B showed this). 6 new runs, seeds 0-5. All 1152 rows checked against the eval form before the box was destroyed (`results/armBcopy-mix-seed*-rows.json`, `results/SUMMARY-wording.json`).

**Disjointness check (how):** `gen2.py` drops every composed frame (24 of 204 dropped) that shares a full sentence or any word 6-gram (placeholders kept as tokens) with any of the 12 eval new-wording frames. The kept 180 frames share 0 six-grams and 0 sentences with the eval; training and eval names (0 shared) and nouns (0 shared) are disjoint; no training question text equals an eval question (checked on a 2000-question sample); eval operand pairs are excluded from training. Report: `results/DISJOINTNESS-REPORT.json`. Limit: this is surface overlap only; the composed stories (two quantities in two places, start-then-gain/loss) share their overall shape with some eval families.

Right-call rate on new-wording questions (96 per run):

| seed | old wording only | varied wording | gain |
|---|---|---|---|
| 0 | 74.0% | 100.0% | +26.0 |
| 1 | 64.6% | 92.7% | +28.1 |
| 2 | 99.0% | 100.0% | +1.0 |
| 3 | 87.5% | 97.9% | +10.4 |
| 4 | 79.2% | 100.0% | +20.8 |
| 5 | 85.4% | 97.9% | +12.5 |

Paired mean gain **+16.5 points** (SD 10.4, 95% t-interval +5.6 to +27.4). Every seed is up. Train-wording right-call rate is 100% in all six.

Rule: PASS needed mean >= +8, interval lower bound > 0, and train-wording right-call mean >= 98%. All three hold: **PASS** (shown on this eval, 6 paired seeds).

Spread: varied-wording new-wording right-call mean 98.1%, SD 2.8 points (range 92.7-100), against SD 11.9 for old wording. Final accuracy over all 192 questions: mean 99.0%, SD 1.4 (old wording 90.8%, SD 5.9). Unseen-answer final accuracy mean 99.3%, SD 1.3. No wrong unseen answer is a training answer. Pairs both right were not re-counted here.

What it means: with a copy path for the result and a calculator for the call, the failures on unseen answers and on new wording both went away on this task, once training wording was varied. The lever for the remaining error was wording variety, not training length or call timing.

Not shown: other task kinds (here only two-number add/subtract), larger numbers, multi-step problems, truly new story structures, or the PC pipeline. This is a calculator-assisted copy task; it says little about how a model computes hard answers itself. The eval new-wording set is only 6 families and has now been used for many decisions in this thread, so it should be refreshed before any headline claim.

Cost: box 54045204 (RTX 3090, $0.163/h) ~18:02-18:36 UTC ~$0.10. Total for this thread about $0.60; credit about $13.9.

---
# Follow-up 5: sealed headline confirmation on new story structures (rule in `PASS-MARKS-6.md`; eval `EVAL-FORM-v2.json` sealed in `SEAL-v2.json`)

Eval v2: 96 matched ADD/SUB pairs in six story structures that training never shows (question first, distractor sentence, table layout, quoted dialogue, future tense with scene-setting, distance with units). One subagent wrote it, an independent subagent checked it (`EVAL2-CHECK-REPORT.md`; first check found number words like "two"/"first" in the text, the author's templates were patched by me and the check re-run: PASS), hash-sealed before any training, scored once per run. Arms, 6 seeds each: copy-only (old 4 templates) vs combined (copy path + varied training wording). All 2304 rows were counted and checked against the form before the boxes were destroyed (`results/*-v2-rows.json`, `results/SUMMARY-eval2.json`). One box crashed with CUDA errors on 5 of 6 combined runs (bad GPU); I destroyed it and re-ran all 6 seeds on another box (extra cost ~$0.09).

Right-call rate on all 192 v2 questions:

| seed | copy-only | combined | gain |
|---|---|---|---|
| 0 | 74.5% | 81.8% | +7.3 |
| 1 | 73.4% | 80.2% | +6.8 |
| 2 | 69.8% | 78.1% | +8.3 |
| 3 | 65.6% | 76.0% | +10.4 |
| 4 | 66.7% | 75.5% | +8.9 |
| 5 | 75.5% | 84.9% | +9.4 |

Paired mean gain **+8.5 points** (SD 1.3, 95% interval +7.1 to +9.9). Combined mean right-call rate **79.4%** (SD 3.6; copy-only 70.9%, SD 4.2).

Rule: CONFIRMED needed mean gain >= +8 (met), interval lower bound > 0 (met), and combined mean >= 80% (**missed by 0.6 points**). FALSIFIED needed gain < +3 (not met). Strictly: not a full CONFIRMED, in between. Read it as: the gain from varied wording holds on genuinely new story structures and is consistent on every seed, but it is smaller than on the first eval (+16.5) and the combined recipe is not near-perfect there (79%).

Where it still fails (right-call rate, copy-only / combined): table layout 38% / 36%, question-first 64% / 70%, distance-with-units 57% / 78%, dialogue 76% / 98%, future-scene 92% / 100%, distractor 100% / 94%. So the remaining errors are specific structures (a list layout with no sentence, the question stated before the facts), which the composer never shows. Final accuracy equals the right-call rate in every run (copy path), unseen-answer accuracy is 72.2% (copy-only) and 78.6% (combined) against 69.6% / 80.2% on seen answers, and no wrong unseen answer is a training answer (0 of 283).

Standing numbers on this harder eval (6 seeds): copy-only SD 4.2 points, combined SD 3.6; paired-gain SD 1.3.

---
# Follow-up 6: two-step problems, chained calls (fast lane, marks in `PASS-MARKS-7.md`, fixed before training)

Recipe as before (copy path, 4 loops) plus a call head that can point at 3 numbers and at the result slots of calls 1 and 2; training = 70% two-step items (x op1 y, then that result op2 z) plus 30% one-step items, never-repeating, two-step training wording from `gen_two.py` (pruned of any frame sharing a sentence or 6-gram with the eval frames). Eval: 96 two-step questions with different wording (48 final answers unseen as training answers, 48 seen), simple held-out split, no sealing. 6 seeds; 576 rows checked before destroying the box (`results/two-seed*-rows.json`, `results/SUMMARY-twostep.json`). Code: `model2.py`, `train2.py`, `gen_two.py`, `build_eval_two.py`.

| measure (mean of 6 seeds, SD) | value |
|---|---|
| call 1 right | 64.4% (2.0) |
| call 2 right | 45.7% (1.2) |
| both calls right (chain) | 39.9% (0.9) |
| final accuracy | 39.9% (0.9) |
| final on unseen answers / seen answers | 42.7% / 37.2% |
| train fit (two-step items, chain) | 100% (all seeds, at the end of training) |

Rule: HOLDS needed chain >= 80% and unseen >= 75% and < 20% of wrong unseen finals equal to a training answer. FAILS if chain < 50% or unseen < 40%. Chain is 39.9%: **FAILS**.

What it shows:
- The copy path holds in the sense that matters: whenever the chain is right, the final answer is right (final accuracy equals chain rate in every run). No readout error appears.
- The calls do not hold on the new wording. Per operation pair (seed 0; seed 3 is similar): add-then-add 19/24 chain right, subtract-then-add 20/24; **any problem whose second step is a subtraction is 0/48 on call 2**, and add-then-subtract also loses call 1 (1/24 and 5/24). The training fit is 100%, so this is generalisation to new wording of the loss/gain phrases, not inability to learn the task.
- That is the same kind of failure as before (call decided from pooled features on wording seen only in 4 families of phrases), now made worse by two operations in one text. Suggested, not shown: the calls need the same wording variety that fixed the one-step case, plus likely a way to read the operations in order (the action head reads a mean over the question, which cannot tell the first operation from the second).
- 59% of wrong unseen finals equal a training answer (97 of 165); this is about what chance gives for wrong values (training answers are two-thirds of the values), so it is not evidence of a lookup.

Cost for follow-ups 5 and 6: boxes 54049235, 54049236 (crashed), 54049875, 54052643 at ~$0.16/h for 0.5-0.9 h each: about $0.45. Credit now about $13.0. Total for this thread about $1.1.

---
# Follow-up 7: two-step with varied wording (V) and ordered read (O) (fast lane, marks in `PASS-MARKS-8.md`, fixed before training)

Four arms, 6 seeds each, all scored on `EVAL-TWO-v2.json`: 96 two-step questions with the earlier eval wording plus 96 held-out variants of table / question-first / distance structures (wording in no training frame; `results/DISJOINTNESS-TWO.json`: 0 shared 6-grams, 0 shared sentences). BASE = narrative wording only. V = BASE plus composed table, question-first and distance-with-units training frames. O = each loop reads the question with its own learned attention query instead of the mean. VO = both. All 4608 rows were checked against the eval form before the boxes were destroyed (`results/twoB-*-rows.json`, `results/SUMMARY-twostep-arms.json`). Code: `gen_two2.py`, `model2.py` (`ordered`), `train2.py`, `build_eval_two2.py`.

Chain rate (both calls right = final right) on all 192 questions, mean over 6 seeds (SD):

| arm | all 192 | earlier wording | held-out table/question-first/distance | call 1 | call 2 | second op = SUB | second op = ADD | paired gain vs BASE (95% interval) |
|---|---|---|---|---|---|---|---|---|
| BASE | 28.0% (1.4) | 39.6% | 16.5% | 54.7% | 34.0% | **0.0%** | 56.1% | - |
| V | 56.5% (4.7) | 54.9% | 58.2% | 68.5% | 67.0% | 53.0% | 60.1% | +28.5 (+22.3 to +34.7) |
| O | 25.6% (2.1) | 41.1% | 10.1% | 49.5% | 32.0% | 0.0% | 51.2% | -2.4 (-4.6 to -0.3) |
| VO | **70.8%** (5.1) | 77.4% | 64.2% | 77.7% | 79.3% | 66.1% | 75.5% | **+42.8** (+36.5 to +49.0) |

Per held-out structure (chain, mean of 6 seeds), BASE / V / O / VO: question-first 39% / 59% / 25% / 47%, table 0.5% / 31% / 1% / 48%, distance 10% / 84% / 4% / 97%, earlier wording 40% / 55% / 41% / 77%.

Rule (per arm vs BASE): PASS = paired mean gain >= +15 with interval lower bound > 0; FAILS = gain < +5.
- **V: PASS** (+28.5).
- **O alone: FAILS** (-2.4; slightly worse, interval just below 0).
- **VO: PASS** (+42.8, and the best arm).

What it shows:
- Varied wording is the main lever again: it takes the "second step is a subtraction" calls from 0% to 53%, and fixes distance-with-units (84-97%). Every seed is up for V and VO.
- The ordered read does nothing alone but adds +14 points on top of varied wording (VO 70.8% vs V 56.5%, with a stable per-seed gap). So the ordered read helps only once the wording is diverse enough to learn from; alone it cannot fix a wording failure. This interaction is suggested by 6 paired seeds, not isolated by a separate arm of V vs VO (that is the V vs VO comparison above, paired by seed in the saved summary).
- Still weak: table layout (31-48%) and question-first (47-59%), both far from the 80% bar set earlier for one-step. Seed spread is larger for V and VO (SD 4.7-5.1) than for BASE (1.4).
- The copy path holds throughout: final accuracy equals chain rate in every run; unseen-answer finals track the chain rate (V 58.2%, VO 70.3%).

Limits: fast lane (no authored/sealed eval); the eval's held-out structures were written by me, and BASE/O never saw any of them; add/subtract only, two-digit values, an exact calculator; the training frames for the weak structures are procedural (few sentence shapes each).

Cost: four boxes, ~$0.16/h, ~0.9 h each: about $0.55. Credit now about $12.3. Total for this thread about $1.7.
