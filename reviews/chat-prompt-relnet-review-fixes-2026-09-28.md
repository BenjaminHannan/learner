Effort: high (Opus 5.5)

# Goal: make the relation-net race finishable and fair before its first maze score

Paste into the manager chat that owns artifacts/claude-relnet-eq-20260928. Practice started 19:07 UTC on CPU. No maze score exists yet. Read first: artifacts/claude-dir-h8-review-20260928/REVIEW.md sections 2 (X1-X4) and 3.3 (R1-R5). Check each against your files and report which you reject.
Do, in this order, all as NEW addenda committed before the first maze score:
1. R1 (blocks): TIMING-ESTIMATE.md says about 54 h per dev run at one thread; ADDENDUM-4.md:15 of the ruler says a measured overturn of CPU feasibility needs a separate GPU addendum (strict fp32, TF32 off, CPU-equivalent smoke, at most one rental, $4 cap). PASSMARKS-C.md:80-81 says "report it, do not change the recipe". Write the GPU addendum now (Ben's standing OK: vast until told otherwise, $4 per job; the Director releases the rental through the Mac kit, so hand the Director a queue-ready job file, do not launch one). Alternatively run only the two practised runs first (pre, seeds 0 and 1, about 108 core-hours) and add the fresh copies later.
2. Copy each practised source.pt (6.6 MB) to a durable place and write its sha256 to source.json, so a GPU run can resume from it and no rebuild is needed (the distill run shows a rebuild changes numbers, RESULTS.md:46-52).
3. X2: PASSMARKS-C.md:55-56 and scripts/claude_relnet_eq_race.py:100-101 say REJECTED if ANY gaining seed breaks a gate. Change to EVERY gaining seed (the patch race and the ruler's original wording lean that way), fixing the three lines in a new report script copy.
4. X1: judge the old-kind sleep gates on the mean of 3 sleep draws per branch, margin max(6, 2 x SE) (draw machinery: scripts/claude_fewex_distill_sleep.py).
5. X3: add F_few (k = 1, 4, 16, 64) at least +5 over the loop in both seeds as a second required verdict row; X4: call a non-win "not shown" unless both seeds are at least 2 points below the loop.
6. R3, R4, R5: one line each (stale 4-6x cost line now 12.1x per maze update; verdict says "on mazes"; disclose thread-count change on seed 1).
Rules: commit to main, no PRs, new files only, times from `date -u`, never touch other chats' folders, never read keys. Final reply: what changed, what you rejected, and the new expected finish time.
