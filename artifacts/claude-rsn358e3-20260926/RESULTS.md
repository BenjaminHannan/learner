# rsn-358e3 results: a small grids replay in phase B (sleep research thread, 2026-09-27 00:24 UTC)

## Verdict: FAIL, not proved wrong (moe-grow-replay, the one graded arm)
The pre-fixed split reading applies: **"replay keeps the old skill; the frozen net's capacity, not replay, is the sums problem".**
- grids5 after B was 191 / 188, against a bar of 150 on both seeds: met.
- sums4 after B was 136 / 67, against a bar of 120 on both seeds: missed on seed 2.
- **The FAIL stands.** Not same-size: this arm is 1.64x dense's weights in phase B, as moe-grow was.

Counted from runs/{moe-grow-replay,dense-replay}-s{1,2}/result.json. A blind recount by a separate agent, from the raw files and PASSMARKS.md only, agrees on every number below. Run note: run/RUN-NOTE.md.

## Marks (dev, right of 200, the net's own stop), seed 1 / seed 2

| | moe-grow (358e, no replay) | **moe-grow-replay (graded)** | dense-replay (report only) |
|---|---|---|---|
| grids5 after A (V >= 120) | 187 / 188 | **187 / 188** (met, identical to moe-grow as expected) | 199 / 198 |
| grids5 after B (>= 150) | 40 / 70 | **191 / 188** (met) | 184 / 172 |
| F = after A - after B | 147 / 118 | **-4 / 0** | 15 / 26 |
| sums4 after B (>= 120) | 139 / 124 | **136 / 67** (seed 2 missed) | 200 / 200 |
| sums6 after B | 83 / 68 | 94 / 32 | 194 / 196 |
| maze7 after C | 3 / 3 | 9 / 0 | 150 / 136 |
| grids5 after C | 32 / 47 | 185 / 160 | 0 / 0 |
| trainable weights in B | 1,054,728 | 1,054,728 | 1,646,750 |

- replayed_batches = 250 in every run, as sealed.
- Proved wrong needs grids5 after B <= 100 on both seeds. It does not fire.
- The "weights" field in moe-grow-replay's result.json reads 1,650,342, the count before growing (as in 358e).
- S after B for moe-grow-replay (report only) is 0.913, 0.437 / 0.583, 0.636. As in 358e, these shares were read after the second grow step.

## What it shows
- **Shown:** with 1 grids step in 10 during phase B, the grown router keeps sending grids to the old experts. grids5 is fully kept (191 / 188), against 40 / 70 without replay. That confirms the diagnostic's reading: the router forgot because it saw no grids.
- **Shown:** the frozen net still learns sums poorly (136 / 67) and mazes not at all (9 / 0) with only its new third of weights free. That is why it fails.
- **Report only, and not a graded claim:** the plain dense loop with the same replay kept most of grids (184 / 172, F 15 / 26) AND learned sums fully (200 / 200) and mazes (150 / 136). On these two seeds, replay alone does most of the work, and the frozen experts add a smaller forgetting number at a large cost in new learning. The sealed marks allow no experts-vs-dense claim from this test, so this is suggested only.
- Also report only: with no replay in phase C, every net loses whatever phase C does not practise. dense-replay drops grids5 to 0 after mazes. moe-grow-replay keeps grids5 at 185 / 160 through phase C, because its grids experts stay frozen and still get routed to.
- moe-grow-eq and moe-grow-eq-replay (report only) started at 00:21 UTC; their rows are added when they finish.

## Plain words
Freezing the old experts plus a little practice of the old skill keeps the old skill perfectly. But the frozen net then learns new things badly. A normal net given the same little practice keeps almost as much of the old skill and learns the new things fully. For the brain comparison (a guess): replay, the sleep-like part, is doing the protecting here, not the separate experts.
