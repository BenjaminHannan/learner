# R2: Latent chain-of-thought, pause/filler tokens, and distilling explicit CoT into latent computation

Sweep date 2026-10-24. Most PDFs were read directly (tables included). A few 2026 items were read at abstract level only; these are marked (abs). All IDs resolve at https://arxiv.org/abs/<id>.

Labels: **[shown]** = measured in that paper in the stated setting. **[suggested]** = the authors' interpretation, or my inference from their numbers, not isolated by an ablation. **[untested]** = I found no paper testing it, or it is an extrapolation to our setting (LFM2.5-24B-A2B, tau2-retail).
"Gap closed" = (latent - no-CoT) / (explicit CoT - no-CoT), computed by me from the tables.

## 0. Bottom line

1. No paper I found evaluates silent latent computation on multi-turn tool use (tau-bench, tau2, BFCL multi-turn). Nearest are ALAR (single-turn BFCL AST, LoRA-tuned 4B) and HybridAgent (math/search/GAIA; hybrid latent+text). The 23->30 target on tau2 is [untested] everywhere.
2. Pure latent loops close roughly 65-90% of the CoT-vs-no-CoT gap on small models (GPT-2 to 8B) with short, templated math traces, and 25-60% on realistic traces or harder tasks. Methods that keep any text close ~100% but are not silent.
3. Distilling the model's own long natural-language reasoning is the setting where pure latent methods fail hardest (Tale of Two Regimes).
4. Frozen-backbone latent methods give real but modest gains (+1 to +10 points on GSM8K-style tasks) unless the latent module is large and trained on a lot of data.
5. RL on latent loops works only from a distilled warm start and only with injected stochasticity; the three 2026 RL papers I read all report that naive GRPO collapses or stalls.

## 1. Per-paper notes

### A. Curriculum / self-distillation family (backbone is trained, not frozen)

**Coconut** (Hao et al., arXiv 2412.06769, v4 Aug 2026). GPT-2 124M, full finetune. Last hidden state is fed back as the next input embedding; n latent steps cost n+1 sequential forward passes in training. Curriculum: stage k replaces the first k CoT steps with k*c latents (c=2 on GSM8k, c=1 on ProsQA); optimizer reset each stage; loss on remaining text only.
- GSM8k: CoT 42.9, No-CoT 16.5, iCoT 30.0, Pause 16.4, Coconut 34.1+-1.5 (about 67% of gap) **[shown]**. ProntoQA: no-CoT already 93.8 vs Coconut 99.8. ProsQA: CoT 77.5, no-CoT 76.7, Coconut 97.0, but iCoT 98.2 and pause-as-thought 96.6 match it, so these toy sets do not need latent content **[shown]**.
- Ablations: no curriculum 14.4 (below no-CoT); curriculum with no latents 21.6; curriculum with pause tokens 24.1 **[shown]**. So about 43% of Coconut's GSM8k gain over no-CoT is reproduced by content-free positions plus curriculum **[suggested, my arithmetic]**.
- More latents: c=0->1->2 improves; c=3 slightly worse, with a training-loss spike **[shown]**.
- Larger backbones: Llama-3.2-3B 26.0->31.7, Llama-3-8B 42.2->43.6 (c=1; no CoT number given). Authors say gains shrink because larger models are heavily language-pretrained **[shown; reason suggested]**. Single task, no explicit CoT comparator at those sizes.
- Cost: 8.2 effective tokens vs 25 for CoT.

**CODI** (Shen et al., 2502.21074). GPT-2 and Llama-3.2-1B-Instruct. One shared model plays teacher (explicit CoT, teacher-forced) and student (autoregressive latents). Loss = student CE on answer + teacher CE on CoT + L1 between teacher and student hidden states at the single token before the answer (the ":" in "The answer is:"), at all layers, teacher stop-grad. 6 latents plus bot/eot, small MLP+LN projection, no curriculum.
- GSM8k-Aug GPT-2: CODI 43.7 vs No-CoT 19.1; about 99% of CoT-SFT. Llama-1B about 90% of CoT-SFT. OOD GPT-2 (SVAMP/GSM-Hard/MultiArith) CODI >= CoT-SFT; Llama-1B CODI 61.1 vs CoT-SFT 66.7 on SVAMP **[shown]**.
- Ablations: drop the L1 term 24.5 (-19 points); separate frozen teacher 27.1; keep the last CoT step in teacher data 31.7 (leaks a shortcut to the answer token) **[shown]**.
- Accuracy peaks at 6 latents **[shown]**. 2.7x speedup (3.1x compression) on compact CoT, 5.9x on verbose CoT.
- Caveat: Llama is only 1B; on CommonsenseQA the CoT data actually hurt Llama-1B (authors' observation).

**SIM-CoT** (Wei et al., 2509.20317). Adds an auxiliary decoder, used only in training, that decodes each latent into its own CoT step. Coconut on GPT-2 collapses to 12.5% at 5 latents and fails at 8/16; with SIM-CoT it stays stable **[shown]**.
- Table (GSM8k-Aug, no-CoT / SFT-CoT / CODI / CODI+SIM):
  GPT-2 19.1/42.7/42.0/42.6; Llama-1B 28.8/58.4/52.7/56.1; Llama-3B 38.3/71.5/60.8/62.3; Llama-8B 39.5/71.7/61.1/64.1.
- Gap closed for CODI: 97%, 81%, 68%, 67%. With SIM-CoT: 92% (1B), 72% (3B), 76% (8B). The fraction closed falls as the backbone grows **[shown; trend across 4 sizes, one seed each as far as I can tell]**.

**KaVa** (Kuzina et al., 2510.02312, ICLR 2026). Distills the teacher's compressed KV cache into the student's latent keys/values layer by layer (R-KV style eviction to latent budget), plus CE on answer; PCCoT-style parallel latent updates. LoRA on Llama-3.2-1B/3B-Instruct and Qwen2.5-0.5B-Instruct.
- GSM8k-Aug (no-CoT/CoT/CODI/KaVa): Qwen-0.5B 31.5/50.6/37.5/46.9; Llama-1B 33.2/63.4/53.9/56.5; Llama-3B 41.7/73.2/61.0/65.7 **[shown]**. Gap closed by KaVa: 81%, 77%, 76%.
- Natural-language traces (GSM8k-Aug-NL): Qwen-0.5B CODI falls 37.5->20.2 while KaVa 46.9->44.4; Llama-1B KaVa 55.7 vs CoT 53.2 **[shown]**. Best evidence that a richer target than one hidden state holds up on verbose traces.
- KaVa had to set the CODI-loss weight to 0 in some configs because it was unstable **[shown]**. Forward passes 62-92% fewer than CoT.

**CoLaR** (Tan et al., 2505.16552, NeurIPS 2025). Llama-3.2-1B-Instruct + LoRA; predicts compressed embeddings (c consecutive tokens merged) with a latent head; then GRPO on the stochastic head.
- GSM8k-Aug: CoT 49.4, CoLaR-2 40.1, CoLaR-5 26.8, Coconut 23.1, iCoT 19.8 (their re-runs, 5 seeds) **[shown]**.
- MATH: Qwen-1.5B-distill CoT 23.5 vs CoLaR 8.9 -> 14.3 after RL (chain 83% shorter); Llama-1B CoT 9.7 -> 5.3 -> 7.1 **[shown]**. Still far below CoT; RL helped but did not close it.

**CCoT** (Cheng & Van Durme, 2412.13171). Llama-2-7B-chat + LoRA, GSM8K (~9k train). Contemplation tokens regress mid-layer (about L/2) hidden states of evenly spaced CoT positions, generated autoregressively, then a decode module answers.
- EM: no tokens 8.9, 20x compression 15.1, 10x 17.9, full CoT 31.5; PAUSE 9.2/9.9 **[shown]**. Gap closed 27-40%. Decode time 0.33-0.78 s vs 8.1 s. Single seed.

**iCoT / Stepwise Internalization** (Deng et al., 2405.14838). Gradually deletes CoT tokens while finetuning (removal smoothing, optimizer reset). No latents at all.
- GSM8K (CoT/no-CoT/iCoT): GPT-2-S .41/.13/.30; Mistral-7B .68/.38/.51; Phi-3-3.8B .74/.28/.31 **[shown]**. Gap closed 61%, 43%, 7%. Authors state it lags explicit CoT.

**System-1.5** (Wang et al., 2505.18962). Stage 1 distills CoT hidden states into latent thoughts; stage 2 freezes the transformer and trains router-adapters for depth/step shortcuts. GPT-2-124M and Llama-3.2-1B only. GSM8K GPT-2: CoT 46.9, CODI 43.8, System-1.5 46.7 at 2 steps, >20x speedup. Small models; baseline definitions differ from other papers (their pause baseline equals CoT at 38 steps) **[shown, with caveat]**.

### B. Frozen-backbone family

**SoftCoT** (Xu et al., 2502.12134). Frozen 1B assistant (Llama-3.2-1B-Instruct) produces soft thoughts; only a linear projection is trained (LM loss on gold CoT + answer). The big frozen LLM then still writes an explicit CoT after the soft prefix.
- Llama-3.1-8B-Instruct GSM8K: zero-shot CoT 79.6/80.0 (with UNK) -> SoftCoT 81.0; 5-task avg 68.5 -> 70.5. Qwen2.5-7B GSM8K 84.1 -> 85.8, avg 70.6 -> 75.1, mostly StrategyQA +10 and AQuA +8 **[shown, 5 seeds]**.
- LoRA finetuning and Coconut on Llama-3.1-8B-Instruct came out below zero-shot CoT (75.7/76.1 vs 79.6), which the authors attribute to forgetting (one run) **[shown; cause suggested]**.
- 6 soft tokens ~ 24 hard "pause" tokens. Not silent: explicit CoT remains. Gains are small where the baseline is strong.

**SoftCoT++** (Xu et al., 2505.11484). Multiple initial tokens + contrastive loss for diverse soft thoughts, combined with self-consistency. GSM8K at N=100 chains: Llama 92.4 -> 92.7, Qwen3-8B 93.0 -> 94.1 **[shown]**. Gain <= ~1 point over SC.

**Latent Recurrent Thoughts (LRT)** (Chen & Fu, 2609.01117, Sept 2026). The most relevant architecture. Frozen Qwen3-8B; 4.2M proposer + 7M TRM-style recurrent refiner emits K latents as soft tokens. Per-task training with answer supervision only. 3 seeds, same decoder/prompt/data/budget for all.
- Avg of 5 tasks: LRT 54.1, EBM-CoT 33.5, zero-shot CoT (non-thinking) 35.0, Direct 30.9, SoftCoT 29.5 (below Direct). Countdown-4: LRT 56.7 vs SoftCoT 5.9, EBM-CoT 8.4, CoT 30.0 **[shown]**.
- Qwen3-8B thinking mode, not compute-matched: Countdown-4 85.3, HumanEval 92.1 (LRT 37.8), MBPP 49.3 (LRT 51.5), StrategyQA 76.4 (LRT 75.1), Sudoku 0.5 (LRT 49.2). LRT uses ~1-2 TFLOP vs 9-454 for thinking **[shown]**. Gap closed on Countdown-4 vs thinking: 48%.
- A generic frozen assistant's latents can be worse than none off the natural-language substrate; SoftCoT/EBM-CoT collapsed to a near-uniform latent across instances **[shown]**. Bigger refiner (7->28M) helps; more recurrent cycles help monotonically **[shown]**.
- Authors' own limits: per-task modules, one 8B decoder, no cross-task transfer.

**Differentiable cache augmentation** (Liu et al., DeepMind, 2412.17747). Frozen Gemma-2 2B plus a coprocessor (same architecture, initialised from the LLM) that reads the KV cache and appends N latent embeddings in one pass. Trained with the decoder's LM loss only, ~100k steps x 1024 x 2048 tokens of pretraining data, no task data.
- 8-shot GSM8K 21.4 -> 22.7 (4 latents) ... 26.8 (32) ... 31.4 (64); MMLU +4.7; MATH +2.1; BBH +0.4; HumanEval +3.0. Pause baseline +1.0 on GSM8K vs +5.4 for latents (same count); zero-shot CoT 23.2 **[shown]**.
- Monotone in latent count. But the coprocessor is as big as the model and the base model is weak (21% GSM8K). Single seed.

**LTPO** (Ye et al., 2510.04182, ICLR 2026). No training. Optimise K latent thought vectors per problem against a confidence reward from the frozen LLM's own distribution; then decode as usual. GSM8K Qwen2.5-7B 88.2 vs CoT 88.6; averages are carried by AIME (16.7 vs 10.0, n=30 problems, one problem = 3.3 points) **[shown; AIME result statistically thin]**. SoftCoT scores 0.0 on AIME in this table.

**LatentSeek** (Li et al., 2505.13308, v3 Jan 2026). Test-time policy-gradient on the latents of the generated CoT, self-reward, needs full re-decoding each iteration. Large gains are on weak baselines (Llama-3.1-8B GSM8K 50.2 -> 78.5, probably format fixes); Qwen2.5-14B 92.0 -> 92.5 **[shown; benefit shrinks as baseline strengthens]**. About 8-16x slower than CoT in LTPO's timing (49-62 s vs 5.8 s on GSM8K).

**Soft Thinking** (Zhang et al., 2505.15778). Training-free; feed probability-weighted token embeddings. On 32-70B reasoning models avg +0.5 to +2.5 points and 12-22% fewer tokens (math), still ~3.7-5.7k tokens per problem **[shown]**; not silent. Follow-up (Wu et al., 2508.03440) shows models behave as "single-threaded", effectively following the top token; Gumbel noise helps **[shown]**.

### C. Hybrids, compression, RL, and agentic work

**Token Assorted** (Su et al., 2502.03275). Fine-tunes Llama-3.2-1B/3B and 3.1-8B on MetaMathQA, replacing the first m CoT tokens (random m) with VQ-VAE discrete codes (1 code per 16 tokens). GSM8K CoT -> latent: 42.7->48.7, 69.7->73.8, 80.1->84.1; traces only ~17% shorter **[shown]**. Replacing everything at once ("All-Replace") collapses: 4.2/12.8/19.9 GSM8K **[shown]**. Mixed text+latent beats CoT; fully latent does not. Their "Pause Token" baseline keeps the CoT text, so it is not comparable.

**LightThinker** (Zhang et al., 2502.15589). Compresses already-generated thought spans into gist tokens (attention masks) during long reasoning. Qwen2.5-7B (SFT on long R1-style traces): GSM8K 90.9->90.1, GPQA 30.8->30.3, peak context 2086->676 tokens; Llama-3.1-8B GSM8K 91.4->88.3, GPQA 40.9->36.4 **[shown]**. A model that still thinks, but keeps a compact memory of it; 1-5 points lost for ~2-3x less context.

**HRPO** (Yue et al., 2505.18454). RL; learnable gate mixes sampled-token embedding with previous hidden state; no CoT supervision. Qwen2.5-1.5B/3B-Instruct. GSM8k 0.720 vs GRPO 0.711 (1.5B), 0.845 vs 0.834 (3B) **[shown]**. Important side finding: feeding raw last hidden states as the next input made RL rollouts nonsensical (zero reward); interpolation collapsed later **[shown]**. Still emits tokens; +1 point over GRPO.

**Latent-GRPO** (Deng et al., 2604.27998) and **Soft Tokens, Hard Truths** (Butt et al., 2509.19170), **SofT-GRPO** (2511.06411), **Dropout-GRPO** (2606.10184), **TARPO** (2606.05859, abs), **LEPO** (2604.17892, abs).
- Latent-GRPO: soft (top-K mixture) latents; naive GRPO on a latent SFT model "consistently collapses". With advantage masking for off-manifold samples + one-sided noise + first-token selection: Llama-1B GSM8K-Aug 47.6 -> 66.3 (explicit GRPO 62.3, chains ~4.4x shorter); Qwen2.5-Math-7B Math500 64.9 -> 80.4 (explicit GRPO 75.2), AIME24 6.7 -> 26.6 (explicit 16.6) **[shown; math, full finetune]**.
- Soft Tokens, Hard Truths: RL with noisy soft tokens matches discrete CoT on pass@1, beats at pass@32; best deployed with hard tokens at inference. SofT-GRPO: +0.13 pass@1, +2.19 pass@32 over discrete GRPO **[shown]**.
- Dropout-GRPO: deterministic latents give identical rollouts, so group advantage is zero; a shared dropout mask per rollout restores variance; Coconut GSM8K 27.3 -> 29.0 only **[shown]**.

**Switch / "Demystifying Hidden-State Recurrence"** (Yang et al., 2606.13106, EMNLP Findings 2026). Qwen3-8B, LoRA, discrete <swi>/</swi> tokens bracket latent spans, so GRPO ratios are defined on the boundary tokens; gradients flow through the recurrence. Matched re-implementations on OpenR1-Math:
- MATH-500 (no-CoT 11.3, text-CoT SFT 80.6): Coconut 46.6, CODI 48.3, CoLaR 53.6, pause 14.6; Switch after SFT 66.7, after GRPO 79.3 (but 1,721 visible tokens). GSM8K (28.4 / 88.6): Coconut 76.1, CODI 76.4, CoLaR 78.5, Switch 89.2 **[shown]**.
- Fully latent Coconut-style at 8B closes ~51-61% on MATH-500 and ~79-83% on GSM8K. RL on the latent spans added +12.6 points latent-conditional accuracy while the switch rate fell 81% -> 58% (the model learned to use latents less) **[shown]**.

**Abstract-CoT / "Thinking Without Words"** (IBM, Ramji et al., 2604.22709). Post-training Qwen3-8B/4B and Granite-4.0-Micro-3B: short sequence (~140 tokens) from a reserved "abstract" vocabulary replaces the verbal CoT. Stage 1 warm-up (SFT on masked CoT plus self-distillation to produce abstract tokens from the prompt), stage 2 RL under constrained decoding.
- Qwen3-8B (MATH-500 / AlpacaEval win / HotpotQA F1): base 82.4/52.4/51.1; SFT no-CoT 85.8/54.9/51.3; SFT+RL verbal 92.6/58.4/58.1 (1.7k tokens); Abstract-CoT warm-up 88.0/55.9/53.7; warm-up+RL 90.8/60.8/58.8 (144 tokens) **[shown]**. GPQA-D 50.5 vs 51.5; AIME25 24.4 vs 25.6.
- RL-only from the base model was at or below baseline (82.0). Pause tokens 78.6 (below baseline). Warm-up then RL needed **[shown]**.
- Closes ~74% of the gap between SFT-no-CoT and SFT+RL-CoT on MATH-500, and exceeds verbal on the judge-scored AlpacaEval **[shown, my arithmetic]**. Discrete latents make GRPO ordinary. Reported with instruction-following style prompts, not IFEval or tool use. Single run per cell as far as I can tell.

**ALAR, Adaptive Latent Agentic Reasoning** (Jung et al., 2606.02871, June 2026). The closest match to our plan. Per turn the model emits <LAT> + K=4 continuous thoughts (2-layer MLP projector on previous hidden state, fed back) or <THINK> text. LoRA r=16 on the base (not frozen) + projector.
- Action-Anchored Self-Distillation: the same model in thinking mode produces rollouts; keep only successful ones (21K for BFCL from ToolMind graph_syn; 76-86K for search); train latent mode with CE on the anchor action tokens only (tool calls), gradient through the K latents. No hidden-state or text target for the latents. Then AR-GRPO with success-conditioned reward to choose latent vs explicit per turn **[shown]**.
- BFCL AST (Qwen3-4B-Thinking): explicit 86.1 avg, 760 tokens; Stage 1 (always latent) 88.8, 87 tokens; Stage 2 89.2, 117 tokens (-85%). Length-compression baselines 85.1-88.4 at 156-251 tokens. K=1 87.4, 2 88.6, 4 89.2, 8 89.1 **[shown]**.
- Search-R1 Qwen2.5-3B/7B: avg EM 38.2->38.4 / 42.7->41.7 with 22-44% fewer tokens.
- Caveats: BFCL AST is single-turn exact match, already easy for the base (86%); no thinking-OFF baseline reported, so no "gap closed" number; no tau-bench; author-stated limitation that it needs successful teacher trajectories and inherits their coverage. Explicit CoT was used mostly on turn 1 (planning); later turns were mostly latent (search) **[shown]**.

**HybridAgent** (Zou et al., 2610.18861, Oct 13 2026 -- very recent, unreviewed). Qwen3-Base 4/8/14B, full post-training. HybridLink (2-layer MLP + residual) maps last hidden state to input-embedding space, regressed (cos+MSE) onto the embedding of the gold text token at latent positions. Two-pass self-conditioned SFT (second pass uses the model's own latent inputs). RL with exact rollout replay.
- 8B SFT: Coconut MATH500 51.4, SoftCoT 63.6, text SFT 78.2, HybridAgent-SFT 78.4; after RL 84.6 (GRPO 82.0). AIME25 13.1/16.5/30.0/30.8/39.2. Agentic tasks GAIA/WebWalker/HLE reported **[shown]**.
- Self-conditioning ablation (14B MATH500): activation-only 73.8 -> self-conditioned 84.2 **[shown]**. HybridLink ablation (14B, MATH500/MedQA/MuSiQue): identity feedback of raw hidden states 71.4/73.7/24.5 vs 2-layer MLP+residual 88.2/81.7/34.5 **[shown]**. Latent interventions (MATH500, 8B/14B, intact 84.6/88.2): cross-problem latent swap 44.8/48.6, mean-latent 53.6/58.4, random-token replacement 41.2/44.6, within-block permutation 73.2/76.4, forbidding latent mode (text only) 80.4/78.8, so the latents carry real, content-specific computation **[shown]**. Cuts text tokens 2.2-3.1x; 2.1x faster. Tool calls themselves are made in text mode.
- Not run on tau-bench/BFCL; latents are inside a model that is fully tuned.

### D. Pause, filler and thinking tokens

**Pause tokens** (Goyal et al., 2310.02226). 1B and 130M decoders pretrained from scratch on C4. Pause in pretrain AND finetune: gains on 8/9 tasks at 1B (SQuAD +18 EM, CommonsenseQA +8, GSM8K 7.5 -> 8.5). Standard pretrain + pause finetune only: "mixed", about 5 of 9 gains, smaller. Pause-pretrain + standard finetune: gains on 2 tasks. Filler periods in a standard model: no gain. Optimal pause count task-dependent **[shown]**. Reading: delays need a model that was taught to use them; absolute GSM8K is tiny.
- Other repos' pause baselines: Coconut GPT-2 GSM8k 16.4 vs 16.5 no-CoT; CCoT +1 point; Abstract-CoT Qwen3-8B -3.8 points; DCA +1.0 vs +5.4 for learned latents; Switch Qwen3-8B +5 GSM8K / +3 MATH **[shown]**. Content-free positions give little unless combined with a curriculum (Coconut pause-as-thought 24.1) **[shown]**.

**Filler tokens** (Pfau, Merrill, Bowman, 2404.15758). 34M Llama trained from scratch on 3SUM/2SUM-Transform: filler "......" lets the model solve tasks it fails without CoT, but only with dense, parallelizable-decomposition supervision; instance-adaptive (sequential) CoT demonstrations did not teach it to use filler **[shown, synthetic]**. Theory: helps only for problems with shallow quantifier depth. Relevance: multi-turn agent decisions are probably neither, so do not expect content-free laps to help **[suggested]**.

**Quiet-STaR** (Zelikman et al., 2403.09629). Mistral-7B continued pretraining on web text with learned thoughts at each token; zero-shot, no task finetuning: GSM8K 5.9 -> 10.9, CommonsenseQA 36.3 -> 47.2 (direct-answer accuracy, not comparable to CoT). Needs heavy pretraining-scale compute **[shown]**.

### E. Critical and analysis papers

- **Training Continuous CoT Models: A Tale of Two Regimes** (Yerram, He, Choi, 2607.16972). Llama-3.2-1B-Instruct and Qwen2.5-1.5B-Instruct. On compact (~25 token) and semi-natural (~62 token) GSM8k traces, direct (C-MTP) and indirect (CODI) supervision are within ~10% of CoT-SFT. On "realistic" traces the model's own correct generations on MATH (~350-550 tokens, rejection-sampled): Qwen-1.5B CoT-SFT 52.8 vs CODI-6/10/20 12.4-14.5 and C-MTP-2 14.2; Llama-1B 23.8 vs 7.4-9.9. Roughly 60-65% performance drop; errors are arithmetic slips/malformed expressions that accumulate **[shown, 2 backbones, 1B-1.5B]**. This is the closest match to our distill-own-thinking-trace plan.
- **Capabilities and Fundamental Limits of Latent CoT** (Zou et al., 2602.01148, theory + reanalysis of Coconut tables): argues latent models trade exploration for execution precision, and that direct (no-curriculum) training provably fails by distribution mismatch **[suggested, theoretical]**.
- **Do Latent Tokens Think?** (2512.21711, EMNLP 2026, abs). Coconut tokens barely respond to steering and promote shortcuts **[shown by authors]**. **Observable Patterns Are Not Explanations** (2606.12689, abs): Coconut/CODI patterns also appear in controls; latent use is graded, causal effect concentrated in low-rank directions **[shown]**.
- **Surveys.** Reasoning Beyond Language (Chen et al., 2505.16782): "current methods still underperform explicit CoT, largely due to training instability" and generalise poorly to novel structures. A Survey on Latent Reasoning (Zhu et al., 2507.06203) is a taxonomy, with no calibrated gap estimate. I found no 2026 survey that adds new gap numbers.
- Looped/recurrent-depth models (Huginn 2502.05171: 3.5B from scratch, GSM8K CoT rises with recurrence and saturates task-dependently, ~42% flex at r=32; Ouro 2510.25741, pretrained loops, abs; Retrofitting Recurrence 2511.07384: Llama-3.2-1B/OLMo/TinyLlama converted to prelude/recurrent/coda with a recurrence curriculum, beats the non-recurrent model at equal FLOPs on GSM8K/MATH after ~50B tokens of math continued training) **[shown, trained not frozen, math]**.

## 2. Gap closed on non-toy tasks (computed)

| Setting | Gap closed |
|---|---|
| GPT-2, GSM8k-Aug, CODI | 97% |
| Llama-1B/3B/8B GSM8k-Aug, CODI | 81% / 68% / 67% |
| same, CODI+SIM-CoT | 92% / 72% / 76% |
| Llama-1B/3B, Qwen-0.5B, KaVa | 77% / 76% / 81% (compact); 68% (3B, NL traces) |
| iCoT on GSM8K Mistral-7B / Phi-3 | 43% / 7% |
| CCoT Llama-2-7B GSM8K | 27-40% |
| Qwen3-8B, MATH-500 / GSM8K, Coconut/CODI/CoLaR | 51-61% / 79-83% |
| Qwen3-8B MATH, Abstract-CoT (discrete, RL) vs SFT-no-CoT->SFT+RL | ~74% |
| Own-trace MATH, Qwen-1.5B CODI | ~25% of CoT accuracy (no-CoT not given) |
| Hybrid with text kept (Switch-GRPO, Token Assorted) | ~100% or above |
| Frozen Qwen3-8B + LRT, Countdown-4, vs thinking mode | 48% |

Single seeds are common (CCoT, iCoT, SIM-CoT tables, Abstract-CoT). Differences under about 1.5 points are within noise in most of these.

## 3. Lessons for our block

1. **Do not train the loop on final-answer loss alone.** Coconut with no curriculum scored at no-CoT level (14.4 vs 16.5) and Abstract-CoT RL-only was at or below baseline. Give the block a teacher signal first. [shown, small models]
2. **Prefer a richer-than-one-vector distillation target.** CODI's single answer-preceding hidden state (all layers, L1, teacher stop-grad) is worth ~19 points over no distillation; KaVa's per-layer KV matching beats CODI by 2.6-4.7 points on compact traces and by far more on verbose traces (Qwen-0.5B NL: 44.4 vs 20.2); step-level decoding (SIM-CoT) is what keeps more than 4-5 latents trainable; CCoT found mid-depth states best. With a frozen backbone the thinking-ON teacher is a fixed target, so a KV/hidden-state target at the answer position plus CE on answer and tool-call tokens is cheap to compute. [suggested for our case; each component shown separately on math]
3. **Use outcome-token supervision on filtered own-rollouts as the base objective.** ALAR trains CE on action tokens only, conditioned on K=4 latents, using only successful thinking-mode rollouts, and matched the thinking model on BFCL AST. This is the closest recipe to "distill from the same backbone's thinking-ON answers". Filter by task success, not by judge score alone. [shown on single-turn BFCL; untested on multi-turn]
4. **Strip answer leakage from the teacher target.** Keeping the final CoT step in CODI's teacher cost 12 points. For us: cut the teacher's hidden states/KV at a point before the final reply or tool-call tokens. [shown]
5. **Train on your own latents.** Teacher-forced latents give an exposure-bias gap; HybridAgent's two-pass self-conditioning took MATH500 from 73.8 to 84.2 at 14B. Also keep the feedback vector on the input-embedding manifold (projection MLP with residual, norm control): raw hidden-state feedback gave nonsense RL rollouts in HRPO, and in HybridAgent's ablation identity feedback scored 71.4 vs 88.2 on MATH500 (14B). [shown]
6. **Start with few laps (4-6), add one at a time.** Optimum was 6 (CODI, SoftCoT), 4 (ALAR; 8 flat), c=2 (Coconut; c=3 spiked). Coconut collapses at 5+ latents without step supervision. Accuracy rises monotonically with latents only for frozen-LM coprocessors trained on huge data (DCA 4->64: +1.3 -> +10 on GSM8K) and for LRT's recurrent refiner. [shown]
7. **A frozen backbone caps gains, and the cap depends on block capacity and what the block can read.** SoftCoT (linear projector, frozen 1B assistant): +1 to +2 on GSM8K. LRT (11M trained, per-task): beats non-thinking CoT by ~19 average points but trails thinking mode on the two hardest tasks. DCA: +10 on GSM8K with a full-size coprocessor reading the KV cache and ~200B tokens. A generic frozen assistant can be worse than no latents. Give the block cross-attention to the backbone's KV/hidden states, size it generously (LRT: 7->28M helped), and expect "frozen + small block" to recover a fraction of the gap, not all. [shown; no tool-use evidence]
8. **Expect verbose self-generated thinking traces to be the hard case.** Tale of Two Regimes: on the model's own 350-550 token MATH traces, CODI fell to 12-15% vs CoT 53%. Fixes seen: KV-level targets (KaVa), keep a short text plan and use latents for routine turns (ALAR put explicit CoT mainly in turn 1), hybrid text+latent (Switch, Token Assorted), discrete abstract codes (Abstract-CoT). Before building, measure the length and per-turn distribution of LFM2.5's thinking on tau2-retail. [shown on math; untested on agents]
9. **RL only after distillation, with explicit exploration.** Naive GRPO on latent policies collapses (Latent-GRPO) or has zero variance (Dropout-GRPO). Working recipes: noise on latent inputs with one-sided noise and invalid-sample masking; shared dropout masks per rollout; discrete boundary/abstract tokens so ratios are defined; success-conditioned format rewards (ALAR). Because our judge reward attaches to sampled answer tokens, GRPO is defined on those; backprop through laps carries it to the block (Switch-GRPO). Gains seen: +7.9 to +14.8 points (Latent-GRPO, from a weak latent SFT start), +12.6 latent-conditional (Switch), +2.8 over warm-up (Abstract-CoT), +5.4 (CoLaR on MATH, still below CoT). Expect RL to move the number a few points and to shorten, not to rescue a bad distillation. [shown on math]
10. **Control for "extra positions" and "constant latent".** Pause-as-thought plus curriculum explained ~43% of Coconut's GSM8k gain; SoftCoT/EBM-CoT collapsed to near-constant latents; Coconut tokens barely react to steering in analysis papers. Our table should always include: thinking-OFF, thinking-ON, laps with a constant/shuffled board, and the trained block, plus a latent-perturbation test (HybridAgent: swapping in another problem's latents costs ~36-40 points, mean-latent ~30). [shown / suggested]
11. **Make the pass mark noise-aware.** 23/40 vs 30/40 is 7 tasks; one task = 2.5 points; binomial SE ~7.5-7.7 points at p=0.6. At the 67-77% gap-closed seen for the best distilled methods at 3-8B, the expected landing point is 23 + (0.67 to 0.77) x 7 = 27.7-28.4 tasks, i.e. just under thinking-ON and inside noise [untested extrapolation]. Use every available retail task (I recall ~114 in tau2 retail; verify) with repeated trials, or paired scoring. Also: Nemotron-Cascade 2 (2603.19220) reports that the official tau2 harness drops prior-turn reasoning, costing 3-5 points versus keeping the latest-turn reasoning; if the thinking-ON baseline was run under one policy and the loop under another, the comparison moves by as much as the gap [suggested; one model, secondary source].
12. **Persist the board across turns.** HybridAgent keeps a "continuous working memory" (KV) across turns; the tau2 retention result hints that carried reasoning state is worth points. A thinking board that survives between user turns is a candidate advantage over thinking-ON runs that discard it. [suggested, untested for us]

Not found in any paper: latent loops on a hybrid conv/attention MoE like LFM2.5, or latent feedback through MoE routers and short-conv layers. Treat router stability and conv-state handling of injected slots as [untested].

## 4. The three results most predictive of closing 23->30 silently

1. **ALAR on BFCL (2606.02871, Tables 2 and 4).** Latent K=4 thoughts, distilled from the model's own successful thinking-mode tool-call rollouts with LoRA, matched/exceeded the thinking model (86.1 -> 88.8 / 89.2) at ~85% fewer tokens, and explicit CoT was mostly needed on turn 1. If this transfers to multi-turn retail, the "silent" target is realistic. Weakness: single-turn AST, no thinking-OFF baseline, LoRA rather than frozen.
2. **Tale of Two Regimes (2607.16972) read with Switch's table (2606.13106).** On the model's own long traces, fully latent methods fall to ~25-40% of CoT, while hybrids reach parity only by keeping 1.4-1.7k text tokens. This predicts failure if tau2's thinking-ON turns are long and arithmetic-like, and success if they are short planning/policy-lookup steps. It is the main risk, and it can be checked before any training by measuring thinking length per turn.
3. **LRT on a frozen Qwen3-8B (2609.01117, Tables 1-2) with DCA (2412.17747).** A trained 11M recurrent block on a frozen decoder reaches 54 vs 35 average (non-thinking CoT) at ~1-2 TFLOP, is within 1-2 points of thinking mode on StrategyQA and MBPP, but gets only 48% of the way on Countdown-4 and reaches 41% of thinking-mode accuracy on HumanEval (37.8 vs 92.1). Frozen-backbone loops will probably recover part of the gap; the biggest and most efficient gains show up with a large block that reads the KV cache and with latent count scaling.

Calibration anchor: best distilled latent methods at 3-8B close 67-77% of the no-CoT to CoT gap in-distribution on math (SIM-CoT, KaVa), less on harder or verbose settings.
