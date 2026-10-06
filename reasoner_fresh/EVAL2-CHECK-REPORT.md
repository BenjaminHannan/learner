# EVAL-FORM-v2 independent check (re-run after patch)

Verdict: PASS, 0 defects. All of checks (1)-(7) were re-run on the current files.

1. Every row has exactly two digit groups, x then y, and no other digits. I scanned for number words and ordinals (including two, first, second, third, once, twice, pair and half) and found none. "both" is allowed, as agreed.
2. All 192 answers are correct. SUB rows always have x>y.
3. There are 96 pairs. Each has one ADD and one SUB, with the same x, y, family and cell. There are 32 rows per family and 96 per cell.
4. Names and nouns are disjoint from train, eval1 and gen2.py. No v2 frame, and no individual sentence, matches any frame in train, eval1, v1 text or the gen2 composed frames after masking names, nouns and numbers.
5. Each v2 family differs from the training wording, which shows one or two plain statements followed by one question.
   - question-first: the question comes before the facts.
   - distractor: an irrelevant sentence sits between the facts and the question.
   - table: the data is in an "item -> label: n" table.
   - dialogue: quoted speech from two speakers.
   - future-scene: future tense with a long irrelevant scene sentence.
   - distance: a unit with no countable noun, asking "how far / how much farther".
6. There are no duplicate texts. No (x,y) is repeated within v2, and none matches v1, even swapped.
7. All 96 seen/new_structure answers are in the T list (60 values) and none are in H. All 96 unseen/new_structure answers are in the H list (30 values) and none are in T.

Rewritten items, read after the patch:
- Dialogue ADD is "What is the sum of what Fran and Glen have?" and SUB is "How many more oranges does Fran have than Glen?" (the speaker named first in the quotes, x). The names are named explicitly, so there is no ambiguity. x-y gives 25 and x+y gives 73, both correct.
- Future-scene ADD is "How many wallets will Zane have carried to the hall by the end?" (77+19=96). SUB is "How many fewer wallets will Zane carry on the later trip than on the earlier trip?" (the later trip is y and the earlier trip is x, so 77-19=58). Both are unambiguous and correct.
- Table and distance use "both days". That is fine.
