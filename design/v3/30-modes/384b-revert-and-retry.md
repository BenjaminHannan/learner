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

## Honest comparison with the alternatives (added ~20:15 UTC after Ben's "don't yes-man me", 19:31 UTC)
Extra papers checked on arXiv today: Huang et al. 2310.01798, Zhang et al. 2404.17140, rStar 2408.06195, DeepSeek-R1
2501.12948; full text of To Backtrack or Not (2504.07052) and TRM (2510.04871).
Where an existing approach beats or matches Ben's idea:
- Many separate fresh tries (what blurt already does). Shown (2504.07052, models of 3M-144M trained from scratch, close to
  our reasoner's size): on Countdown, separate tries beat one backtracking try at equal compute, and the gap widened with
  size; the backtracking model was capped by the search traces it imitated. Backtracking won on Sudoku, and the paper
  ties the difference to search depth. After RL (GRPO) the backtracking model improved and found new strategies.
- Tree search over saved states. Going back to the last good point (depth-first) is the narrowest use of snapshots; with
  a score per state the model can resume the most promising one. Shown (rStar): LLaMA2-7B on GSM8K 12.5% -> 63.9% with
  tree search plus a second model checking. Suggested: best-first over snapshots is at least as flexible as reverting.
- Redrafting the whole answer each round. Shown (TRM): a 5-7M loop model with no backtracking beat the previous best on
  Sudoku-Extreme (55% -> 87%) and Maze-Hard (75% -> 85%). Suggested: in a loop that refines the whole answer, early
  mistakes can be fixed without reverting, so revert helps only if the loop gets stuck.
- Ruling out the failed step. Classic backtracking just never picks the abandoned step again; the model does not read it.
  Suggested (experience-following, 2505.16067): models tend to repeat what they are shown, so the note could steer a
  small model back into the same path. Whether the note beats a plain ban is untested.
- The "don't like where I am" signal. Shown (2310.01798): without outside feedback, models often fail to fix their own
  reasoning and sometimes get worse. Shown (2404.17140): small models self-correct well only with a strong verifier.
  So the idea is only as good as its judge; this is its biggest risk.
Where Ben's idea is better:
- Short working memory. Reasoning models back up in text ("wait, let me try another way", shown to emerge from RL in
  DeepSeek-R1), which keeps every dead end in the context. Small models handle long context badly (Dynamic Cheatsheet
  sec. 4.5, shown for GPT-4o-mini), and a 30-100M loop reasoner has little room. Restoring a saved state plus a short
  note keeps it small. Suggested.
- Cheap: restoring a latent is a copy, not a re-think. Untested whether it pays in accuracy.
- New: I found no work that reverts a loop reasoner's hidden state with the failed branch as input (quick search).

## Correction to rv-385 (supersedes the test above; still not sealed)
Flaw found in my own design: an exact dead-end check on number puzzles does most of the solving (it is a search), so it
would flatter every arm and likely hit the ceiling. Revised:
- Task: 358a-style small Latin-square/Sudoku grids (deeper search, where theory expects backtracking to matter), with
  only the visible rule check (no repeated symbol in a row, column or box). A partial grid can pass that check and still
  be a dead end, found only later; that is where going back matters. Plain MiniCPM5-1B proposes one cell at a time.
- Arms, same step budget and same rule check: RESTART (start over after a conflict); REVERT+BAN (go back to the last
  conflict-free state and rule out the failed step, the model sees nothing); REVERT+NOTE (go back and show the abandoned
  path, no ban; Ben's version). One change between neighbouring arms.
- Marks to fix before any run: PASS if REVERT+NOTE solves at least 6 more grids than RESTART and more than REVERT+BAN,
  both seeds. Proved wrong: REVERT+NOTE no better than REVERT+BAN in both seeds (then the note adds nothing over
  classic backtracking). Budget set on practice grids so RESTART solves a third to a half.
- Later rivals to test in the loop reasoner itself: keep refining (TRM-style) and parallel restarts.

## rv-385 result (22:20 UTC): registered FAIL, proved wrong, blind recount agrees
Plain 1B, 5x5 Latin grids, 60 choices each, 80 fresh grids per seed: restart 0 and 0, revert_ban 46 and 54, revert_note
13 and 14. The 1B picked numbers already noted as failed 58% and 56% of the time vs 37% and 35% for blind guessing: the
note pulled it back to the failed path. First choices were near chance (22-29% vs 20%), so this says nothing about a
skilled or trained model. Design consequence: when the loop reasoner reverts, keep the "not again" list in code on the
saved state; test a note only on a trained model, as one later change. Next: the latent revert wrapper in the 358 loop,
after 358a has a result (agreed with Sleep research).

## Plain summary for Ben
Your idea is a known family (backtracking) with one new part: doing it by restoring the small reasoner's saved inner
state. It is not better everywhere. On shallow number puzzles, many fresh tries do as well; tree search over saved
states and loops that redraft the whole answer are strong rivals; and it only works if the model can tell when it is on
a bad path, which models are often bad at without a checker. Its real advantage is keeping the thinking short, which
matters for a small model. The fair test pits it against starting over and against plain backtracking, on grids.
