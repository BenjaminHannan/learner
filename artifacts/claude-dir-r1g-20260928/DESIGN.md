# R1g: a general reach channel for the looped reasoner

Helper R1G, 2026-09-28. Rebuilds design R1 of `artifacts/claude-dir-h9-novelty-20260928/REPORT.md` after the check in
`artifacts/claude-dir-h11-check-20260928/CHECK.md` (on branch claude/h11-check-h9-baw7nd) found its start-like and goal-like features
"a route-finder's vocabulary" (CHECK section 7 and 8). Ben rejects maze-shaped designs. Labels: *shown* = a file or a run here says so;
*suggested* = my reasoning; *untested* = no run.

## What changed from R1, in plain words
| R1 as written (H9) | R1g (this design) | why |
|---|---|---|
| one "start-like" score and one "goal-like" score per cell | **four learned, unnamed probes** per item; each gives a "reached from this subset" number and a "reaches this subset" number | a probe is just a learned subset of items; nothing says start or goal, and a task with no start or goal simply learns other subsets |
| feature "lies between" = start reach x goal reach | dropped; the next round's MLP can multiply any two features if a task wants it | that product only means something for route-finding |
| feature "total reach" S.1 | replaced by "routes that lead back to this item" (S_ii - 1) | shown by the smoke test: because each link row sums to 1, S.1 is the same number for every item (feature std 0.0 after 60 practice steps), so it carried nothing |
| 81-entry offset table | the loop's own row and column offsets (9 + 9 entries), the same form its attention blocks use | the channel gets exactly the position input the loop already has, no new grid table |
| 6,485 extra weights | 8,472 extra weights | probes and a wider mix layer |
| gamma and biases under weight decay | gamma, link bias and probe bias exempt from weight decay (two AdamW groups, the H3 v2 fix) | decay 0.1 over the practice schedule would pull gamma from 0.95 toward 0.84 with no gradient asking for it (arithmetic of H3 ADDENDUM-1 (d)) |

## The mechanism (one change, in `Net.step`)
Each round, after the two shared blocks: (1) a learned "which item leads to which item" table P (row-softmax of a rank-8 query-key score plus the
loop's row and column offsets); (2) M = gamma P, gamma starting at 0.95; (3) S = all routes of 0 to 63 steps, computed exactly by 5 squarings
(prod of I + M^(2^j)); (4) four learned item subsets a_k; (5) ten numbers per item: reached-from-subset k (x4), reaches-subset k (x4), routes back to
itself, share of all flow into it; all scaled into [0, 1]; (6) one linear layer, zero-initialised, adds them to the state. The learned stop, the
48-round cap, the input re-added every round and the two shared blocks are the loop's own.

Why it might help few-example learning (*suggested*, *untested*): a task whose answer follows a chain of pairwise links needs the loop to grow
that chain a hop at a time; the channel does 63 hops in one round, leaving only the link table and the subsets to be learned from k examples.
Carry chains in sums are the same kind of relation, so practice on sums and grids may already train the channel.

Brain link (goals page: ask how the brain does it): the hippocampal successor representation, a discounted sum of powers of a learned
transition table (Stachenfeld et al. 2017; H11 found the page is a paywalled preview that says only "predictive representation", so the discounted-sum sentence is general knowledge, not verified from the page). Where silicon does better:
the sum is computed exactly, not sampled.

## Why this is general (and what is not shown)
*Shown by the CPU self-test* (`artifacts/claude-dir-r1g-20260928/selftest-cloud.json`, torch 2.14 CPU):
- `no_kind_words`: 0 identifiers or strings in the plug-in's code (docstrings removed) contain maze, wall, route, start, goal, grid, puzzle, kind, sudoku, latin or digit; `step` reads only (h, e, dr, dc).
- `equivariance`: renumbering the 81 items (with their offsets) renumbers the ten features and the round output (max difference 2e-6 and 1e-6).
- `set_input`: it runs on 37 unordered items with no positions at all.
- `same_loop`: with the zero-initialised mix the design equals the loop bit for bit over 6 rounds on sums, grids and mazes.
*Not shown*: that it helps on any kind other than mazes. The ruler judges mazes only (PASSMARKS "What this ruler can and cannot say"). Its cost grows with the cube of
the item count: 10 products of T x T per round; T = 81 is about +4% of the blocks' multiply-adds (H9 arithmetic, H11 recomputed 4.17% for the R1 version), T = 900 would be too costly (*suggested*).

## Size (shown, `scripts/claude_dir_r1g_net.py:describe`, asserted in the selftest)
Extra weights 8,472: LayerNorm 512, q and k 4,096, row and column offsets 18, link bias 1, probes 1,024 + 4, gamma 1, mix 2,560 + 256.
Stored 1,654,198 against the loop's 1,645,726: +0.515%. Inside the 1% band (1,629,269 to 1,662,183), so inside the 2% rule. Plain net 1,619,965 (R1g is +2.11% over plain, as the loop is +1.59%).

## Smoke numbers (shown, not scores of the ruler's task)
Cloud CPU self-test, 150 practice steps on sums and grids: loss 4.99 to 2.15, gradient check nonzero on all 20 matrices, checkpoint reload identical,
mean |mix.weight| 0.0092 (the channel is being used from the first steps). Timing at 2 threads: practice step on sums 0.46 s against the loop's 0.35 s,
on grids 0.81 s against 0.71 s, 48-round inference on 32 mazes 2.10 s against 1.95 s. Full-scale run time is untested.

## Risks (*suggested*)
The link table has to learn from k mazes that walls block; the bwd features were nearly flat (std 0.001) after 150 steps, so the probes may need longer to
separate items; practice on sums and grids may leave the channel switched off (the mix-size report catches that); the F_eq +10 bar is a long shot for any
design (the sparse loop was +3.88 and -6.25 against it).
