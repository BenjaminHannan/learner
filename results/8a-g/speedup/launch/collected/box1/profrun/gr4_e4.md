# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## equiv

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

pre-registration: PREREG-eg-once.md: E1 vectors (bf16 GPU), E2 vectors (fp32 CPU, 64 rows), E3 loss + gradient (fp32 CPU), E4 loss trace (bf16 GPU, 300 updates)
stochastic parts pinned: True (K0 8); rows 256; on CPU (fp32, no autocast): False; E3 setting: fp32 on cuda (registered: cpu)

### E3: loss and gradient of one update (rule: loss rel diff <= 1e-05 and gradient cosine >= 0.99999; token-mean weighting changes = NOT EXACT)

| vs baseline | |d loss| | rel d loss | grad cosine | grad rel L2 | E3 (fp32 row) | per-token weighting |
|---|---|---|---|---|---|---|
| baseline rerun (fp32) | 0.00e+00 | - | 1.00000000 | 6.36e-07 | noise floor |  |
| accum=1 full batch (fp32) | OOM |  |  |  |  |  |
| baseline rerun (bf16) | 0.00e+00 | - | 0.99999995 | 3.05e-04 | noise floor |  |
| accum=1 full batch (bf16) | 5.34e-05 | 2.35e-06 | 0.99999502 | 3.16e-03 | reference only |  |
| defer (fp32) | 0.00e+00 | 0.00e+00 | 1.00000000 | 7.51e-07 | **PASS** | not analysed: this model's loss is not one token-mean cross_entropy per micro-batch (b3g2 / b3 average per row |
| defer (bf16) | 8.01e-05 | 3.53e-06 | 0.99999958 | 9.20e-04 |  |  |

### E4 defer: 300-update loss trace (schedule real): updates 101..300: mean |loss_variant - loss_old| 0.0481 (limit 0.02), difference of the two means 0.0350 (limit 0.01; old 2.9057, variant 2.8707). **E4: FAIL**

