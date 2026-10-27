# ADDENDUM gr-1 #1: more practice layouts and a second blind test of formats practice never had (2026-09-26 17:32 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. This addendum was written before any head was
trained and before any gr-1 run. PASSMARKS-gr1.md is not edited.

## Why
The Thread manager asked for it after rt-02h failed on one blind wording: "Sleep research's scorer fix found tables with
header rows, row labels and LaTeX arrays in real replies. Make sure its practice includes those formats ... and that
its blind panel has formats practice never saw."

## Change 1: practice layouts (the training set only; the head is not trained yet)
Practice squares now use 8 layouts, not 4 (claude_gr1.LAYOUTS, drawn by claude_gr1.layout_recipe):
- The 4 registered layouts: "Row k:" lines, bare lines, "|" cells and comma cells.
- Markdown tables with a header row of column names and a "|---|" line.
- LaTeX arrays, with or without "$$" lines.
- Row labels: "A:", "R1:", "1)", "row 1 -".
- A header line of column numbers or letters, then rows labelled by number or letter and " | ".
The labels and headers are not cells, and the head is trained to tag them O. Number blocks that are not squares now
also come in these layouts (a column too many, or numbers above 9). Everything else in PASSMARKS "Training" stands: the
words are the 1B's own drafts, and code builds the squares and the labels. The wording stays the 1B's, and GLM is not
used. For a grid reader, the risk is the layout of the rows, not the words around them. gr-1U (below) reports reads by
wrapper, so a gap in wording would show there.

R1-R4, their bars, the arms and the decision rule are unchanged. The sealed gr-1 blind panel is unchanged.

## Change 2: gr-1U, a second blind test with its own marks
- Formats: a blind writer that saw no code was told all 8 practice layouts. It wrote 20 grid format recipes that are
  none of them: prefix, separator, suffix, the text between rows, divider lines and header lines. Blanks stay "_", as
  in the reading definition.
- Panel: artifacts/claude-panel-gr1u-20260926, made by scripts/claude_gr1u_make_panel.py and sealed before any head is
  trained. It has 3 fresh squares per format (seeds 488004-488007, sizes 4-7, 15 each, about 20% broken), each inside
  one of gr-1's sealed blind wrappers, 60 messages in all. A message where two cells fall in one token of the 1B's
  tokenizer is kept and counted, because the reader cannot read it exactly.
- Run: the same head, launched once (`claude_gr1.py run --task unseen`). Score: `claude_gr1.py scoreu`.

| Row | Test | Bar |
|---|---|---|
| U1 | squares in unseen formats read exactly, L | >= 48 of 60 |
| U2 | squares in unseen formats read as a different grid, L | <= 2 |

gr-1U passes only if both rows pass, and it gets its own verdict. It does not change gr-1's decision rule: R1-R4 still
decide the offer to Sleep research. Report only: C (the code stand-in) on the same 60; reads by format; formats read
3 of 3 and 0 of 3; reads without token clashes.

What would prove it wrong (fixed now): U1 below 48 means the head learned the practice layouts, not what a grid is. A
new format then needs its own examples, and the next measure is how many. U2 above 2 means it reads new formats
wrongly instead of declining them, which is the worst failure.
