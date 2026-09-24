# chatpanel338 v2 audit (blind key audit, 2026-09-24)

Scope: all 60 conversations (400 turns) read in full against spec 338 checks 1 to 6.
Turn index is 0-based. No panel text is quoted here.

## Fixes

| item_id | turn | issue type | fix |
|---|---|---|---|
| chat-05 | 3 | 4 reply-dependence | followup reworded so it no longer reads as reacting to a specific suggestion the assistant may not have made |
| chat-11 | 1 | 3 teach facts | added the amount-owed fact the turn states (the later ask_known gold relies on it); owner USER |
| chat-23 | 1 | 3 teach facts | added the wedding-month fact the turn states (the later ask_known gold relies on it); owner USER |
| chat-35 | 1 | 3 teach facts | relation renamed from an inferred country-of-origin claim to where the user says they moved from |
| chat-48 | 2 | 3 teach facts | value restored to the approximate amount the turn states (it had dropped the approximation) |

Counts by issue type: 1 ask_known gold = 0; 2 ask_unknown = 0; 3 teach facts = 4; 4 reply-dependence = 1; 5 names/titles = 0; 6 realism/kind labels = 0. Total 5.

## Checked, no change needed

- ask_known (15): every gold appears verbatim in an earlier turn of its conversation and each question has one answer.
- ask_unknown (10): each asks about the user's own life; none is answered anywhere in its conversation, directly or indirectly.
- Names: 12 person names, all first letters N to Z, none repeated across conversations; pet names also fall in N to Z; no real public figures; book and film titles are made up. Real countries appear only as places.
- Kinds: labels match the turns; no kind was changed, so README counts are unchanged from v1.
- Structure: keys exact, 60 conversations, 4 to 7 turns each, at most one teach and one ask_known per conversation, 40/15/10 conversations with teach/ask_known/ask_unknown.

## Accepted, not fixed

- teach + ask_known + ask_unknown share is 16.2% vs the implied 10% (writer's known issue: the spec's own minimums force it). The five named kinds are within 5 points of their targets.
