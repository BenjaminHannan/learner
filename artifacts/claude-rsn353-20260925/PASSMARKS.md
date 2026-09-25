# rsn-353 pass marks (fixed before any run; 2026-09-25)

One change from 296's loop arm: no step embedding in LoopThinker.forward. Scoring as in 296 (checked
right, 294's sealed scorer; TEST-ONLY panels at category level only).

| mark | what (loop arm, each seed) | pass |
|---|---|---|
| L1 | copy-phase action_ce at the last copy step (train_log) | ≤ 0.05 (296 loop: copy loss 1.85 / 1.97) |
| L2 | fresh panel296 v2 total | ≥ 296 plain same seed − 10 (s1 ≥ 215, s2 ≥ 207); 296 loop got 106 / 101 |
| L3 | invented answers (checked), each panel | ≤ 2 |
| L4 | dev checked right at 6, 12 and 20 passes (report) | does thinking longer help? |

Verdict: **PASS = L1, L2 and L3 on both seeds.**

**Proved wrong (the step embedding is not the full-size cause):** L1 fails on both seeds with
action_ce > 0.5.

Predictions: L1 likely pass (CPU at width 256, 3/3 seeds); L2 uncertain (the practice phase is untested
for the loop); L4 likely flat (nothing in training rewards more passes yet).
