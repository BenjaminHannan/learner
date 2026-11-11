# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## abequiv

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

mark 6 of PREREG-b3g2-speed-ab.md: one update, 256 rows, stochastic parts pinned: True (K0 8); reference accum 4; on CPU: False; bar: relative loss difference <= 0.0001 and gradient cosine >= 0.9999, beside the reference rerun noise floor below; with a CPU fp32 comparison (Amendment 1) also: nosync bit-exact, pad64 / pad64p equal to rounding (relative gradient and loss difference <= 1e-06), tf32 and unfused bar only. A mark 6 labelled bf16_bar_only rests on the bar alone: CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run

| vs reference | rel d loss | grad cosine | grad rel L2 | step cosine | bit exact (loss + grad) | bar | mark 6 |
|---|---|---|---|---|---|---|---|
| reference again (fp32) | 0.00e+00 | 1.0000000000 | 6.68e-07 | 0.9999999921 | False | noise floor |  |
| reference again (bf16) | 0.00e+00 | 0.9999999546 | 3.01e-04 | 0.9999809346 | False | noise floor |  |
| nosync (fp32) | 0.00e+00 | 1.0000000000 | 6.71e-07 | 0.9999999924 | False | bar met |  |
| nosync (bf16) | 0.00e+00 | 0.9999999552 | 2.99e-04 | 0.9999804447 | False | bar met | **mark 6: holds (bf16_bar_only)** |
| pad64p (fp32) | 0.00e+00 | 1.0000000000 | 6.54e-07 | 0.9999999932 | False | bar met |  |
| pad64p (bf16) | 0.00e+00 | 0.9999996657 | 8.18e-04 | 0.9999716415 | False | bar met | **mark 6: holds (bf16_bar_only)** |
| pad64 (fp32) | 0.00e+00 | 0.9999999501 | 3.16e-04 | 0.9999420230 | False | bar met |  |
| pad64 (bf16) | 3.11e-06 | 0.9999992830 | 1.20e-03 | 0.9998487366 | False | bar met | **mark 6: holds (bf16_bar_only)** |
| tf32 (fp32) | 8.74e-06 | 0.9999998219 | 6.26e-04 | 0.9997954813 | False | bar met |  |
| tf32 (bf16) | 1.77e-06 | 0.9999995609 | 9.39e-04 | 0.9998610244 | False | bar met | **mark 6: holds (bf16_bar_only)** |
| unfused (fp32) | 0.00e+00 | 1.0000000000 | 6.70e-07 | 0.9999999670 | False | bar met |  |
| unfused (bf16) | 0.00e+00 | 0.9999999534 | 3.05e-04 | 0.9999815576 | False | bar met | **mark 6: holds (bf16_bar_only)** |

nosync: mark 6 holds [bf16_bar_only]; bar in bf16: True; CPU fp32 clause (bit_exact): None; bit exact in fp32 on the CPU: None; equal to rounding: None (CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run)
pad64p: mark 6 holds [bf16_bar_only]; bar in bf16: True; CPU fp32 clause (equal_to_rounding): None; bit exact in fp32 on the CPU: None; equal to rounding: None (CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run)
pad64: mark 6 holds [bf16_bar_only]; bar in bf16: True; CPU fp32 clause (equal_to_rounding): None; bit exact in fp32 on the CPU: None; equal to rounding: None (CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run)
tf32: mark 6 holds [bf16_bar_only]; bar in bf16: True; CPU fp32 clause (bar_only): None; bit exact in fp32 on the CPU: None; equal to rounding: None (CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run)
unfused: mark 6 holds [bf16_bar_only]; bar in bf16: True; CPU fp32 clause (bar_only): None; bit exact in fp32 on the CPU: None; equal to rounding: None (CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run)

mark 6 of PREREG-b3g2-speed-ab.md with Amendment 1. bit_exact = loss equal and gradient bit for bit. On a CPU fp32 run: nosync must be bit-exact; pad64 and pad64p must be equal to rounding (relative gradient difference and relative loss difference at most 1e-06); tf32 and unfused are bar-only (unfused only changes the optimizer kernel and the CPU has no fused one). On a run with no CPU fp32 comparison (every GPU run) mark 6 is the bf16 bar alone, labelled bf16_bar_only: CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run. step_* = the parameters' change after one optimizer step (descriptive; for unfused it is where fused and unfused AdamW differ, the loss and gradient cannot).

