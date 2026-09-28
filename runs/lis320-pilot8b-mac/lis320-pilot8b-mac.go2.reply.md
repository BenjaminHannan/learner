Resuming the cut-off pilot — checking for orphaned runs and picking up where it left off.
Seals check out — now running the required self-tests.
Seeds and self-tests done — launching the main wording run.
Wording complete with zero failures — now running the verification checks.
All checks passed — copying the outputs and writing the final report.
Verdict: DONE — lis320-pilot8b complete, all green. No orphan run existed; steps 1–8 ran as written. $D removed and confirmed gone. PUSH: artifacts/claude-lis320-20260926/pilot8 (7 copied files + RESULTS.md).

Marks table (integer counts):
- seals: 4/4 OK (ADDENDA 6, 8, 9, 10)
- selftests: 5/5 ok (luna2, seed_cr, check_we3, rawcheck2, 1 live Luna selftest: `selftest ok: model gpt-6-luna, output-file True`)
- seeds: 60 dialogs, 415 turns
- wording calls: 60, parsed 60, skipped 0, failed_calls 0, batches 2, stopped done, minutes 15.4; "call failed" lines 0; raw lines 60
- rawcheck: OK, 60 rows, 0 dup ids, 60 model_ok, 60 temp-null, 0 dup3, 0 not_in_seeds (no ROUTE-FAIL)
- check: 415 turns → kept 408, dropped 7 (teach 3, yes_after_ask 2, ack_after_ask 1, plan 1; reasons: group_speaker 3, assert_hedged 2, reply_ask_missing 2, stray_name 1); kept plan 14/15
- style: kept 408 turns, median 9 words, p90 26, lowercase 0.794, noapos 0.23, over20 0.174

Moves: fetch origin/main @ 3e8cf1186bf64cca8a77f0e5428596bd2bc70b30 → archive to $D → seals → selftests → seeds (seed 328) → wording (3 workers, max 40 min) → rawcheck → check+style → copy to worktree pilot8/ + RESULTS.md → rm -rf $D (confirmed `No such file or directory`).
Misses/errors/deviations: none.
Times: start Mon Sep 28 00:02:04 UTC 2026 (load 49.19), end 00:17:26 UTC 2026 (load 86.72). Dialogs/min 3.90 (60/15.4; wall 15m22s same). Turns/min 26.95. Total Luna calls 61 (60 + 1 selftest). $0, Mac CPU, no GPU/reader/rental.

What it means (plain English): we made 60 fake practice conversations with the new Luna writer and ran the standard quality filters. All 60 came back usable at the conversation level; the filters kept 408 of 415 individual turns and dropped only 7 for known quality reasons. Nothing was trained; pass/fail against the pre-fixed pilot-7 thresholds happens downstream, not here.
