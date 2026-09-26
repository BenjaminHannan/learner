Pilot starting — reading the handoff rules and queueing the 60 wording calls.
Seals verified — now running self-tests.
Leak check passed — generating the 60 seeds.
Wording calls finished — checking the results.
All checks passed — copying artifacts into the worktree and writing up results.
Verdict: PASS — pilot4 ran end to end with no stop conditions. All 10 steps done, outputs in artifacts/claude-lis320-20260926/pilot4/ (8 files), temp tree deleted. Not pushed (watcher pushes PUSH paths).

Marks table (integer counts):

| Mark | Count |
|---|---|
| origin/main commit | 0ab78103 (full: 0ab7810308ef608a60f6e097e894bb1f226e97a3) |
| Seal ADDENDA-5 files OK | 6 / 6 |
| Seal ADDENDA-6 files OK | 6 / 6 |
| Selftests passed | 4 / 4 (glm_oclow 4/4 incl. 1 expected unparsed; seed_cr 400 dialogs; check_cr 1 kept + 1 dropped; rawcheck 4/4) |
| Leak-check calls | 1, exit 0, reply_ok true, left_after_cleanup 0 |
| Seed dialogs | 60, turns 419 (correct_ref 26, correct 28, backref 32, teach 136) |
| Share: opencode-run procs (N) | 8, workers (W) 6 |
| Wording calls | 60, parsed 58, skipped 0, failed_calls 0, batches 2, stopped done, minutes 3.1 |
| "call failed" lines | 0, distinct errors 0 |
| Rawcheck rows | 60, duplicate_ids 0, model_ok 60, temperature_null 60, not_in_seeds 0 |
| Kept turns | 362 (correct_ref kept 22), dropped 43, recased 164, dialogs_unparsed 2 |
| Files copied to pilot4/ | 7 + RESULTS.md written |
| Temp tree gone | confirmed GONE |
| Misses / deviations / errors | 0 |

Every move: fetch origin/main → archive to temp dir → seals OK → 4 selftests ok → leak check exit 0 → seeds (60) → share count (N=8, W=6) → wording 22:06:50–22:09:57 UTC (3.1 min, 19.4 dialogs/min) → rawcheck OK → check_cr + style → copied 7 files + RESULTS.md to worktree pilot4/ → rm -rf temp dir, confirmed gone. No branch checkout, no push, no flag changes, no config/auth/key reads.

What it means in plain English: the fast low-thinking route worked at pilot scale — 60 prompts went through in about 3 minutes with zero failed calls, and 58 of 60 gave usable wordings. The correction-row check kept 362 turns including 22 of the new correct_ref type. Whether that passes the pre-set thresholds in ADDENDUM-6 is for the director to judge against the sealed numbers; this run only reports the counts. What it doesn't mean: nothing was trained, and this says nothing about quality beyond the counts — the kept/dropped breakdown is in check.json for review.
