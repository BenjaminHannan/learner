# S1 "Turn and flip mazes": pass marks

Written 2026-09-29 (started 02:05 UTC, `date -u`; the commit time is in git) by helper S1 (thread "Turn and flip mazes"), on top of main `f5fdc2571`, **before any D4 maze score exists** (no run of this change has started) and before the code is sealed. No mark changes after this file is committed. Source of the test and its numbers: `design/research/lead-sweep-2026-09-29/SYNTHESIS.md` section 3, test 1; brief `handoff/director-briefs/sweep-tests.md` S1. Counts are "x of N". Labels: shown / suggested / untested.

## Label (Director's ruling, 02:04 UTC)
**This is a hand-picked, mazes-only prior, not kind-blind.** The 8 turns and mirrors are chosen by hand because a maze's answer turns with the maze. Sums and Latin grids do not have this symmetry. It is applied to **both** the loop and the plain net, both seeds. A pass is reported as **"works with a maze-specific shortcut"**, never as general learning. Every number is dev panel only; the holdout and every blind panel stay unopened.

## The one change
In the maze adaptation step only, every maze in every batch is turned by one random member of D4 (4 turns x mirror = 8 views, uniform), tokens, fill slots and answer together (`scripts/claude_s1_d4_aug.py`, `claude_s1_d4.py`). Same k support mazes and pool (`support_sha256` unchanged), same batches, same 2,048 optimizer updates per rung, same sealed qualified source nets, same optimizer, same scoring (no voting), fp32 CPU. Sleep is inherited and sees un-turned mazes (report-only). The harness `claude_fewex_eq_bench.py` is not edited; the change is a plug-in.

**Leak guard (found while writing this, not in the synthesis).** There are only 100,352 possible 9x9 maze layouts, and the support pool holds 16,384 of them. A turned support maze can therefore equal a dev or holdout panel layout: 655 of the 8 x 16,384 views in seed 0 and 674 in seed 1 (`claude_s1_d4_selftest.py` part A, counted). Untreated, at k=16,384 about 4% of the support mazes would show the net a rotated copy of a panel maze. The plug-in never uses a turned view whose wall layout is in the dev or holdout set (it draws again from the allowed views; view 0, no turn, is always allowed). Selftest part A asserts no allowed view is a panel layout.

## Arms and controls
- Arms: practised loop + D4 and practised plain + D4, `--init pre`, seeds 0 and 1, on the qualified sources already on the Mac. Fresh nets are not run.
- Each arm is compared with **its own un-augmented row on main**, not retrained: loop `artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre/adapt.json`; plain `eq-runs/plain-s{0,1}-pre/adapt.json`. Loop control per seed = the **higher** of the loop's learned-stop and fixed-16 read (fair comparator). Plain has one read.
- Dev 9x9 fields `rungs[k]["9"]` (`right`, `fixed_right`) of 300, rungs k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384. `F_eq` = mean of the 8 rungs, `F_few` = mean of k = 1, 4, 16, 64, in points.

## Reference: the un-augmented rows (recounted from the four adapt.json, dev)
Loop F_eq learned / fixed-16: 51.21 / 49.83 (seed 0), 51.67 / 50.42 (seed 1); control value = 51.21, 51.67. Loop F_few: 12.42 / 11.83 and 14.75 / 14.58 (control 12.42, 14.75).
Plain F_eq: 34.04 (seed 0), 32.62 (seed 1). Plain F_few: 2.92, 1.25. Loop-minus-plain F_eq gap: +17.17 and +19.05.

## Validity (before any mark is read; failure = INVALID, nothing else claimed)
V1 arm and control agree on `weights`, `fixed_depth`, `lr`, `support_sha256`, `optimizer_updates_per_rung`, `rung_batches`. V2 2,048 updates per rung. V3 cold (k=0) 9x9 count and both old-kind "before" counts within 1 of the control's (same source net, so equal). V4 pool overlap with panels 0 and 16,384 unique layouts. V5 both selftests end with an ok line and `SEAL-code.sha256.txt` verifies, all committed before any run. `claude_s1_d4_marks.py judge` checks V1 to V4.

## Marks (Delta = D4 arm minus its own control, points)
- **G, the gain (the point of the test).** Loop `F_eq` Delta: mean of seeds 0 and 1 >= **+8.0** and each seed >= **+4.0**; OR loop `F_few` Delta: mean >= **+10.5** and each seed >= **+5.0**.
- **GAP, the loop keeps its lead.** With both arms turned, loop-minus-plain `F_eq` >= **17.2 - 3.3 = 13.9** in **both** seeds. This is the plain-net row: a plain net that catches up with the same trick cannot pass it (untested until run; the plain arm is run to make this row).
- **A2, few-example score not hurt** (its own required row, self-check 5). Loop `F_few` Delta >= **-8.5** in both seeds.
- Report-only, no mark: the 8-view plurality vote on the same nets at k = 64, 1,024, 16,384 and the number of the 300 dev mazes that get the same answer in all 8 views (`claude_s1_d4_vote.py`, `vote.json`); plain-arm Deltas and whether plain alone passes G's F_eq bar; 7x7 and 11x11; old-kind counts; both sleeps; the un-turned dev curves.

## Verdict words
1. **WORKS WITH A MAZE-SPECIFIC SHORTCUT:** G, GAP and A2 all pass and no WRONG reason holds.
2. **WRONG (in this form):** loop `F_eq` Delta < +4.0 in **both** seeds, OR the gap (control loop - plain, before) shrinks by more than 4.0 points in **both** seeds. This is the result that would prove the idea wrong.
3. **NOT SHOWN:** anything else (for example G fails in one seed only).
The words never say "general" or "kind-blind". If word 1 holds and plain alone also passes G's F_eq bar, the page adds "the trick helps plain too; loop lead kept only if GAP passes".

## MARKS SELF-CHECK (thread-helper-common.md), each point in this file
1. **Bars above noise.** Run-to-run noise: SD of a difference of two runs' means 3.33 (F_eq) and 4.17 (F_few), twice = 6.66 / 8.34, rounded to bars 7.0 / 8.5, from `artifacts/claude-dir-h12-stop-20260928/PASSMARKS.md` "Bars" (the baseline's two seeds; reproduced by `claude_dir_h12_marks.py`). G's mean bars **8.0 and 10.5 are above 7.0 and 8.5**. The per-seed floors +4.0 and +5.0 are below those bars: they are a consistency guard, not noise bars, and the mean bar carries the noise test.
2. **"Every seed" reading.** WRONG needs its condition in both seeds; a single gaining seed is NOT SHOWN; WORKS needs G, GAP and A2 in both seeds.
3. **Fair comparator.** Loop control = the higher of learned-stop and fixed-16 per seed (`control()` in the marks script). Plain has one read. No retrained baseline is used, so the sealed rows and this run share the same source nets, pool and batches.
4. **Plain-net row.** GAP (above). Memorising: the panel layouts are banned from the pool, and the leak guard also removes every turned view that equals a panel layout (655 and 674 views dropped, counted), so no panel maze in any orientation is trained on.
5. **F_few.** G's second route and its own required row A2.
6. **Sleep gates:** none. Sleep rows are report-only. If anyone later wants a gate it must be the mean of 3 sleep draws with margin max(6, 2 x SE).

## Order (fixed now)
1. Commit this file. 2. Commit plug-in, marks script, vote script, selftests, their logs and `SEAL-code.sha256.txt`. 3. Queue jobs `s1-loop-mac`, `s1-plain-mac` (Mac CPU, strict fp32, $0, no vast). GPU only after an fp32 equivalence smoke on the 5070 Ti, which is not part of this test. 4. `python -B scripts/claude_s1_d4_marks.py judge` prints every number and word; this page wins if they disagree. 5. A separate blind recount from raw JSON and this page only. 6. Nothing changes after any arm's dev score is seen; a job that dies is re-run unchanged, never edited.
