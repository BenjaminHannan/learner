# VERIFY gram-364 (grammar thread, 2026-09-25 ~19:15 UTC)

**Verdict: registered FAIL** on P364.2 (both graders) and P364.3. PASSMARKS.md and code sealed at main cecfa1775
before the run. Run on BensPC 16:48-16:56 UTC (RESULTS-benspc.md: seals 4/4 and 9/9 OK, all tests OK, winnl2 probe
ok with 0 CRLF, 256 rows, 0 CRLF in outputs). Graders: two blind Opus agents (planted errors caught 39/40 and
39/40, clean kept 40/40 and 40/40: both valid). Scores: grades/score.json (scripts/claude_gram364_grade.py).

| Mark | Bar | Result | Verdict |
|---|---|---|---|
| P364.1 v2 fill-in lines clean, each grader | >= 94% | A 140/146 (95.9%), B 138/146 (94.5%) | PASS |
| P364.2 gain over gram-360 on the same parts, each grader | >= +3 | A 136 -> 140 (+2.7), B 136 -> 138 (+1.3) | FAIL |
| P364.3 score changes (confirm flag / confirm answer / ask class); non-rule parts changed | 0 and 0 | 0 / 2 / 0; 0 of 111 | FAIL |
| P364.4 slot words lost | 0 | 0 | PASS |

Proved wrong (gain < +1 on a valid grader): not triggered.

## What happened (report only, counts only; no bank text quoted)
- gram-360 already renders bank H's fill-in lines well: 136/146 clean for both graders (93.2%), better than on
  bank G (91%). v2 rendered only 8 of 183 rule-agent parts differently from gram-360, so there was little left
  for it to win: +4 lines (A) and +2 lines (B).
- The 2 confirm-answer changes both come from change 1 (the catch-all "other" said as 'your note about O says
  "V"'). The word "your" in that wording makes the harness's simulated user treat a fact the user owns as named,
  so its answer to the confirm flipped from no to yes on 2 turns. The rendering changed what the test user heard,
  which is exactly what P364.3 forbids. Any rewording of "other" must avoid "you"/"your" unless the owner is the
  user.
- Unchanged by v2: raw lines 108/146 and 110/146; whole replies 177/191 (A) and 174/191 (B).
- 336 scorer for P364 (report only): facts saved 54/123, day-1 kept 42/42, asks RIGHT 11 + RIGHT_CONFIRM 4,
  WRONG_CANDIDATE 8, confirm rows 57. No control arm was run, so these are not compared.

## What it means
gram-360 stays the fill-in finisher. v2 is not joined anywhere. The remaining fill-in misses are mostly the
reader's nonsense slots (owned by the reading thread) and a handful of rendering cases worth only 1 to 3 points.
Per Ben (2026-09-25 11:02, "stop at 90%"), chat grammar is closed at about 90%; with fill-in lines at ~93% under
gram-360, this thread has no registered next step.
