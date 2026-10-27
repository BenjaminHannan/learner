# lis-319t2: the 0.98 bar on the lis-319f reader (one change: the bar)

Thread "Fix: reading facts from chat" (problem #1, saves too few). Written 2026-09-26 15:18 UTC, before any read of the test panel exists.

## Why
lis-319t FAILED on the lis-319 reader: at 0.98, right saves rose by 38 but wrong saves rose by 7 (bar +2) and no-fact rows with a save
by 5 (bar +1). lis-319f PASSED and replaces lis-319. On the same panel, lis-319f at 0.98 showed +37 right and +2 wrong
(artifacts/claude-lis319t-20260926/VERIFY.md). That was seen after the fact, so it chooses nothing: this is the re-test on a
panel no read of which has been seen.

## The one change
Every fact saves at T = 0.98 instead of 0.995. Same reader (lis-319f, model.safetensors sha256
970ef0acd5966f9e1a42049025d4ed807dee3989225201fd9dbcc6b4aa6b4f9b), same compiler, same prompt (claude_lis319_read.py).

## Test
readpanel319k (TEST-ONLY, sealed main cb0689501; 240 rows: 120 ordinary, 60 correction, 60 lookalike; 239 true facts; 70
rows with no fact), read ONCE by lis-319f on the Mac (handoff/queue/lis319t2-panel-mac.md). Pairs at 0.995 and 0.98
(claude_lis319_fullclaim_b.py pairs), two blind Opus judges (JUDGE_SAME.md, neutral names), then fullclaim_b final.

## Marks (0.98 vs 0.995, same reads)
| Mark | Bar |
|---|---|
| B1 | saved_right_full: 0.98 >= 0.995 + 10 |
| B2 | saved_wrong_full: 0.98 <= 0.995 + 2 |
| B3 | nofact_rows_with_save: 0.98 <= 0.995 + 1 |
PASS = B1 and B2 and B3. Proved wrong: B1 gain <= 3. INCONCLUSIVE if the read covers fewer than 230 rows.
If it passes, 0.98 does not ship as a hand-set bar: it becomes the bar the next retrained reader is checked at.
Report only from this read: lis-319k's CORRECT-at-0.95 counts on lis-319f (lis-319k itself is decided on the lis-319 read).
