# R2g tied-directions loop: pass marks on the equal-practice ruler

Written 2026-09-28 21:29 UTC (`date -u`), before any practice, source-guard or maze score of this design exists (the only things run are the CPU selftests, `selftest.json`, none of which scores a maze).
No mark changes after this file is committed. Design: DESIGN.md. Plug-in: `scripts/claude_dir_r2g_net.py`. Verdict script: `scripts/claude_dir_r2g_report.py` (imports `claude_dir_h3_report_add1.py` unedited).

These are the race marks (RACE-PASSMARKS.md with RACE-ADDENDUM-1.md, `F_all` -> `F_eq`) with the H10 amendments of `artifacts/claude-dir-h3-design-20260928/ADDENDUM-1.md` applied from the start: (a) a REJECTED-by-breaking verdict needs every gaining seed to break an old-kind gate,
(b) the sleep gates use the mean of three sleep draws with margin max(6, 2 x SE), (c) F_few is a second required row. Each seed is judged on its own; seeds are never pooled. Ruler: `artifacts/claude-fewex-20260927` (EQ-DEV-GATE.json = PASS), harness `scripts/claude_fewex_eq_bench.py` unedited, `--plugin claude_dir_r2g_net`.

## Arms
- **R2g**: the tied-directions loop, source-practised (sums and Latin grids only, 12,000 batches of 64), `--init pre`. **Fresh R2g**: same net, random init, `--init fresh`.
- **The loop** and **plain net**: the baseline's `eq-runs/loop-s{seed}-pre` and `plain-s{seed}-pre`, not retrained. The single change against the loop is the tied bias and its cross mask; no other arm is needed (no episodic training, no new learner).

## Numbers to beat (recounted by `claude_dir_r2g_report.py selftest` from the baseline's raw holdout files: 51.00 / 51.29, F_few 13.83 / 16.17)
| seed | loop F_eq | R2g needs F_eq at least | (sum of the eight counts of 300) | plain F_eq | +5 | loop F_few | R2g needs F_few at least |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 51.00 | 61.00 | 1,464 | 33.79 | 38.79 | 13.83 | 18.83 |
| 1 | 51.29 | 61.29 | 1,471 | 33.58 | 38.58 | 16.17 | 21.17 |
`F_eq` = mean over k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384 of 100 x right / 300 on the 9x9 holdout, learned stop. `F_few` = mean over k = 1, 4, 16, 64.

## Source guard (before any maze run)
In each seed the practised R2g gets at least 190 of 200 on 4-digit sums and at least 190 of 200 on 5x5 grids (guard seed SOURCE_SEED+300), and every 2-D weight matrix (the tie tables included) has a nonzero fp32 gradient (harness check). Fail in either seed: report and stop, **reject at this fixed 0.3, no retune**.
Also required first: `scripts/claude_dir_r2g_selftest.py` ends with `"selftest": "ok"` on the machine that runs the job.

## Pass, in both seeds (PASS needs every row)
1. R2g F_eq at least **10 points above the loop** (61.00, 61.29).
2. R2g F_eq at least 5 above the baseline plain net and at least 5 above fresh R2g (counts sum at least fresh sum + 120).
3. **F_few at least +5.0 over the loop** (18.83, 21.17). (H10 amendment (c).)
4. Old kinds before maze adaptation: at least 190 of 200 each (sums4, grids5) and no more than 6 below the loop on each kind.
5. After the k = 64 sleep and the k = 16,384 sleep, each old kind: mean of 3 sleep draws of R2g at least the loop's 3-draw mean minus max(6, 2 x SE). (H10 amendment (b); `claude_dir_r2g_sleepdraws.py`.) If the draws cannot be made, the Director commits `SLEEPS-SKIPPED.txt` and this row is report-only; a run meeting every other row is then worded "PASS (sleep gates not judged)".
6. Size: stored weights within 2% of the loop's 1,645,726 (R2g: 1,645,806).
Reported, not marked: the 7x7 and 11x11 panels, E50, 50% at k = 64, mean rounds, cap hits, fixed-depth counts, stop failures, training time, sleep D values.

## Proved wrong (REJECTED)
- R2g F_eq no higher than the loop in both seeds (a tie counts as no higher); or
- a gain made only by breaking an old-kind gate: at least one seed where R2g is above the loop, and **every** such gaining seed fails row 4 or a judged row 5.
- Also rejected at this budget: the source guard fails (above).
One seed above and one below, or above without reaching +10, is **NOT PROMOTED** with failing rows named per seed, not rejected.

## Result that would prove the idea wrong (fixed now)
Rows 1 and 3 both fail in both seeds. That rejects "sharing one distance table across axes and directions, with a slow direction residual, helps a loop learn a new grid kind from few examples at this budget". It says nothing about learned (non-coordinate) sharing, which is untested.

## Report-only credit checks (read after the verdict, cannot rescue or sink it)
- **Swap check** (`claude_dir_r2g_swapcheck.py`, DEV panel only, k = 1,024 net of each seed, R2g and, if its checkpoint survives, the loop): right counts of 300 on the 300 dev 9x9 mazes and the same mazes transposed. If the loop's gap (original minus transposed) is 20 or less: INCONCLUSIVE (no headroom). A PASS may say "the gain can be read as symmetry" only if R2g's gap is at most half the loop's in both seeds; otherwise it says "the design passed; the gain is not shown to come from symmetry". No loop checkpoint: "symmetry credit not checked".
- **Bystander check**: mean |tie| in each block at the practised net and at k = 1,024. If it is under 1e-3 in both blocks in both seeds the net never used the tied table, and a PASS is worded "the design passed" only.
- Novelty wording: whatever the result, R2g is the mildest of H9's four (residual pathway priors, arXiv 2112.01388, applied to a looped reasoner's relative position bias); do not call a PASS a new principle.

## Order
1. Commit these marks, DESIGN.md, the code, the queue files (all HELD). 2. Job 1: selftests, practise seeds 0 and 1, source guard, commit source.json. 3. Job 2: four dev ladders (pre and fresh, both seeds), dev table, swap and tie checks; nothing changes after any dev score is seen. 4. Job 3: sleep draws (or SLEEPS-SKIPPED). 5. Job 4: holdout once per run, then the verdict script. 6. A separate thread recounts from the raw JSON and this page only. If the baseline's EQ-DEV-GATE.json is not PASS the test is INCONCLUSIVE.
