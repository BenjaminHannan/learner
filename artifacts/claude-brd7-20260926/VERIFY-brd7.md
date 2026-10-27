# brd-7 verification (creative thread, 2026-09-26 ~11:35 UTC)

Source: origin/builder-outbox artifacts/claude-brd7-20260926/ (RESULTS-gpu.md, gpu/), copied unchanged to main.
Run: rental (RTX 5090), rc=0, ~$0.24 of the $1.00 cap, code = unmodified origin/main claude_brd5.py. Only one path
ran: rent-brd7. The BensPC fallback and the slim variant were never run.

## Registered verdict: NOT SHOWN (confirmed)

Recounted from gpu/streams.json with claude_blurt5s.summarize and boot_ci, not copied from the summary.
- W ≥ base + 24 in every seed: NOT met. Base 135; W 158 / 158 / 146 = +23 / +23 / +11.
- The 95% interval for W − base is above 0: met, [+2.65, +13.31] points.
- W ≥ C + 24 in every seed: met. C 28 / 33 / 27, so W − C = +130 / +125 / +119.
- Proved wrong: not triggered, because the upper bound of W − base is 13.3, not below 5. Inconclusive: not
  triggered (183 wins, 20 own).
- PASS needs all three conditions, so the verdict is NOT SHOWN, missed by one puzzle in two seeds and by 13 in one.

## Counts

| Arm | First try (cov@1) | Within 30 (cov@30) | 3-number (of 160) | 4-number (of 80) | Lucky |
|---|---|---|---|---|---|
| base | 12 | 135 | 116 | 19 | 330 |
| W, one hit per won puzzle (203) | 18 / 20 / 21 | 158 / 158 / 146 | 127 / 130 / 121 | 31 / 28 / 25 | 590 / 564 / 547 |
| N, 20 won puzzles repeated | 26 / 26 / 23 | 99 / 89 / 96 | 83 / 69 / 76 | 16 / 20 / 20 | 690 / 808 / 686 |
| C, known answers repeated | 21 / 20 / 20 | 28 / 33 / 27 | 25 / 30 / 23 | 3 / 3 / 4 | 633 / 640 / 603 |

Reported intervals: W − C [+46.6, +57.1] points; W − N [+20.0, +29.3] points.

## Across the three runs (description only; no verdict changes)
| Run | Base cov@30 | W − base per seed | W − base 95% interval | W − N per seed |
|---|---|---|---|---|
| brd-5 | 123 | +21 / +22 / +13 | [+2.2, +13.5] | +53 / +62 / +39 |
| brd-6 (W4) | 108 | +54 / +51 / +52 | [+15.8, +27.9] | (no N arm) |
| brd-7 | 135 | +23 / +23 / +11 | [+2.7, +13.3] | +59 / +69 / +50 |
- Shown three times, each with an interval above 0: sleeping on the model's own checked hits (one per won puzzle)
  solves more different fresh puzzles in 30 tries than no sleep.
- Shown twice by the registered W − C / W − N counts: it beats matched-exposure controls by 39 to 130 puzzles.
- Not shown: the pre-set size of +24 over no sleep in every seed. It held in 1 of 3 panels, and the gain is smaller
  on panels where the untrained model already covers more.
- Repeating a few examples (C, N) raises lucky samples and first-try hits but collapses the number of puzzles
  reached; this held in every run.
