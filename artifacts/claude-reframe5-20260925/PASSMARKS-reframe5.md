# reframe-5: restate the puzzle, solve the easier piece, carry it back (registered 2026-09-25 ~18:15 UTC, before any run)

Why: Ben liked "reframing" (17:00 UTC) and the top three parts from the discoveries study (17:47 UTC). Working
backwards ("24 = 4 x 6, so make 6 from the rest") is the puzzle version of changing how the problem is seen.

Procedure (scripts/claude_reframe5.py, docstring):
- Base MiniCPM5-1B, no training. The measure is at test time only.
- 80 fresh test puzzles (seed 784, blurt-1 DEV puzzles dropped), the blurt-1 recipe (two thirds 3-number, one third
  4-number with target 24).
- Each puzzle gets the same budget of 30 model samples at T 1.5, with the rule keeper on:
  - plain = 30 blurts on the puzzle itself;
  - reframe = the 30 blurts spread over code-written sub-puzzles, each dropping one number x (T−x, T+x, x−T, T/x,
    T·x, x/T; whole-number targets 1-200). Sub-puzzle hits are joined back by code and checked on the ORIGINAL puzzle.
- Honest labelling: code writes the restatements and joins the pieces, and the model does every guess. So this tests
  whether spending guesses on restated, easier pieces beats guessing the whole answer. It does NOT test whether the
  model can invent restatements itself; that is a later step.
- One CPU run on the thread container ($0), after ask-24 finishes. That run is the registered result.

Marks (puzzles solved = at least one checked full answer):
- R1: reframe solves ≥ 1.5 × as many puzzles as plain.
- R2: on the 4-number puzzles, reframe solves ≥ as many as plain.
- PASS = R1 and R2.
- Proved wrong: reframe solves ≤ plain overall.
- Inconclusive: plain solves fewer than 10.
- Expectation, stated before the run: R1 is likely, because 2-number pieces are easy. R2 is the informative part.
- Reported: hits, sub-puzzle hits, samples used, and 3-number vs 4-number splits.
- If PASS, the next step is to sleep on carried-back hits and check whether plain guessing gets luckier.
