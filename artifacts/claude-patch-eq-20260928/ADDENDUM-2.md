# Addendum 2: seven fixes from the independent review (marks and report only; recipe, practice and code of the arms unchanged)

Written 2026-09-28 21:31 UTC (`date -u`) by helper H13, who took the race over from the outgoing director. **Nothing has been scored on a maze:**
`artifacts/claude-patch-eq-20260928/eq-runs/` does not exist yet, so no dev score and no holdout score of this test exists. This file and its
report script (scripts/claude_patch_eq_report_add2.py, tested by `selftest` below) are committed before any maze rung is
scored. Nothing here changes after any dev score is seen. PASSMARKS.md and ADDENDUM-1.md stay as written; where this file says
otherwise, this file wins. Source of the fixes: artifacts/claude-dir-h8-review-20260928/REVIEW.md (X1-X4, P1-P4) and
reviews/chat-prompt-patches-review-fixes-2026-09-28.md. I checked each finding against the code and the raw files (below);
**none is rejected.**

## The seven changes
1. **X1, sleep gates.** The old-kind gates after the k=64 and k=16,384 sleeps compare three-draw means, not single draws.
   Draw 0 is the ladder's own sleep (in adapt.json); draws 1 and 2 use sleep seed `seed + k + 101` and `seed + k + 202`, the same
   offsets as scripts/claude_fewex_distill_sleep.py, from the ladder's saved `k64.pt` / `k16384.pt`, run by
   scripts/claude_patch_eq_add2_sleepdraws.py for **both** the patch and the loop with episodes. Per seed, branch and kind:
   the patch's three-draw mean must be at least the loop's three-draw mean minus `max(6, 2 x SE)`, where
   `SE = sqrt(sd_patch^2/3 + sd_loop^2/3)` (sample SDs of the three draws). Mark 3's "before adaptation" gates (at least 190 of 200; within 6 of the loop) have no draw noise (one fixed checkpoint, scored once) and stay as sealed.
   *Checked (shown):* the distill run's R128 sleeps give s0 k64 sums 174, 158, 134 and grids 104, 104, 94; s1 k16,384 sums 42, 69, 43 (recounted from artifacts/claude-distill-20260928/sleeps/*.json). A sealed single-draw margin of 6 is smaller than that spread.
2. **X2, the words.** "A maze gain made only by breaking an old-kind gate" is REJECTED **only if there is at least one gaining seed and EVERY gaining seed breaks an old-kind gate** (as PASSMARKS.md said and claude_patch_eq_report.py:121-124 already did). One seed that gains and passes every gate stops this rejection. A "gaining seed" is one whose `F_eq` is above the comparator of change 3. Old-kind gates here are marks 4a, 4b and 6 below.
3. **P1, the comparator.** "The loop" in marks 1 and 2 and in every REJECTED reading is the **higher of** the loop with episodes and the baseline ordinary loop (`eq-runs/loop-s{seed}-pre` in the ruler: 51.00 / 51.29 `F_eq`, RESULTS-EQ.md). Mark 1 is patch `F_eq` at least +10 over that. Marks 3b onward still use the loop with episodes only where they say so.
4. **P2, writes off.** One extra dev ladder per seed and one holdout: the practised patch net with `Net.WRITES = False` (scripts/claude_patch_eq_writesoff.py, `--init pre`, source runs/patch-s{seed}); same rungs and the same ordinary updates per rung as the patch, but no writes. Report only, no gate. Wording rule fixed now: "the writes helped" may be said only if the patch is at least 5 points above the writes-off arm on `F_eq` in **both** seeds; otherwise "not shown". The same is reported for `F_few`.
5. **X3, few examples.** `F_few` = mean over k = 1, 4, 16, 64 of 100 x right / 300 on the 9x9 holdout, learned stop. **New required mark 2:** patch `F_few` at least +5 over the higher of the loop with episodes and the baseline loop, in both seeds. `F_few` is quoted next to `F_eq` in the verdict sentence. (+5 because a real few-example gain of +12 on four rungs is ~+6 on the eight-rung mean, and the review's bar was "+5 over the loop".)
6. **X4, non-wins.** A non-PASS is "NOT PROMOTED (not shown)" unless **both seeds are at least 2 points below** the comparator on `F_eq`, which is REJECTED. This replaces "no higher than the loop in both seeds". The per-seed differences are printed next to the verdict.
7. **P3, P4.** The verdict sentence says "at 1.5x the compute" (measured 4.7 s against 3.1 s per maze batch, DESIGN.md; write rounds are in adapt.json). Old-kind scores after each sleep **with the patch kept** (scored just before the sleep zeroes it) are report only, from the patch's sleep draws 1 and 2 (`old_patch_kept_report_only`).

## Marks as they now stand (each seed on its own, never pooled)
1. `F_eq`: patch at least +10 over the higher of loop-with-episodes and baseline loop.
2. `F_few`: patch at least +5 over the same comparator.
3. `F_eq`: patch at least +5 over the baseline plain net and at least +5 over the fresh patch.
4. Old kinds before maze adaptation: at least 190 of 200 each (4a), and no more than 6 of 200 below the loop with episodes on each kind (4b).
5. Size within 2% of the loop with episodes.
6. After the k=64 and after the k=16,384 sleep, each old kind: three-draw patch mean not below the three-draw loop-with-episodes mean by more than `max(6, 2 x SE)`.
**PASS** = marks 1-6 hold in both seeds. **REJECTED** = both seeds at least 2 points below the comparator on `F_eq` (change 6), or a gain made only by breaking (change 2). Otherwise **NOT PROMOTED (not shown)**.
Report only: everything listed as report only in PASSMARKS.md, the writes-off comparison (change 4), the patch-kept sleep scores (change 7), the fast path, `F_eq`/`F_few` of every arm.

## What changes in what runs
- New jobs on top of the sealed ladder driver (unchanged): writes-off ladder per seed (2 jobs); sleep draws 1 and 2 for patch and loop with episodes, per seed and branch (16 jobs, about 5-10 minutes each on one thread, untested for the patch: a 4-step smoke test of both arms ran, 38 s and 24 s).
- Holdout: harness `holdout`, once per arm and seed, now also for the writes-off arm (`--plugin claude_patch_eq_writesoff --init pre --out eq-runs/writesoff-s$S`).
- The report script is scripts/claude_patch_eq_report_add2.py (`dev`, `holdout`, `selftest`). The old scripts/claude_patch_eq_report.py is not used for the verdict.

## Reproduction (the addendum's own pass marks), 2026-09-28 21:31 UTC
`python3 -B scripts/claude_patch_eq_report_add2.py selftest` -> add2-selftest.json in this folder (fake numbers; checks words and arithmetic, not any model). Pass: it prints "all_expected": true, meaning
(a) with one seed that gains and breaks a gate and one that gains and passes, the every-reading prints NOT PROMOTED (not shown) and the any-reading (not used) would print REJECTED; (b) both gain and both break -> REJECTED; (c) both gain and pass -> PASS; (d) one seed slightly below and one above -> not shown; both at least 2 below -> REJECTED; (e) a patch equal to the loop with one noisy sleep draw (-12) fails the old single-draw rule but passes the three-draw rule; (f) the sentence contains "1.5x the compute". The script's real-data path was also run on the ruler's baseline JSON as stand-ins for the arms (no patch data exists).
