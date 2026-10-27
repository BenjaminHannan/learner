# Faster LoRA training on Kaggle T4 x2 (research notes)

Date: 2026-10-25. Scope: Qwen3.5-2B (Gated DeltaNet) and K2-Horizon-3.7B (dense GQA, 250k vocab) LoRA on T4 (sm_75, fp16 tensor cores, no bf16).

Labels: **shown** = measured by someone, with a cited link. **suggested** = reasoned from general knowledge, not checked here. **untested** = nobody has measured it on this setup; needs a run.

Baseline from the repo: 6.5 s/step at 1024 tokens (Qwen3.5-2B, fp16, after the target-positions-only lm_head patch). 4096 tokens OOMs.

Research gaps: the search tools returned few primary sources. The PyTorch AMP, SDPA and backends pages redirected and their content could not be read. No T4 benchmark was found for fla, SDPA, bitsandbytes, torch.compile or DDP. Almost everything below is therefore suggested or untested.

## Ranked changes

1. **Keep the RMSNorm sum-of-squares in fp32 (fp16 overflow guard).** Expected: avoids NaN/loss blow-ups; enables fp16 at all. Label: **shown** for the mechanism. Evidence: SLaNC (arXiv 2410.10553) finds that fp16 accumulation of sum-of-squares overflows often and sharply degrades Llama perplexity. A community Qwen3.5-2B FP16 card reports keeping norm layers in FP32 on Colab T4 for stability (anecdote, not measured). Check against the repo's Qwen3.5 forward.

2. **fp16 AMP with fp32 master LoRA weights and GradScaler.** Expected: the base for every other speed change; no direct speedup number. Label: **suggested** (standard AMP practice). Keep LoRA parameters and optimizer state in fp32, use `torch.autocast(dtype=torch.float16)` plus `GradScaler`, and unscale before clipping. Keep softmax, norm and loss in fp32. Do not use bf16 on T4: a Kaggle forum thread notes T4 (Turing) lacks the tf32/bf16 path and recommends fp16 (**shown**, anecdote: https://discuss.huggingface.co/t/qlora-fine-tuning-is-too-slow-on-llama-based-model-despite-bitsandbytes-optimization/166964).

3. **Fused / chunked linear cross-entropy (biggest memory lever for 250k vocab).** Expected: memory roughly halved at large batch; this is what makes a bigger token budget fit. Label: **shown** for memory. Evidence: PyTorch blog (torchtune + Liger, A100, Llama-3.2-1B) reports 47% lower peak memory at batch 256, with a 1-2% throughput change, and no loss-curve change (https://pytorch.org/blog/peak-performance-minimized-memory/). The blog also gives the logit size: 8 x 4096 x 256k ≈ 16.8 GB. Your target-positions-only lm_head patch already attacks the same cost; a chunked loss may let you go past 1024 tokens. Speed effect on T4: **untested**.

4. **Attention backend: SDPA memory-efficient kernel on sm_75.** Expected: unknown; it is the only option without FlashAttention-2 (which needs Ampere+). Label: **untested**. Evidence on sm_75 support was not found. Test with `torch.nn.attention.sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION)` in fp16 and see whether it raises. Note that the "flash" backend does not run on T4.

5. **Gated DeltaNet kernels (flash-linear-attention, fla).** Expected: if the fla Triton kernels run, large speedup over the pure-PyTorch recurrence; if not, a fallback to torch code will be the bottleneck. Label: **untested**. Evidence: fla's README says the implementations are "verified on NVIDIA, AMD, and Intel," but gives no compute-capability floor and its examples use bf16 (https://github.com/fla-org/flash-linear-attention). Triton does target sm_75 in general (**suggested**). Check: does `chunk_gated_delta_rule` run with fp16 inputs on T4, and do its outputs match the torch reference within fp16 tolerance? Check for NaNs across a full run.

6. **Gradient checkpointing (trade compute for memory).** Expected: costs roughly one extra forward per layer (about 25-35% slower step, **suggested**); lets you raise the token budget. Use it only if the budget gain beats the cost. Label: **suggested**. No T4 timing was found.

7. **Two independent arms, one per T4, instead of DDP.** Expected: about 2x total experiment throughput with no gradient all-reduce. Label: **suggested**. Reason: Kaggle T4s communicate over PCIe, so DDP sync costs are unmeasured. Use DDP only when one run needs both GPUs to fit. Check on the actual hardware.

8. **torch.compile.** Expected: up to ~30% on vision inference per a Hugging Face doc, and compile time is paid per run (https://huggingface.co/docs/transformers/perf_torch_compile). Label: **untested** for T4 LoRA training. Risk: custom Triton (fla) kernels and dynamic shapes may break or recompile. Try once with a fixed token length.

9. **4-bit frozen base via bitsandbytes (QLoRA).** Expected: lower memory, which allows larger budgets; usually slower per step because of dequantization. Label: **suggested** for the trade-off, **untested** on T4 speed. Set `bnb_4bit_compute_dtype=torch.float16` (the HF docs example uses bf16: https://huggingface.co/docs/transformers/quantization/bitsandbytes). Do not use if the 2B model already fits in fp16.

10. **8-bit AdamW for LoRA.** Expected: negligible. Label: **suggested**. LoRA optimizer state is tiny; use plain fp32 AdamW.

11. **Unsloth on T4 for these models.** Expected: possibly faster kernels, but unclear coverage. Label: **shown** for changelog entries only. Unsloth changelog: 2026-03-25 "Colab with free T4 GPUs ... now fixed"; 2026-04-08 "Fix Qwen3.5 and Gemma 4 training issues" and "Fixed float16 audio overflow" (https://unsloth.ai/docs/new/changelog). No entry covers Gated DeltaNet on T4 or K2-Horizon. Evaluate only if your own patched code can't be sped up another way.

## What to test first (one change at a time)

- Pass mark for each: the same loss curve within noise for 200 steps, no NaNs, and step time at or below 6.5 s for 1024 tokens (or more tokens for the same time).
- Failure: any NaN, or a loss gap bigger than the run-to-run spread, means the change is rejected.
- Order: (1) fp32 RMSNorm check, (2) fla kernel check on T4, (3) chunked CE for budget, (4) SDPA backend check, (5) compile, (6) checkpointing.

## Plain-language summary for Ben

1. T4 cards are old: they have fast fp16 but no bf16, so every run must use fp16 with a guard on the math that can overflow.
2. The biggest proven win is a memory fix: the vocabulary logits (250k entries per token) eat most of the memory, and a chunked loss cut peak memory by 47% in a published test.
3. Two separate experiments on two T4s is probably simpler and faster than splitting one model across them.
4. Several speedups are only guesses until we run them on a T4; the notes mark each one.
5. Test one change at a time, and throw it out if the loss curve moves or NaNs show up.
