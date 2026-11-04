# Seed noise: reference writers on seeds 100-104 (not used in evolution or confirmation)

Final harness (2026-10-20): guaranteed decoys; writer isolated in a child process with lines shuffled across visits on every call. The baseline runs exactly as a candidate does (untrusted, with the writer checks); the references run as trusted.

| writer | score mean | score sd | score range | acc familiar | acc novel | pick novel | person-lost errors (novel) | s/seed (4 parallel) |
|---|---|---|---|---|---|---|---|---|
| baseline_singlepool | 0.497 | 0.0196 | 0.046 | 0.607 | 0.388 | 0.537 | 0.448 | 52 |
| mean_pool | 0.345 | 0.0178 | 0.044 | 0.418 | 0.272 | 0.560 | 0.391 | 51 |
| two_pool | 0.616 | 0.0325 | 0.079 | 0.774 | 0.458 | 0.592 | 0.403 | 53 |
| multihead_pool | 0.773 | 0.0213 | 0.053 | 0.982 | 0.565 | 0.568 | 0.430 | 53 |
| oracle_address | 0.972 | 0.0129 | 0.035 | 1.000 | 0.945 | 0.945 | 0.055 | 51 |

Per-seed scores:

- baseline_singlepool: 100: 0.478, 101: 0.502, 102: 0.523, 103: 0.477, 104: 0.506
- mean_pool: 100: 0.334, 101: 0.339, 102: 0.375, 103: 0.331, 104: 0.348
- multihead_pool: 100: 0.783, 101: 0.756, 102: 0.802, 103: 0.749, 104: 0.777
- oracle_address: 100: 0.975, 101: 0.973, 102: 0.966, 103: 0.991, 104: 0.956
- two_pool: 100: 0.600, 101: 0.567, 102: 0.637, 103: 0.631, 104: 0.646
