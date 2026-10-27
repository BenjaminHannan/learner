# DEV REPORT gr-1 (2026-09-26, before the code seal and before any run; no blind panel read)

Owner: Plain-English puzzles thread. Everything below uses practice data and dev data only. CPU on this container,
$0.

## Practice set (train/train.jsonl, made by `claude_gr1.py build`, seed 486000)
- The 1B's wrapper drafts (train/wrap_drafts_1b.jsonl, claude_gr1_drafts.py, seed 4860, plain 1B with every LoRA scale
  at 0): 260 drafts, of which 248 were kept (189 openers, 59 closers; no digits; 400 characters or fewer).
- 360 squares (sizes 3-8, about 20% broken) in 8 layouts (ADDENDUM-1), with the 1B's words around them. 96 of them
  sit in wrappers where code added the blank mark after the 1B's word "blank(s)" or "underscore(s)" (ADDENDUM-2).
- 500 messages without a square: 240 of rt-02h's raw 1B drafts, 60 openers alone, 40 marked wrappers alone, and 160
  code-built number blocks that are not squares (ragged, too wide, too short, numbers above 9, one line, and these
  in the practice layouts).
- Code checks: all 360 squares decode back to the inserted grid from their labels; read_latin finds a square in none
  of the 500 others; no token holds two cells (the feature step asserts this).

## Head (head.pt)
Picked by 5-fold CV over messages, maximising messages read exactly: layer 8, L2 0.001, with 840 of 860 read
exactly in CV. The other choices got 835 to 839 (L2 0.001) and 800 to 814 (L2 0.01).

## Development check (`claude_gr1.py dev`)
| Set | v1 head (ADDENDUM-1 practice) | registered head (ADDENDUM-2 practice) |
|---|---|---|
| 358b3 smoke messages, read exactly | 21 of 30 | 30 of 30 |
| fresh bridge messages (seeds 487004-487007), read exactly | 18 of 24 | 24 of 24 |
| wrong grids | 0 | 0 |
| no-square dev messages read as a square (rt-02d dev, rt-02e practice) | 0 of 135 | 0 of 135 |

The code stand-in read_latin reads 0 of the 135 no-square messages as a square as well. The v1 misses were the "(_)"
in "Fill in the blanks (_)" being read as a cell (14 of 15). ADDENDUM-2 is the one change between the columns.

## What this does not show
Dev messages use the "Row k:" layout and one wording. The blind panels test new wordings (gr-1), and formats practice
never had (gr-1U).
