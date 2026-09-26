# rsn-358i pass marks (fixed before any run; sleep research thread, 2026-09-26)

Question (unchanged from 358a): does the loop (thinks in rounds, learned stop) solve BIGGER puzzles than it practised
better than its plain same-size twin?

Design change tested (one): in every layer of both nets, half the attention heads (0-3 of 8) see only cells within
1 column; the other half are unchanged (every cell, row/column offset bias clipped at 4). Code:
scripts/claude_rsn358i_run.py (`check-mask`). Why: the offset clip at 4 columns (scripts/claude_rsn358a_run.py:39,
:90-91) makes pages wider than practice collapse (Ben's Mac-probe report, 12:26 UTC, verified in code). Picked in an
unregistered small CPU trial (artifacts/claude-rsn358i-20260926/trial/), so the design was chosen with some knowledge
of fresh (non-test) sums and grids at bigger sizes; the sealed tests below were never used there.
Carried over, not tested here: the 358g grid legend fix (a test-validity repair; 358g never ran), 358a v2's stop
rule, nets' sizes (plain 8 layers x 256, loop 2 layers x 512), data, steps (60,000), batch (256), lr and schedule.

Seeds: 1, 2, 3, 4, both arms (8 trainings). An outside report showed the plain net alone swings 58 on sums6 between
two seeds (358a: 197 vs 255), so two seeds cannot separate a +30 gap from luck.

Tests: artifacts/claude-rsn358i-20260926/tests/ (made by code, sealed, 300 each, run once per checkpoint).
All files present in artifacts/claude-rsn358g-20260926/tests/ are byte-identical to 358g's. Added, report only:
sums10 and sums12 (fresh seeds 35814, 35815).

| test | role |
|---|---|
| sums4, grids5, numbers4 (300 held-out hands) | practised size (G0, G2) |
| sums6, grids6, numbers5 | bigger than practised (G1, G3) |
| sums8, sums10, sums12, grids7 | report only |

| mark | pass |
|---|---|
| G0 validity | on every seed, both arms right on >= 210/300 of the practised-size tests in at least 2 of 3 kinds; else INCONCLUSIVE |
| G1 bigger | mean over the 4 seeds of loop - plain >= +30 on at least 2 of sums6 / grids6 / numbers5 and >= -10 on the third; AND on at least 3 of 4 seeds loop - plain > 0 on each of those (at least 2) tests |
| G2 practised | mean over the 4 seeds of loop - plain >= -10 on each practised-size test |
| G3 stop | on at least 3 of 4 seeds: loop right with its own stop >= loop right at fixed 16 rounds - 5 on each bigger test, and mean rounds on sums6 > on sums4 |
| G4 report | every test per seed and arm; means; loop at fixed rounds; sums8/10/12, grids7; comparison with 358a |

**PASS = G0, G1, G2 and G3.** Anything else with G0 met = FAIL (stays FAIL).
**Proved wrong** (for this design): G0 met, and mean loop - plain <= +5 on all three bigger tests.

Predictions before running: grids6 loop lead large (358a: +67/+76; trial with the legend: +84); sums6 lead positive
but near the bar (small trial: +26 at 6 digits, +39 to +44 at 8-12); numbers5 ~0 for both (memorised; the 24-game
rebuild is a later step). PASS maybe 45%. If sums6 misses, the report-only 8-12 digit sums say whether the gap grows
with size.

Sealed with only seed 1 of the small trial in (loop, half-narrow vs unchanged attention, of 200: sums6 187 vs 104,
sums12 121 vs 0, grids6 180 vs 159, grids7 131 vs 106; plain half-narrow: sums6 161, sums12 78, grids6 96, grids7 45).
Trial seed 2 (base and half-narrow only) was still running; it is reported in trial/ and cannot change this run.
