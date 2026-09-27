# rsn-358e4 results: equal-size freeze-and-grow vs dense, both replaying every earlier kind (sleep research thread, 2026-09-27 05:49:43 UTC)

## Verdict: PROVED WRONG for this freeze-and-grow recipe
In the words fixed in ADDENDUM-3-wording.md before seeds 5-8 were read:

"Proved wrong for this freeze-and-grow recipe (zero-initialised new router rows, top-1 routing, old rows frozen, 4 narrow new experts per phase): at equal size with full replay it keeps and learns less than the dense loop. 3 of 6 seeds tested the routing. Most seeds never sent the new kind to the new experts, so this says little about separate experts themselves."

- V met: grids5 after A >= 120 in both arms on all 6 seeds (eq 159-180, dense 194-200); dense sums4 after B = 200 on all 6.
- mean T_eq 239.83 vs mean T_dense 470.17: a gap of -230.33 (the proved-wrong bar is -40). T_eq < T_dense on 6 of 6 seeds (bar: 5 of 6).
- PASS fails on every condition: mean L_eq 3.33 (floor 100; addendum 2's floor L_dense - 20 = 130.33).

Counted from runs/{dense,eq}-replayall-s{3..8}/result.json. A blind recount by a separate agent, from the raw files and the marks only, is in run/blind-recount-output.txt (script run/blind-recount.py) and agrees on every number above, including the routing count (seeds 3, 5, 7). Run notes: run/RUN-NOTE.md (CPU, 1 thread per run, torch 2.14.0+cu130, $0).

## Per seed (dev /200, own stop; T = grids5 + sums4 + maze7 after C, of 600; L = maze7 after C)

| seed | dense T | eq T | dense L | eq L | dense grids5 A / after C | eq grids5 A / after C | dense sums4 B | eq sums4 B | routing tested (sums4 B, maze7 C, new group share per block) |
|---|---|---|---|---|---|---|---|---|---|
| 3 | 489 | 261 | 159 | 7 | 194 / 139 | 180 / 181 | 200 | 75 | yes (0.735, 0.787; 1.000, 0.121) |
| 4 | 417 | 148 | 119 | 0 | 194 / 103 | 159 / 148 | 200 | 0 | no (0.000, 0.000; 0.694, 0.694) |
| 5 | 525 | 238 | 169 | 11 | 200 / 172 | 163 / 147 | 200 | 84 | yes (0.736, 0.815; 0.306, 0.000) |
| 6 | 393 | 285 | 138 | 0 | 194 / 60 | 173 / 176 | 200 | 113 | no (0.863, 0.598; 0.000, 0.000) |
| 7 | 489 | 243 | 146 | 2 | 200 / 151 | 179 / 176 | 200 | 78 | yes (0.667, 0.904; 0.959, 0.653) |
| 8 | 508 | 264 | 171 | 0 | 197 / 143 | 167 / 158 | 200 | 108 | no (0.966, 0.755; 0.000, 0.000) |
| mean | 470.17 | 239.83 | 150.33 | 3.33 | 196.50 / 128.00 | 170.17 / 164.33 | 200.00 | 76.33 | 3 of 6 |

- Replay counts as sealed in all 12 runs: 250 grids batches in B; 75 grids + 75 sums in C.
- Weights: dense 1,646,750; eq 1,654,446 (trainable in B and C: 352,944). Minutes: dense 85.9-87.7, eq 50.6-52.2.

## What it shows
- **Shown:** at equal total size, with every earlier kind replayed, this freeze-and-grow net learns new kinds far worse than the plain dense loop: mazes 0-11 vs 119-171, sums4 after B 0-113 vs 200. The dense loop keeps most of the old skills with replay and learns all three kinds.
- **Report only (not a mark):** the frozen eq net keeps grids better through phase C: grids5 after C 147-181 vs dense 60-172, higher on 5 of 6 seeds (mean 164.33 vs 128.00). Freezing does protect what it froze; the cost is new learning.
- **Suggested, post-hoc split by kind:** the new group got at least 5% of the sums cells in 5 of 6 seeds (all but seed 4), usually 60-97%, and sums still stayed at 0-113. The maze routing failed on 3 seeds (6 and 8: 0.000 in both blocks; 5: 0.306 in one). So the three "untested" seeds split into a dead sums group (seed 4) and a dead maze group (seeds 6, 8). Where the new group did get the kind, it still learned little. Together with the 358e3 eq runs this points to the small trainable share (352,944 of 1,654,446; experts 85 wide; attention frozen) as the main limit, with dead groups as a second failure. rsn-358e6 (shared layers train) and rsn-358e5 (warm routing), sealed at 9b827b22d and running now, test those two readings one change at a time.
- The dev sets (seed 48000) were read in 358e and 358e3, so this is a dev-set comparison, not a held-out test.

## What it does not show
It does not show that separate experts or a mixture of experts are wrong in general. It is one recipe: everything old frozen, zero-initialised new router rows, top-1 routing, a third of the MLP width per phase. Whether to keep separate experts in the reasoner is Ben's question, sent through the Thread manager (ADDENDUM-1 point 5).

## Plain words
We tried keeping old skills safe by locking them away and adding small new parts for each new skill, at the same total size as a normal net. With practice of the old skills in both, the normal net did better on everything except keeping the very first skill: it learned new skills well (mazes about 150 of 200) while the locked-away version barely learned them (mazes about 3 of 200). Locking works for protecting; this way of adding new parts is too small or too badly wired to learn. Two follow-up tests, one change each, are running.

## Recount notes (from the blind recount, all checked)
- The verdict holds with fixed-16 or any-round scores too (mean T 237.67 vs 467.33, and 295.67 vs 501.17; eq lower on 6 of 6 either way).
- Reading "at least 5%" as any single new expert instead of the group sum gives the same routing count (3 of 6).
- ADDENDUM-3 has no seal file; its commit (33b38420b, 02:48:50 UTC) comes before the seed 5-6 and 7-8 results in git order.
- The N <= 3 wording branch rests on one seed (3 of 6).
- The superseded PASSMARKS.md rule (seeds 3-6, bar 30, 3 of 4) gives the same verdict.
- Predictions (ADDENDUM-1): PASS 10%, proved wrong 55%. Proved wrong came true.
