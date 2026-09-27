# rsn-358u marks, DRAFT for the Thread manager: does the loop still beat plain when it is not told the puzzle kind? (sleep research thread, 2026-09-27 12:21:43 UTC; not sealed; nothing run)

**Why:** every 358 net gets the puzzle kind (sums / grids / numbers) as a learned embedding added at every cell (scripts/claude_rsn358a_run.py:96; one kind per batch, :162-165 and :172). So rsn-358i3's PASS is "loop beats plain, both told the kind". Ben, 11:34 UTC: "It should for each request be able to automatically decide what." Sol's input audit (artifacts/codex-autoroute-20260927/INPUT-AUDIT.md) and the Thread manager (12:09 UTC) flagged the same thing.
**One change vs rsn-358i3:** scripts/claude_rsn358u_run.py sets env to the same index (0) for every item in training, dev and tests, so the kind embedding becomes one learned constant. The net has to read the kind from the puzzle's own tokens. Everything else is 358i2's sealed code, imported unchanged: autocast cache off, gradient logging, data, 60,000 steps, batch 256, lr and schedule, v2 stop rule, 48 test rounds, and 358i's sealed tests. The selftest and check-mask pass on CPU (torch 2.14), and a 20-step CPU smoke run trains and saves.
**Arms:** loop (2 x d512) and plain (8 x d256), fresh seeds 13, 14, 15, 16 (358i3 used 5-8 and 358s uses 9-12), both trained on BensPC in this job. No report-only arms.

## Graded test: loop s13-16 vs plain s13-16, both fixed-env, both from this job
The marks are rsn-358i3's V0 and G0-G3, word for word.

| mark | pass |
|---|---|
| V0 validity | steps_block_nograd = 0 in every loop train_summary.json. Otherwise INCONCLUSIVE. |
| G0 validity | On every seed, loop and plain are right on >= 210/300 of the practised-size tests in at least 2 of 3 kinds. Otherwise INCONCLUSIVE. |
| G1 bigger | The 4-seed mean of loop - plain is >= +30 on at least 2 of sums6 / grids6 / numbers5, and >= -10 on the third. AND on at least 3 of 4 seeds, loop - plain > 0 on each of those (at least 2) tests. |
| G2 practised | The 4-seed mean of loop - plain is >= -10 on each practised-size test (sums4, grids5, numbers4). |
| G3 stop | On at least 3 of 4 seeds: loop right with its own stop >= loop right at fixed 16 rounds - 5 on each bigger test. AND mean rounds on sums6 > on sums4. |

**PASS = V0, G0, G1, G2 and G3.** Anything else with V0 and G0 met is a FAIL, and it stays a FAIL.
**Proved wrong:** V0 and G0 met, and the mean loop - plain is <= +5 on all three bigger tests.
Known before running: numbers4/5 were 0-5 of 300 on both arms in 358i2/358i3, so in practice G1 needs sums6 and grids6 at >= +30, and G0 needs sums and grids. The numbers kind is being worked on separately (Sol on Ben's M3 Pro; reviews/gpt-sol-numbers-2026-09-27.md). This run does not change or fix it.

## What each outcome means (scope)
- **PASS:** the loop beats its same-size plain twin without being told the kind, for these three kinds at this size, on one machine. **Scope:** the three kinds look different on the grid, so this shows only that the nets tell visibly different kinds apart. It says nothing about picking a skill from look-alike requests (the Thread manager's note a, 12:18 UTC). The loop nets from this run would replace the kind-told nets in 358b3, so 358b3 needs no caller-given kind.
- **FAIL, not proved wrong:** report which mark missed and the size of the drop from 358i3.
- **Proved wrong:** without the kind the loop's lead is gone. Then the 358i3 lead depended on being told the kind (suggested, since the seeds differ).
- **INCONCLUSIVE (G0 missed):** the nets could not learn the practised sizes without the kind. That is itself a finding, reported as such.

## Report only (not graded)
- Per arm and test, the fixed-env mean minus 358i3's kind-told mean (different seeds, so suggested only).
- sums8/10/12, grids7, the loop at fixed rounds, right at any round, mean rounds; torch/CUDA/GPU; minutes per run.
- If G0 misses: the practised-size scores per kind, per seed.

**Predictions:** PASS 60%; proved wrong 10%; G0 missed 15%. Why: the kinds use different layouts and tokens, so reading the kind should be easy, but grids6 at +30 over 4 fresh seeds already needed a large lead in 358i3 (+52).
**Cost:** $0 (BensPC). 8 runs; 358i3's loop-s5 took 78.5 min with 4 running at once. Estimate 3-5 h plus evals, run after rsn-358s. Cap 10 h. Run by BASH-ONLY jobs (no LLM builder), like 358s; the job files will follow after sealing.

## Changes after the Thread manager's review (12:25 UTC), added 2026-09-27 12:27:32 UTC, before sealing
1. **New validity mark V1 (poison check):** for every trained checkpoint, `python -B scripts/claude_rsn358u_run.py poison --ckpt W/<R>/final.pt --out W/<R>/poison.json` runs 100 freshly generated practised-size items per kind twice, once as is and once with every item's env field swapped (sums/grids to numbers, numbers to sums). Every prediction must be identical (all 48 rounds and stop values for the loop). **V1 missed on any checkpoint = INCONCLUSIVE.** It uses freshly generated items (sums4 seed 13579, grids5 seed 13580, numbers4 from the 4-number practice hands, rng 13581), not the TEST-ONLY panel, so each checkpoint still sees the test panel exactly once. Checked on CPU: a 20-step smoke checkpoint gives V1 identical on all 3 kinds with the patch, and not identical on all 3 when the real kind id is put back (negative control).
2. **Dead weights, disclosed:** the kind embedding keeps its 3 rows, and 2 of them (2 x d: 1,024 weights for the loop, 512 for plain) are never used, in both arms. They count in the weight totals (loop 6,438,302; plain 6,385,149, as in 358i3).
3. **Scope, corrected:** the loop nets from this run *could* replace the kind-told nets in 358b3, *if Month-end adds that by addendum*. 0.2d is Month-end's.
4. **G1 wording, clarified:** "on each of those (at least 2) tests" means **on each bigger test counted toward the +30**.
