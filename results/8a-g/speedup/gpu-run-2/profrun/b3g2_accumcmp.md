# Profile: B3G2 3M accum 32 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## accumcmp

arm B3G2 | rung 3M | accum 32 | batch 256 | device cuda | torch 2.11.0+cu128

one update, 256 rows, stochastic parts pinned: True (K0 8); on CPU: False; reference accum 32

| accum vs 32 | |d loss| | rel d loss | grad cosine | grad rel L2 | note |
|---|---|---|---|---|---|
| 32 again (fp32) | 0.00e+00 | - | 1.00000000 | 5.14e-07 | noise floor |
| 16 (fp32) | 3.81e-06 | 1.68e-07 | 0.99999987 | 5.01e-04 |  |
| 8 (fp32) | 1.91e-06 | 8.41e-08 | 0.99999987 | 5.14e-04 |  |
| 4 (fp32) | 0.00e+00 | 0.00e+00 | 0.99999988 | 4.89e-04 |  |
| 32 again (bf16) | 0.00e+00 | - | 0.99999999 | 1.31e-04 | noise floor |
| 16 (bf16) | 1.28e-04 | 5.63e-06 | 0.99999949 | 1.01e-03 |  |
| 8 (bf16) | 9.67e-04 | 4.26e-05 | 0.99999909 | 1.35e-03 |  |
| 4 (bf16) | 2.48e-05 | 1.09e-06 | 0.99999854 | 1.71e-03 |  |

descriptive only: no pass bar. K pinned means every accum runs the same number of thinker rounds, so this isolates the partition (how rows share a micro-batch and its loss average).

