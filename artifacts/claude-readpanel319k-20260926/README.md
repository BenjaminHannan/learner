# claude-readpanel319k-20260926: corrections panel for lis-319k (TEST-ONLY)

TEST-ONLY: never read, train or tune on; runners read it; scorers print counts only.

Tests lis-319k (facts the reader labels CORRECT save at 0.95 instead of 0.995) on fresh everyday chat. Written from
scratch by a separate agent from a brief only (WRITER.md; no repo files; names checked against the dev name list: 0 clashes);
all names fictional; nothing from any benchmark. A blind second labeller (LABELLER.md) saw only the dialogs; a third
blind agent (ADJUDICATE.md) ruled on the rows where they disagreed. The reading thread never read panel text; every
check ran as a script printing counts. Marks were registered before this panel existed
(artifacts/claude-lis319k-20260926/PASSMARKS.md, main 6bd125ee5).

## Files
- `panel.jsonl`: the key. Rows {id, dialog, t, kind (ordinary|correction|lookalike), reason, prev_reply, turn, facts,
  replaced}. facts carry needs_history and correction (true = replaces a value stated earlier or mis-echoed in
  prev_reply); replaced = the old values (also on negation-only rows, which have no facts).
- `label_B.jsonl`, `adjudication.jsonl`: the blind second labels and the rulings. WRITER/LABELLER/ADJUDICATE.md: briefs.
- `AUDIT.md`: agreement counts. `SEAL.sha256.txt`: sha256 of the files above.
Tools (code only): artifacts/claude-lis319k-20260926/panel_tools/agree.py, finalize.py.

## Counts
| | n |
|---|---|
| dialogs | 30 |
| rows | 240 (ordinary 120, correction 60, lookalike 60) |
| current facts | 239 (38 need history) |
| correction facts | 60 |
| replaced items | 68 |
| rows with no current fact | 70 |
One mid-dialog row the adjudicator dropped as ambiguous stays in the file (its history feeds later rows) with an empty
key (adjudicated_drop true): a save there counts as wrong.
