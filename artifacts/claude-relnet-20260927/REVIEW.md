# relnet: review of GPT-6 Pro's design 3 (persistent relation-state network), with build checks

Written 2026-09-27 20:36 UTC; updated 20:57 UTC. CPU only (4 threads), fp32, $0. At first Ben cut the scope to a
20-minute review, then withdrew that ("go based off the first prompt"). The practice gate is therefore running; its
result will go in RESULTS.md. The race (Test C) waits for the test chat's RACE-PASSMARKS.md, which was not on
origin/main at 20:39 UTC.

Files: scripts/claude_relnet_net.py (the net and the checks), scripts/claude_relnet_smoke.py (a 300-step learning
smoke), checks.json/checks.log, smoke-relnet.log and smoke-loop.json/.log. The first smoke run crashed on the loop arm because of a setup bug in the smoke script (wrong arm name, so no stop head). The relation-net arm had already finished and is kept as smoke-relnet.log, with the traceback. The loop arm was rerun alone with the fix.

## 1. What was built (shown)
The equations in reviews/gpt6pro-brain-reasoner-contenders-REPLY-2026-09-27.md, design 3, at width 256 with
relation width q = 64 and the MLP hidden width GPT gives (1,576). The inputs are only cell tokens, the fill-in
flag (slot) and row/column offsets clipped at 4, as in the loop. There is no kind label, no constraint graph, no
maze adjacency and no carry rule. Relation states start at zero for each puzzle and carry across rounds. The stop
head is the loop's. The training schedule is the loop's: 1-16 rounds, gradient through the last 1-6. The net has
the same interface as the xfer-1 loop, so the existing practice code runs it unchanged.
Two additions GPT did not write: a LayerNorm before the MLP and a state LayerNorm after the residual, as the loop
has. Suggested (not tested): without them the state could grow without bound over 48 rounds.

**Weight table** (relation net vs the 358e small dense loop, 2 x 256, 8 heads):

| part | relation net | loop |
|---|---:|---:|
| embeddings (token, slot, kind*, position) | 33,664 | 33,536 |
| reasoning core | 1,577,640 | 1,580,320 |
| answer head + read-out norm | 32,637 | 32,637 |
| stop head | 257 | 257 |
| **total** | **1,644,198** | **1,646,750** (-0.155%) |

*Only the loop has the kind embedding (4 kinds x 256 = 1,024 weights; the 358e loop adds mazes to sums, grids and numbers). The relation net's position tables have 1,152 weights.
The smoke loop in section 2 is the same design without the kind embedding, hence 1,024 fewer weights (1,645,726).
Core detail: GRU_n 591,360; MLP 808,744; V 65,536; GRU_e 61,824; P_h, P_v and U 16,384 each; norms 1,024.
There is no persistent coefficient beyond these weights.

**Gradient check:** in one fp32 step with no autocast, all 19 of 19 weight matrices, and every other weight, got a
nonzero gradient.

**Cost** (one worst-case training step of 16 rounds with gradient through 6, and 48-round inference; time per puzzle;
each row in its own process; re-run at 20:53 UTC after a speed-up that computes the round-invariant gate terms once
per puzzle — same outputs to 1e-6, 48-round answers identical):

| size (batch) | train, relation net | train, loop | ratio | inference, relation net | inference, loop | ratio | peak memory, relation net / loop |
|---|---:|---:|---:|---:|---:|---:|---:|
| 5x5 (8) | 23 ms | 19 ms | 1.2x | 35 ms | 33 ms | 1.1x | 0.9 / 0.8 GB |
| 7x7 (32) | 91 ms | 15 ms | 6.2x | 132 ms | 36 ms | 3.6x | 2.9 / 1.3 GB |
| 9x9 (4) | 192 ms | 50 ms | 3.9x | 424 ms | 91 ms | 4.6x | 1.6 / 0.8 GB |
| 11x11 (2) | 362 ms | 83 ms | 4.4x | 809 ms | 140 ms | 5.8x | 1.7 / 0.8 GB |

Caveats:
- Memory is the peak for the whole process, including about 0.6 GB for PyTorch itself.
- The small-batch ratios are rough. 7x7 with batch 32 is the maze-training size, so the 6.2x there is the one that
  matters for the race.
- No batch or round window had to shrink. No pairs were cut.
- An earlier pass, before the speed-up and with memory not split by net, gave 3.4-4.8x at 9x9 and 11x11.
- torch.compile gave a further 25% but was not used: it took 72 s to compile and adds risk in the backward pass.

## 2. Learning smoke (shown, but only a smoke)
One seed. The same 300 batches of 32 sums and grids went to both nets, with the xfer-1 loss and the 1-16-round schedule. The
loop is the xfer-1 design at 2 x 256 with no kind label (1,645,726 weights).

| | relation net | loop |
|---|---:|---:|
| mean loss, first 50 steps | 3.564 | 3.661 |
| mean loss, last 50 steps | 2.086 | 1.726 |
| 4-digit sums right (16 rounds) | 0 of 100 | 0 of 100 |
| 5x5 grids right (16 rounds) | 0 of 100 | 0 of 100 |
| training time | 106 s | 44 s (2.4x less) |

- Shown: the relation net trains, and its loss falls.
- Suggested: it falls more slowly than the loop's over the same batches, and less smoothly (2.08 at steps 150-175,
  then 2.52 at 175-200).
- Untested: whether it passes the practice gate. 300 small batches is about 2.5% of the practice recipe.

## 3. Review of the idea

**Prior work.** The literature search ran through web-search snippets. The proxy blocked the arXiv and OpenReview
pages, so the papers were not read in full.
- **Recurrent Relational Networks** (Palm et al. 2018, arXiv 1711.08028). Shown: they solve Sudoku with repeated
  message passing, but over a **given** row/column/box graph. Messages are recomputed each step, with no stored pair
  state.
- **Edge Transformer** (Bergen et al. 2021, arXiv 2112.00578). Shown: it keeps a state for every pair with no given
  graph, and its triangle attention (i to k to j) beat transformers on compositional tests. Its pair states pass from
  layer to layer, not round to round.
- **AlphaFold2**. Shown: it recycles a pair representation with triangle updates.
- **Triplet-GMPNN** (arXiv 2209.11142) and the **Relational Transformer** (arXiv 2210.05062). Shown: both use edge or
  triplet messages for algorithm learning.
- Suggested: no paper was found with exactly this recipe, a GRU relation state carried across rounds over all pairs
  with no triangle term. It is a new combination of known parts.
- Untested: no paper was found that tests learning a new puzzle kind from few examples after practice, for any of
  these nets.

**Weak points, in order of how much they matter:**
1. **Suggested: no triangle term.** r_ij sees only h_i, h_j, the two symbols and the offset. It can never combine
   "i relates to k" with "k relates to j". Maze solving is exactly that kind of chaining (is this cell connected to
   the exit through open cells?). So every multi-step hop still has to pass through the cell states, as in the loop.
   The pair state then works like an attention score with memory, which is less different from the transformer than
   the pitch suggests. The strongest all-pairs nets (Edge Transformer, AlphaFold2, Triplet-GMPNN) all have a
   triangle or triplet term.
   Arithmetic (shown): at 121 cells a triangle update costs about 121^3 x 64 = 113M multiply-adds per round. The
   pair GRU already costs 14,641 x 3 x 64 x 64 = 180M. So adding one would not change the cost class.
2. **Suggested: the message is a plain mean over all N cells.** There is no softmax. A cell's 2-4 useful neighbours
   are averaged with 120 others at 11x11, and with 24 at 5x5. The message size therefore shifts about 5x between
   the sizes it practises on and the 9x9/11x11 tests. The loop's softmax attention does not have this problem.
3. **Shown: it is 3.6-6.2x slower than the loop at 7x7 to 11x11**, with the same weight count.
4. **Suggested: nothing in it is a fast-learning mechanism.** It changes what the net finds easy to represent, not
   how an example changes the net. Any few-example gain has to come from relation habits learned on sums and grids
   carrying over to mazes. In sums and grids, "same row" and "next column" are fixed by position. In mazes, a
   neighbour counts only if both cells are open, so it also depends on content.
5. **Suggested: the brain story is thin.** The honest analogy is short-term synaptic change (fast weights, Ba et al.
   2016; activity-silent working memory, Mongillo et al. 2008). But r_ij is a learned GRU vector, not a local
   plasticity rule, and GPT itself calls its hippocampus link an interpretation.

**Protocol risk (shown from the xfer-1 records).** The best small loop solved 0.5-1.5% of 9x9 mazes after 1,000
examples (artifacts/claude-xfer1-20260927/RESULTS.md). At GPT's support sizes of 1-64 examples, every arm is
likely near 0. The registered negative result ("F_relation <= F_loop in both seeds") could then trigger on a 0-vs-0
tie. Ben's extended ladder (up to 64k examples) avoids most of this. The sealed marks should still say how ties
count; they were not on main to check.

## 4. Verdict of the review
- **Race it?** Yes, as GPT specified it, since it is built, sized and checked. Expect a loss on mazes if point 1
  is right (suggested). Mark the cost: a race will take roughly 3-4x the loop's CPU time at 9x9/11x11.
- **Single next test:** the practice gate, which is also a race gate. Train the relation net on sums and grids
  with the loop's exact recipe (6,000 batches of 64), about 1-2 CPU hours (estimate, untested).
  Pass marks fixed now:
  - it reaches 95% (190 of 200) on fresh 4-digit sums and on fresh 5x5 grids;
  - it is within 3 points of the loop on each.
  Proved wrong if it stays below 95% on either after the full recipe with a 3-point learning-rate sweep (5e-4,
  1e-3, 2e-3).
- **If it later loses the race**, the one follow-up change is a triangle term in the r_ij update. Nothing else
  changes.

## 5. Blind recount (shown)
A separate agent recomputed the key numbers from checks.json, smoke-relnet.log, smoke-loop.json and the xfer-1
RESULTS.md, without reading this file. Every number matched:
- both weight totals and the -0.155%, with the table rows summing to the totals;
- 0 of 19 matrices without a gradient;
- all six cost ratios;
- the smoke losses, 0-of-100 scores and the 2.4x time ratio;
- both pieces of triangle arithmetic;
- the xfer-1 maze fractions (0.015 and 0.005).

It flagged two things:
- **The 1,024-weight gap between the two loops.** Explained above: the kind embedding.
- **The traceback in smoke-relnet.log.** It read this as the relation net crashing. In fact the crash is the loop
  arm starting after the relation-net arm had finished, as noted at the top.
