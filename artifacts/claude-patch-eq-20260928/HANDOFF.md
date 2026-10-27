# Handoff: the patch race on the equal-practice ruler

Written 2026-09-28 21:22 UTC (`date -u`) by the outgoing director, on Ben's instruction to stop and hand
over. **Nothing has been scored on a maze.** No dev score and no holdout score of this test exists. All marks are
sealed and unchanged. Read this file, then PASSMARKS.md, DESIGN.md and ADDENDUM-1.md in this folder.

## 1. The task, in one paragraph
Race Ben's "clip-on patch" (a rank-8, feedback-written fast-weight patch on the recurrent loop) against the
ordinary loop on the equal-practice few-example ruler (artifacts/claude-fewex-20260927: ADDENDUM-4.md,
RACE-ADDENDUM-1.md, harness scripts/claude_fewex_eq_bench.py). All practice is on sums and Latin grids only,
exactly like the sparse test (artifacts/claude-sparse-20260928). Test A: patch `F_eq` at least 10 points above the
**loop with episodes** in **both** seeds (plus the other marks in PASSMARKS.md). The originating prompt is
reviews/chat-prompt-patches-eq-race-2026-09-28.md; it is the authority for scope and the final report.

## 2. State at handoff (all shown, from files in this folder)
| Step | State | Evidence |
|---|---|---|
| Marks, practice recipe, adapter design | done, sealed | PASSMARKS.md, DESIGN.md at `948652576` |
| Self-tests (zero patch = ordinary loop; fresh learner bit-identical to the harness's; identical episodes for both arms; all matrices live; smoke rung = 512 writes and exactly 2,048 updates; sleep ends with the patch removed) | done | selftest.json / .log at `f49711b3f` |
| Practice of 4 source nets (patch and loop with episodes, seeds 0 and 1) | done | runs/*/source.json, `e66daf091` |
| Source guard | **passed**: all four nets 200 of 200 sums and 200 of 200 grids; 20 of 20 (patch) and 16 of 16 (loop) matrices live | same |
| Resumable ladder driver | done and checked bit-identical to an uninterrupted run and to the harness's own loop | ADDENDUM-1.md, ladder-selftest-*.json, `a970243bd` |
| Dev ladders (6) and fast path (2) | **not started as a record.** Two earlier launches were killed by container restarts; a third was stopped by Ben's instruction about one minute after launch (21:20 UTC). eq-runs/ is empty. | this file |
| Holdout, RESULTS.md, blind recount, final report | not started | |

Practice numbers worth knowing (report only; nothing depended on them): source-selected fixed depths are
patch 48 / 8 and loop-with-episodes 8 / 32 (seed 0 / seed 1). Learned-stop guard was also 200 of 200 on both kinds
for every net after the 12,000 batches, before the episodes. Practice took 7,660-8,313 s per net (four at once, one
thread each). The trained patch's factor norms are about 0.09-0.10 against the sealed bound of 1.0 (Frobenius);
that says nothing about whether the patch helps.

## 3. Where things are
- Marks and design: PASSMARKS.md, DESIGN.md, ADDENDUM-1.md (execution only; no mark changed).
- Code, all new files: scripts/claude_patch_eq_{plugin,fresh,practice,selftest,ladder,fastpath,report}.py and the
  launchers scripts/claude_patch_eq_{practice,dev}_queue.sh. The ruler's harness and the old patch files are untouched.
- Source nets: artifacts/claude-patch-eq-20260928/runs/{patch,loop_ep}-s{0,1}/source.pt (6.6 MB each). `artifacts/`
  is gitignored, so **they are not on main.** checkpoints-sha256.txt records their hashes. To keep them, the
  outgoing director also pushed the four `source.pt` files, and only those, to the branch
  `claude/funny-heisenberg-ot316m` (see section 8). If both the checkout and that branch are lost, retraining is
  deterministic but takes about 2.5 h per net, and the hashes are the check.
- Baseline arms you reuse, not retrain: artifacts/claude-fewex-20260927/eq-runs/{plain-s{0,1}-pre,loop-s{0,1}-pre}.
  Their `adapt.json` and `holdout.json` are on main; `eq-runs/loop-*` is report-only.

## 4. How to continue (in order; change nothing about the recipe)
Setup on a fresh machine: `pip install torch==2.14.0+cpu --index-url https://download.pytorch.org/whl/cpu numpy`
(fp32 CPU, no autocast, same device for every arm; the sparse test and baseline were CPU). Clone main. Restore the
four `source.pt` files under runs/ (verify sha256) if they are not present.

1. **Dev ladders and fast path:** `bash scripts/claude_patch_eq_dev_queue.sh` (4 jobs at a time, 1 thread each; jobs
   are patch-s0/s1, fresh-s0/s1, loopep-s0/s1, fast-s0/s1; logs in logs/, queue line in dev-queue.log). It is
   idempotent: after any restart, run it again and each job resumes from its 32-batch checkpoint; finished jobs are
   skipped. Watch for `adapt_done` lines and for `Traceback`. Nothing may change after any dev score is seen.
2. `python -B scripts/claude_patch_eq_report.py dev` prints dev tables (race-dev.json). Commit the dev records
   (eq-runs/*/adapt.json and partial/ck-free files, fastpath-dev-s*.json, race-dev.json) **before** the holdout.
3. **Holdout, once**, per arm and seed, with the harness's own command and the same `--plugin`, `--arm loop`,
   `--seed`, `--init`, `--out` as the ladder: patch = `--plugin claude_patch_eq_plugin --init pre --out
   eq-runs/patch-s$S`; fresh = `--plugin claude_patch_eq_fresh --init fresh --out eq-runs/fresh-s$S`; loop with
   episodes = default plug-in, `--init pre`, `--out eq-runs/loopep-s$S`. It refuses unless
   claude-fewex-20260927/EQ-DEV-GATE.json says PASS (it does) and drops a `holdout.started` marker, so never re-run a
   partial holdout job silently; if one dies, tell Ben and decide together.
4. `python -B scripts/claude_patch_eq_report.py holdout` applies PASSMARKS.md and writes race-holdout.json with the
   verdict (PASS / REJECTED / NOT PROMOTED, failing marks per seed). It was tested on the baseline's JSON as
   stand-ins: it reproduces the baseline's 51.00 and 51.29 and the sleep counts.
5. Write RESULTS.md (verdict, main table x of 300, old kinds x of 200, gates per seed, report-only items listed in
   PASSMARKS.md, fast-path dev table, timings, deviations including the restarts and the driver). Get a **blind
   recount** from a separate subagent that reads only the raw JSON and PASSMARKS.md. Push to main.
6. Final report to Ben, 10 lines at most, plain words, result first (the six questions are at the end of the
   originating prompt), with commit hashes.

## 5. Time
Measured, not guessed. On this 4-core CPU with four one-thread jobs at once: one patch maze rung about 65 minutes
(4.7 s per maze batch alone, against 3.1 s for the loop), so a patch ladder is roughly 9-10 hours plus sleeps and
scoring; a fresh-patch rung took about 33 minutes (k = 1); a loop-with-episodes ladder is expected near the fresh
one (untested). Eight jobs in two waves: **expect 15 hours or more**, longer than the first estimate of 6-10 h.
More cores would help, since the jobs are independent. A GPU would need the strict fp32 CPU-equivalence smoke result
that ADDENDUM-4's GPU rule asks for, recorded before any maze score.

## 6. Decisions already made (do not reopen without Ben)
- Adaptation per rung: each maze batch is written into the patch once (mean of the batch's per-puzzle
  proposals, one blend), then gets the loop's four ordinary updates: 512 writes and 2,048 updates. Sleep is the
  harness's 512 updates with the patch fixed, patch zeroed afterwards. Fresh patch: never written, writer frozen.
- Loop with episodes: same 12,000 batches and same 2,000 episodes (second-order inner SGD, lr 0.01), run through the
  ruler's own loop class. It was trained with claude_patch_net's `loop` (same parameter names and shapes; explicit
  attention); a strict load into the ruler's class gives logits equal to about 7e-7, not bit-equal. Tell the reader.
- "The loop" in every mark is the loop with episodes. The baseline loop is report-only.
- The seed pool, panels, replay, learning rates and thresholds are the ruler's; the report script reads them.

## 7. Things I would watch (suggested, untested)
- Patch and fresh patch share a random init under the harness seed (900000 + seed); a fresh loss of ground would
  show up as low `F_eq` for the fresh arm, as the sparse test's fresh arm did.
- If the patch's dev curve is flat across all rungs, the write may not matter at this scale; the fast-path dev
  table (frozen weights, 512 writes only) is where that shows. Report it plainly either way.
- The old six-kind run is closed; do not reuse its checkpoints or budget-v2/ (sealed, unrun).

## 8. Practical traps
- The container has restarted three times; every process died each time. Use the idempotent launcher, relaunch
  after a restart notice, and never trust a background job across one.
- Local `main` in this checkout is a stale ref of a shallow clone. Work from the checkout and push with
  `git pull --rebase origin main && git push origin HEAD:main`. Never force-push. `git checkout -B main ...` was
  denied by the harness's classifier; don't try to work around that.
- Session branch: `claude/funny-heisenberg-ot316m` carries the same commits as main plus one extra commit holding
  the four `source.pt` files (added with `git add -f`). Ben's prompt says commit to main, no PRs; the branch is
  only a safe copy. No PR was opened.
- Times in files come from `date -u`; stop processes by exact PID; never touch secrets; label claims shown,
  suggested or untested; counts as "x of 300" / "x of 200". CLAUDE.md asks for a plain-language summary for Ben
  (a high-school senior) in every result.
- Money so far: $0. Nothing was rented.
