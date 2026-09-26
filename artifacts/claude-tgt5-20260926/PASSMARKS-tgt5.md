# tgt-5: does sleep make the model match an answer to its own target? (registered 2026-09-26 ~01:20 UTC, before any run)

Source: experiment A of GPT-6 Pro's answer to reviews/gpt6pro-creative-problems-2026-09-26.md (the claim check is
in reviews/gpt6pro-creative-problems-2026-09-26-CHECK.md). Pass marks are the reviewer's, adopted unchanged.
Why: sleeping on correct answers to newly won puzzles widens coverage (blurt-3, 3r, 5s), but nothing so far shows
whether sleep taught which answers fit which TARGET, or only broadened which expressions the model likes.

Procedure: scripts/claude_tgt5.py (docstring). No sampling on the measure. For each of 120 pairs (2 per hand, 60
fresh 3-number hands, seed 795; no pair uses a practice or DEV puzzle): targets g ≠ h the hand can make, and correct
answers a (makes g) and b (makes h) of equal tokenizer length (a does not make h, b does not make g).
  D = log P(a|g) + log P(b|h) − log P(a|h) − log P(b|g)
Here log P covers the answer tokens plus end-of-answer, each renormalised over the tokens the rule keeper allows.
The raw version is reported too. Models: the frozen base, and W trained inside the run by the blurt-5s recipe
(practice seed 9, 400 puzzles, DEV temperature rule 1.0 vs 1.5, 30 blurts, first hit per won puzzle, LoRA r16,
3 epochs, seeds 0/1/2). E and C (blurt-5s arms) are trained and scored too, as secondary descriptions only.
One GPU run on a rental. That run is the registered result.

Marks (masked D; the one-sided bounds are 98.33% (the reviewer's multiplicity-adjusted level), from a bootstrap over hands):
- PASS = W has D > 0 on at least 84/120 pairs in EACH of its three seeds, AND the mean of (W's D averaged over
  seeds − base D) is at least 0.20 nats with a lower bound above 0.
- Proved wrong ("sleep did not improve target matching"): the upper bound of that mean is at or below 0.
- Otherwise: NOT SHOWN.
- Inconclusive: fewer than 20 won practice puzzles, or fewer than 10 own greedy-correct answers.
Reported: base, W, E and C counts and mean D (masked and raw), and practice counts.
Interpretation limit (reviewer): a pass shows better target matching, not a new arithmetic procedure.
Smoke (before registering; seed 1, 4 pairs that are not in the panel; base only): the code runs, D is finite, and the
bootstrap works.
