# bm-394s PLAN: the reasoner on Sudoku-Extreme, the published way (benchmarks thread, 2026-09-25 ~20:00 UTC)

Registered before any Sudoku training or recipe exists. Asked for by the sleep research thread (358 line), which
will train the net; this thread owns the test and scores it. Harness: scripts/claude_bm394_grid.py (main 13571d013),
notes artifacts/claude-bm394-20260925/README.md.

Label for every number: "protocol-matched, in-domain Sudoku result". It is not a general reasoning score, and a
pass is never reported as one.

## Data (fixed)
- Test: the harness's seeded 10,000 of the 422,786 Sudoku-Extreme test puzzles (seed 394;
  sudoku_test.jsonl sha256 6c6d337a5e56577a9bac0928a7189c2a04d8e400ad931f522c02a532cf6ba70a). Only the reference
  checks (copy, and the exact solver on the first 500) have been run on it. No net has seen it.
- Practice: the harness's seeded 1,000 from the train file (sudoku_practice.jsonl sha256
  6edcb858a8a1e38512469bbcc8b858d8db08b8d8590b5bd0796b63159ecd46df); 0 of the 10,000 test puzzles are in the train file.
- Licence: the hub card has no licence tag. The source column names match tdoku's benchmark collections
  (puzzles0_kaggle ... puzzles6_forum_hardest_1106, plus 01_file1); tdoku's code is BSD-2 and HRM's dataset builder
  is Apache-2.0; the collections themselves come from puzzle forums and Kaggle (inferred from the names, not
  checked further). Use: practice and measurement for our own report, as the HRM and TRM papers did. Ben is told
  this in one line with the result (he asked for no questions until about 23:40 UTC).

## Rules the arm must follow (else the result is not reported as protocol-matched)
1. Training uses at most these 1,000 practice puzzles, with rule-keeping shuffles only (relabel digits, permute
   rows within a band and columns within a stack, swap bands or stacks, transpose), the published augmentation.
   No other Sudoku data, no generated Sudoku, no Reasoning Gym sudoku or maze tasks.
2. At test time the net alone answers: one try per puzzle, no search, no solver, no checker-guided retries, no
   voting over shuffles. The net's own rounds of thinking and its learned stop are allowed (that is the method).
3. The recipe (code commit and weights sha256) is frozen and sent to this thread before the test run. The test is
   run once. A crash may be re-run with the same frozen weights; nothing else is re-run.
4. Parameter count is reported. The same-size claim needs at most 7M weights (TRM-Att is 7M); at most 27M for the
   HRM comparison.
5. The plain twin from the same recipe (358's equal-size one-pass net) is scored the same way and reported.

## Pass marks (fixed now; exact whole-grid match, the harness's 95% Wilson interval on 10,000)
- S1, beats the published same-size model: the interval's lower end is above 74.7 (TRM-Att 7M), with at most
  7M weights.
- S2, beats HRM: the interval's lower end is above 55.0 (HRM 27M), with at most 27M weights.
- Report only: TRM-MLP 5M's 87.4; the loop net minus the plain twin (paired difference, harness `--pair`).
Anything else: no claim. A result below either mark stays a registered FAIL of that mark.

## What would prove the claim wrong
The lower end at or below the mark, a rule above broken, or the frozen weights not reproducing the reported score
on a re-score of the saved replies.
