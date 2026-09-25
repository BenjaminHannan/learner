# notepanel378 audit (TEST-ONLY, counts only)

> Sealed test panel. Never quote dialogs, names, questions or answers from this folder.

Blind answerer B (`answer_B.jsonl`, 180 rows) answered from the blind files only and was compared with the key.

Rules: an answer agrees when it has the same meaning (for `time`, the same time; for `none`, only "not mentioned" matches "not mentioned"). Evidence agrees when B shares at least one turn with the key (for `none`, both are empty). For `multi`, the table also counts how many key turns B gave. Answer meaning was judged by hand, question by question. Evidence was counted by script.

## Before audit (original key, 180 questions)

| type | n | answer agree | evidence overlap | multi: key turns given / key turns | multi: all key turns given |
|---|---|---|---|---|---|
| single | 30 | 30 | 30 | | |
| time | 30 | 30 | 30 | | |
| multi | 30 | 30 | 30 | 64 / 68 | 26 of 30 |
| latest | 30 | 30 | 30 | | |
| preference | 30 | 30 | 30 | | |
| none | 30 | 30 | 30 | | |
| total | 180 | 180 | 180 | | |

No answer disagreed. 22 questions had evidence sets that differed from the key (B gave extra turns or left some out). Each one was reviewed.

## Decisions (22 reviewed)

- Key fixes: 3 (1 multi, 1 multi, 1 latest). In each case B named a turn that also holds part of the answer, so that turn was added to the key's evidence.
- Rewrites: 3 (all multi). The original question could be answered from one turn, so it was reworded (still type multi) so that every evidence turn is needed. Their answers changed, so B's answers to these no longer apply and need a fresh blind answer.
- Left: 16. B gave extra context turns (for example, the earlier value of a changed item) or left out a turn the key needs for context; its answers were already correct.

All checks were re-run after the edits and passed with 0 errors. The blind files were rebuilt: the blind dialogs are unchanged and 3 blind questions were reworded.

## After audit (current key)

| type | n | answer agree | evidence overlap | multi: key turns given / key turns | multi: all key turns given | pending re-answer |
|---|---|---|---|---|---|---|
| single | 30 | 30 | 30 | | | 0 |
| time | 30 | 30 | 30 | | | 0 |
| multi | 30 | 27 of 27 scored | 27 of 27 scored | 63 / 64 | 26 of 27 | 3 |
| latest | 30 | 30 | 30 | | | 0 |
| preference | 30 | 30 | 30 | | | 0 |
| none | 30 | 30 | 30 | | | 0 |
| total | 180 | 177 of 177 scored | 177 of 177 scored | | | 3 |
