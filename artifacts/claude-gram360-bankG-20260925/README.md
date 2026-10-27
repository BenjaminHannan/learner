# Bank G (gram360, spec 331 format)

Written blind on 2026-09-25 in the format of bank DEV. 10 lives, ids `e2e-g360-01`..`e2e-g360-10`, 3 days each,
194 user turns, 134 facts on the truth sheet (10 of them closed by a correction).

Files: `turns.jsonl` (one object per user turn), `truth.jsonl` (one object per fact), `check_bank.py` (the five checks).

## Names

Every person's and pet's first name starts with a letter from **E to J**. Invented towns, companies, clinics,
schools and the like also start with E to J, and so do the real big cities (and the one country and one island)
used as places. No person, pet or place name repeats across lives.

## Counts per kind

| kind | count | minimum (spec / 4, rounded up) |
|---|---:|---:|
| teach | 59 | 35 |
| correct | 10 | 7 |
| nosave | 15 | 7 |
| ask | 71 | 53 (sum of ask minimums) |
| smalltalk | 29 | 13 |
| creative | 10 | 8 |
| other | 0 | - |

Teach breakdown: 19 single-fact turns (min 18), 40 turns with 2 or more facts (min 10); 12 of the teach turns
give a fact in passing or inside an aside (min 8; counted by the writer, not by the checker).

## Counts per ask_type

| ask_type | count | minimum |
|---|---:|---:|
| one_hop | 16 | 15 |
| two_hop | 11 | 9 |
| reversal | 10 | 7 |
| edit | 10 (7 of them two-hop through the corrected fact) | 7 (3 two-hop) |
| yesno | 9 (5 yes, 4 no) | 4 |
| never_told | 10 | 8 |
| partial | 5 | 3 |

Asks on day 3 whose facts were all taught on day 1: 21 (minimum 15).

## Counts per day

| day | turns | teach | correct | nosave | ask | smalltalk | creative |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 63 | 41 | 0 | 10 | 0 | 12 | 0 |
| 2 | 61 | 18 | 10 | 5 | 19 | 7 | 2 |
| 3 | 70 | 0 | 0 | 0 | 52 | 10 | 8 |

Asks by day: day 2 has one_hop 12, two_hop 5, reversal 2; day 3 has edit 10, reversal 8, two_hop 6,
yesno 9, never_told 10, one_hop 4, partial 5. Each life has 19 or 20 turns, with 6 or 7 turns per day.

## Conventions

- Fact ids are `g360NN-fMM` (`NN` = life number); `MM` is a label local to the life and is not in teaching order.
- `gold.values` is empty for `yesno` and `never_told`; for `yesno` the `uses_facts` are the facts that
  decide the answer from the notebook as it stands.
- For `reversal` asks the gold value is the fact's owner (the thing asked for), not its value.
- For `partial` asks the gold value is the known first-hop value; the second hop was never taught.
- For `two_hop` and two-hop `edit` asks, `values` holds only the final answer; `uses_facts` holds both hops.
- The old fact is closed at the correcting turn; every correction here keeps the relation and changes the value.

## Checks run (spec 331, five checks; `python3 check_bank.py`)

1. Every line parses and has exactly the spec keys: pass.
2. Every `uses_facts` id exists, was taught before the ask and was not closed before it: pass.
3. Every gold value equals the value (or, for reversal, the owner) of a fact it cites, after corrections: pass.
4. Every name obeys E to J and no name repeats across lives: pass.
5. Kind and ask_type minimums (bank / 4, rounded up) are met: pass.

Check 1 also confirms turn order, 4 to 7 turns per day, that truth and the turns' `facts` lists match one to one,
and that each correction closes an older fact at its own turn. Check 2 also covers `creative_seed_facts`.
Check 3 also requires two-hop answers to be the last hop of a chain and edit answers to be the corrected value.
Check 4 also scans the user text: capitalised mid-sentence words must be E to J names (weekdays, months and
"I" excepted), and no life's text uses another life's names.
