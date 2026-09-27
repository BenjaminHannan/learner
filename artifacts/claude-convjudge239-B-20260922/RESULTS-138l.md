# Judge B: 138k vs 138l on the exp 239 subset. TEST-ONLY

**Result first:** on my 61-turn subset, 138l is one turn more correct than 138k (21 vs 20). It has one fewer grammatical reply (24 vs 25) and one fewer bad write (0 vs 1). Mean naturalness is flat (2.85 vs 2.84). The change is small, and most of it comes from cleaner saved values.

The panel seal check passed. Before grading, I checked the 138l change list against my own comparison of the 138k and 138l transcripts, and it matched on all 244 turns. I graded 28 turns blind:
- all 15 turns whose reply changed (2 are in my subset and 13 are outside it)
- 13 more subset turns whose stored facts, or an earlier reply in the same conversation, changed

The other 46 subset turns carry their 138k grades over (carried=true). In grades-138l-subset.jsonl, the 13 out-of-subset rows are marked in_subset=false, and they are not counted in the subset rates.

## Subset rates (61 turns)

| Measure | 138k | 138l |
|---|---|---|
| grammatical = yes | 25 (41%) | 24 (39%) |
| correct = yes | 20 (33%) | 21 (34%) |
| natural, mean | 2.84 | 2.85 |
| bad_write = yes | 1 | 0 |

| Main mistake | 138k | 138l |
|---|---|---|
| none | 17 | 18 |
| other (knock-on from an unsaved fact) | 14 | 15 |
| misread_request | 11 | 10 |
| missing_write | 9 | 9 |
| missed_known_fact | 4 | 4 |
| odd_or_broken_sentence | 3 | 3 |
| wrong_value | 1 | 1 |
| ignored_correction | 1 | 1 |
| bad_write | 1 | 0 |

## Re-graded subset turns (15): better / worse / same

| Category | Better | Worse | Same |
|---|---|---|---|
| grammatical | 0 | 1 | 14 |
| correct | 1 | 0 | 14 |
| natural | 1 | 0 | 14 |
| bad_write | 1 | 0 | 14 |
| mistake label | 1 (bad_write to none) | 0 | 13 |

One more label changed, from misread_request to other. On that turn, a wrong but grammatical reply was replaced by the garbled fallback. The turn is still not correct, and it now counts as grammatically worse.

## All 15 reply-changed turns (including 13 outside my subset)
- 4 of 15 grammatical, 4 of 15 correct, mean natural 2.87, 1 bad write.
- Mistakes: none 4, other 4, missing_write 4, misread_request 2, bad_write 1.

## What changed (general words)
- **Cleaner saved values:** teach sentences of the form "my X is called/named Y" now store just the name, not "called Y" or "named Y". These saves became correct.
- **Typo kept in a save:** one save still keeps the user's misspelled relation word, and repeats it back. I marked that as a bad write and as ungrammatical, which is my convention.
- **Questions still mistaken for teaches:** some questions, including ones about stored facts, now get the "couldn't save that" reply.
- **Stored facts still missed:** questions about stored facts still failed wherever the question used a relation phrase ("my grandson", "my name"), even when the value was now stored cleanly.

## What it means
On my subset, 138l saves some kinds of teach sentences more cleanly. That removed the one bad write I had, and gave one more correct turn. It does not yet answer the follow-up questions about those facts.

## What it doesn't mean
This is one judge, grading by hand, on a quarter of the turns plus the changed replies. A one-turn difference is within grading noise. None of this has been checked against Judge A.
