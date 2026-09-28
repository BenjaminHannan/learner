# Chat prompt: race the clip-on patch on the equal-practice ruler, practising on sums and grids like the sparse test (Thread manager, 2026-09-28T11:37:08Z)

Ben chose "Race like sparse" on the TM's decision card at 11:34 UTC, instead of the 16-run budget-v2 study (15 to 20 hours,
no maze verdict) or dropping patches. The TM checked on main: every arm of the six-kind run, both loop controls included,
missed the grids gate of 285 of 300 (artifacts/claude-patch-20260927/RESULTS.md); the equal-practice ruler passed V1-V3
(RESULTS-EQ.md, cad73c0c3); the sparse test practised on sums and grids only with the baseline's 12,000-batch recipe and
raced on that ruler (artifacts/claude-sparse-20260928/ADDENDUM-D1.md); Test A requires the loop control to get the same
episode training as the patch (RACE-PASSMARKS.md:7); the EQ harness makes 10 Learners per job (8 rungs plus sleeps after
k = 64 and 16,384) and refuses a rung without exactly 2,048 updates (scripts/claude_fewex_eq_bench.py:110-125), so the old
seven-phase adapter (scripts/claude_patch_plugin.py PHASES) and its writer-only ladder cannot run on it unchanged. Paste into
the SAME patches chat: it has the patch code and the machine. Everything below the line is the prompt.

---

Effort: high (Opus 5.5)

# Goal: race the clip-on patch against the loop on the new equal-practice ruler, with all practice on sums and grids only, exactly like the sparse test

**Why (read this first)**
- Your six-kind run failed its practice gate in every arm, your loop controls included, so no maze race ran. Ben chose not to run the 16-run budget study. He wants the patch raced the way the sparse test was raced.
- The ruler has changed since your run. ADDENDUM-4.md and RACE-ADDENDUM-1.md in artifacts/claude-fewex-20260927/ replaced the old ladder: every rung k = 1, 4, 16, 64, 256, 1,024, 4,096 and 16,384 now trains a clean copy for exactly 512 batches of 32 (2,048 updates), and `F_eq` (the mean 9x9 holdout accuracy over those 8 rungs) replaces `F_all` with the thresholds unchanged. The baseline passed V1-V3 (RESULTS-EQ.md, cad73c0c3): practised loop `F_eq` 51.00 and 51.29, practised plain 33.79 and 33.58.
- Read artifacts/claude-sparse-20260928/PASSMARKS-D.md, ADDENDUM-D1.md and RESULTS.md, and copy how that test was set up.

**The one change from your failed run**
- Practice kinds go back to sums and grids only, with the ruler's qualified recipe (ADDENDUM-3: 12,000 batches of 64, the ruler's own source seeds, the guard at SOURCE_SEED+300), the same recipe the baseline loop and the sparse loop had.
- The patch then gets your sealed 2,000 support-then-query episodes, built from sums and grids only. Everything else in the episode recipe stays as sealed.
- Nothing else about the patch changes: rank 8, the writer, the gate, the bounds, 1,652,767 coefficients.
- Train new source nets. Don't reuse the six-kind checkpoints, and leave budget-v2/ sealed and unrun.

**Arms (logical seeds 0 and 1, on the ruler's own support pools and panels)**
- **Patch**, practised as above.
- **Loop with episodes**, your episodic loop control, with the same 12,000 batches and the same 2,000 episodes adapted by ordinary gradient steps. Test A requires it (RACE-PASSMARKS.md:7). This is "the loop" for the +10 mark.
- **Fresh patch**, untrained, learning by ordinary gradient steps with the patch removed and the writer frozen, as before.
- **Plain net:** reuse the baseline's `eq-runs/plain-s{seed}-pre` runs. Don't retrain it; the sparse test did the same.
- **Report only:** the baseline's ordinary loop `eq-runs/loop-s{seed}-pre`, so Ben can see whether the episodes alone changed the loop.

**Adaptation on the ruler (the default I picked; write it into the marks)**
- On every rung, each maze batch is first written into the patch, then gets the same 4 ordinary updates as the loop. So every arm gets 2,048 ordinary updates per rung, and the patch also gets 512 writes. The old "writer only, weights frozen" rule can't run on this ruler, because each rung must make exactly 2,048 updates.
- The sleeps are unchanged: 512 updates with replay after k = 64 and after k = 16,384, and the patch is removed after sleep.
- **Report only, dev only:** the fast path alone. At k = 1, 4, 16 and 64, freeze the ordinary weights and make only the 512 writes, then score the 9x9 dev panel. Use a separate script, because the harness would refuse a rung with no updates.
- Build a new adapter, scripts/claude_patch_eq_plugin.py, for the ruler's 10 Learners per job. Name phases by their order only, never by puzzle kind. Keep the harness's plug-in contract, and never edit scripts/claude_fewex_eq_bench.py or the old plug-in.

**Marks (write artifacts/claude-patch-eq-YYYYMMDD/PASSMARKS.md and commit it before any practice run)**
Test A with RACE-ADDENDUM-1's substitution. Each seed is judged on its own, and seeds are never pooled.
- **Source guard, before any maze run:** the patch and the loop with episodes each get at least 190 of 200 on the guard's 4-digit sums and 5x5 grids, and every weight matrix gets a nonzero fp32 gradient. If either fails in either seed, report it and stop.
- **Pass, in both seeds:**
  - Patch `F_eq` is at least 10 points above the loop with episodes.
  - Patch `F_eq` is at least 5 points above the baseline plain net and above the fresh patch.
  - Old kinds before maze adaptation are at least 190 of 200 each and no more than 6 of 200 below the loop with episodes.
  - After both sleeps, each old kind is no more than 6 of 200 below that loop's same record.
  - Size stays within 2% of the loop's, counting every stored number.
- **Proved wrong (REJECTED):** patch `F_eq` no higher than the loop with episodes in both seeds (a tie counts as no higher), or a maze gain made only by breaking an old-kind gate.
- **Verdict words:** PASS, REJECTED, or NOT PROMOTED with the failing marks named.
- **Report only:**
  - E50, the 7x7 and 11x11 panels, and the fixed-depth check on every rung.
  - The baseline loop's `F_eq` against the loop with episodes.
  - The writer-only dev scores.
  - Old kinds after sleep with the patch removed.
  - Writes, updates, time and device.

**Order**
1. Commit the marks, the practice recipe (kinds, budget, the episode subset, seeds) and the adapter design.
2. Self-tests: a zero patch runs as the ordinary loop; a smoke rung reports exactly 2,048 updates; gradients are nonzero. Commit them.
3. Practise 4 source nets: patch and loop with episodes, 2 seeds each. Run the source guard.
4. Dev ladders: patch, fresh patch and loop with episodes, both seeds. Change nothing after any dev score is seen.
5. Score the holdout once with the harness's `holdout` command. Write RESULTS.md, with a blind recount by a separate subagent from the raw JSON and the marks only.

**Compute and money**
- Use this chat's own machine, $0, fp32 with no autocast, and the same device for every arm you train here. If that device is not the CPU, first show on a smoke rung that it matches the CPU in fp32, as ADDENDUM-4's GPU rule asks, and record it.
- My estimate (untested) is 6 to 10 hours. Run long jobs in the background and don't poll.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push.
- New files only: scripts/claude_patch_eq_*.py and artifacts/claude-patch-eq-YYYYMMDD/. Don't edit the ruler's files, the sparse test's files, your own earlier sealed files or the repo-root notebook/.
- Training data is code-made only. There are no mazes in practice.
- Times in files come from `date -u`. Stop processes by exact PID. Never touch secrets.
- Label claims shown, suggested or untested. Give counts as "x of 300" or "x of 200".

**Done means**
- Marks, code, self-tests, source guard, dev and holdout records, and RESULTS.md with the verdict and the recount, all pushed to main.
- Final report for Ben, 10 lines at most, plain words, result first:
  - Does the patch learn mazes from fewer examples than the loop given the same episodes?
  - Does it keep sums and grids after sleep?
  - What does the fast path do on its own, with no weight changes?
  - Did the episodes help the ordinary loop?
  - Time and money.
  - Commit hashes.
