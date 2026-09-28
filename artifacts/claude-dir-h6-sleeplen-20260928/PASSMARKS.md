# dir-h6 pass marks: does a gentler long night keep the grid gain that slp-358n3's long night lost?

Written 2026-09-28 19:24 UTC (`date -u`) by helper H6. Fixed before any run of this test. No score of the new arm (B)
exists anywhere. One disclosure about order: `scripts/claude_dir_h6_sleeplen.py` was drafted about a minute before this file
(py_compile only, never run); it contains no marks, and nothing in it depends on a result. Marks are never changed after a
score is seen. The reasons for each number are in DESIGN.md section 4.

Scope: the full-size loop reasoner (4 checkpoints from 358u, seeds 13-16), code-made sums and Latin grids. It is not the
small card experiments and not the village model. Training data: code-made puzzles and code answers only (as slp-358n3).

## The one change
Arm B is slp-358n3's long night (L: 6,000 steps a night, lr 3e-5 constant, half the batches from the day's 300 puzzles
per kind and half rehearsal, 3 nights) with ONE change: the learning rate is 3e-5 x 300 / 6,000 = 1.5e-6 (the same
learning rate x steps as the 300-step night S). Everything else is identical to L: same checkpoint, same 3 days of
puzzles, same rehearsal stream, same batch plan, same round draws, same optimizer settings.

Arms run on every seed, all from the same checkpoint: N (no night), S (300 steps, lr 3e-5), L (6,000 steps, lr 3e-5),
B (6,000 steps, lr 1.5e-6). S, L and N are re-run as controls in the same code and on the same card; the earlier
slp-358n3 numbers are context only. Seeds 13, 14, 15, 16. Tests, day puzzles, day sizes (sums 12, grids 7), exclusions:
exactly slp-358n3's (its `sizes.json`, its test seed 58630, its day seeds). Grading is after night 3.

## Marks (per seed; counts are right answers out of the test size)
Two kinds of tests: day tests (day_sums, day_grids; 400 each) and old-skill tests (harm_sums4, harm_grids5; 300 each;
rep_sums6, rep_sums8, rep_sums10, rep_grids6; 200 each).

| mark | what | pass |
|---|---|---|
| M0 the problem shows up again (validity, not a result) | L - S on day_grids | <= -40 on at least 3 of 4 seeds. If not, the run is VOID: the long-night grid loss did not reproduce, and B is not judged. |
| M1 the gentle long night keeps the grid gain | B - L on day_grids, and B against S | B - L >= +40 on at least 3 of 4 seeds, AND B >= S - 30 on at least 3 of 4 seeds, AND the 4-seed mean of B >= the 4-seed mean of S - 30. |
| M2 sums keep up | B against S on day_sums | B >= S - 20 on at least 3 of 4 seeds. |
| M3 no harm (slp-358n3's own limit) | B on harm_sums4 and harm_grids5 | B >= N - 6 on every seed, each test. |
| M3b retention (slp-358n3's own limit) | "lost" = harm items the arm's earlier net got right and the morning gets wrong, after each night | B lost <= 15 of 300, every seed, every night, each harm test. |
| M3c old skills that are not at the ceiling | B on rep_sums6, rep_sums8, rep_sums10, rep_grids6 | B >= N - 15 of 200 on every seed, each test. |
| INTEGRITY | the JSON flags `plan_identical_L_B` (B and L drew exactly the same batches) and the recorded learning rates | plan_identical_L_B true on every seed; recorded lr of B = 1.5e-6, of L and S = 3e-5. If not, the run is VOID. |

A seed counts only if all four arms finished all 3 nights on it. If fewer than 3 seeds finish, the run is VOID (a
dead seed is reported, never replaced). When 3 seeds finish, "at least 3 of 4" means 3 of 3; when 4 finish, 3 of 4.

**PASS (rescue) = M0 valid, and M1, M2, M3, M3b, M3c and INTEGRITY all met.**
It is registered as one thing only: with the same steps and the same mix, a much smaller learning rate keeps the grid gain
and does no harm. It is not a claim that longer is better than short (that is report only, below).

**Proved wrong** ("the grid loss in long nights comes from the learning rate being too high for that many steps"): with M0
valid and INTEGRITY met, B - L <= +15 on day_grids on at least 3 of 4 seeds. Then a smaller learning rate does not rescue
the grids, and the replay-mix / repeat-count explanations are what remain (next test in DESIGN.md section 6).
If B also sits at N level on grids (B - N <= +20 on 3 of 4 seeds), say plainly that a too-small learning rate could also
explain the miss (the night may simply not have learned), which this test cannot separate.

**Partial** (neither PASS nor proved wrong): reported as the numbers say, no verdict word beyond "partial".

## Report only (decides nothing)
- Every test, every arm, every seed, after nights 1, 2 and 3, with the count out of N; 4-seed means and the range.
- B - S on day_sums, day_grids, rep_sums10, rep_grids6 (does length itself add anything once it is safe?).
- L - N and B - N on day_grids; S - N on day_grids.
- mean stop round and fixed-8 / fixed-48 scores per arm on day_grids and day_sums (slp-358n3 saw L slower than N at 8
  forced rounds: -49 and -46).
- day tries (the morning's model on that day's 300 fresh puzzles, before its night) for every arm.
- how far S, L and N match the earlier slp-358n3 numbers on seeds 13 and 14 (the card differs, so exact equality is not expected).
- torch.__version__, GPU name and minutes in every summary; excluded day items.

## What this does not license
- Nothing about product nights: the answers here are code-made. Nothing about chat puzzles, other kinds of problems, or
  more than 3 nights. Nothing about stopping mid-night (RESUME and ip-1 are separate sealed tests).
- A PASS says one gentler long night is safe and keeps the grid gain on these tests. It does not say the brain does it
  that way, and it does not choose the night length for the product.

## Predictions (before any run)
- M0 valid: 75%.
- M1 met (given M0 valid): 40%.
- PASS overall: 25%.
- Proved wrong (given M0 valid): 35%.

## Blind recount
A separate step, given only this file and the raw per-seed JSONs, recounts every mark before RESULTS.md is written.
