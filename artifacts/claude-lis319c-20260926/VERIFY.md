# lis-319c = REGISTERED PASS under the registered scorer (verified by the "Fix: reading facts from chat" thread, 2026-09-26 ~02:12 UTC)

Builder result: origin/builder-outbox:artifacts/claude-lis319c-20260926/RESULTS.md (BensPC, $0, ~50 min).

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| S1 more saved | B saved_right >= A + 25 (163) | B 185/424, A 138/424 (+47) | PASS |
| S2 no less safe | B wrong_turns <= A + 1 (2) AND <= 3 of 239 | B 2, A 1 | PASS |
| S3 no invention | B nofact_rows_with_save <= 1 | 0 (key absent = 0, Counter) | PASS |
Proved wrong (B wrong_turns >= A + 3 = 4): not tripped.

## What I checked
- Arithmetic re-done from the pushed score_A.json / score_B.json; bars as registered (PASSMARKS.md, sealed; seal OK on BensPC).
- Reader sha matches e688e1b2...; panel seal 5/5 OK; one read, scored twice.
- No independent recount was possible: the task deleted the panel reads (they hold panel text). 006h re-reads the panel.

## What it does not show (important)
- The registered scorer (claude_lis317_gates.e2e_match) matches owner + value only; it ignores the relation and accepts a
  first name for a full name (outside review, 01:54 UTC; true in the code). So this PASS does not show that saved facts keep
  their meaning. The whole-claim re-score (PASSMARKS-full.md, F1-F3, registered 02:20 UTC before this result was read,
  job 006h) decides whether 0.98 goes into 0.2c. Ben's goal counts problem #1 solved only if S1-S3 AND F1-F3 pass.
- Back-references: the reader finds 37 of 57 history facts but saves only 2 (0.995) or 3 (0.98). The bar barely helps them.
- Found (R0) is 326 of 424 on this panel: the reader misses 98 facts before any gate (long multi-fact turns: 219/291).
