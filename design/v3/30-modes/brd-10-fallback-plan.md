# Problem 7 (lucky hits into lasting skill): what runs after brd-8 and brd-9

Creative research thread, 2026-09-26 ~14:40 UTC. Written while brd-8 runs, so each result is followed at once by the
next step (Ben's 14:03 rule). A plan, not a registration: brd-10 is sealed only when brd-9's verdict is in.

## Order
1. brd-8 (running on a rental): does night 2 compound when the slept model collects the hits?
2. brd-9 (sealed, held in handoff/held/rent-brd9.md): three nights in a row vs no sleep. PASS bar = a fifth of the
   puzzles the base model cannot reach, in every seed (+24 of 240 kept as the reported G7 line); panel leans to
   four-number puzzles, where the room is. Released when brd-8's result is verified, unless brd-8 is INCONCLUSIVE.
3. Then, by brd-9's verdict:
   - PASS: replicate on a fresh panel in a WIDER puzzle world (below), same recipe, same marks. Problem 7 counts as
     solved only after the replication passes too.
   - NOT SHOWN or proved wrong: brd-10 below.

## The puzzle world has run out
Three-number puzzles use numbers 1-9 and targets 5-40, and only 1,346 of them are solvable. Practice, the DEV set and
the brd-5..9 panels leave only 86. Every later test (the replication or brd-10) needs a wider world, for example
three numbers from 1-13 with targets 5-60, plus four numbers (1-13) with target 24, which still has hundreds unused. The first job of
either next step is to measure plain MiniCPM5-1B's cov@1 and cov@30 on the new world on DEV puzzles only, to check
there is room left. Bars stay headroom bars (a share of the puzzles the base model misses), as in brd-9.

## brd-10 (fallback if three nights do not clear the bar): several different answers per won puzzle
Why: the pass measure (cov@30) counts puzzles where ANY of 30 samples is right, so it rewards a model that tries
varied answers. Today each won puzzle teaches exactly one answer (the first hit). Repeats of a few answers
collapse coverage (C and N in brd-5), and more puzzles past about 200 add nothing (brd-6). The untested direction is
more different answers per puzzle.
- ONE change: K3 = for each won puzzle, up to 3 distinct correct expressions from its 30 blurts; W = the first hit
  only (today's recipe). Greedy-correct puzzles give their greedy answer in both arms.
- Equal exposure, as brd-6 and brd-8 did (claude_brd6.matched to the same number of example passes).
- One night, 3 seeds, fresh panel in the wider world, 30 samples per test puzzle.
- Draft marks: PASS = K3 ≥ W + 12 in every seed and the 95% interval above 0; a headroom line as in brd-9; proved
  wrong = upper bound of K3 − W below +2.5 points.
- If K3 passes, the next step folds it into the nightly loop (brd-9's recipe with K3 hits) as its own test.
