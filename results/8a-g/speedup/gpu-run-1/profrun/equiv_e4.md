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
| baseline rerun (fp32) | 0.00e+00 | - | 1.00000000 | 1.48e-08 | noise floor |  |
| accum=1 full batch (fp32) | OOM |  |  |  |  |  |
| baseline rerun (bf16) | 0.00e+00 | - | 1.00000000 | 4.67e-07 | noise floor |  |
| accum=1 full batch (bf16) | OOM |  |  |  |  |  |
| eg_once (fp32) | 0.00e+00 | 0.00e+00 | 0.99999818 | 1.91e-03 | **PASS** | weights unchanged |
| eg_once (bf16) | 0.00e+00 | 0.00e+00 | 0.99999781 | 2.10e-03 |  |  |

### E4 eg_once: 300-update loss trace (schedule real): updates 101..300: mean |loss_variant - loss_old| 0.0162 (limit 0.02), difference of the two means 0.0088 (limit 0.01; old 1.5322, variant 1.5234). **E4: PASS**

