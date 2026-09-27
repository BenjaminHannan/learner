# DEV note: can the plain 1B get lucky in the two new worlds? (creative research thread; written 2026-09-26 23:47 UTC by `date -u`)

DEV items only (seeds 900000-900011, the creative range Sleep research never uses; no test items). Plain
MiniCPM5-1B (commit 87179e5c, no adapter, thinking off, chat template), on this container's CPU. For each item: one
greedy reply, then 30 samples at temperature 1.0 (plain sampling, no constrained decoding). "Reached" = at least one
of the 30 samples passes the exact code checker. Raw outputs: dev/*.json in this folder.

| world and reply form | code (commit) | items | greedy right | reached in 30 | right samples |
|---|---|---|---|---|---|
| squares 3x3, 3 blanks, whole square back (world's own prompt) | claude_latin_dev.py (62bcd77b7) | 10 | 0 | 0 | 0 |
| squares 3x3, 2 blanks, missing numbers only * | (0fd5f0902) | 10 | 0 | 7 | 28 |
| squares 3x3, 3 blanks, missing numbers only * | (0fd5f0902) | 10 | 1 | 6 | 12 |
| squares 4x4, 3 blanks, missing numbers only, exact count | (f31e26172) | 12 | 0 | 0 | 0 |
| squares 4x4, 5 blanks, same | (f31e26172) | 12 | 0 | 0 | 0 |
| squares 4x4, 7 blanks, same | (f31e26172) | 12 | 0 | 0 | 0 |
| text game keys, level 1 (plans 3-8 steps) | --form game (9c7c0de05) | 10 | 0 | 0 | 0 |
| text game recipes, level 1 (plans 4-6 steps) | --form game (9c7c0de05) | 10 | 0 | 0 | 0 |

\* These two rows used my first check, which read the first k numbers of the reply. It lets echoed clues count as
luck (greedy replies such as "3 1 2 2 1 3 2 1 3 …"), so they overstate luck and are not comparable to the exact-count
rows. Sleep research's check_blanks (exact count) replaced it for every later row. 3x3 is too small a world for
practice plus a test anyway (12 distinct squares).

Commands (the model path is the local snapshot of plain MiniCPM5-1B):
    python3 -B scripts/claude_latin_dev.py --model M --out F --settings 3:3 --items 10                  (whole square)
    python3 -B scripts/claude_latin_dev.py --model M --out F --form blanks --settings 3:2,3:3 --items 10
    python3 -B scripts/claude_latin_dev.py --model M --out F --form blanks --settings 4:3,4:5,4:7 --items 12
    python3 -B scripts/claude_latin_dev.py --model M --out F --form game --settings keys:1,recipes:1 --items 10

Three wrong greedy replies each (copied from the outputs):
- 4x4, 5 blanks: "1 3 4 2 5 6 7 8 9 10 11 12"; "3 4 1 2 4 3 1 2 3 4 2 1"; "3 4 1 2 4 3 1 2 4 3 2 1" (too many numbers).
- keys level 1: "go Ivystone / take blue key / go Glimmer Den / go Kestrel Attic / go Ivystone";
  "go ivystone / take blue key / go cobblenook / go lanterncellar / take green key / go kestrel Attic";
  "go Lantern Cellar / take gold key / go Cobble Nook / go Dunmere" (well formed, wrong).
- recipes level 1: "make flint"; "make resin / make honey / make reed / make thorn"; "make salt / make ash / make chalk /
  make twine".

Finding: with 4x4 squares (exact check) and level-1 text games, the plain 1B got no lucky hits in 30 samples on any
DEV item. A loop that learns from its own lucky hits has nothing to start from there. Next: text games at level 0
(1-2 step plans, Sleep research aec0ae1da), reported by plan length; and the replication moves to a wider number world
(brd-11).

## Addendum (2026-09-27T05:15Z): wider number world and level-0 games (DEV only, CPU, plain MiniCPM5-1B, 30 samples)

| setting | command | items | greedy right | reached in 30 | lucky samples |
|---|---|---|---|---|---|
| wider number world, rule-kept, T 1.0 (20 three-number 1-13 / target 5-60, 20 four-number 1-13 / target 24) | brd-11 --dev (464ebce58 code) | 40 | 2 | 11 (3-number 11 of 20, 4-number 0 of 20) | 38 |
| text game keys, level 0 (plans 1-2 steps) | --form game --settings keys:0 --items 20 | 20 | 4 | 11 (1-step 11 of 16, 2-step 0 of 4) | 43 |
| text game recipes, level 0 | same, recipes:0 | not run | | | |

Files: dev/wide_rulekept_T1.0.json, dev/games_level0_keys.json. Recipes at level 0 hit the 10,000 s CPU timeout
before writing a line, so there is no number for it.

Reading the 4-number 0 of 20: brd-9's base model reached 40 of its 160 four-number test puzzles (numbers 1-13, target
24), but brd-9 sampled at T 1.5, chosen by its DEV rule. The run above used T 1.0, and 20 items is small. brd-11 as
drafted fixed T at 1.0, which differs from brd-9's recipe; it now applies brd-9's DEV rule (claude_blurt2.pick_temp,
1.0 vs 1.5) on its own DEV panel. A T 1.5 DEV measurement is running to check 4-number luck before the panel mix is
fixed.

Level-0 key games: one-step plans give luck (11 of 16), two-step plans none (0 of 4). A games loop could start there,
but level 1 (0 of 20) is out of reach without a curriculum.

## Addendum (2026-09-27T05:30Z): wider world at T 1.5, and how many 4-number puzzles are left
T 1.5 (brd-11 --dev --temps 1.5, 40 puzzles, 30 samples): reached 17 (3-number 12 of 20, 4-number 5 of 20), greedy
right 2, lucky 39. File: dev/wide_rulekept_T1.5.json. So 4-number luck exists at T 1.5 (0 of 20 at T 1.0).
The 4-number target-24 world (numbers 1-13) has 1,362 solvable puzzles; brd-5..9 and brd-11's nights and DEV use 1,242,
leaving 120. brd-11's panel takes all 120 plus 120 three-number puzzles.
