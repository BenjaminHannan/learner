# stylepanel339 v2: blind key audit

Auditor read all 60 lives in v1 in full (768 turns) against the spec and six audit checks. No panel text is quoted here.
v2 = copy of v1 plus the fixes below. Only `user_text` changed on the listed turns. No ids, days, turn_index values,
kinds, lives.jsonl rows, truth.jsonl or README counts changed.

## Fixes

| life_id | turn_index | issue type | fix |
|---|---|---|---|
| sty-01 | 11 | 4: depends on an earlier exchange | The turn asked the assistant to repeat an explanation that was never given in this life. Reworded as a fresh question on the same topic. |
| sty-09 | 2 | 1: feedback carries a second preference | The no_questions feedback also hinted at wanting shorter replies. Removed that part so only no_questions is signalled. |
| sty-41 | 2 | 6: typing style out of character | The feedback turn was the only sentence-case turn in an all-lowercase life, so the style change gave it away. Lowercased it to match; the wording is the same. |
| sty-54 | 11 | 2: look-alike too weak | The control's only look-alike was a passing use of one shared word. Replaced a filler turn with a clear look-alike about a third party, using no_questions-style wording, that is not about the assistant. |

## Counts by issue type
- 1 (feedback clarity / preference / detail): 1
- 2 (control look-alike / no feedback): 1
- 3 (preference visible on days 2 and 3): 0
- 4 (depends on assistant reply): 1
- 5 (names / public figures): 0
- 6 (casual typing): 1

## Checked and passing (no change)
- All 40 feedback turns are on day 1, one per life, and match `preference`. All 5 no_nickname and 5 name `detail` values match the word or first name given.
- All 20 controls contain no feedback about the assistant. Each has at least one look-alike turn (sty-54 after the fix).
- Days 2 and 3 of every feedback life have turns where the preference would show.
- Names: 16 distinct fictional first names, all A to M, none repeated across lives. No real public figures.
- Structure: 60 lives, 3 days each, 4 to 6 turns per day, turn_index contiguous, keys exact, preference spread 5 each, truth.jsonl empty.

## Noted, not changed
- Formal-preference and longer-preference users mostly write in polished full sentences, and casual-preference users write loosely. That is realistic, but a system could guess some preferences from the user's own style. This was left alone because fixing it would mean rewriting whole lives.
- Two no_nickname feedback turns give a similar reason. They are still distinct turns, so they were left as written.
