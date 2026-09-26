# slp-358lp results: registered FAIL; picking night practice by learning progress did no better than random

Verdict: **FAIL** (V met on both seeds; P1, P2 and P3 fail on both seeds; P4 passes). Proved wrong: **not triggered**
(seed 7 meets it, +5 and −2, but seed 8's sums8 gap is +13). The flipped control (pick the WORST score) did as well
as the learning-progress pick.
Code: scripts/claude_slp358lp_nights.py, sealed at f20fd114f before any run (SEAL-code.sha256.txt, all OK at
launch). Seeds 7 and 8, CPU, 2 threads each: 40.0 and 39.0 minutes. excluded_day_items_in_tests = 0 on both.

## After night 3 (S random / L learning progress / F flipped / N no night)
| test | seed | S | L | F | N |
|---|---|---|---|---|---|
| transfer_sums8 (200, P1) | 7 | 97 | 102 | 100 | 12 |
| | 8 | 132 | 145 | 146 | 71 |
| transfer_grids6 (200, P2) | 7 | 18 | 16 | 19 | 9 |
| | 8 | 65 | 69 | 64 | 16 |
| harm_sums4 (300, P4) | 7 | 291 | 290 | 291 | 231 |
| | 8 | 300 | 300 | 300 | 278 |
| harm_grids4 (300, P4) | 7 | 148 | 154 | 154 | 140 |
| | 8 | 199 | 198 | 200 | 173 |
| day_sums (400, report) | 7 | 342 | 346 | 348 | 163 |
| | 8 | 386 | 393 | 381 | 318 |
| day_grids (400, V and report) | 7 | 82 | 87 | 81 | 61 |
| | 8 | 194 | 198 | 199 | 101 |

## Marks
| mark | seed 7 | seed 8 |
|---|---|---|
| V S − N day_grids ≥ +20 | +21 met | +93 met |
| P1 sums8 L − S ≥ +20 | +5 FAIL | +13 FAIL |
| P2 grids6 L − S ≥ +20 | −2 FAIL | +4 FAIL |
| P3 L − F ≥ +10 on sums8 / grids6 | +2 / −3 FAIL | −1 / +5 FAIL |
| P4 L ≥ N − 6 harm sums4 / grids4 | 290 ≥ 225 / 154 ≥ 134 PASS | 300 ≥ 272 / 198 ≥ 167 PASS |
| proved wrong (L − S ≤ +5 on both, both seeds) | yes (+5, −2) | no (+13) |

## Report-only
- Candidate picks were spread almost evenly over the 4 candidates in both L and F (e.g. seed 8 L night 1: 30/37/45/29).
- Nights 1-2 show the same picture: L, F and S within a few counts of each other on every test.
- Sleep itself worked again: every night arm beats N on the day kinds and the bigger sizes.

## What it means (plain words)
Choosing which of 4 random batches of the day's checked puzzles to practise, by "does this push the weights the way
they were already moving", made no measurable difference: the flipped choice (the least aligned batch) did just as
well. At this scale the night's gain comes from practising the day's checked puzzles at all, not from picking among
similar batches. Limits: small nets on CPU, 3 nights, a pick among only 4 random batches (the paper trained a writer
to make new items), two puzzle kinds.
