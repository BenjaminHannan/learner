# rsn-358a pass marks (fixed before any run; 2026-09-25, sleep research thread)

Question: on puzzles that are not relation facts, does a net that thinks in rounds (loop, with a learned stop)
solve BIGGER puzzles than it practised better than its plain same-size twin? Code: scripts/claude_rsn358a_run.py,
scripts/claude_rsn358a_envs.py. Tests: artifacts/claude-rsn358a-20260925/tests/ (made by code, sealed, 300 each).
Two arms (plain, loop), seeds 1 and 2, same data stream, steps (40,000), batch (256), learning rate and schedule.
Graded by exact code (any valid answer counts). Final checkpoint only; no early stopping; tests run once.

| test | practised? | role |
|---|---|---|
| sums4, grids5, numbers4 (300 held-out hands) | practised size, fresh items | G2 |
| sums6, grids6, numbers5 | bigger than ever practised | G1, G3 |
| sums8, grids7 | even bigger | report only |

| mark | what (each seed) | pass |
|---|---|---|
| G0 validity | both arms right on at least 210/300 (70%) of the practised-size tests in at least 2 of 3 kinds | else the run is INCONCLUSIVE (undertrained), neither PASS nor FAIL |
| G1 | bigger tests: loop − plain | ≥ +30/300 on at least 2 of the 3 bigger tests, and not below −10 on the third |
| G2 | practised-size tests: loop − plain | ≥ −10/300 on each |
| G3 | the stop picks the length | on each bigger test, loop right with its own stop ≥ loop right at a fixed 16 rounds (training maximum) − 5; and mean rounds used on sums6 > mean rounds on sums4 |
| G4 | report | sums8, grids7; loop right at 1/2/4/8/12/16/24/32/48 rounds; right at any round; rounds histograms; training curves |

**PASS = G0, G1, G2 and G3 on both seeds.** Anything else with G0 met on both seeds = FAIL (stays FAIL).

**Proved wrong ("thinking in rounds lets a small net carry a method to bigger puzzles than it practised"):**
G0 met, and loop − plain ≤ +5/300 on all three bigger tests on both seeds.

Predictions (written before any run): plain should fail sums6 badly (fixed depth can't carry 6 columns it never
saw; published transformers usually fail this); loop sums6 uncertain; grids6 uncertain for both; numbers5 likely
low for both (a much bigger search). G1 overall: uncertain, maybe 35%.

Limits known in advance: the loop spends more compute per question than the plain net (that is the thing being
tested: can extra thinking time be turned into bigger puzzles); a plain net given more compute in some other way is
not tested here. Practised-size sums/grids tests are fresh seeds in very large spaces, not proven disjoint from
training draws (numbers4 is proven disjoint).
