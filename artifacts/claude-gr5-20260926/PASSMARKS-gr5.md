# PASSMARKS gr-5: the reader 1B is trained to copy the square, or to say none (registered 2026-09-26 20:12 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. These marks were written before the adapter was
trained, before the blind panel was made and before any gr-5 run. They are never edited; changes go in a dated
addendum before the registered run. The plan went to the Thread manager at 20:04 UTC. The review passed it with four
conditions, all written in below: the split and what dev may pick, class balance, compute, and proved-wrong numbers.

## Why
Two learned readers failed their blind tests: gr-1 (per-token tags, R1 85 of 100), gr-2 (a search over gr-1's tags,
3 false squares, 7 wrong sizes in new formats). gr-3 (a learned size glance) is sealed, and its run on its own panel
was going when these marks were written; its cross-validation named a wrong size for 40 of 360 practice squares. None
of gr-3's results was read before these marks. Ben's 19:20
rule asks for the plain, well-known fix first. The plain 1B, asked to copy the square under a grammar (gr-4, NOTE
e51d7f347), read 4 of 20 practice squares, and 3 of 20 with two worked examples, so prompting alone is not enough.
The standard fix for a small model that must turn text into a structure is to fine-tune it on examples of the task.

## Brain first (Ben 16:05)
Reading a grid out of a message is a perceptual skill that people learn by practice. A child copying a puzzle from a
page looks back at the source for each cell. Nobody hands the child a rule for each layout; they copy many grids and get
better. In Ben's design, reading belongs to the reader 1B, whose job is to translate the message for the reasoner. This
test teaches the reader that one skill, from practice alone.

## One change (from gr-4)
A LoRA adapter on the reader 1B (claude_blurt2.add_lora: rank 16 on q/k/v/o, alpha 32, dropout 0.05). It is trained
with the sleep recipe (3 epochs, lr 2e-4, AdamW, batch 8, seed 4990), with the loss on the answer tokens only. The
prompt, the grammar (disclosed hand-written scaffolding: digits, "_", spaces and newlines in an s x s shape, or the one
word "none") and the greedy decode are gr-4's, unchanged (scripts/claude_gr5.py Copier5; claude_gr4.py).

## Training rows (scripts/claude_gr5.py build; no Claude text, no GLM text, no test item, no panel)
- gr-1's 860 practice messages: code-made squares in 8 layouts inside the 1B's own wrappers, and the 1B's own
  no-square messages, including code-made number blocks that are not squares.
- gr-3's 58 kept 1B number tables, labelled by read_latin (none in all 58).
- Target printed by code: the square, one row per line, "_" for a blank, or the one word "none". The word "none" is a
  class label, the way a classifier's output is, not a sentence frame.
- Held-out split, by message: every fifth message of each kind is held out for dev. That gives 739 train rows (451
  none, 288 squares) and 179 dev rows (107 none, 72 squares). Every square is different (no grid repeats), but 19 of
  the 72 dev squares sit in a 1B wrapper that also wraps a training square, so dev is easier than the blind panel.
- Class balance: none to square is 451 to 288 in training (about 1.6 to 1). The loss is on the answer only. "none" is
  one token plus the end token, and a square is about 10 to 70 tokens. The loss is averaged within each message and
  each message counts once in its batch, so one "none" weighs as much as one whole square.
- Nothing is picked on dev, not even a checkpoint: the adapter after epoch 3 is the one tested. Dev is reported per
  class (held-out squares, held-out none rows) and can only stop the run (below).
- The 30 messages that gr-4 was tried on (10 from 358b3's free smoke panel, 10 fresh code requests, 10 rt-02d
  no-square dev cases) are format dev only. gr-4's grammar was fixed on them, so they are reported, never a gate.

## Stop rule before the run (fixed now)
If the held-out dev split reads fewer than 65 of its 72 squares exactly, or reads any of its 107 no-square rows as a
square, gr-5 is recorded as a dev FAIL and the blind panel is not spent.

## Test data (blind, fresh, made and sealed before the adapter is trained)
artifacts/claude-panel-gr5-20260926, made by scripts/claude_gr5_make_panel.py (gr-3's maker with new seeds 4970/4980
and gr5- ids). A new blind writer, who saw no code and no earlier panel, wrote the wrappers, lookalikes and formats.
- 100 squares in 30 new wrappers: seeds 497004-497007, sizes 4-7, 25 each, about 20% broken, "Row k:" and bare layouts.
- 60 new lookalikes, about 20 hard to tell from a puzzle at a glance. The truth is what read_latin reads.
- 60 squares in 20 new formats that are none of the 8 practice layouts: seeds 498004-498007, 3 per format.
- dl-1's 300 general items.
- Only claude_gr5.py run/score read the panel, and they print counts only.

## Arms (each task launched once; greedy, so one output per message)
- L: gr-5, the trained reader. It decides the marks. Tasks: squares, lookalikes, unseen, general.
- P0: the plain 1B under the same grammar (gr-4, every LoRA scale 0). Report only. Tasks: squares, lookalikes, unseen.
- C: the code stand-in read_latin. Report only, and no comparison on R1 and R2: the truth of each lookalike is what
  read_latin reads, and the maker checks that read_latin reads every inserted square.

## Marks (the same bars as gr-1 to gr-3)
| Row | Test | Bar |
|---|---|---|
| R1 | squares read exactly, L | >= 97 of 100 |
| R2 | lookalikes read as a square where the truth is none, L | <= 1 |
| R3 | squares read as a different grid, L | <= 1 |
| R4 | general items read as a square, L | 0 of 300 |
| U1 | squares in unseen formats read exactly, L | >= 48 of 60 |
| U2 | squares in unseen formats read as a different grid, L | <= 2 |

gr-5 PASSES only if R1-R4 all pass. gr-5U is its own verdict (U1 and U2). A FAIL stays a FAIL. Report only: every arm
on every row, exact reads by size, layout and format, and outputs that did not finish inside the grammar.

## Where it runs
Training: this container's CPU if one timed step says 3 epochs fit in 4 hours; otherwise BensPC (free), with only the
adapter shipped back. The run and score are on this container's CPU. $0 either way, no rental.

## Decision rule (fixed now)
If gr-5 passes, the reader (the 1B with this adapter on while reading, off otherwise) is offered to Sleep research to
replace the code stand-in read_latin in 358b3's path, joined as their own single change. If it fails, the stand-in
stays, and the next step is chosen from where it failed.

## What would prove it wrong (fixed now)
- 2 or more lookalikes, or 1 or more general items, read as a square: the trained reader copies number blocks, so
  training taught "copy numbers", not "find the square".
- Fewer than 97 of 100 squares read exactly, with "none" as the most common miss: training taught it to say none.
- 2 or more squares, or 3 or more unseen-format squares, read as a different grid: it copies with slips or at a wrong
  size, as the plain 1B did.
- 97 or more of 100 squares but fewer than 48 of 60 in unseen formats: it learned the 8 practice layouts, not grids.
