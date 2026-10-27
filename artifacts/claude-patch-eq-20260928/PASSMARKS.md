# Test A on the equal-practice ruler: the clip-on patch, practised on sums and grids like the sparse test

Written 2026-09-28 16:05 UTC (`date -u`), before any practice run of this test and before any maze dev or
holdout score of the patch. No mark changes after this file is committed. Design and recipe: DESIGN.md.

These are RACE-PASSMARKS.md Test A with RACE-ADDENDUM-1.md's substitution (`F_all` -> `F_eq`, the 64k
sleep -> the 16,384 sleep), thresholds unchanged. Each seed is judged on its own; seeds are never pooled.

## Arms (logical seeds 0 and 1, the ruler's own support pools and panels)
- **Patch**: practised (DESIGN.md), run with `--plugin claude_patch_eq_plugin --init pre`.
- **Loop with episodes** ("the loop" for every mark below): the ruler's loop given the same 12,000 batches
  and the same 2,000 episodes, adapted by ordinary gradient steps (Test A's required control,
  RACE-PASSMARKS.md). Run with the ruler's own loop and learner.
- **Fresh patch**: untrained patch net, never written, writer frozen, ordinary gradient steps
  (`--plugin claude_patch_eq_fresh --init fresh`).
- **Plain net**: the baseline's `eq-runs/plain-s{seed}-pre` (adapt.json, holdout.json). Not retrained.
- **Report only**: the baseline's ordinary loop `eq-runs/loop-s{seed}-pre`.

## How the numbers are read (fixed now)
- `F_eq`: from the harness's holdout.json, the mean over k = 1, 4, 16, 64, 256, 1,024, 4,096 and 16,384 of
  100 x right / 300 on the 9x9 holdout, learned stop. Differences are percentage points.
- "Old kinds before maze adaptation" is the harness's `old.before` (200 sums4, 200 grids5). "After both
  sleeps" is `sleep.64.old` and `sleep.16384.old` (patch removed). Being above the loop always passes.
- Size: every stored number (parameters plus the 4,096 A/B coefficients), from `weights` in adapt.json.
- The marks are computed by scripts/claude_patch_eq_report.py, committed with this file.

## Source guard (before any maze run)
In each seed, the practised patch and the practised loop with episodes each get at least 190 of 200 on the
guard's 4-digit sums and at least 190 of 200 on its 5x5 grids (seed SOURCE_SEED+300), and every
two-dimensional weight matrix gets a nonzero fp32 gradient on a sums or a grids batch (the harness's
check). If either fails in either seed: report it and stop. No maze run.

## Pass, in both seeds
1. Patch `F_eq` at least **10 points above the loop with episodes**.
2. Patch `F_eq` at least 5 points above the baseline plain net, and at least 5 above the fresh patch.
3. Old kinds before maze adaptation at least 190 of 200 each, and no more than 6 of 200 below the loop with
   episodes on each kind.
4. After the k=64 sleep and after the k=16,384 sleep, each old kind no more than 6 of 200 below the loop
   with episodes' same record.
5. Size within 2% of the loop's, counting every stored number (1,652,767 vs 1,645,726: +0.43%).

## Proved wrong (REJECTED)
- Patch `F_eq` no higher than the loop with episodes in both seeds (a tie counts as no higher); or
- a maze gain made only by breaking an old-kind gate: in every seed where the patch's `F_eq` is above the
  loop with episodes, at least one of marks 3-4 fails. (Mazes are compared through `F_eq` only, as the
  sparse test read it.)

## Verdict words
PASS if marks 1-5 hold in both seeds. REJECTED if a proved-wrong condition holds. Otherwise NOT PROMOTED,
with the failing marks named per seed.

## Report only (no gate)
- E50 (smallest rung with at least 150 of 300 on 9x9), the 7x7 and 11x11 panels, and the source-selected
  fixed-depth check on every rung (a learned-stop score more than 2 points below it is a stop failure),
  mean rounds and cap hits.
- The baseline ordinary loop's `F_eq` against the loop with episodes (did the episodes change the loop?).
- The fast path alone (dev only): writes with frozen weights at k = 1, 4, 16, 64 (DESIGN.md).
- Old kinds after each sleep with the patch removed, and D per kind.
- Writes, updates, practice and adaptation time, device, threads.
- The learned-stop guard counts after the 12,000 batches, before the episodes.

## Order
1. Commit these marks, DESIGN.md (practice recipe and adapter design) and the code.
2. Self-tests (selftest.json): a zero patch runs as the ordinary loop; a smoke rung reports exactly 2,048
   updates and 512 writes; gradients are nonzero. Commit them.
3. Practise four source nets (patch and loop with episodes, seeds 0 and 1); run the source guard; commit.
4. Dev ladders: patch, fresh patch, loop with episodes, both seeds; the fast path. Nothing changes after any
   dev score is seen. Commit the dev records before the holdout.
5. Score the holdout once with the harness's `holdout` command. RESULTS.md with the verdict and a blind
   recount by a separate subagent that reads only the raw JSON and these marks.
