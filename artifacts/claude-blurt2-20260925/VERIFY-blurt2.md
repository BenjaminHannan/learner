# blurt-2 learning loop: overall verdict = registered FAIL (both runs finished; PASS needed both)

Rule (PASSMARKS-blurt2.md, fixed before running): "if both finish, both are reported and PASS needs both."

| run | temp (DEV rule) | wins | S0 | W seeds (mean) | C seeds (mean) | L1 W−S0 ≥ +8 | L2 W−C ≥ +5, each W > each C |
|---|---|---|---|---|---|---|---|
| CPU (thread container) | 1.0 | 173/379 | 6/127 | 15, 19 (17) | 6, 6 (6) | +11 PASS | +11 PASS |
| GPU (BensPC 5070 Ti) | 1.5 | 184/379 | 6/127 | 13, 11 (12) | 5, 6 (5.5) | +6 FAIL | +6.5 PASS |

Verdict: FAIL (L1 missed on the GPU run). Checked against both loop_summary.json files; counts match the builder's
report. The builder's deviations (CRLF puzzle file, content identical; one relaunch) do not change anything.

What is shown (both runs): sleeping on creative wins beats the same amount of practice without them on fresh puzzles
(+11 and +6.5; every W seed above every C seed). Practice without wins never helps (6, 6, 5, 6 vs S0 6).
What failed: the size of the gain. The bar was +8; the GPU run got +6.
Suggested (not shown): the gap between runs may be the temperature (the DEV rule picked 1.5 on the GPU because of a
39-vs-44 coin flip) or just seed noise; four W runs span 11 to 19.
Not yet tested: whether the right answers matter (placebo run blurt-2p, running), transfer to other puzzle kinds.
