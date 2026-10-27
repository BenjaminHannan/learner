# slp-358lp pass marks (fixed before any run; 2026-09-26 03:00 UTC, sleep research thread; Ben's yes 02:06 UTC)

Question: does picking the night's day practice by LEARNING PROGRESS (the candidate batch whose descent direction best
matches the recent weight movement; idea from "Self-Play Pretraining with Zero Data") make the small reasoner better
at bigger unseen puzzles than picking it at random?
Code: scripts/claude_slp358lp_nights.py (docstring has the arms). Base = slp-358n2's sleep night (registered PASS).
Arms: S random (= slp-358n2 sleep), L learning progress (best of K=4 candidates), F flipped (worst of the same 4),
N no night. Seeds 7 and 8 (fresh). Same fixed tests as slp-358n2 (seed 58600). Scores after night 3.

| mark | what (each seed) | pass |
|---|---|---|
| V validity | S − N ≥ +20 on day_grids (400) (sleep itself worked in this run) | else INCONCLUSIVE |
| P1 | transfer_sums8 (200): L − S | ≥ +20 |
| P2 | transfer_grids6 (200): L − S | ≥ +20 |
| P3 | flipped does not match: L − F ≥ +10 on each transfer test | both |
| P4 | harm: L ≥ N − 6 on harm_sums4 and harm_grids4 (300 each) | both |
| report | day_sums, day_grids (L − S, L − F), nights 1-2, candidate picks, minutes | - |

**PASS = V, P1, P2, P3 and P4 on both seeds.** V met on both seeds and anything else = FAIL (stays FAIL).
**Proved wrong** (for this learning-progress pick at this scale): L − S ≤ +5 on both transfer tests, both seeds.

Sanity check of the proposer's marks (coordinator relay 02:06): kept its +20/200 on both bigger tests, harm within 6,
proved-wrong at ≤ +5. Made "the placebo does not match" concrete: the flipped arm (pick the worst score) is the
control, because a shuffled-score pick is a uniformly random candidate, the same as S. Added V so a run where sleep
itself did nothing can't count. Prediction: FAIL likely; the paper's gains were at 1M-25M weights with a trained
writer, here only a pick among 4 random batches. Limits: small nets on CPU, 3 nights, two puzzle kinds; the "recent
movement" includes weight decay; L and F spend 4 extra gradient passes per day step (scoring only, not training).
