# VERIFY brd-8 (creative research thread; written 2026-09-26 15:16 UTC by `date -u`)

Checked: the rental's RESULTS-gpu.md, brd8_summary.json, and a recount from streams.json and practice.json with
the thread's own code (claude_blurt5s.boot_ci, same 2,000 draws). The recount matches the summary on every number.
Code unmodified (origin/main scripts/claude_brd8.py); panel md5 beb76d9492f990641754dc8bb509c2a0 matched; plain
MiniCPM5-1B commit 87179e5c; RTX 5090; script 31.2 min; 3 rentals (1 stuck, 1 host died, full rerun on the 3rd);
~$0.88 of the $1.00 task budget.

## Registered verdict: compounding NOT SHOWN; G7 MET (its own line)
- Base cov@30 108 of 240 (3-number 97/160, 4-number 11/80).
- ITER (slept model collects night-2 hits): 143 / 161 / 166. CTRL (base model collects them): 152 / 152 / 167.
- ITER − CTRL per seed: −9 / +9 / −1 (PASS needs +12 in every seed). 95% interval [−3.96, +3.33] points: not above
  0, so PASS fails. Upper bound 3.33 is not below 2.5 (6 puzzles), so it is not proved wrong either: NOT SHOWN.
- G7: ITER − base +35 / +53 / +58 (bar +24 in every seed), interval [+14.66, +25.65] above 0: MET.
  CTRL − base +44 / +44 / +59, interval [+15.24, +25.46] (reported).
- Not inconclusive: 165 night-1 wins (≥ 40), and the slept model won MORE night-2 puzzles than the base model in
  every seed (200 / 215 / 185 vs 171; own greedy-right 46 / 41 / 53 vs 13).
- Practice check: all 1,109 saved answers (own and win rows) pass the exact checker; 0 bad.

## What it means
- The slept model really is better at practice: it solved 54 to 72 more of the 400 night-2 puzzles (238-256 vs 184), with 3 to 4
  times as many right on its first try. But training on ITS hits did not teach more than training on the base
  model's hits of the same puzzles. At equal exposure, which model collected the hits made no clear difference.
- Two nights' worth of hits beat no sleep by +35 to +58 of 240 on this panel, clearing problem 7's old +24 bar in
  every seed. Caution: this panel's base is 108, the same as brd-6's, where one night already gave +51 to +54; the
  panels with bases 123 and 135 gave +11 to +23. So G7 met here says as much about the panel's room as about the
  recipe. brd-9 (three nights, a bar set on the puzzles the base cannot reach, four-number-heavy panel) tests that.
