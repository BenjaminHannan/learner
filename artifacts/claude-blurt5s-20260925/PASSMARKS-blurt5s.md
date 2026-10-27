# blurt-5s: own lucky hits vs exact-solver answers (registered 2026-09-25 ~19:45 UTC, before any run)

Source: experiment 1 of the GPT-6 Pro review Ben relayed at 19:13 UTC (prompt:
reviews/gpt6pro-creative-mind-brainstorm-2026-09-25.md). The pass marks below are the reviewer's, adopted unchanged
except where a note says so. Ben 19:13: "you can use vast btw".

Why: blurt-3 and blurt-3r (both PASS, replicated) showed that sleeping on the 1B's own checked lucky hits (W) about
doubles lucky guesses on fresh puzzles, while sleeping on repeated known answers (C) does not. But W also sees correct
answers on more, and harder, puzzles than C. So "self-made hits are special" and "more correct supervision on new
puzzles is enough" are tangled. This test separates them.

Procedure: scripts/claude_blurt5s.py (docstring). ONE change from blurt-3's W: for each newly won practice puzzle the
target is an exact-solver answer (arm E) instead of the model's own first lucky hit. Same prompts, same own
greedy-correct examples, same number of examples, same LoRA recipe (r16, 3 epochs).
- Solver answer rule, fixed now: all expressions the brute-force solver finds, minimal brackets; drop the model's own
  hit (spaces ignored) if another remains; pick the one closest in length to the model's hit; ties alphabetical.
- Arms: W, E, C (own greedy-correct answers repeated to W's size). LoRA seeds 0, 1, 2.
- Practice seed 9 (400 puzzles). Fresh test: seed 785, 240 puzzles (2/3 with 3 numbers, 1/3 with 4 numbers, target
  24), overlap with practice and DEV dropped. DEV temperature rule 1.0 vs 1.5 on the blurt-1 DEV puzzles. 30 samples
  per test puzzle.
- One GPU run on a vast rental. That run is the registered result.

Main measure: coverage = test puzzles with at least one correct sample in 30 (cov@30). Also reported: cov@1, cov@5,
cov@10, lucky samples, mean target length of W and E wins, how many E targets equal the own hit (should be ~0), and
group-resampled 95% intervals (bootstrap over number hands, 2,000 draws).

Let D = 24 if the test set keeps all 240 puzzles, else ceil(n_test / 10).
- S1 (self-made hits are special): W's cov@30 >= E's cov@30 + D in EVERY seed (seed k vs seed k), AND the
  seed-averaged 95% interval for W - E excludes zero.
- PASS = S1.
- Proved wrong ("correct supervision is enough"): E's cov@30 >= base cov@30 + D in every seed, AND the lower 95%
  bound of E - W is above -5 percentage points (that is, the upper bound of W - E is below +5).
- Otherwise: NO DIFFERENCE SHOWN (neither claim holds); reported as such, not as a pass.
- Inconclusive: fewer than 20 won practice puzzles, or fewer than 10 own greedy-correct practice answers.
- Sanity (reported, not a mark): W should beat base as in blurt-3/3r; if W <= base in every seed, say so first.

Note: C is kept to show again that repeated known answers collapse variety; it is not part of S1.
