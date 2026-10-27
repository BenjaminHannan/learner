# Engineering brief: from-scratch conversational LM on one RTX 5070 Ti

**Build a ~360M-parameter model, not 125M and not 1B.** On a 16 GB RTX 5070 Ti, the best risk/reward target is roughly **6B pretraining tokens + 0.3B dialogue mid-training + 0.08B SFT tokens**, using a modern nanochat-style decoder and Muon. With an optimized training stack, I would budget **about 5–8 days end-to-end**, leaving substantial margin inside a two-week run.

The key point is that the goal is much easier than “make a generally knowledgeable 360M model.” You need **good English + conversational state + basic reasoning**, while facts can later come from external memory. That lets you spend capacity on exactly what a small model can learn well.

## 1\. What the evidence says at each size

There is no clean 2026 experiment that trains 30M, 125M, 350M and 1B models on identical chat data and reports human conversation quality. So the table below separates **published/measured anchors** from my engineering estimate of what a targeted from-scratch run should feel like.

| Size | Strong evidence anchor | What conversation actually feels like | Sensible token budget for this project |
| --- | --- | --- | --- |
| **~30M** | TinyStories showed that even **<10M parameters** or a single transformer layer can write multi-paragraph, grammatical, internally consistent simple stories. [arXiv+1](https://arxiv.org/abs/2305.07759?utm_source=chatgpt.com) | Surprisingly fluent in a tiny domain. Can learn “Hi, how are you?”, basic Q&A and short exchanges, but loses the thread, repeats, invents things and has almost no robust reasoning. A demo/chat toy, not something pleasant to converse with. | **0.5–1.5B** |
| **~125M** | nanochat's 135M model used ~1.08B tokens in its Jan. 2026 compute-optimal sweep. SmolLM2-135M was driven all the way to **2T tokens** yet its Instruct model scored only **1.98 MT-Bench**. [GitHub+1](https://github.com/karpathy/nanochat/discussions/420) | Fluent sentences and recognizable assistant behavior, but noticeably “small”: shallow answers, contradictions, looping, and fragile follow-ups. Huge extra token counts do not remove the capacity ceiling. | **1.5–3B** |
| **~350M** | nanochat's 362M run used 2.9B base tokens. SmolLM2-360M, after an extreme **4T-token** pretrain, reached MT-Bench **3.66**. [GitHub+1](https://github.com/karpathy/nanochat/discussions/420) | This is the first size I would expect to be **pleasantly usable for constrained everyday chat** after targeted dialogue training: sensible 2–5-turn exchanges, basic explanations and easy reasoning. It will still contradict itself sometimes and should not be trusted for facts. | **5–8B** |
| **~1B** | nanochat's scaling fit puts a ~1B model around 8.1–8.3B tokens for GPT-2-Large/GPT-3-Medium-like CORE levels, although Karpathy explicitly warns that these are extrapolations. SmolLM2-1.7B-Instruct reaches MT-Bench **6.13**, but was trained on **11T tokens**. [GitHub+1](https://github.com/karpathy/nanochat/discussions/420) | Clearly more robust conversation: better recovery from follow-ups, fewer absurd transitions, better elementary reasoning. But it is much less attractive on a 16 GB training GPU. | **10–20B+** |

### What each research line contributes

**TinyStories is the strongest evidence that data simplicity matters enormously.** Instead of forcing a tiny model to approximate the full distribution of the Internet, it constrains language enough that models below 10M parameters learn grammar, coherence and rudimentary reasoning. The original set has about 2.1M stories; a 4K-BPE reproduction contains about **488M training tokens**. [arXiv+1](https://arxiv.org/abs/2305.07759?utm_source=chatgpt.com) The mistake would be training mostly on TinyStories: the resulting model sounds like a children's-story generator.

**BabyLM reinforces the data-efficiency lesson, but I would not copy its winning recipes literally.** The 2024 challenge restricted models to 10M or 100M words and found that data, architecture and objective changes mattered substantially; a hybrid causal/masked objective won overall. [ACL Anthology+1](https://aclanthology.org/2024.conll-babylm.1/?utm_source=chatgpt.com) The famous 2023 BabyLlama recipe specifically uses knowledge distillation, so it violates your “every weight learned by me/no teacher logits” constraint. [ACL Anthology](https://aclanthology.org/2023.conll-babylm.pdf?utm_source=chatgpt.com)

**SmolLM shows what happens when tiny models are massively overtrained.** SmolLM's 135M and 360M models consumed 600B tokens each, with depth-over-width architectures, GQA, 2048 context and a long cooldown. [Hugging Face](https://huggingface.co/blog/smollm?trk=article-ssr-frontend-pulse_little-text-block&utm_source=chatgpt.com) SmolLM2 pushed that to 2T and 4T tokens. The lesson is not “you need trillions of tokens”; it is that small models continue benefiting from excellent data for a very long time, but **capacity still wins eventually**.

**modded-nanoGPT/nanochat is the most relevant training recipe.** modded-nanoGPT brought the GPT-2 124M validation target below 400M tokens using RoPE, QK norm, ReLU², Muon, improved initialization, better attention/data packing and other optimizations. [GitHub](https://github.com/KellerJordan/modded-nanogpt?utm_source=chatgpt.com) nanochat packages many of the robust ideas into an end-to-end base → dialogue midtrain → SFT pipeline, using RoPE, QK norm, RMSNorm, ReLU² and Muon/AdamW. [GitHub+1](https://github.com/karpathy/nanochat/discussions/1?utm_source=chatgpt.com)

Muon is no longer just a speedrun curiosity: the 2025 scalable-Muon work reports roughly **2× compute efficiency versus AdamW** in its compute-optimal scaling experiments. [arXiv](https://arxiv.org/abs/2502.16982?utm_source=chatgpt.com)

* * *

# 2\. The model I would actually train

### Architecture

I would use this fixed configuration:

| Component | Choice |
| --- | --- |
| Parameters | **~362M** |
| Layers | **32** |
| `d_model` | **960** |
| Query heads | **15 × 64-dim** |
| KV heads | **5** — 3:1 GQA |
| MLP | **3840**, ReLU² |
| Norm | parameter-free RMSNorm |
| Attention | QK normalization |
| Position | RoPE |
| Biases | none |
| Dropout | 0 |
| Embedding/head | **untied** |
| Tokenizer | byte-level BPE, **24,576 tokens**, trained from scratch |
| Base context | **1,024** |
| Dialogue/SFT context | **2,048** |
| Precision | BF16 |
| Attention kernel | PyTorch fused SDPA/FlashAttention; FA3 if stable on your stack |

This deliberately combines SmolLM's **deep, narrow small-model geometry** with the simpler nanochat/modded-nanoGPT block. SmolLM2-360M itself uses 32 layers, width 960, 15 Q heads and 5 KV heads. [Hugging Face](https://huggingface.co/HuggingFaceTB/SmolLM2-360M/blob/main/config.json?utm_source=chatgpt.com) nanochat supplies the QK-normalized/RMSNorm/ReLU² variant. [GitHub](https://github.com/karpathy/nanochat/blob/master/nanochat/gpt.py?utm_source=chatgpt.com)

The approximate parameter arithmetic is:

- attention/layer: `2×960×960 + 2×960×320 = 2.458M`
- MLP/layer: `2×960×3840 = 7.373M`
- 32 blocks: `32 × 9.830M = 314.57M`
- embedding + untied head: `2 × 24,576 × 960 = 47.19M`

**Total ≈ 361.8M parameters.**

I prefer a 24K tokenizer to a 49K–65K tokenizer here because this model is English-focused and capacity-constrained. Every vocabulary entry costs parameters twice with an untied head. Train the tokenizer on a representative mix of pretraining plus dialogue text, and reserve the eventual chat control tokens from the beginning.

### Optimizer

Use **Muon for the 2-D transformer matrices and AdamW for token embedding/head/scalars**, following nanochat's basic split. nanochat's established starting point is a Muon matrix LR around `0.02`, with AdamW β around `(0.8, 0.95)` for the embedding/head groups. [GitHub](https://github.com/karpathy/nanochat/discussions/8?utm_source=chatgpt.com)

I would test `Muon LR = 0.01` versus `0.02` during the short pilots rather than treating one as sacred.

For scheduling, use **Warmup–Stable–Decay (WSD)**:

`~1% warmup → ~79% stable → ~20% decay`

MiniCPM introduced WSD specifically because the stable section can keep training and later branch into a decay phase, which is excellent for resumable solo training. [arXiv](https://arxiv.org/abs/2404.06395?utm_source=chatgpt.com) SmolLM independently found a trapezoidal schedule with a **20% cooldown** effective. [Hugging Face](https://huggingface.co/blog/smollm?utm_source=chatgpt.com)

Keep a checkpoint **immediately before the decay begins**. Then if 6B tokens looks undertrained, resume the stable checkpoint with another 1–2B tokens rather than restarting.

### Why not 1B locally?

A normal BF16 Adam-style 1B training state is already roughly:

`2 GB weights + 2 GB gradients + 8 GB FP32 moments = 12 GB`

before activations, CUDA workspaces, attention buffers, compilation and possibly FP32 master weights. Muon improves the situation, checkpointing helps, and offload is possible, but all of those sacrifices make a one-GPU 1B run less efficient.

At ~360M you can optimize for **throughput rather than survival**.

### RTX 5070 Ti timing

NVIDIA specifies the 5070 Ti as 16 GB GDDR7, 896 GB/s, 8960 CUDA cores. [NVIDIA](https://www.nvidia.com/en-us/geforce/graphics-cards/compare/?utm_source=chatgpt.com) Its dense BF16 Tensor throughput with FP32 accumulation is about **87.9 TFLOP/s**. [Local AI Registry+1](https://local-ai-registry.vercel.app/hardware/rtx-5070-ti-16gb?utm_source=chatgpt.com)

For 6B base tokens:

6ND\=6(3.62×108)(6×109)≈1.303×1019 FLOPs.

Assume **30–40% MFU** until your own benchmark proves otherwise:

87.9×(0.30–0.40)\=26.4–35.2 effective TFLOP/s.

Thus the simple `6ND` estimate is:

1.303×1019/(26.4–35.2)×1012≈103–137 hours

or **4.3–5.7 days**.

That corresponds to approximately:

26.4–35.2T/(6×362M)≈12.1–16.2K tokens/s.

Full attention, evaluation, checkpoint writes, dataloading and imperfect kernel utilization are not captured perfectly by `6ND`, so I would **plan on 10–14K tok/s and about 5–7 days for the 6B-token base**.

This is deliberately conservative. A 2026 nanochat report got a customized **338M model above 400K tok/s across eight RTX 5090s**, about 50K/GPU, at ~58% reported BF16 MFU. [GitHub](https://github.com/karpathy/nanochat/discussions/664?utm_source=chatgpt.com) A separate single-5090 nanochat run trained a 1.384B model from scratch in 41.4 hours. [GitHub](https://github.com/karpathy/nanochat/discussions/819?utm_source=chatgpt.com)

**Do the training under WSL2/Linux rather than native Windows** unless your exact compile/FlashAttention stack benchmarks equally well. The first 30-minute run should settle the real number.

* * *

# 3\. Data plan

## Stage A — 6.0B-token base pretraining

| Source | Tokens consumed | Mix | Why | License |
| --- | --- | --- | --- | --- |
| **FineWeb-Edu** | 3.6B | 60% | clean explanatory English, broad syntax and commonsense | ODC-By 1.0 [Hugging Face](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu/tree/main) |
| **Cosmopedia** | 0.9B | 15% | synthetic textbooks, how-to prose, stories; unusually learnable text | Apache-2.0; corpus is ~25B tokens [GitHub](https://github.com/huggingface/cosmopedia?utm_source=chatgpt.com) |
| **TinyStories / V2 GPT-4** | 0.6B | 10% | very clean simple English and local coherence | CDLA-Sharing-1.0 [Hugging Face](https://huggingface.co/datasets/roneneldan/TinyStories/blob/main/README.md?utm_source=chatgpt.com) |
| **FineWeb** | 0.9B | 15% | prevents the model becoming entirely textbook/children's-story flavored | ODC-By 1.0 [Hugging Face](https://huggingface.co/datasets/HuggingFaceFW/fineweb?utm_source=chatgpt.com) |

I would actually make TinyStories slightly heavier during the first ~500M tokens, then taper it, while preserving roughly the 10% aggregate share.

Do **not** try to emulate SmolLM's hundreds of billions of tokens. Your model only needs enough general language competence for targeted dialogue training to work.

## Stage B — ~300M-token conversational mid-training

Use full next-token loss over conversations here, including role/control tokens.

A good mixture is:

- **45% Smol-SmolTalk (~135M tokens)**. It has ~460K training conversations and was explicitly redesigned for models **below 1B parameters**: shorter conversations, less task-specific data, no function calling and no advanced math. Apache-2.0. [Hugging Face+1](https://huggingface.co/datasets/HuggingFaceTB/smol-smoltalk/blob/main/README.md?utm_source=chatgpt.com)
- **35% SODA (~105M)**. It contains ~1.49M socially grounded dialogues, including ~1.19M train examples, under CC-BY-4.0. Use it to teach natural turn transitions rather than assistant identity. [Hugging Face](https://huggingface.co/datasets/allenai/soda/blob/main/README.md?utm_source=chatgpt.com)
- **20% base-data replay (~60M)**. This protects ordinary language modeling while conversation formatting is being learned.

This is almost exactly the conceptual role of nanochat's mid-training: introduce conversation control tokens and multi-turn structure **after** the base already understands language. [GitHub](https://github.com/karpathy/nanochat/discussions/1?utm_source=chatgpt.com)

## Stage C — ~80M-token assistant SFT

Now mask the loss so only assistant completions count, as current nanochat does. [GitHub](https://github.com/karpathy/nanochat/blob/master/scripts/chat_sft.py?utm_source=chatgpt.com)

I would use approximately:

- **50M Smol-SmolTalk**, aggressively filtered for ordinary Q&A/conversation.
- **15M UltraChat-200k**, but only short/simple examples. UltraChat-200k has 207,865 SFT conversations and an MIT license. [Hugging Face](https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k/blob/main/README.md)
- **10M Everyday Conversations**, by intentionally repeating/reshuffling its small corpus. The dataset has ~2.26K simple 3–4-exchange conversations and was created specifically because tiny SmolLM models otherwise failed on embarrassingly basic prompts such as “Hi” and “Who are you.” Apache-2.0. [Hugging Face](https://huggingface.co/datasets/HuggingFaceTB/everyday-conversations-llama3.1-2k?utm_source=chatgpt.com)
- **5M GSM8K/easy arithmetic reasoning**. GSM8K has 7,473 training examples with step-by-step solutions and is MIT licensed. [Hugging Face](https://huggingface.co/datasets/openai/gsm8k/blob/refs%2Fpr%2F1/dataset_infos.json?utm_source=chatgpt.com)

For GSM8K, prefer short 2–4-step solutions. You want the model to learn **“break an easy question into steps”**, not imitate pages of synthetic chain-of-thought.

### Data I would deliberately exclude

Avoid code, multilingual text, advanced mathematics, function-calling/tool traces, long-form legal/scientific material, giant encyclopedic-fact mixtures, enormous creative-writing responses, and preference/DPO data initially.

Also filter UltraChat very heavily. Its own dataset card shows the sort of long dystopian creative-writing conversation that is useful to a 7B assistant but wastes scarce capacity here. [Hugging Face](https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k/blob/main/README.md)

Too much TinyStories gives you a child-story voice. Too much SODA gives you a social-chat character rather than a useful assistant. Too much large-model reasoning text teaches **the surface style of reasoning** faster than the underlying ability.

The later external notebook is a major advantage: **do not spend hundreds of millions of weights memorizing trivia you intend to retrieve anyway.**

* * *

# 4\. Cheap evaluation for “can I actually talk to it?”

Do not make MMLU your main success criterion. Build a fixed **100-conversation evaluation suite** around the actual product.

Each test should contain 4 turns, giving 400 assistant replies total. Cover roughly: ordinary greetings, simple Q&A, follow-up pronouns, remembering a fact supplied earlier in the conversation, topic persistence, correction after the user says “No, I meant…”, commonsense, and very easy two-step reasoning.

Use a separate strong model purely as a **blind evaluator**, never as a training teacher. LLM judges have shown >80% agreement with human preferences in MT-Bench experiments, although they have known position and verbosity biases. [arXiv](https://arxiv.org/abs/2306.05685?utm_source=chatgpt.com) Length bias is sufficiently real that AlpacaEval later added explicit length control. [arXiv](https://arxiv.org/abs/2404.04475?utm_source=chatgpt.com)

Score every response 0/1/2 for:

| Dimension | Meaning |
| --- | --- |
| English | grammatical and comprehensible |
| Relevance | actually answers the latest user message |
| Memory | respects information from earlier turns |
| Sensibility | answer makes basic commonsense sense |
| Non-repetition | does not loop/restate itself |
| Reasoning | where applicable, steps support conclusion |

Fix generation at, for example, **max 128 new tokens** so a model cannot win by verbosity.

I would declare the final run successful only if the held-out set reaches roughly:

- **≥90%** comprehensible English
- **≥85%** on-topic answers
- **≥80%** correct use of prior-turn context
- **≤5%** obvious repetition/degeneration
- **≥70%** whole-conversation success, meaning no fatal failure across all four turns
- **≥60%** on a separate set of very easy reasoning questions

Also manually blind-review **20 conversations** at every major checkpoint. An automated judge can be systematically wrong; a 20-transcript human check costs almost nothing.

* * *

# 5\. De-risk it before the multi-day run

| Run | What to do | Continue only if… |
| --- | --- | --- |
| **10–15 min** | Exact 362M architecture; deliberately overfit a tiny shard. Test save/resume. | Loss can be driven very low, resumed training matches expectations, no NaNs. |
| **≤30 min** | Exact model on real pretraining mix. Optimize compilation/batching. | At least **~10K tok/s** is reachable, loss decreases smoothly, VRAM has margin, fused attention is actually active. |
| **≤30 min wind-tunnel** | Also train a cheap ~30–60M version on TinyStories. | It starts acquiring obvious English patterns quickly. This catches tokenizer/data bugs cheaply. |
| **4–8 h** | 362M, ~150–350M real tokens. | Validation loss follows a clean downward curve and samples move from word salad toward syntactically recognizable English. |
| **~24 h** | Reach roughly 0.8–1.2B tokens. Fork the checkpoint and do a tiny dialogue adaptation. | Base output is grammatical enough that the dialogue copy becomes recognizable Q&A instead of merely learning `<user>` syntax. |
| **~3 days** | Reach ~3B tokens. Run ~50–100M dialogue tokens on a fork. | Follow-up/relevance eval is clearly improving and repetition is falling. |
| **5–7 days** | Finish the ~6B base tokens, including WSD decay. | Use best validation/conversation checkpoint, not blindly the final step. |
| **\+ ~8–15 h** | Full ~300M midtrain + ~80M SFT. | Final 100-conversation rubric clears the predefined thresholds. |

The first 30-minute run is especially important. If it gives **6K tok/s rather than 12K**, that single measured number changes the full-run estimate more reliably than any hardware calculation.

### Three failures I would expect first

**1\. Training is much slower than the FLOP estimate.** Detect this in the first 30 minutes: low GPU utilization, graph breaks, explicit attention masks, bad dataloader stalls or OOM-driven tiny batches. The 2026 single-5090 nanochat report specifically found that falling off the fused attention path caused major problems. [GitHub](https://github.com/karpathy/nanochat/discussions/819?utm_source=chatgpt.com) Fix throughput before spending days training.

**2\. Loss looks healthy but the data distribution produces the wrong personality.** If samples are all children's stories, textbook paragraphs or generic web prose, the model is learning exactly what you fed it. Reduce TinyStories/Cosmopedia and increase ordinary English/dialogue. Keep fixed generation prompts from hour one.

**3\. SFT makes a decent base model worse.** The tell is sudden repetition, verbosity, role-token leakage, or forgetting ordinary language after SFT. Use a lower LR, one pass rather than repeated epochs, 10–20% base/midtraining replay, strict length filtering, and checkpoint before every adaptation stage.

* * *

# 6\. What $1K–$5K of cloud money changes

The answer changes substantially: **scale the model, not just the token count of the 360M model.**

Karpathy's original nanochat setup quoted about **$24/hour for 8×H100**, and its historical 1.879B-parameter “$1000-tier” run trained on **37.58B tokens** in about 30.8 hours on 8×H100. [GitHub+1](https://github.com/karpathy/nanochat/discussions/1?utm_source=chatgpt.com) Current pricing varies by provider; for example, CoreWeave currently lists 8×H100 at $49.24/hour on demand and $19.71/hour spot. [CoreWeave](https://coreweave.com/pricing?utm_source=chatgpt.com)

With cloud money I would therefore change the roadmap to:

**At ~$1K:** first run several 100–350M “wind-tunnel” experiments to select data mix/LR, then train roughly a **1–1.5B final model on 15–30B high-quality tokens**. Keep exactly the same conversation-centric post-training.

**At ~$2K–$3K:** target roughly **1.5–2B**, with enough compute for controlled architecture/data ablations before committing. This is the range where conversation quality should stop feeling so obviously “tiny.”

**At ~$5K:** I would still resist maximizing parameter count. Spend perhaps 15–25% on several reproducible ablations and the rest on a **~2B final run with 30–60B carefully selected tokens** plus proper mid-training/SFT. Multiple smaller experiments before the final run are far more valuable than gambling the entire budget on one 3–4B training run.

SmolLM2 demonstrates why: despite an absurd **4T tokens**, its 360M model remains at MT-Bench 3.66, whereas the 1.7B model reaches 6.13. [Hugging Face+1](https://huggingface.co/HuggingFaceTB/SmolLM2-360M/blob/main/README.md?utm_source=chatgpt.com) Once you can afford more parameters, continuing to pour data into 360M increasingly runs into a capacity ceiling.

## Bottom line

For the existing 5070 Ti, I would freeze the first serious target at **~362M / 6B base tokens / 300M dialogue midtrain / 80M SFT**. It is large enough that targeted simple conversation should be realistic, but small enough that every weight can genuinely be trained from random initialization on one 16 GB GPU without optimizer offloading or a multi-week run.

The most important departure from traditional “train a small LLM” advice is **not to optimize for world knowledge**. Train a language-and-reasoning core that knows how English conversation works, how to maintain state, and how to perform simple reasoning; let the later notebook supply long-tail facts. That gives the limited 360M parameters a much easier job.

### Sources

- [nanochat miniseries, January 2026](https://github.com/karpathy/nanochat/discussions/420?utm_source=chatgpt.com)
- [nanochat end-to-end training discussion](https://github.com/karpathy/nanochat/discussions/1?utm_source=chatgpt.com)
- [modded-nanoGPT](https://github.com/KellerJordan/modded-nanogpt?utm_source=chatgpt.com)
- [TinyStories paper](https://arxiv.org/abs/2305.07759?utm_source=chatgpt.com)
- [BabyLM 2024 findings](https://aclanthology.org/2024.conll-babylm.1/?utm_source=chatgpt.com)
- [SmolLM training report](https://huggingface.co/blog/smollm?utm_source=chatgpt.com)
- [SmolLM2-360M model card](https://huggingface.co/HuggingFaceTB/SmolLM2-360M?utm_source=chatgpt.com)
- [MiniCPM / WSD paper](https://arxiv.org/abs/2404.06395?utm_source=chatgpt.com)
- [Muon scalability paper](https://arxiv.org/abs/2502.16982?utm_source=chatgpt.com)
- [Smol-SmolTalk dataset](https://huggingface.co/datasets/HuggingFaceTB/smol-smoltalk?utm_source=chatgpt.com)
- [Everyday Conversations dataset](https://huggingface.co/datasets/HuggingFaceTB/everyday-conversations-llama3.1-2k?utm_source=chatgpt.com)
- [FineWeb-Edu](https://huggingface.co/datasets/HuggingFaceFW/fineweb-edu?utm_source=chatgpt.com)
- [MT-Bench / LLM-as-a-Judge paper](https://arxiv.org/abs/2306.05685?utm_source=chatgpt.com)
