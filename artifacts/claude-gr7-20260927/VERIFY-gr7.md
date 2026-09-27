# VERIFY gr-7: dev PASS, then gr-7 FAIL (R2, R3) and gr-7U FAIL (U2), though U1 passed 54 of 60 (2026-09-27 07:35 UTC)

Owner: Plain-English puzzles thread. Times from `date -u`. Marks: PASSMARKS-gr7.md (c8b971c76). Code and chain seal:
f6ec1b62f. Rows and panel: gr-6's seals (eea8d6e10). Run and score: 298b0b38f. Blind recount: recount/ (README.md says
who wrote it and what it read). Every count below is in both score/gr7_score.json and recount/output.txt.

## What ran
- The chain ran once on this container's CPU at $0 (run/RUN-NOTE.md, run/logs/). The first STEP line was at
  04:25:50Z and STEP done at 07:27:13Z: 3 h 1 min, inside the 6-hour cap. No restart. Every task was launched once.
- Training (epochs 4 to 6 from gr-6's adapter) took 117.4 minutes. Adapter sha256 c8f95557..., kept off git.
- The gr-6 panel (artifacts/claude-panel-gr6-20260927) is now spent. It can never serve as a test again.

## Dev and loss (PASSMARKS-gr7, in the order fixed there)
| Dev row | Result | Rule |
|---|---|---|
| gr-5's 72 held-out squares, exact | 72 of 72 | 66 or fewer is PROVED WRONG; 69 or more to pass |
| All 123 held-out squares, exact | 121 of 123 (1 wrong, 1 none) | 111 or more to pass |
| Held-out no-square rows read as a square | 0 of 139 | 0 to pass |
| The 51 held-out squares in new layouts (report only) | 49 of 51 | none |
| Squares in the 8 dev-only layouts (report only) | 64 of 64 | none |
| Format-dev messages (report only) | 30 of 30 | none |
| Mean loss, epochs 4, 5 and 6 | 0.0107, 0.0111, 0.0021 | prediction: epoch 6 at most 0.001 |

- **Dev outcome: PASS.** The under-training reading was not proved wrong.
- **The loss prediction failed** (0.0021 against 0.001). Epochs 4 and 5 sat above gr-6's epoch 3 (0.0062). Suggested only:
  AdamW's moments started fresh.
- **Disclosure (from the marks).** These 123 rows have now been copied row by row three times (gr-6's dev, the post-hoc
  breakdown, gr-7's dev). So this dev pass is weaker evidence than a first read. The panel below is the real test.

## The registered test: gr-6's marks with L7 in L6's place
| Row | Test (L7) | Result | Bar | |
|---|---|---|---|---|
| R1 | squares read exactly | 97 of 100 | >= 97 | pass |
| R2 | lookalikes read as a square where read_latin's truth is none | 2 of 52 | <= 1 | **FAIL** |
| R3 | squares read as a different grid | 3 | <= 1 | **FAIL** |
| R4 | general items read as a square | 0 of 300 | 0 | pass |
| U1 | unseen-format squares read exactly | 54 of 60 | >= 48 | pass |
| U2 | unseen-format squares read as a different grid | 5 | <= 2 | **FAIL** |

**gr-7 is a FAIL** (R2 and R3). **gr-7U is a FAIL** (U2), though U1 passed. gr-2 also passed U1, with 50 of 60 on its
own panel, and failed R2 (false squares) and U2 (7 wrong grids). gr-5, which gr-7 grows from, read 40 of 60 on its own panel. Those were other
panels, so the counts are not compared. A FAIL stays a FAIL. read_latin stays in 358b3's path.

## The one proved-wrong result: not met
The recipe is proved wrong if L7's U1 is not above G5's on the same panel. L7 read 54 of 60 and G5 (gr-5's adapter, same
prompt and grammar) read 39. So it is not proved wrong. The prediction of at least 6 more was met (15 more).

## Report-only lines fixed in advance
- **U1 split by whether the cell separator was seen in training.** Seen (51 squares): L7 47, G5 32. New (9 squares):
  L7 7, G5 7. Suggested only: the whole gain of 15 is on formats whose separator was seen. On the 9 with a new
  separator L7 is no better than G5, and 9 is too few to say more.
- **The 8 lookalikes that hold a square.** L7 read 1 as a square, and not as the stored grid, and 7 as none. G5 did the
  same: 1 read as a square, not the stored grid, and 7 as none. read_latin agrees with the stored truth on all 8.

## Other report-only counts
- **L7's 3 wrong squares** are all the right size, but 109 cells differ across the three (the sizes that missed are one
  6 x 6 and two 7 x 7, 134 cells in all). Suggested only: these are not small slips.
- **L7's 5 wrong unseen grids:** 3 the right size (44 cells differ across them) and 2 larger than the truth. 1 more was
  read as none.
- **L7's 2 false lookalike squares** are 3 and 5 on a side.
- **G5 on this panel:** squares 98 exact, 2 wrong, 0 none; unseen 39 exact, 15 wrong, 6 none; 2 false lookalike
  squares. So G5 would also fail R2 and R3 here. On gr-5's own panel it had 0 wrong squares.
- **C (read_latin):** 100 of 100 squares, 0 false lookalike squares, 0 general items, and 0 of 60 unseen (all none).
- **Speed:** L7 took a median of 6152.5 ms per square on this CPU.

## Readings fixed in advance (gr-6's, applied to L7)
- "Code layouts don't cover how people write grids" and "wider practice doesn't teach grids at this size": not met
  (U1 is 54).
- **"The near misses did not teach 'find the square'": met** (R2 is 2). The reading is that the false squares come from
  something else. It is a reading, not a tested cause.
- **"The new data hurt the practice layouts": met on R3** (3 wrong), not on R1 (97). A caveat, report only: G5, which
  never saw the new data, also read 2 of these 100 squares wrong, so part of R3 may be this panel's squares, not the
  new data.

## Predictions
- gr-7's: the epoch-6 loss at most 0.001 failed. DEV PASS with at least 69 of the 72 and at least 111 of 123 was met.
- gr-6's, with L7: R1 and R4 pass (met), R2 pass (failed), dev-only layouts at least 80% (met, 64 of 64), U1 from 48 to
  55 (met, 54), U2 at most 5 (met, 5), L7 above G5 by at least 6 (met, 15).

## What this suggests (not tested)
- **Shown on this panel.** gr-6's recipe with 3 more epochs gives a reader that reads 54 of 60 squares in formats no
  training layout writes the same way, against 39 for gr-5's reader. gr-6's own adapter was never run on the panel.
- **Shown on this panel.** It still says "square" for 2 of the 52 number blocks that read_latin calls none, and it
  returns a wrong grid for 3 of 100 squares and 5 of 60 unseen ones. Those are the three bars that failed.
- **Suggested.** The wrong squares are mostly whole grids of the right size with most cells different, not one-cell
  slips. Whether they are copies of another number block in the same message or grids not in the message at all is
  not known; no one has looked, and the owner has not read the panel text.

## Next
Nothing is sealed. The Thread manager gets a plan before anything runs. Any next reader needs a fresh blind panel.
