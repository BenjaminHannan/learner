# 0.2d gates, ADDENDUM-38: correction to ADDENDUM-37's pilot line. Written 2026-09-27 05:25 UTC, before any run

Month-end. Additive only; ADDENDUM-37 is not edited.

- ADDENDUM-37 says the Luna pilot goes through "the same checks the frame line already has (the code check of every
  puzzle it wraps and the DEV sleep run, D0.6)". That overstates it. The frame is one fixed instruction line
  (ADDENDUM-19, replacing claude_blurt1.puzzle_prompt); no check of the line itself was ever registered. The puzzles it
  wraps are code-made and code-checked, but that checks the puzzles, not the line.
- Corrected pilot: the Luna line is used only after one DEV sleep night with it completes without error (D0.6,
  ADDENDUM-26) and its text is recorded with the writer in the sleep run's result file. No new mark is added.
