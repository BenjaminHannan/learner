# Profile: PTS 3M accum 16 batch 256 on arm (cpu), torch 2.14.1

model plain_tf_steps_g, 4,023,976 trained params, data /Users/ben-hannan/speedup/pool-sample (20,049 rows), EG front real, bf16 autocast False, seed 402, caps caps_b3s.json

## equiv

arm PTS | rung 3M | accum 16 | batch 256 | device cpu | torch 2.14.1

pre-registration: PREREG-eg-once.md: E1 vectors (bf16 GPU), E2 vectors (fp32 CPU, 64 rows), E3 loss + gradient (fp32 CPU), E4 loss trace (bf16 GPU, 300 updates)
stochastic parts pinned: True (K0 8); rows 256; on CPU (fp32, no autocast): True; E3 setting: fp32 on cpu (registered: cpu)

### E1: eg_once vs the old path, Gemma state H at every valid char position (256 rows, torch.float32, cpu, eg real; registered setting met: False)

| comparison | min position cos | positions < 0.998 | min row-mean cos | rows < 0.9995 | largest per-row mean-cos gap |
|---|---|---|---|---|---|
| old accum 16 vs old accum 8 (the old path's own spread) | 1.000000 | 0 | 1.000000 | 0 | 3.821e-12 |
| eg_once vs old accum 16 | 1.000000 | 0 | 1.000000 | 0 | 1.188e-11 |

rules as registered: (1) every position cos >= 0.998: PASS; (2) every row-mean cos >= 0.9995: PASS; (3) eg_once gap <= 1.5 x the old spread (ratio 3.11): PASS. **E1 overall: PASS**

### E2: eg_once vs the old path, 64 rows, real Gemma, fp32, cpu (registered setting met: True): max abs diff of H 2.154e-03 (limit 0.0001). **E2 (registered wording, abs 1e-4): FAIL**

E2 revised after seeing the CPU result (max abs diff <= 1e-05 x max |H|; counts only on rows other than the 64 of the first CPU run; this run: seed 402, prompts sha256 f0fd2653c1b2ab72): **PASS**

scale (diagnostic, not a mark): max |H| 564.2, p99.9 |H| 273.2, mean |H| 33.65; max abs diff / max |H| 3.819e-06; the largest difference sits on a value of -9.639 (relative 2.235e-04)

### E3: loss and gradient of one update (rule: loss rel diff <= 1e-05 and gradient cosine >= 0.99999; token-mean weighting changes = NOT EXACT)

| vs baseline | |d loss| | rel d loss | grad cosine | grad rel L2 | E3 (fp32 row) | per-token weighting |
|---|---|---|---|---|---|---|
| baseline rerun (fp32) | 0.00e+00 | - | 1.00000000 | 0.00e+00 | noise floor |  |
| accum=1 full batch (fp32) | not run |  |  |  |  |  |
| eg_once (fp32) | 0.00e+00 | 0.00e+00 | 1.00000000 | 5.99e-08 | **PASS** | weights unchanged |

