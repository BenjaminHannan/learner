# RESULT gr-7d (practice only): the distractor-block idea is SUNK, and my "lost its place" reading is PROVED WRONG

Owner: Plain-English puzzles thread. Times from `date -u`. Plan and seals: PLAN-gr7d.md (a017d5143). Run notes:
run/RUN-NOTE.md. Count: run/logs/count.log (513192eea). Separate recount: recount/. Post-hoc breakdown: posthoc/.
This is a diagnosis on a code-made practice set. It is not a test, and it gives no verdict on any reader.

## What ran
- The chain ran once on this container's CPU at $0, from 07:43:42Z to 09:27:19Z (1 h 44 min). The seals, both
  adapters' sha256 and both selftests were checked before any reader ran.
- Each of L7 (gr-7's adapter) and G5 (gr-5's adapter) read 200 squares, 200 squares in 40 new formats and 150 lookalikes.
  Each task was launched once. No row was incomplete.

## Counts
| | L7 | G5 |
|---|---|---|
| Squares (200): exact / wrong / none | 200 / 0 / 0 | 198 / 2 / 0 |
| New formats, seen separator (100): exact / wrong / none | 96 / 2 / 2 | 70 / 29 / 1 |
| New formats, new separator (100): exact / wrong / none | 83 / 14 / 3 | 38 / 56 / 6 |
| Lookalikes (150) read as a square | 6 (all non-square blocks) | 6 (all non-square blocks) |

## The kinds of wrong grid (sealed definitions)
| | L7 | G5 |
|---|---|---|
| A: numbers that are not cells | 2 | 44 |
| B: lost its place in the square | 3 | 15 |
| C: other | 11 | 28 |
| Wrong grids in all | 16 | 87 |

**False squares on lookalikes.** L7 had 6 false squares, all on non-square blocks: 4 copied the message's numbers (A) and
2 were other (C). None kept the block's whole shape. G5 had the same counts: 6 false, 4 A and 2 C.

## What the sealed rules say
- **The distractor-block idea is SUNK for these kinds.** A is 2 of L7's 16 wrong grids, under a third, and 16 is at
  least 10.
- **My own reading, that the reader loses its place inside the square, is PROVED WRONG.** B is 3 of 16, under half.

## Predictions
1. At least 10 L7 wrong grids, mostly with new separators: **met** (16, and 14 of them with a new separator).
2. B at least half and A under a third: **B failed** (3 of 16). **A was met** (2 of 16).
3. At least 5 L7 false squares, mostly in the non-square and numbers kinds, at least two thirds A: **met** (6, all
   non-square; 4 of 6 A, exactly at the line). No near miss and no block of two-digit numbers was read as a square.
4. G5 has more wrong grids than L7 on the new formats: **met** (85 against 16).

## What most of L7's wrong grids are (post hoc, report only)
posthoc/size.py was written after the count, so everything here is a suggested reading and not a registered result.
- **The size is wrong.** 11 of L7's 16 wrong grids have the wrong size: 10 are too big (9 by one, 1 by two) and 1 is one too small.
  The other 5 have the right size.
- **The cells are kept, but blanks are added.** In 9 of the 16, the square's own cells are all there, in order, and the
  reader only added or dropped cells. The cells added were 87 blanks and 23 digits.
- **An example (practice data).** A 4 x 4 written as "1 - <2;_;_;_>" was read as 5 x 5. Each row got an extra blank, and
  a fifth row was added.
- **So most of the C kind is a wrong size decision under an unfamiliar separator or row end.** The sealed kinds call it
  "other" because it is neither one far row nor within 2 edits.

**G5 against L7 (report only).** Half of G5's wrong grids (44 of 87) read labels or headers as cells, against 2 of 16 for
L7. Suggested: gr-6's wider layouts, trained to gr-7's length, removed that kind of error.

## Limits
- **The words around the grids are familiar.** They are the 1B's own openers and drafts, which the reader trained on.
  On these practice squares L7 read 200 of 200. The panel's 3 wrong squares came with a blind writer's words, and this
  set does not reproduce them. So nothing here explains R3.
- **The lookalikes are 3 code kinds.** The panel's were a writer's free text.
- **The kind definitions and their thresholds** (1 cell, 2 edits) were my choice, fixed before the run.

## Next
Nothing is sealed. A gr-8 plan, chosen from the size errors, goes to the Thread manager first, and any test uses a fresh
blind panel.
