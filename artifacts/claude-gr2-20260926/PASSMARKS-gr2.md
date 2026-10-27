# PASSMARKS gr-2: the learned grid reader reads the grid as a whole (registered 2026-09-26 18:56 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. These marks were written before the blind panel was
made and before any gr-2 run. They are never edited; changes go in a dated addendum before the registered run.

## Why
gr-1 (registered FAIL, artifacts/claude-gr1-20260926/VERIFY-gr1.md) read 85 of 100 squares exactly against a bar of 97,
and 25 of 60 in unseen formats against 48. It almost never read a wrong grid (1 of 160) or a false square (0 of 340),
but it tagged each token alone, so one slipped cell or row start lost the whole grid.

## Brain first (Ben 16:05)
A person reads a grid as a whole. They expect every row to have the same number of cells, and when a row looks short
they look at it again. They do not decide each mark on its own.

## One change
The same learned head (artifacts/claude-gr1-20260926/head.pt, sealed in d5bf293ce and not retrained), with the same
echo prompt and the same features, gives every token its probabilities of O, B and I. Instead of taking each token's
most likely tag and rejecting a non-square, code finds the single most probable tagging among:
- every tagging that forms an s x s square (3 <= s <= 9, cells only on tokens holding one digit or "_", values 1..s
  or blank, not all blank), and
- the tagging with no cells at all.
If the no-cells tagging is the more probable one, the reading is none. There is no threshold and nothing new is
trained. The code is claude_gr2.joint_decode. The square constraint is the same one gr-1's code already applied when
accepting a reading. The code now searches with it over the head's probabilities rather than using it only to reject.

## Checks before registering (practice and dev only; no panel)
- gr-1's practice CV, same folds, layer and L2, reading each held-out message both ways: squares 340 of 360 exact per
  token against 360 of 360 whole-grid, with 0 wrong either way. Messages without a square: 500 of 500 per token
  against 499 of 500 whole-grid (1 false square).
- Dev (358b3 smoke 30, fresh bridge 24, no-square 135): both readings perfect, so dev does not tell them apart.

## Test data (blind, fresh, sealed before the run)
artifacts/claude-panel-gr2-20260926, made by scripts/claude_gr2_make_panel.py from a new blind writer's file. The
writer saw no code and no earlier panel.
- 100 squares in 30 new wrappers: seeds 491004-491007, sizes 4-7, 25 each, about 20% broken, with "Row k:" and bare
  layouts as in 358b3.
- 60 new lookalikes, with numbers in rows and not a request to fill a Latin square. About 15 are tricky: small
  square-looking blocks, or "_" for missing values. The truth is what claude_puzzle_reader.read_latin reads, usually
  none.
- 60 squares in 20 new formats that are none of the 8 practice layouts: seeds 492004-492007, 3 per format.
- dl-1's 300 general items.
- Only claude_gr2.py run/score read the panel, and they print counts only.

## Arms (this container's CPU, fp32; each task launched once)
- L: gr-2, whole-grid reading. It decides the marks.
- P: gr-1's per-token reading, from the same forward pass. Report only.
- C: the code stand-in read_latin. Report only.

## Marks
| Row | Test | Bar |
|---|---|---|
| R1 | squares read exactly, L | >= 97 of 100 |
| R2 | lookalikes read as a square where the truth is none, L | <= 1 of 60 |
| R3 | squares read as a different grid, L | <= 1 |
| R4 | general items read as a square, L | 0 of 300 |
| U1 | squares in unseen formats read exactly, L | >= 48 of 60 |
| U2 | squares in unseen formats read as a different grid, L | <= 2 |

gr-2 PASSES only if R1-R4 all pass. gr-2U is its own verdict, U1 and U2 both. A FAIL stays a FAIL. Report only: P and C
on every row, and reads by size, layout or format, and broken or not.

## Decision rule (fixed now)
If gr-2 passes, the learned reader (claude_gr2.read_grid with gr-1's head) is offered to Sleep research to replace the
code stand-in in 358b3's path, joined as their own single change. If it fails, the stand-in stays as disclosed
scaffolding.

## What would prove it wrong (fixed now)
- R1 below 97: whole-grid reading does not fix the slips on unseen wordings, and the head itself misses cells.
- R2 or R4 above the bar: forcing the best square makes the reader see squares in ordinary number tables.
- R3 or U2 above the bar: forcing a square turns "not sure" into a wrong puzzle, the worst failure. This is the main
  risk of the change.
