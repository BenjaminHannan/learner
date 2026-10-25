# Swap-1 results (in progress, 2026-10-25)

Labels: shown = measured here; suggested = vendor or third-party claim.

## Store test, GPU (vLLM 0.32 bf16 on an RTX 5090, tau2 retail tasks 0-39 x 2 trials, Haiku 5.5 as customer and judge), shown
| arm | DB match /80 | reward pass /80 | agent tokens/sim | s/sim | ended by errors |
|---|---|---|---|---|---|
| K2-Horizon-3.7B, thinking off | 56 | 51 | 2025 | 41 | 0 |
| K2-Horizon-7B, thinking off | 55 | 49 | 1832 | 46 | 0 |
| K2-Horizon-7B, reasoning_effort low | 50 | 44 | 1881 | 55 | 0 |
| K2-Horizon-3.7B, reasoning_effort low | 46 | 40 | 2094 | 45 | 1 |
The LFM2.5-8B-A1B control didn't start on vLLM 0.32 ("Layer 0 (conv) does not dispatch through the Transformers attention interface"),
so the pre-registered same-stack control is missing. The Qwen3.5-4B/9B arms failed after it (GPU memory not freed; serve() fixed since).
Earlier Mac runs of LFM2.5-8B scored 14/40 (bf16), 19/40 (q4) and 23/40 (q8), each 1 trial, on mlx_lm.
P1 (K2 >= LFM + 10 points) holds against every LFM run, but only across stacks, so it is suggested, not shown, until the Mac q4 run of K2-3.7B.
Short thinking (low) did not help either K2 size.

## Speed on Ben's M1 Pro, MLX 4-bit, tok/s each at 1 / 2 / 4 agents, shown
| model | 1 | 2 | 4 | TTFT 1k / 4k | peak GB |
|---|---|---|---|---|---|
| Qwen3.6-35B-A3B | 47.1 | 30.1 | 17.4 | 2.5 / 9.6 s | 21.5 |
| K2-Horizon-3.7B | 35.9 | 30.1 | 15.9 | 3.0 / 13.0 s | 5.5 |
| K2-Horizon-7B | 23.9 | 18.4 | 10.3 | 5.4 / 22.9 s | 8.5 |
| K2-Horizon MoVA 36B-A4B | 16.8 | 13.4 | 8.8 | 4.2 / 17.5 s | 28.1 |
| LFM2.5-8B-A1B (Oct 24) | 108 | 67 | 38 | ~5 s at 4k | 4.5 |
MoVA's store test was stopped at 0/80 (OOM at 2 agents, >10 h at 1).

## Decision (Ben, 13:40Z / 13:43Z)
Big tier: Qwen3.6-35B-A3B. Small tier: K2-Horizon-3.7B. Pivot if something better ships before release.

## Qwen3.6-35B-A3B vs Qwen3.8-27B on Vast Blackwell (Oct 25, did not finish)
- vLLM 0.32.0 on sm_120 (RTX 5090 / RTX PRO 6000) in the pytorch cu12.8 image: AWQ, NVFP4 and the default bf16 MoE path all fail with "No supported CUDA architectures found for major versions [12]". The cause is FlashInfer JIT (CUTLASS fused MoE) needing nvcc >= 12.9 for SM 12.x.
- `--moe-backend triton --gdn-prefill-backend triton --max-num-seqs 32` serves, and tool calls parse, but it is unusably slow: 35B ~1000 s per sim (4/4 DB match in 25 min, too few to mean anything), and the 27B smoke took 80 s for 57 tokens. The box was destroyed.
- Next time: use an image with CUDA >= 12.9 (e.g. vllm/vllm-openai, which ships prebuilt kernels) or an sm_80/90 GPU. Or run the 27B on Ben's PC via llama.cpp (GGUF already there).
- Vast spend for the whole swap thread: about $2.7 of the $3.50 cap.

## Caveats (bug-hunt review, Oct 25)
- P1 passes by one sim: K2-7B no-think scored 55/80 (68.75%) against a bar of 67.5%. The 95% CI is about ±10 points, and the same-stack LFM control never ran (vLLM can't serve LFM2.5's conv layers). Read it as "about as good as or better than LFM", not as a clear win.
- The headline metric is db_match. reward_pass (49/80 for K2-7B) also penalises leaked planning text.
- Output caps differ by arm: 16,384 tokens for thinking arms, 4,096 for no-think arms. Length stops are not logged.
- serve() falls back to --model-impl transformers without recording it. Check for vllm_native.log in each arm dir.

## Mac M1 Pro 32 GB, Qwen3.6-35B-A3B variants (Oct 25 evening, thinking off, 300 new tokens)
tok/s per agent (total) at 1 / 2 / 4 agents; TTFT at ~1.2k / ~4.9k prompt tokens
| variant | 1 | 2 | 4 | TTFT | memory |
|---|---|---|---|---|---|
| MLX 4-bit (mlx_lm) | 47.1 | 30.1 (60) | 17.4 (70) | 2.5 / 9.6 s | 20-21.5 GB |
| REAP-19B, optiq serve default | 35 | 17 (35) | 8.7 (35) | 3.0 / 11.9 s | 12.5 GB |
| REAP-19B, OPTIQ_BATCH_HYBRID=1 | 34.5 | 25.6 (50) | 15.2 (59) | 3.1 / 12.1 s | 12.5 GB |
| llama.cpp UD-Q3_K_M | 39.0 | 25.9 (50) | 16.9 (65) | 2.7 / 10.7 s | ~17 GB |
- OptiQ-4bit (± MTP) and llama.cpp Q4_K_M don't fit: 22-26 GB at load, memory pressure warn, killed by the watchdog.
- REAP MTP fails: the main model is pruned to 128 experts but the MTP head still has 256. REAP's sanity answer was slightly wrong.
- Verdict: plain MLX 4-bit stays the big-tier serving format. REAP-19B (12.5 GB) is the fallback for 16-24 GB Macs, but its quality is unmeasured.
