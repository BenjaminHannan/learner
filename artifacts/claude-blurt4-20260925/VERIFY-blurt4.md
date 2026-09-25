# blurt-4 result: PROVED WRONG on its registered measure (hindsight hits lowered luck), but a coverage twist

Marks: PASSMARKS-blurt4.md (main be2ee7b52, registered before the rental). Run: vast RTX 5090 (the builder's
RESULTS-gpu-4.md, copied here from builder-outbox), 16 minutes, pinned model 87179e5c. I recounted every mark from
gpu-4/blurt4_summary.json and it agrees with the builder.

Test: 64 fresh puzzles × 30 blurts; DEV picked T 1.0 (41 vs 35 lucky). Before sleep: 66 lucky blurts, 32 puzzles hit.
| Arm (560 examples each) | Lucky blurts, seeds 0 / 1 (mean) | Puzzles hit, of 64 | Greedy right |
|---|---|---|---|
| W (blurt-3 recipe, padded by repeats) | 219 / 223 (221) | 32 / 35 | 5 / 8 |
| H (+375 hindsight hits, correctly relabelled) | 156 / 124 (140) | 41 / 43 | 5 / 3 |
| P (same blurts, WRONG relabel) | 163 / 117 (140) | 46 / 42 | 7 / 1 |

- H1 (mean H ≥ 1.2 × mean W, and every H seed above every W seed): NOT MET (140 vs 221).
- H2 (mean H ≥ 1.2 × mean P): NOT MET (140 vs 140).
- Proved wrong (mean H ≤ mean W): MET. Verdict: PROVED WRONG.

What it means (puzzles only):
- Shown: sleeping on hindsight relabels lowered the lucky-blurt count, and relabelling them wrongly (P) did exactly
  as well as relabelling them right (H). So on the registered measure, the correctness of the relabel did not matter.
- Shown, but not a registered mark, so it can't count as a pass: both relabel arms reached MORE different puzzles
  (H 41/43, P 46/42) than W (32/35, no better than before sleep, 32). W piled its extra luck onto puzzles it could
  already hit. Since P matches H, the likely cause is more varied practice targets, not correct hindsight
  (suggested, untested).
- Note: this W did not widen coverage, unlike blurt-3r's W (29 → 40/43 at T 1.5). Here DEV picked T 1.0. Whether
  temperature explains the difference is untested.
