# Profile: B3G2 3M accum 32 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## bench

arm B3G2 | rung 3M | accum 32 | batch 256 | device cuda | torch 2.11.0+cu128

| variant | median s/update | speed vs baseline | peak GB | runs |
|---|---|---|---|---|
| baseline | 7.2053 | 1.000 | 1.50 | 7.2571; 7.1535 |
| eg_once | 6.5889 | 1.094 | 2.46 | 6.8265; 6.3512 |

