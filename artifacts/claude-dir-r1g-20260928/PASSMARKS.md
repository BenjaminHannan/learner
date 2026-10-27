# R1g (general reach channel): pass marks on the equal-practice ruler

Written 2026-09-28 (`date -u` at the foot of this file) by helper R1G for the Director, before any practice, source-guard, dev or
holdout run of this design exists. **No mark changes after this file is committed.** Design: DESIGN.md. Plug-in: scripts/claude_dir_r1g_net.py.
Verdict script: scripts/claude_dir_r1g_report.py.

These are RACE-PASSMARKS.md with RACE-ADDENDUM-1 (`F_all` becomes `F_eq`) and the H10 amendments of ADDENDUM-1 in
artifacts/claude-dir-h3-design-20260928 (three-draw sleep gates, the F_few row, every-gaining-seed rejection, gate-tensor weight-decay exemption),
copied here so this test is judged on this page alone. Thresholds are the ones the race already fixed. Each seed is judged on its own; seeds are
never pooled. Ruler: artifacts/claude-fewex-20260927 (EQ-DEV-GATE.json = PASS). Harness scripts/claude_fewex_eq_bench.py is used unedited, with
`--plugin claude_dir_r1g_net`. This is one change: the reach channel (DESIGN.md). Nothing else differs from the loop.

## Arms (logical seeds 0 and 1, the ruler's own support pools and panels)
- **R1g**: the loop plus the reach channel, source-practised (sums and grids only, the ADDENDUM-3 recipe), `--init pre`.
- **Fresh R1g**: the same net at random init, never practised, `--init fresh`.
- **The loop** and **the plain net**: the baseline's `eq-runs/loop-s{seed}-pre` and `plain-s{seed}-pre`. Not retrained.

## The numbers to beat (recounted from the raw holdout.json of the baseline; the report script reproduces them: F_eq 51.00 and 51.29, F_few 13.83 and 16.17)
| seed | loop F_eq | R1g needs F_eq at least | loop F_few | R1g needs F_few at least | plain F_eq | R1g needs at least (plain + 5) |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 51.00 (sum 1,224) | **61.00** (sum 1,464) | 13.83 | **18.83** | 33.79 | 38.79 |
| 1 | 51.29 (sum 1,231) | **61.29** (sum 1,471) | 16.17 | **21.17** | 33.58 | 38.58 |

## How the numbers are read (fixed now)
- `F_eq`: from the harness's holdout.json, the mean over k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384 of 100 x right / 300 on the 9x9 holdout,
  learned stop. `F_few`: the same over k = 1, 4, 16, 64. Differences are percentage points.
- "Old kinds before maze adaptation" is `old.before` (200 sums4, 200 grids5). Sleep gates are described in mark 4.
- Size: `weights` in adapt.json, every stored number. R1g is 1,654,198 against the loop's 1,645,726 (+0.515%, extra 8,472).

## Source guard (before any maze run)
In each seed the practised R1g gets at least 190 of 200 on the guard's 4-digit sums and at least 190 of 200 on its 5x5 grids (seed SOURCE_SEED+300),
and every two-dimensional weight matrix has a nonzero fp32 gradient (the harness's check). If either fails in either seed: report and stop, no maze
run, reported INCONCLUSIVE at this budget. Also required first: `python scripts/claude_dir_r1g_selftest.py` ends with `"selftest": "ok"` on the machine
that practises (it already did on the cloud CPU: artifacts/claude-dir-r1g-20260928/selftest-cloud.json).

## Pass, in both seeds (PASS needs every row in both seeds)
1. R1g `F_eq` at least **10 points above the loop** (61.00 in seed 0, 61.29 in seed 1).
2. R1g `F_eq` at least 5 above the baseline plain net, and at least 5 above the fresh R1g.
3. Old kinds before maze adaptation at least 190 of 200 each, and no more than 6 of 200 below the loop on each kind.
4. Old kinds after the k = 64 sleep and after the k = 16,384 sleep: for each (branch, kind), `mean(R1g) >= mean(loop) - max(6, 2 x SE)` over 3 sleep draws
   each (offsets 0, 101, 202), SE = sqrt(var_R1g/3 + var_loop/3) with sample variances. All four cells must pass in a seed. Draw files come from
   scripts/claude_dir_r1g_sleepdraws.py; draw 0 must equal the harness's recorded sleep. If a seed's draw files are missing or void, mark 4 is
   report-only there and a run that meets every other row reads **"PASS (sleep gates not judged)"**, never plain "PASS".
5. Size within 2% of the loop's, counting every stored number.
6. **F_few at least +5.0 over the loop's F_few** (18.83 and 21.17). Required, like row 1. It does not enter the REJECTED conditions.

## Proved wrong (REJECTED)
- R1g `F_eq` no higher than the loop in both seeds (a tie counts as no higher): i.e. the eight holdout counts sum to at most 1,224 in seed 0 and
  at most 1,231 in seed 1. This is the result that proves "a learned, kind-blind reach channel raises few-example maze skill by 10 points at this budget" wrong; or
- a maze gain made only by breaking an old-kind gate: **every** seed where R1g's `F_eq` is above the loop has at least one judged old-kind gate (marks 3 or 4) failing.
If one seed is above the loop and one below, the design is **not promoted but not rejected** (the sparse loop's reading: +3.88 and -6.25).

## Verdict words
PASS if rows 1-6 hold in both seeds. REJECTED if a proved-wrong condition holds. Otherwise NOT PROMOTED, with the failing rows named per seed.

## Credit check and channel use (report only; they never change the verdict word, they decide which sentence a PASS may carry)
- **Credit:** on the **dev** panel (never the holdout), take each seed's k = 1,024 net and switch the ten reach features off at inference
  (`Net.REACH_OFF`). If the dev 9x9 count drops by at least **30 of 300** in both seeds, a PASS may say "the reach channel passed". If it drops by less in
  either seed the PASS is worded "the design passed; the reach channel is a bystander". Script: claude_dir_r1g_credit.py.
- **Channel unused:** mean |mix.weight| below 0.001 both after practice and at k = 16,384, in both seeds: a PASS is worded "the reach channel was unused;
  the design passed but the reach channel is not the cause".
- Also reported: gamma after practice and adaptation, mean rounds and cap hits per rung against the loop, E50 (k for 50% on 9x9), the 7x7 and 11x11
  panels, both sleep `D` values by kind, training time, stored weights, and the mean |mix.weight| by feature column.

## What this ruler can and cannot say about "general" (written now, so nobody reads more into a PASS)
- The ruler scores **one held-out kind, mazes**. A PASS is a maze result. It does not show carry-over to a second unseen kind; that needs the H1 ruler
  with two more held-out kinds (roadmap item 3), and a PASS here should be re-run there.
- "General" in this test means the design's *inputs and features*: shown by the CPU self-test (`no_kind_words`: no identifier or string in the
  plug-in's code names a maze, wall, route, start, goal, grid, puzzle or kind; `step` reads only the state, the input embedding and the loop's own
  offsets; `equivariance`: permuting the items permutes the output; `set_input`: it runs on 37 unordered items with no grid at all). These are checks
  of the code, not of how well it works on other kinds (untested).

## Order
1. Commit these marks, DESIGN.md, the code and SEAL.sha256.txt. 2. Job 1 (`queue-r1g-1-practice.md`): selftest and practice, source guard. 3. Job 2
(`queue-r1g-2-dev.md`): dev ladders, dev table, credit check; nothing changes after any dev score is seen. 4. Job 3 (`queue-r1g-3-holdout.md`): three-draw
sleeps if the loop's checkpoints exist, one holdout pass per run, the verdict script. 5. A separate step recounts from the raw JSON and this page only.
If the baseline's EQ-DEV-GATE.json on main is not PASS, this test is INCONCLUSIVE.

Written at 2026-09-28 21:28 UTC (`date -u`), before any run of this design.
