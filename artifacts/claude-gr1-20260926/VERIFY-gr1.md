# VERIFY gr-1 and gr-1U: both registered FAIL on exact reading (2026-09-26 18:48 UTC)

Owner: Plain-English puzzles thread. Marks: PASSMARKS-gr1.md (38e382313), ADDENDUM-gr1-1 (cf2d9603a) and ADDENDUM-gr1-2.
The blind panels were sealed before any head was trained (e9426db9b, cfbe2530a). Code, head and practice data were
sealed in d5bf293ce, and the run checked that seal before starting. Each task was launched once on this container's
CPU at $0, 18:37-18:46 UTC, and the outputs and scores are in 975a10c42. A separate blind agent recounted with its own
code, without importing the scripts and printing integers only. Every L value, every mark and both verdicts agree
with the score files, and every panel id appears exactly once.

## gr-1 (358b3's layouts, blind wrappers)
| Row | Test | L (learned) | C (code stand-in, report) | Bar | |
|---|---|---|---|---|---|
| R1 | squares read exactly | 85 of 100 | 100 | >= 97 | FAIL |
| R2 | lookalikes read as a square | 0 of 40 | 0 | <= 1 | pass |
| R3 | squares read as a different grid | 1 (one cell off, 4 x 4) | 0 | <= 1 | pass |
| R4 | general items read as a square | 0 of 300 | 0 | 0 | pass |

**gr-1 is a registered FAIL, and it stays a FAIL.** Under the decision rule, the code stand-in stays in 358b3's path
as disclosed scaffolding, and the learned grid reader is still owed.

L exact reads: by size 18, 23, 22 and 22 of 25 (sizes 4-7); by layout, "Row k:" 46 of 50 and bare 39 of 50; broken 8 of
14 and whole 77 of 86. The 15 misses are spread over 11 of the 30 wrappers, 1 or 2 each. The median time was 1.5 s
per message.

## gr-1U (20 formats practice never had)
| Row | Test | L | C (report) | Bar | |
|---|---|---|---|---|---|
| U1 | squares read exactly | 25 of 60 | 9 | >= 48 | FAIL |
| U2 | squares read as a different grid | 0 | 0 | <= 2 | pass |

**gr-1U is a registered FAIL.** L read 3 formats 3 of 3 and 7 formats 0 of 3; the code stand-in read 3 formats 3 of 3
and 17 formats 0 of 3. 3 messages in 1 format put two cells in one token; L read none of them.

## What it shows
- Shown: the learned reader declines rather than misreads. It read 1 wrong grid in 160 squares, and it saw a square in 0
  of 340 messages without one.
- Shown: it carries to unseen formats better than the code stand-in (25 against 9 of 60), but not well enough.
- Shown: it misses a square it should read too often, 15 of 100 even in 358b3's own two layouts, where the code reads
  all 100.
- Suggested (practice CV, not the panel): a miss is usually 1 to 3 wrong tokens out of 25 to 60 cells, split across
  missed cells, missed row starts and extra cells. Each token is tagged on its own, so one slip loses the whole grid.
- Untested: what fixes it.

## Brain first (Ben 16:05)
A person reads a grid as a whole. They expect every row to have the same number of cells, and when one row looks
short they look again at that row. They do not decide each mark alone. The single change that matches this: keep the
same learned head and its probabilities, and choose the most probable tagging that forms a square (joint decoding)
instead of tagging each token alone and rejecting. Code finds that best square with a search over the head's scores,
and it only accepts it when the head saw a grid. The risk is more wrong grids, the worst failure, so the bars stay
strict. This needs a fresh blind panel, because these two are now used.
