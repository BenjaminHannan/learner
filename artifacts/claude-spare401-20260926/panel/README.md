# corrpanel401 test bank (sf-401), escrow copy

TEST-ONLY. Never train on, tune on, quote or read these items. This README gives counts only;
no item is quoted. Format: the 331 end-to-end bank format (month-end/331-e2e-bank-spec.md, "Files a writer
produces"), plus `decoys.jsonl` and `corrections.jsonl` as defined in the sf-401 panel spec.

## Files

- `turns.jsonl`: 628 user turns
- `truth.jsonl`: 484 facts (64 closed by a correction)
- `decoys.jsonl`: 47 decoy turns
- `corrections.jsonl`: 64 correction turns

Lives: 24 (`sf-t-01`..`sf-t-24`), 3 days each, 5 to 9 user turns per day. Turns per life: 25 to 27.

## Turns per kind

| kind | count |
|---|---:|
| `teach` | 206 |
| `correct` | 64 |
| `nosave` | 45 |
| `ask` | 232 |
| `smalltalk` | 81 |
| `creative` | 0 |
| `other` | 0 |

Teach turns by shape: one fact 63, 2-3 facts in one message 101, fact in passing or in an aside 42.

## Asks per ask_type

| ask_type | count |
|---|---:|
| `one_hop` | 68 |
| `two_hop` | 24 |
| `reversal` | 24 |
| `edit` | 70 |
| `yesno` | 22 |
| `never_told` | 24 |
| `partial` | 0 |

Edit asks by shape: one-hop 31, two-hop through the corrected fact 24, yes/no 15.
Asks on day 3 about facts taught on day 1 and never corrected: 76.

## Turns per day

| day | total | teach | correct | nosave | ask | smalltalk |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 216 | 168 | 0 | 24 | 0 | 24 |
| 2 | 204 | 38 | 64 | 21 | 48 | 33 |
| 3 | 208 | 0 | 0 | 0 | 184 | 24 |

## Corrections per style

| style | meaning | count |
|---:|---|---:|
| 1 | own mistake, old value named | 11 |
| 2 | own mistake, old value not named | 11 |
| 3 | real change, old value named | 11 |
| 4 | real change, old value not named | 11 |
| 5 | negation plus new value | 10 |
| 6 | said in passing inside another message | 10 |

## Decoys per style

| style | count |
|---|---:|
| `second_value` | 8 |
| `same_value_other_person` | 10 |
| `visit_not_move` | 9 |
| `past_said_as_past` | 11 |
| `plan_or_question` | 9 |

Decoy turns by kind: teach 18, nosave 20, smalltalk 9. Each decoy is checked by a later non-edit ask whose gold is the unchanged value.

## Names

All people, pets, towns, companies, schools and clinics are invented for this bank, except real countries and
big real cities used as places. No person or pet name is shared between lives, and no proper-noun value repeats
across lives. No names from the 331 DEV bank or from the spec's examples are used.
