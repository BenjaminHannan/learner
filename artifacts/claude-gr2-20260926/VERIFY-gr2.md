# VERIFY gr-2: registered FAIL on R2 (false squares); gr-2U registered FAIL on U2 (wrong grids) (2026-09-26 19:12 UTC)

Owner: Plain-English puzzles thread. Marks were sealed before the panel existed (d890bf437, disclosure ADDENDUM-gr2-1
a175481e7). The fresh blind panel was written by a new blind writer and sealed before the run (1676d54bc). The run
checked the head, code, marks and panel seals, and each task was launched once on this container's CPU at $0,
19:01-19:10 UTC; outputs and score are in 3496eaee7. A separate blind agent recounted with its own code, without
importing the scripts and printing integers only. Every L and P value, all six marks and both verdicts agree, and every
panel id appears exactly once.

## gr-2 (358b3's layouts, new blind wrappers)
| Row | Test | L (whole grid) | P (gr-1 per token, report) | C (code stand-in, report) | Bar | |
|---|---|---|---|---|---|---|
| R1 | squares read exactly | 100 of 100 | 84 | 100 | >= 97 | pass |
| R2 | lookalikes read as a square where the truth is none (55) | 3 | 0 | 0 | <= 1 | FAIL |
| R3 | squares read as a different grid | 0 | 0 | 0 | <= 1 | pass |
| R4 | general items read as a square | 0 of 300 | 0 | 0 | 0 | pass |

**gr-2 is a registered FAIL on R2, and it stays a FAIL.** Under the decision rule, the code stand-in stays in 358b3's
path as disclosed scaffolding. The 5 lookalikes whose truth is a square by the reading definition: L read 1 as a
different grid and 4 as none; P read all 5 as none.

## gr-2U (20 new formats practice never had)
| Row | Test | L | P (report) | C (report) | Bar | |
|---|---|---|---|---|---|---|
| U1 | squares read exactly | 50 of 60 | 22 | 3 | >= 48 | pass |
| U2 | squares read as a different grid | 7 | 0 | 0 | <= 2 | FAIL |

**gr-2U is a registered FAIL on U2.** L read 16 formats 3 of 3 and 3 formats 0 of 3; P read 2 formats 3 of 3. All 7
wrong readings have a different number of rows than the true square. 3 of the 7 are broken squares. The 3 messages
with two cells in one token were not read.

## What it shows
- Shown: gr-1's misses were slips. Reading the grid as a whole recovered 16 squares and 28 unseen-format squares that
  per-token tagging lost. Nothing per-token read exactly was lost. With the same learned head, the reader now reads
  100 of 100 in 358b3's layouts and 50 of 60 in formats it never practised (the code stand-in reads 3).
- Shown: the price is the risk named in the marks. Forcing the best square finds squares that are not there (3 of 55
  lookalikes) and picks the wrong size in new formats (7 wrong grids, all with the wrong number of rows). Per-token
  reading made none of these errors.
- Suggested: the search chooses the size s freely, and "none" competes only with a tagging that has no cells at all.
  Nothing learned says how big the block is, or whether it is a puzzle square at all.
- Untested: whether a learned judgement of the block's size fixes both errors.

## Brain first (Ben 16:05)
Before reading cells, a person takes in the block at a glance: "that is a 5 by 5 grid", or "that is a price list, not
a puzzle". The size and the yes or no come first, as one whole-block judgement, and the cells are read inside that
frame. The single change that matches this is a small learned head that reads the whole echoed message and says the
square's size, or "no square". It would be trained on the same practice set with code labels. The search then only
looks for a square of that size, and returns none when the head says none. This also moves part of the grouping from
code into a learned part, as the Thread manager asked. The test needs a fresh blind panel, because this one is now
used.
