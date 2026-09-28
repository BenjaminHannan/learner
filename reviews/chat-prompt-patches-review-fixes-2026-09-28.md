Effort: high (Opus 5.5)

# Goal: fix the patch race's marks before any maze score is seen, using the independent review

Paste into the SAME patches chat. Nothing in the patch race has a maze score yet, so every change below must be committed as a new addendum (ADDENDUM-N, new file, never edit PASSMARKS.md) BEFORE the first maze rung is scored. Read first: artifacts/claude-dir-h8-review-20260928/REVIEW.md sections 2 (X1-X4) and 3.1 (P1-P5); it was written from your PASSMARKS.md, DESIGN.md and scripts, and recounts agree with your files. Check each finding against your code yourself and tell the Director (thread "Director", via your final reply) which ones you reject and why.

Changes to commit in the addendum (the Director's recommendations; you may argue against one with evidence):
1. X1 (blocks): the old-kind sleep gates ("within 6 of 200") are below the sleep-draw noise (sums up to about 14 of 200, grids about 5 of 200 per draw, from artifacts/claude-distill-20260928/sleeps/*.json). Judge each gate on the mean of 3 sleep draws per branch for BOTH the patch and the loop, margin max(6, 2 x SE). The draw machinery is scripts/claude_fewex_distill_sleep.py (draws at seed+k, +101, +202); save the k=64 and k=16,384 checkpoints of each arm so the draws can run.
2. X2 (blocks the word): "a maze gain made only by breaking an old-kind gate" = REJECTED only if EVERY seed that gains breaks a gate (PASSMARKS.md:44-46 and scripts/claude_patch_eq_report.py:121-124 already say this; keep it, and state it as the reading for everyone).
3. P1: mark 1 must be +10 F_eq over the HIGHER of loop_ep and the baseline loop (51.00 / 51.29 from RESULTS-EQ.md), not loop_ep alone.
4. P2: add one dev ladder per seed with the practised patch net and writes off (Net.WRITES = False), so "the writes helped" is separated from "the practised net is a better start". Read the patch's gain over that too.
5. X3: add F_few (mean of k = 1, 4, 16, 64) as a required second verdict row (at least +5 over the loop in both seeds) and quote it next to F_eq.
6. X4: word a non-win as "not shown" unless both seeds are at least 2 points below the loop; report per-seed differences.
7. P3 and P4: say "at 1.5x the compute" in the verdict sentence; report old-kind scores after sleep with the patch kept, as report-only.
Pass marks for your addendum's own claims are the reproduction: rerun scripts/claude_patch_eq_report.py on two fake seeds (one gains-and-breaks, one gains-and-passes) and show it prints different words for "any" and "every" readings.
Rules: commit to main, no PRs, new files only, fictional names, times from `date -u`, never touch other chats' folders. Do not start the maze rungs until the addendum is on main. Final reply: what you changed, what you rejected, and the earliest time the maze rungs can start.
