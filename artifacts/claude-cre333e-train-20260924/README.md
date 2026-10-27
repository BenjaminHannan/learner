# claude-cre333e-train-20260924: write_creative training turns

`turns.jsonl`: 640 hand-written user turns for teaching a small assistant when to call its `write_creative` tool.
Each line has these keys: `{"id", "history", "text", "label", "type"}`. `history` holds 0-3 earlier user messages from the same chat.

## Counts

| label | type | count |
|---|---|---|
| 1 | gift | 54 |
| 1 | plan | 54 |
| 1 | poem_toast_card | 53 |
| 1 | cook_bring | 53 |
| 1 | message | 53 |
| 1 | other | 53 |
| **1** | **total** | **320** |
| 0 | fact_lookalike | 90 |
| 0 | recall_question | 90 |
| 0 | general_question | 50 |
| 0 | plain_fact | 40 |
| 0 | smalltalk | 50 |
| **0** | **total** | **320** |

## Notes
- Of the 320 label-1 texts, 285 (89.1%) avoid all of these: idea(s), suggest*, recommend*, gift*, present*, poem*, story/stories, song*, toast*, plan*, brainstorm*, "come up with" and "help me". The check matches words by prefix, so it also flags words like "planning" and "presentation".
- In a recall_question with a non-empty history, the answer is in that history. 9 recall questions have an empty history, so the assistant should say it wasn't told.
  - 6 of those texts also appear with a history that contains the answer. They are the only repeated texts in the file.
- Some label-0 turns follow an earlier creative request in the history (for example "thank u, she loved it" after a toast request). They are hard negatives.
- Every person and pet name is made up and starts with N, O, P, Q or R. Surnames used: Olsen, Ruizes.
- Rows are shuffled with seed 333. The generator and check scripts were kept in the session scratchpad and are not part of the repo.
