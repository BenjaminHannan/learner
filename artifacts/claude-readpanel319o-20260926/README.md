# claude-readpanel319o-20260926: history-owner panel for lis-319o (TEST-ONLY)

TEST-ONLY: never read, train or tune on; runners read it; scorers print counts only. Sealed 2026-09-26 16:08 UTC.

Tests lis-319o (the compiler accepts an owner named in earlier turns) on fresh everyday chat. Marks were registered before
this panel existed (artifacts/claude-lis319o-20260926/PASSMARKS.md, main 76cb540bc, addendum 1 main 075118317).
Written from scratch by a separate agent from a brief only (WRITER.md, plus its "Addition"; no repo files). Names were checked
against the dev name list by script (0 clashes). All names are fictional, and nothing comes from any benchmark. A blind second
labeller (LABELLER.md) saw only the dialogs. A third blind agent (ADJUDICATE.md) ruled on the rows where they disagreed.
The reading thread never read panel text; every check ran as a script printing counts.

## Files
- panel.jsonl: the key. Rows {id, dialog, t, kind (ordinary|history_owner|lookalike), reason, prev_reply, turn, facts,
  replaced}; facts carry needs_history and correction.
- label_B.jsonl, adjudication.jsonl: the blind second labels and the rulings. WRITER/LABELLER/ADJUDICATE.md: the briefs.
- AUDIT.md: agreement counts. SEAL.sha256.txt: sha256 of the files above.
Tools (code only): artifacts/claude-lis319k-20260926/panel_tools/agree.py, finalize.py.

## Counts
| | n |
|---|---|
| dialogs | 30 (all name two or more people before the first history-owner turn) |
| rows | 240 (ordinary 100, history_owner 80, lookalike 60; lookalike reasons: ambiguous 10, negation_only 8, 7 each of question, plan, doubt, someone_else, hypothetical, confirm) |
| current facts | 240 (86 need history) |
| correction facts | 30 |
| replaced items | 38 |
| rows with no current fact | 72 (8 of them are adjudicated drops kept empty mid-dialog; a save there counts as wrong) |
