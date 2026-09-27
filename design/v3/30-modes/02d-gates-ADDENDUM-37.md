# 0.2d gates, ADDENDUM-37: the sleep-frame line may be written by GPT-6 Luna. Written 2026-09-27 05:23 UTC, before any run

Month-end. Additive only; ADDENDUM-30 is not edited. No 0.2d code is sealed and nothing has run.

- What changes: ADDENDUM-30 sends 0.2d's one data step, the sleep-frame line (ADDENDUM-19, -28 item 4), to GLM through
  the Director's opencode helper. The GLM route is stalled (opencode Go limit spent 09-27). Ben allowed GPT-6 Luna to
  write training data for new experiments at 03:47 UTC and widened it at 03:47:41 UTC ("just have luna rewrite all the
  training data"; design/v3/30-modes/ben-goals-2026-09-26.md:110-115, commit cd475e141). 0.2d is not sealed, so it
  counts as new.
- Rule from now on: if the H-B recipe that passes already carries a frame line, that line is reused and no call is made
  (as ADDENDUM-30). Otherwise the line is written by GPT-6 Luna through scripts/claude_luna_codex.py (Luna as a text
  helper only, never as a builder; the Director's check refused Luna builders at 03:53 UTC). GLM stays allowed if its
  route works again first. The writer is recorded in the sleep run's result file.
- Before the line is used: a small Luna pilot through the same checks the frame line already has (the code check of
  every puzzle it wraps and the DEV sleep run, D0.6). No mark changes. Claude never writes or judges the line.
- Not decided here: the H-B recipe itself (dl-9, dl-8 still open), and every other 0.2d slot.
