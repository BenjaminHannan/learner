# brd-11 DRAFT marks (written 2026-09-27T05:16Z by `date -u`; NOT sealed; sent to the Thread manager for review first)

Question: does brd-9's PASS (three nights of the model's own checked hits beat no sleep by a fifth of the unreached
puzzles) hold on fresh puzzles in a wider number world, with brd-9's recipe unchanged; and does a stronger night search
(120 blurts per miss instead of 30) add to it?

Why: brd-9 PASSED on one panel in a 3-number world that is now used up. Problem 7 counts as solved only after a
replication on a fresh panel passes (brd-10 fallback plan), and Ben's goals need it not to damage anything else.

Procedure: scripts/claude_brd11.py (docstring). Recipe identical to brd-9 except the world:
- World: 3 numbers from 1-13 with target 5-60, and 4 numbers from 1-13 with target 24. Every puzzle in brd-5..9's
  practice, DEV, test and transfer sets is excluded (selftest checks the 1,200 night puzzles against them).
- Nights: seeds 9101/9102/9103, 400 new puzzles each (two thirds 3-number), the same puzzles in both arms.
- Hits: greedy if right, else the first of n_miss rule-kept blurts that the exact checker accepts (RuleKeeper is
  disclosed test scaffolding, as in brd-5..9). Each night retrains a fresh LoRA from base on everything kept, 3 epochs,
  r16, lr 2e-4, batch 8, LoRA seeds 0/1/2. The model that slept practises the next night.
- Temperature: brd-9's registered DEV rule (claude_blurt2.pick_temp, 1.0 vs 1.5, more lucky blurts wins) on brd-11's
  own DEV panel (seed 9199, 40 puzzles, never in test or nights).
- Arms: R (n_miss 30 = brd-9) and S (n_miss 120, the one change).
- Test panel: 240 puzzles from seed 9150, [MIX TO FIX: 80 three-number + 160 four-number, as brd-9, unless the T 1.5
  DEV run shows no 4-number luck], 30 samples each, for base, night 1 and night 3 of both arms and every seed.
- Harm: Fix sleep's 300 general items (claude_dl1_nights.harm_panel), greedy; lost = right at base, wrong at night 3.
- One GPU run on BensPC ($0). That run is the registered result.

Claims (unreached = 240 − base cov@30; bar = 0.20 × unreached):
- PASS (the replication, arm R): R3 cov@30 ≥ base + bar in EVERY seed, AND the 95% interval (hand-grouped bootstrap)
  for R3 − base above 0, AND no harm: R3 lost ≤ 20 of the 300 items in EVERY seed.
  If the coverage part passes but harm fails, the verdict is FAIL (harm), reported as such.
- Proved wrong: the upper 95% bound of R3 − base is below 100 × bar / 240 points.
- Otherwise NOT SHOWN. Inconclusive: fewer than 40 night-1 blurt wins in arm R.
- S claim (its own verdict, not part of PASS): SHOWN if S3 ≥ R3 + 12 in EVERY seed (seed k vs seed k) AND the 95%
  interval for S3 − R3 above 0. Proved wrong: upper bound of S3 − R3 below 5 points (12 of 240). Otherwise NOT SHOWN.
  S is judged on coverage only; S3's harm is reported.
- G7 line (reported): R3 ≥ base + 24 in every seed with the interval above 0.
- NIGHTS line (reported): R3 ≥ R1 + 12 in every seed with the R3 − R1 interval above 0.
Reported, not marks: cov@1, cov@30 split by 3- and 4-number, lucky samples; own/win/miss per night and seed; the
intervals for R1 − base, S1 − base, S3 − base, S3 − S1; harm lost/gained/net for R3 and S3.

Prediction (before any run): base cov@30 about 90-110 (bar about 26-30). R3 − base about +25 to +40; the coverage part about 55%, full PASS (with harm) about 25%.
Harm: lost ≤ 20 about 40% (a guess; dl-5's sleep nights lost 98 and 61 on this panel, RESULTS-gpu.md:59, though
with different training rows; brd training rows are bare expressions, which could spill into other answers). S3 − R3 about 0 to +8;
S SHOWN about 20%, because S only adds hits on puzzles R missed and keeps one hit per puzzle.

Limits: one panel again; the S arm adds night-search compute (up to 4x blurts on misses), so S vs R is a compute
comparison, not equal compute.
