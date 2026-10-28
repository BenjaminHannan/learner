# Addendum H on the M3: result notes (2026-10-28)

Pre-registered outcome (SUMMARY_laps.txt, reproduced from test.jsonl): **NOT SHOWN**. NEXT: no follow-up unless Addendum G passes.

- shown: the plain Qwen3.6-35B-A3B 3-bit model follows 1-link chains (96%) and 2-link chains (73%), drops to 28% at 3 links, and is
  at the 1-in-7 floor from 4 links on (test, 100 rows per depth).
- shown: C* (layers 16-27 run twice, picked on dev) minus plain on D = {2, 3}: +4.0 [-1.0, +9.0], n = 200. The bar was +5 with CI > 0.
  Depths below D (depth 1): +1.0 [-2.0, +5.0].
- shown: answer-stable halting used 2.0-2.5 laps at every depth (Spearman 0.04 [-0.01, 0.08]); it does not adapt.
- suggested (post hoc, no mark): the control block (layers 4-15 run twice) gained +12.0 [+7.0, +17.0] on D. It tied C* on dev
  (62.5 each on 80 rows; C* won the pre-set tie-break on mean answer log-prob, -1.78 vs -1.96). By depth, plain / C* / control:
  d1 96/97/99, d2 73/72/84, d3 28/37/41, d4 21/23/25, d5+ at the floor for all three. The two blocks give the same answer on
  76.5% of D rows. Because the control was not the pre-chosen block, its gain is a lead for a new pre-registered test, not a result.
- untested: whether an early-block repeat helps at 4-bit or 8-bit, on other prompts, or on general ability (MMLU-Pro).
