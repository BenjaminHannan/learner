# Bank H (gram364, spec 331 format)

Written blind on 2026-09-25 in the format of bank DEV. 10 lives, ids `e2e-g364-01`..`e2e-g364-10`, 3 days each,
199 user turns, 123 facts on the truth sheet (10 of them closed by a correction).

Files: `turns.jsonl` (one object per user turn), `truth.jsonl` (one object per fact), `check_bank.py` (the five checks).

## Names

Every person's and pet's first name starts with a letter from **A to D**. Invented towns, companies, clinics,
schools, farms, stables and the like also start with A to D, and so do the real big cities (and the one real
town) used as places. No person, pet or place name repeats across lives.

## Counts per kind

| kind | count | minimum (spec / 4, rounded up) |
|---|---:|---:|
| teach | 59 | 35 |
| correct | 10 | 7 |
| nosave | 17 | 7 |
| ask | 72 | 53 (sum of ask minimums) |
| smalltalk | 31 | 13 |
| creative | 10 | 8 |
| other | 0 | - |

Teach breakdown: 21 single-fact turns (min 18), 38 turns with 2 or more facts (min 10); 10 of the teach turns
give a fact in passing or inside an aside (min 8; counted by the writer, not by the checker).

## Counts per ask_type

| ask_type | count | minimum |
|---|---:|---:|
| one_hop | 17 | 15 |
| two_hop | 11 | 9 |
| reversal | 10 | 7 |
| edit | 10 (all 10 two-hop through the corrected fact) | 7 (3 two-hop) |
| yesno | 10 (6 yes, 4 no) | 4 |
| never_told | 10 | 8 |
| partial | 4 | 3 |

Asks on day 3 whose facts were all taught on day 1: 22 (minimum 15).

## Counts per day

| day | turns | teach | correct | nosave | ask | smalltalk | creative |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 67 | 40 | 0 | 10 | 0 | 17 | 0 |
| 2 | 62 | 19 | 10 | 7 | 22 | 4 | 0 |
| 3 | 70 | 0 | 0 | 0 | 50 | 10 | 10 |

Asks by day: day 2 has one_hop 12, two_hop 6, reversal 4; day 3 has edit 10, reversal 6, two_hop 5,
yesno 10, never_told 10, one_hop 5, partial 4. Each life has 19 or 20 turns, with 6 or 7 turns per day.

## Conventions

- Fact ids are `g364NN-fMM` (`NN` = life number); `MM` is a label local to the life and is not in teaching order.
- `gold.values` is empty for `yesno` and `never_told`; for `yesno` the `uses_facts` are the facts that
  decide the answer from the notebook as it stands.
- For `reversal` asks the gold value is the fact's owner (the thing asked for), not its value.
- For `partial` asks the gold value is the known first-hop value; the second hop was never taught.
- For `two_hop` and two-hop `edit` asks, `values` holds only the final answer; `uses_facts` holds both hops
  (one two_hop ask, in life 06, runs three hops and cites all three).
- The old fact is closed at the correcting turn; every correction here keeps the relation and changes the value.

## Checks run (spec 331, five checks; `python3 check_bank.py`)

1. Every line parses and has exactly the spec keys: pass.
2. Every `uses_facts` id exists, was taught before the ask and was not closed before it: pass.
3. Every gold value equals the value (or, for reversal, the owner) of a fact it cites, after corrections: pass.
4. Every name obeys A to D and no name repeats across lives: pass.
5. Kind and ask_type minimums (bank / 4, rounded up) are met: pass.

Check 1 also confirms turn order, 4 to 7 turns per day, that truth and the turns' `facts` lists match one to one,
and that each correction closes an older fact at its own turn. Check 2 also covers `creative_seed_facts`.
Check 3 also requires two-hop answers to be the last hop of a chain and edit answers to be the corrected value.
Check 4 also scans the user text: capitalised mid-sentence words must be A to D names (weekdays, months and
"I" excepted), and no life's text uses another life's names.
