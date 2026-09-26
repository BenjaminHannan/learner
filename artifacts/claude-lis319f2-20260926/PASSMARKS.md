# lis-319f2: "used to" as a save-time hold rule (fallback for lis-319f; one change, no retraining)

Thread "Fix: reading facts from chat". Written 2026-09-26 ~14:25 UTC, before any read of readpanel371c is seen here.

## Decision rule, fixed now
If lis-319f PASSES, it goes forward and this result is report only. If lis-319f FAILS or is INCONCLUSIVE, this verdict
decides whether the hold rule goes forward instead. (Either way it is computed once, from reads that already exist.)

## The one change
scripts/claude_lis319f2_rule.py: on the unchanged lis-319 reader, a fact is held (never saved) when
claude_lis319f_data.is_former(fact, turn) is true: the exact code rule that relabelled lis-319f's training data.
Dev (lis-319 dev reads): holds 7 facts; at 0.995 and 0.98 it removes 4 saves, all 4 on the dev rows lis-319f relabels
as former (their old gold still calls them current).

## Test
readpanel371c (TEST-ONLY, sealed), OLD = reads_panel_old.jsonl from rent-lis-319f (lis-319, read once there);
NEW = the same reads after the hold rule (rows = claude_lis319_rows.py output). Same scorers and blind-judge verdicts as
lis-319f (NEW saves are a subset of OLD saves). Marks exactly lis-319f's, NEW vs OLD at 0.995:
M1 NEW former_as_current <= 1; M2 NEW saved_right_full >= OLD - 3; M3 NEW wrong_turns_full <= OLD.
Proved wrong: NEW former_as_current >= half of OLD's (rounded up) when OLD >= 2. INCONCLUSIVE as in lis-319f.
