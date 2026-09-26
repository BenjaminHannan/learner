# lis-319c-full addendum B (registered 2026-09-26 ~02:45 UTC, before any F-mark data: 006h has not run)

A second outside review (Ben, 02:11 UTC) asked that the whole-claim scoring also handle four cases. Checked against the code:
1. One prediction matching several people: claude_lis319_fullclaim.py could credit one saved fact to two gold facts
   (e.g. "Ada" judged same as both "Ada Rook" and "Ada Lin"). TRUE -> fixed: one-to-one credit.
2. Unsupported specialisation: it treated a narrower saved relation (mother for gold parent) as exact. TRUE -> fixed:
   narrower relations go to the blind judges, who say same only if the turn states the narrower one.
3. Missing predictions dropping out of the denominator: already handled (rows with no read or no frame keep their gold).
4. Compiler rejections removing gold facts: not in the panel scorers (panel gold is never compiled; a rejected
   prediction just is not saved). It IS true of the dev scorer claude_lis300_score.score, which compiles gold frames, so
   dev coverage numbers leave out gold facts the compiler would reject. The 0.98 choice compared wrong-save counts and
   saves on the same denominator at every bar, so the choice is unaffected; the dev coverage share is overstated.

Rule: F1-F3 (PASSMARKS-full.md, same bars) are decided by scripts/claude_lis319_fullclaim_b.py (pairs + final, sealed
below), using the same judge brief (full/JUDGE_SAME.md) and two blind judges on its pairs file (a superset of the first
script's pairs). The first script's final counts are reported alongside. Registered S1-S3 verdict unchanged.
