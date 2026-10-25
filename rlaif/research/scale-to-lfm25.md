# Scaling RLAIF-1 to LFM2.5-24B-A2B (research, 2026-10-24)

Labels: SHOWN = stated on the cited page. SUGGESTED = my inference or arithmetic from shown facts. UNTESTED = nobody (incl. us) has verified it.
Method note: web search/fetch only, no runs. Cost rule limited fetching (no subagents available to me), so several items are UNTESTED, not checked.
Scope: small-card experiments and the village model are not covered here; this is only the RLAIF-1 pipeline.

## 0. Facts about the model
- SHOWN: LFM2.5-24B-A2B, 24.0B total / 2.45B active, 40 layers = 30 double-gated short-conv + 10 GQA attention, 64 experts/MoE block, top-4, 131k ctx. https://huggingface.co/LiquidAI/LFM2.5-24B-A2B
- SHOWN: the card calls it "a pure reasoning model that always thinks before it answers"; chat template adds `<think>`; no toggle documented. Same URL.
  - FLAG: our plan says "thinking off". That is UNTESTED for this checkpoint. Check the template; if it cannot be turned off, rollouts are much longer (cost x3-10, SUGGESTED) and the Qwen3-1.7B thinking-off result transfers less.
- SHOWN: Liquid lists TRL recipes (LoRA SFT, DPO, GRPO) and Unsloth (CPT, LoRA SFT) for it; a Base variant exists for fine-tuning. Same URL.
- SHOWN: needs transformers>=5.0 (the 2.0 card says >=5.2). https://docs.liquid.ai/lfm/models/lfm2-24b-a2b
- SHOWN: Liquid says the older LFM2-24B-A2B is deprecated in favour of 2.5 (same page).

## 1. Can it be LoRA-trained, and where?
Weights memory (SUGGESTED, params x bytes, ignoring activations/KV): bf16 ~48 GB; 8-bit ~24 GB; 4-bit ~13-14 GB. SHOWN: LM Studio lists 14 GB RAM minimum for smallest quant of the 24B and Liquid says it is designed to fit 32 GB. https://www.lmstudio.ai/models/lfm2-24b-a2b ; https://www.mindstudio.ai/blog/lfm2-5-24b-a2b-local

PEFT/Unsloth on MoE:
- SHOWN: Unsloth advises against 4-bit QLoRA for MoE (bitsandbytes limitation); use bf16 LoRA. Qwen3-30B-A3B 16-bit LoRA = 63 GB. https://unsloth.ai/docs/basics/faster-moe
- SHOWN: in transformers v5 expert weights are one nn.Parameter (gate_up_proj, down_proj); plain PEFT builds a full merged delta (memory heavy); Unsloth "Split LoRA" avoids that. Router is not trained by default. Same URL.
- SHOWN: that Unsloth page does not list LFM; Liquid's Unsloth page shows only dense LFM2.5-1.2B with q/k/v/o + gate/up/down and `load_in_4bit`; says nothing on conv layers or MoE. https://docs.liquid.ai/lfm/fine-tuning/unsloth
- SUGGESTED: the safe LoRA target set is attention + conv in/out projections + shared/dense MLP, with experts frozen. Expert LoRA is the risky part.
- UNTESTED: any PEFT/Unsloth LoRA run on lfm2_moe; QLoRA on its conv layers; expert LoRA.
- SHOWN: mlx-lm has `lfm2.py` and `lfm2_moe.py` model files. https://github.com/ml-explore/mlx-lm/tree/main/mlx_lm/models . UNTESTED: that mlx-lm's LoRA trainer works on them, and its peak memory (no source found).

Where (feasibility; throughput numbers below are SUGGESTED estimates, all UNTESTED):
| Hardware | Fits? | RL throughput guess |
|---|---|---|
| M1 Pro 32 GB, MLX | 4-bit 14 GB weights + LoRA grads + KV: tight but plausible for short contexts. UNTESTED | Our measured 54 tok/s single stream. An episode of ~1,500 generated tokens ~30 s, so ~120 episodes/h unbatched; batched mlx-lm decode could give a few x. A 64-episode GRPO step ~30+ min plus the train pass. ~2 steps/h, i.e. a smoke test, not a campaign |
| 2x T4 (16 GB each, fp16, no bf16) | 4-bit weights fit on one card for inference only. bf16 LoRA impossible; MoE QLoRA unsupported (see Unsloth). | Not viable for the 24B training. Fine for Qwen3-1.7B/4B and LFM2-2.6B-class |
| 1x RTX 4090 24 GB | 4-bit inference fits; bf16 LoRA (~50+ GB) does not; QLoRA-on-MoE unsupported | Rollout-only box (vLLM FP8/4-bit), not trainer |
| A100/H100 80 GB | bf16 48 GB weights + LoRA + KV: fits at modest context. SUGGESTED | vLLM decode on 2.45B-active MoE is fast; guess ~10-40 episodes/min, i.e. 600-2,400/h. UNTESTED. Liquid reports 21k output tok/s on a B300: https://www.mindstudio.ai/blog/lfm2-5-24b-a2b-local |

Prices: Vast A100 80GB reported $0.67/h (one aggregator) up to ~$1.9; H100 $0.90-1.87 on Vast per one review, $2-4 elsewhere; 4090 spot ~$0.30/h but interruptible. Sources disagree and are snapshots: https://vantaige.io/es/ai-tool/vast-ai ; https://jarvislabs.ai/blog/a100-price ; https://io.net/p/rent-nvidia-gpus-for-ai-h100-a100-and-rtx-4090-pricing-comparison . Check live Vast listings before budgeting.
Conclusion (SUGGESTED): on our hardware the 24B can only be LoRA-trained (bf16) on a rented 80 GB card; the Mac is a smoke-test/inference target, the T4s and 4090 cannot train it.

## 2. Rollout generation and weight sync
- SHOWN: vLLM supports LFM2.5 (pip install vllm; no minimum version stated); SGLang supports LFM2.5 incl. 24B-A2B natively, CUDA only, `--tool-call-parser lfm2`; llama.cpp (GGUF) and MLX (4-bit/8-bit builds) exist; FP8 checkpoint for vLLM/SGLang. https://huggingface.co/LiquidAI/LFM2.5-24B-A2B ; https://docs.liquid.ai/docs/inference/sglang ; https://docs.liquid.ai/lfm/models/lfm2-24b-a2b
- SHOWN: Liquid reports 184 tok/s on an M5 Max with MLX; our measured M1 Pro is 54 tok/s (ours). https://www.mindstudio.ai/blog/lfm2-5-24b-a2b-local
- SHOWN: SGLang page says nothing on LoRA or weight update for RL. https://docs.liquid.ai/docs/inference/sglang
- SHOWN: vLLM has an RL weight-transfer API (init once, update per step, NCCL for separate GPUs). https://docs.vllm.ai/en/stable/training/weight_transfer/
- SHOWN: vLLM can load LoRA at runtime (`--enable-lora`, VLLM_ALLOW_RUNTIME_LORA_UPDATING, /v1/load_lora_adapter). https://unsloth.ai/docs/de/grundlagen/inference-and-deployment/vllm-guide/lora-hot-swapping-guide
- SHOWN (secondary): TRL's AsyncGRPOTrainer can sync only the LoRA adapter to vLLM (PR #7017); TRL GRPOTrainer supports vllm colocate/server modes. https://prismix.dev/news/85052f9befba
- UNTESTED: vLLM's LoRA path on lfm2_moe (LoRA kernels for fused experts/conv layers may be missing; a LoRA on attention+conv only may not be loadable). Fallback that surely works (SUGGESTED): merge the adapter into bf16 weights and reload/sync full weights each step; ~48 GB over local NVLink/PCIe is slow, so sync every N steps (off-policy by N) or use the weight-transfer API.
- Our pipeline today uses HF generate with the same model (SHOWN: rlaif/train.py, rollout.py). For 24B that is too slow; replacing the sampler with a vLLM/SGLang server speaking OpenAI tools format is the main code change (SUGGESTED).
- Loop-1L (looped middle layers) will not exist in vLLM/SGLang/MLX; sampling a looped model needs the HF path or a custom port (SUGGESTED). This favours doing the loop experiments at 1.7B-4B, not 24B.

## 3. Staged plan (all SUGGESTED, costs UNTESTED estimates)
Stage 0 (now, $0): finish Qwen3-1.7B GRPO vs JOLT+ against the preregistered marks in rlaif/SPEC.md. No scale-up until "RL works" (>= +10 pts held-out) is met by either arm.
Stage 1 (free, 1 night on Kaggle 2x T4 or 5070 Ti): same pipeline on LFM2.5-1.2B-Instruct (dense, SHOWN Unsloth-supported) or the 1.2B/2.6B LFM2-class dense model. Purpose: check the LFM conv+attention architecture trains with LoRA at all, and read the tool-call format. Cost $0, ~8-20 h.
Stage 2 (~$5-15, Vast 4090 or the 5070 Ti): Qwen3-4B or LFM dense 2.6B with vLLM sampler + TRL; practise the sampler/weight-sync path that the 24B needs. Check whether gains grow with size.
Stage 3, the cheapest go/no-go for the 24B (~$3-8): rent one 80 GB card ~3-5 h at ~$1-2/h.
  1. Baseline only: sample 100 held-out tasks greedy, no training (30-60 min, mostly model download). Pass mark fixed ahead: if base success is >= 85% there is no headroom, stop; if < 5%, RL signal is too sparse, add SFT/format first.
  2. Else 20-30 GRPO steps, LoRA on attention+conv only, 8 tasks x 8 samples. Pass mark: held-out success +5 pts over baseline (half the +10 mark, because the run is short) with no Sonnet-score gaming alarm. Proved wrong: held-out drops below baseline, or LoRA will not load/train on lfm2_moe (that alone is a useful answer).
  Even before renting, a ~free Mac check (SUGGESTED): `mlx_lm.lora` for 20 iterations on the 4-bit MLX build to see if it runs and its peak memory (UNTESTED; this is the real cheapest test of "can the Mac train it at all").
Stage 4 (only if Stage 3 passes, ~$30-50): 150-300 steps on the 80 GB card with a vLLM sampler. Then bring the adapter to the Mac for inference.
Open check before any 24B spend: thinking cannot be disabled? (section 0). If so, add the token cost and prefer training with thinking on.

## 4. What I did not verify
Layer-level LoRA module names for lfm2_moe; actual mlx-lm LoRA memory; vLLM/SGLang minimum versions for the 24B; Vast live prices; any real 24B RL throughput (all rows in section 1 are my estimates).

## Lead check (2026-10-24)

- Point 2 ("always thinks"): the project already ran LFM2.5-24B-A2B on tau2 retail with thinking off (23/40 vs 30/40 on, gaps/scoreboard1 harness), so an off switch exists in practice; confirm it is the same mechanism before RL rollouts.
- The Opus advisor check was not run (no Agent tool in this helper); the staged plan is unreviewed.
