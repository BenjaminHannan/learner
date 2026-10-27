# lis-319c-full = REGISTERED FAIL (F2); lis-319 diagnostic holds (verified by the "Fix: reading facts from chat" thread, 2026-09-26 ~04:50 UTC)

Reads: job 006h (origin/builder-outbox:artifacts/claude-lis319c-20260926/full/RESULTS-full-reads.md) re-read readpanel319c and
readpanel319 with the sealed lis-319 reader; the old-scorer counts reproduce 006e and lis-319 exactly (every key but ms).
Scoring: scripts/claude_lis319_fullclaim_b.py (addendum B, registered before these data), two blind same-claim judges
(full/JUDGE_SAME.md): 81 pairs on 319c, judges agree on all 81 (76 same, 5 not); 22 pairs on 319, all same.

| Mark (readpanel319c, 239 turns, 424 facts) | Bar | A = 0.995 | B = 0.98 | Verdict |
|---|---|---|---|---|
| F1 saved right, whole claim | B >= A + 25 (159) | 134 | 180 | PASS (+46) |
| F2 wrong turns, whole claim | B <= A + 1 (6) AND <= 3 | 5 | 7 | FAIL |
| F3 saves on no-fact turns | <= 1 | 0 | 0 | PASS |
Proved wrong (B >= A + 3 = 8): not tripped (7).

The first script (claude_lis319_fullclaim.py) gives the same counts (no narrower-relation or multi-person cases occurred).
Files: full/scoreB_319c.json, full/score1_319c.json; verdicts full/v1_*.jsonl, full/v2_*.jsonl (TEST-ONLY with pairsB_*).

## What this means
- The registered S verdict (PASS, old owner+value scorer) stays on record, but the goal rule needed S AND F: problem #1 is
  NOT solved by 0.98. Month-end keeps build_330a_334_r319 (0.995).
- Whole-claim scoring finds relation errors the old scorer hid: 4 extra wrong turns at 0.995 (5 vs 1) and 5 extra at 0.98
  (7 vs 2), e.g. work location saved for lives in, former job for current job (judges' categories; no text quoted).
  So even the live 0.995 bar makes a wrong save on about 2% of these messages.
- lis-319 diagnostic (readpanel319, 0.995): whole-claim 65 right, 1 wrong turn (old scorer 65 / 1): its H3 (<= 2 of 240)
  still holds; the lis-319 PASS is not overturned.
- Next single change (not tonight): relation errors, not the bar, are what a lower bar lets through. Candidate: train the
  gate/checker on the reader's own relation confusions (hard negatives), whole-claim scored, fresh panel, marks set first.
