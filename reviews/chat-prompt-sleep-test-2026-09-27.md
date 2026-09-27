# Chat prompt: get the thinker's sleep test (slp-358n3, the build's sleep gate H-B) running (Thread manager, 2026-09-27T23:46Z)

The Thread manager told Ben at 23:43 UTC that the sleep test is the only build seat with no chat on it, and that it is
blocked on the 358u loop weights. Ben answered "yes" at 23:45:25 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEWLBspSJjT9SphuZtpcyuGox)
to writing this prompt. Everything below the line is the prompt.

---

# Goal: get the 4 kind-blind thinker nets safely onto Ben's Mac (recovered or retrained), then run the sealed sleep test slp-358n3 once and report its verdict

**Context**
- Repo BenjaminHannan/learner (Ben's Premonition project). Read CLAUDE.md first.
- Ben (a high-school senior) reads your final report.
- The thinker is a small looped net. slp-358n3 asks whether a night of practice on the day's puzzles makes it better at fresh puzzles of that kind, without harming what it knew, and whether a night can be stopped and resumed. It is the build's sleep gate (H-B). Its marks are sealed: artifacts/claude-slp358n3-20260927/PASSMARKS.md.
- n3 starts from the 4 loop nets of rsn-358u (PASS; artifacts/claude-rsn358u-20260927/RESULTS.md). The copy back to the Mac broke on the first file, so no Mac copy matches 358u's SEAL-run. All 8 checkpoints are still on vast instance 52964920, which is stopped. Two restarts (jobs rent358u-4-recopy and -4b-recopy) printed NO-START: it stayed "exited" for 15 minutes both times, and the job log guesses its host's GPU was busy. See their replies on origin/builder-outbox under runs/.
- The Sleep research and Fix sleep threads that own this work are stopped. You act for them on this one test only.
- Other chats are running (few-example test, patches, relation net, lis-320 reader, thinker-as-reader, the build's note writer). Don't edit their files, don't touch their jobs, and never stop another agent's rental.

**Read first**
- artifacts/claude-slp358n3-20260927/PASSMARKS.md and SEAL-code.sha256.txt; scripts/claude_slp358n3_nights.py; the kit handoff/kit/sleep358nv; the job handoff/queue/rent358n3-1-start.md and its reply ("WAITING: ... 358u not collected").
- artifacts/claude-rsn358u-20260927/ (PASSMARKS, ADDENDUM-1/2, SEAL-run, RESULTS); scripts/claude_rsn358u_run.py; the kit handoff/kit/sleep358uv; handoff/queue/rent358u-4b-recopy.md.
- The newest Fix sleep result, artifacts/claude-fs358r-20260927/RESULTS.md, for context only. n3 is sealed, so don't change its recipe to match it.

**Step 1: the weights (one path, in this order)**
1. Try the restart once more: a new job copied from rent358u-4b-recopy under a new name, unchanged otherwise. It keeps a file only if its sha256 matches SEAL-run, and destroys 52964920 only if all 8 match.
2. If it prints NO-START or RECOPY-INCOMPLETE, retrain the 4 loop runs only (seeds 13-16) with 358u's sealed code and settings, unchanged, on one rental. The plain runs aren't needed. Before training, write and commit artifacts/claude-rsn358u2-YYYYMMDD/PLAN.md with this acceptance mark: each re-run loop net passes 358u's V0, and the 4-seed loop mean is within 15 points of 358u's on sums8 (274.25 of 300) and on grids7 (184.00 of 300). If the re-run misses it, stop and report; don't run n3 on it.
3. Copy the weights back one file at a time through a tmp file, check each sha256 against the run's own manifest, and retry a failed file. Destroy the rental only after all 4 are verified on the Mac. The last copy-back died on a broken pipe partway through one big tar.
- If you retrain, 52964920 stays stopped with 358u's original files. Don't destroy it. Tell Ben it's still there and costing a little for storage, and leave that call to him.

**Step 2: n3**
- If the originals come back, run n3 exactly as sealed.
- If you use the re-run nets, write artifacts/claude-slp358n3-20260927/ADDENDUM-1.md and commit it before any n3 run. It says the base is the 358u re-run (its own SEAL-run), and one thing changes: which checkpoint file the sha check reads. The kit's vstart.sh checks against 358u's SEAL-run, so make a new kit copy (for example handoff/kit/sleep358n3r) instead of editing sleep358nv.
- Known risk (inferred): n3's vstart waits 8 minutes for ssh. Tonight a different kit's 3 rented hosts all stayed "loading" past 8 minutes. If n3's first host does the same, a longer wait in your kit copy is the likely fix. Disclose it in the addendum.
- Everything else stays sealed: arms S, R, Z, N and the report-only L, the 3 days, the tests, M1-M3b, RESUME, and the proved-wrong line.
- A separate subagent does a blind recount of the key numbers from the score files and the marks only.

**Rules**
- Commit to main, no PRs. `git pull --rebase` before every push; never force-push. New files only. Never touch the repo-root notebook/.
- Times in files come from `date -u`.
- Money: Ben's standing rule lets you rent. At most $4 per job. The restart costs cents, a loop-only retrain about $1 (358u's 8 runs cost $1.25), and n3's own guard stops at $2.00. Weights never go to git. Never read or print the vast key or any auth file.
- Mac jobs are bash-only, through main's handoff/queue/, following the existing job files.
- Stop processes by exact PID.
- Label claims shown, suggested or untested. Give counts as "x of N".
- Save usage: run long jobs in the background, don't poll, skip status chatter, and use subagents only when needed.

**Done means**
- The 4 nets verified on the Mac, n3 run once with its verdict, RESULTS.md and the recount pushed to main, and every rental you started destroyed after a verified copy-back (or stopped, and said so).
- Final report for Ben, 12 lines at most, plain words, result first:
  - Did a night of sleep make the thinker better at the day's puzzles, without harming what it knew?
  - Did stopping and resuming a night work?
  - Were the original nets recovered, or retrained, and does 52964920 still exist?
  - Money spent, from the guard's own count.
  - The single next step.
  - Commit hashes.
