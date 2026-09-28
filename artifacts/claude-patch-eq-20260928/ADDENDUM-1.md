# Addendum 1: a resumable driver for the dev ladders (execution only; no mark, recipe or score changes)

Written 2026-09-28 21:19 UTC (`date -u`), before any maze dev score of this test exists.

**What happened.** The container running this test restarted twice during the first hours of the dev ladders
(about 20:2x UTC and 21:1x UTC, killing every process). The harness's `adapt` has no resume and a patch ladder
takes many hours. The first two launches produced no finished rung score that was read; their partial files
were moved out of the artifact folder and are not used. The first launch's log showed one rung training time
(patch seed 0, k = 1: 3,922 s with four jobs on four cores).

**What changed.** DESIGN.md's dev commands now run scripts/claude_patch_eq_ladder.py instead of
`claude_fewex_eq_bench.py adapt`. It calls the harness's own functions unchanged (pool, batches, the plug-in
Learner, maze_scores, the same assertions and output files) and only adds checkpoints: a training checkpoint
every 32 batches inside a rung, and finished rungs kept. The harness's `holdout` command is still the one that
scores the holdout, from the same `k*.pt` and `sleep*.pt` files and adapt.json. The loop with episodes also runs
through this driver (with the ruler's own plug-in), so all three arms share one execution path. The fast-path
script keeps finished rungs on restart.

**Check (ladder-selftest-patch.json, ladder-selftest-loop.json).** For the patch learner and for the loop
learner, a rung interrupted after 3 of 6 batches and resumed has bit-identical weights to an uninterrupted run,
and both are bit-identical to the harness's own loop over its own `batches()`. Nothing in the computation uses a
global RNG. Wall-clock training seconds in adapt.json are summed across restarts; `interruptions` counts them.
