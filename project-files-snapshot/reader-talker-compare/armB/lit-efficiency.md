# Literature: making a frozen LFM2.5-1.2B reader cheaper (research notes, 2026-10-04)
Labels: [shown] = seen on a cited page this session; [memory] = from my background knowledge, not re-checked now;
[suggested] = literature implies it; [untested-guess] = my estimate for THIS system. Repo not read; no experiments run.

## 1. LFM2 / LFM2.5 architecture
- Layers: 16 = 10 double-gated short-conv (LIV) blocks + 6 GQA attention blocks, for 1.2B (LFM2 and LFM2.5 identical) [shown]
  https://huggingface.co/LiquidAI/LFM2.5-1.2B-Base , https://huggingface.co/LiquidAI/LFM2-1.2B
- LFM2.5 config.json: hidden 2048, 16 layers, layer_types = conv,conv,attn,conv,conv,attn,conv,conv,attn,conv,attn,conv,attn,conv,attn,conv
  (attention at indices 2,5,8,10,12,14; the LAST layer, 15, is conv), 32 heads / 8 KV heads, conv_L_cache=3 (kernel 3),
  vocab 65,536, MLP width 12288 (config value; may be the pre-adjust value) [shown]
  https://huggingface.co/LiquidAI/LFM2.5-1.2B-Base/raw/main/config.json
- Tied embeddings: yes (card config says tie_embedding true; HF Lfm2Config default tie_word_embeddings=True) [shown]
  https://huggingface.co/docs/transformers/model_doc/lfm2
- Params: 1.17B total, context 32,768, 28T training tokens for LFM2.5 vs ~10T for LFM2 [shown]
- Split: embedding table = 65,536 x 2048 = 134M (~11.5%, shared with the LM head); blocks ~1.04B (~88%) [arithmetic from shown numbers]
  Consequence: the LM head matmul (2048 x 65536 per position) costs about as much as ~1/8 of the blocks per token IF logits are computed
  for all positions; use logits_to_keep / skip the head when only hidden states are needed [suggested]. HF forward has logits_to_keep [shown].
- Siblings (all 16 layers, 10 conv + 6 attn, vocab 65,536, 32K ctx) [shown]:
  | model | params | MMLU | GSM8K | IFEval |
  | LFM2-350M | 354.5M | 43.43 | 30.1 | 65.12 |  https://huggingface.co/LiquidAI/LFM2-350M
  | LFM2-700M | 742.5M | 49.9 | 46.4 | 72.23 |   https://huggingface.co/LiquidAI/LFM2-700M
  | LFM2-1.2B | 1.17B | 55.23 | 58.3 | (not retrieved) | https://huggingface.co/LiquidAI/LFM2-1.2B
  Also a 2.6B dense and an 8.3B/1.5B-active MoE exist. Tech report: https://arxiv.org/abs/2511.23404 [shown]
  The 350M has the same depth, so "read from layer k" ideas transfer; its width is smaller (hidden size not retrieved; I believe 1024 [memory]).
  Drop 1.2B -> 700M: MMLU -5.3, GSM8K -12 points (generative benchmarks, not probing). Cost: ~0.63x params [arithmetic].
- Caching in HF: Lfm2Model takes past_key_values (a Cache), returns the same cache format; for conv layers the repo-internal
  class is Lfm2HybridConvCache holding the last-3-token conv state per conv layer plus KV per attention layer [memory: class name; the doc page
  confirms past_key_values/Cache semantics only]. Prefix reuse = pass the cache and only the new tokens. Caveats [suggested]:
  (a) the cache is mutated in place, so copy.deepcopy it (or crop) before branching; (b) left-padded batches complicate the conv state
  (padding tokens enter the 3-wide conv window; HF masks them, but verify equality with a no-cache forward to ~1e-2 in bf16);
  (c) DynamicCache.crop works for KV but conv state cannot be "cropped" - you can only keep the state at the end of the shared prefix.
  Must be verified by a numeric equality test before trusting [untested-guess].

## 2. Prefix/prompt caching literature
- vLLM PagedAttention + automatic prefix caching (Kwon et al. 2023, https://arxiv.org/abs/2309.06180) [memory]
- RadixAttention / SGLang (Zheng et al. 2023, https://arxiv.org/abs/2312.07104): radix tree of KV for shared prefixes; up to ~5x throughput on
  workloads with heavy sharing [memory]
- Prompt Cache (Gim et al. 2023, https://arxiv.org/abs/2311.04934): precomputed modules; 8x (GPU) to 60x (CPU) TTFT reduction, with
  position-approximation error for non-prefix modules [memory]
- All of these require EXACT prefix identity (same tokens, same positions, causal). Hybrid conv models: conv state is just a small fixed
  state, so prefix reuse is simpler than for pure KV, but SSM/conv caches can only be snapshotted at prefix boundaries [suggested].
- Savings here [untested-guess]: you described reader pass (N prompt tokens) + exit pass (same prompt words + pointer). If the exit pass's
  token sequence has the reader's sequence as an exact causal prefix and the frozen LM weights/inputs are identical, the second pass only
  computes the new pointer/answer tokens: cost goes from ~2N to ~N + m tokens, i.e. up to ~1.8-1.95x fewer LM FLOPs per question and the
  "3-5x slower than bare LM" gap shrinks to roughly 1.6-2.7x. Does NOT apply if the exit pass modifies earlier positions (inserted
  embeddings, different instruction text before the question, trainable adapters inside the LM), because causal states then differ.
  "Question first" is what makes the exit's extra material a suffix; the question-first order also changes what the reader sees (quality
  must be re-measured). At batch 1 the work is prefill-bound (~2.7k tok/s -> 160 tokens ~ 60 ms per pass), so removing one pass ~halves LM time.
  Fixed per-forward launch overhead (kernel launches for 16 layers) is a separate cost not removed by caching (see section 3).

## 3. Speed fixes with no quality change
- Batch 1 prefill of 160 tokens at 2.7k tok/s = ~60 ms is far below the 5090's compute roofline (1.2B x 2 FLOP x 2.7k = ~6 TFLOP/s vs
  hundreds of bf16 TFLOP/s) -> it is launch/overhead-bound, not FLOP-bound [arithmetic; suggested]. Decode 70 tok/s at batch 1 is also
  ~10x slower than the memory-bandwidth bound (2.3 GB weights / ~1.8 TB/s = ~1.3 ms/token, ~700 tok/s) [arithmetic]. Eager HF with Python
  overhead is the likely culprit.
- bf16 already used (weights native BF16) [shown]. fp16/TF32 no gain.
- torch.compile (mode="reduce-overhead"/"max-autotune") + CUDA graphs: typical 2-4x on small-model batch-1 decode in eager-HF-vs-compiled
  comparisons (e.g. gpt-fast reports ~8x vs naive eager on Llama-7B decode, mostly from removing overhead) [memory: https://pytorch.org/blog/accelerating-generative-ai-2/].
  For a fixed-shape prefill (pad every prompt to 160 tokens, static cache) CUDA graph capture is straightforward: expect 2-5x at batch 1 [untested-guess].
  Conv layers with a cache need static-shape conv state; HF static cache support for Lfm2 hybrid cache is unverified [untested-guess].
- Fused/optimized runtimes: Liquid ships/endorses llama.cpp, vLLM and ExecuTorch support for LFM2 [memory; Liquid blog]. vLLM with prefix caching + CUDA graphs
  would give both fixes; hybrid-model prefix caching support in vLLM is newer/less mature [memory].
- Weight-only quantization (GPTQ https://arxiv.org/abs/2210.17323, AWQ https://arxiv.org/abs/2306.00978, bitsandbytes LLM.int8/NF4):
  speeds decode (bandwidth-bound) ~1.5-3x for int4 with good kernels (Marlin/ExLlama), but bitsandbytes is often SLOWER than bf16 at small batch/prefill
  [memory]. For prefill-bound, compute-bound batch-256 work it gives ~no gain. Quality: int4 loses small amounts on generative benchmarks
  (~0.5-2 points for 7B; relatively larger for 1B) [memory] and it perturbs hidden states, which matters if you train heads on frozen
  features: it is NOT "no quality change" for a probe trained on bf16 features unless you retrain. Not recommended first [suggested].
- Priority order for the stated goal (batch 1, ~19 q/s): (1) CUDA graphs/static shapes, (2) prefix reuse, (3) skip LM head / compute logits
  only where needed, (4) quantization last [suggested]. Large-batch throughput (290-360 q/s) is already within ~5-10x of FLOP limits? Check:
  bare LM 36-71k tok/s at batch 64 vs your ~300 q/s x ~2 passes x ~160 tok = ~100k tok/s -> consistent with two passes being the cost [arithmetic].

## 4. Early exit / layer skipping for a frozen LM as feature extractor
- CALM (Schuster et al. 2022, https://arxiv.org/abs/2207.07061): per-token confidence early exit for generation, up to ~3x speedup with preserved
  quality; for decoder models, skipped layers' KV must be copied/propagated [memory].
- LayerSkip (Elhoushi et al. 2024, https://arxiv.org/abs/2404.16710): needs training with layer dropout + early-exit loss (NOT frozen-friendly);
  self-speculative decoding 1.8-2.2x [memory].
- Skean et al. 2025, "Layer by Layer" (https://arxiv.org/abs/2502.02013): mid-depth embeddings often match or beat final-layer on 32 MTEB tasks,
  across transformers and SSMs; the best layer is typically around the middle, and final layers specialize for next-token prediction [shown: abstract].
  Reported gains in the paper are a few points of average MTEB score; I recall the mid layer beating the last by up to ~10-20% relative for some
  models [memory, unverified].
- Probing literature (Tenney et al. 2019 BERT rediscovers the pipeline; linear probes peak mid-depth for syntax/semantics) [memory].
- Expected speedup reading from layer k of 16 (blocks dominate; layers have similar MLP cost; conv layers slightly cheaper than attention):
  cost ~ k/16 of block FLOPs, plus the head is skipped. k=8 -> ~2x, k=10-11 -> ~1.5x [arithmetic; untested-guess for wall time given overhead-bound regime:
  speedup in wall-clock at batch 1 may be smaller unless CUDA graphs remove launch overhead].
- Accuracy retained [suggested, not shown for this model]: for classification-like probing, layers at ~50-75% depth usually retain ~95-100% of
  last-layer probe accuracy, sometimes exceed it. For your task the exit also uses the LM as part of the answer path, so reading from an intermediate layer
  changes the downstream distribution: needs retraining the small head on layer-k features. Test with k in {6, 8, 10, 12, 16}; pass mark fixed in advance.
  Note: layer 15 (final) is a conv layer and the model's own final norm/head expects layer-15 output; intermediate hidden states need their own norm.
- Hybrid caveat: truncating at layer k leaves later conv/attention caches unfilled, so a later full-depth continuation (e.g. generation) can't reuse
  that cache; fine if you never go deeper [suggested].

## 5. Embeddings-only readers
- Input embedding table alone: 65,536 x 2048 (134M params, 11.5% of the model) ~ costs only a gather; no transformer compute [arithmetic].
- Literature [memory; none specific to LFM]: bag-of-embeddings / fastText (Joulin et al. 2016, https://arxiv.org/abs/1607.01759) is within ~1-3 points of deep
  models on topic/sentiment classification, but loses on tasks needing word order, negation, and composition (NLI, QA, multi-hop). Static
  word-embedding baselines on GLUE-style tasks lose roughly 10-20 points vs a pretrained contextual encoder [memory; e.g. Wang et al. 2018 GLUE baselines
  BiLSTM+GloVe vs BERT]. Transplanting LLM input embeddings into a small trainable encoder (e.g. "embedding transplant"/distilled-embedding models, Model2Vec
  https://github.com/MinishLab/model2vec: static embeddings distilled from sentence transformers retain ~85-92% of teacher MTEB score at ~500x speed) [memory].
  Layer-0 LLM embeddings are not trained for semantic similarity (the LLM's first layers are what build context), so a 2048-d lookup + small
  transformer (2-4 layers, d=256-512) trained from scratch on your task is the realistic variant; quality loss relative to the 16-layer reader is
  UNKNOWN for your task and likely substantial for compositional questions [untested-guess].
- Cost: a 4-layer d=512 encoder on 160 tokens is ~1% of the LM FLOPs [arithmetic], so it frees nearly all reader time; also conv-only LFM-like layers are cheap.
- Compatible with an exit that still uses the frozen LM only on pointer/answer tokens (short) rather than the 160-token prompt [suggested].

## Candidate order (one change at a time; pass marks to be fixed beforehand by Ben/team)
1. CUDA graphs + fixed-length padding, quality-neutral (check bitwise-ish equality of outputs, max |diff| in hidden states).  Proves wrong if speedup <1.5x at batch 1.
2. KV+conv prefix reuse, with equality test vs the two-pass baseline (<=1e-2 bf16 logit diff, identical answers on a fixed sample). Proves wrong if the exit pass modifies earlier positions.
3. Read from layer k (k in 8,10,12) with retrained head; pass mark: accuracy within a pre-set margin of the full-depth reader.
4. Embeddings-only + small encoder as a separate, riskier arm (keep separate from card experiments and the village model).

## Plain-language summary for Ben
Right now the LM reads each question twice. Three safe fixes: (a) stop the GPU wasting time between tiny operations (CUDA graphs), (b) save the first read and
reuse it so the second read only handles the few new tokens, (c) stop reading at layer ~10 of 16. Each should give roughly 1.5-2x and they stack. Shrinking to
a smaller model or throwing away the LM's layers entirely saves more but risks accuracy, and we have no direct evidence on how much.
