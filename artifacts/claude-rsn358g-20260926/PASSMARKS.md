# rsn-358g pass marks (fixed before any run; sleep research thread, 2026-09-26 ~12:10 UTC, after 358a's FAIL)

Question (unchanged from 358a): does the loop (thinks in rounds, learned stop) solve BIGGER puzzles than it practised
better than its plain same-size twin?
ONE change vs 358a v2: a data fix to the Latin grids. 358a's grids sometimes blanked every copy of a symbol, so the
required answer was not determined by the input (fresh 300 per size: 67 at 4x4, 45 at 5x5, 21 at 6x6, 12 at 7x7;
found by an outside review, confirmed in code). Each grid now carries, under a blank separator row, a legend row of
its s symbol names (random order, given). Code: scripts/claude_rsn358g_run.py (`audit`: 300/300 grids per size show
every needed symbol). Answer cells, checker, sums, number puzzles, nets, steps (60,000), batch (256), lr, stop rule
(v2) are unchanged. Seeds 1 and 2, both arms retrained (the legend shuffle draws from the same random stream, so the
practice stream is not batch-for-batch 358a's).
Tests: artifacts/claude-rsn358g-20260926/tests/ (made by code, sealed here, 300 each, run once per checkpoint). Sums
and numbers files are byte-identical to 358a's; grids are fresh fixed grids from the same seeds.

Marks: exactly G0, G1, G2, G3 and the proved-wrong clause of artifacts/claude-rsn358a-20260925/PASSMARKS-v2.md.
**PASS = G0, G1, G2 and G3 on both seeds.** Anything else with G0 met on both seeds = FAIL.
Report only: every test for both arms vs 358a; loop right at fixed rounds; training exact_by_kind.

Prediction before running: grids5/6/7 rise for both arms; the loop keeps a large grids6 lead. Sums and numbers are
unchanged in design, so G1 still hinges on sums6 (358a: loop 256/244, plain 197/255) and numbers stay ~0.
PASS maybe 30%. This fixes a known data fault; the carry-training and number-puzzle changes come after, one at a time.
