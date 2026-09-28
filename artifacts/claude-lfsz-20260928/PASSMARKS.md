# lf-sz pass marks: is it depth, or just size, that keeps old skills through a new kind? (fixed before any run)

Written 2026-09-28 by the "lf-sz" Director helper thread, for the Director. Serves finish-line item 7 (scaling) and item 5.
lf-8 (artifacts/claude-lf8-20260927/RESULTS.md) passed: the 8-layer loop kept old grids through mazes (grids5 after C 181 and
177 of 200) far better than the 2-layer loop (120 and 61), but it has 3.9x the weights (6,386,174 vs 1,646,750). This test
gives the shallower loops the same weights. Keeps to the small card experiments only; nothing here touches the village model.

## Code (scripts/claude_lfsz_run.py, new file; 358e4's dense-replayall arm and its imports are unchanged)
ONE change: the SHAPE of the loop net at (nearly) the same total weights. Heads stay 8. Everything else is lf-8's recipe:
code-made data in three phases A grids, B sums, C mazes; steps 2,500 / 2,500 / 1,500; batch 64; every earlier kind replayed
(every 10th step); the loop schedule; the dev sets (seed 48000, 200 items each); scoring (the net's own stop, 48 rounds).

| arm | width d | loop layers | weights | vs loop8 |
|---|---|---|---|---|
| loop8 | 256 | 8 | 6,386,174 | (lf-8's loop8 run again, same box as the others) |
| loop2w | 512 | 2 | 6,438,814 | +0.8% |
| loop4w | 360 | 4 | 6,334,182 | -0.8% |

The weight counts come from a formula that reproduces lf-8's two known counts exactly (1,646,750 and 6,386,174); it was NOT
run here (this box has no torch). The run's selftest on the GPU box asserts the three counts and the 2% limit before any run
starts, and each result.json records its own weights. If the assert fails, nothing runs and the numbers here are wrong.
Seeds are 9 and 10 (the ones lf-8 used), each arm on both seeds, so runs pair by seed. 6 runs in all.

## Scores and reading
Dev items right out of 200. Per run: G = grids5 after C (keeping the first skill), S = sums4 after C, M = maze7 after C,
T = G + S + M (out of 600, as in lf-8). Forgetting = grids5 after A minus G; sums4 after B minus S (report only).
- **V** (validity, as in lf-8): in every run, grids5 after A >= 120 and sums4 after B >= 120. If any loop8 run fails V, every reading is
  INCONCLUSIVE; if only a wide arm fails V, that arm's reading is INCONCLUSIVE.
- **Comparator B** = whichever of loop2w and loop4w has the higher mean T over the two seeds (tie: higher mean G). loop8 must beat the
  better same-size shallow loop, not the worse one.
- Gaps, per seed s: dT_s = T(loop8) - T(B), dG_s = G(loop8) - G(B). Both use the loop8 run from THIS job, not lf-8's numbers.
- **DEPTH ADDS** (read as "suggested, worth a bigger test", never "shown", because 2 seeds): mean dT >= +105 AND mean dG >= +80 AND
  dT_s > 0 and dG_s > 0 on both seeds.
- **SIZE EXPLAINS** (the depth-only story is rejected at this scale): on BOTH seeds dT_s <= +50 AND dG_s <= +40. (Every seed must be
  clearly below; one seed above is not enough to reject.)
- **NOT SHOWN**: anything else (some depth effect may be there; 2 seeds cannot tell).
- Report only, no mark: each of loop2w and loop4w against B separately; loop4w vs loop2w (does depth help within the shallow
  range?); each wide arm vs lf-8's narrow loop2 (T 468 / 374, G 120 / 61: does size alone help?); S and M and the forgetting rows;
  weights, minutes per run, replay counts.
- **R** (rerun agrees, report only): loop8 T here within 53 of lf-8's on each seed (559 for s9, 561 for s10). If it is not, say
  "the box differs"; the comparator is still this job's loop8, and lf-8's numbers are never swapped in.

## Marks self-check (Ben's H8 list, 21:37 UTC 09-28)
1. **Bars above noise.** Noise is 358e4's six dense-replayall seeds (s3-s8, artifacts/claude-rsn358e4-20260927/runs/*/result.json,
   read again for this file): T = 489, 417, 525, 393, 489, 508, mean 470.2, sd 52.8; G = 139, 103, 172, 60, 151, 143, mean 128.0,
   sd 40.1. The gap between two 2-seed means has standard error about one seed-sd (53 for T, 40 for G), so the DEPTH ADDS bars are
   2 x that: +105 and +80. (lf-8's own gaps were T +139 and G +88.5; the bars come from the noise, not from that result.)
2. **"Every seed" reading.** SIZE EXPLAINS needs both seeds clearly below (+50 and +40, about one seed-sd); the middle is NOT SHOWN.
   DEPTH ADDS is worded "suggested". No "proved wrong" is claimed from one seed.
3. **Fair comparator.** The higher of the two same-size shallow loops (B), and loop8 is rerun on the same box, not borrowed from lf-8.
4. **Plain-net proof row: NOT BUILT, gap stated.** Every arm here is a loop; a plain same-size net is a different training path and
   this box cannot test new torch code. What stands in for it: every run's "start" (untrained) score must be 0 on all five dev sets
   (a net that has learned nothing cannot pass), the dev items are code-made from seed 48000 while training data comes from other seeds
   (scripts/claude_rsn358e_moe.py:110 dev_sets vs run's rng 5800+seed, inspected, not re-run here), and maze7 (M) is scored on a kind
   the net first sees in phase C. No mark depends on a plain net. Untested: whether a plain same-size net scores like these loops.
5. **F_few (k=1..64) and F_eq: not applicable.** This test makes no few-example claim and its exam (lf-8's) has no few-example
   score, so no mark reads one; nothing here may be quoted as a few-example result.
6. **Sleep gates: not applicable.** No sleep phase in this test.

## Prediction (a guess before any run)
DEPTH ADDS 30%, SIZE EXPLAINS 25%, NOT SHOWN 45%. Reason: lf-8's gap is large (+139 T), but part of it likely comes from 3.9x the
weights, and the wide 2-layer net has more room per round while the 8-layer net has more steps of composition per round.

## What each outcome means
- **DEPTH ADDS:** depth helps beyond size at ~6.4M weights, on 2 seeds. The forgetting tests should move to the 8-layer loop and a
  bigger-seed test comes next. Supports finish-line item 7 (scaling with depth rather than width).
- **SIZE EXPLAINS:** weights, not depth, kept the old skill; the cheapest way to scale is the widest net that fits, and lf-8's
  headline needs re-reading as a size result.
- **NOT SHOWN:** run more seeds (3 to 6 per arm) before deciding; each extra seed costs about the same as this job's per-run price.

## Compute
6 runs at once on one vast card, torch 2.11.0+cu128 as lf-8. Price in RUN-PLAN.md.
