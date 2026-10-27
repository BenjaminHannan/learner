# NOTE gr-4: the plain 1B copying under a grammar, on practice messages only. Not registered. (2026-09-26 20:04 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. This is the obvious-fix test the Thread manager
asked for after Ben's 19:20 rule: before more learned-reader variants, check whether the plain 1B, asked to copy the
square with its output held to a grammar, already reads grids. Nothing was trained and no blind panel was read. The
dev set is 30 practice messages: 10 from 358b3's free smoke panel, 10 fresh code requests (seeds 487004-487007), and
10 of rt-02d's no-square dev cases. Code: scripts/claude_gr4.py (selftest 15/15). $0, this container's CPU.

## Results (dev/)
| Try | Squares exact (of 20) | Squares read as a wrong grid | No-squares answered none (of 10) | Seconds per message |
|---|---|---|---|---|
| Grammar only (grammar_only_30.txt) | 4 | 12 | 3 | 19.5 |
| Grammar plus two worked examples in the chat (two_examples_30.txt, two_examples_dev.py) | 3 | 3 | 10 | 7.1 |

- Grammar only: 7 of the 10 no-squares came out as an invented grid, and 12 squares came out wrong. Looking at 9
  outputs (look9.py): the first row ran on into the second row's first cell, so the grid came out one size too big;
  a row dropped its last blank; a sum puzzle became a 9 x 9 block of 3s.
- Two worked examples (one 4 x 4 square in a 1B wrapper and one 3 x 4 number block answered none, both from gr-1's
  practice set, train.jsonl rows 42 and 7): every no-square now says none, but so do 12 of the 20 squares.
- The bars on a blind panel would be 97 of 100 squares and at most 1 false square. Neither try is near them on dev,
  so gr-4 is not registered and no panel is spent on it.

## Reading (suggested, not tested)
The plain 1B copies numbers but does not decide "is there a square here, and how big" on its own, with or without
examples. That matches rt-02g (plain 1B copies 156 of 159 numbers but cannot decide) and 358b2 (free copy exact on
25-39 of 100). Showing it the format moves the answer between "copy" and "none" without making it right.

## Next plain fix
Train the reader 1B to copy: supervised fine-tuning (a LoRA adapter, the sleep recipe) on gr-1's practice messages and
the 1B's number tables, with targets printed by code (the square, or none). This is the standard way to teach a small
model a text-to-structure task. The plan goes to the Thread manager before anything is sealed.
