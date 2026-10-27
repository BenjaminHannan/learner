# claude-readpanel320-20260926: fresh reading panel for lis-320 vs lis-319f (TEST-ONLY)

TEST-ONLY: never read, train or tune on it. Only the runners read it, and the scorers print counts only. Sealed 2026-09-26 17:35 UTC.

This is the test for lis-320, a reader trained only on GLM-worded chats with code labels, which must match lis-319f.
The marks were registered before this panel existed: artifacts/claude-lis320-20260926/PASSMARKS.md (main e8987ab81) and
ADDENDUM-1-ask-back.md (R7). The panel was written from scratch by a separate agent, working from its brief only
(WRITER.md and its two additions). It opened no repo files and never saw the lis-320 seeder, the GLM output or any training
data. A script checked names against the dev name list and found 0 clashes. All names are fictional, and nothing comes
from any benchmark. A blind second labeller (LABELLER.md) saw only the dialogs, and a blind adjudicator (ADJUDICATE.md)
ruled on the rows where the two disagreed. The reading thread never read panel text; every check ran as a script that
printed counts.
Known bias, as stated in PASSMARKS: the panel is Opus-written and lis-319f trained on Opus-written chats, so the panel
favours lis-319f.

## Files
- panel.jsonl is the key. Each row is {id, dialog, t, kind (ordinary|correction|backref|former|lookalike), reason,
  prev_reply, turn, facts, replaced, former}. Facts carry needs_history and correction. adjudicated_drop marks
  mid-dialog rows left empty; kind_changed_by_adjudication marks 4 look-alike rows the ruling gave a fact, which are
  now ordinary.
- label_B.jsonl and adjudication.jsonl hold the blind second labels and the rulings. WRITER.md, LABELLER.md and
  ADJUDICATE.md are the briefs.
- AUDIT.md has the agreement and diversity counts. SEAL.sha256.txt has the sha256 of the files above.
- The code-only tools are in artifacts/claude-lis320-20260926/panel_tools/ (prep, agree, finalize). Scorer:
  scripts/claude_lis320_score.py with scripts/claude_lis319k_score.py.

## Counts (validity bars from PASSMARKS in brackets)
| | n |
|---|---|
| dialogs / rows | 42 / 336 (d01-d40 plus d41-d42 from addition 2) |
| kinds | ordinary 124, backref 71, correction 29, former 31, lookalike 81 |
| current facts | 358 (99 need history) |
| correction facts | 52 [>= 40] |
| backref rows (kind backref or a needs_history fact) | 76 [>= 50] |
| former items | 36 [>= 30] |
| ambiguous rows (lookalike, no fact) | 14 [>= 10] |
| ack_after_ask rows (no fact) | 16 [>= 12] |
| yes_after_ask rows (fact taken from the question) | 11 |
| rows over 20 words with a fact | 75 |
| rows with no current fact | 122 (4 of them adjudicated drops; a save there counts as wrong) |
