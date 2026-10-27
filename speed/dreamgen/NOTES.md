# dreamgen: faster sleep-night generation (opt-in, nothing in backbone/ touched)

Labels: SHOWN = measured/checked here (CPU test or code read). SUGGESTED = arithmetic from the Qwen3.6 RTX PRO 6000 bench numbers. UNTESTED = needs the GPU.

## Where the time is (SHOWN, from results_a11 moebench estimate, typical 0.6 length, 7 nights, 15466 s)
tag_names_detect 427 s, dream_generate 775, dream_verify 1008, rem_generate 335, rem_verify 126 = ~2670 s generation (17%) + probes ~200.
Bench decode is ~250-300 new tok/s at bs 32/64/128 (flat), so a decode step costs ~ rows x 3.5 ms: dead rows (finished, still stepped) are paid in full.
Brain.gen -> Lang.generate -> HF generate: it stops only when ALL rows hit EOS, the batch is sorted by prompt chars only, nothing else is reused.
Call shapes (sleepb.py): tag 160 new greedy (~220 tok prompt); names 12/256; detect 8; dream sampled 400 x scale (~450 tok); verify 20 greedy (~420 tok, ~4-8 questions share one diary ctx);
REM 40 sampled; probe generate_p 20. bench_gen rows force min_new = max_new, so its numbers are the worst case; real replies stop early.

## Ranking (seconds saved per week-run of 7 nights; per night = /7)
| # | idea | est. saved | status |
|---|------|-----------|--------|
| 1 | row compaction: drop finished rows from batch+cache every `seg`=8 tokens (fastgen.compact) | dream ~200-300, verify ~150-400, tag ~100, rem ~60: **~500-800 s/week (3-5%)** | CPU-proven exact (greedy, Qwen3_5Moe + dense, LoRA on/off, eos list, generate_p); gain SUGGESTED, gpu_bench measures it |
| 2 | CUDA graphs / HF static cache + compile for decode | bench step 0.07 s at bs32 looks launch-bound: 2x decode would save ~800-1300 s/week | UNTESTED; gpu_bench --try-static times it; MoE grouped_mm + compile may fail |
| 3 | shared-prefix reuse for verify/dream (ctx_prompt: ~400 of 420 tokens shared by 4-8 prompts) | prefill is ~30% of verify: ~200-250 s/week | SUGGESTED, not built: left-padded batches need equal suffix lengths per group or per-row suffix prefill; DeltaNet state copies fine via cache.reorder_cache(repeated idx) |
| 4 | pad_multiple=64 (fastgen option) | bench prefill is a ~6 s constant for 7k-57k tokens: if it is a per-shape JIT/autotune, up to ~120-240 s/night; else 0 | UNTESTED; gpu_bench shape_probe shows it (same shape x3 vs fresh lengths) |
| 5 | dedupe identical greedy prompts (fastgen.dedupe) | <=10% of verify: ~50-100 s | SHOWN exact on CPU; gain SUGGESTED |
| 6 | vLLM for generation phases | 5-10x decode: ~2000 s/week net of reloading ~65 GB weights each night | UNTESTED, big restructure: needs GPU memory for both engines (96 GB card: no), LoRA support for GDN in_proj_qkv/out_proj + shared expert unknown. Not recommended before 1-4 |
| 7 | transformers 5.20.2 generate_batch / ContinuousBatchingManager | would give true refill | SHOWN not usable: grep of generation/continuous_batching/ has no linear-attention (DeltaNet) state handling, only full/sliding |
| 8 | merged vs unmerged LoRA in generation | base phases already run adapter-off (zero LoRA cost); only probes/final scoring run adapter-on: <30 s/week, and merging changes bf16 values | not worth it |
| 9 | token-length sort, bigger gen_bs | step cost is ~linear in rows: ~0 | dropped |

## What is implemented
- `fastgen.py`: `install(sleepb, compact=True, seg=8, dedupe=True, pad_multiple=1)` patches `sleep1.Lang.generate` and `sleepb.generate_p`; `uninstall()` restores. Falls back to the original for non-HF stubs and models with cached rope_deltas.
  Mechanism: generate() in segments of `seg` tokens via the same HF call, cache handed on; after a segment, rows with an end id leave the batch, `seq`, mask and cache (`Cache.reorder_cache`, which index_selects KV and DeltaNet conv/recurrent state). Output per row = tokens to its first end id, then pad to the longest row, exactly as HF returns.
  Greedy = same tokens (float noise only from a different batch size; bf16 near-ties could flip a few, gpu_bench reports `same_as_base`). Sampling = same per-row distribution (same warpers), other RNG stream.
- `run_sleepb_fast.py`: wrapper that installs fastgen then runs sleepb.main() with the usual args (env FASTGEN_SEG/PAD/DEDUPE). Default off: plain sleepb.py is untouched.
- `test_fastgen.py` (CPU, ~1 min, 1 thread): tiny random Qwen3_5Moe and Qwen3_5, LoRA on/off/adapter-disabled, eos list, bs 3/8, dup prompts, pad_multiple 8: identical outputs and p_first; sampling with one segment is bit-identical under a seed. Row-steps drop 25% (MoE) / 42% (dense) on the tiny random model.
- `gpu_bench.py`: phases tag/dream/verify/rem/probe x variants base | compact | compact_pad64 | compact_seg16 -> one JSON (seconds, tok/s, row-steps, same_as_base, shape_probe, optional static_compile).

## Pass marks for the lead (fixed in advance)
Keep compaction if: greedy same_as_base >= 0.97 on every phase AND dream/tag speedup >= 1.15 AND no phase slower than 0.97x. Keep pad64 only if shape_probe fresh-length prefill is >= 2x the repeated-shape prefill and compact_pad64 beats compact by >= 5%. Falsified if compact is not faster on dream (then decode is not row-linear on this box).
