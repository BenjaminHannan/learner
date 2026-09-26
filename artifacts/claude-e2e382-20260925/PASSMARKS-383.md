# 383: plain questions go straight to the 1B. Marks fixed 2026-09-26 ~01:15 UTC, before any run

Month-end thread, after the coordinator relayed Benchmarks' finding (00:50 UTC): inside 0.1 the 1B's GSM8K drops
from 191/300 to 29/300 and MMLU gives no letter on 134/300, because questions that are not about the user end in
"I'm not sure" or a clarify line. 382b does not touch this, so it is its own change, run in the same rental as 382b.

## The one change
R = scripts/claude_e2e383.py:build_383 = the 336b G arm + route383: when the final reply abstains or asks to rephrase
on a question that is not about the user (no recall/check wording, no my/mine/our, no name the notebook holds) and
nothing was written to the notebook, the base 1B answers it plainly under 338's guards. Control: G. Report only:
ER = build_383e (G + ep-382 k=20 + route383), the candidate 0.2 if 382b and 383 both pass.

## Marks (R vs G; same runs, tests and judging as PASSMARKS-382.md)
| Mark | What | Bar |
|---|---|---|
| Q1 | chatpanel382 think turns with a number, right by script (of 23): R − G | ≥ +5 |
| Q2 | bank C never-told asks answered "don't know" (the 336 scorer's M5 count): R − G | ≥ −1 |
| Q3 | bank C wrong answers stated as fact, judged as 336 M2: R − G | ≤ +1 |
Report only: GSM8K and MMLU-Redux via the Benchmarks harness (bm-391 registers its own marks); route383 counters
(tried, replaced after a think-split, replaced otherwise, kept because about the user, all guards failed).

## Proved wrong
If Q1 fails, the lost math is not recovered by handing abstained questions to the 1B inside the agent (look next at
turns that never abstain but answer wrongly, or at think299b itself). If Q2 or Q3 fails, the about-the-user test is
too narrow and routing leaks memory questions to the 1B.

## Addendum 2026-09-26 ~01:45 UTC, before any run (no mark changed)
Benchmarks found that on LoCoMo the about-the-user test would miss almost every question about the people talking
(1 of 1,540 with no names in the notebook), so R would answer them from the question alone. The test now also
counts any name heard in an earlier turn of the same chat (a capitalised word inside a sentence, or "<Name> said";
kept in <state_dir>/route383_names.json). Checks: scripts/claude_e2e383_test.py 11/11. Same change, same marks.
