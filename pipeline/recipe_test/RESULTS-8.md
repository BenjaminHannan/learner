# Round 8: long questions with irrelevant numbers inside (2026-10-04; marks in PASS-MARKS-8.md fixed before training)

12 runs on RTX 5090 boxes (LONG control re-run and DIST, seeds 0-5; two boxes were about 20x slow and were replaced). Rows in `results8/` (sha-checked, 84 files), table in `results8/SCORE8.txt`, scorer `score8.py`.
Code change that made it testable: task operands are found among the literals by value (x, y, z distinct), so pointer labels stay right when extra numbers are present; old rows map exactly as before.

## Verdict by the fixed marks: **partial, no claim** (USABLE met by a hair; NO-DROP missed on one guard by 0.6 point)
| chain, mean of 6 (SD) | LONG (no practice with distractors) | DIST | paired gain (95% interval) |
|---|---|---|---|
| **DISTR: long questions with 1-4 irrelevant numbers, 192** | 16.3 (1.9) | **50.2 (2.9)** | **+33.9 (+29.7 to +38.1)**, 6/6 up |
| DISTR call 1 right | 29.6 | 66.0 | +36.4 |
| DISTR call 2 right given call 1 | 55.2 | 76.1 | +21.0 |
| guard: round-7 long set (no numbers) | 62.4 (2.2) | 60.4 (2.5) | -2.0 (-6.1 to +2.1) |
| guard: old own-wording | 78.1 (3.5) | 77.4 (3.6) | -0.7 (-7.7 to +6.3) |
| guard: Blind-1 | 78.6 (4.0) | 79.2 (3.2) | +0.5 (-6.6 to +7.6) |
| guard: Blind-2 | 66.1 (2.7) | 62.4 (2.4) | **-3.6 (-8.1 to +0.9)**, mark was >= -3 |
1. USABLE (DIST chain on DISTR >= 50%): met, 50.2% (SD 2.9; two seeds are under 50).
2. NO-DROP (every guard mean gain >= -3): missed on Blind-2 (-3.6; the interval includes 0). Gate met (train fit 86-95%). The FAILS line (any drop below -5 or DISTR < 30%) was not reached.

- Shown: irrelevant numbers are a real problem for an untrained pointer. The round-7 recipe falls from 62.4% on numberless long questions to 16.3% once 1-4 irrelevant numbers are inside, with call 1 right only 29.6% (it points at the wrong number).
- Shown: practice on distractors fixes most of it (+33.9, every seed up, every layout kind and both seen/unseen finals), but the result is still only 50%, below the 62-79% the same recipe gets on short and numberless long questions.
- Shown by length: DISTR chain 57.2% at 55-80 tokens, 52.3% at 81-110, 45.2% at 111-150: more text means more places to be misled.
- Shown by layout: DIST does well on question-first (72%), first-person (69%), table (60%), spreadsheet (58%); worst on receipts (26%), reports (34%), other (42%). The slip of 2 to 4 points on the guards (round-7 long -2.0, Blind-2 -3.6) is small, not significant, and the same sign on 2 of 4 guards; it may be a real cost of spending training on distractors.
- Suggested, untested: the pointer heads need more than 3000 updates or a relevance step to ignore numbers reliably (call 1 only 66%); a larger share of distractor items or a longer run may close part of the gap without the slip.
- Not shown: distractor numbers of other kinds (3-digit, decimals, dates written as 12/05, numbers that look like quantities of the same item: those are the genuinely hard case and were excluded by design); the PC checkpoints.
- Caveats: distractor sentences for the eval were written by a separate Claude worker, layouts from Claude-written blind sets; fresh weights.

Cost round 8: about $1.1 (12 runs plus two replaced slow boxes); credit $8.43 at 17:32Z (shared).
