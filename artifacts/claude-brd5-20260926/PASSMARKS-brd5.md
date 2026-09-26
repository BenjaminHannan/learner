# brd-5: does sleep widen coverage because it sees MANY DIFFERENT new wins? (registered 2026-09-26 ~01:55 UTC, before any run)

Source: the follow-up named in artifacts/claude-tgt5-20260926/VERIFY-tgt5.md; Ben 01:42 UTC: "Ok do it then".
Why: in blurt-5s, W (own greedy-correct answers + one lucky hit per newly won puzzle) widened coverage (base 77 →
108-112 of 184), while C (the same greedy-correct answers repeated to W's size) collapsed it (11-14). tgt-5 showed
C matches answers to targets as well as W, so target matching does not explain the gap. C differs from W in two
ways: few distinct puzzles, and no new wins. This test changes only the first.

Procedure: scripts/claude_brd5.py (docstring). ONE change from W: arm N has only 20 distinct won puzzles (chosen
from W's wins with seed 798), each with W's own first lucky hit, repeated in turn to W's exact example count. The
own greedy-correct examples, prompts, LoRA recipe (r16, 3 epochs), practice (seed 9, 400), DEV temperature rule
(1.0 vs 1.5 on the blurt-1 DEV panel) and 30 samples per test puzzle are the same as W. C is scored as a reference.
LoRA seeds 0, 1, 2. One GPU run on a rental. That run is the registered result.
Test panel FIXED NOW: artifacts/claude-brd5-20260926/test_puzzles.jsonl (md5 968b9f2fb798f0c30b58e99a11185050):
240 puzzles (160 with 3 numbers, 80 with 4 numbers and target 24; 182 hands), seed 798, with no overlap with practice
or DEV. Nothing is dropped after registration (the script stops if it finds overlap).

Measure: cov@30 = test puzzles with at least one correct sample in 30. Intervals: 95%, bootstrap over number hands
(2,000 draws), seed-averaged (claude_blurt5s.boot_ci). D = 24 puzzles (10% of 240).
- PASS ("breadth matters"): W's cov@30 ≥ N's cov@30 + 24 in EVERY seed (seed k vs seed k), AND the 95% interval
  for W − N is above 0.
- Proved wrong ("a few new wins repeated teach as well as many"): the upper 95% bound of W − N is below +5
  percentage points.
- Otherwise: NOT SHOWN.
- Inconclusive: fewer than 40 won practice puzzles, fewer than 10 own greedy-correct answers, or W's cov@30 is not
  at least base + 24 in every seed (the effect being explained did not replicate).
Reported, not marks: base, W, N, C counts at cov@1/5/10/30 and lucky samples; intervals for W − base and N − base;
the distinct puzzle counts per arm.
Reading (fixed now): PASS with N near C means breadth explains most of the collapse. PASS with N well above C means
breadth and newness both matter. Proved wrong means newness, not breadth, is what counts.
Limit: in N, fewer distinct puzzles also means fewer distinct answer strings; this test does not separate those.
CPU smoke (before registering; 40 practice, 3 test puzzles, 1 seed, 1 epoch; not the panel's results): runs end to end.

Addendum 2026-09-26 ~02:00 UTC (report-only, added after registration while the task was queued and not yet
launched; the code and the marks are unchanged). Following the outside review Ben posted (section 12), VERIFY-brd5
will report these four numbers separately for base, W, N and C, all computed from gpu/streams.json:
1. first-try success: cov@1, the first SAMPLE, not a greedy answer (the script does not score greedy on the test);
2. success within the fixed budget: cov@30;
3. distinct puzzles reached: the same as cov@30 here, since every test puzzle is a different (hand, target);
4. success on a harder structure: cov@30 split into 3-number (160) and 4-number (80) puzzles, the 4-number ones being
   the kind practice solves least.
