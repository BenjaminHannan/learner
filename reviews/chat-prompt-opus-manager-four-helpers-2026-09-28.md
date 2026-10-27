# Chat prompt: one Opus manager with four Sonnet helpers, one per open problem (Thread manager, 2026-09-28T18:38:26Z)

Ben asked at 18:35-18:36 UTC for simultaneous chats, then: "An opus chat manages four sonnet subagents working on each of
those things. Give me a prompt for the opus chat". The four problems are the ones on the TM's 18:2x list: the relation net
race on the equal-practice ruler, why no net learns the numbers puzzles, the vector reader's wrong-person slip, and the
sleep test's official write-up. The TM checked the facts below on main: RACE-PASSMARKS.md:5 and :11 (common gates, Test C),
RACE-ADDENDUM-1.md, the sparse test's ADDENDUM-D1.md (the template for a plug-in race on the new ruler); relnet passed its
practice gate on a GPU with its own recipe, not the ruler's (artifacts/claude-relnet-20260927/RESULTS.md), and
scripts/claude_relnet_net.py has no harness plug-in yet; numbers4 scored 0-3 of 300 on all 8 runs
(artifacts/claude-rsn358u-20260927/RESULTS.md:12); Astra's wrong-person numbers are in
reviews/astra-diagnose-vread-backref-2026-09-28.md; slp-358n3's records are only on origin/builder-outbox. Paste into a NEW
cloud chat: none of the four needs another chat's saved files. Everything below the line is the prompt.

---

Effort: high (Opus 5.5)

# Goal: work four open problems at once. You manage; four Sonnet helpers each take one problem.

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first. Ben, a high-school senior, reads your final report.
- You are the manager. Start four helper subagents at once, on the Sonnet model, one per problem below. Each helper sees only the brief you give it, so paste its whole section below into its brief, together with the shared rules.
- Your job:
  - Start them.
  - Answer their questions.
  - Check every factual claim they report against the code and the raw files before you accept it.
  - Have each result blind-recounted by a separate subagent that sees only the raw files and the marks.
  - Write the final report.
- Don't redo a helper's work yourself. If a helper gets stuck or goes off its brief, send it back with a correction. Restart it only if that fails.
- **Long jobs:** start them as detached background processes (`nohup` or `setsid`, with logs in the helper's own folder) so they outlive the helper. Check each job once, when it is expected to finish, and don't poll.

**Shared rules (give these to every helper)**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push. If a push conflicts, pull again and retry. Never edit another helper's files.
- New files only, in your own folder and with your own script prefix (given in your section). Never edit sealed files, other tests' files or the repo-root notebook/.
- If your task has marks, commit them before any run they judge.
- fp32 on CPU, $0, no rentals, no downloads.
- Training data is code-made only; never text an AI wrote.
- Never open readpanel320 or any other blind panel. Use fictional names only when quoting chats.
- Times in files come from `date -u`. Stop processes by exact PID. Never read or print keys, tokens or auth files.
- Label every claim shown, suggested or untested. Give counts as "x of N".
- Proposals follow CLAUDE.md: one change at a time, pass marks fixed in advance, and the result that would prove it wrong. Keep the small card experiments and the village model out of it.
- Report back to the manager in 12 lines or fewer, with commit hashes.

## Helper R: race the relation net on the new ruler (prefix scripts/claude_relnet_eq_*, folder artifacts/claude-relnet-eq-YYYYMMDD/)
- **Why:** Ben's main measure is how few examples a new kind needs. The equal-practice ruler passed V1-V3 (artifacts/claude-fewex-20260927/RESULTS-EQ.md, cad73c0c3): practised loop `F_eq` 51.00 and 51.29, practised plain 33.79 and 33.58. The sparse loop raced on it and was NOT PROMOTED. The relation net passed its practice gate last night, but on a GPU with its own recipe, so it has not raced yet.
- **Copy the sparse test's setup exactly.** Read artifacts/claude-sparse-20260928/PASSMARKS-D.md, ADDENDUM-D1.md and RESULTS.md, and scripts/claude_sparse_net.py and claude_sparse_practice.py. Then read artifacts/claude-relnet-20260927/ (GATE-PASSMARKS.md, RESULTS.md, REVIEW.md) and scripts/claude_relnet_net.py.
- **The one change:** the loop becomes the relation net, unchanged (1,644,198 weights). Write a plug-in, scripts/claude_relnet_eq_plugin.py, that meets the harness's plug-in contract the way the sparse plug-in does. Never edit scripts/claude_fewex_eq_bench.py.
- **Practice:** the ruler's qualified recipe (ADDENDUM-3: 12,000 batches of 64, the ruler's source seeds, the guard at SOURCE_SEED+300), seeds 0 and 1. Don't reuse last night's GPU nets. Source guard: at least 190 of 200 on sums4 and grids5, and every weight matrix gets a nonzero fp32 gradient. If either fails, report it and stop.
- **Race:** `claude_fewex_eq_bench.py adapt --plugin <yours> --init pre` and `--init fresh`, seeds 0 and 1. Dev first, change nothing after a dev score, then the holdout once with the harness's `holdout` command. Compare with the baseline's `eq-runs/loop-s{seed}-pre` and `eq-runs/plain-s{seed}-pre` (not retrained).
- **Marks (PASSMARKS-C.md):** Test C (RACE-PASSMARKS.md:11) with RACE-ADDENDUM-1's `F_eq`, and the common gates (:5) read as ADDENDUM-D1 reads them.
  - `F_eq` at least 10 points above the loop in both seeds.
  - At least 5 above the plain net and above the relation net's own fresh copy.
  - Old kinds at least 190 of 200 before mazes, and no more than 6 of 200 below the loop before mazes and after both sleeps.
  - Size within 2%.
  - **Proved wrong:** `F_eq` no higher than the loop in both seeds, or a maze gain made only by breaking an old-kind gate.
- **Report only:** E50, the 7x7 and 11x11 panels, mean rounds, the fixed-depth check, and whether last night's decay at a forced 48 rounds on sums shows up.
- **Time:** the sparse race took about 75 minutes of practice per seed and about 3 hours of ladders on CPU. Run the jobs detached.

## Helper T: why no net learns the numbers puzzles (read-only diagnosis; folder artifacts/claude-numbers-diag-YYYYMMDD/, prefix scripts/claude_numbers_diag_*)
- **The problem (shown):** in rsn-358i3 and rsn-358u (8 runs, loop and plain), sums4 and grids5 reach 300 of 300, but numbers4 stays at 0 to 3 of 300 (artifacts/claude-rsn358u-20260927/RESULTS.md:12). A numbers puzzle means using each given number once with + − × ÷ to hit a target, with the answer written in postfix (scripts/claude_rsn358a_envs.py:11-14; solver and checker in scripts/claude_blurt1.py).
- **Find out why.** Candidates to check, not conclusions:
  - Many hands have several right answers. Is the net trained toward one stored answer while being graded on that same one, or on any valid answer?
  - How often is the net's output a valid expression? How close are the near-misses?
  - Is the answer format hard for a one-shot-per-cell output head?
  - How much of practice went to this kind?
  - Is the loop's thinking time used at all on these puzzles?
- **Allowed:** reading code, results and saved outputs; CPU scripts that compute statistics from existing files or from the generator; CPU inference with saved nets if they are on this machine.
- **Not allowed:** training, edits to existing files, or GPUs.
- **Deliver DIAGNOSIS.md:**
  - Causes ranked by evidence, each labelled.
  - One proposed fix, as one change with pass marks and a proved-wrong result.
  - The fix must be general: no rule written for this puzzle kind, no kind label, and nothing that looks built for arithmetic.

## Helper W: why the vector reader credits the wrong person (read-only diagnosis; folder artifacts/claude-vread-wrongperson-YYYYMMDD/, prefix scripts/claude_vread_wp_*)
- **The problem (shown):** the vread vector reader (a small looped net reading a frozen MiniCPM5-1B's layer-12 vectors and pointing at word spans to write fact cards) loses on backref facts, where the owner was named in an earlier turn.
  - Astra's read-only diagnosis (reviews/astra-diagnose-vread-backref-2026-09-28.md) found two problems. The first was split confidence across repeated copies of a name. vread2 tested that fix and was INCONCLUSIVE (artifacts/claude-vread2-20260928/RESULTS.md).
  - The second is still open: when a rival person is named, the reader picks another person, usually one named more recently, in 16 cases against 4 for the LoRA reader.
- **Files:**
  - artifacts/claude-vread-20260927/: RESULTS.md, scores/, data/, and run/out/vec_dev_reads.jsonl and lora_dev_reads.jsonl, which hold every card with its owner and value tokens.
  - artifacts/claude-vread2-20260928/scores/.
  - scripts/claude_vread_model.py, claude_vread_data.py, claude_vread_score.py and claude_lis319_common.py.
- **Find out why.** Candidates to check, not conclusions:
  - Does it always pick the nearest or newest name?
  - Is the gold label itself ambiguous, such as a pronoun that could mean either person?
  - Do position offsets clipped at ±4 tokens (claude_vread_model.py:76-83) hide how far back a name is?
  - Which of the 7 probabilities is low on these cards?
  - What does the LoRA reader do on the same cards?
- **Allowed:** reading files and CPU scripts over existing outputs, on the dev split only.
- **Not allowed:** training, GPUs, or edits to existing files.
- **Deliver DIAGNOSIS.md** with ranked, labelled causes and one proposed fix, as one change with pass marks and a proved-wrong result.

## Helper S: the sleep test's official write-up (folder artifacts/claude-slp358n3-20260927/, new files only; prefix scripts/claude_slp358n3_report*)
- **The problem:** slp-358n3 finished on 09-28 (collected 09:04 UTC), but its records exist only on the origin/builder-outbox branch, and no official scoring or recount exists. The Thread manager's own raw count said every mark passes; that count is unofficial and decides nothing.
- **Steps:**
  1. Copy `artifacts/claude-slp358n3-20260927/runs/`, `run-vast/` and `SEAL-run.sha256.txt` from origin/builder-outbox to main unchanged. Check every file against run-vast/MANIFEST.sha256 and SEAL-run.sha256.txt, and report any mismatch.
  2. Score the four seed JSONs with the sealed PASSMARKS.md exactly as written, including its ceiling and floor rules: M1 (S − R), M2, M3 (harm), M3b (lost) and RESUME identical.
  3. Report the L arm (longer nights, seeds 13 and 14) beside S, as report only.
  4. Write RESULTS.md with the verdict.
  5. Have a separate subagent blind-recount from the raw JSONs and PASSMARKS.md only.
- Never edit PASSMARKS.md or the sealed code (SEAL-code.sha256.txt), and never re-run training. If a record is missing, say so and stop.

**Done means**
- Each helper's files are pushed to main: marks before runs, then results and recounts. For R, that means the holdout scores and RESULTS.md. For T and W, DIAGNOSIS.md. For S, RESULTS.md and the copied records.
- If R's ladders are still running when the others finish, report the other three, then report R when it ends.
- Final report for Ben, at most 16 lines, plain words, result first. Give one short block per problem:
  - R: does the relation net learn mazes from fewer examples than the loop?
  - T: why do the numbers puzzles fail, and what's the one fix to test?
  - W: why does the reader pick the wrong person, and what's the one fix to test?
  - S: did the sleep test pass officially?
  - Then time, money and commit hashes.
