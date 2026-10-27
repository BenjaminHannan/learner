# lis-319 = REGISTERED PASS (verified by the "Fix: reading facts from chat" thread, 2026-09-25 ~20:30 UTC)

Builder result: origin/builder-outbox:artifacts/claude-lis319-20260925/RESULTS.md (BensPC, $0, 2 h 50 min).

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| H1 back-references (needs_history facts, greedy R0) | >= 69 of 98 AND >= A + 40 | B 93/98, A 1/98 | PASS |
| H2 other facts | >= A - 3 points | B 104/113, A 102/113 | PASS |
| H3 wrong turns at T_B | <= 2 of 240 | 1 | PASS |
| H4 invented saves on no-fact rows | <= 1 | 0 | PASS |
| G1 single-turn dev hits | B >= A - 3% (524) | B 577/971, A 553/971 | PASS |

Proved-wrong clause (B's H1 <= A's + 10) did not trip.

## What I checked
- G1 recount: rebuilt WORK/data from sealed code on CPU (dev 1,311; split single 1,178 / hist 133), scored both pushed
  dev_pred files with claude_lis300_score.py at 0.995: A 553/971 (1 wrong turn), B 577/971 (3 wrong turns). Exact match.
- Whole dev at T_B: 611/1053 hits, 3 wrong turns. Exact match. T_B = 0.995 by the sealed rule (no grid value reaches 0).
- H4: claude_lis318_score.score uses a Counter and `dict(c)`, so an absent nofact_rows_with_save key is 0.
- score_A/score_B read from the pushed JSONs; H1-H3 arithmetic re-done above. Panel files not opened.
- Train ran to completion (6256/6256 steps, 76.5 min), max-len 512, 0 rows over (LENGTHS.json).

## What it does not show
- The gate is still the bottleneck: at 0.995 the reader finds 197 of 211 panel facts but saves only 65 (132 held back).
  rd-371 (learned "does the turn say this?" checker) is the registered test for that.
- Arm A's 11 wrong turns on this panel come from reading history-dependent turns without history; lis-319 brings them to 1.

Merged reader: sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76,
BensPC C:/Users/benja/lis319/work/run/merged, Mac ~/premonition-models/lis319-merged/.
