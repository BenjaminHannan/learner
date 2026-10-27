# Plan: teach the reasoner to doubt its own pencil marks (thought-memory thread; drafted 2026-09-26 22:08 UTC by date -u; a proposal, not sealed, needs Ben's yes)

## Why
- Going back needs a signal that says "that guess was wrong". Four tries found none that beats simply counting guesses.
  - rv-387: the net's "am I done" value never fell.
  - rv-391 dev: none of the net's untrained signals separates wrong guesses from right ones (best AUC 0.53).
  - The critic probe on 358i's nets: PROVED WRONG, 0.776 against counting's 0.777 (14de0f17e).
  - The critic probe on the retrained rsn-358i2 nets: PROVED WRONG, 0.763 against counting's 0.794
    (RESULTS-critic-358i2.md).
- A wrong guess ruins the puzzle. On practice 7x7, 368 of the 720 puzzles 358i's nets failed were ruined by one wrong
  guess (rv-391 dev, 358i's nets; not yet measured on rsn-358i2's).
- Root cause (suggested): the net never trained on a page containing a wrong symbol. Every given in training was
  true, and the worker writes each guess as if it were a given. So the net has learned to trust whatever is written.

## The plain fix (field and brain)
- Field: Stream of Search (arXiv 2404.03683) trains a model on its own search, dead ends and backtracks included,
  instead of only on clean solutions. The model then searches better (the paper's result: +25% on Countdown). Our
  version: train the loop net on pages from its own guessing runs, wrong guesses included, with the true solution as
  the target.
- Brain: people learn from their own errors (error-driven learning). They also keep track of which beliefs they
  guessed and which they were told (source monitoring, a frontal function). Sleep replay includes failed attempts.
  This is textbook-level, and mapping it onto the net is a guess.

## What changes (one change; no new weights)
- A guess becomes a pencil mark. The guessed symbol goes into the answer cell, and the cell stays marked as an answer
  cell (slot 1) instead of turning into a given (slot 0). The net can already tell the two apart, so no new weights
  are needed. In training so far an answer cell always held the blank token (scripts/claude_rsn358a_envs.py:191-192),
  so a symbol in an answer cell is new to the net; teaching it what that means is the point of the fine-tune.
- Fine-tune each rsn-358i2 loop net on a mix of:
  - its usual training data;
  - pages from its own GUESS runs on fresh code-made training puzzles, pencil marks included, some of them wrong.
  The target is the true solution in every answer cell, pencilled ones included. It is a bare target checked by code
  (test-hygiene rule 1). No test or practice puzzle is used in training.
- Machine: BensPC, $0, torch 2.11 with the autocast cache off. Our best guess is 1 to 2 hours for 4 nets.
- Going back then uses the net itself. If its read-out disagrees with a pencil mark, erase the mark and continue.
  There is no separate critic and no hand-set time slice.

## Marks (to be sealed before training; unit = practice 7x7 states from the fine-tuned nets' own guessing runs)
- WORKS if, in at least 3 of 4 nets:
  - the net's top symbol disagrees with at least 60% of WRONG pencil marks and at most 10% of RIGHT ones;
  - and its dead-page AUC (the lowest read-out probability of any pencil mark on the page) beats count-only by at
    least 0.05 on average.
- NO HARM: on 358i's test sets with no pencils (grids6, grids7, sums6), each fine-tuned net stays within 5 of 300 of
  its rsn-358i2 original, on average.
- PROVED WRONG: the nets disagree with fewer than 30% of wrong pencils in at least 3 of 4 nets, OR the AUC is no
  better than count-only.
- If it WORKS and does no harm: registered rv-391, the worker going back when the net overrules a pencil mark,
  against the same worker without going back. Fresh 7x7 test puzzles, marks sealed first.

## Plain words (for Ben)
Right now, when the puzzle solver writes down a guess, it treats the guess like a fact printed in the puzzle and never
questions it. So one bad guess ruins the whole puzzle. The fix: write guesses in pencil. Then practise the solver on
its own old attempts, including the ones where its pencil marks were wrong, and show it the right answer. If it
learns to say "that pencil mark is wrong", it can erase it and try again, the way a person does. It is free
(Ben's PC) and takes about an hour or two of training.

Note added 22:42 UTC by date -u: this proposal became rv-393 (artifacts/claude-rv393-20260926/PLAN.md, with a
no-pencil control arm and sealed marks). "Needs Ben's yes" in the title is withdrawn: the Thread manager noted at
22:29 UTC that a $0 test with no new weights is this thread's call, and Ben's yes is reserved for architecture changes
and money (ben-goals-2026-09-26.md:96). The marks in rv-393's PLAN.md replace the draft marks above.
