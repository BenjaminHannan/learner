# rsn-358c2 pass marks, DRAFT (fixed 2026-09-26 02:40 UTC; run only if 358c1 shows the stop still loses answers)

ONE change vs 358a v2: the stop head's training label is the real checker's verdict (any valid expression counts for
number puzzles; sums and grids have one answer, so they are unchanged). Code: scripts/claude_rsn358c2_run.py. Loop
arm retrained, seeds 1-2, same steps/data/tests as 358a; the plain arm is 358a's (same code path, seeds and data).
Marks: G0-G3 exactly as artifacts/claude-rsn358a-20260925/PASSMARKS-v2.md, plus
L1: on numbers4/numbers5, loop right with its own stop ≥ loop right at the fixed 16 rounds − 3 (the stop no longer
refuses valid alternative answers). Proved wrong (for this change): L1 fails on both seeds.
Reject this change if the labels are correct (checked in smoke) but the stop's losses on numbers do not shrink.
