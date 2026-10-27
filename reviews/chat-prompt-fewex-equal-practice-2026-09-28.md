# Chat prompt: fix the few-example ruler with equal practice per rung (Thread manager, 2026-09-28T01:54:47Z)

Ben pasted the ruler's INCONCLUSIVE result at 01:52 UTC (c0d023346) and asked at 01:53:24 UTC for prompts that can run overnight.
The TM checked the code: each few-example rung trains for 8 passes of batches of at most 32, and every batch does UPDATES = 4
optimizer steps (scripts/claude_fewex_bench.py:28, :267-271, :187-193). So k = 1, 4 and 16 each get 32 updates and k = 64 gets
64, while the stream's 4,096 point has had 512 and its 16,384 point 2,048. The ruler therefore mixes "how many different mazes"
with "how much practice". Best pasted into the SAME chat that ran the ruler, because the qualified source nets are on its machine.
Everything below the line is the prompt.

---

Effort: high (Opus 5.5)

# Goal: fix the few-example ruler so every rung gets the same amount of practice, then run the baseline again and, if the new ladder is usable, open the holdout once

**Why (read this first)**
- Your ruler came back INCONCLUSIVE (c0d023346): V1 and V2 passed, V3 failed, and the holdout is still unopened. That was the right call.
- Look at how much practice each rung got (check it in scripts/claude_fewex_bench.py:28, :187-193 and :267-271). k = 1, 4 and 16 got 32 optimizer updates each and k = 64 got 64, but the stream had 512 updates by 4,096 mazes and 2,048 by 16,384. So the cliff between 1,024 and 4,096 may be about practice, not about how many different mazes the net saw (suggested, not tested).
- Ben's main measure is how few **different** examples a new kind needs. To measure that, every rung needs the same practice.

**The one change**
- New ladder: k = 1, 4, 16, 64, 256, 1,024, 4,096 and 16,384 different 9×9 layouts, nested, drawn from one sealed support pool with no overlap with the panels.
- Every rung starts from a clean copy of the starting net and trains for exactly **512 maze batches of 32 (2,048 optimizer updates)**, the same practice the old stream had at 16,384. For k under 16,384, batches cycle through the k mazes in shuffled order, so each one is used about equally often. For k under 32, a batch repeats mazes to fill 32.
- This number is fixed now. Don't tune it.
- Keep everything else from the protocol: the four arms (practised and fresh loop, practised and fresh plain), seeds 0 and 1, the same qualified source nets (reuse them, don't retrain), the learning rates and the plain rate chosen before, the dev and holdout panels, the learned stop and fixed-depth check, scoring, and old-kind scoring.
- Sleep branches: run them after the k = 64 rung and after the k = 16,384 rung (this replaces the 65,536 branch), with the unchanged sleep recipe.
- Put this in a new file, scripts/claude_fewex_eq_bench.py, reusing the old harness's pieces. Never edit the old harness. Keep the plug-in contract exactly (`--plugin`, Net, Practice, an optional Learner with `maze_batch`), so the relation net, patches and sparse loop plug-ins run unchanged.

**Order**
1. Write artifacts/claude-fewex-20260927/ADDENDUM-4.md and commit it before any new maze score. It needs:
   - the change above;
   - the new score F_eq, the mean 9×9 accuracy over the 8 rungs;
   - E50, the smallest rung reaching 50% (report only);
   - V3 with the same wording on the new rungs: at least one arm in at least one seed has at least 3 of the 8 rungs strictly between 10% and 90% on dev, or INCONCLUSIVE and stop;
   - a disclosure that this addendum was written after seeing the old ladder's dev scores, and that the holdout is untouched.
2. Write artifacts/claude-fewex-20260927/RACE-ADDENDUM-1.md and commit it in the same commit. In every race mark, F_eq replaces F_all, with the thresholds unchanged. No design has seen a maze score yet, so this is allowed. Say so, and name the commit.
3. Run the dev ladder for all 4 arms and both seeds. If V3 fails, report INCONCLUSIVE and stop.
4. If V3 passes, score the holdout once, for all arms and both seeds. Write RESULTS-EQ.md, with a blind recount by a separate subagent from the raw JSON and the marks only.

**Compute**
- If CPU would not finish by 12:00 UTC, first write a GPU addendum like the relation net's (strict fp32, TF32 off, shown equal to the CPU on a smoke run) and commit it before any maze score. Then use at most one rental job, capped at $4.
- Destroy an instance only after a checked copy-back, otherwise stop it. Never read or print the vast key or any auth file. Never stop another agent's rental.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push. New files only, and never touch the repo-root notebook/.
- Times in files come from `date -u`. Stop processes by exact PID.
- Label claims shown, suggested or untested. Give counts as "x of N".
- Save usage: run long jobs in the background, don't poll, and skip status chatter.

**Done means**
- ADDENDUM-4, RACE-ADDENDUM-1, the dev ladder, and if V3 passes the holdout and RESULTS-EQ.md, all pushed to main.
- Final report for Ben, 10 lines at most, plain words, result first:
  - Is the new ruler usable?
  - How many different mazes does the practised loop need to reach 50%, against the fresh loop and the plain net?
  - Did old kinds survive sleep?
  - Time and money.
  - Commit hashes.
