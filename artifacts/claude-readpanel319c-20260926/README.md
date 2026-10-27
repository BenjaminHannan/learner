# claude-readpanel319c-20260926: save-bar blind panel (lis-319c)

TEST-ONLY: never read, train or tune on; runners read it; scorers print counts only.

Tests the lis-319 reader's save bar (0.98 vs 0.995) on fresh everyday chat. Written from scratch by a separate Opus agent from a
brief only (no repo files; names checked against the dev name list: 0 clashes); all names fictional; nothing from any benchmark.

## Files
- `panel.jsonl`: the key, same schema as readpanel319 plus `kind` (long_multi / short / backref / nosave).
- `label_B.jsonl`: a blind second labeller's labels (never saw the key).
- `adjudication.jsonl`: a third blind agent's ruling on the 37 rows where key and B disagreed.
- `AUDIT.md`: agreement counts. `SEAL.sha256.txt`: sha256 of the files above.

## Counts
| | n |
|---|---|
| dialogs | 30 |
| rows | 239 (d29-t7 dropped as ambiguous; last turn of its dialog, so no other row's history changes) |
| facts | 424 (58 needs_history) |
| rows with no facts | 68 |
| kinds | long_multi 65, short 64, backref 42, nosave 68 |
