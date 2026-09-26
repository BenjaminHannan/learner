# Bank D (331 end-to-end conversation bank, TEST-ONLY)

Written blind to design/v3/30-modes/331-e2e-bank-spec.md and 331-bank-CD-addendum.md. Not to be trained on, tuned on, quoted or read by builders. No items are quoted here.

## Scope

- Lives: 40, ids `e2e-d-01`..`e2e-d-40`; 3 days each, 4 to 7 user turns per day (14 to 19 turns per life).
- Turns: 658. Facts in truth.jsonl: 352 (29 of them closed by a later correction).
- Names: every person and pet first name is an invented Nordic- or Slavic-sounding name (bank D rule; no letter range applies). 153 distinct person/pet names, none shared between lives. Towns and companies are invented; a few big real cities and countries appear as places. No real public figures.

## Counts per kind

| kind | count | spec minimum | day 1 | day 2 | day 3 |
|---|---:|---:|---:|---:|---:|
| `teach` | 224 | 140 | 138 | 86 | 0 |
| `correct` | 29 | 25 | 0 | 13 | 16 |
| `nosave` | 39 | 25 | 14 | 25 | 0 |
| `ask` | 244 | - | 12 | 24 | 208 |
| `smalltalk` | 86 | 50 | 42 | 38 | 6 |
| `creative` | 36 | 30 | 0 | 4 | 32 |
| `other` | 0 | - | 0 | 0 | 0 |

Teach breakdown: one fact in a message 98 (min 70), 2-3 facts in one message 81 (min 40), fact in passing or in an aside 45 (min 30).

## Counts per ask_type

| ask_type | count | spec minimum | day 1 | day 2 | day 3 |
|---|---:|---:|---:|---:|---:|
| `one_hop` | 68 | 60 | 11 | 14 | 43 |
| `two_hop` | 39 | 35 | 0 | 1 | 38 |
| `reversal` | 35 | 25 | 0 | 0 | 35 |
| `edit` | 30 | 25 | 0 | 5 | 25 |
| `yesno` | 23 | 15 | 0 | 2 | 21 |
| `never_told` | 36 | 30 | 1 | 2 | 33 |
| `partial` | 13 | 10 | 0 | 0 | 13 |

- Asks on day 3 whose facts were all taught on day 1: 82 (min 60).
- Edit asks that are two-hop through the corrected fact: 19 (min 10). Every edit ask uses a fact created by a correction.
- Turns per day (all kinds): day 1 206, day 2 190, day 3 262.

## Gold conventions

- `value` asks (one_hop, two_hop, reversal, edit): `values` holds the final answer, which is the `value` of a fact in `uses_facts`. For reversal asks the answer (a person or pet name) is the value of the relation fact that introduced that name, which is included in `uses_facts`.
- `yesno`: `type` is `yes` or `no`, `values` is empty, `uses_facts` lists the notebook facts that decide it.
- `never_told`: `type` `idk`, empty `values` and `uses_facts`; always about a person or thing that exists in that life.
- `partial`: `values` holds the known middle value; `uses_facts` holds the taught first hop(s).
- `nosave`, `smalltalk`, `creative` and `ask` turns carry no facts; `creative_seed_facts` lists facts a good answer could draw on.

## Writer checks (spec section "Checks")

| check | result |
|---|---|
| 1. every line parses, exact keys | pass |
| 2. uses_facts exist, taught before the ask, not closed before it | pass |
| 3. gold values equal the (post-correction) fact values | pass |
| 4. names follow the bank rule; no name repeats across lives | pass |
| 5. kind minimums met | pass |

Check 4 was run mechanically for uniqueness (each declared name belongs to one life, and no life text mentions another life's name); the Nordic/Slavic style was judged by the writer. Overlap with banks A, B, DEV and G could not be checked blind and is left to the escrow checker.
