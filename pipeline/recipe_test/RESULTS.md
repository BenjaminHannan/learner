# Real-pipeline recipe test: results (2026-10-03, fast lane, marks in PASS-MARKS.md fixed before training)

**Verdict (by the fixed marks): PARTIAL.** The copy path fixes unseen answers in the real pipeline modules (H1 passes). Varied wording does not
fix new-wording calls the way it did in the reimplementation (H2 misses on both of its conditions).

## Setup
Real modules, fresh weights, frozen LFM2.5-1.2B FP32: lexical-embedding reader, fresh 9.0M ordered core, real CalculatorPath + mechanical calculator
(predicted calls, real label policy), real StatePrefix exit pooled to 8 vectors. Batched copy of the batch-1 runtime (`run_arm.py: calc_forward`).
Batch 16, 3000 updates, 6 paired seeds, 4 arms. Eval: 192 questions, 60/30 train/held-out answer split (seed 20261101), model's own calls.
Not the PC checkpoints, not the English pilot. 24 runs, all rows in `results/`.

## Numbers (mean over 6 seeds, SD in brackets; per-seed values in the run files)
| arm | train fit | unseen-answer final | seen-answer final | new-wording call | train-wording call | new-wording final | all final |
|---|---|---|---|---|---|---|---|
| BASE (pooled exit, 4 templates) | 92.2 (2.9) | 0.3 (0.5) | 74.3 (2.5) | 59.4 (4.4) | 94.4 (0.5) | 30.6 (2.0) | 37.3 (1.2) |
| COPY only | 92.4 (2.2) | 68.1 (4.0) | 73.3 (0.5) | 58.5 (1.5) | 95.1 (2.2) | 55.6 (2.2) | 70.7 (2.1) |
| WORD only (varied wording) | 95.5 (2.1) | 0.2 (0.4) | 78.3 (3.1) | 68.6 (4.9) | 93.9 (0.8) | 35.2 (2.8) | 39.2 (1.5) |
| RECIPE (copy + varied) | 94.2 (2.6) | 72.4 (5.2) | 76.6 (1.4) | 64.8 (3.8) | 95.3 (2.3) | 63.5 (4.3) | 74.5 (3.0) |

## Marks
- Gate (BASE train fit >= 90%): 92.2%, met (narrowly; models are not fully fit at 3000 updates).
- H1 unseen-answer final: RECIPE 72.4% (>= 70 met), paired gain +72.0 (95% interval +66.2 to +77.9; >= +40 met), worst seed +65.6 (>= +25 met). **PASS.**
- H2 new-wording right-call rate: paired gain +5.4 (interval +0.6 to +10.2; needed >= +8, **missed**); RECIPE train-wording call 95.3% (needed >= 98, **missed**). **MISS.**
- PARTIAL. Not FALSIFIED (H1 gain far above +15).

## What it shows (shown / suggested / untested)
- Shown (6 paired seeds, exploratory ablation, same eval): the copy path alone takes unseen-answer accuracy from 0.3% to 68.1% (+67.7, interval +63.9 to +71.5). In BASE, about 91 of the 96 unseen questions come out as a training answer; with the copy path that drops to 5-7 of about 27-31. Varied wording alone does nothing for unseen answers (-0.2).
- Shown: with the copy path, final accuracy sits just under the right-call rate (RECIPE all: call 80.0%, final 74.5%), so the remaining errors are mostly wrong calls, but not exclusively: about 3.6 points are right calls overwritten by a later wrong call (the copy uses the latest OK result; last result right 76.4%) and about 2 more are lost between a right copied result and the emitted answer.
- Shown: the call is the limit, and it is an ADD problem on new wording. RECIPE ADD calls on new-wording frames: 32% overall; three of the six new families (bakesale, bus, library) get 0-2%, they are called SUB. SUB calls are 98%. Train-wording ADD 99%, but train-wording SUB 92% (tr-relational SUB 67%).
- Shown (smaller than in the reimplementation): varied wording lifts new-wording calls by +9.2 on the pooled exit and +6.2 on top of the copy path (interval +0.8 to +11.7), against +16.5 in the reimplementation, and the real pipeline reaches 60-69%, not 98%.
- Suggested: the real reader sees only context-free token embeddings through a 32-wide pipe and the action head reads their mean at loop 0, so telling "altogether" from "how many more" in unfamiliar phrasing is hard; the reimplementation used contextual LM states and teacher-forced the loop-0 call. Untested which of the two matters.
- Untested: starting from the trained parent checkpoints (now on claude/real-pipeline-checkpoints); the pointer exit / wider entry from the info-flow thread; more updates (train fit is 92-95%, not 100%); this eval has now been used by several runs, refresh before a headline claim.

## Suggested next single change (untested)
Give the action decision a better view of the sentence (read the call at a later loop or from a contextual reader), with the same eval and 6 paired seeds, marks fixed first. Or first check whether more updates alone lift ADD-on-new-wording.

Cost about $1.35 of vast credit, see LEDGER.md. First attempt lost its per-question rows to log truncation and was rerun.
