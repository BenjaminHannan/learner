# Bank DEV (spec 331)

Ordinary dev data; builders may read it. 10 lives, ids `e2e-dev-01`..`e2e-dev-10`, 3 days each,
194 user turns, 131 facts on the truth sheet (10 of them closed by a correction).

Files: `turns.jsonl` (one object per user turn), `truth.jsonl` (one object per fact).

## Names

Every person's and pet's first name starts with a letter from **S to Z**. Invented towns, companies,
clinics and the like also start with S to Z, and so do the real big cities used as places. No person
or pet name repeats across lives.

## Counts per kind

| kind | count | DEV minimum (bank / 4, rounded up) |
|---|---:|---:|
| teach | 59 | 35 |
| correct | 10 | 7 |
| nosave | 15 | 7 |
| ask | 71 | 53 (sum of ask minimums) |
| smalltalk | 29 | 13 |
| creative | 10 | 8 |
| other | 0 | - |

Teach breakdown: 19 single-fact turns (min 18), 40 turns with 2 or more facts (min 10); at least 10 of
the teach turns give a fact in passing or inside an aside (min 8).

## Counts per ask_type

| ask_type | count | DEV minimum |
|---|---:|---:|
| one_hop | 16 | 15 |
| two_hop | 11 | 9 |
| reversal | 10 | 7 |
| edit | 10 (7 of them two-hop through the corrected fact) | 7 (3 two-hop) |
| yesno | 9 | 4 |
| never_told | 10 | 8 |
| partial | 5 | 3 |

Asks on day 3 whose facts were all taught on day 1: 19 (minimum 15).

## Counts per day

| day | turns | teach | correct | nosave | ask | smalltalk | creative |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 63 | 41 | 0 | 10 | 0 | 12 | 0 |
| 2 | 61 | 18 | 10 | 5 | 19 | 7 | 2 |
| 3 | 70 | 0 | 0 | 0 | 52 | 10 | 8 |

Asks by day: day 2 has one_hop 12, two_hop 5, reversal 2; day 3 has edit 10, reversal 8, two_hop 6,
yesno 9, never_told 10, one_hop 4, partial 5. Each life has 19 or 20 turns, with 5 to 7 turns per day.

## Conventions

- Fact ids are `devNN-fMM`; `MM` is a label local to the life and is not in teaching order.
- `gold.values` is empty for `yesno` and `never_told`; for `yesno` the `uses_facts` are the facts that
  decide the answer from the notebook as it stands.
- For `reversal` asks the gold value is the fact's owner (the thing asked for), not its value.
- For `partial` asks the gold value is the known first-hop value; the second hop was never taught.
- For `two_hop` and two-hop `edit` asks, `values` holds only the final answer; `uses_facts` holds both hops.
- A correction may change the relation as well as the value;
  the old fact is closed at the correcting turn either way.

## Checks run (spec 331, five checks)

1. Every line parses and has exactly the spec keys: pass.
2. Every `uses_facts` id exists, was taught before the ask and was not closed before it: pass.
3. Every gold value equals the value (or, for reversal, the owner) of a fact it cites, after corrections: pass.
4. Every name obeys S to Z and no name repeats across lives: pass.
5. Kind and ask_type minimums (bank / 4, rounded up) are met: pass.
