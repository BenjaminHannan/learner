# Generalization gap: results (2026-10-23; dev, validation and probes only; sealed test never touched here)

## Phase 1: probes (500 fresh visits each; generalize/evaluate.py; full tables in results/*/D-final.md)
| model | validation | P0 | Pname | Pword | Pstyle | Pdepth | Prule | wording share of gap |
|---|---|---|---|---|---|---|---|---|
| v1 FULL (PC weights) | 45.6 | 82.7 | 82.3 | 50.6 | 82.6 | 74.8 | 79.5 | 87% |
| D-only base seed 1 | 43.0 | 73.0 | 72.4 | 45.1 | 72.3 | 67.6 | 70.3 | 93% |
| D-only base seed 0 | 47.4 | 77.2 | - | 53.1 | - | 71.8 | - | 80% |
| D-only more stories (fmore) | 47.4 | 80.5 | 81.1 | 51.4 | 81.2 | 73.9 | 79.0 | 88% |
Verdict by PASSMARKS: **Pword is the bottleneck** (drop >= G/2 in every model). Names, style, R8 each < G/4; depth ~ G/5.
Q11 95 -> 0 and Q6/Q7/Q8 collapse under new wording alone. Rule-question weakness (n_families=1) is mostly wording (63.5 -> 9.3, base1).
Caveat (ten-weaknesses audit, PR #99): Q13 answer leaks via place order; Q13 scores here are not trustworthy.

## Phase 2: one change at a time (D-only, Muon+S2, 6,000 steps, full dev / full validation from final.json)
| arm | seed | dev | validation |
|---|---|---|---|
| base | 0 | 77.8 | 47.1 |
| base | 1 | 73.2 | 42.6 |
| base | 2 | 79.4 | 48.2 |
| fmore (+47.5k plain train visits, control) | 0 | 81.2 | 47.7 |
| fdepth (+47.5k visits with validation difficulty knobs) | 0 | 82.6 | 48.5 |
| fdepth | 1 | 76.6 | 45.3 |
| fword (+47.5k visits rendered with bank-v1-aug, 1,779 train-only Claude wordings) | 0 | 76.2 | 52.1 |
| fword | 1 | box ended early; result not recovered yet | |
Baseline mean validation 46.0 (sd ~3.0, N=|s0-s1|=4.5). Pass = +8 over B, dev >= B-2, gain > 2N.
- fdepth: +1.4 (s0) / +2.7 (s1): **wrong-if met (< 3): depth is not the bottleneck.**
- fword s0: +5.0 vs base s0, +4.4 vs fmore; dev -1.6. **Not a pass (< +8), not proved wrong (> 3).** Needs seeds; bank still has 16 banks on 3 fallback wordings (q.where_before, q.who_has, ...).
