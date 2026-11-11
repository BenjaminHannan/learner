# Profile: B3G2 3M accum 32 batch 32 on x86_64 (cpu), torch 2.14.1+cpu

model b3g2, 205,014 trained params, data /dev/shm/ptcdry/J/work/g8a/pools/p10-rung30-s400-a64-L (400 rows), EG front stub, bf16 autocast False, seed 400, caps caps_b3g2.json

## accumcmp

arm B3G2 | rung 3M | accum 32 | batch 32 | device cpu | torch 2.14.1+cpu

one update, 32 rows, stochastic parts pinned: True (K0 9); on CPU: True; reference accum 32

| accum vs 32 | |d loss| | rel d loss | grad cosine | grad rel L2 | note |
|---|---|---|---|---|---|
| 32 again (fp32) | 0.00e+00 | - | 1.00000000 | 0.00e+00 | noise floor |
| 16 (fp32) | 0.00e+00 | 0.00e+00 | 1.00000000 | 1.33e-07 |  |
| 8 (fp32) | 0.00e+00 | 0.00e+00 | 1.00000000 | 1.26e-07 |  |
| 4 (fp32) | 0.00e+00 | 0.00e+00 | 1.00000000 | 1.18e-07 |  |

descriptive only: no pass bar. K pinned means every accum runs the same number of thinker rounds, so this isolates the partition (how rows share a micro-batch and its loss average).

