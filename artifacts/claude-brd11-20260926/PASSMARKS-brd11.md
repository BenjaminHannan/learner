# brd-11: does brd-9's PASS replicate in a wider puzzle world, and does a stronger night search add to it? (registered 2026-09-27 05:29 UTC by `date -u`, before any run)

From the draft PASSMARKS-brd11-DRAFT.md as reviewed by the Thread manager (768507db2); changes at sealing are listed at the end.

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
- Test panel FIXED NOW: artifacts/claude-brd11-20260926/test_puzzles.jsonl (md5 8c86108a424bda4fae541adec2858302),
  `claude_brd11.py --make-panel` (n3 120): 120 three-number puzzles from wide(seed 9150) + 120 four-number (target 24)
  puzzles; 240 distinct puzzles, 221 hands, 0 overlap with any brd-5..9 set, brd-11's nights or its DEV panel.
  Why 120 + 120: the mix rule (reviewed) kept 4-number puzzles, since the plain model reached 5 of the 20 four-number
  DEV puzzles at T 1.5 (0 at T 1.0). But the 4-number target-24 world has only 1,362 solvable puzzles and 1,242 are
  already used, so all 120 left are in the panel (enumerated, shuffled with seed 9150), and the other 120 are
  three-number. 30 samples each,
  scored for base, night 1 and night 3 of both arms and every seed.
- Harm: Fix sleep's 300 general items (claude_dl1_nights.harm_panel), greedy; lost = right at base, wrong at night 3.
- One GPU run on BensPC ($0). That run is the registered result.

Claims (unreached = 240 − base cov@30; bar = 0.20 × unreached):
- PASS (the replication, arm R): R3 cov@30 ≥ base + bar in EVERY seed, AND the 95% interval (hand-grouped bootstrap)
  for R3 − base above 0, AND no harm: R3 lost ≤ 20 of the 300 items in EVERY seed.
  If the coverage part passes but harm fails, the verdict is FAIL (harm), reported as such.
- Proved wrong: the upper 95% bound of R3 − base is below 100 × bar / 240 points.
- Otherwise NOT SHOWN. Inconclusive: fewer than 40 night-1 blurt wins in arm R.
- S claim (its own verdict, not part of PASS): SHOWN if S3 ≥ R3 + 12 in EVERY seed (seed k vs seed k) AND the 95%
  interval for S3 − R3 above 0. "S cannot reach the bar": upper bound of S3 − R3 below 5 points (12 of 240); this
  does NOT mean S adds nothing. "S adds nothing": upper bound of S3 − R3 ≤ 0 points. Otherwise NOT SHOWN.
  S is judged on coverage only; S3's harm is reported.
- G7 line (reported): R3 ≥ base + 24 in every seed with the interval above 0.
- NIGHTS line (reported): R3 ≥ R1 + 12 in every seed with the R3 − R1 interval above 0.
Reported, not marks: cov@1, cov@30 split by 3- and 4-number, lucky samples; own/win/miss per night and seed; the
intervals for R1 − base, S1 − base, S3 − base, S3 − S1; harm lost/gained/net for R3 and S3.

Prediction (before any run): base cov@30 about 90-110 (bar about 26-30). R3 − base about +25 to +40; the coverage part about 55%, full PASS (with harm) about 25%.
Harm: lost ≤ 20 about 40% (a guess; dl-5's sleep nights lost 98 and 61 on this panel, RESULTS-gpu.md:59, though
with different training rows; brd training rows are bare expressions, which could spill into other answers). S3 − R3 about 0 to +8;
S SHOWN about 20%, because S only adds hits on puzzles R missed and keeps one hit per puzzle.

Limits: the harm panel is Fix sleep's own dev harm panel (claude_dl1_nights.harm_panel, 300 code-made items), used
again here, so passing it is a consistency check, not fresh evidence of no harm; lost and gained are both reported.
One panel again; the S arm adds night-search compute (up to 4x blurts on misses), so S vs R is a compute
comparison, not equal compute.

DEV counts behind the choices (dev/, seed 9199, 40 puzzles, 20 + 20): T 1.0 reached 11 (3-number 11, 4-number 0);
T 1.5 reached 17 (3-number 12, 4-number 5). The registered run re-applies the DEV temperature rule itself.

Changes at sealing (vs the reviewed draft): the panel mix is 120 + 120, not 80 + 160 (not enough unused 4-number
puzzles, above); make_panel enumerates the 4-number part instead of sampling it.
Smokes (not results): selftest ok; a fake-solver run (scratchpad b11_fake.py) ran every line of run() through the DEV
temperature rule, both arms, 3 seeds, harm flips, all six intervals and the summary files; a real-model CPU call of
the harm panel scorer through claude_blurt2.Solver returned 4 scores.
brd11_partial.json is rewritten after each arm-seed so a stopped run keeps what finished; a run that does not reach
the final summary gives no verdict (partial, reported as such), and the one re-run then allowed is a fresh launch.
