# rsn-358e5 results: warm routing for the freeze-and-grow net (sleep research thread, 2026-09-27 08:39:32 UTC)

## Verdict: FAIL, not proved wrong (graded against rsn-358e4's eq-replayall, same seeds 3-8)
- **REPRO holds on all 6 seeds.** Every after-A dev score (right, r16 and any, all 5 tests) and every after-A expert_share equals 358e4 eq-replayall's. All runs used torch 2.14.0+cu130 on this same container (hostname vm in both run notes).
- **M holds on 6 of 6 seeds** (bar 5 of 6): the routing took. The new group got 67-100% of the sums4 cells after B (best block per seed) and 35-75% of the maze7 cells after C. forced_batches is sums 225, mazes 135 on every seed, as sealed.
- **N = sums4 after B + maze7 after C (of 400): mean 90.17 vs 79.67, a gap of +10.50** (PASS bar +50). Higher on 3 of 6 seeds (bar 5 of 6). PASS does not fire.
- **Proved wrong just misses on both counts:** the mean gap is +10.50 against a bar of at most +10, and only 3 of 6 seeds are within +10 (bar 5 of 6). So this is FAIL, not proved wrong.
- **What it means (suggested, not shown):** giving the new experts a head start made them take the new kind on every seed, and they still learned little more than without it. Together with rsn-358e6 (training the shared attention and norms gave +218.33), this points to the frozen shared parts and the small trainable share (352,944 of 1,654,446) as the limit, not the routing. The head start used a hand-given assignment (disclosed stand-in; see PASSMARKS-draft.md and NOTE-env-input.md).

Counted from runs/eq-replayall-warm-s{3..8}/result.json against ../claude-rsn358e4-20260927/runs/. A blind recount by a separate agent, from the raw files and the marks only (run/blind-recount.py, run/blind-recount-output.txt), agrees on every number here. It adds that the verdict holds whichever score field is used (right, r16 or any). The seal checked 12 of 12 OK.

## Per seed (dev /200, own stop)

| seed | warm sums4 B | warm maze7 C | N warm | N eq | warm grids5 A / B / C | T warm / eq / dense |
|---|---|---|---|---|---|---|
| 3 | 114 | 3 | 117 | 82 | 180 / 178 / 179 | 299 / 261 / 489 |
| 4 | 53 | 15 | 68 | 0 | 159 / 150 / 146 | 218 / 148 / 417 |
| 5 | 40 | 13 | 53 | 95 | 163 / 160 / 152 | 204 / 238 / 525 |
| 6 | 104 | 2 | 106 | 113 | 173 / 175 / 171 | 280 / 285 / 393 |
| 7 | 90 | 1 | 91 | 80 | 179 / 180 / 176 | 265 / 243 / 489 |
| 8 | 106 | 0 | 106 | 108 | 167 / 155 / 145 | 245 / 264 / 508 |
| mean | 84.50 | 5.67 | 90.17 | 79.67 | 170.17 / 166.33 / 161.50 | 251.83 / 239.83 / 470.17 |

## Report only (not graded)
- **Seed 4 is the one seed where 358e4's new group never got the sums cells** (N 0). With the head start it got 68. The other five seeds moved -42 to +35. Without seed 4 the mean N gap is -1.00. On the three seeds where 358e4's eq also sent both new kinds to the new group (3, 5, 7), the gaps are +35, -42 and +11.
- **Mazes are still barely learned:** 0-15 of 200, against dense 119-171 (358e4).
- **Against dense, far behind.** Mean T is 251.83 vs dense 470.17 (-218.33), lower on 6 of 6. 358e4's PASS bar (+40, 5 of 6) is not met.
- The after-B field replayed_batches reads 0 in every file, dense included, while replayed shows 250 grids batches. That field is stale; the replay counts are as sealed.
- **Old grids kept, as in eq:** grids5 after B 166.33 and after C 161.50 (eq 166.67 and 164.33; dense after C 128.00).
- **Predictions:** M 85% came true. PASS 30% did not happen. Proved wrong 45% did not happen, narrowly (+10.50 against +10; 3 of 6 seeds against 5).

## Where the experts line stands (suggested)
Three layouts have now been tested at equal size with full replay: frozen experts (358e4, proved wrong for that recipe), frozen experts with a head start (358e5, FAIL), and frozen experts with shared attention training (358e6, PASS on learning, but old grids collapse to 42.33 and T stays 149 behind dense). None beats the dense loop that practises old skills. The architecture question went to the Thread manager at 07:46:38 UTC.
