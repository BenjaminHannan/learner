# lis-319f: a FORMER mode, so "used to" is never saved as now (one change on top of lis-319)

Thread "Fix: reading facts from chat". Written 2026-09-26 ~12:25 UTC, before the lis-319f data was built on BensPC,
before any training, and before readpanel371c was sealed or run. Plan: design/v3/30-modes/371c-note-and-save-plan.md.

## Why
Ben's pasted report (12:00 UTC), checked against the data here: the reader's modes cannot say "used to", and its
training labels teach former jobs as current (e.g. "he was a fisherman out of Peterhead his whole life" -> occupation
fisherman, ASSERT). On readpanel319c (whole-claim scoring) the report traced 3 of the 7 wrong saves at 0.98 to former
jobs saved as current (panel text not read here; counts only). On lis-319 dev, the old reader saves 4 former facts as
current on the 7 dev rows the new rule relabels.

## The one change
Training data = lis-319's data, built exactly as before (scripts/claude_lis319_data.py, same args), then
scripts/claude_lis319f_data.py: (1) facts in time-bound relations whose clause carries a past cue right before the value
("was a", "worked at", "used to", "my old roommate", "lived in ... till last year") and no present cue get mode FORMER
(16 unique training chats, 64 rows with lis-319's repeats; 7 dev rows); (2) 1,200 train / 150 dev single-turn rows made
by code from the data's own name and value pools: former sentences, former + current pairs, and look-alike current
sentences ("has worked at X for 6 years", "moved to X last year") that stay ASSERT. Spec note:
design/v3/60-listener/frame-spec-notes-319f.md. No new text written by a model; the compiler is unchanged (FORMER is
not a write mode, so it is held). Same base model, same training args as lis-319 (2 epochs, lr 2e-4, rank 32, batch 16,
max-len 512, seed 300). Expected build counts: BUILD-dryrun.json (train 51,244, dev 1,461).

Both readers save at the same bar, T = 0.995 (lis-319's registered bar), so the bar is not a second change.

## Test set
readpanel371c (TEST-ONLY): 30 fresh dialogs written blind by a separate agent, a blind second labeller and a blind
adjudicator, sealed before any run. Each row carries current `facts` and `former` items (no longer true). About 45
former rows. The old reader (lis-319, merged sha256 e688e1b2...) and the new reader each read it once.

Scoring: whole claims, exactly as lis-319c addendum B (scripts/claude_lis319_fullclaim_b.py: owner, relation and value
must all match; mismatched wording goes to two blind judges with brief artifacts/claude-lis319c-20260926/full/
JUDGE_SAME.md; one-to-one credit). Former-as-current: scripts/claude_lis319f_score.py panel (a saved fact whose owner
and value match a former item of its row and no current fact).

## Marks (new = lis-319f, old = lis-319, both at 0.995, same panel)
| Mark | Bar |
|---|---|
| M1 | new former_as_current <= 1 |
| M2 | new saved_right_full >= old saved_right_full - 3 |
| M3 | new wrong_turns_full <= old wrong_turns_full |
PASS = M1 and M2 and M3.
Proved wrong: new former_as_current >= half of old former_as_current (rounded up), when old >= 2.
Validity: the sealed panel needs >= 30 rows with a former item and the old reader needs >= 2 former-as-current saves;
otherwise the panel cannot test the change and the verdict is INCONCLUSIVE (reported as such, not as a pass).

## Report only (no bar)
Dev (scripts/claude_lis319f_score.py dev) for both readers; lis-319's dev score (claude_lis300_score.py --threshold
0.995) for the new reader on the lis-319f dev set; per-kind panel counts.
Not in this change: the job + place relation rule (the report's second fix) and the save checker (paused).
