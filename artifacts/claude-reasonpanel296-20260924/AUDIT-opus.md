# rsn 296: blind Opus audit of the reasonpanel296 key

Auditor: Claude Opus 5.5, blind. I did not open `scripts/claude_rsn29*_*.py`, the validator or any other panel.
Date: 2026-09-24.

## Seal

`sha256sum -c artifacts/claude-reasonpanel296-20260924/SEAL.sha256.txt`, run from the repo root:

- `items.jsonl`: OK
- `README.md`: OK

## Method

- I read all 300 items by hand, one category at a time. For each item I checked the question, the frame, the gold answer and the support against the notebook.
- As a cross-check I wrote my own small solver in the scratchpad, not the panel validator. It applies the README rules (newest `when` wins, year order for history rows, distinct values for counts). It agrees with the gold answer on 300 of 300 items.
- I also scanned for these problems:
  - repeated subject + relation rows outside newest_correction (none found);
  - backwards items where more than one row matches, or where the value also appears under another relation (none are ambiguous);
  - chains where a person on the path has a row under a relation with an overlapping meaning (none change the English reading).

## Counts per category

| category | items | OK | wrong_gold | ambiguous_question | frame_mismatch | unanswerable | real_name | other |
|---|---|---|---|---|---|---|---|---|
| one_step | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| two_step | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| heldout_three_step | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| backwards | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| yes_no | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| counting | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| comparing | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| before_after | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| newest_correction | 30 | 28 | 0 | 2 | 0 | 0 | 0 | 0 |
| missing_fact | 30 | 30 | 0 | 0 | 0 | 0 | 0 | 0 |
| **total** | **300** | **298** | **0** | **2** | **0** | **0** | **0** | **0** |

Other checks, all clean:
- yes_no has 15 yes and 15 no.
- Every missing_fact item is truly missing its needed row at the stated hop. No other reasonable reading of the question can be answered.
- Every counting question counts exactly the rows of the asked person and relation. Duplicate values are collapsed correctly.
- Every direction word in comparing matches the frame direction and the numbers.
- Every before_after answer is the row with the next lower or next higher year.
- No real-person names were found.

## Flagged items

Both flags are minor. In each, the gold follows the panel's rule (the newer row wins). The English wording still allows a second reading.

| id | category | problem | reason | smallest mechanical fix |
|---|---|---|---|---|
| rp296-194 | newest_correction | ambiguous_question | The two conflicting rows use a past-tense relation that a person can truly hold twice. So the question can be read as "both", not as a correction. | Retag the relation of rows f4 and f7, and `frame.relations`, to a present-state single-valued relation, and reword the question to match. Or drop f7 and move the item out of newest_correction. |
| rp296-215 | newest_correction | ambiguous_question | Same issue: the two conflicting rows use a past-tense relation that can truly hold two values. The question has no "now" to mark one row as the current one. | Retag the relation of rows f8 and f10, and `frame.relations`, to a present-state single-valued relation, and reword the question to match. Or drop f8 and move the item out of newest_correction. |

Borderline, not flagged: rp296-152 asks about a relation with a fixed meaning (where a person grew up). Reading the newer row as a correction is natural there, so I left it as OK.
