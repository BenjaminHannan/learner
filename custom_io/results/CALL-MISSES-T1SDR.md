# T1SDR call-accuracy misses (Amendment 8: NOT SHOWN on R4 only, breakdown first)

Read only, CPU fp32, `python3 -m custom_io.diag_call_misses` on the call-accuracy rows of Tool.extra_evals (400 program rows of the big dev
set, 806 gold calls; a call is right when the op and both operand strings are the gold ones). The CPU run reproduces the box: T1SDR_s200
free run 97.89 (17 wrong of 806; the mark 98 allows 16), T1SD_s200 98.26 (14 wrong).

| checkpoint | teacher-forced call acc (wrong) | free-run call acc (wrong) | free-run misses in table_calc |
|---|---|---|---|
| T1SDR_s200 | 98.26 (14) | 97.89 (17) | 12 |
| T1SD_s200 | 98.51 (12) | 98.26 (14) | 9 |
| T1SDR_s201 | 98.76 (10) | 98.51 (12) | 9 |

Shown:
- R4 missed by one call on seed 200 (17 wrong, 16 allowed). The rest of R4 (tool off 0.0) and every other mark pass; answers copy at
  100.0 in every length cell on both seeds.
- 12 of seed 200's 17 missed calls are missed by T1SD_s200 too, and the same 12 by T1SDR_s201: a shared core of hard calls.
- Most misses are table_calc rows where the writer copies the numbers of the WRONG table row (e.g. "Row hammer: qty 9, price 4 ... total
  cost of row hammer?" written as 2 x 3). Both operands come from the prompt; these are lookup misses, not long-number copy misses.
- The 5 calls only T1SDR_s200 misses: 3 table_calc, 2 list_stats.
Suggested, not tested: the drills (which only change result strings) did not cause the shared misses; the 3-call gap to T1SD_s200 is within
run-to-run noise at n = 806.
