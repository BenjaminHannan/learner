# Speed box 1 (Vast 57719271, RTX PRO 6000 Max-Q UK, $1.07/h, 20:37-21:14Z Oct 25, ~$0.66). Raw: speed_all.json

## Packed 4-bit frozen base (qwen36_mem) - SHOWN
- Bit-exact: packed logits bitwise equal to the qdq copy on the real model.
- Weights 64.6 -> 18.9 GiB. Peak at tok 2048: 83.7 -> 39.4 GiB (plain), 22.1 GiB with checkpointing. packed_fit (31.4 GiB cap) runs tok 8192 with ckpt at 23.3 GiB: fits a 32 GB RTX 5090.
- Speed cost (s/step, same box): qdq 2048 plain 1.67 (best qdq; 4096/8192 need ckpt: 2.27/2.42).
  packed eager dequant: 9.18 (5.5x slower). packed fused (--compile-dequant): 2048 plain 4.20, 4096 plain 3.49, 8192 ckpt 4.22 (2.1-2.5x slower than the best qdq).
- Verdict: memory win shown; NOT a speed win. Per-step dollars on a 5090 (~$0.49/h) at ~4.2 s would be ~$0.57 per 1000 steps vs ~$0.56 on a PRO 6000 at 1.67 s ($1.20/h): about even, and slower in wall time (suggested; untested on a real 5090). Next lever: a fused int4 grouped-GEMM kernel instead of dequant-then-grouped_mm (untested).

## Dream generation row compaction (dreamgen) - SHOWN speed, NOT exact
Seconds base -> compact (batch 32, n 64): tag 44.3 -> 28.4 (1.56x), dream 88.0 -> 37.9 (2.32x), verify 3.42 -> 9.25 (0.37x; pad64 3.19), rem 9.08 -> 5.25 (1.73x), probe 4.45 -> 1.44 (3.1x).
Greedy replies equal to base: tag 0.75 (pad64 0.33, seg16 0.94), verify 0.80, probe 0.61. Far below the >=0.97 expected. Unknown if base itself is deterministic run to run (box 2 adds a base_again row). Not adoptable until that floor is known.

## Train-step profiler (qwen36_step) - FAILED to run
Bug: CPU torch.Generator for CUDA LoRA params (profile_step.py:115). Fixed; the harness now runs end to end on a tiny real-architecture checkpoint on CPU (parity True for baseline, sync_free, kl_cache, fused_norms; fla variants need a GPU).
