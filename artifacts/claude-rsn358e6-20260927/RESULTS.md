# rsn-358e6 results: the frozen-expert net with shared attention and norms training (sleep research thread, 2026-09-27 07:46:34 UTC)

## Verdict: PASS (graded against rsn-358e4's eq-replayall, same seeds 3-8)
- **REPRO holds on all 6 seeds.** Every after-A dev score (right, r16 and any, all 5 tests) equals 358e4 eq-replayall's. All runs used torch 2.14.0+cu130 on this same container (hostname vm in both run notes).
- **N = sums4 after B + maze7 after C (of 400): mean 298.00 vs 79.67, a gap of +218.33** (bar +50). Higher on 6 of 6 seeds.
- Proved wrong does not fire (0 of 6 seeds within +10).
- **What the PASS shows (sealed line 1):** a larger trainable share (882,640, 53%, vs 352,944, 21%) lets the frozen-expert net learn new kinds. It does not separate "attention trains" from "more weights train".

Counted from runs/eq-replayall-shared-s{3..8}/result.json against ../claude-rsn358e4-20260927/runs/. A blind recount by a separate agent, from the raw files and the marks only (run/blind-recount.py, run/blind-recount-output.txt), agrees on every number here. The seal checked 12 of 12 OK.

## Per seed (dev /200, own stop)

| seed | shared sums4 B | shared maze7 C | N shared | N eq | shared grids5 A / B / C | T shared / eq / dense |
|---|---|---|---|---|---|---|
| 3 | 200 | 107 | 307 | 82 | 180 / 167 / 47 | 346 / 261 / 489 |
| 4 | 197 | 84 | 281 | 0 | 159 / 134 / 83 | 342 / 148 / 417 |
| 5 | 198 | 103 | 301 | 95 | 163 / 129 / 38 | 316 / 238 / 525 |
| 6 | 200 | 100 | 300 | 113 | 173 / 140 / 27 | 309 / 285 / 393 |
| 7 | 200 | 112 | 312 | 80 | 179 / 153 / 28 | 323 / 243 / 489 |
| 8 | 200 | 87 | 287 | 108 | 167 / 107 / 31 | 291 / 264 / 508 |
| mean | 199.17 | 98.83 | 298.00 | 79.67 | 170.17 / 138.33 / 42.33 | 321.17 / 239.83 / 470.17 |

## Report only (not graded)
- **Against dense, still behind.** Mean T is 321.17 vs dense 470.17 (-149.00), lower on 6 of 6. 358e4's PASS bar (+40, 5 of 6) is not met.
- **Old grids collapse.** grids5 after C is 42.33, against 164.33 for eq-replayall and 128.00 for dense, and it is below both on 6 of 6. grids6 after C falls the same way (4-44 vs eq 88-110). The frozen grids experts no longer work once the shared attention under them has moved, even with 1 grids batch in 20 replayed in phase C.
- **Mazes:** 84-112, against dense 119-171 and eq 0-11.
- **Routing:** tested on 6 of 6 seeds (new group 51-65% of sums cells after B, 28-50% of maze cells after C). eq-replayall managed 3 of 6.
- trainable_next_phase is 882,640 after A and after B on every seed. Replay counts are as sealed.
- **Predictions:** PASS 60% came true; proved wrong 15% did not happen. "Grids kept below eq but above dense" (50%) was wrong: it came out below both.

## What 358e4 and 358e6 show together (suggested; small nets, dev sets)
| layout (same total size, same replay) | learns new kinds | keeps the first kind | T of 600 |
|---|---|---|---|
| dense loop | yes (sums 200, mazes 150) | partly (grids5 128) | 470 |
| experts, everything old frozen (358e4) | barely (sums 76, mazes 3) | best (grids5 164) | 240 |
| experts, shared layers train (358e6) | mostly (sums 199, mazes 99) | worst (grids5 42) | 321 |

Neither freeze-and-grow layout beats the plain dense loop with replay. Freezing everything keeps the old skill but starves new learning. Letting the shared layers learn fixes new learning but breaks the frozen experts, because they rely on attention that has changed. rsn-358e5 (warm routing on the fully frozen layout) is still running and is graded against 358e4 only.

## Plain words
We let the shared parts of the locked-away network keep learning. Now it learns new puzzles almost as well as a normal network, but it forgets the first puzzle type worse than a normal network does. The locked-away parts stop working when the parts around them change. So far the plain network that practises old skills in its sleep is the best of the three designs.
