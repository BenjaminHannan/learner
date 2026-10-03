# Two-doors test: results (2026-10-03)

Question (Ben, 19:08 UTC): do the fixes from "two narrow doors" work? Marks were fixed in `PASS-MARKS.md` and committed (69115ebe1) before any training. Reimplementation harness on vast (RTX 3090s), not the PC pipeline. Fast lane: generated held-out split.

Task: short stories (3 people, 2 objects, 2 places), questions answered by one word from the story. One-hop: who took X, where did P go, what did P take. Two-hop: who has X after a hand-over, where is X via the person who took it. Unseen-answer stories use only words never seen in training. 384 eval questions, 6 seeds per arm, 3000 updates x 16.

## Numbers (accuracy %, mean of 6 seeds)

| arm | unseen answers | seen answers | two-hop | one-hop | train fit | wrong unseen answers that are training words |
|---|---|---|---|---|---|---|
| A today (8 averages) | **0.0** (all 6 seeds) | 16.9 | 9.5 | 7.5 | 22.0 | 1152 / 1152 |
| C sharper averages | 0.0 | 14.9 | 8.2 | 6.7 | 21.1 | 1152 / 1152 |
| W wider door in (32 -> 256) | 0.0 | 28.2 | 14.6 | 13.6 | 40.4 | 1152 / 1152 |
| B pointer exit | **51.1** | 51.4 | 61.1 | 41.4 | 67.8 | 12 / 563 |
| BW pointer + wider door | 56.2 | 53.2 | 64.6 | 44.9 | 67.4 | 1 / 504 |

B lesion (pointer weights made uniform at test): unseen 0.0 (BW lesion also 0.0). Pointer top weight lands on the answer word in 77% of questions. Train wording vs new wording for B: 68.4 vs 34.1.

## Verdicts against the fixed marks

- **B pointer exit: PASS.** Unseen answers B - A = +51.1 points (95% CI +45.3 to +57.0; every seed +44 to +59). Seen answers +34.5 (CI +28.9 to +40.0), so no cost on seen answers. The lesion removes the whole gain (51.1 to 0.0), so the gain comes from pointing.
- **W wider door in: PASS, narrowly.** Seen-answer two-hop W - A = +10.2 (CI +2.9 to +17.6; seeds +3 to +19). Mark was +10 with CI above 0.
- **BW vs B (does the wider door still help once the exit is open): IN BETWEEN.** Two-hop BW - B = +3.5 (CI -3.5 to +10.4). The rule says 4 more paired seeds, then the line stops.
- **C sharper averages:** 0.0 on unseen answers, same as A. "More and sharper vectors" is not enough; pointing is what does it.

## What it means

- Shown, on this task: the 8-average exit cannot say a word it never said in training. Every one of A's 1,152 wrong unseen answers was a training word, the same closed-set signature as the calculator (PR #29) and the English pilot (F-E1, 74%).
- Shown: a pointer exit fixes it, and also lifts seen answers from 17% to 51%. The talker still never reads the story; it only gets the words the core points at.
- Suggested: the wider door in helps when the exit is the averaging one, but adds little once the pointer is there (+3.5, not settled).
- Not solved: overall accuracy is about 51-55%. Train fit is only 68% after 3000 updates, so the runs are still underfit, and new wording is weak (34% vs 68%). One-hop "who took / where did P go" questions are harder than two-hop ones here (41% vs 61%), which is odd and not yet explained.
- Not shown: anything about the PC pipeline, the English pilot itself, longer answers (all answers here are one token), or answers that are not words in the input.

## Suggested next single changes (untested)
1. Port the pointer exit to the real pipeline (branch `claude/real-pipeline-code`) with the copy path and varied wording, and run the English pilot with it.
2. On this harness: train longer (train fit 68%), then varied wording (it fixed new wording for the calculator).

## Provenance
All 30 runs' JSON and per-question rows are in `results/box*/out/`; `analyze.py` writes `ANALYSIS.json`. Cost and the hung-loop mistake are in `LEDGER.md` (about $1.5 total).
