# Loop-1L addendum 2 (2026-10-24 ~12:15Z, before any GPU run)
Ben asked how to make the model use all of its loops. Change to arms B and C (A unchanged):
- Training samples the pass count per optimizer step from 1..8, with weight proportional to the count (mean about 5.7). Flag: `--rand-passes 8`.
- The primary M_tool for B and C is measured at 8 passes (the top of the trained range). A pass curve is measured at 1, 4 and 12
  on the first 50 eval chats, so B/C have scores at 1, 4, 8 and 12 passes. 12 is beyond anything seen in training.
- New report (no mark): the curve of M_tool against passes. "Uses its loops" means the curve rises from 1 to 8 and doesn't fall at 12.
- K1/K2 compare B and C at 8 passes with A. The lesion rule ("wrong if" the 1-pass score costs < 1 point) uses the 1-pass score.
Bug fixed before the run: arm A had been set up to train with 4 passes and evaluate with 1. It now never loops.
Box time limit raised to 5 h (about $2.35 on the chosen A100 80 GB at $0.47/h).
