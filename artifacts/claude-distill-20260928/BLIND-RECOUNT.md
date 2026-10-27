# Blind recount

Written 2026-09-28 19:36 UTC (`date -u`). A separate subagent was given only `PASSMARKS.md` and the 60 raw
`sleeps/*.json` (it was told not to read summary.json, tables.md, RESULTS.md or the scripts, and did not edit the
repo). Its script was `/tmp/recount.py` (not kept).

Result: **every number and every verdict matches `summary.json`.** Cell means (sums4 / grids5 of 200 / 9x9 of 300),
M1 (sums4 +4.5, grids5 +9.75, both 4 of 4 cells higher, both fail the 20 bar), M1b (sums4 -1.75, grids5 +1.25, fail),
M2 (cell diffs +17.7, -18.0, +7.7, -10.0; fails in two cells), smaller store (D16-R16 sums4 +1.17, grids5 +7.5; D16 within
6 of R128 in 0 of 4 cells on both kinds), verdict "not passed, not proved wrong". All 60 records agree with their
filename on seed, branch, arm, draw, sleep seed (seed + k + {0,101,202}), store size and mode, and all have 512 updates.

Its only flag: the proved-wrong rule needs both kinds under 5 of 200; sums4 is 4.5 (under) and grids5 is 9.75 (not), so it
read the rule strictly and did not call it proved wrong. That is also how `summary.json` reads it. It could not check the
validity clause against `adapt.json` (not allowed by its brief); that check is in RESULTS.md.
