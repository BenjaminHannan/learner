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

## Results (unregistered; small nets, 4,000 CPU steps, 200 fresh puzzles each; loop at 32 rounds)

| run | sums6 | sums8 | sums10 | sums12 | grids5 | grids6 | grids7 |
|---|---|---|---|---|---|---|---|
| loop base s1 | 104 | 12 | 0 | 0 | 195 | 159 | 106 |
| loop half-narrow s1 | 187 | 159 | 141 | 121 | 200 | 180 | 131 |
| loop fade s1 | 182 | 144 | 123 | 95 | 191 | 102 | 11 |
| plain base s1 | 170 | 81 | 25 | 16 | 137 | 92 | 45 |
| plain half-narrow s1 | 161 | 120 | 97 | 78 | 147 | 96 | 45 |
| plain fade s1 | 176 | 125 | 101 | 77 | 138 | 91 | 27 |
| loop base s2 | 156 | 66 | 24 | 9 | 195 | 155 | 85 |
| loop half-narrow s2 | 192 | 168 | 150 | 117 | 175 | 115 | 56 |
| plain base s2 | 150 | 58 | 14 | 15 | 139 | 94 | 44 |
| plain half-narrow s2 | 165 | 122 | 101 | 75 | 133 | 95 | 44 |

Seed 2 (landed after 358i was sealed) confirms the sums fix (loop half-narrow minus plain half-narrow: +27/+46/+49/+42
at 6/8/10/12 digits) but shows a grids risk: the half-narrow loop fell BELOW the unchanged loop on grids (grids6 115 vs
155, grids7 56 vs 85; over plain half-narrow only +20/+12). Seed 1 had it the other way (180 vs 159). So for 358i's
G1, grids6 is less safe than the sealed prediction said. Nothing here changes the sealed run.
