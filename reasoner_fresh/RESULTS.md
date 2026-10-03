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
