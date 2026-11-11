# DRYRUN at 9a3579adc (after the Q26 review fixes, items 1-3 and 7-8), 2026-10-18

**A DRY RUN: tiny preset (d = 32), tiny visits (60 train / 24 validation), CPU, T = 30 s. Every number and verdict is
meaningless and nothing was tuned on it.** It proves only that the box script runs end to end at this commit and that the
readout computes every mark.

`DRYRUN=1 PIN=9a3579adc… WORKERS=3 OUT=…/dryrun-9a3579a bash scripts/premonition_swarm_box.sh`. The tiny data cache was
deleted first, so the data step is a fresh build.

- Exit 0 after 927 s; 33 steps, all rc 0 (`steps.tsv`). HEAD == PIN, and all 18 files of the manifest check OK.
- C0: T overridden to 30 s; ratio S0m4/D1 = 1.03; stop_and_ask False; money_stop False.
- Every mark of both cards is COMPUTED (MARKS-S0: M1-M6 + KILL; MARKS-S1: M1-M6, M6b + KILL-COMM).
- All four verdicts are **VOID (seconds)**: train-D1-s0 ran 30.60 s, +2.01% over T = 30. The M5 guard fired correctly. On
  CPU one tiny step is about 0.3-0.6 s, while ±2% of 30 s is only 0.6 s, so one step of overshoot trips it. On the box,
  T ≥ 300 s gives ±6 s or more, which no single step can exceed. Because of the VOID, this dry run does not exercise the
  verdict branches past VOID. The unit tests cover them, and the earlier dry run (`../dryrun/`) reached KILL with
  `--min-items 1`. **Next CPU dry run: use T = 120 s** (`--t-override 120`) so the full verdict path runs too.
- Train seconds per run: 30.09-30.60 s. Every run stopped on "seconds budget".
