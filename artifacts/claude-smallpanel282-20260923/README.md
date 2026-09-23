# smallpanel282 — blind panel for exp 282 (casual greetings and closings)

60 turns total. All names (people, places, pets, teachers, streets, boats, bands) are freshly invented
and fictional. Written without reading any code or any other panel.

## Counts per category (per-turn)

| category | turns | description |
|---|---|---|
| greeting | 20 | casual greetings: lowercase, slang, little or no punctuation |
| closing | 15 | thanks and closings with a short tail (thats all / thats it / bye for now / see ya / bye) |
| mixed | 15 | a greeting or thanks plus a real teach (9) or a real question (6) |
| control | 10 | plain teaches (8, incl. 6 setup teaches for the mixed questions) and plain questions (2) |
| total | 60 | |

Dialog structure: d01-d20 single-turn greetings; d21-d35 single-turn closings; d36-d44 single-turn
mixed teaches; d45-d50 two-turn dialogs (turn 0 plain teach, turn 1 mixed question about that fact);
d51-d52 two-turn plain control dialogs (turn 0 teach, turn 1 question; d52 turn 1 asks about a
relation never taught, so the gold is abstain).

## Schema (panel.jsonl, one JSON object per line)

| field | meaning |
|---|---|
| dialog_id | dialog identifier (d01-d52); dialogs run with a fresh notebook each |
| turn_index | 0-based turn number within the dialog |
| user_text | the user turn text |
| category | one of: greeting, closing, mixed, control |
| gold | expected outcome for the turn (see below) |

Gold values:
- "smalltalk" — the turn is pure small talk; expect a fitting small-talk reply and no notebook write.
- exact fact string (e.g. a place or pet name) — a question whose fact was taught; expect that exact answer.
- "abstain" — a question whose fact was never taught; expect an abstain, not a guess.
- {"subject", "relation", "value"} triple — a teach turn; expect that triple stored (values in canonical capitalization).

Scorer notes: small-talk turns (gold "smalltalk") must produce zero writes. Mixed turns carry fact or
question content and must keep the base (260) route and result exactly; their golds are triples
(teaches) or exact facts (questions answered from the dialog's own turn-0 teach).
