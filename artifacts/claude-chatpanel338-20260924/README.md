# chatpanel338 (TEST-ONLY)

Test-only panel: never train on, tune on, quote, or show to builders.

## Counts

- conversations: 60
- turns: 400
- turns per conversation: 4 turns = 2 conversations, 5 turns = 1 conversations, 6 turns = 12 conversations, 7 turns = 45 conversations

| kind | turns | share |
|---|---|---|
| smalltalk | 75 | 18.8% |
| advice | 91 | 22.8% |
| explain | 68 | 17.0% |
| feelings | 34 | 8.5% |
| followup | 67 | 16.8% |
| teach | 40 | 10.0% |
| ask_known | 15 | 3.8% |
| ask_unknown | 10 | 2.5% |

- conversations with a teach turn: 40 (none in 20)
- conversations with an ask_known turn: 15
- conversations with an ask_unknown turn: 10

## Notes

- `facts` is `[]` on every non-teach turn; `gold` is `null` on every non-ask_known turn.
- teach + ask_known + ask_unknown = 65 turns (16.2%). The spec's implied remainder is 10%, but its own minimums (40 teach + 15 ask_known + 10 ask_unknown = 65 turns, at most 7 turns x 60 conversations = 420) make at least 15.5% unavoidable, so the 5-point check is applied to the five named kinds only.
