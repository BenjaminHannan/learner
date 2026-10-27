# lis-319j: job + place hold rule (one change, no retraining)

Thread "Fix: reading facts from chat". Written 2026-09-26 ~14:20 UTC, before any read of readpanel371c exists here
(the rent-lis-319f job is reading it now; this thread has seen no read of it).

## Why
Ben's 12:00 report: some wrong saves on readpanel319c at 0.98 mix up "works in" and "lives in" when a job and a place
share a sentence. That panel motivated the rule, so it is not used to test it. Dev check (lis-319 dev reads): the rule
holds 2 city facts, neither of which is saved at 0.995 or 0.98 (no dev harm, no dev gain: dev has no such error).
Training labels: of ~1,400 unique city / work_location labels, 8 label a place "city" in a clause with a work word.

## The one change
scripts/claude_lis319j_rule.py: a city/home fact is held when its clause has a job cue (work word, or the value of the
frame's own occupation/employer/job fact) and no home cue; a work_location fact is held when its clause has a home cue
and no job cue. Held facts are never saved. Everything else unchanged.

## Test
readpanel371c (TEST-ONLY, sealed 2d3d5b64e; its writer was told to put "a job and a home town in one sentence"),
the OLD (lis-319) reads that rent-lis-319f produces (reads_panel_old.jsonl), read once there; no new read.
OLD = those reads; NEW = the same reads after `claude_lis319j_rule.py hold` (rows = claude_lis319_rows.py output).
Whole-claim scoring exactly as lis-319f (claude_lis319_fullclaim_b.py, two blind judges, one-to-one credit). NEW saves
are a subset of OLD saves, so the judges' verdicts on OLD's pairs (at 0.995 and 0.98) cover both.
Primary bar T = 0.98 (where the report saw the errors, and the bar this thread must decide next); 0.995 report only.

## Marks (NEW vs OLD at T = 0.98)
| Mark | Bar |
|---|---|
| J1 | saved_wrong_full: NEW <= OLD - 1 |
| J2 | saved_right_full: NEW >= OLD - 1 |
| J3 | held saves that were right <= held saves that were wrong |
PASS = J1 and J2 and J3. Proved wrong: NEW saved_wrong_full = OLD saved_wrong_full (the rule removes no wrong save).
Validity: the rule must hold >= 2 facts that OLD saves at 0.98; otherwise INCONCLUSIVE (the panel cannot test it).
Also report the same counts for the lis-319f reads (report only; whichever reader goes forward gets the rule's verdict
from its own reads if it is re-tested).
