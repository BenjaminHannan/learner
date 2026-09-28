# H3 settle-gate loop: pass marks on the equal-practice ruler

Written 2026-09-28 19:16 UTC (`date -u`), before any run of this design's code (the code has never been run: the
box it was written on has no torch) and before any practice, source-guard or maze score of this design exists.
No mark changes after this file is committed. Design: DESIGN.md. Plug-in: scripts/claude_dir_h3_net.py.

These are RACE-PASSMARKS.md with RACE-ADDENDUM-1.md's substitution (`F_all` -> `F_eq`, the 64k sleep -> the
16,384 sleep), copied here so this test is judged on this page alone. Thresholds are the ones the race
already fixed. Each seed is judged on its own; seeds are never pooled. The ruler is the equal-practice ruler
(artifacts/claude-fewex-20260927: ADDENDUM-3, ADDENDUM-4, RACE-ADDENDUM-1; EQ-DEV-GATE.json = PASS). Its
harness scripts/claude_fewex_eq_bench.py is used unedited, with `--plugin claude_dir_h3_net`.

## Arms (logical seeds 0 and 1, the ruler's own support pools and panels)
- **H3**: the settle-gate loop, source-practised (sums and grids only, the ADDENDUM-3 recipe), `--init pre`.
- **Fresh H3**: the same net at random init, never practised, `--init fresh` (harness seed 900000+seed).
- **The loop**: the baseline's `eq-runs/loop-s{seed}-pre` (adapt.json, holdout.json). Not retrained. This design
  uses no episodic source training and no new learner, so the loop control needs nothing extra.
- **Plain net**: the baseline's `eq-runs/plain-s{seed}-pre`. Not retrained.

## The numbers to beat (from RESULTS-EQ.md, already on main)
| seed | loop F_eq | H3 needs F_eq at least (loop + 10) | plain F_eq | H3 needs at least (plain + 5) |
|---:|---:|---:|---:|---:|
| 0 | 51.00 | 61.00 | 33.79 | 38.79 |
| 1 | 51.29 | 61.29 | 33.58 | 38.58 |
The fresh H3's own F_eq is only known after its run; the mark is H3 F_eq at least the fresh H3 F_eq + 5.

## How the numbers are read (fixed now)
- `F_eq`: from the harness's holdout.json, the mean over k = 1, 4, 16, 64, 256, 1,024, 4,096 and 16,384 of
  100 x right / 300 on the 9x9 holdout, learned stop. Differences are percentage points.
- "Old kinds before maze adaptation" is the harness's `old.before` (200 sums4, 200 grids5). "After both sleeps" is
  `sleep.64.old` and `sleep.16384.old`. Being above the loop always passes.
- Size: `weights` in adapt.json (every stored number). H3 is 1,645,984 against the loop's 1,645,726 (+0.016%).
- The marks are computed by scripts/claude_dir_h3_report.py (committed with this file; it calls the sparse
  test's arithmetic in scripts/claude_sparse_race.py, which reproduces the loop's 51.00 and 51.29 from the
  baseline files, checked before this page was committed).

## Source guard (before any maze run)
In each seed, the practised H3 gets at least 190 of 200 on the guard's 4-digit sums and at least 190 of 200 on
its 5x5 grids (seed SOURCE_SEED+300), and every two-dimensional weight matrix gets a nonzero fp32 gradient on a
sums or a grids batch (the harness's check). If either fails in either seed: report it and stop. No maze run.
Also required before any maze run: scripts/claude_dir_h3_selftest.py ends with `"selftest": "ok"`.

## Pass, in both seeds
1. H3 `F_eq` at least **10 points above the loop** (61.00 in seed 0, 61.29 in seed 1).
2. H3 `F_eq` at least 5 points above the baseline plain net, and at least 5 above the fresh H3.
3. Old kinds before maze adaptation at least 190 of 200 each, and no more than 6 of 200 below the loop on each kind.
4. After the k=64 sleep and after the k=16,384 sleep, each old kind no more than 6 of 200 below the loop's same record.
5. Size within 2% of the loop's, counting every stored number.
6. Learned stop kept: the 48-round cap, the same source-selected fixed-depth check. (Reported below, not a
   separate mark; a stop failure is reported per rung, as the ruler defines it.)

## Proved wrong (REJECTED)
- H3 `F_eq` no higher than the loop in both seeds (a tie counts as no higher); or
- a maze gain made only by breaking an old-kind gate: in every seed where H3's `F_eq` is above the loop, at
  least one of marks 3-4 fails.

## Verdict words
PASS if marks 1-5 hold in both seeds. REJECTED if a proved-wrong condition holds. Otherwise NOT PROMOTED, with
the failing marks named per seed (the sparse loop ended NOT PROMOTED this way: +3.88 and -6.25).

## What this design's own mechanism would look like if it worked (report only, no gate, written now)
These are read after the verdict and cannot rescue or sink it.
- Gate use: per-round mean gate, share below 0.5 and share above 0.98, on source sums, source grids and dev
  mazes, at the practised net and at the k=64 and k=16,384 checkpoints (scripts/claude_dir_h3_gate_report.py).
  **Dead gate** (reported as such): mean gate above 0.98 in every round on every set, or below 0.05.
  Then the design is the loop, or a broken loop, and the F_eq difference means nothing about the mechanism.
- Mean rounds and cap hits per rung against the loop (the mechanism predicts fewer cap hits: DESIGN.md).
- E50, the k=64 50% line, the 7x7 and 11x11 panels, F_few minus cold, both sleep `D` values by kind, the
  stop-failure list, training time, optimizer updates, raw example memory (unchanged from the harness: 128 sums
  and 128 grids of replay plus the branch's own mazes; the plug-in stores nothing), stored weights (1,645,984)
  and persistent coefficients (the same).

## Order
1. Commit these marks, DESIGN.md and the code. 2. Selftest (torch machine) and commit selftest.json/log.
3. Practise two source nets (seeds 0, 1), source guard; commit. 4. Dev ladders: H3 and fresh H3, both seeds;
   commit the dev records and dev table; nothing changes after any dev score is seen. 5. Holdout once per run
   with the harness's `holdout` command, then the report script. 6. A separate subagent recounts from the raw
   JSON and this page only. If the baseline's EQ-DEV-GATE.json on main is not PASS, this test is INCONCLUSIVE.
