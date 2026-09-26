# lis-319k: corrections save at a lower bar (one change, no retraining)

Thread "Fix: reading facts from chat". Written 2026-09-26 ~13:55 UTC, before the test panel (readpanel319k) exists and
before any read of it. Plan: design/v3/30-modes/371c-note-and-save-plan.md (problem 1 now includes corrections, ME1).

## Why
0.2c's fact-correction row failed (3 vs 4), and the "Wrong answers stated as fact" thread traced most wrong-as-fact
answers to corrections that were heard but not saved: lis-319 reads correction turns right but below its 0.995 bar,
so the old value stays in the notebook. Checked here on lis-319's own dev reads (artifacts/claude-lis319-20260925 dev
predictions, builder-outbox; dev only, counts): of 111 gold CORRECT facts, lis-319 saves 55 right at 0.995; if facts
the reader itself labels CORRECT save at 0.95 it saves 77 right with 0 wrong CORRECT saves (0.9: 80 right, 2 wrong).
ASSERT saves are not touched by this change.

## The one change
Save rule: a fact whose predicted mode is CORRECT saves when its confidence >= 0.95; every other fact keeps 0.995.
Same reader (lis-319, model.safetensors sha256 e688e1b221cff938d7032a8864c87df60111ad92bc09a650d091931704776a76),
same compiler checks, same everything else. The reader reads the panel ONCE; both rules are scored from that one read
(scripts/claude_lis319k_score.py bar rewrites the confidences of CORRECT facts >= 0.95 to 1.0, then the usual scorers
run at 0.995). OLD = the read scored as is; NEW = the rewritten read.

## Test set
readpanel319k (TEST-ONLY): 30 fresh dialogs x 8 user turns, written blind by a separate agent, labelled by a blind
second labeller, adjudicated blind, sealed before the read. About 60 rows correct or update a detail stated earlier
in the same dialog (self-corrections, corrections of the assistant's prev_reply, updates like "we moved, we're in
Harrow now"); gold facts on those rows carry "correction": true and the replaced value goes in "replaced". About 60
look-alike rows must not save a changed value (questions about it, "I think it might be 13, not sure", plans to
change, corrections of someone else's claim that the user does not endorse, negation only). The rest are ordinary.

Scoring: whole claims exactly as lis-319c addendum B (owner, relation and value must match; mismatched wording goes to
two blind judges with artifacts/claude-lis319c-20260926/full/JUDGE_SAME.md; one-to-one credit), per
scripts/claude_lis319k_score.py final. NEW saves are a superset of OLD saves, so the judges judge NEW's pairs once and
both rules use the same verdicts.

## Marks (NEW vs OLD, same read)
| Mark | Bar |
|---|---|
| K1 | correction facts credited right: NEW >= OLD + 5 |
| K2 | saved_wrong_full: NEW <= OLD + 1 |
| K3 | stale saves (a saved fact matching a row's "replaced" value and no current fact): NEW <= OLD |
| K4 | saves on look-alike rows: NEW <= OLD + 1 |
PASS = K1 and K2 and K3 and K4.
Proved wrong: NEW - OLD on K1 <= 1.
Validity: the sealed panel needs >= 40 gold facts with "correction": true, and OLD must miss >= 8 of them; otherwise
INCONCLUSIVE (reported as such, not as a pass).

## Report only
Per-kind counts, saved_right_full overall, wrong_turns_full, the device the read ran on (confidences from a different
device than BensPC's are one read for both rules, so the comparison is fair; absolute counts are for that device).
Not in this change: FORMER (lis-319f, separate test), job + place rule, 0.98 vs 0.995 for ASSERT.
