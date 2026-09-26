# rsn-358i small attention trial (unregistered, sleep research thread, 2026-09-26)

Why: Ben's Mac-probe report (12:26 UTC) showed wide sums fail because 358a's attention only tells columns apart up
to 4 away (`scripts/claude_rsn358a_run.py:39`, `:90-91`). Its narrow-window fix was tried on sums only; grids need
each cell to see its whole row. Ben chose (12:28) to test an attention fix next, together with the 358g grid legend
fix, with 4 seeds per net.

This folder holds the small CPU trial used to pick the design before anything is sealed: `attn_trial.py`
(plain d128x8 vs loop d256x2, ~1.6M weights; practice sums 1-4 digits + 4x4/5x5 grids with the legend; designs
base / mixed (half the heads see only columns within 1) / fade (fixed per-head distance penalty); fresh test
puzzles from seed 77000, never the sealed test files). It is not a registered test and decides nothing on its own.
Results will be added here when the runs finish.
