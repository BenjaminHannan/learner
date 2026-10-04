# Round 8: long questions with irrelevant numbers inside (2026-10-04, fast lane). Marks fixed before training

Question: round 7 lifted the 49-token cap and long questions work when the extra text has no numbers. The real calculator path treats EVERY number in the text as a candidate operand (up to 8 literals), so a time, a room number or a bus number in the extra text is a distractor the pointer heads must ignore.
Code change that makes this testable (no model change): task operands are now located among the literals by value (each of x, y, z must appear exactly once; x, y, z distinct), so pointer labels point at the right candidate even when extra literals exist. All earlier rows have no extra numbers and map exactly as before.

## Arms (6 seeds 0-5, one run per RTX 5090 box or two per box; both arms trained with cap 160 and 30% lengthened items, TABV frames; both scored on all five sets)
- **LONG (control, re-run):** round-7 recipe, filler without numbers. Its models were not saved, so it is re-run.
- **DIST (the one change):** same, but half of the lengthened training items carry 1 to 4 irrelevant-number sentences (40 sentences of mine with a {d} slot; values 2 to 99, distinct from x, y, z and from each other, so up to 7 literals).

## Evals
- **DISTR (new):** 192 long two-step questions (55 to 150 tokens) from the 24 independently written layout families, with 1 to 4 irrelevant-number sentences from a pool of 60 written by a separate worker (`eval_distractors_r8.json`; sentences sharing a 5-gram with my training pool dropped) plus neutral filler from the round-7 eval pool. x, y, z distinct; triples excluded from training. 24 families x 4 op pairs x (1 unseen + 1 seen final).
- Guards: round-7 long set (no numbers), old own-wording, Blind-1, Blind-2.

## Marks (6 seeds, t = 2.571)
1. USABLE: DIST chain on DISTR, mean >= 50%.
2. NO-DROP: paired gain DIST minus LONG on each of old-all, Blind-1-all, Blind-2-all, and on the round-7 long set: mean >= -3.
**PASS = both. FAILS = DIST chain on DISTR < 30%, or any guard mean gain < -5. Otherwise partial, no claim.**
Reported with no mark: LONG's own chain on DISTR (how much unpractised distractors hurt) and the paired DIST minus LONG gain on DISTR; chain by length and by number of distractors; call 1 / call 2 given call 1; share of wrong calls whose refs include a distractor literal; seed SD.
Gate: train fit (last 192 two-step training items) >= 70%, else UNDERFIT-VOID.
Wrong-if: DIST chain on DISTR < 30% means the pointers cannot learn to skip irrelevant numbers at this size, and number-bearing long text needs another design (e.g. the reader must flag relevance first).
Budget cap ~$2 (expected about $1; 12 runs). Credit must stay > $1 (shared with the fair scaling run).
