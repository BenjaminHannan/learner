# brd-6: at equal exposure, do twice as many different won puzzles widen coverage more? (registered 2026-09-26 ~03:05 UTC, before any run)

Source: follow-up to brd-5 (registered INCONCLUSIVE; artifacts/claude-brd5-20260926/VERIFY-brd5.md), for Ben's
overnight goal (problem 7: turn lucky hits into lasting skill). Ben is asleep; this is the thread's default choice.
Why: brd-5 showed that, at equal exposure, FEWER distinct won puzzles (20 repeated) drop coverage below the untrained
model. This asks the same question in the other direction: do MORE distinct puzzles, at the same exposure, help?

Procedure: scripts/claude_brd6.py (docstring). Practice = puzzles(seed 9, 800); the first 400 are brd-5's practice set.
- W4 = brd-5's W, unchanged: own greedy-correct answers + first lucky hit per won puzzle, from the first 400; 3 epochs.
- W8 = the same from all 800, trained for the same number of example passes as W4 (3 x len(W4)): examples shuffled
  and repeated in turn to that length, one pass. Optimizer steps equal up to rounding (both are reported).
- ONE change: the number of distinct practice puzzles behind the examples (about double) at equal exposure.
- LoRA r16, lr 2e-4, batch 8, seeds 0/1/2; DEV temperature rule 1.0 vs 1.5 (blurt-1 DEV panel); 30 samples per
  test puzzle. One GPU run on a rental. That run is the registered result.
Test panel FIXED NOW: artifacts/claude-brd6-20260926/test_puzzles.jsonl (md5 018f09ff751477d0b9b001ec78ad2ab2):
240 puzzles (160 with 3 numbers, 80 with 4 numbers and target 24; 177 hands), seed 799, with no overlap with the 800
practice puzzles or DEV. 34 of them also appear in brd-5's test panel; that panel was only ever tested, never
trained or tuned on. The script stops if it finds overlap with practice or DEV.

Measure: cov@30 = test puzzles with at least one correct sample in 30 (= distinct puzzles reached). Intervals: 95%,
bootstrap over number hands (2,000 draws), seed-averaged (claude_blurt5s.boot_ci).
- PASS ("more distinct puzzles help at equal exposure"): W8's cov@30 ≥ W4's cov@30 + 12 in EVERY seed (seed k vs
  seed k), AND the 95% interval for W8 − W4 is above 0.
- Proved wrong: the upper 95% bound of W8 − W4 is below +2.5 points (6 puzzles).
- Otherwise: NOT SHOWN.
- Inconclusive: W8 has fewer than 300 examples, OR the lower 95% bound of W4 − base is at or below 0 (the brd-5 gain
  over the untrained model did not show at all).
Reported, not marks: for base, W4 and W8, cov@1 (first sample), cov@30, 3-number and 4-number cov@30 separately,
lucky samples; intervals for W4 − base and W8 − base; own/win counts, mean answer length, 3-number share and
optimizer steps for W4 and W8 (the arm-matching check Ben's evaluator asked for); practice.jsonl saves every
practice puzzle's outcome, so the matching can be rechecked.
Why these bars: 12 puzzles is 5% of the panel, half of brd-5's 24, because this compares two good arms rather than
good against collapsed. The brd-5 "base + 24" replication gate is replaced by "W4 beats base at all": the claim here
is W8 vs its matched control, not the size of W4's gain.
Limit: W8 examples are seen 1-2 times, W4's 3 times; fewer repeats per example is part of the change, as in brd-5.
CPU smoke (before registering; 30 practice, 3 test puzzles, 1 seed, 1 epoch; not panel results): runs end to end.
