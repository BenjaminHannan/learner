# claude-readpanel319-20260925: history-reading blind panel

TEST-ONLY: never read, train or tune on; runners read it; scorers print counts only.

Tests whether the fact-reader uses the earlier conversation (a pronoun, "my sister", "the kid" or a short answer resolved from earlier user turns). Written from scratch, all names fictional; no name from the dev name list.

## Files
- `panel.jsonl`: the key. One JSON per line: `{"id", "dialog", "t", "prev_reply", "turn", "facts": [{"owner", "relation", "value", "needs_history"}], "nosave_reason"}`. owner is `USER` for the speaker, else the full name as named in the dialog. value is the exact word from the turn (3 short answers take it from prev_reply).
- `label_B.jsonl`: the blind second labeller's labels (`{"id", "facts", "nosave_reason"}`), in full agreement with the key after resolution (see AUDIT.md).
- `AUDIT.md`: agreement counts.
- `SEAL.sha256.txt`: sha256 of the four files above.

## Counts
| | n |
|---|---|
| dialogs | 30 |
| rows (user turns) | 240 (8 per dialog) |
| rows with facts | 178 |
| rows with no facts | 62 |
| facts | 211 |
| facts with needs_history = true | 98 |
| short answers (value in prev_reply) | 3 |

nosave reasons: smalltalk 16, plan 11, negation 8, our_we 7, question 7, hypothetical 6, sarcasm 4, reported 3.

## Audit
Blind Opus labeller B: first pass 236/240 rows agreed, 211/211 facts matched; the 4 disagreements were nosave_reason only and were fixed in the key. Final: 240/240 rows, 211/211 facts, 0 disagreements. needs_history agreement 209/211 (not graded).
