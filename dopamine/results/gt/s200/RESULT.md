# G-transfer result, seed 200

run /mnt/project-files/domain-mode/runs/sheet-s200-v7; days 2..7; self-quiz 8000 q per day; subset 2500.

| head | within-kind AUC | groups | pooled AUC | Brier |
|---|---|---|---|---|
| SELFQUIZ8K | 0.642 | 38 | 0.756 | 0.2016 |
| SELFQUIZ2.5K | 0.607 | 38 | 0.714 | 0.2365 |
| D0 | 0.543 | 38 | 0.669 | 0.2844 |
| K_D0 | 0.500 | 38 | 0.722 | 0.2556 |
| K_SQ | 0.500 | 38 | 0.730 | 0.2050 |
| SELFQUIZ8K_S899 | 0.641 | 38 | 0.756 | 0.2016 |
| D0_S900 | 0.543 | 38 | 0.669 | 0.2840 |

Per day within-kind AUC (SELFQUIZ8K / SELFQUIZ2.5K / D0) and pooled AUC:

- day 2: 0.613 / 0.614 / 0.471 ; AUC 0.754 / 0.738 / 0.495
- day 3: 0.641 / 0.596 / 0.462 ; AUC 0.758 / 0.712 / 0.572
- day 4: 0.633 / 0.615 / 0.558 ; AUC 0.758 / 0.729 / 0.688
- day 5: 0.685 / 0.641 / 0.555 ; AUC 0.773 / 0.718 / 0.684
- day 6: 0.645 / 0.601 / 0.560 ; AUC 0.717 / 0.667 / 0.655
- day 7: 0.618 / 0.579 / 0.605 ; AUC 0.672 / 0.614 / 0.652

Marks (this seed; seeds are combined by hand):

- Baseline check: D0 recomputed 0.543 vs json 0.543: reproduces.
- PASS (SELFQUIZ8K >= 0.62 and >= D0 + 0.05): HOLDS. SELFQUIZ8K 0.642, D0 0.543
- PROVED WRONG (SELFQUIZ8K <= D0 + 0.01): does not hold. SELFQUIZ8K 0.642, D0 0.543

Extras: SELFQUIZ8K_S899 = self-quiz head on [A,S] (D0's feature set); D0_S900 = walk-forward head on [A,S,conf].
