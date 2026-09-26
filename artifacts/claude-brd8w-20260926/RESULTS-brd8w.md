# brd-8w results (2026-09-26, 13:22 UTC)

## Registered verdict: INCONCLUSIVE
Ben asked me to stop the rental at about 13:21 UTC. The seed-2 box had finished its sleep arm (W) and all 7 control
nights, but it was stopped during the control's final 240-puzzle test. So seed 2 never wrote brd8_seed.json or
streams.json. The registered rule says "a seed's process does not finish" means INCONCLUSIVE. That is the verdict,
even though every mark that could be counted was met.

## What was counted
Seeds 0 and 1 were recounted from streams.json by `claude_brd8w_week.py --score` (table below). Seed 2's numbers come
from its log only (gpu/seed2/log.txt), with no streams file, so they could not be recounted or bootstrapped.

| Seed | Base | W after 1 night | after 3 | after 7 | W - base | C (7 nights) | W - C | cov@1 base → W7 |
|---|---|---|---|---|---|---|---|---|
| 0 | 128 | 158 | 169 | 169 | +41 | 22 | +147 | 12 → 41 |
| 1 | 139 | 136 | 156 | 174 | +35 | 22 | +152 | 8 → 35 |
| 2 (log only) | 118 | 140 | 159 | 162 | +44 | not measured | - | 15 → 45 |

- W ≥ base + 24: met in all 3 seeds (seed 2 from its log).
- 95% interval for W − base, 2 seeds only: [+11.0, +20.4] points of 240. It is above 0.
- W ≥ C + 24: met in seeds 0 and 1. Seed 2 has no C score.
- Reported: W − C interval, 2 seeds, is [+56.5, +67.4]. W after 7 nights minus W after 1 night is [+5.3, +15.0].
- The same untrained model scored 128, 139 and 118 on the same panel under different sampling seeds. So chance moves
  the no-sleep reading by about 20 puzzles.

## To make it official
Rerun seed 2 only, with unchanged code and panel (about 1.3 h on one GPU, about $0.65). Then score all 3 seed dirs.
This completes the registered run; it does not change the test.

## Cost
Billed so far for 3 × RTX-class GPUs at $0.485/h: $0.63 (vast.ai invoice lines for 52748679/81/82). Final lines may
add a few cents.

# brd-8 marks (recounted from streams.json; 2 seeds)

Verdict: **INCONCLUSIVE**

| Seed | Base | W (7 nights) | C (7 nights) | W - base | W - C | W after night 1 | after night 3 |
|---|---|---|---|---|---|---|---|
| 0 | 128 | 169 | 22 | +41 | +147 | 158 | 169 |
| 1 | 139 | 174 | 22 | +35 | +152 | 136 | 156 |

- W >= base + 24 in every seed: True
- 95% interval W - base (points of 240) (11.02, 20.37), above 0: True
- W >= C + 24 in every seed: True
- Proved wrong (upper bound of W - base below 5): False
- Inconclusive: True
- Reported: 95% interval W - C (56.53, 67.39); W after 7 nights - W after 1 night (5.31, 14.96)

```json
{
 "rows": [
  {
   "seed": 0,
   "base": 128,
   "W": 169,
   "C": 22,
   "W_minus_base": 41,
   "W_minus_C": 147,
   "wins_total": 529,
   "C_empty_nights": 0
  },
  {
   "seed": 1,
   "base": 139,
   "W": 174,
   "C": 22,
   "W_minus_base": 35,
   "W_minus_C": 152,
   "wins_total": 524,
   "C_empty_nights": 0
  }
 ],
 "ci95_W_minus_base_pct": [
  11.02,
  20.37
 ],
 "ci95_W_minus_C_pct": [
  56.53,
  67.39
 ],
 "ci95_W7_minus_W1_pct": [
  5.31,
  14.96
 ],
 "pass_every_seed_base_plus_24": true,
 "pass_ci_above_0": true,
 "pass_every_seed_C_plus_24": true,
 "proved_wrong_upper_below_5": false,
 "inconclusive": true,
 "verdict": "INCONCLUSIVE"
}
```
