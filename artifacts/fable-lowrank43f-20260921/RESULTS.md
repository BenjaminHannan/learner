# Experiment 43F — results (2026-09-21). All 24 runs finished; fresh accuracy at the FINAL update; seeds 4102/4103/4104.

| episodes | plain | rank 4 |
|---|---|---|
| 20 | 0.060 / 0.045 / 0.030 | 0.085 / 0.105 / 0.035 |
| 50 | 0.255 / 0.430 / 0.180 | 0.400 / 0.285 / 0.270 |
| 100 (from 43E) | 0.490 / 0.585 / 0.435 | 0.710 / 0.905 / 0.885 |

| rank at 100 episodes | fresh |
|---|---|
| 1 | 0.720 / 0.840 / 0.745 |
| 2 | 0.755 / 0.915 / 0.885 |
| 4 (43E) | 0.710 / 0.905 / 0.885 |
| 8 | 0.580 / 0.850 / 0.450 |
| 16 | 0.585 / 0.730 / 0.560 |
| unlimited = plain (43E) | 0.490 / 0.585 / 0.435 |

- F1 (rank-4 >= plain + 0.10 at 50 episodes, 2/3 seeds, never lower by > 0.02): +0.145 / -0.145 / +0.090 -> FAIL.
- F2 (same at 20 episodes): +0.025 / +0.060 / +0.005 -> FAIL.
- F3 (rank-4 at 20 episodes >= 0.50): 0.085 / 0.105 / 0.035 -> FAIL. The episode wall stands for this model.
- F4 (another rank beats 4 by >= 0.05 in 2/3): best is rank 2 at +0.045 / +0.010 / 0.000 -> FAIL. Keep 4 (ranks 2 and 4 are equal within noise).
- F5 (rank 16 at least 0.10 below rank 4 in 2/3): -0.125 / -0.175 / -0.325 -> PASS. Tighter limit = better, in order (1–4 > 8 > 16 > unlimited):
  the low rank itself matters, not just "some limit".
- F6 old skills kept: worst change 0.000 -> PASS.

Reading: the rank limit is a real but narrow gain. It broke where predicted: below ~100 episodes it no longer helps reliably,
and it never gets near 20-episode learning. Exploration seeds only; F5 would need fresh seeds before any claim. Toy only; nothing about length.
20-episode learning on this toy has so far been reached only by reusable skills + a router (43H, addresses given by hand).
