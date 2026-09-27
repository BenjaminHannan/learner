# PLAN gr-7d: where do the trained reader's bad reads come from? (practice only; written 2026-09-27 07:46 UTC)

Owner: Plain-English puzzles thread. Times from `date -u`. This is a diagnosis on a fresh code-made practice set. It is
never a test, it is never trained on, and it gives no verdict on any reader. The predictions and the result that would
sink the distractor-block idea are fixed here, before any reader runs on the set.

## Why
gr-7 (VERIFY-gr7, 737d4c3f4) failed on 2 false squares, 3 wrong squares and 5 wrong unseen-format squares. I proposed
to sort those 10 bad reads by where they came from. The Thread manager (07:38 UTC) said no: the spent gr-6 panel is
never read, even as counts by a separate agent, because choosing gr-8's change from its failures would be tuning on it.
The obvious route instead is a fresh code-made practice set of the same kinds, with L7 (gr-7's adapter) and G5 (gr-5's
adapter) run on it on this CPU at $0, and the count done there. That gives more bad reads than 10, and it leaves a
future blind panel clean.

## The practice set (scripts/claude_gr7_diag.py make; sealed with this plan)
- **Squares (200).** Seeds 507104-507107, 50 per size from 4 to 7, 38 broken as in 358b3. Layouts are "Row k:" and bare,
  alternating, as in the panel. read_latin reads all 200 exactly.
- **Unseen formats (200).** Seeds 507204-507207, 5 squares in each of 40 formats. The formats are drawn by code (seed
  5073) from gr-6's part lists plus new ones (NEW_LABELS, NEW_WRAPS and NEW_SEPS, hand-written scaffolding, disclosed).
  No format writes a row the same way as a training or dev layout (claude_gr6.signature). Formats F00 to F19 use a cell
  separator seen in training, and F20 to F39 use a new one. A format whose row label or row end uses the separator's
  mark (like "1 - 3 - 4") is not drawn, because it is ambiguous even to a person.
- **Lookalikes (150), in 3 kinds of 50.** All are blocks in training layouts:
  - near misses: s x s single digits with one above s, the kind gr-6 trained on
  - non-square blocks: r x c single digits, with r not equal to c
  - square blocks of numbers up to 40, with at least one two-digit number

  read_latin reads none of them as a square (0 redrawn).
- **The words around the grids** are the 1B's own openers and closers, plus its everyday drafts for the lookalikes. These
  are the same pools gr-6 and gr-7 trained with. So the words are familiar to the reader, where the panel's came from a
  blind writer. Only the grids, the seeds and the unseen formats are new.
- **What the owner looked at before writing this.** The owner looked at the 40 formats, one row of each task and one
  lookalike of each kind to check the maker. No reader has run on the set.

## What runs
cpu/chain.sh checks the seals and both adapters' sha256, then runs the sealed `claude_gr7.py run` unchanged:
- arms L7 and G5
- tasks lookalikes, squares and unseen, each launched once
- then `claude_gr7_diag.py count`

The chain runs on this container's CPU at $0, for about 1.6 hours estimated.

## The kinds of bad read (fixed now; code in claude_gr7_diag.py)
**Terms.**
- A *far* output row is not within 1 cell of any truth row of the same length.
- T is every digit and "_" in the message, in order. A token is a *cell token* when it is one of the square's own cells.
  The maker records where the cells are.

**A wrong grid** is a square that was there but was read as a different grid. It is one of three kinds:
- **A: numbers that are not cells.** Some far output row is an exact run of T that includes a non-cell token: a row
  label, a column header, a number in the words, or another block. This is the kind the distractor-block idea is for.
- **B: lost its place in the square.** It is not A. Also, at most one output row is far, or the output's cells in order
  are within 2 edits of the truth's. Examples are a shifted cell, a skipped or repeated row, and a few slips.
- **C: other.** Two or more rows are neither the square's rows nor the message's numbers.

**A false square** is a lookalike whose truth is none but which the reader returned as a grid. It is one of two kinds:
- **A: it copied the message's numbers.** All but at most one output row are exact runs of T.
- **C: other.**

Squares read as none are counted but are not bad reads here.

## Predictions (fixed now)
1. L7 returns at least 10 wrong grids on squares and unseen together, most of them in the new-separator formats.
2. B is at least half of L7's wrong grids, and A is under a third.
3. L7 has at least 5 false squares on the 150 lookalikes, mostly in the non-square and numbers kinds. At least two
   thirds of them are A.
4. G5 has more wrong grids than L7 on the unseen formats.

## What decides (fixed now)
- **The distractor-block idea is SUNK for these kinds** if A is under a third of L7's wrong grids on squares and unseen,
  with at least 10 of them. It is NOT SUNK, and stays a candidate, if A is a third or more.
- **Too few.** Under 10 wrong grids decides nothing, and no gr-8 is chosen from the count.
- **My own reading is proved wrong** if B is under half of L7's wrong grids. That reading is that the reader loses its
  place inside the square.
- **Lookalikes are reported on their own.** A false square on a lookalike is the target of gr-6's near-miss rows, not of
  distractor blocks. The pooled split is printed too, as report only.

## Before anything goes out
- A separate agent recounts the kinds with its own code from this plan's definitions and the run files. Its script and
  output go under recount/.
- Then one line goes to the Thread manager.
- Nothing about gr-8 is sealed from this. A gr-8 plan goes to the Thread manager first and gets a fresh blind panel.
