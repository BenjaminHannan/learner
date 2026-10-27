# Experiment 27 / M1-F (frozen code scale 1.2) — coordinator's forecasts

Fable (coordinator), 2026-09-21 UTC, written before any experiment-27 code exists. I have read the reviewer's
design (`design/v3/27-new-names-followup-design-fable-review.md`, sha 63d2bb51…) including its one fixture-seed
probe (frozen 1.2 reached batch LINK 0.5–0.7 by update 1,500), so these are not blind to that.

| # | Statement | Probability |
|---|---|---|
| P118 | F (frozen scale) passes 3/3 seeds | 0.30 |
| P119 | F passes in ≥ 1 seed | 0.65 |
| P120 | Control passes ≥ 2/3 | 0.90 |
| P121 | Every F seed has first-stage LINK on c2 ≥ 0.50 (reserved codes) | 0.60 |
| P122 | Any `reserved_gap` (reserved worse than training-pool by > 13/512 on some cell) in ≥ 1 F seed | 0.12 |
| P123 | `copy_side_failure` in ≥ 1 F seed | 0.12 |
| P124 | L arm (learned, started at 1.2): lowest logged scale ≤ 1.0 in 3/3 | 0.80 |
| P125 | L arm passes 3/3 | 0.22 |
