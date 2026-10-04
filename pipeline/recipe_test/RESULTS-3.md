# Round 3: two-step chained calls, with and without the ordered read (2026-10-03; marks in PASS-MARKS-3.md fixed before training)

**Verdict by the fixed marks: the ordered read FAILS on the real model** (needed >= +5 chain points; got -11.8). It does not reproduce the stand-in result (chain 56.5% -> 70.8%).

Setup: round-2 recipe (copy path + composed wording + contextual reader) on two-step problems, real modules, fresh weights, 6 paired seeds, 3000 x 16. Label policy extended to chains (task calls in order).
TWO = base; TWO-O = each loop reads the question with its own learned attention query instead of the mean. Fresh eval: 192 new two-step questions, 4 structures x 4 op pairs x unseen/seen finals
(narrative, question-first, table layout, distance), new wording, disjoint from training (DISJOINTNESS-TWO-r3.json). 12 runs, rows in `results3/` (sha-checked, 0 mismatches).

| mean of 6 seeds (SD) | TWO | TWO-O | paired gain (95% interval) |
|---|---|---|---|
| train fit (two-step items, chain) | 99.6 (0.4) | 99.9 (0.2) | gate met (>= 70) |
| **chain (both calls right), all 192** | **54.9 (9.3)** | 43.1 (2.2) | **-11.8 (-23.2 to -0.4)**, 5 of 6 seeds down |
| call 1 right | 78.2 (8.2) | 62.8 (4.0) | |
| call 2 right given call 1 | 70.0 (7.8) | 68.8 (4.3) | |
| final answer right | 54.8 (9.2) | 43.8 (2.9) | |
| narrative chain | 61.5 (15.8) | 31.9 (5.0) | -29.5 |
| question-first chain | 51.0 (15.2) | 24.7 (4.8) | -26.4 |
| table-layout chain | 29.9 (17.7) | 21.5 (13.7) | -8.3 |
| distance chain | 77.1 (10.6) | 94.1 (8.3) | +17.0 (all 6 seeds up) |
| second op = SUB / ADD | 52.4 / 57.3 | 34.7 / 51.4 | |
| first op = SUB / ADD | 59.5 / 50.2 | 30.6 / 55.6 | |
| unseen / seen finals (chain) | 57.1 / 52.6 | 43.9 / 42.2 | |

- Shown: both arms fit the training data (99.6-99.9%), so the gap is on new wording/structures. TWO alone reaches 54.9% chain, about the stand-in's V arm (56.5%), with large seed spread (SD 9.3, range 44-68). The weak structures are still weak: table layout 30%, question-first 51%.
- Shown: the ordered read lowers chain on narrative and question-first questions by about 26-30 points and on table layout by 8, raises distance by 17, and mostly hurts when the first operation is SUB (59.5 -> 30.6). It makes the seeds more alike (SD 2.2) but at a lower level.
- Shown: the copy path still holds: final == chain on all but 9 of 2304 rows.
- Suggested, untested: the learned loop queries (init 0.02 randn, one per loop, 3000 updates) may collapse to near-uniform attention or latch on position cues that fit training wording; with a contextual reader the mean read is already informative, so the stand-in's gain (which used the same reader) may have depended on its other details (teacher-forced call slots, bf16, fixed result slots).
- Not shown: any other way of ordering the read; more updates; whether another seed set changes the picture (interval is -23 to -0.4, so a small effect cannot be ruled out, but a gain of +5 or more is not supported).
- Real-pipeline fact found on the way: the real core refuses questions over 49 tokens with EOS. The first launch crashed in 8 of 12 runs on that; data generation now resamples to fit (the eval set was already within the cap). Longer problems need a core change.
- Caveats: eval wording authored by the same model that designed the test, not independently checked; two-digit add/subtract, exact calculator, fresh weights, not the PC checkpoints.

Cost round 3: about $0.85 (first launch ~$0.27 lost to the length crash, second ~$0.58). Total thread about $2.9, credit about $6.7 after (shared across threads).

Suggested next single change (untested): since TWO is the better arm, look at why table layout and question-first calls fail (call 1 right only 78%): more composed table/question-first training variety, or a larger loop budget. Keep the ordered read out until it is shown to help here.
