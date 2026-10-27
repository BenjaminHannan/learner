# brd-6 verification (creative thread, 2026-09-26 ~03:50 UTC)

Source: origin/builder-outbox artifacts/claude-brd6-20260926/ (RESULTS-gpu.md, gpu/), copied unchanged to main.
Run: rental 52683960 (RTX 5090), rc=0, ~$0.27 of the $1.00 cap, unmodified origin/main code, panel md5 checked.

## Registered verdict: PROVED WRONG (confirmed)

Recounted from gpu/streams.json with claude_blurt5s.summarize and boot_ci, not copied from the summary.
- W8 − W4 cov@30 per seed: −1 / +1 / −13 (the PASS bar was +12 in every seed). 95% interval [−5.72, +2.09] points;
  the upper bound is below +2.5, so the proved-wrong clause fires.
- Inconclusive clause: not triggered. W8 had 398 examples (≥ 300); the lower bound of W4 − base is +15.8 (> 0).
- So at equal exposure, doubling the different won puzzles (about 200 to about 400) did NOT widen coverage.

## Counts

| Arm | First try (cov@1) | Within 30 (cov@30) | 3-number (of 160) | 4-number (of 80) | Lucky |
|---|---|---|---|---|---|
| base | 11 | 108 | 95 | 13 | 231 |
| W4, 400 practice (199 examples, 3 passes each) | 18 / 20 / 15 | 162 / 159 / 160 | 130 / 128 / 129 | 32 / 31 / 31 | 499 / 531 / 498 |
| W8, 800 practice (398 examples, 1-2 passes each) | 18 / 20 / 17 | 161 / 160 / 147 | 124 / 135 / 123 | 37 / 25 / 24 | 536 / 521 / 508 |

## Arm matching (checked from gpu/practice.jsonl)
Every saved answer passes the exact checker. The arms had 597 passes each and 75 optimizer steps each.
Both halves of the practice set happen to give 199 examples, 1,540 answer characters and 171 three-number puzzles. I checked this is a coincidence and not a copy: all 800 puzzles are distinct, the own/win split differs (20/179 vs 13/186), and no answer string is shared. So W4 and W8 have the same mean answer length (7.74) and the same three-number share (0.859).

## What this shows (description only)
- Shown: sleep on own checked hits (W4) solved 51-54 more of 240 fresh puzzles than the untrained model in 30 tries
  (interval +15.8 to +27.9 points), including 18-19 more 4-number puzzles. This is a much larger gain than brd-5's +13
  to +22 on a different panel; it was a reported number here, not a mark.
- With brd-5: too FEW distinct puzzles (20 repeated) collapses coverage, but past about 200 more distinct puzzles at
  the same exposure add nothing. Breadth is a floor, not a dial.
