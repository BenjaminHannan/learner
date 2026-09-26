# brd-7: on a fresh panel, does sleeping on the 1B's own checked hits solve more different puzzles? (registered 2026-09-26 ~04:00 UTC, before any run)

Source: Ben's overnight goal, problem 7 (turn lucky hits into lasting skill). The coordinator's definition of
"solved": a registered test where sleeping on the model's own checked hits makes it solve more DIFFERENT fresh
puzzles, within a fixed budget, than a matched control. Ben is asleep; this is the thread's default choice.
Why: brd-5 (INCONCLUSIVE) and brd-6 (PROVED WRONG on its own question) both reported, but did not mark, a
coverage gain from this sleep: +13 to +22 of 240 over the untrained model in brd-5, and +51 to +54 in brd-6. That
spread is too wide to call. This is a CONFIRMATION run, registered before it runs, on a panel no run has seen.

Procedure: scripts/claude_brd5.py UNCHANGED (docstring), with a new test panel. W = own greedy-correct answers + first
lucky hit per won puzzle (practice seed 9, 400 puzzles, DEV temperature rule 1.0 vs 1.5, 30 blurts). C = the same
own answers repeated to W's size (matched exposure; the blurt-3/5s control). N (20 wins repeated) is also trained
and only reported. LoRA r16, lr 2e-4, batch 8, 3 epochs, seeds 0/1/2. 30 samples per test puzzle. One GPU run on a
rental. That run is the registered result.
Test panel FIXED NOW: artifacts/claude-brd7-20260926/test_puzzles.jsonl (md5 6977ea8626e47c004a25b1e495743b1d):
240 puzzles (160 with 3 numbers, 80 with 4 numbers and target 24; 183 hands), from puzzles(seed 800, 1500). It
excludes practice seed 9 (all 800), the DEV panel and the brd-5 and brd-6 test panels.

Measure: cov@30 = test puzzles with at least one correct sample in 30 (= distinct puzzles reached). Intervals: 95%,
bootstrap over number hands (2,000 draws), seed-averaged (claude_blurt5s.boot_ci, as the script reports them).
- PASS: W's cov@30 ≥ base cov@30 + 24 in EVERY seed, AND the 95% interval for W − base is above 0, AND W's cov@30
  ≥ C's cov@30 + 24 in every seed (seed k vs seed k).
- Proved wrong: the upper 95% bound of W − base is below +5 points (12 puzzles).
- Otherwise: NOT SHOWN.
- Inconclusive: fewer than 40 won practice puzzles or fewer than 10 own greedy-correct answers.
Reported, not marks: cov@1 (first sample), cov@30 split into 3-number and 4-number, lucky samples, for base, W, N and
C; the W − N interval.
Honesty note: the 24-puzzle bar is the one brd-5 used. This run tests whether the brd-6 gain holds on new puzzles; a
pass here would be a confirmation of an effect seen once, reported as such.

Addendum 2026-09-26 ~04:05 UTC (before any run): the Director held the rental to keep vast credit for 0.2c. The same
registered run may instead run once on BensPC (handoff/held/zbrd7-benspc.md): same code, command, panel and marks;
only the GPU differs, and it is reported. Whichever of the two runs first is the registered result; the other is not
run.
