# Judge B: 138i vs 138k on the exp 239 subset (61 turns). TEST-ONLY

**Result first:** on my subset, 138k is no more correct than 138i: 20 of 61 in both, and 25 of 61 grammatical in both. The mean naturalness went up a little, from 2.66 to 2.84. There was 1 bad write in each.

The panel seal check passed. Before grading, I checked the change list against my own comparison of the two transcripts, and they matched on all 244 turns. 13 of my 61 subset turns changed, and I re-graded those blind from the panel, the 138k transcript and the stored facts. The other 48 turns carry their 138i grades over (carried=true).

## Rates

| Measure | 138i | 138k |
|---|---|---|
| grammatical = yes | 25 / 61 (41%) | 25 / 61 (41%) |
| correct = yes | 20 / 61 (33%) | 20 / 61 (33%) |
| natural, mean | 2.66 | 2.84 |
| bad_write = yes | 1 / 61 | 1 / 61 |
| re-graded turns | n/a | 13 (48 carried) |

On the 13 changed turns alone: grammatical went from 3 to 3, correct from 0 to 0, and mean natural from 2.15 to 3.00.

| Main mistake | 138i | 138k |
|---|---|---|
| none | 17 | 17 |
| other | 14 | 14 |
| misread_request | 10 | 11 |
| missing_write | 9 | 9 |
| missed_known_fact | 5 | 4 |
| odd_or_broken_sentence | 3 | 3 |
| wrong_subject | 2 | 0 |
| wrong_value | 0 | 1 |
| ignored_correction | 0 | 1 |
| bad_write | 1 | 1 |

## What changed (general words)
- **Unsaved teach sentences:** 9 changed turns fall in this group. They now get an honest, clear reply saying the fact could not be saved, with an example of a form that works. This reads better than the old glued fallback. It still ends a question without a question mark, so I marked it ungrammatical. No facts were saved on any of these turns.
- **Questions about the agent itself:** these now describe the agent as software being taught, instead of answering about the user. It still says it has no name and does not give its name, so neither turn became correct.
- **A question mistaken for a teach:** one question about a stored fact now gets the cannot-save reply, as if the user had been teaching it something.
- **A correction that did not stick:** in one conversation, the first workplace fact is now saved, but the correction after it is not. The later question returns the old value. The mistake moved from a knock-on error to ignoring the correction.

## What it means
On my subset, 138k's replies to failures read more politely and clearly, and it describes itself better. It gets no more turns right than 138i.

## What it doesn't mean
This is one judge on a quarter of the turns. Some of the other 183 changed or unchanged turns may show gains that this subset misses. Scoring the 48 carried grades again would give the same values by design. None of this has been checked against Judge A.
