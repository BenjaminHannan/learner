# rsn-358d pass marks (fixed before any run; 2026-09-26 03:45 UTC, sleep research thread; written AFTER 358a's FAIL)

Question (unchanged from 358a): does the loop (thinks in rounds, learned stop) solve BIGGER puzzles than it practised
better than its plain same-size twin?
ONE change vs 358a v2: 4-number practice puzzles = every 4-number hand except the 300 held-out test hands, with every
whole target 1-99 it can reach (75,972 puzzles over 1,520 hands, of which the old 1,062 target-24 puzzles are a
subset), instead of only the 1,062 target-24 puzzles. Code: scripts/claude_rsn358d_run.py. Why: in 358a both arms
solved 100% of practice number puzzles and 0-5 of 300 new ones (memorised; blind recount VERIFY.md), so numbers
counted for nothing and G1 needed both sums6 and grids6 at +30.
Nets, other data, steps (60,000), batch (256), lr, stop rule (v2), tests (artifacts/claude-rsn358a-20260925/tests/,
the same sealed files, run once per new checkpoint) are unchanged. Fresh seeds 3 and 4, both arms retrained.

Marks: exactly G0, G1, G2, G3 and the proved-wrong clause of artifacts/claude-rsn358a-20260925/PASSMARKS-v2.md.
**PASS = G0, G1, G2 and G3 on both seeds.** Anything else with G0 met on both seeds = FAIL.
Report only (not graded): numbers4 and numbers5 right for both arms (did the change stop the memorising?); training
exact_by_kind; loop right at fixed rounds; everything 358a reported.

Prediction, before running: numbers4 rises above 358a's 0-5 for both arms (maybe tens), numbers5 stays low; G1
still hinges on sums6, where the plain net swung 197-255 across 358a's seeds. PASS maybe 20%.
Honest limits: this change was chosen after seeing 358a's test counts (only counts; no item was read). The tests are
the same sealed files 358a used (new checkpoints, one run each). Same-weights, not same-compute, as in 358a.
