# brd-5 verification (creative thread, 2026-09-26 ~02:50 UTC)

Source: origin/builder-outbox artifacts/claude-brd5-20260926/ (RESULTS-gpu.md, gpu/), copied unchanged to main.
Run: rental 52678258 (RTX 5090), rc=0, ~$0.23 of the $1.00 cap, unmodified origin/main code, panel md5 checked.

## Registered verdict: INCONCLUSIVE (confirmed)

Recounted from gpu/streams.json with claude_blurt5s.summarize and boot_ci (same seed), not copied from the summary.
- The inconclusive clause fired: W's cov@30 had to be at least base + 24 = 147 in every seed. It was 144 / 145 / 136.
  The size of the effect being explained did not replicate on this panel (base covers 123 of 240 here, against 77
  of 184 in blurt-5s).
- The PASS sub-conditions were all met numerically: W − N = +53 / +62 / +39 puzzles (bar 24 in each seed), 95%
  interval [+16.5, +26.2] points. Because the inconclusive clause fired, this is NOT a pass.
- Proved wrong: not triggered (the upper bound of W − N is 26.2, not below 5).

## The four numbers (addendum), from streams.json

| Arm | First try (cov@1) | Within 30 (cov@30) = distinct puzzles | 3-number (of 160) | 4-number (of 80) | Lucky samples |
|---|---|---|---|---|---|
| base | 11 | 123 | 106 | 17 | 263 |
| W, one hit per won puzzle (187 distinct) | 15 / 14 / 17 | 144 / 145 / 136 | 119 / 118 / 112 | 25 / 27 / 24 | 425 / 521 / 493 |
| N, 20 won puzzles repeated (40 distinct) | 20 / 20 / 13 | 91 / 83 / 97 | 76 / 65 / 82 | 15 / 18 / 15 | 518 / 518 / 518 |
| C, known answers repeated (20 distinct) | 11 / 12 / 9 | 22 / 22 / 18 | 20 / 19 / 14 | 2 / 3 / 4 | 313 / 296 / 284 |

N's lucky total is 518 in all three seeds. I checked: the per-puzzle counts differ on 103 puzzles between seeds 0 and
1, so the equal totals are a coincidence, not a copying error.

## Arm matching (asked by Ben's evaluator; description only)
- Exposure: W and N have exactly 187 examples each (asserted in code), the same epochs and batch size, so the same
  optimizer steps. N's 20 hits average 8.1 characters (no spaces). W's wins were not saved in this run; blurt-5s,
  with the same recipe, had 8.13. So token exposure is close, but the W side is approximate.
- Mix: 17 of N's 20 picks are 3-number puzzles (85%); the practice set is 266/400 (66%). Wins skew to 3-number
  puzzles anyway, but W's own mix wasn't saved, so this comparison is incomplete. N's picks are a seeded random
  draw from W's wins, so they carry the same labels (first lucky hit) and no easier-by-design selection.

## What this shows (description only; changes no verdict)
- Shown: at equal exposure, 20 won puzzles repeated made coverage FALL below the untrained model (N − base
  interval [−20.2, −6.8] points), while lucky samples doubled and piled up on few puzzles (the top 10 puzzles hold
  196-229 of N's 518 hits, against 88-100 of W's). One hit on each of many different won puzzles raised coverage
  (W − base [+2.2, +13.5] points).
- So breadth matters a lot for not collapsing. N sits well above C (83-97 vs 18-22), so newness matters too.
- Not shown: that this sleep adds 24+ puzzles over base; here it added +13 to +22.
- Recipe consequence (unchanged code): claude_dl1_nights.copy_examples (one example per puzzle, no padding) is the
  right shape; never pad a night by repeating a few examples.
