# PASSMARKS gr-3: a learned glance says the grid's size, or "no square", before the cells are read (registered 2026-09-26 19:16 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. These marks were written before the glance head was
trained, before the blind panel was made, and before any gr-3 run. They are never edited; changes go in a dated
addendum before the registered run.

## Why
gr-2 (registered FAIL, artifacts/claude-gr2-20260926/VERIFY-gr2.md) read 100 of 100 squares and 50 of 60 in new
formats. It did this by searching every size from 3 to 9 for the most probable square over gr-1's learned token
probabilities. It also found squares in 3 of 55 lookalikes (R2 FAIL). In new formats it read 7 squares as a different
grid, all at the wrong size (U2 FAIL). Nothing learned said how big the block was, or whether it was a square at all.

## Brain first (Ben 16:05)
A person takes in a block at a glance: "that is a 5 by 5 grid", or "that is a price list". The size and the yes or no
come first, as one judgement about the whole block. The cells are then read inside that frame.

## One change
A small learned head, the glance, reads the whole echoed message and says none, or a size from 3 to 9. It is a
multinomial logistic regression on the mean hidden state of the second copy at one layer.
- If the glance says none, the reading is none.
- If it says s, gr-2's search (claude_gr3.decode_at, gr-2's code restricted to one size) looks only for an s x s square,
  still against the tagging with no cells. The search remains disclosed hand-written scaffolding (ADDENDUM-gr2-1).
- The per-token head is gr-1's sealed head (d5bf293ce), unchanged. The echo prompt and features are unchanged.

## Training the glance (only the 1B's text; code labels; no Claude text; no panel)
- gr-1's 860 practice messages (artifacts/claude-gr1-20260926/train/train.jsonl), labelled with the size of the
  inserted square or none.
- The 1B's own messages sharing a small table of numbers (scripts/claude_gr3_drafts.py, seed 4960, 18 everyday topics
  x 2 styles x 4 samples, kept when 3 or more lines hold digits). Each is labelled with the size that the reading
  definition (claude_puzzle_reader.read_latin) finds in it, or none. No label comes from what the 1B was asked to
  write (test-hygiene rule 2).
- The layer (8, 16 or 24) and the L2 weight (0.001, 0.01, 0.1), and nothing else, are picked by 5-fold CV accuracy of
  the size label.

## Test data (blind, fresh, sealed before the glance is trained)
artifacts/claude-panel-gr3-20260926, made by scripts/claude_gr3_make_panel.py (gr-2's maker with new seeds and ids).
A new blind writer, who saw no code and no earlier panel, invented the lookalikes' situations without being given a
list.
- 100 squares in 30 new wrappers: seeds 493004-493007, sizes 4-7, 25 each, about 20% broken, "Row k:" and bare layouts
  (358b3's).
- 60 new lookalikes, about 20 of them hard to tell from a puzzle at a glance. The truth is what read_latin reads.
- 60 squares in 20 new formats that are none of the 8 practice layouts: seeds 494004-494007, 3 per format.
- dl-1's 300 general items.
- Only claude_gr3.py run/score read the panel, and they print counts only.

## Arms (this container's CPU, fp32; each task launched once; one forward pass per message)
- L: gr-3 (the glance, then the search at that size). It decides the marks.
- G2: gr-2's reading (search over every size). Report only.
- P: gr-1's per-token reading. Report only.
- C: the code stand-in read_latin. Report only.

## Marks (the same bars as gr-1 and gr-2)
| Row | Test | Bar |
|---|---|---|
| R1 | squares read exactly, L | >= 97 of 100 |
| R2 | lookalikes read as a square where the truth is none, L | <= 1 |
| R3 | squares read as a different grid, L | <= 1 |
| R4 | general items read as a square, L | 0 of 300 |
| U1 | squares in unseen formats read exactly, L | >= 48 of 60 |
| U2 | squares in unseen formats read as a different grid, L | <= 2 |

gr-3 PASSES only if R1-R4 all pass. gr-3U is its own verdict (U1 and U2). A FAIL stays a FAIL. Report only: every arm on
every row, and how often the glance named the right size or said none.

## Decision rule (fixed now)
If gr-3 passes, the reader (claude_gr3: the glance, gr-1's head and the disclosed search) is offered to Sleep research
to replace the code stand-in in 358b3's path, joined as their own single change. If it fails, the stand-in stays.

## What would prove it wrong (fixed now)
- R2 or R4 above the bar: the glance does not tell number tables from puzzle squares.
- R1 or U1 below the bar: the glance says none, or the wrong size, for real squares, and turns reads into misses.
- R3 or U2 above the bar: the glance names a wrong size and the search forces a grid at it.
