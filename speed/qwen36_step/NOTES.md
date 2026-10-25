# qwen36_step: Qwen3.6-35B-A3B LoRA sleep-training step (Trainer.step 1.70 s at tok budget 2048 vs 0.485 s plain 8x256)

Labels: SHOWN = measured or proven here (CPU, tiny config, or source/arithmetic). SUGGESTED = follows from a measurement or the source plus arithmetic, no GPU run.
UNTESTED = idea only. Nothing here was timed on a GPU (none in this container); every s/step number below is an estimate until `profile_step.py` runs.
Small card experiments and the village model are not touched: this is pure engine speed, same loss and gradients.

## Files
- `fast_step.py`  opt-in patches: `undo = fast_step.install(sleepb, sync_free=, kl_cache=, packed=, fla_conv=, fused_norms=)`. All off = the original `Trainer.step` (tested bit-identical).
- `test_fast_step.py`  CPU parity on sleepb's tiny random Qwen3.5-MoE (fp32, LoRA, random B): baseline vs each option, 2 steps (second hits the KL cache), single and split
  micro-batches, weighted and unweighted. `test_trim.py`  the layer-trimming loader on a tiny many-shard checkpoint in the real key layout.
- `profile_step.py`  GPU harness (first N real layers, real shards, sleepb `Trainer.step`, torch.profiler, baseline + each fix, one JSON). `realistic.py`, `padding_stats.py` (+ `padding_stats.json`)  night-shaped batches / padding sizing.
- Run: `python speed/qwen36_step/profile_step.py --layers 8 --out profile_step.json` (then `--layers 4`; per-layer cost = difference / 4; constant = lm_head, embed, optimizer).
  24-32 GB card: N=8 is ~17 GB of weights. Add `--extra-budgets 4096` to time baseline/packed at a bigger budget. `--variants baseline,packed` for one change at a time.

## CPU results (SHOWN; fp32, max abs diff vs baseline; largest |grad| = 0.049, 0.040 weighted)
| option | CE | KL | LoRA grad |
|---|---|---|---|
| sync_free | 0 | 6e-11 | 1.9e-9 |
| kl_cache (hits on step 2) | 0 | 6e-11 | 1.9e-9 |
| packed (split into several bins / one bin) | 9.5e-7 | 1.7e-10 | 1.9e-8 |
| all three, split / weighted / padded+weighted | <=9.5e-7 | <=1.7e-10 | <=1.9e-8 |
| fused_norms (torch.compile, CPU) | 0 | - | 1.3e-8 |
| all off vs original | - | - | 0 exactly |
Packed no-leak check: a sequence's hidden states change by 7e-7 when its pack neighbour is replaced (fp32 noise). The packed CPU path uses per-sequence torch loops for the
GDN conv/chunk ops (`torch_varlen_patches`), so it proves the plumbing (positions, block mask, target gather, weights, loss scaling), NOT the fla varlen kernels: those are checked on GPU by
`profile_step.py`'s parity step. GPU pass marks, fixed in advance (bf16 and different batch shapes, so not bit-equal): CE rel diff < 1e-2, KL rel diff < 5e-2, LoRA-grad cosine > 0.99.
A variant that fails them is not a win whatever its speed.

## Ranked candidates (expected = share of today's step time saved, on night-shaped batches)
Sizing basis (SHOWN, `padding_stats.json`, week1 diary + real Qwen3.6 chat template; short-example lengths assumed, open-book prompts ~346 tokens measured): a bsz-16 step carries
1828 real tokens in 2707 padded (33% padding) in 2.2 micro-batches at budget 2048, and the replay group 439 real in ~530 padded (18%): total 30% padding. At budget 4096 the
unsorted single-group path pads 54%. First-fit-decreasing packing needs 1.35 bins for the batch. Also: moe_bench's synthetic batch has 5.3k padded tokens per step versus ~3.2k here,
so the 1.70 s in the .estimate.json is likely too high for the real run by roughly a third (SUGGESTED; check with the realistic batches in `profile_step.py`, which also prints the real tokens per step).

1. **Padding-free packing (`packed`)  expected 20-28%, SUGGESTED.** Evidence: 30% of fwd+bwd tokens are padding (SHOWN); step time ~ tokens (the micro bench 4.2k tok/s) so
   ~-30% tokens, minus lost batch efficiency in the expert GEMMs. Pad tokens also go through router + experts today. Also removes the micro-batch count (2.2 -> 1.35 + 1). Mechanism (read in
   transformers 5.20.2 source): position_ids reset per sequence + attention_mask=None makes `create_causal_mask` build a block-diagonal mask for the 10 sdpa layers (`find_packed_sequence_indices`);
   `cu_seq_lens_q` reaches the 30 GDN layers, where HF forwards it to fla's `chunk_gated_delta_rule(cu_seqlens=)` (fla 0.6.0 installed). Correction to the brief: causal-conv1d is NOT needed for packing,
   fla ships its own Triton `causal_conv1d(cu_seqlens=)`; but HF's torch-conv fallback does NOT raise on `cu_seq_lens_q` (it only checks `cu_seqlens`/`seq_idx`), it silently convolves across the
   sequence boundary (3 tokens leak), so packing without `fla_conv` is wrong. `fast_step` always pairs them. Not done: flash varlen for the full-attention layers (flash-attn not installed; sdpa with a T x T
   bool mask is ~1.5% of FLOPs at T=2048). Wrong if: parity step fails the marks, or packed s/step is not below baseline s/step on the realistic batches (then the expert GEMMs are not token-proportional at this size).
2. **KL reference cache (`kl_cache`)  expected ~5%, SUGGESTED.** Evidence: the reference forward is 1 of 4 forward-equivalents on ~15-20% of the tokens (530 of 3240 padded tokens, fwd only = 5% of the cost units);
   it also drops one lm_head+decoder call per replay micro-batch. Safe: sleepb never writes base weights (grep of backbone/sleep/brain/sleepb.py: only `lora_*.weight.data` and `delta_w`; `restore`
   copies only trainable/delta tensors; q4 runs before LoRA; delta hooks are off inside `disable_adapter()`). Cache = adapter-off final hidden at the target positions, keyed by (ids, loss_start), 200 replay
   examples ~ 2 MB per 200x... (SHOWN on CPU tiny; ~30 MB at real size), capped at 512 MB; a fingerprint of 4 frozen tensors is re-checked every 100 steps and clears the cache if the base moved.
   Cold start: each example is computed once (hit rate after k steps = 1-(1-8/200)^k; ~98% by step 100). Changes numerics only by batch-shape bf16 noise (the cached ref was computed in another micro-batch composition).
   The harness pre-fills the cache and reports steady state plus the fill time. Wrong if: step time does not drop by >= 3%.
3. **Fused RMSNorm (`fused_norms`)  expected 3-6%, UNTESTED.** 80 RMSNorms + 30 gated norms + q/k norms run as ~7 fp32 elementwise kernels each (~150 MB of traffic per norm per 2048 tokens fwd,
   2-3x that bwd): ~30 ms per 2048 tokens by bandwidth arithmetic against 485 ms. torch.compile(dynamic) on the two forwards; recompile limit raised to 64. Check the `norm`/`cast_copy`/`elementwise` buckets in the profile.
4. **fla Triton short conv (`fla_conv`)  expected 2-6%, UNTESTED.** HF without causal-conv1d runs `F.conv1d` (depthwise, 8192 channels, kernel 4) + padding copy + slice + a separate silu, on a transposed view; backward
   is the slow depthwise path. fla 0.6.0 has `fla.modules.causal_conv1d.causal_conv1d` (Triton fwd+bwd, fused silu, cu_seqlens), which `fast_step` swaps in with zero copies (HF's [B,D,T] is a transpose view of [B,T,D]).
   Installing the `causal-conv1d` CUDA package for sm_120 (nvcc >= 12.8, `TORCH_CUDA_ARCH_LIST=12.0`, `--no-build-isolation`) is feasible but unnecessary; if it is installed HF picks it up on its own (padded only,
   no cu_seqlens), which would be the A/B for this. Wrong if: `conv` bucket is < 2% of GPU time in the baseline profile.
5. **Host syncs (`sync_free`)  expected 1-3%, SUGGESTED.** Per micro-batch: 3 boolean-mask gathers (`x[tm]` = nonzero = sync) and `float(part.detach())`; about 12 syncs per step, each leaves the GPU idle until
   Python relaunches. Replaced by CPU-built index tensors and one tensor sum read only when the curve is logged (every 10th step). Exact. Check `gpu_busy_frac` and `top_cpu_ops` in the profile: if the baseline's
   gpu_busy_frac is already ~0.97+, there is nothing to win here.
6. **`use_cache=False` (always on in the fast step)  expected <1%, SUGGESTED.** The baseline's `m.model(...)` builds a DynamicCache in training (shown on the tiny model: past_key_values is a DynamicCache), so each GDN
   layer runs fla with `output_final_state=True` and copies conv/recurrent state, and the 10 attention layers keep K/V alive. Same outputs.
7. **LoRA overhead, 310 modules (UNTESTED, look first in the profile).** peft keeps LoRA weights fp32 so every adapter call casts x to fp32 (several modules share an input) and runs two tiny fp32 GEMMs;
   ~4k small kernels fwd+bwd per step. If the profile shows `kernels_per_step` in the tens of thousands with `gpu_busy_frac` well below 1, the step is launch-bound and the fix is fewer kernels (bf16 LoRA weights, fused q/k/v adapters), not faster kernels.
8. **Cross-entropy / fp32 logits / chunked or fused CE (Liger-style)  < 1%, SHOWN by arithmetic.** Only target rows hit lm_head: ~300 CE rows + ~280 KL rows x 248k. lm_head fwd+bwd ~ 1.2 TFLOP = 2-3 ms; log_softmax x2 +
   kl_div ~ 70M elements x few passes = 2-5 ms. A fused kernel would save memory (~1.5 GB transient), not time. Not implemented.
9. **Bigger budget once packed (UNTESTED).** 4096 padded tokens needs checkpointing today (2.34 s). A packed step has ~2250 real tokens, so budget 2048-2560 holds it in 1-2 bins without checkpointing; `--extra-budgets 4096`
   shows whether larger forwards amortize the 256-expert grouped GEMMs better. Not in the list above: fla's `repeat_interleave`-free GVA call (q,k 16 -> 32 heads copies, ~1%), fused AdamW (<1%), router (not worth it).

Stacking (rough, not additive): packed + kl_cache + sync_free + use_cache=False ~ 28-35% less per step; with fused_norms and fla_conv maybe 35-45% (SUGGESTED / UNTESTED). Training is ~80% of a 4.6 h arm, so 30% of the step is ~24% of the arm (~1.1 h).

## Order to land (one change at a time, as in CLAUDE.md)
1. `--variants baseline,sync_free,kl_cache` (exact-math; marks above), then `baseline,packed` (largest, needs the fla kernels to pass parity), then `fla_conv`, `fused_norms`. `all` is only a final check.
2. A fix lands only if parity passes AND s/step falls by at least half its expected value; otherwise leave it opt-in/off. To use in a real run: `import fast_step; fast_step.install(sleepb, ...)` before the nights start (e.g. from a
   wrapper script; sleepb.py itself is unchanged). `--bench-train`/selftest of sleepb are unaffected with everything off.
## Open risks
- fla varlen GDN + Triton conv have never run in this container (no GPU/Triton): the first GPU run decides. If `chunk_gated_delta_rule` with `cu_seqlens` rejects the HF call, the error will show in the packed row of the JSON.
- Packed attention mask is a [1,1,T,T] bool tensor per forward (T <= budget): fine at 2048-4096, not for 16k.
- Different micro-batch composition changes bf16 rounding, so loss curves will not be bit-equal to old runs even though the math is identical; do not mix old and new numbers inside one comparison of arms.

## Per-expert backward (found from the box 2 profile; the loop is in FORWARD and backward, and it is not a backward-formula problem)
SHOWN (source, torch v2.9.1; not run on a GPU here): `torch._grouped_mm` has a fast kernel only on sm90/sm100. `aten/src/ATen/native/cuda/Blas.cpp` `_grouped_mm_cuda`:
`use_fast_path = _scaled_mm_allowed_device(sm90_only=true, sm100_only=true) && bf16`; otherwise it calls `_grouped_mm_fallback` (`aten/src/ATen/native/GroupedMMUtils.h` lines 115-164), which does
`offs.cpu()` then, for each of the 256 experts, `offs_cpu[i].item()`, `mat_a.slice`, `out.slice`, `mat_b[i]`, `at::mm_out`. The RTX PRO 6000 is sm_120 (major 12), so every call takes the loop. That is
the select/slice/item/as_strided storm and the 16x16 cutlass tiles, all inside the 560 `aten::_grouped_mm` calls: 560 x 256 = 143,360 of the 151,653 mm. The autograd formula is fine
(`derivatives.yaml`: `_grouped_mm_mat1_backward` = one `_grouped_mm(grad, mat2^T, offs)`, and the weight grad is skipped for frozen weights), but that one call loops too. HF 5.20.2 `integrations/moe.py`
`_can_use_grouped_mm` returns True for CUDA >= 8.0 with torch 2.9, so it never reaches its own `grouped_mm_fallback` custom op (that one would be worse: backward computes the weight grad too).
So the earlier guess "backward-only" was wrong: forward (gate_up, down) and backward (grad_x) each loop; weights are frozen so there is no weight-grad loop.
Fix, opt-in: `fast_experts.py` (`fast_step.install(sb, fast_experts=True)`, variants `fast_experts`, `kl_cache+fast_experts` in `profile_step.py`). It patches `transformers.integrations.moe._grouped_mm`
with one Triton grouped-GEMM launch (tile -> expert found from offs by an in-kernel cumsum, no host sync, strides passed so `weight.transpose(-2,-1)` is read in place, fp32 accumulate) and a
`torch.autograd.Function` whose backward is `gmm(grad, W^T, offs)` with no weight grad. A weight that requires grad, or a non-CUDA tensor, takes the original path.
CPU results (SHOWN, `test_fast_experts.py`, tiny Qwen3.5-MoE, fp32, experts grouped_mm, Triton run by its CPU interpreter, 2 steps, max|grad| 0.049): vs the original path, per-expert-loop backend CE 0 / KL 0 / grad 0;
Triton backend CE 0 / KL 2.3e-9 / grad 1.5e-8; with kl_cache CE 4.8e-7 / KL 2.6e-9 / grad 2.6e-8 (all within 1e-5 x max|grad|; the 1e-6 target is met on loss, grads are 3e-7 relative). aten::mm per step on CPU:
original 732, loop-structure backend 732, Triton backend 412 (the expert mms are gone; the rest are LoRA/attention/lm_head). `aten::item` 369 -> 49. Unit test (random, empty experts, transposed weights, sentinel tail): 7.6e-6 abs on values ~5 (fp32 order).
NOT shown: the Triton kernel has never been compiled for sm_120 or timed (interpreter only here); the CPU mm counts only show structure.
SUGGESTED saving: of the 1.457 s step, 1.02 s of GPU is the mm loop and most of the 63% idle time is the ~530k tiny launches/CPU ops; bandwidth arithmetic for streaming the active expert weights is ~0.1-0.2 s per step
(40 layers x 3 matrices x 256 x 2048 x 512 x 2 B ~ 32 GB per forward-equivalent, ~7 forward-equivalents, at ~1.5 TB/s). So a plausible step is 0.5-0.8 s (-45% to -65%); a kernel at half of bandwidth still wins big.
Pass marks, fixed in advance: parity row passes (CE rel diff < 1e-2, KL < 5e-2, grad cosine > 0.99; expect ~1e-3 or better since only accumulation order changes) AND median s/step <= 0.85 x baseline median.
Proven wrong if: parity fails, or `aten::mm` calls/step in the profile do not fall below ~10k, or the median saving is under 15% (then something else, e.g. CPU launch cost elsewhere, dominates).
UNTESTED: tile sizes (BM 64 / BN 128 / BK 64 are a guess; ~100 rows per expert on average, so BM=32 or autotune may be better), a persistent/swizzled variant, torch 2.10's `F.grouped_mm` (may have an sm_120 path), and fp8.
Run: `python speed/qwen36_step/profile_step.py --layers 8 --variants baseline,fast_experts,kl_cache+fast_experts --no-profile-variants` (defaults are now `--steps 4 --warmup 2`; mean and median reported; the
profiler pass runs for the baseline only with `--no-profile-variants`, profile `fast_experts` once separately without it to confirm the mm count). Needs `triton` importable (ships with torch cu128).
