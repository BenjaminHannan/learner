# 384b: go back to an earlier thought and try another way (thought-memory thread, 2026-09-25 ~20:05 UTC)

Ben, 19:28 UTC (project chat), right after "what if we gave the model a memory for its thoughts that it could recall?":
"so that if it doesn't like where it is right now in its internal representation, it can revert to an old one with the
old thread as an input, and go a different direction".

This replaces the first reading in 384 (a diary of past attempts across problems). 384 stays as a later idea.

## The idea in three parts
1. **Snapshots.** While the model thinks, keep its internal state after each step or round.
2. **A "don't like where I am" signal.** Something that says the current path is a dead end.
3. **Revert with the old thread as input.** Go back to an earlier snapshot, give the model the abandoned path
   ("from here I tried X and it went nowhere"), and let it go a different direction.

For a transformer like the 1B, going back to an earlier point in its thinking is exactly reverting its internal state
(its cache at that point), so a step-by-step version on the 1B is a faithful test. For the small loop reasoner that
Sleep research is building (358: thinks in rounds, learned stop), the snapshot is the latent state after each round,
and the abandoned path goes in as an extra input.

## What the research says (labels: shown = measured in the cited work; suggested; untested = ours)
Abstracts checked on arXiv 2026-09-25; Self-Backtracking's table read in full.
| work | what it does | result |
|---|---|---|
| Tree of Thoughts, 2305.10601 | explores steps as a tree, judges them, backtracks | shown: GPT-4 Game of 24 from 4% to 74% |
| Thought Rollback, 2412.19707 | rolls back to the mistaken step and puts the failed try in the prompt (Ben's "old thread as input") | shown: GPT-4 +9% on MATH over the previous best |
| Self-Backtracking, 2502.04404 | trains the model to emit a backtrack token and return to the last step | shown: Llama3.2-1B on Countdown (a 24-like game) 28.9% -> 67-74%, vs 41% for best-of-8 |
| Stream of Search, 2404.03683 | trains a small model from scratch on search traces that include dead ends and backtracks | shown: +25% over training on perfect paths only, Countdown |
| To Backtrack or Not, 2504.07052 | same compute: backtracking in one long try vs many separate tries | shown: backtracking LOST on Countdown and WON on Sudoku; it gained most once trained with RL |
| Coconut, 2412.06769 | thinks in hidden states instead of words | shown: one hidden "thought" can hold several next steps at once, like a breadth-first search |

Suggested reading: backtracking with the failed path as input helps, including at 1B size, but on number puzzles
many independent tries (what our guesser already does) can be just as good for the same cost. So the test must
compare against separate tries at equal budget, not against a single try. I did not find work that snapshots a loop
reasoner's hidden state and reverts it with the failed branch as input (quick search only); that part is untested.

Brain side (suggested, textbook, not checked today): rats pausing at a maze fork replay each option in the hippocampus
before choosing ("vicarious trial and error"), and the anterior cingulate cortex signals "this is going wrong".

## The "don't like where I am" signal
Creative's test 3 (in its queue) is a small judge on the 1B's hidden states that tells dead ends from still-solvable
states. That is this signal, learned. Until it passes, the first test gives every arm the same exact dead-end check
by code, so the only difference between arms is what happens after a dead end.

## First test, rv-385 (proposed, $0, CPU, test time only, not sealed)
Model: plain MiniCPM5-1B, step-by-step on number puzzles ("a op b = c", then the numbers left). Every arm gets the same
budget of model steps per puzzle and the same dead-end check.
- RESTART: after a dead end, start a fresh try from the beginning (many separate tries, as today).
- REVERT: after a dead end, go back to the last state that was still solvable and pick a different step there.
- REVERT+NOTE: the same, plus the abandoned steps from that point shown as "tried here: X, dead end" (Ben's "old
  thread as an input").
Budget: chosen on practice puzzles so RESTART solves about a third to a half, then fixed before the test.
Measure: fresh puzzles solved within the budget; 80 fresh puzzles with 5 numbers (4-number 24 hands may be too easy with
a dead-end check); 2 seeds; puzzle is the unit.
Proposed marks, fixed before any run: PASS if REVERT+NOTE solves at least 6 more puzzles than RESTART and more than
REVERT, in both seeds. Proved wrong: REVERT+NOTE no better than RESTART in both seeds. Prediction: REVERT beats
RESTART (it wastes fewer steps); whether the note helps a 1B is open.
Next single changes, one at a time: the learned judge (Creative's test 3) replaces the code check; then the loop
reasoner version inside 358 with hidden-state snapshots (Sleep research owns that model); then training on its own
revert traces (Stream of Search, Self-Backtracking) through sleep.

## Plain summary for Ben
Your idea is close to "backtracking", and it has good evidence: a 1B model trained to back up one step on a 24-like
puzzle went from 29% to about 70%. One study found that on number puzzles, simply taking many separate fresh tries
works as well for the same effort, so the fair test is "go back one step and remember the dead end" against "start
over", with the same budget. That test costs nothing and runs on the CPU. The version inside the new small reasoner's
hidden state is new as far as I found, and comes after its first test works.
