# 358: the reasoner line stops being about relation facts (sleep research thread, 2026-09-25 19:40 UTC)

Ben, 19:22 UTC (Fix sleep thread, relayed to every thread): relation facts are "genuinely 1% of the work this
model will do ... a foundation", and threads should overlap their functions and work with each other directly.

## Honest look at this line
Everything the learned reasoner has done so far (294-357) is relation lookups over notebook rows: chains,
counts, comparisons, corrections. The 30M net reads anonymous row symbols, not text, so it CANNOT do anything
else as built. Ben is right that this is too narrow: it can at most be the notebook-query part of the brain.

## What changes
- rsn-357r (practise 3-step relation chains, test 4) is HELD before launch ($0). Its question (does the loop
  generalise past practised depth?) is still good, but it will be asked on general puzzles instead.
- The loop reasoner becomes a small TOKEN model that thinks in rounds with a learned stop, trained with
  group-relative RL (MiMo-style mixed environments, as Ben asked on 09-24) on many checkable kinds of problem.
  Relation chains over the notebook are one environment among many, not the target.
- Evidence this can work at small size (to verify before building on it): tiny looped/recursive nets
  trained from scratch on puzzles with halting (Tiny Recursive Model, Hierarchical Reasoning Model) report
  strong Sudoku / maze / ARC-style results at 7-27M parameters. Suggested, from memory; to be checked.

## Environment set (all checked by exact code, generated fresh, so no answer is memorised)
number puzzles (24-game and countdown, shared with the creative thread), multi-digit arithmetic with carries,
Sudoku-style constraint grids, mazes / shortest path, sorting and list ops, boolean logic and small program
tracing, word-free deduction (knights and knaves style), relation chains over a notebook (1 of 9).

## How it will be judged (Ben's rules)
- Held-out kinds and longer sizes than practised (e.g. practise 4x4 grids and 3-digit sums, test 6x6 and 5-digit),
  never the practised items. Thinking longer must help on the bigger ones, and the stop token must pick the length.
- Plain same-size twin with equal tuning; fresh test sets fixed before the recipe is frozen; 2 seeds;
  one change per registered run; a registered FAIL stays FAIL.

## Overlaps with other threads (Ben: functions should partially overlap)
- Creative: its generator's checked "lucky hits" on number puzzles become training episodes for this reasoner
  (the loop Ben described 00:51); both use the same puzzle checkers.
- Fix sleep: practice school draws from these environments as well as taught facts; sleep calls
  scripts/claude_rsn_recipe.py today and will call the token recipe once it exists.
- Benchmarks: picks the public puzzle benchmarks where small models compete (Sudoku-Extreme, mazes, ARC-style)
  so this line is measured against published same-size results, not only our own tests.

## First registered step (next)
358a: the loop token reasoner vs a plain twin on 3 environments first (24-game, arithmetic with carries, 4x4
grids), practise small sizes, test bigger ones; pass marks sealed before any run. Code and marks next.
