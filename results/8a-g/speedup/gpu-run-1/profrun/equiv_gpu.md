# Profile: PTC 3M accum 16 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model plain_tf_steps_g, 4,023,976 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3s.json

## equiv

arm PTC | rung 3M | accum 16 | batch 256 | device cuda | torch 2.11.0+cu128

pre-registration: PREREG-eg-once.md: E1 vectors (bf16 GPU), E2 vectors (fp32 CPU, 64 rows), E3 loss + gradient (fp32 CPU), E4 loss trace (bf16 GPU, 300 updates)
stochastic parts pinned: True (K0 8); rows 256; on CPU (fp32, no autocast): False; E3 setting: fp32 on cuda (registered: cpu)

### E1: eg_once vs the old path, Gemma state H at every valid char position (256 rows, torch.bfloat16, cuda, eg real; registered setting met: True)

| comparison | min position cos | positions < 0.998 | min row-mean cos | rows < 0.9995 | largest per-row mean-cos gap |
|---|---|---|---|---|---|
| old accum 16 vs old accum 8 (the old path's own spread) | 0.776068 | 205 | 0.998554 | 3 | 1.446e-03 |
| eg_once vs old accum 16 | 0.528807 | 119 | 0.996825 | 3 | 3.175e-03 |

rules as registered: (1) every position cos >= 0.998: FAIL; (2) every row-mean cos >= 0.9995: FAIL; (3) eg_once gap <= 1.5 x the old spread (ratio 2.20) or <= the 1e-4 floor of amendment 1 (gap 3.17e-03): FAIL. **E1 overall: FAIL**

### E2: eg_once vs the old path, 64 rows, real Gemma, fp32, cpu (a second copy loaded for this) (registered setting met: True): max abs diff of H 5.722e-04 (limit 0.0001). **E2 (registered wording, abs 1e-4): FAIL**

E2 revised after seeing the CPU result (max abs diff <= 1e-05 x max |H|; counts only on rows other than the 64 of the first CPU run; this run: seed 400, prompts sha256 40271958166306a8): **PASS**

scale (diagnostic, not a mark): max |H| 533.7, p99.9 |H| 273.8, mean |H| 35.68; max abs diff / max |H| 1.072e-06; the largest difference sits on a value of 79.06 (relative 7.238e-06)

### E3: loss and gradient of one update (rule: loss rel diff <= 1e-05 and gradient cosine >= 0.99999; token-mean weighting changes = NOT EXACT)

| vs baseline | |d loss| | rel d loss | grad cosine | grad rel L2 | E3 (fp32 row) | per-token weighting |
|---|---|---|---|---|---|---|
| baseline rerun (fp32) | 0.00e+00 | - | 1.00000000 | 1.78e-08 | noise floor |  |
| accum=1 full batch (fp32) | OOM |  |  |  |  |  |
| baseline rerun (bf16) | 0.00e+00 | - | 1.00000000 | 3.19e-06 | noise floor |  |
| accum=1 full batch (bf16) | OOM |  |  |  |  |  |
| eg_once (fp32) | 0.00e+00 | 0.00e+00 | 0.99999818 | 1.91e-03 | **PASS** | weights unchanged |
| eg_once (bf16) | 0.00e+00 | 0.00e+00 | 0.99999781 | 2.10e-03 |  |  |
| sortpad,oldw (fp32) | 0.00e+00 | 0.00e+00 | 0.99999824 | 1.88e-03 | **PASS** | per-token weights restored by oldw |
| sortpad,oldw (bf16) | 2.38e-05 | 5.04e-06 | 0.99999730 | 2.32e-03 |  |  |
| sortpad,bigmb,oldw (fp32) | 4.77e-07 | 1.01e-07 | 0.99999813 | 1.93e-03 | **PASS** | per-token weights restored by oldw |
| sortpad,bigmb,oldw (bf16) | 3.15e-05 | 6.65e-06 | 0.99999708 | 2.42e-03 |  |  |
| eg_once,sortpad,oldw (fp32) | 0.00e+00 | 0.00e+00 | 0.99999818 | 1.91e-03 | **PASS** | per-token weights restored by oldw |
| eg_once,sortpad,oldw (bf16) | 2.38e-05 | 5.04e-06 | 0.99999723 | 2.36e-03 |  |  |
| sortpad (fp32) | 6.24e-03 | 1.32e-03 | 0.95268086 | 3.11e-01 | **NOT EXACT (token-mean weighting changes)** | NOT EXACT: the variant changes the per-token weights (token-mean loss per micro-batch, ratio of a row's weight |
| sortpad (bf16) | 6.24e-03 | 1.32e-03 | 0.95254392 | 3.12e-01 |  |  |
| bigmb (fp32) | 3.43e-05 | 7.26e-06 | 0.99990798 | 1.37e-02 | **NOT EXACT (token-mean weighting changes)** | NOT EXACT: the variant changes the per-token weights (token-mean loss per micro-batch, ratio of a row's weight |
| bigmb (bf16) | 6.01e-05 | 1.27e-05 | 0.99990638 | 1.38e-02 |  |  |
| tf32 (fp32) | 6.20e-06 | 1.31e-06 | 0.99999982 | 5.97e-04 | **PASS** | weights unchanged |
| tf32 (bf16) | 0.00e+00 | 0.00e+00 | 1.00000000 | 2.62e-07 |  |  |
| prefetch (fp32) | 0.00e+00 | 0.00e+00 | 1.00000000 | 1.74e-08 | **PASS** | weights unchanged |
| prefetch (bf16) | 0.00e+00 | 0.00e+00 | 1.00000000 | 3.87e-07 |  |  |

prefetch batches identical to the plain iterator: True

