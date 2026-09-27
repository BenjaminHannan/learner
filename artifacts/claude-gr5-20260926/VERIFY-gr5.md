# VERIFY gr-5: registered FAIL (R2); gr-5U FAIL (U1, U2) (2026-09-27 01:09 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. Marks: PASSMARKS-gr5.md (3634a4195), ADDENDUM-gr5-1
(dcb37487e), -2 (9a4aecfee) and -3 (40289d02f). The panel, the training rows and the code were sealed in 915373a4c
before the adapter was trained. The whole chain ran once on this container's CPU at $0 (cpu/chain.sh, ADDENDUM-3):
first STEP 2026-09-26T22:43:40Z, STEP done 2026-09-27T01:04:51Z, inside the 6-hour cap, with no restart (run/RUN-NOTE.md).
Each task was launched once (run/, run/logs/, score/gr5_score.json; ac9183716). A separate blind agent recounted
everything from the run files and the panel with its own code, without reading or importing any claude_gr*.py or the
score file, and printed integers only (recount/count.py, recount/output.txt, recount/README.md). Its counts match
score/gr5_score.json on every row below.

## Result (L = gr-5: the reader 1B with the trained adapter, gr-4's prompt, grammar and greedy decode)
| Row | Test | Bar | L | Pass |
|---|---|---|---|---|
| R1 | squares read exactly | >= 97 of 100 | 100 | yes |
| R2 | lookalikes read as a square where the truth is none (53) | <= 1 | 2 | no |
| R3 | squares read as a different grid | <= 1 | 0 | yes |
| R4 | general items read as a square | 0 of 300 | 0 | yes |
| U1 | unseen-format squares read exactly | >= 48 of 60 | 40 | no |
| U2 | unseen-format squares read as a different grid | <= 2 | 13 | no |

**gr-5 registered FAIL (R2: 2 false squares, bar 1). gr-5U registered FAIL.** The code stand-in read_latin stays in
358b3's path (decision rule, PASSMARKS-gr5).

Before the blind run the dev gate passed: 71 of 72 held-out squares exact, 0 wrong, 107 of 107 no-square rows read as
none, and 30 of 30 on the format-dev messages.

## Report only (every arm on this fresh panel)
| Arm | Squares exact / wrong / none | Unseen exact / wrong / none | False lookalikes (of 53) | General |
|---|---|---|---|---|
| L (gr-5, trained) | 100 / 0 / 0 | 40 / 13 / 7 | 2 | 0 |
| P0 (plain 1B, same prompt and grammar) | 41 / 47 / 12 | 9 / 46 / 5 | 37 | not run |
| C (read_latin, code) | 100 / 0 / 0 | 3 / 0 / 57 | no comparison | 0 |

- C is no comparison on R1 and R2: the truth of each lookalike is what read_latin reads.
- L's exact reads by size: 25 of 25 at each size from 4 to 7. In unseen formats: 12, 10, 11 and 7 of 15 at sizes 4 to
  7. No output ran outside the grammar or failed to finish (0 incomplete rows for L and P0).
- L's 2 false squares were both 5 x 5, and neither is a valid partial Latin square (a number repeats in a row or a
  column). One had no blank cells; the other had 4.
- L's 13 wrong unseen reads: 8 at a larger size than the truth, 5 at the right size with 29 cells wrong in all (19 in
  one grid), none at a smaller size. L's 7 unseen "none" reads were all in whole (not broken) squares; it read 8 of the
  9 broken unseen squares exactly.
- Median time per square for L: 5349 ms.

## ADDENDUM-1 lines (report only)
1. The 7 lookalikes that read_latin reads as a square (read_latin on the text agrees with the stored truth on all 7):
   L read 1 of them as a square, the same grid read_latin reads, and 6 as none. P0 read all 7 as squares, and 1 of
   them was the same grid read_latin reads. So where the blind writer meant "no square" but the code finds one, the
   trained reader mostly sides with the writer.
2. Held-out dev squares split by wrapper (run/logs/devclean.log): 52 of 53 exact in wrappers the training never saw
   (0 wrong, 1 none), and 19 of 19 in wrappers that also wrap a training square. The dev gate's 71 of 72 holds either
   way.

## What this shows
- Shown: training the reader on code-printed copies is the plain fix that worked for the main job. On this panel it
  took the plain 1B under the same grammar from 41 to 100 of 100 squares exact, from 47 to 0 wrong grids, and from 37
  to 2 false squares. On their own panels gr-1 read 85, gr-2 100 and gr-3 92 squares exactly, with 0, 3 and 2 false
  squares (different panels, so suggested, not a like-for-like comparison).
- Shown: it still fails R2. The sealed reading for 2 or more false squares was "training taught copy numbers, not find
  the square". Both false squares were 5 x 5 number blocks that break the Latin rule, which fits that reading. On 2 of
  53 the evidence is thin, but the bar was fixed in advance and a FAIL stays a FAIL.
- Shown: it fails in new formats (40 of 60 exact; bar 48). The sealed reading was "it learned the 8 practice layouts,
  not grids". It is still far ahead of the plain 1B (9) and read_latin (3) there. Most of its wrong unseen grids were
  too big (8 of 13), so it copied extra rows or columns that were not part of the square.
- Suggested, not tested: a validity check on the copied grid would have removed both false squares, but it would be a
  new hand-written rule, and 358b3 plants broken puzzles on purpose (26 of the 100 test squares), so it could also
  drop real squares. It is not registered and is not the owner's pick without the Thread manager's review.

## Disclosure
At about 00:47 UTC, while writing the brief for the blind recount, the owner printed the first row of each panel file
to learn the field names. That was after the adapter was fixed and after all four L tasks had run. Nothing in the
code, the adapter, the marks or the run was changed after it, and no panel text is quoted anywhere.

## Next
gr-5 goes no further as a replacement for read_latin. What to try next is chosen from where it failed (2 false
squares, extra rows and columns in new formats), and goes to the Thread manager as a plan before anything is sealed.
