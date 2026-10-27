# lis-319t: ordinary facts save at 0.98 instead of 0.995 (one change: the bar)

Thread "Fix: reading facts from chat". Written 2026-09-26 ~14:30 UTC, before any read of readpanel371c is seen here.
Answering from memory's y1d (14:24): answering from the user's raw words got 13 of 56 on DEV, so memory answers still
run through saved facts, and "saves too few" (0.2c: 134 of 424 true facts kept) still costs answers.

## Evidence so far (dev only)
lis-319 dev reads: ASSERT saves right 688 at 0.995 vs 801 at 0.98, wrong 4 vs 4. The readpanel319c report (Ben 12:00)
saw more wrong saves at 0.98, mostly works-in vs lives-in and former jobs; lis-319j and lis-319f target those.

## The one change
Every fact saves at T = 0.98 instead of 0.995 (same reader, same compiler). Scored from the lis-319 reads of
readpanel371c that rent-lis-319f produces (reads_panel_old.jsonl; read once there, no new read), whole-claim with the
same two blind judges (pairs are built at 0.995 and 0.98), one-to-one credit (claude_lis319_fullclaim_b.py final).

## Marks (0.98 vs 0.995, same reads)
| Mark | Bar |
|---|---|
| B1 | saved_right_full: 0.98 >= 0.995 + 10 |
| B2 | saved_wrong_full: 0.98 <= 0.995 + 2 |
| B3 | nofact_rows_with_save: 0.98 <= 0.995 + 1 |
PASS = B1 and B2 and B3. Proved wrong: B1 gain <= 3.
If B2 fails, the same count is re-read with lis-319j's rule applied at 0.98 (report only here; lis-319j has its own
verdict): if the rule brings wrong saves within +2, the next registered test is "0.98 + job/place rule" as one package
on a fresh panel. Whichever reader goes forward (lis-319 or lis-319f) is the one this bar is re-tested on before shipping.
