# G-transfer result, seed 201

run /mnt/project-files/domain-mode/runs/sheet-s201-v7; days 2..8; self-quiz 8000 q per day; subset 2500.

| head | within-kind AUC | groups | pooled AUC | Brier |
|---|---|---|---|---|
| SELFQUIZ8K | 0.671 | 38 | 0.791 | 0.1902 |
| SELFQUIZ2.5K | 0.628 | 38 | 0.747 | 0.2261 |
| D0 | 0.597 | 38 | 0.671 | 0.3051 |
| K_D0 | 0.500 | 38 | 0.722 | 0.2735 |
| K_SQ | 0.500 | 38 | 0.745 | 0.2037 |
| SELFQUIZ8K_S899 | 0.671 | 38 | 0.791 | 0.1902 |
| D0_S900 | 0.597 | 38 | 0.671 | 0.3063 |

Per day within-kind AUC (SELFQUIZ8K / SELFQUIZ2.5K / D0) and pooled AUC:

- day 2: 0.660 / 0.607 / 0.535 ; AUC 0.773 / 0.735 / 0.617
- day 3: 0.685 / 0.647 / 0.618 ; AUC 0.766 / 0.718 / 0.687
- day 4: 0.671 / 0.656 / 0.563 ; AUC 0.725 / 0.702 / 0.607
- day 5: 0.621 / 0.552 / 0.570 ; AUC 0.818 / 0.757 / 0.653
- day 6: 0.695 / 0.638 / 0.621 ; AUC 0.755 / 0.691 / 0.676
- day 7: 0.677 / 0.651 / 0.630 ; AUC 0.792 / 0.761 / 0.698
- day 8: 0.688 / 0.637 / 0.642 ; AUC 0.764 / 0.704 / 0.720

Marks (this seed; seeds are combined by hand):

- Baseline check: D0 recomputed 0.597 vs json 0.597: reproduces.
- PASS (SELFQUIZ8K >= 0.62 and >= D0 + 0.05): HOLDS. SELFQUIZ8K 0.671, D0 0.597
- PROVED WRONG (SELFQUIZ8K <= D0 + 0.01): does not hold. SELFQUIZ8K 0.671, D0 0.597

Extras: SELFQUIZ8K_S899 = self-quiz head on [A,S] (D0's feature set); D0_S900 = walk-forward head on [A,S,conf].
