# R2g: tied directions, made general (design note)

Written 2026-09-28 21:27 UTC (`date -u`) by helper R2g (Claude). Rebuilds design R2 of `artifacts/claude-dir-h9-novelty-20260928/REPORT.md` (section 5) so it is not a grid
rule. Nothing here has a maze score. Labels: **shown** = read in a file or produced by the CPU selftest (`selftest.json`); **suggested** = my reasoning; **untested** = no run.

## What is wrong with R2 as written (shown)
H9's R2 tied the loop's up/down/left/right position biases with a 15-entry table indexed by (rows apart, columns apart), fixed the residual at eps = 0.3, and
changed the narrow-head mask from a column strip to a cross. H11's check (`artifacts/claude-dir-h11-check-20260928/CHECK.md`, PR 5) called it "grid-specific and hand-picked" and noted a word question has no 2-D grid.

## The general form (built)
The loop's bias is `br[dr] + bc[dc]` (one signed table per axis; `claude_fewex_net.py:35-41`). R2g replaces it with

    bias(i, j) = sum over axes a of tie[|d_a|]  +  0.3 * (br[dr] + bc[dc])

- `tie` is one learned table of distances 0..4 per head and block (8 x 5 x 2 = **80 new weights**). It is shared by every axis and both signs: "one step away" is one fact.
- The old signed tables stay, scaled by a fixed 0.3, so their effective learning pace is 0.3 of the tied part's (Adam moves each weight by about the same step; the
  output moves 0.3 as far). This is the residual-pathway recipe (Finzi et al., arXiv 2112.01388, cited by H9). 0.3 is fixed now and never tuned.
- The narrow heads (first 4 of 8) may attend where at most one axis is far (|d| > 1), a cross of strips. The loop's strip is a column-only rule. For one axis nothing is masked.
- Nothing in it names a puzzle, a slot, a wall, a start, a goal or a grid size. It reads only the per-axis offsets between two positions: `tied_bias(tie, resid, axes)` takes a list of
  [T, T] offset tensors, one per coordinate axis, from `coord_offsets(coords)` for any coordinates [T, n] (1 axis = a token sequence, 2 = a grid, 3 = a block, any cell order).
  **Shown by the selftest** (`selftest.json`): the shared bias is unchanged by axis flips and axis swaps on 1-, 2- and 3-axis layouts and on a shuffled point cloud; a block gives the
  permuted output for a permuted cell order; a fresh net with a random tie table maps a flipped or transposed 7x5 grid to the flipped or transposed logits to 1e-6, while the untied loop with random signed tables does not (gap 0.28).
- What is learned and what is fixed (say this to Ben plainly): the **table is learned**; the **sharing rule** (same distance on any axis, either side, is one relation) comes from the
  coordinates and is fixed, not learned; the mix 0.3 is fixed. A layout with no coordinates (a bag of words with no order, a graph with no embedding) gets no tying: this design does nothing there. It is a symmetry
  assumption about coordinate layouts, one step more general than R2 (which had 15 two-axis orbits). It is not a claim that the net discovers symmetry.

## Why it might work on the ruler (suggested, untested)
All the loop's other weights are direction-blind; direction enters only through this bias and the strip mask (`claude_fewex_net.py:33-45`). Sharing removes about half of the direction-specific facts the
net must learn from k mazes (two signed 9-entry tables per head become one 5-entry table plus a slow correction). H9's arithmetic says a 4-times gain in examples everywhere is worth about +10 F_eq, so a
smaller real gain is likely. My chance of +10 in both seeds: under one in three (a guess). Risk: practice on sums (which carry leftward) may need the direction-specific residual at a faster pace than 0.3; the source guard catches a broken sums result before any maze run.

## Cost (shown, `selftest.json`)
Stored 1,645,806 against the loop's 1,645,726: +80 weights, +0.0049%. No added compute: CPU step times equal the loop's within noise (sums 0.43 s vs 0.41 s, one sample each).

## One change, and the honest caveat
The tie and the mask change are two halves of one "orientation prior" (H9 REPORT:296-298 said the same). `TiedBlock.CROSS = False` gives the table-only variant (loop mask kept); the selftest shows it equals
the base block with the signed tables scaled by 0.3 (error 0). It is not run in this race; it is the next design if this one is not promoted and the Director wants the purer edit.

## Next after this (not built)
An alternative that learns the sharing itself, "R2b": a learned embedding per relation id with a low-rank bias. It would work on layouts with no coordinates but has no symmetry prior; **untested**, and I do not expect it to help few-example maze learning from sums and grids practice.
