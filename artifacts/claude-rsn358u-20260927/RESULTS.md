# rsn-358u results (sleep research thread, 2026-09-27T18:14:33Z)

**Verdict: PASS** (V0, V1, G0, G1, G2 and G3 all met). The loop reasoner keeps its lead over its same-size plain twin when neither net is told the puzzle kind.

Run: one vast RTX 5090 (torch 2.11.0+cu128), all 8 runs at once, seeds 13-16, sealed code unchanged. Results are copied from builder-outbox (rent358u-3-collect, afaeb0402). Every tests.json, poison.json, train log and summary matches the rental's sha256 manifest (32 of 32), and SEAL-run matches the manifest for all 8 checkpoints. Only the Mac copies of the checkpoints failed (see Weights).

## Marks
| mark | result |
|---|---|
| V0 | steps_block_nograd = 0 in all 4 loop runs: met |
| V1 poison | predictions identical with the kind field swapped, all 3 kinds, all 8 checkpoints: met |
| G0 | sums4 300 and grids5 300 on all 8 runs (numbers4 0-3, as in 358i3), so 2 of 3 kinds reach at least 210: met |
| G1 | mean loop − plain: sums6 +144.50, grids6 +41.50, numbers5 +0.25. The loop is ahead on sums6 and grids6 on 4 of 4 seeds: met |
| G2 | practised gaps: sums4 +0.00, grids5 +0.00, numbers4 −0.50: met |
| G3 | own stop ≥ fixed-16 − 5 on every bigger test on 4 of 4 seeds; mean rounds on sums6 (7.99-8.28) > on sums4 (6.80-7.23) on every seed: met |

Per seed (loop / plain, of 300, s13-s16):
- sums6: 300/130, 299/131, 298/153, 296/201.
- grids6: 295/245, 294/252, 288/245, 287/256.

## Report only
- Bigger sizes, mean loop − plain: sums8 +220.25, sums10 +210.75, sums12 +178.00, grids7 +36.75 (loop ahead on grids7 on 3 of 4 seeds; s16 −9).
- Loop means: sums8 274.25, sums10 238.00, grids7 184.00.
- Against 358i3 (kind told, seeds 5-8, BensPC): loop sums6 298.25 vs 295.00, grids6 291.00 vs 292.25; gaps sums6 +144.50 vs +124.00, grids6 +41.50 vs +52.00. This comparison is suggested only: the seeds and the machine differ (vast 5090, all 8 at once, vs BensPC, 2-3 at a time).
- Minutes: about 90 per loop run, about 100 per plain run, all 8 at once. Rentals: $1.25 by the guard's count, including 2 hosts that failed to start.

## Weights: not yet on the Mac
The guard's copy-back failed at 77 of 78 files: loop-s13/final.pt was truncated by a broken pipe. So instance 52964920 was STOPPED, not destroyed, and no Mac copy of any final.pt matches SEAL-run. The sealed sha256s are in SEAL-run.sha256.txt. A held re-copy job (rent358u-4-recopy) starts the instance, copies all 8 with a sha check, and destroys it only after a verified copy.

## What it means (plain words)
Earlier tests told the reasoner which kind of puzzle it was looking at. Here it had to work that out from the puzzle itself, and it still beat the same-size plain net by the same kind of margin. On 6-digit sums it got about 298 of 300 against about 154. On 6x6 grids it got about 291 against about 250. Limits:
- These are small nets on code-made puzzles.
- Neither net learns number puzzles.
- The 358i3 comparison crosses seeds and machines.
