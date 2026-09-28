# Does sleep keep old kinds better if the loop also matches its own earlier answers?

Written 2026-09-28 19:40 UTC (`date -u`). Marks: `PASSMARKS.md`, committed (abf0bf81a) before any sleep ran.
Records: `sleeps/` (60 files), `summary.json`, `tables.md`. Recount: `BLIND-RECOUNT.md` (matches everything below).
Counts are "x of 200" (old panels), "x of 300" (9x9 maze). Labels: **shown** = measured here on these 2 seeds,
**suggested** = plausible reading, **untested** = not tried.

## Verdict: NOT PASSED, NOT PROVED WRONG

| Mark | Needed | Got | Result |
|---|---|---|---|
| M1 sums4 (D128 - R128, mean of 4 cells; cells higher) | >= 20 of 200; >= 3 of 4 | +4.5; 4 of 4 | fail |
| M1 grids5 | >= 20 of 200; >= 3 of 4 | +9.75; 4 of 4 | fail |
| M1b sums4 (D128 - W128) | >= 10 of 200 | -1.75 | fail |
| M1b grids5 | >= 10 of 200 | +1.25 | fail |
| M2 (D128 9x9 maze minus R128, every cell) | >= -6 of 300 | +17.7, -18.0, +7.7, -10.0 | fail (2 cells) |
| Proved wrong (< 5 of 200 on both kinds) | | 4.5 sums4, 9.75 grids5 | no: grids5 is above 5 |
| Smaller store: D16 - R16 sums4 / grids5 | >= 20 each, >= 3 of 4 cells | +1.17 (3 of 4) / +7.5 (4 of 4) | fail |
| D16 within 6 of R128, >= 3 of 4 cells | | 0 of 4 on both kinds | no |

**Shown:** matching the teacher's answers added a small, consistent gain over true-answer replay (D128 above R128 in
all 4 cells on both kinds; +4.5 of 200 on sums, +9.75 of 200 on grids), far below the 20 bar. **Shown:** it is not
a better use of the extra weight than simply doubling the true-answer loss: W128 is as good or better on sums (-1.75)
and about equal on grids (+1.25). **Shown:** D128 cost 9x9 maze skill in the two k = 16,384 cells (-18 and -10 of 300).
**Shown:** an 8x smaller store (16 per kind) collapses old-kind scores for every arm (3 to 26 of 200); the teacher term
recovers a few grids (+7.5) and almost no sums (+1.2). **Suggested:** with 2 seeds and 3 draws, the grids gain is real
but small (the biggest single cell, +23.7 in seed 0 after k = 16,384, drives half of the mean); sums is within draw noise.
**Untested:** other KL weights, temperatures, longer sleep, or teacher outputs on extra puzzles (weight 1.0 was fixed, not tuned).

## Cell means over 3 draws (sums4 / grids5 of 200; 9x9 of 300)

| Cell | R128 | D128 | W128 | R16 | D16 |
|---|---|---|---|---|---|
| s0 k64 | 155.3 / 100.7 / 120.7 | 160.0 / 111.0 / 138.3 | 179.0 / 112.0 / 132.0 | 10.3 / 12.0 / 135.0 | 13.7 / 14.7 / 107.0 |
| s0 k16384 | 72.3 / 83.7 / 281.0 | 76.0 / 107.3 / 263.0 | 72.7 / 106.7 / 276.3 | 5.7 / 6.3 / 259.3 | 4.7 / 16.3 / 271.0 |
| s1 k64 | 156.0 / 132.7 / 110.7 | 161.3 / 136.0 / 118.3 | 150.3 / 131.3 / 101.3 | 11.0 / 13.3 / 110.3 | 13.0 / 26.3 / 130.0 |
| s1 k16384 | 51.3 / 128.0 / 268.0 | 55.7 / 129.7 / 258.0 | 58.0 / 129.0 / 257.7 | 3.3 / 2.7 / 269.3 | 3.7 / 7.0 / 283.0 |

Per-draw values, 7x7 (of 24), 11x11 (of 300), fresh-panel counts, KL and stop rounds for all 20 arm-cells: `tables.md`.

## Validity (needed disclosure)

**The saved nets (`k0.pt`, `k64.pt`, `k16384.pt`) and qualified sources were not in the checkout, so I rebuilt them**
(unchanged `claude_fewex_source_qualify.py`, then the harness's own functions for rungs 64 and 16,384 only; the other
six rungs do not affect these two, but skipping them is a disclosed deviation). The rebuild is **not bit-identical** to
the ruler's run (`rebuild/…/rebuild-k*.json`, `all_exact: false`): old-kind counts before and after maze practice and
the rung-0 maze matched, but later maze scores and the harness sleep differ, and the seed-1 source picked fixed depth 8
instead of 16. **Suggested** cause: different machine and torch build (untested).

Mark "R128 draw 0 equals adapt.json exactly": **fails.** R128 draw 0 vs. the ruler's sleep (sums4 / grids5): s0 k64
174/104 vs 149/99; s0 k16384 79/86 vs 76/90; s1 k64 152/132 vs 155/86; s1 k16384 42/121 vs 83/100. Per the marks, the
re-run R128 is the control for every comparison above (all arms share the rebuilt nets). **Shown:** R128 draw 0 equals the
rebuild's own harness sleep exactly in all 4 cells (old and maze scores), and the code's mode R equals the harness sleep
bit for bit (`selftest.json`), so the comparison D128 vs R128 is like for like. The ruler's absolute numbers should not be
quoted from these nets.

Other disclosure: the D arms hold one extra frozen copy of the net during sleep only (no teacher output or extra puzzle stored).

## Report only

- **Draw spread** (min-max, sums4 / grids5), R128 vs D128: s0 k64 134-174 / 94-104 vs 147-181 / 107-113; s0 k16384 60-79 / 80-86 vs
  73-82 / 103-110; s1 k64 152-158 / 127-139 vs 155-169 / 135-138; s1 k16384 42-69 / 121-132 vs 41-75 / 120-136.
  Sums draws overlap heavily; grids in the two seed-0 cells separate cleanly. All other arms in `tables.md`.
- **Teacher (k0) scores**, fixed panel sums4 / grids5: seed 0 200 / 199, seed 1 200 / 200; fresh panel 200 / 200 on both seeds.
- **KL(teacher || student) on the 128+128 store**, mean over rounds 1-16, before sleep: sums 12.4-16.6, grids 17.3-19.0. After
  sleep, R/W/D128: 0.03-0.32 (sums), 0.16-0.29 (grids); D128 only slightly lower than R128 (e.g. sums s0 k64 0.064 vs 0.081).
  With 16 stored: 2.1-4.7, and D16 lowers grids KL (about 2.2 vs 2.9) but not sums KL.
- **Rounds:** mean trained rounds per kind per step: total about 8.2-8.9, with gradient on about 3.0-3.1. Learned-stop rounds
  differ by arm (see `tables.md`); D128 sometimes stops later (s0 k16384 sums 33.0 vs 17.8).
- **Fresh old-kind panel** (200+200, never in the store): tracks the fixed panel, same ordering of arms (e.g. s0 k16384 grids5
  D128 109.0 vs R128 78.3), so the gains are not the store's own puzzles.
- **Cost:** a D sleep took about 290 s vs about 255 s for R (+14%), 1 thread each.

## Time and cost

Started 15:49 UTC; sources ~75 min, rebuild ~39 min, teacher, 60 sleeps to 19:32 UTC (total about 3 h 50 min). $0, no
rentals, fp32 CPU in this container (4 cores, 4 jobs at a time).
