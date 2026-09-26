# claude-readpanel371c-20260926: "used to" panel for lis-319f (TEST-ONLY)

TEST-ONLY: never read, train or tune on; runners read it; scorers print counts only.

Tests lis-319f (a FORMER mode) against lis-319 on fresh everyday chat. Written from scratch by a separate Opus agent from a
brief only (WRITER.md; no repo files; names checked against the dev name list: 0 clashes); all names fictional; nothing from
any benchmark. A blind second labeller (LABELLER.md) saw only the dialogs; a third blind agent (ADJUDICATE.md) ruled on the
rows where they disagreed. The reading thread never read panel text; every check ran as a script printing counts.

## Files
- `panel.jsonl`: the key. Rows {id, dialog, t, kind, prev_reply, turn, facts, former, nosave_reason}. `facts` = current,
  stated-as-true facts; `former` = details that used to be true and no longer are.
- `label_B.jsonl`, `adjudication.jsonl`: the blind second labels and the rulings. WRITER/LABELLER/ADJUDICATE.md: briefs.
- `AUDIT.md`: agreement counts. `SEAL.sha256.txt`: sha256 of the files above.

## Counts
| | n |
|---|---|
| dialogs | 30 |
| rows | 240 |
| kinds | long_multi 48, short 38, backref 43, former 48, nosave 63 |
| current facts | 355 (60 need history) |
| rows with a former item | 49 (64 items) |
| rows with no current fact | 90 |
One mid-dialog row the adjudicator dropped as ambiguous stays in the file (its history feeds later rows) with an empty key
(nosave_reason dropped_ambiguous, adjudicated_drop true): a save there counts as wrong.
