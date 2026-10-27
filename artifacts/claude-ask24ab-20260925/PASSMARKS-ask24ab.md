# ask-24ab: is "none on everything" an answer-format problem? (registered 2026-09-25 ~20:00 UTC, before the run)

Source: experiment 2 of the GPT-6 Pro review Ben relayed at 19:13 UTC. Pass marks are the reviewer's, unchanged.
Why: offered "an expression, or the word none", the base 1B said none on 20/20 impossible AND 20/20 solvable DEV
puzzles (ask-24 DEV). Hypothesis (untested): the frozen model can partly tell solvable from impossible hands, and the
expression-or-none format hides it.

Procedure: scripts/claude_ask24ab.py (docstring). Model frozen: no training, no examples, no reasoning asked for.
- original: ask-24's prompt and decoder, greedy; "impossible" iff the answer is none.
- AB1: one-letter answer, A = "yes, it can be done", B = "no, it cannot be done"; the decision is whichever letter
  the model scores higher as its next token.
- AB2: the same with the meanings swapped.
- Panel: 120 impossible + 120 solvable four-card hands (1-13, target 24) as 120 matched pairs differing in one card,
  seed 790, labels proved by exhaustive search (selftest checks all of this). The panel was not looked at before the
  run; the smoke test used seed 1 (3 pairs; there the A/B model said "yes" on all 6 hands under both mappings).
- One CPU run in this container. That run is the registered result.

Marks (scored on meaning, not the letter):
- PASS = under BOTH AB1 and AB2: at least 84/120 impossible hands called impossible, AND at most 36/120 solvable
  hands called impossible, AND balanced accuracy at least 20 points above the original format's; AND AB1 and AB2
  disagree on at most 12 of the 240 hands.
- Proved wrong (for this format change): balanced accuracy 55% or less under BOTH mappings.
- Otherwise: NOT SHOWN (reported with counts).
- Reported too: letter probability mass, how often the top token is a letter, how often A was chosen, pairs where
  both twins were called right, and the original format's correct expressions on solvable hands.
Interpretation limit (reviewer): telling solvable from impossible is not the same as finding the expression.
