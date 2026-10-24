# Research: own draft head for LFM2.5 on M1 Pro (2026-10-24)

Labels: **shown** = a paper/post measured it; **suggested** = reasoned or claimed by a secondary source; **untested** = nobody has measured it for our setup.
Caveat: web search snippets only. I did not read most papers in full. Check numbers before acting.

## Summary for Ben (plain language)
1. A "draft head" is a tiny add-on that guesses the next few words so the big model can check them all at once.
2. On GPUs this gives 2-3x speed. On a Mac the gain is much smaller, because checking extra words still costs real time.
3. The one public Mac test of this idea (EAGLE-3 on MLX) got only 1.05x. Our model is bigger and slower per word, so we may do better, but nobody has shown it.
4. Our model has MoE (a pool of "expert" sub-networks), and checking several words wakes extra experts, which eats the gain.
5. So: first run a cheap test that tells us if it is worth building, before we train anything.

## 1. Which method, and does MoE hurt
- EAGLE family (draft from backbone hidden states): shown, EAGLE-1 on Vicuna-13B about 3x, acceptance length (tau) about 4 on GPU. [EAGLE](https://arxiv.org/pdf/2401.15077)
- Medusa: shown, about 2.0-2.4x, tau about 2.0-2.6 on Vicuna-7B in a third-party table; EAGLE self-reports 1.5-1.6x faster than Medusa. [DEER comparison](https://arxiv.org/pdf/2512.15176)
- Hydra (sequential heads): suggested better than Medusa, costs more to train. Same DEER source.
- EAGLE-3: claimed up to 6.5x, about 1.4x over EAGLE-2 (paper); 2-3x typical when acceptance per token is 0.6-0.8 (blogs, suggested). [Kaitchup](https://kaitchup.substack.com/p/eagle-3-speculators-when-to-use-them)
- All of these are CUDA numbers. None are for a 1-2B-active MoE at batch 1. Untested for us.
- MoE hurts: shown. Verifying K tokens activates more experts; Mixtral K=7 moved roughly 3x more expert data; slowdowns up to 1.5x; K=3 gave +39% on code but -54% on math. [Cascade](https://arxiv.org/pdf/2506.20675)
- Mitigations: cap experts during verify (MoE-Spec, +10-30% over EAGLE-3) [link](https://arxiv.org/abs/2602.16052); pick drafts that reuse experts (EcoSpec, up to 1.62x on huge MoEs) [link](https://www.alphaxiv.org/abs/2607.12696). Both shown on big MoEs only.
- Counterpoint: a NeurIPS 2026 poster says fine-grained MoEs gain more at low batch. Read before relying on it. [link](https://neurips.cc/virtual/2026/poster/150811) LFM2 MoE is fine-grained (many small experts), so expert overlap between adjacent tokens is the key unknown. Untested.
- Our backbone is mostly ShortConv layers, so attention/KV cost is small; the weight bandwidth (experts) dominates. Suggested.

## 2. Cheap training, and LoRA
- Data: train on the backbone's own generations (prompts, then target-model outputs). Shown to matter: heads trained on other models' outputs misalign; regenerating with the target fixed acceptance (0.33 to 0.41; tau 2.7-3.0 for GLM-5.1). [Baseten](https://www.baseten.co/blog/how-to-train-custom-eagle-3-heads-for-speculative-decoding/), [GLM thread](https://huggingface.co/AQ-MedAI/GLM-5.1-eagle3/discussions/3), [Nanbeige](https://huggingface.co/NullSense/Nanbeige4.2-3B-EAGLE3)
- Sizes: I found no reliable number for tokens/steps. Original EAGLE used about 68k ShareGPT dialogues (from memory, unverified). Suggested starting point: 20-50k target-generated samples, one chain-head layer, under a few hours on M1 Pro (untested).
- Frozen-backbone head cost is small (one decoder layer plus LM head reuse). The DEER GPU-hour table (EAGLE-3 about 696h on Qwen3-8B) is for large-scale training, not our scale.
- After a LoRA update: no paper tests a small nightly LoRA. Sources say mismatch lowers acceptance and the fix is retrain/continue on regenerated data. Suggested: LoRA deltas are small, so the old head may keep most acceptance; fine-tune the old head for a short run rather than retrain from scratch. Untested; this is experiment 2.
- Joint head+LoRA training reported better acceptance (AFA-LoRA). [link](https://arxiv.org/pdf/2512.22455) Different setup; suggested.

## 3. Batched speculative decoding (2-4 streams)
- Shown (authors only, GPU): batch spec decoding is hard because accepted lengths differ per stream, forcing realignment (up to 40% of compute at batch 8). EXSpec reached 3x throughput at batch 8 vs batch 1. [paper](https://arxiv.org/html/2510.22876v2)
- On our hardware: batching streams already amortizes weight reads, and spec decoding does too, so they compete for the same slack. Suggested: for 2 streams, plain batching likely beats spec. Untested.
- mlx_lm.server turns batching off with a draft model (given). Pick one per request pattern. Suggested: spec for single-user latency, batching for throughput.

## 4. Existing MLX work
- EAGLE-3 port to MLX, Llama-3.1-8B 4-bit on M3 Ultra: acceptance 0.34, best 1.05x, fp16 draft 0.94x (slower). Chain only. Cost per extra verify token 0.5-1 ms; draft head about 0.4 ms. [mlx-lm #890](https://github.com/ml-explore/mlx-lm/discussions/890) Shown, but LLM-written and unverified.
- DFlash port [dflash-mlx](https://www.sourcepulse.org/projects/28031409), tree variant [ddtree-mlx](https://oosmetrics.com/repo/humanrouter/ddtree-mlx) (about 1.5x claimed), MTP heads [MTPLX](https://www.sourcepulse.org/projects/29507173). I did not open these repos. Suggested only.
- No Medusa or Hydra for MLX found. Does LFM2.5 ship an MTP head? Not found; do not assume.
- General: spec decoding on consumer Apple hardware slowed 3 of 5 configs; best 1.61x at K=6; quantized Metal kernels may run "parallel" verify serially. [Lossless but Not Free](https://arxiv.org/pdf/2607.17283) Shown.

## 5. Tree vs chain on Apple Silicon
- Nobody has measured tree on Apple Silicon (I found none). On CUDA, tree verify is nearly free; on Mac each extra token costs time, so trees likely pay off less. Suggested.
- mlx_lm KV cache uses one integer RoPE offset, which blocks tree masks (needs per-token position ids). #890 above. Shown as a blocker.
- For ShortConv layers a tree also needs per-branch conv state, which is harder than the chain fix. Suggested.
- With MoE, wider trees touch more experts. Suggested: start with chain, K=2-3.

## Recommended design (suggested)
- Chain drafting, K=3, one EAGLE-style head (1 layer, input: last hidden state plus next token embedding), 4-bit or bf16 to match the backbone.
- Conv-state fix: keep the last 2+K rows of the conv input and roll back to the accepted length. Exact.
- Adaptive K: turn drafting off when recent acceptance falls (Cascade idea).
- Retrain nightly by short fine-tune on the post-sleep model's own outputs; start from yesterday's head.
- Do NOT build tree drafting or batched spec first.

## First experiment: measure the ceiling before training (no head needed)
Cheap and no new training: use the 24B-A2B or 8B-A1B as target, and measure the cost of one verify step of K+1 tokens vs 1 token (forward pass with a K+1 token input, no cache trimming needed on a fresh prompt).
- Measure on 20 prompts: ms per forward with 1, 2, 3, 4 tokens.
- Break-even: with draft cost d (assume 0.4 ms) and per-token acceptance a, speedup = tau / (1 + (cost(K+1)-cost(1) + d)/cost(1)).
- **Pass mark (fixed now):** cost(4 tokens) <= 1.35 x cost(1 token) for 8B-A1B bf16 (41.7 tok/s means 24 ms/token). With that, tau >= 2.0 gives a projected speedup >= 1.4x, and we proceed to train a head.
- **Proves it wrong:** cost(4 tokens) > 1.6 x cost(1) (MoE expert cost eats the gain: needs tau > 3 for just 1.4x, unrealistic at batch 1). Then drop EAGLE for this MoE, or try the dense/less-sparse model, or expert-capped verify.
- Second experiment (only if passed): train the head on 20k self-generated samples; pass mark is mean accepted length >= 2.0 at K=3 on held-out prompts and measured end-to-end >= 1.3x. Third: after a LoRA sleep update, stale head keeps >= 80% of its tau (otherwise retrain nightly).

## Open questions
- What is the real MoE overlap between consecutive tokens for LFM2 (measure router choices)?
- Does mlx's quantized MoE kernel (gather_qmm) scale well from 1 to 4 tokens? This decides everything.
