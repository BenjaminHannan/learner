# PASSMARKS gr-1: a learned reader finds the number square in a chat message (registered 2026-09-26 17:21 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u` at writing. These marks were written before any
head was trained and before the blind panel was made. They are never edited; changes go in a dated addendum before
the registered run.

## Why
Sleep research's 358b3, the headline gate for "puzzles asked in chat", reads the square with a code parser
(claude_puzzle_reader.read_latin at 3de583312). That parser is a disclosed hand-written stand-in, because 358b2 showed
the plain 1B cannot retype a square: 25/39/28 of 100 were exact, and it drops "_". The learned reader is owed.

## Brain first (Ben 16:05)
A person does not retype a grid to read it. They see the layout: which marks are cells, where each row starts, and
that the block is square. They also take a second look when needed. gr-1 does the same:
- The plain 1B (every LoRA scale 0) reads the message twice in one prompt: "Read this message carefully ... The same
  message again: ...". The second copy's tokens can then attend to the whole message, which is the second look.
- A small learned head labels every token of the second copy O (not a cell), B (the first cell of a row) or I (a later
  cell in the row).
- A cell's value is the token it points at: a digit, or "_" for a blank. Nothing is retyped.
- Code accepts the result only if it is well formed: s rows of s cells, 3 <= s <= 9, values 1..s or blank.

## One change
In claude_puzzle_reader, the code parser read_latin is replaced by claude_gr1.read_grid (the learned head). The rest
of 358b3's path stays as it is.

## Training (only text the 1B wrote; code-made squares and labels; no Claude text; no panel)
- The words around each square come from the 1B's own drafts (scripts/claude_gr1_drafts.py, seed 4860, first
  paragraph, no digits).
- Messages without a square are the 1B's own drafts from rt-02h (artifacts/claude-rt02h-20260926/train, raw), plus
  1B drafts with code-built number blocks that are not squares.
- Squares are built by code (claude_rsn358b2_bridge.make_requests, seeds 486000-486999, sizes 3-8), with about 20%
  broken the way 358b3 breaks them. Layouts are "Row k:" lines, bare lines, "|" cells and comma cells.
- The layer (from a fixed list), the L2 weight and nothing else are picked by 5-fold cross-validation over training
  messages. The pick maximises messages read exactly: squares read as their grid, others read as none.

## Test data (blind, sealed before any head is trained)
artifacts/claude-panel-gr1-20260926 (SEAL-panel.sha256.txt):
- A blind writer that saw no reader code wrote 30 wrappers with a {rows} slot and 40 lookalikes: chat messages with
  numbers in rows that do not ask for a square.
- scripts/claude_gr1_make_panel.py fills the wrappers with 100 fresh squares: seeds 485004-485007, sizes 4-7, 25 each,
  about 20% broken, layouts "Row k:" and bare as in 358b3.
- The truth for each square is the inserted grid. The truth for a lookalike is what the reading definition gives,
  usually none.
- The panel also uses dl-1's 300 general items (no square).
- Only scripts/claude_gr1.py run/score read the panel, and they print counts only.

## Arms (this container's CPU, fp32; each run launched once)
- L: gr-1, the learned reader.
- C: the code stand-in read_latin, report only.

## Marks
| Row | Test | Bar |
|---|---|---|
| R1 | squares read exactly (every cell and the size), L | >= 97 of 100 |
| R2 | lookalikes read as a square where the truth is none, L | <= 1 of 40 |
| R3 | squares read as a different grid (a wrong puzzle), L | <= 1 |
| R4 | general items read as a square, L | 0 of 300 |

gr-1 PASSES only if every row passes. A FAIL stays a FAIL. Report only: C on the same rows, reads by size, layout and
broken or not, and wall time per message.

## Decision rule (fixed now)
If gr-1 passes, the learned reader is offered to Sleep research as the replacement for the stand-in in 358b3's path.
They join it as their own single change. If it fails, the stand-in stays disclosed as scaffolding and the learned grid
reader is still owed.

## What would prove it wrong (fixed now)
- R1 below 97: the head does not reliably find the cells and row starts in unseen wordings.
- R2 or R4 above the bar: it takes number tables in ordinary messages for puzzles.
- R3 above 1: it reads a square but gets a cell wrong. A solver would then answer the wrong puzzle, the worst failure.
