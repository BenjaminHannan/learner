# VERIFY-02c — joined build 0.2c (verified 2026-09-26 ~11:05 UTC)

**Verdict: 0.2c = registered FAIL.** Registered FAILs stay FAILs.

Run: 006k on BensPC (results on origin/builder-outbox: RESULTS-benspc.md, run/, score/).
Build X = claude_e2e02c:build_02c (G + copy-practice sleep LoRA + lis-319 reader @0.995 + F1 delivered history; MEM, ROUTE, TRIM off). G = claude_e2e360:build_360. T = plain MiniCPM5-1B, thinking off.
Marks: PASSMARKS-02c.md + addenda (sealed; not edited). Seals: SEAL-code.sha256.txt (b89c105c3).

## Mark table

| Row | What | Bar | Result | Verdict |
|---|---|---|---|---|
| L1-L6 | sleep inside the joined assistant (3 nights) | as registered | lucky right 74 -> 192 of 100 fresh x samples; greedy 5 -> 12; puzzles reached 39 -> 61; lost 10 of 201 old-right general (limit 20); restart loads exact trained weights (sidecar sha OK) | PASS (6/6) |
| Q1 | think-numeric, X - G | >= +3 | 10 vs 12 = -2 | FAIL |
| Q2 | think-numeric, X - T | >= 0 | 10 vs 11 = -1 | FAIL |
| K2 | puzzles asked in plain English, X >= T | X >= T | 0 vs 0 | PASS (both zero) |
| Y1 | answerable memory asks, X - G | >= +10 pts | 45/195 vs 44/195 (+0.5 pts) | FAIL |
| ME1 | edit (correction) asks, X >= G | X >= G | 3 vs 4 | FAIL |
| H3 | never-told asks answered "don't know", X - G | >= -2 | 18 vs 33 of 36 (-15) | FAIL |
| H1 | wrong answers stated as fact, X - G | <= +2 | 8 vs 5 (+3) | FAIL |
| H2 | turns with a wrong save, X - G | <= +2 | 34 vs 36 (-2) | PASS |
| H4 | chat X vs G, conversations lost | <= 15/60 | G won 30, X 28, tie 2 | FAIL |
| C1 | chat X vs T, conversations won | >= 40/60 | 30 - 30 | FAIL |
| C2 | grammar, both graders | >= 90% | 92.3% and 93.0% (grader validity 39/40, 40/40) | PASS |
| K1 | creative useful | >= 30/50 and >= T | 18/50 vs T 21 | FAIL |
| S1 | made-up facts about the user, X <= T | X <= T | X 26 (chat 23 + creative 3) vs T 16 (14 + 2) | FAIL |
| H5/H6 | GSM8K / MMLU no-harm | as registered | not run (out of time) | NOT MEASURED |

Status labels (MANIFEST-02c.md): sleep = **passed inside the joined assistant** for its own rows. lis-319 reader, F1 delivered history = component PASS or fixed-in-code only; their joined rows above fail. MEM, ROUTE (#2), TRIM (#4) were not in 0.2c.

## Deviations (disclosed; FAILs stay)

- **D1 reader weights (my task-file error).** rent-02c step 5 (reused by 006k) gave bank D arm X `--model READER` = lis-301 weights, while build_02c runs the lis-319 interface. Rows H1, H2, H3, Y1, ME1 therefore ran the new reader's code with the old reader's weights and do not fairly test lis-319. The rows are reported as run.
- **D2 not run:** H5/H6 (GSM8K, MMLU) — out of time before 11:00 UTC.
- **D3 freeze moved** to ~05:20 UTC (BensPC instead of rental); composition unchanged.
- **Judge contamination.** Saves/asks judges 1 and 2 shared one scratch file (485/486 agreement), so they are not independent. Replaced by judges 3 and 4, each in a private folder; agreement saves 485/486, asks 34/35. Final H1/H2 use judges 3+4, judge 2 breaks the 2 splits. Judge 1 files kept for the record only.

## Judging

Blind opus judges saw packets only (neutral ids, shuffled arms); keys applied by script (judges/judge_prep02c.py, seeds 3364-3367). Chat pairs: 8 judges x 15 conversations (pair_a* = X vs G, pair_b* = X vs T). Grammar: two graders, 40 planted errors + 40 clean lines for validity (>= 36/40). Creative: one judge, 100 items (X and T mixed). Files: judges/out/, judges/keys/.

## Plain summary for Ben

The joined assistant failed overall. Sleep worked inside the real assistant: after 3 nights it got many more fresh puzzles right (74 to 192 lucky guesses, 5 to 12 first try) and forgot only 10 of 201 old questions. Grammar passed (about 92%), and it didn't save more wrong facts. Everything else failed: chat tied the plain model 30 to 30, creative was useful 18 of 50 times, it made up more about the user (26 vs 16), and it said "I don't know" far less often when it truly hadn't been told (18 vs 33 of 36). Part of the memory rows used the old reader's weights by my mistake, so those rows don't fairly test the new reader.
