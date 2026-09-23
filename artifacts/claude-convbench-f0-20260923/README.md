# convbench-f0: conversation benchmark, step F0

Blind-written everyday dialogs for the talking line's conversation benchmark
(step F0 of design/v3/30-modes/talk-fluency-plan.md).

## Files

- `dialogs.jsonl`: 40 multi-turn dialogs, one line per user turn.
- `README.md`: this file.
- `SEAL.sha256.txt`: sha256 seal of the two files above.

## Format (dialogs.jsonl)

One JSON object per line with exactly these keys:

- `dialog_id`: `conv-f0-01` through `conv-f0-40`
- `turn_index`: 0-based index of the user turn within its dialog
- `user_text`: the user's message; casual everyday chat with an assistant
  that keeps a notebook of facts about people
- `kind`: one of `teach` / `ask` / `correct` / `smalltalk` / `other`
- `gold`:
  - `teach` turns: stored triple `Subject|relation|Object`
  - `ask` turns: the exact expected value
  - `smalltalk` turns: `"smalltalk"`
  - `correct` / `other` turns: `"none"`

Dialog lengths: 6 to 10 user turns each. All person names are fictional and
freshly invented for this benchmark.

## Counts per kind (user turns)

| kind      | count |
|-----------|------:|
| teach     |    84 |
| ask       |    84 |
| smalltalk |    68 |
| correct   |    10 |
| other     |    40 |
| **total** | **286** |

Dialogs: 40. Dialogs containing at least one correction: 10.
