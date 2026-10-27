# Judge B: 138l vs 138m on the exp 239 subset. TEST-ONLY

**Result first:** on my 61-turn subset, 138m is correct on 2 more turns than 138l (23 vs 21). Grammatical replies nearly double (47 vs 24), and mean naturalness rises from 2.85 to 3.34. There are no bad writes in either version. Most of the gain comes from replacing the garbled fallback with one clean sentence. That change does not make the agent answer any more memory questions.

The panel seal check passed. I regraded 39 subset turns from scratch: every subset turn whose own reply changed, or where an earlier reply in the same conversation changed. The other 22 subset turns carry their 138l grades (carried=true). The file keeps the same 74 rows as grades-138l-subset.jsonl. The 13 rows outside the subset stay in_subset=false and are not counted in the rates below. Three of those 13 rows had a changed reply, so I regraded them as well (carried=false) instead of carrying stale grades. The other 10 carry over.

## Subset rates (61 turns)

| Measure | 138l | 138m |
|---|---|---|
| grammatical = yes | 24 (39%) | 47 (77%) |
| correct = yes | 21 (34%) | 23 (38%) |
| natural, mean | 2.85 | 3.34 |
| bad_write = yes | 0 | 0 |

| Main mistake | 138l | 138m |
|---|---|---|
| none | 18 | 23 |
| other (knock-on from an unsaved fact) | 15 | 15 |
| misread_request | 10 | 10 |
| missing_write | 9 | 9 |
| missed_known_fact | 4 | 3 |
| odd_or_broken_sentence | 3 | 0 |
| wrong_value | 1 | 0 |
| ignored_correction | 1 | 1 |

## Regraded subset turns (39): better / worse / same

| Category | Better | Worse | Same |
|---|---|---|---|
| grammatical | 23 | 0 | 16 |
| correct | 5 | 3 | 31 |
| natural | 25 | 0 | 14 |
| bad_write | 0 | 0 | 39 |

The mistake label changed on 8 turns: 5 moved to none (3 from misread_request, 1 from missed_known_fact, 1 from wrong_value), and 3 moved from odd_or_broken_sentence to misread_request.

## Out-of-subset rows with a changed reply (3, not counted above)
- All 3 are grammatical, none are correct, natural 3 each. All 3 are knock-on errors, since the fact was never saved.

## What changed (general words)
- **Clean fallback:** the three-part garbled fallback is now one clear sentence that asks the user to rephrase. I mark it grammatical, with naturalness 3. This accounts for almost all of the grammar and naturalness gains.
- **Self questions fixed:** the agent now gives its name and says who built it. Those turns became correct.
- **Small talk:** small-talk turns asking how the agent is now get a friendly ready-to-learn reply instead of a mode-status line. I count these as correct.
- **One stored-name question** is now answered correctly.
- **Three turns got worse on correctness:** these are questions where the right answer was to abstain, say no, or say it cannot check. The old fallback included a not-knowing part, so under my convention it counted as an acceptable abstain. The new fallback only says it did not understand, so it does not abstain and I mark it misread_request.
- **Unchanged:** no teach behaviour changed on my subset. Unsaved facts still cause the same knock-on failures, and chain questions over stored facts still fail.

## What it means
138m reads much better, and it handles questions about itself. On memory tasks it is no better than 138l, and it is slightly worse on turns where the right answer is to abstain.

## What it doesn't mean
This is one judge, grading by hand, on a quarter of the turns. A two-turn difference in correctness is within grading noise. The three "worse" turns depend on my convention for when a fallback counts as an abstain. None of this has been checked against Judge A.
