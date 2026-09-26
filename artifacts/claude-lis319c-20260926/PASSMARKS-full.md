# lis-319c-full: the same lis-319c marks, scored as whole claims (registered 2026-09-26 ~02:20 UTC, before the lis-319c result)

Why: an outside review (Ben, 01:54 UTC) found that the panel scorer (claude_lis318_score / claude_lis319_score, via
claude_lis317_gates.e2e_match) counts a saved fact as right when owner and value match, ignoring the relation, accepts a
first name for a full name, and drops rows with no read before counting their gold. Checked against the code: all three
are true. (The dev sweep that chose 0.98 used claude_lis300_score.match, which does check owner, relation and value.)
Count-only check: 233 of the 424 gold facts in readpanel319c use relation words outside the reader's relation table, so
a plain string compare of relations would be unfair; mismatched wording goes to blind judges instead.

The registered lis-319c verdict (PASSMARKS.md, S1-S3) stays the record. This file adds a stricter scoring of the same
kind of read. Ben's overnight goal counts problem #1 as solved only if BOTH S1-S3 and F1-F3 pass.

## Reads
Job 006h re-reads readpanel319c with the same sealed reader and scripts (greedy, deterministic). It must reproduce
006e's score_A.json and score_B.json counts exactly with claude_lis319_score.py; if not, F1-F3 are void and reported.

## Scoring: scripts/claude_lis319_fullclaim.py (sealed below)
Same save rule as lis-319c (live structural check + min-token conf >= T; A = 0.995, B = 0.98). A saved fact is right only if:
- exact: owner equal (the user <-> me; else the whole name), value equal, relation equal or narrower (NARROWER table); or
- judged: it matched under the old rule but not exactly, and BOTH of two blind judges (brief JUDGE_SAME.md, fixed now)
  say it states the same claim as the gold fact.
Everything else saved is wrong. Rows without a read keep their gold in the denominator.

## Marks (identical numbers to S1-S3)
| Mark | Bar |
|---|---|
| F1 | B saved_right_full >= A saved_right_full + 25 |
| F2 | B wrong_turns_full <= A wrong_turns_full + 1 AND <= 3 of 239 |
| F3 | B nofact_rows_with_save <= 1 |
Proved wrong: B wrong_turns_full >= A wrong_turns_full + 3.

## Diagnostic only (no bar)
The lis-319 panel (readpanel319, reader B at 0.995) re-read and scored the same way; its registered PASS stays the record.
