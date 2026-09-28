---
name: listener-line-overnight
description: Reading-facts thread state for Ben's overnight goal 09-26 (lis-319c 0.98 bar + whole-claim re-score, rd-371b note checker), from 02:30 UTC
metadata:
  type: project
  modified: 2026-09-26T01:59:45.291Z
---
Continues [[listener-line]]. Goal items: #1 saves too little, #3 notes untrustworthy. Passes to Month-end by 07:30 UTC.
- SCORER FLAW (Ben's outside review 01:54 UTC, verified in code): panel scorers claude_lis318_score/claude_lis319_score use claude_lis317_gates.e2e_match = owner+value only (relation ignored, first name ok for full name, rows with no read drop their gold). Dev scorer claude_lis300_score.match DOES check relation. 233/424 readpanel319c gold relations are outside the reader's relation table, so relation compare needs blind "same claim?" judges.
- Registered BEFORE the 319c result: artifacts/claude-lis319c-20260926/PASSMARKS-full.md (F1-F3 = same numbers as S1-S3, whole-claim scoring via scripts/claude_lis319_fullclaim.py pairs/final; judge brief full/JUDGE_SAME.md; main 1ab554ff0). #1 solved only if S AND F pass; 0.2c uses build_330a_334_r319c only then, else build_330a_334_r319.
- BensPC queue order: 006e lis-319c (running since 01:12 UTC) -> 006g rd-371b-notes (note writer drafts on 120 train dialogs + greedy notes on sealed notepanel371b, 30 dialogs) -> 006h lis-319c-full (re-reads both panels, pushes reads/pairs TEST-ONLY to full/).
- rd-371b next: blind judges grade drafts (scratchpad c371b/j/build.py builds judge_in; key.py builds panel key from 2 judges), then J2 train/sweep/test.
- Store (Benchmarks' claude_ep382_store) recall defaults to heard+note; any note switch-on must restrict answering to heard and resolve notes to cites. Told Benchmarks + Month-end 02:25.
- 02:10 lis-319c = REGISTERED PASS (old scorer): B 185 vs A 138 of 424, wrong turns 2 vs 1 of 239, nofact 0 (VERIFY main f2b83913d). Month-end holds r319 until F marks pass.
- 02:45 addendum B (main 66e238e81): F marks decided by scripts/claude_lis319_fullclaim_b.py (one-to-one credit, narrower relations judged). Back-refs: check_fact needs owner in turn/prev -> 37 found, 3 saved; dev preview of history owner check +28 right/+3 wrong (role confusion): follow-up plan design/v3/30-modes/319d-history-owner-check.md (ask back first).
- 006g launched 02:11 UTC.
- 04:50 lis-319c-full = REGISTERED FAIL on F2 (whole claim: wrong turns 0.98 7 vs 0.995 5 of 239; right 180 vs 134). #1 NOT solved; Month-end keeps r319 (0.995). lis-319 diag holds (65 right/1 wrong). Even 0.995 wrong-saves ~2% whole-claim (relation errors). VERIFY-full main 78a46a2b7. Next: relation-confusion hard negatives for the gate (follow-up).
- rd-371b: training data 2,054 own drafts judged (868 ok/993 unsup), key sealed (ok 132, unsup 145, excl 37; main ab068157f); 006i training on BensPC ~04:45-05:30.
- 05:25 rd-371b = REGISTERED FAIL (builder report): dev bar 0.98 kept 6/277 dev; test kept 1/132 true notes; proved-wrong tripped. Provisional VERIFY main a543d074b; result files stuck on Mac (my PUSH line used bare names) -> Director's 000-push-rd371b, held by Mac disk <5 GB. GPT prompt reviews/gpt-diagnose-note-checker-2026-09-26.md. Both goal items #1 and #3 = honest FAILs; Month-end told (0.2c: r319 0.995, no notes/checker).
- LESSON: queue PUSH lines must use full artifacts/... paths.
