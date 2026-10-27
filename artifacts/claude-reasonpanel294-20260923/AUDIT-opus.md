# reasonpanel294: blind audit (Opus)

Auditor: Claude Opus 5.5, 2026-09-23. Every one of the 300 items was read by hand: the notebook,
the English question, the frame and the gold. The validator was not used for any judgement.
This file names no people, values or question text.

## Seal

`sha256sum -c artifacts/claude-reasonpanel294-20260923/SEAL.sha256.txt`: **OK** (items.jsonl OK, README.md OK).

## Counts per category

| category | items | OK | flagged | flag types |
|---|---|---|---|---|
| one_step | 30 | 30 | 0 | |
| two_step | 30 | 30 | 0 | |
| backwards | 30 | 30 | 0 | |
| yes_no | 30 | 30 | 0 | (15 yes / 15 no confirmed) |
| counting | 30 | 21 | 9 | wrong_gold x9 |
| comparing | 30 | 30 | 0 | |
| before_after | 30 | 30 | 0 | (15 before / 15 after confirmed) |
| newest_correction | 30 | 30 | 0 | |
| missing_fact | 30 | 30 | 0 | |
| heldout_three_step | 15 | 15 | 0 | |
| heldout_big_notebook | 15 | 15 | 0 | |
| **total** | **300** | **291** | **9** | |

Problem types across the panel: wrong_gold 9; ambiguous_question 0; frame_mismatch 0;
unnatural_or_unanswerable 0; real_name 0; other 0.

## Flagged items

All nine have the same cause. In each one, the person being counted has a single-valued
`instrument` row as well as their `plays` rows, and that row names an instrument not among
the `plays` values. Elsewhere in the panel, `instrument` is the relation behind questions like
"what does X play" (one_step and newest_correction items ask what someone plays and use it).
So a careful reader counts that instrument too, and the true count is one more than the gold.
The frame counts only `plays`, so gold and frame agree with each other, but both miss what the
English question asks.

| id | category | problem type | reason |
|---|---|---|---|
| rp294-031 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |
| rp294-041 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |
| rp294-051 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |
| rp294-054 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |
| rp294-086 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |
| rp294-112 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |
| rp294-129 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |
| rp294-193 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |
| rp294-300 | counting | wrong_gold | the counted person's separate instrument row names one more instrument, and the gold leaves it out |

Suggested fix, for the key's owner to decide: in the instruments-counting template, either drop
the same-person `instrument` distractor, give it a value already among that person's `plays`
values, or count both relations. The language, children and cats counting items have no such
second relation and are fine.

## What was checked and found clean

- missing_fact: in all 30 the needed row is truly absent. The near misses (hometown vs
  lives_in, former_employer vs employer, allergy vs favorite_food, cat vs dog, cousin vs sister)
  do not honestly answer the question. No symmetric row (someone else's sister, best friend and
  so on pointing back at the person asked about) supplies the fact.
- comparing: every direction word (older, younger, born first, born later, taller, shorter,
  longer or shorter commute, lives closer, travels farther) matches the frame direction and the gold.
- before_after: every gold is the next lower or next higher year in that person's own history,
  never another person's. The undated former_employer distractor in one item does not change
  the answer.
- counting: apart from the nine above, every count equals the distinct values of that person's
  matching rows, and duplicate rows belong to other people.
- newest_correction: every gold takes the larger `when`, including the items that list the
  newer row first.
- two_step, three_step and big notebook: every chain is unique at each hop, and no symmetric
  relation points back at a person in the question.
- backwards: the answer is unique every time.
- No real famous people or brands are used as people.
