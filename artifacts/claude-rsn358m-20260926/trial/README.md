# Maze trial (unregistered, CPU, small ~1.6M nets, half-narrow "mixed" heads, 1 seed; written 2026-09-26 15:00 UTC)

Question: can small nets learn perfect mazes (practice sizes 5 and 7) in a short budget? Not a test of anything;
fresh mazes from trial seeds, not the 358m test files. Solved out of 200 at step 2,000:

| arm | loss | maze7 | maze9 | maze11 |
|---|---|---|---|---|
| plain (8 layers) | 0.0001 | 200 | 34 | 0 |
| loop (rounds 8 / 16 / 32) | 0.46 | 102 / 108 / 108 | 16 / 22 / 25 | 0 / 2 / 2 |

Read: at this budget plain fits the practice sizes fully and the loop is still underfit (it learned more slowly in
every earlier trial too). More rounds help the loop a little at 9x9. Neither transfers to 11x11. This lowers my
expectation for 358m; it does not decide it. 358m runs only if EXIT-RULE.md's "in between" case is hit.
