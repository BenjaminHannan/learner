# DEV REPORT gr-3: the glance trained and checked on practice data only (2026-09-26 20:02 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. Written after training and the dev check, and
before any run on the blind panel (artifacts/claude-panel-gr3-20260926), which nothing here read. Marks:
PASSMARKS-gr3.md and ADDENDUM-gr3-1.md, unchanged. Logs: logs/table_drafts.log and logs/feats_fit_dev.log.

## The 1B's number-table messages (scripts/claude_gr3_drafts.py, seed 4960)
- 144 drafts (18 topics x 2 styles x 4). 58 kept (3 or more lines with digits and at most 700 characters).
- read_latin finds a square in 0 of the 144, so all 58 kept tables are labelled none.

## Training rows (claude_gr3.py feats)
918 rows: gr-1's 860 practice messages plus the 58 tables. Labels: none 558, size 3 37, size 4 44, size 5 81,
size 6 75, size 7 86, size 8 37 (size 9: 0, as ADDENDUM-gr3-1 says).

## The pick (5-fold CV on size-label accuracy, as sealed)
| Layer | L2 | Right of 918 | none read as square | square read as none |
|---|---|---|---|---|
| 8 | 0.001 | 842 | 3 | 2 |
| 8 | 0.01 | 837 | 3 | 2 |
| 8 | 0.1 | 810 | 2 | 3 |
| 16 | 0.001 | 851 | 1 | 1 |
| 16 | 0.01 | 845 | 1 | 1 |
| 16 | 0.1 | 820 | 0 | 3 |
| 24 | 0.001 | 877 | 1 | 2 |
| 24 | 0.01 | 869 | 1 | 2 |
| 24 | 0.1 | 842 | 0 | 5 |

Picked: layer 24, L2 0.001 (877 of 918). By source at the pick: every no-square group right except 1 of 23 short
blocks; the 58 tables 58 right; gr-1's 360 squares 320 right. So in CV the glance names the wrong size (or none, 2
times) for 40 of 360 practice squares. That is a warning for R1 and U1: gr-1's practice squares span 8 layouts, and a
wrong size makes the search read a wrong grid or none. Which layouts carry the 40 is not broken down here.

## Dev check (practice messages only: 358b3's free smoke panel, fresh code requests, rt-02d's no-square dev cases)
| Set | n | gr-3 exact | gr-3 wrong | gr-2 exact | gr-1 exact |
|---|---|---|---|---|---|
| smoke | 30 | 30 | 0 | 30 | 30 |
| fresh | 24 | 24 | 0 | 24 | 24 |
| no square | 135 | 135 | 0 | 135 | 135 |

The dev sets use the "Row k:" layout, and every reader is perfect on them, so dev cannot separate gr-3 from gr-1 or
gr-2. gr-1 was also perfect here and then read 85 of 100 on its blind panel. The registered run decides.

## Sealed next (SEAL-code-gr3.sha256.txt)
scripts/claude_gr3.py (selftest 25/25), scripts/claude_gr3_drafts.py, scripts/claude_gr2.py, scripts/claude_gr1.py,
sizehead.pt, train/table_drafts_1b.jsonl, and gr-1's token head artifacts/claude-gr1-20260926/head.pt. Then each task
is launched once on this container's CPU ($0): squares, lookalikes, unseen, general.
