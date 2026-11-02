# Speed box 2 (Vast 57723465, RTX PRO 6000 Max-Q UK, $1.07/h, 21:19-21:54Z Oct 25, ~$0.63; box 1+2 ~$1.29). Raw: box2_speed_all.json

## Train step, full 40-layer Qwen3.6-35B-A3B, realistic night batches (1,619 real tokens/step), tok 2048 (qwen36_step)
Use MEDIANS: the means carry warm-up/allocator outliers (baseline steps 1.45 1.45 4.29 3.40 1.46 1.44).
- baseline median 1.457 s, peak 84.8 GiB. parity reference.
- sync_free 1.524 s: no gain (the 28.7% "saved" on means is an outlier artifact). parity pass.
- kl_cache 1.331 s: ~9% faster (SHOWN, exact: CE/KL rel diff 0, grad rel 4e-8). Prefill 200 replay examples 3.6 s, 26 MB.
- fla_conv / fused_norms / packed / all: not reached (14-min timeout; profiler passes cost ~5-7 s/step each).

## Profile (baseline): the GPU is idle 63% of the step
528,770 kernels per step; gpu_busy 0.37. aten::mm 151,653 calls/step (1.02 s GPU, tiny 16x16/32x32 wmma cutlass tiles),
aten::item 144,640, select/slice ~288k each, but aten::_grouped_mm only 560 calls. Suggested cause: the BACKWARD of torch 2.9 _grouped_mm
for the frozen routed experts runs a per-expert loop (560 calls x 256 experts ~ 143k mm + one .item() each). Fix (exact up to float order):
a custom autograd Function whose backward computes grad_x with one grouped_mm against the transposed frozen weights (no weight grad).
Untested; expected to remove most of the 1.0 s of tiny GEMMs and the CPU launch overhead.

## Dream generation (dreamgen): base vs base_again is 1.000 identical on all greedy phases (GPU generation is deterministic),
so compaction's differences are REAL, not noise: tag same 0.84 (pad64 0.42), verify 0.94, probe 0.63-0.69. Speed: tag 43.5 -> 30.1 s,
probe 3.05 -> 0.55-1.44 s, verify ~flat. Verdict: NOT exact (bf16 numerics change with batch shape, flipping greedy picks); do not adopt as exact.
Could only be adopted after a quality check showing the night's outputs are no worse.
