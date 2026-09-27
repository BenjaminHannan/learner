# rv-390 on the retrained nets (rsn-358i2), and the rv-391 trigger choice on them (thought-memory thread; written 2026-09-27 16:43 UTC by date -u)

Raw output: run-358i2/ (rv-390, step A) and ../claude-rv391-20260926/dev-358i2/ (rv-391 dev measure, step C), copied
from builder-outbox. Job: rent-rv390b-p1 (script only, no builder), vast RTX 4090 (81.4 TFLOPS, $0.4014/h), 27 min,
about $0.18 by its LEDGER line. Code: git archive of f5213af7c. Seals 15/15, 14/14 and 2/2 on the rental. The four
nets' sha256 match NETS-358i2.sha256.txt on the Mac and on the rental (run-358i2/SOURCES.txt). Torch 2.11.0+cu128.
Every copied file matched a sha256 manifest made on the rental. The selftest matched rv-387's GUESS on 30 of 30
practice puzzles for every net. Marks: PASSMARKS.md (sealed 86a7ddfd1), unchanged by ADDENDUM-358i2-rerun.md.
Blind recount: see the end of this file.

## rv-390 verdicts (hard grids7 puzzles: unfinished, and no round of the day's 48 accepted)

| seed | hard | KEEP | RESTART | GUESS | KEEP - RESTART | GUESS - KEEP |
|---|---|---|---|---|---|---|
| 1 | 84 | 0 | 30 | 50 | -30 | +50 |
| 2 | 36 | 1 | 27 | 4 | -26 | +3 |
| 3 | 78 | 0 | 49 | 42 | -49 | +42 |
| 4 | 90 | 0 | 43 | 52 | -43 | +52 |

- H (carrying on vs starting over): PROVED WRONG. KEEP solved no more than RESTART in 4 of 4 seeds; the mark needed 3.
  Carrying on for 480 rounds solved 0 or 1 hard puzzle per net. Ten fresh 48-round starts solved 27 to 49.
- G (writing guesses while working): PASS. GUESS beat KEEP by 50, 3, 42 and 52; the mark needed at least 10 in 3 of 4
  seeds (seed 2 missed it).
- I (interruptible): PASS. In all 4 seeds KEEP's every round and all 40 GUESS results equal the run without pauses;
  every message answer equals the answer with no worker running (60, 145, 85 and 65 messages); the longest wait was
  0.226, 0.218, 0.142 and 0.187 s on the rental's GPU with 5 nets sharing it. The Mac and BensPC are untested.
- Same verdicts as on 358i's nets (RESULTS.md). The retrained nets finish more of the day (hard sets 36 to 90, was 177
  to 275), as the addendum expected.

## Report only
- GUESS vs RESTART on hard grids7: 50 vs 30, 4 vs 27, 42 vs 49, 52 vs 43, so 148 vs 149 in total. Neither is ahead
  overall; on 358i's nets GUESS led 104 vs 76.
- Untrained control r0 (same code, random weights, report only): day pass 0 of 300; KEEP 0 and RESTART 0 hard solves;
  GUESS 26 of 300 hard grids7 and 62 of 300 hard grids6. So part of what GUESS solves comes from the disclosed code parts
  (the checker, and candidates that skip symbols already in the row or column), not from the net.
- grids6 hard (few puzzles): KEEP 0, 1, 0, 0; RESTART 4, 4, 7, 10; GUESS 2, 0, 7, 7 of 5, 4, 8, 11.
- Sigma picked on practice grids: 0.1, 0.3, 0.1, 0.1. grids7 seconds per net: 139, 154, 175, 164.
- Peak GPU memory for 5 nets at once: 3,947 MiB of 24,564.

## Defaults this sets (per the addendum: the 358i2 verdicts set them)
- Between messages, the worker starts fresh rather than carrying on (H proved wrong on both net sets).
- Writing guesses beats carrying on (G), but it does not beat starting fresh in total (148 vs 149), and the untrained
  control shows the code's candidate rule does part of the work.

## rv-391 trigger choice on the same nets (NOTE-dev-plan.md rule, p-grids7, all guesses; AUC 0.5 = no signal)

| signal | net 1 | net 2 | net 3 | net 4 | mean |
|---|---|---|---|---|---|
| dq (drop in q) | 0.331 | 0.415 | 0.398 | 0.332 | 0.369 |
| d_mean_ent | 0.440 | 0.460 | 0.485 | 0.421 | 0.452 |
| d_max_ent | 0.469 | 0.456 | 0.497 | 0.454 | 0.469 |
| flips | 0.449 | 0.451 | 0.506 | 0.477 | 0.471 |
| p_written (low) | 0.469 | 0.490 | 0.442 | 0.451 | 0.463 |
| clash (rule-based, comparison only) | 0.437 | 0.436 | 0.422 | 0.477 | 0.443 |

No candidate reaches a mean of 0.65, and none is above 0.5 in all four nets. The fallback applies, as on 358i's nets:
rv-391 goes back when the checker has not accepted the grid 16 rounds after a guess (W = 16).
Guesses measured: 489, 323, 610 and 575 (wrong 87, 94, 115 and 120).

Blind recount (separate worker, returned 16:48 UTC; it did not read this file): agrees on every count and verdict: H PROVED WRONG,
G PASS, I PASS, and no rv-391 trigger chosen (fallback W = 16). It recomputed every hard solve from the finds rows and
every p-grids7 AUC from the per-guess rows (all match the JSON to 4 decimals), checked all 854 saved answers against
the day puzzles (givens kept, rows and columns valid, equal to the stored solution; 0 failed), confirmed the 25 + 12
files against the SOURCES.txt manifests, SEAL 15/15, and the sigma picks. One note from it: PASSMARKS Setup names 358i's
SEAL-run file for the net check; ADDENDUM-358i2-rerun.md replaced that with NETS-358i2.sha256.txt, which the nets match.
