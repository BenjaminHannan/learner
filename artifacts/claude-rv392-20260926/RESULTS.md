# rv-392 results: fresh starts with guesses vs fresh starts alone (thought-memory thread; written 2026-09-27 17:16 UTC by date -u)

Raw output: run/ (25 files plus SOURCES.txt), copied from builder-outbox 73369ff46. Job: 174-rv392-358i2-pc on BensPC
(RTX 5070 Ti, $0), step B, 23 min. Torch 2.11.0+cu128. Seals 15/15, 14/14 and 2/2. The four nets' sha256 match
../claude-rv390-20260926/NETS-358i2.sha256.txt (the rsn-358i2 nets, per that folder's ADDENDUM-358i2-rerun.md).
Selftest: guess_from equal to rv-390's worker on 30 of 30 practice puzzles for every net, so all 4 nets ran.
Marks: PASSMARKS.md (sealed) and ADDENDUM-1-untrained-net-control.md (sealed, report only).

## Verdict: PASS (hard grids7 puzzles: unfinished, and no round of the day's 48 accepted)

| seed | hard | RESTART | RG | RG - RESTART | GUESS480 (report only) |
|---|---|---|---|---|---|
| 1 | 83 | 36 | 55 | +19 | 31 |
| 2 | 51 | 34 | 43 | +9 | 10 |
| 3 | 80 | 33 | 48 | +15 | 44 |
| 4 | 83 | 27 | 43 | +16 | 37 |

- RG (10 fresh 48-round starts, guesses written inside each) beat RESTART (the same starts, no guesses) by at least 10
  in 3 of 4 seeds (seed 2 missed by 1). The mark needed 3.
- P392.1 (PASS) held. P392.2 (RG at least GUESS480 in 3 of 4 seeds) held in 4 of 4.
- By PASSMARKS "Next, fixed now": the between-messages worker is fresh starts with guesses.

## Untrained control r0 (addendum 1, report only)

On each trained net's own hard grids7 puzzles, r0 solved 0 in every arm and seed (rv-390 GUESS, rv-392 RG, RESTART and
GUESS480). Every grids7 puzzle r0 solved (26 on rv-390's day, 36 on rv-392's day) was one the trained net already got
right in its day pass, except one on rv-390's day for seed 4, which was unfinished but not hard.
- "The net adds over the code" (trained beats r0 by at least 10 on the same puzzles): RG 4 of 4 seeds; RESTART 4 of 4;
  GUESS480 4 of 4; rv-390 GUESS 3 of 4 (seed 2: 4 vs 0).
- r0 came within 10 of a trained net's GUESS or RG in 1 of 4 seeds (rv-390 GUESS, seed 2), not 3, so the addendum's
  "hand-written stand-in" label is not triggered. The code parts (checker, row and column candidates) solve easy
  puzzles alone, but none of the trained nets' hard ones.

## Report only
- All unfinished grids7 (not only hard), RESTART / RG / GUESS480: seed 1 49 / 68 / 44 of 96; seed 2 39 / 49 / 16 of 57;
  seed 3 61 / 77 / 72 of 109; seed 4 49 / 66 / 61 of 107.
- RG solves in its first loop (rounds 1 to 48), all unfinished: 49, 17, 38 and 38 (hard: 37, 16, 21 and 20).
- Guesses written by RG on grids7: 2247, 1092, 2720 and 3160.
- grids6 hard (few puzzles), RESTART / RG / GUESS480: 5 / 8 / 6 of 8; 3 / 3 / 0 of 3; 5 / 5 / 5 of 5; 8 / 10 / 8 of 11.
- Sigma per net: 0.1, 0.3, 0.1, 0.1 (r0 0.1). grids7 seconds per net: 269, 196, 287, 288.

## Checks
Counted from the raw rows, not the job's summary: hard and unfinished sets from ../claude-rv392-20260926/daydump
(rent-rv390b-p1, same nets), solves from run/*.finds.jsonl. Every hard, unfinished, solved and first-loop count equals
rv392-s*.json. All 866 saved answers (783 from s1 to s4, 83 from r0) keep the givens, have valid rows and columns, and equal the
stored solution (0 failed, 0 duplicates). No separate blind recount was run (Ben's usage rule, 14:34 UTC 09-27).
