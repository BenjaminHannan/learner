# ADDENDUM gr-1 #2: the blank mark written in words (2026-09-26 18:08 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. This addendum was written before the registered
head was trained and before any gr-1 run. PASSMARKS-gr1.md and ADDENDUM-gr1-1.md are not edited. No blind panel was
read.

## What the development check showed (dev data only)
A first head (v1) was trained on the practice set from ADDENDUM-1. Its cross-validation read 796 of 820 practice
messages exactly, choosing layer 8 and L2 0.001; all 24 misses were squares read as none. On development data, it read
21 of 30 of 358b3's smoke messages and 18 of 24 fresh bridge messages, with 0 wrong grids and 0 of 135 no-square
messages read as a square. In 14 of the 15 dev misses, the grid itself was read, but the "(_)" in the sentence "Fill
in the blanks (_) ..." was tagged as a one-cell first row. None of the 1B's practice wrappers contains "_", so the head
had never seen the blank mark in running text. 358b3's own messages use that sentence, so this matters for the 0.2d
path.

## Brain first
A person knows the "_" in "blanks (_)" is part of a sentence that explains the mark, not a cell, because it sits in
prose and not in a row of marks. The head needs examples of that.

## The change (training set only)
Code adds the blank mark after the 1B's own word for it. In the 1B's wrapper drafts that say "blank(s)" or
"underscore(s)", the mark " (_)", ' ("_")', " '_'" or " _" is inserted right after that word. Code writes only the
mark; the words stay the 1B's. 30% of the square messages use such a marked wrapper, and there are 40 new no-square
messages made of a marked wrapper alone. The labels stay code-made, and the mark is always O. A 3 x 3 puzzle with no
row that has both a clue and a blank is left whole rather than broken, which is a code fix for a crash.

Everything else stands: layer, L2 and nothing else are picked by CV. R1-R4, U1-U2, the arms, the panels and the
decision rule are unchanged. v1's head is not used for any run.
