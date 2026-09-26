# brd-8: does a second practice round help more when the SLEPT model collects the hits? (registered 2026-09-26 ~13:25 UTC, before any run)

Source: problem 7 (turn lucky hits into lasting skill), still unsolved after brd-7 (NOT SHOWN). Ben 12:59 UTC: work
each unsolved problem, $2 of vast compute per thread. The thread picked this test (its default choice).
Why: one night on the model's own checked hits beat no sleep in brd-5, 6 and 7 (intervals above 0 each time) but
cleared +24 of 240 only once. In Ben's loop, tomorrow's practice is done by the model that slept tonight, so its
lucky hits should reach harder puzzles. brd-6 showed that more puzzles collected by the SAME base model add nothing
at equal exposure. So the open question is whether hits collected by the improved model compound.

Procedure: scripts/claude_brd8.py (docstring).
- Round 1 (shared): the base model practises A = puzzles(9, 800)[:400] (brd-5's set); M1 = LoRA on those examples.
- Round 2, ONE change, which model practises B = puzzles(9, 800)[400:]: ITER = M1 (seed s); CTRL = the base model.
- Each arm trains a fresh LoRA from base on round-1 + its round-2 examples, for EXACTLY 3 x (round-1 + CTRL round-2
  examples) example passes (claude_brd6.matched). So both arms get equal exposure and optimizer steps; only the
  source of the round-2 hits differs. ITER may have more distinct examples, each seen fewer times. brd-6 showed
  that alone does not change coverage.
- Hits: greedy answer when right, else the first of 30 rule-kept blurts at the DEV temperature (1.0 vs 1.5 rule,
  blurt-1 DEV panel); exact checker. LoRA r16, lr 2e-4, batch 8, seeds 0/1/2. 30 samples per test puzzle.
- One GPU run on a rental. That run is the registered result.
Test panel FIXED NOW: artifacts/claude-brd8-20260926/test_puzzles.jsonl (md5 beb76d9492f990641754dc8bb509c2a0):
240 puzzles (160 with 3 numbers, 80 with 4 numbers and target 24; 188 hands), from puzzles(seed 801, 1500). It
excludes all 800 practice puzzles, the DEV panel, and the brd-5, brd-6 and brd-7 test panels.

Measure: cov@30 = test puzzles with at least one correct sample in 30 (= distinct puzzles reached). Intervals: 95%,
bootstrap over number hands (2,000 draws), seed-averaged (claude_blurt5s.boot_ci).
Two claims, both fixed now:
- PASS (compounding): ITER's cov@30 ≥ CTRL's cov@30 + 12 in EVERY seed (seed k vs seed k), AND the 95% interval
  for ITER − CTRL is above 0.
- G7 (problem 7's bar, its own line): ITER's cov@30 ≥ base cov@30 + 24 in EVERY seed, AND the 95% interval for
  ITER − base is above 0. Reported as met or not met. It is a separate claim, not part of PASS.
- Proved wrong (compounding): the upper 95% bound of ITER − CTRL is below +2.5 points (6 puzzles).
- Otherwise: NOT SHOWN.
- Inconclusive: fewer than 40 round-1 wins, or M1 wins fewer B puzzles than the base model in every seed (then the
  slept model did not practise better, and the question was not posed).
Reported, not marks: for base, ITER and CTRL, cov@1, cov@30 split by 3-number and 4-number, lucky samples;
own/win/miss counts per round and arm; the intervals for CTRL − base. practice.json saves every practice outcome.
Limit: ITER's round-2 puzzles are the same B set as CTRL's, so what differs is which of them are won, and with which
answers. More wins on harder puzzles is the mechanism under test, not a confound.
CPU smoke (before registering; 8+8 practice, 3 test puzzles, 1 seed, 1 epoch; not panel results): runs end to end.
