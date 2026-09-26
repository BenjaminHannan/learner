# rsn-358y DRAFT: a deeper, thinner loop at equal weights (sleep research thread, 2026-09-26 16:40 UTC)

DRAFT, not sealed. It is written before any 358t result. It is sealed only after 358t's verdict, and only in the form the branch table below picks. No code exists yet.

**Where the idea came from:** Ben, 16:36-16:37 UTC, relayed by the Thread manager:
- cmsg_01FuvegZXjMmeUzStiEFVnEWNtzRiE1zKJKLfCAo3kmdac: stack many more layers, like GPT-3's 96.
- cmsg_01FuvegZXjMmeUzStiEFVnEWTNGL6YZGxdRP7fhx89HggA: "we can make the layers narrower then".

**Question:** at the same number of weights, does a looped stack that is deeper and narrower solve bigger puzzles better than its plain same-size twin, and better than the looped arm it grows from?

**Brain angle** (a guess, textbook level): cortex is a deep stack of many thin processing stages rather than a few wide ones, and thinking re-uses the same stack over and over. loop8 already tests "re-use the whole stack". 358y tests "more, thinner stages per pass".

## The one change
Depth and width only, at equal weights. The schedule, stop rule, data, steps, seeds and tests all come from the base arm.

| arm | shape | weights (counted from R.Net with 358t's patches) |
|---|---|---|
| plain (358i) | 8 x 256, 8 heads | 6,385,149 |
| loop8 (358t) | 8 x 256, 8 heads | 6,385,918 |
| loop (358i) / loop-trm | 2 x 512, 8 heads | 6,438,302 |
| **loop32 (new)** | **32 x 128, 8 heads of 16** | **6,382,718** (0.04% under plain) |

Compute per round is the same as loop8. The matrix work per layer scales with width squared (32 x 128² = 8 x 256²). Attention is about 2x loop8's. Activation memory is about 2x.

**Why 32 x 128 and not 16 layers:**
- It matches the weight count almost exactly. The nearest 16-layer shape is 16 x 180 with 6 heads, at 6,306,894 weights (1.2% under).
- It is the strongest form of the idea, so a FAIL says more.
- 16 x 180 is the sealed fallback (below).

## Branch table, fixed now; the shape is chosen by 358t's verdict

| 358t outcome | 358y base | graded change |
|---|---|---|
| loop8 PASS (with or without loop-trm) | loop8, or loop8-trm if it beats loop8 on the G1 mean | 8 x 256 -> 32 x 128, same schedule |
| only loop-trm PASS | loop-trm (2 x 512) | 2 x 512 -> 32 x 128 with the TRM schedule. This is still one change against the base: shape only. |
| both FAIL | none. 358y is shelved. | The next design is two states (EXIT-RULE-ADDENDUM-1). |

**If loop8 fails, does deeper-thinner still make sense?** Only if loop8 fails because of grids while at 1 round it matches plain (a G4 row). That would mean the depth works and looping is the problem, and going deeper does not fix looping. If loop8 is behind even at 1 round, a thinner state is the likely cause, and 32 x 128 makes the state thinner still. So a loop8 FAIL shelves 358y either way.

A lone 358t pass must first replicate on seeds 5-8. 358y waits for that replication, so it never builds on an unreplicated pass.

## Marks (same as 358t PASSMARKS-v2, applied to loop32)
- G0: validity.
- G1: bigger, with mean >= +30 on 2 of sums6 / grids6 / numbers5, >= -10 on the third, and 3 of 4 seeds.
- G2: practised, >= -10.
- G3: stop.

All four are measured against 358i's plain on 358i's sealed tests.

**Added mark G6, vs its base:** the loop32 4-seed mean >= base mean + 10 on at least 2 of the 3 bigger tests, and never below base - 10.

**PASS = G0-G3 and G6.**
- G0-G3 without G6: "deeper-thinner works, but no better than the base". Reported, and the base is kept because it is cheaper to run.

**Proved wrong:** G0 met, and the loop32 mean is at or below the base mean on all three bigger tests.

**FAIL fallback, sealed with this test:** 16 x 180, 6 heads. It runs only if loop32 fails G0 because it trains too slowly: a training curve still rising at step 60,000 on a practised kind. If loop32 fails with a flat curve, 358y stops there.

**Prediction:** PASS 20%. The main risk, carried over from 358t's written risk, is that a 128-wide state carries less per cell and trains more slowly. Also, 32 sequential layers per round times up to 6 rounds of gradient is a deep path, 192 layers.

## Cost (estimate)
- 4 seeds of one arm on one RTX 5090.
- Weight-matrix FLOPs per round match loop8, so each run should take about loop8's time plus the extra attention.
- 358i's 8 runs cost about $0.94.
- Estimate: $0.60-0.90. Proposed cap: $1.00.
- The exact figure is fixed from 358t's measured loop8 minutes per run before sealing.
- This is beyond the sleep research thread's $2, so it goes to the Thread manager for Ben's yes before anything is queued.
