# DRAFT pass marks for gr-9: separator variety in the reader's training (dev only)

Owner: Plain-English puzzles thread. This is a draft for the Thread manager's review, written on 2026-09-27; the commit
carries the time. Nothing is sealed, trained or run yet. The script is scripts/claude_gr9.py (selftest 5/5). Its
training rows and dev set were built once, in a scratch folder, only to check the counts below. The owner read 5 dev
rows and 4 training rows to check their shape.

## Why
- gr-7d (RESULT-gr7d, 07ccf04be) and gr-8 dev (RESULT-gr8d, c0dd55c54) are practice data only, and suggested only.
- In gr-8 dev, gr-7's reader read 99 of 100 new-format squares exactly when it had seen the separator in training.
  With a new separator, it read 63 of 100.
- The size pick fixed most wrong sizes (21 to 7), but the grids stayed wrong (37 to 33 wrong). So the size is not the
  main problem. The unfamiliar separator is.
- The Thread manager chose separator variety as the next change (11:5x).

## Brain first
A child who has copied grids written with commas and bars can copy one written with dots. They have learned that the
thing between the numbers is only a divider, whatever it looks like. This is a guess about the brain, not a claim.

## The one change
gr-7's adapter trains 3 more epochs on gr-6's training rows plus new code-made rows whose cells are split by
separators the reader has never seen. Nothing else changes: the same prompt, grammar, greedy read and recipe.

## The separator sets (Thread manager points 1, 2 and 6)
- **The list.** A hand-written list of 59 marks (SEP_MARKS in the script), disclosed as scaffolding. It is a list of
  symbols, not training text. It was written before any training and without looking at any panel.
- **No shared characters.** Two marks that share a character go in the same family. Marks that look alike count as one
  character; the lookalike table (LOOKS) is hand-written and disclosed. It can only make the held-out sets harder.
- **Dropped marks.** "||", "//" and "¦" share a character with a separator gr-6 trained on, so they are dropped.
- **The split.** Code splits whole families, so no character (after LOOKS) is in two sets. The four marks that failed
  most in gr-8 force their families into dev. Code then draws test families with seed 5091 until test has at least
  10 marks. Training gets the rest.

| Set | Marks | Count |
|---|---|---|
| Dev held-out | `.` `·` `•` `…` `∙` `..` / `*` `×` `**` / `=` `==` / `:` `-` `::` `--` `:-` `-:` | 17 in 4 families |
| Test held-out | `§` `$` `£` `%` `¶` `!` `!!` `'` `"` `` ` `` `''` | 11 in 6 families |
| Training | `¤` `?` `¿` `¢` `@` `µ` `°` `○` `÷` `¥` `«` `»` `€` `^` `^^` `■` `~` `~~` `#` `¬` `♦` `©` `+` `†` `±` `++` `‡` `\` | 28 |

- **One change from your point 1.** Dev holds 17 marks, not 10. Keeping whole families apart puts every dot, star,
  equals, colon and dash mark in dev. My first draft split by exact string, which would have trained on ".." and "**"
  while testing "." and "*".
- **Test is reserved.** The test marks are never trained on and never used in dev. They are kept for the registered
  blind test that follows a DEV-PASS.
- **Spacing.** Each format draws the spacing " m ", "m " or "m" by code.
- **Ambiguous formats are redrawn.** A format is redrawn if its row label, row end, divider or text around the block
  uses the separator's mark, or if its row join equals the separator.

## Training rows (all code-made, Thread manager point 6)
- **gr-6's 1072 training rows**, unchanged.
- **300 squares**, spread evenly over the 28 training marks (10 or 11 each). Each is in a format drawn from gr-6's and
  gr-7d's part lists and sits inside the 1B's own openers and closers. About 20% are broken (64 of 300 in the draft
  build), as in gr-6. Sizes 3 to 8.
- **80 near misses** in those formats, labelled none, as gr-6 built them.
- Total 1452 rows. No Claude-written text: the grids and formats are code, and the wrappers are the 1B's own drafts.
- **Recipe.** Start from gr-7's adapter (sha256 c8f95557…). Fresh AdamW, constant lr 2e-4, batch 8, loss on the answer
  only, 3 epochs, seed 5090. This is gr-5's recipe, as in gr-7.

## The dev set (fresh practice, never a test)
It is made by `claude_gr9.py make` with seeds 5092 to 5096 and 5098.
- **Squares:** 200, in the practice layouts. read_latin reads all 200 exactly.
- **Seen:** 100 squares in 20 new formats with separators gr-6 trained on.
- **Held-out:** 100 squares in 21 formats with the dev marks. The four forced marks have 2 formats and 10 items each;
  the other 13 marks have 1 format and 4 or 5 items each.
- **Lookalikes:** 150 (near, nonsquare and numbers, 50 each). 81 are written in the dev formats (49 held-out, 32 seen)
  and 69 in gr-6's training formats. read_latin reads none of them as a square.

## Marks (fixed now; every mark uses the greedy read, as in gr-7)
L9 is the new adapter and L7 is gr-7's. Both use the greedy read (claude_gr5.Copier5), and L7 reads the same held-out
items and lookalikes.

| Mark | Test | Bar |
|---|---|---|
| M1 | held-out squares read exactly by L9 | at least 90 of 100 |
| M2 | practice-layout squares read exactly by L9 | at least 199 of 200 |
| M3 | seen-separator squares read exactly by L9 | at least 98 of 100 |
| M4 | lookalikes read as a square | L9 at most L7 + 1 |

- **DEV-PASS** needs every mark to pass.
- **PROVED WRONG:** L9 reads fewer than 10 more held-out squares exactly than L7, on the same items with the same greedy
  read (point 4).
- **TOO-EASY:** L7 already reads at least 85 of the 100 held-out squares, so the set cannot show the change. This is
  decided before the other marks.
- **Report only:**
  - the size pick (claude_gr8.Copier8, from the same pass as L9's greedy read);
  - held-out counts by mark and for the four forced marks;
  - lookalikes by the format they were written in;
  - mean training loss by epoch.

## Caveat from the design check (Thread manager point 5, design data only)
- **The count.** artifacts/claude-gr9-20260927/design/blanks.py counted gr-7's greedy row errors on gr-8 dev's fresh
  new-format squares, for grids read at the right size. Rows are split by whether two blanks sit next to each other.
- **What it found.** In " . " and " * " formats, 12 of 121 such rows were wrong, against 0 of 87 other rows. Other new
  separators: 9 of 140 against 5 of 85. Seen separators: 0 of 365 against 1 of 184. gr-7d had only 8 right-size dot
  or star rows (none wrong), so it cannot check this.
- **What it suggests.** Some dot and star errors may come from "_ . _" runs, where the blank marker and the separator
  alternate, rather than from the separator only being new. Separator variety might not fix those. The result will
  report held-out rows split the same way (report only).

## Predictions (fixed now)
- L7 reads 45 to 70 of the 100 held-out squares; L9 reads 92 to 98 (gain at least 25).
- L9 reads 200 of 200 practice squares and 99 or 100 seen-separator squares.
- L9 lookalike false squares are within 1 of L7's, and L7 has at most 8.
- The last epoch's mean loss is at most 0.01.

## What follows
- **DEV-PASS:** a registered gr-9 on a fresh blind panel in the test held-out marks. Its plan goes to you first.
- **DEV-FAIL:** a post hoc count on practice data only, and the next change goes to you first.
- **PROVED WRONG:** variety in 28 marks does not carry to new families. Count-first training (your 09:36 line) is next.
- **TOO-EASY:** I report it and ask you before anything else.

## Where it runs
- This container's CPU, 4 threads, $0.
- Training takes about 2.7 hours (gr-7's 3 epochs on 1072 rows took 117 minutes). The dev runs take about 1.75 hours.
- A chain script will check the seals and gr-7's adapter sha256, then run train, the six run files (each launched
  once) and the count.
- A separate agent recounts from the run files before the result goes out.
