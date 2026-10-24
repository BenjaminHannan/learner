# R4: Side modules, latent workspaces and agent evidence for a frozen LM (sweep dated 2026-10-24)

**Labels.** *Shown* = a controlled result in the cited paper. *Suggested* = the paper's reading, or my inference from a result. *Untested* = nobody has run it in our setting.
**Provenance.** Numbers came from arXiv HTML pages through a page summariser. For Qwen3, Klear-AgentForge and Nemotron-Cascade 2 I converted the PDFs locally and read the tables, so those are the most reliable. LFM layer facts come from the Hugging Face `config.json` files. Weak spots are flagged inline.

---

## 1. Closest prior: Liu et al., "Deliberation in Latent Space via Differentiable Cache Augmentation" (arXiv 2412.17747, ICML 2025)

**Setup.**
- Frozen Gemma-2 2B. The coprocessor is a full copy of the 2B model, initialised from it and fully finetuned (LoRA r=64/128 and from-scratch were also tried).
- It reads the frozen model's KV cache (all layers) plus N_L trainable soft tokens, and emits N_L latent embeddings.
- The latents are appended as extra inputs to the frozen decoder. Per 2510.00494's reading, only the coprocessor's final-layer output is fed back, as input embeddings. This is not a direct per-layer K/V write.
- The base works unchanged without them, and augmentation can run asynchronously.

**Training.**
- Loss: plain next-token LM loss on the Gemma pretraining mixture. No RL, no task data.
- Scale: 100k steps, batch 1024, 2048-token sequences, about 2.1e11 tokens.
- Only coprocessor and soft tokens get gradients. Each augmentation point predicts the next N_A=16 tokens by teacher forcing.
- 128 random augmentation points per sequence, packed into one pass with a custom mask (latents see only earlier original tokens).
- At benchmark time the coprocessor runs once, at the end of the prompt.

**Numbers (Table 2, accuracy %, 8-shot GSM8K, 5-shot MMLU):**

| N_L | 0 (base) | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|
| GSM8K | 21.38 | 22.67 | 23.12 | 24.72 | 26.76 | **31.43** |
| MMLU | 52.00 | 52.45 | 52.24 | 52.34 | 54.61 | 56.70 |
| MATH | 16.50 | 16.38 | 16.78 | 17.00 | 17.18 | 18.56 |
| ARC-c | 50.26 | 51.28 | 52.39 | 53.24 | 54.44 | 54.44 |
| BBH | 42.22 | 42.36 | 42.37 | 42.53 | 42.48 | 42.64 |

**Controls at 32 latents (shown):**
- Pause tokens: GSM8K 22.37, and first-token perplexity gets worse (11.63 vs 10.96 base).
- Zero-shot CoT: 23.20.
- Coprocessor reading last-layer activations instead of the KV cache: 23.20 (KV-cache read: 26.76).
- Coprocessor LoRA r=64 / r=128: 23.35 / 24.03.
- Coprocessor from scratch: 25.78. The search snippet reported 29.80 at 64 latents.
- Full finetune: 26.76.
- Lookahead N_A (16 latents): 4 → 24.03, 8 → 24.11, 16 → 24.72, 32 → 23.73.
- Perplexity drops 1.5% (8 latents) to 3.9% (64 latents) on the first token after the augmentation point, fading to 0.5-1.2% by position 32.

**Reading.**
- *Shown:* gains are monotone in N_L, beat the pause-token and CoT-prompt controls, and need the full-KV read plus a full-size, fully trained coprocessor.
- *Shown:* gains are task-uneven. BBH, HumanEval at low N_L, and several others are flat or negative. Lower perplexity does not guarantee benchmark gains.
- *Untested:* anything above 2B, RL, tool use, multi-turn.
- Caveats: no seeds. The paper gives two perplexity values (10.60 and 10.69) for the same setting. I could not confirm from the text whether the GSM8K answers still include text CoT (standard 8-shot does).
- **Cost to us:** the recipe needs about 2e11 tokens and a coprocessor the size of the base. Our block is much smaller and trained on far less.

---

## 2. Frozen-backbone latent reasoning, 2025-2026 (nearest to our plan)

### 2.1 Coda-Forno et al., "Exploring System 1 and 2 communication for latent reasoning" (2510.00494)
This is the most skeptical test of the Liu idea.
- Models: GPT-2 124M and Qwen3-0.6B.
- H1 = frozen base plus the coprocessor's per-layer KV concatenated into the base cache at every layer.
- H2 = Liu-style input-embedding injection with the base co-finetuned.
- Controls: "soft embeddings" and "continued pretraining" both train the base.

| GSM8K (N_L=12) | GPT-2 | Qwen3-0.6B |
|---|---|---|
| Soft embeddings (base trainable) | 26.5 | 38.5 |
| Liu et al. (frozen base) | 16.5 | 22.4 |
| H1 (frozen base, per-layer KV) | 12.0 | 24.0 |
| H2 (co-finetuned) | 31.5 | 38.6 |

- *Shown (small scale):* frozen-base variants trail the trainable-base variants by 15-20 points. Training the base is not necessary for large-scale perplexity gains: on the pretraining benchmark average, Qwen3 H1 got 47.2 vs 40.7 for continued pretraining. But for step-by-step reasoning the frozen base was the bottleneck.
- *Shown:* GSM8K is flat or dips as N_L grows, and gains flatten past N_L=8. Latents overlap heavily (mean off-diagonal capture 0.987).
- Authors' read: dual designs "mostly add compute."
- Caveat: the base is tiny and the supervision is Coconut-style CoT curriculum. The soft-embedding control also trains the base, so it is not a clean frozen comparison.

### 2.2 INTACT (2610.19568, Oct 2026): best structural match
- Frozen backbones: Llama-3.2-1B/3B, Llama-3.1-8B, Qwen2.5-3B.
- A 107M encoder reads the frozen model's final-layer hidden states over the question plus earlier latent blocks. It has 6 pre-norm layers; each cross-attends from c learned queries to the context.
- It emits K=4 blocks of c=4 vectors (16 latent positions), each conditioned on the frozen model's re-encoding of the earlier blocks. They go in as an input-embedding prefix after the question.
- **Stage 1:** per-token KL distillation of the model's own written-CoT continuation, where latent blocks stand in for the first i reasoning chunks. Plus a "preservation" KL on the model's own rollouts.
- **Stage 2:** group-relative policy gradient with a binary correctness reward. Only the encoder trains. The frozen LM's text sampling supplies the stochasticity, so no sampling of latents is needed.
- Results (GSM8K, frozen / S1 / S2): Llama-3.2-3B 75.8 / 77.9 / 79.3; Qwen2.5-3B 77.6 / 78.0 / 79.7; Llama-3.1-8B 72.3 / 83.7 / 83.6; Llama-3.2-1B 44.0 / 44.2 / 48.7.
- *Shown:* the 8B baseline of 72.3 is a prompt artifact. The same model with its native chat template reaches 78.4, so the real gain is about +5. Out-of-domain accuracy also moves (e.g. 8B: 53.9 → 72.1).
- *Shown:* RL adds little over distillation (-0.1 to +4.5) but shortens outputs.
- Ablations (Qwen2.5-3B):

| Variant | GSM8K |
|---|---|
| No preservation term (β=0) | **42.9** (collapses to short degraded outputs) |
| Gold-chain anchor | 74.0 |
| Frozen-rollout anchor | 76.2 |
| Student-rollout anchor (used) | 78.8 |
| Block width c=1 / 2 / 4 / 8 | 73.7 / 78.0 / 78.8 / 73.7 |
| Prefix swapped from another question | 70.9 (shuffled blocks: 77.0) |

- Progressive block construction beats joint or independent construction (84.4 vs 82.0 / 82.4 on 8B).
- Latency: 0.81× of the frozen model (3B, GSM8K), because outputs shorten.
- At 1B it loses to Aug-SFT, and Nemo-SFT (82.9) beats it at 3B. It is not a universal win.
- Caveat: math/commonsense only; no tool use or agents.

### 2.3 Latent Recurrent Thoughts (2609.01117, Sep 2026)
- Qwen3-8B fully frozen. The side network is about 11.2M parameters (0.14%): a ~4.2M bidirectional proposer that reads the question and emits K=32 latents (only 4 kept at inference), and a ~7M TRM-style recurrent refiner.
- The refiner has a 256-d working space with fast/slow states. It applies a bounded residual Δ to the latents. The result goes in as soft tokens after the prompt.
- Training: answer cross-entropy through the frozen decoder, 30 epochs per stage, plus a 0.01·‖Δ‖² penalty. No traces.

| Method | Countdown-4 | Sudoku | HumanEval | MBPP | StrategyQA |
|---|---|---|---|---|---|
| Direct | 27.8 | 17.3 | 13.4 | 28.7 | 67.4 |
| Zero-shot CoT (non-thinking) | 30.0 | 23.9 | 15.9 | 35.4 | 69.9 |
| SoftCoT | 5.9 | 10.4 | 20.7 | 40.2 | 70.2 |
| LRT | **56.7** | **49.2** | **37.8** | **51.5** | **75.1** |
| Thinking mode (reference) | 85.3 | 0.5 | 92.1 | 49.3 | 76.4 |

- *Shown (Countdown-4):* both instance-conditioning and recurrence matter. Prefix-tuning 12.5, P-tuning v2 28.4, instance-conditioned proposer alone 42.0, plus recurrent refinement 56.7. A non-recurrent refiner with the same budget gets 47.5.
- *Shown:* regenerating the latents instead of a bounded residual Δ costs roughly 33-44 average points.
- *Shown:* SoftCoT and EBM-CoT collapse to near-identical latents across instances.
- Limits: one proposer per task family, no transfer test, a single backbone scale, and thinking mode still wins on 3 of 5 tasks. The mechanistic probes are correlational (57.5% vs 52.5% majority).

### 2.4 Other 2025-2026 items

| Paper | What it adds | Source |
|---|---|---|
| SoftCoT (2502.12134) and Self-SoftCoT (ACL 2026) | Frozen LLM plus a trained projection of soft thoughts. Self-SoftCoT uses GSPO and per-position projections to stop latents homogenising. With N=2 soft tokens it averages 78.42 vs 75.06 (Qwen2.5) and 74.55 vs 70.52 (Llama-3.1) for the SoftCoT baseline. | search snippets, not read in full |
| KaVa (2510.02312, ICLR 2026) | Distils a teacher's compressed KV cache (R-KV eviction to M latents) into latent steps with L1/MSE on K and V, plus CODI. LoRA-tuned 0.5B-3B backbones, 24 latents. GSM8k-Aug, Llama-1B: KaVa 56.5 vs CODI 55.6, PCCoT 53.4, Coconut 45.3, CoT 61.6. Also 62-92% fewer forward passes. | read |
| Switch (2606.13106) | Qwen3-8B. Latent steps feed the last hidden state back as the next input. Switch-GRPO lifts MATH-500 from 66.7 to 79.3 (text-CoT SFT: 80.6) and GSM8K from 80.2 to 89.2 (text-CoT SFT: 88.6). Reward hacking late: switch rate 100%, about 13 latent steps. Latent positions get gradients only indirectly through the KV cache. | read |
| Thinking States (2602.08332, Google, Feb 2026) | A 1-layer thinking block writes text thoughts every few input tokens. A 1-layer compression block pools them to a fixed state, **added** to the input embeddings after layer 1. Trained by teacher forcing, no BPTT. Qwen2.5-1.5B finetuned: GSM 42.2 vs CoT 60.5 at 2.7× speed; Coconut 32.7. Backbone is finetuned, not frozen. | read |
| Soft Tokens, Hard Truths (2509.19170) | RL on continuous CoT with noise on the input embeddings for exploration, up to 8B. Matches discrete CoT at pass@1 and beats it at pass@32. Train soft, infer hard works best. | abstract only |
| Memorilla (2610.21375) | Frozen Qwen3-4B-Instruct-2507 agent. A trainable module compresses a frozen encoder's trajectory embeddings into K=8 soft tokens placed before the prompt. GRPO on sparse reward in TextWorld: 24.2% vs 18.6% full-history ICL. **Untrained (random) memory: 15.3%, worse than ICL.** The closest agentic frozen-LM latent-slot paper (a game, not tool-calling). | read |
| Trained Persistent Memory for Frozen LLMs (2603.22329) | Frozen GPT-2, six write-back routes, one seed, a memory-retention task (not reasoning). Zero-init scalar-gated parallel cross-attention retained 9.0%. Hebbian 9.2%, sparse-slot write 7.1%. Prefix, KV-extension and sigmoid-gated branch with negative bias retained about 0% at 1× capacity. At 10× all converge to 7.6-10.3%. | read |
| LoopUS (2605.11011) | Splits a pretrained LLM into encoder / looped middle / decoder, with a Mamba-style selective gate. About +1.6 to +2.2 average points on Qwen3 1.7B-8B, and flat on MMLU. Sigmoid gating and no-gate both gave higher final loss. Naive reuse of the middle block drifts. | read |
| Retrofitted recurrence (2511.07384) | Loop a middle block with a linear adapter and a curriculum. Better than post-training at equal compute on GSM-style math. | abstract only |
| ReLAR (2606.17524) | Additive steps on the final hidden state with a depth controller and critic. The base LM is trained, not frozen. 0.14 s vs 9.09 s for CoT. | read |
| Universal Reasoner (2505.19075) | Small RL-trained module whose logits are **added** to the frozen LM's logits. Composable. | abstract only |
| LatentMAS (2511.20639) | Training-free sharing of layer-wise KV caches as "latent working memory" between agents. Claims +13.3% accuracy and 4.3× speed (self-reported). | search summary only |

**Gaps.** I found no 2026 paper applying a latent coprocessor, board or soft-token module to function-calling or tool-use agents (only Memorilla, in a game). I found no RL follow-up to Liu et al. and no LLM-judge reward on a frozen-backbone latent module.

---

## 3. Gated and zero-init side modules (the mechanics)

| Paper | Attach point | Gate / init | Key evidence |
|---|---|---|---|
| Flamingo (2204.14198) | Gated cross-attn + FFN before frozen LM layers | `tanh(α)`, α init 0, per layer | Flamingo-3B overall: with gate 70.7, without 66.5. Cross-attn every layer 70.7, every 4th 68.8, every 2nd 68.2, **single in the middle 59.8**. Frozen LM 70.7 vs finetuned 62.7 vs from scratch 57.8. *Shown* (vision-language). |
| LLaMA-Adapter (2303.16199) | Learnable prompts in the top 30 of 32 layers | Zero-init gating on the adapter attention | ScienceQA val: zero-init 83.85 vs random-init 40.77. Layers inserted: 10 → 55.95, 20 → 73.36, 30 → 83.85, 32 → 81.03. 1.2M params, 1 h on 8×A100. *Shown*. |
| CALM (2401.02412) | Cross-attn from anchor to augmenting model, every 4th layer, residual add | Both models frozen | HumanEval 16.4 → 22.5; GSM8K high-resource 28.0 → 31.8; encoder-only use of the second model drops HumanEval to 16.0; same-parameter LoRA gets 18.3. Adds about 1.5% parameters. Zero-init not documented. |
| ControlNet (2302.05543) | Trainable branch into a locked model | Zero convolutions | Abstract claims stable training on small and large data. Not re-fetched beyond the abstract. |
| LST (2206.06522) | Side network fed by ladder shortcuts from the backbone | n/a | 69% training-memory saving. No backprop through the backbone. |
| Tandem (2402.08644) | Small model attends to a large model's representations | n/a | +3.3% next-token accuracy over the small model alone. An efficiency paper. |
| LongMem (2306.07174) | Frozen backbone as memory encoder, residual SideNet reads it | n/a | 65k-token memory, beats long-context baselines on ChapterBreak. |
| Block-Recurrent Transformer (2203.07852) | One recurrent layer at layer 10 of 12 | **Fixed** gate beats LSTM gates | 512 state vectors; 128 → 3.54, 512 → 3.53, 2048 → 3.55 bits/token. Adjacent recurrent layers (9+10) gave no gain. Trained from scratch. |

Lineage not re-read this sweep: Recurrent Memory Transformer (2207.06881, memory tokens plus segment recurrence), ViT registers (2309.16588, extra tokens absorb high-norm artifacts), Gist tokens (2304.08467, 26× prompt compression via attention masks), Memorizing Transformers (2203.08913), Goyal et al. shared global workspace (2103.01197, limited-capacity workspace with competitive writes), Huginn recurrent depth (2502.05171), Pause tokens (2310.02226, gains need pause tokens in pretraining; +18% SQuAD EM, +1% GSM8K at 1B). Anthropic's July 2026 "global workspace" work (J-space) finds a small set of internal patterns whose ablation kills multi-step reasoning. It gives no layer range or injection recipe, so it is only suggestive.

---

## 4. Agentic evidence: what thinking buys on tau-bench-style tasks

**Paired thinking on/off, same model family** (Qwen3 table values are from local PDF conversion of the Qwen3 report; tau numbers from Hugging Face cards and Klear-AgentForge's own evaluation):

| Model | Metric | Off | On | Gap |
|---|---|---|---|---|
| Qwen3-4B | tau2 Retail / Airline / Telecom | 28.1 / 12.0 / 17.5 | 38.6 / 28.0 / 17.5 | +10.5 / +16 / 0 |
| Qwen3-4B | tau1 Retail | 24.3 | 33.9 | +9.6 |
| Qwen3-4B-2507 (separate Instruct and Thinking checkpoints) | tau2 Retail | 40.4 | 53.5 | +13.1 |
| Qwen3-8B (Klear, own eval) | tau-bench Retail / Airline | 35.7 / 12.0 | 45.2 / 25.0 | +9.5 / +13 |
| Qwen3-32B (Klear, own eval) | tau-bench Retail / Airline | 40.0 / 20.0 | 48.7 / 28.0 | +8.7 / +8 |
| Qwen3 0.6B / 1.7B / 4B / 8B / 14B / 30B-A3B / 32B / 235B | BFCL v3 | 44.1 / 52.2 / 57.6 / 60.2 / 61.5 / 58.6 / 63.0 / 68.0 | 46.4 / 56.6 / 65.9 / 68.1 / 70.4 / 69.1 / 70.3 / 70.8 | +2.3 / +4.4 / +8.3 / +7.9 / +8.9 / +10.5 / +7.3 / +2.8 |

Reading:
- *Shown:* thinking is worth about +9 to +10 points on tau retail for 4B-32B hybrids. This is a similar order to our 23/40 → 30/40 (57.5% → 75%).
- *Shown:* the BFCL v3 gain is small for sub-2B models. Thinking helps most when the model is big enough to use it.
- **Our 7-task gap is statistically soft.** Unpaired z ≈ 1.66, p ≈ 0.10 on n=40. One task is 2.5 points.

**Why thinking helps (and when it does not):**
1. **Failure types.** Original tau-bench (2406.12045), gpt-4o function-calling, retail: about half the agent failures are wrong arguments or information (hallucinated IDs, omitted information, bad arithmetic). Roughly a quarter are rule-following mistakes (e.g. several exchange calls where policy allows one). About a fifth are partial handling of compound requests. The percentages in the source are garbled, so treat them as approximate.
   - Removing the policy text costs gpt-4o 4.4 points on retail and 22.4 on airline.
   - Adding a "think" function to function-calling agents did not help, while ReAct-style reasoning helped text-format agents.
2. **The think tool.** Anthropic's think-tool post (Claude 3.7 Sonnet) says the scratchpad is used to list applicable rules, check that required information is collected, check a planned action against policy, and check tool results.
   - Airline pass^1 rose from about 0.33-0.37 to about 0.57-0.58. The post's text and table disagree slightly.
   - Retail is much flatter: baseline 0.783, think 0.812, extended thinking 0.770.
   - It helps in long, policy-heavy chains and not on single calls.
3. **Thinking can hurt when it never reaches the action.** "Thinking Is Not Telling" (2602.07796) tested an enforced think tool on five strong models. Retail pass^1 fell for GPT-4o (64.1 → 59.7), GPT-4.1 (73.3 → 65.5), GPT-5 (74.8 → 69.6) and DeepSeek-V3.1 (71.0 → 63.5). It rose for gpt-oss-120b (63.8 → 66.7). Its explanation: private reasoning is not reliably turned into user-visible disclosure. Injecting the decision-relevant facts helped most. This is a think tool, not a native reasoning mode, so it is partial evidence.
4. **Carrying thoughts across turns.** Nemotron-Cascade 2 (2603.19220) found the official tau2 harness drops all prior reasoning. Keeping the latest turn's reasoning added 3-5 points. Keeping all prior reasoning was no better. Self-reported, with SFT built to match that policy.
5. **Overthinking.** Klear-AgentForge (2511.05951) SFT'd a reasoning model on agent data. Scores fell to about 0 because it spent the 64k budget thinking before a tool call. The Qwen3.5-0.8B card warns of thinking loops. A secondary summary says the CCTU benchmark found some models do not benefit from thinking; I did not verify it.

**What the silent loop must replicate** (my synthesis, *suggested*): (a) grounding arguments from tool outputs (pick the right ID, compute the total), (b) checking the planned call against policy, (c) tracking multi-part requests across turns, (d) carrying the plan to the next turn. Items (a)-(b) are what the think-tool and tau-bench failure analyses name. Item (d) is supported only by the Nemotron thought-retention finding. All four are *untested* for latent loops.

---

## 5. Architecture facts for the two backbones

**LFM2.5-24B-A2B** (`config.json`, Lfm2MoeForCausalLM; model card; blog):
- 24.0B total / 2.45B active. 40 layers, hidden size 2048, vocab 128,000, context 131,072, RoPE θ=1e7, tied embeddings.
- **10 GQA attention layers at indices 2, 6, 10, 14, 18, 22, 26, 30, 34, 38** (every 4th from layer 2). The other 30 are gated short-conv blocks (kernel 3, state width 3).
- Attention: 32 query / 8 KV heads, head dim 64. Only the 10 attention layers keep a KV cache.
- Layers 0-1 use a dense FFN (11,776). Layers 2-39 are MoE: 64 experts, top-4, expert FFN width 1536.
- Pretraining 33T tokens.
- Post-training: SFT, teacher specialisation, non-agentic MOPD, agentic MOPD, agentic RL inside OpenClaw, Hermes, Pi and OpenCode harnesses.
- **It is a reasoning-only model.** The chat template opens every assistant turn with `<think>`, and no supported non-thinking mode is documented.
  - So our "thinking-off" arm is probably a forced empty think block, which is off-distribution. It may understate what a trained non-thinking mode would score. Check how that arm was built.
  - Qwen's own report shows non-thinking mode needs explicit training: Qwen3-32B BFCL v3 stage-4 non-thinking is 63.0 vs thinking 70.3.
- Liquid reports BFCLv4 65.01 and τ³-Bench Banking 8.04 for it. I found no tau2-retail number.

**LFM2-8B-A1B** (tech report 2511.23404; `config.json`): 24 layers, hidden size 2048, 6 attention layers at 2, 6, 10, 14, 18, 21, and 18 conv. First 2 layers dense. 32 experts top-4, expert FFN 1792. Tech report: GQA with RoPE and QK-norm. A hardware-in-the-loop search chose a minimal hybrid, and the paper gives no sweep over the attention-layer count.

**Qwen3.5-0.8B pilot** (model card): 24 layers, hidden size 1024, 18 Gated DeltaNet plus 6 gated-attention layers (3:1), 2 KV heads of dim 256. Non-thinking by default.
- Its card scores (thinking): TAU2-Bench 11.6, BFCL-V4 25.3 (the 2B scores 48.8 and 43.6).
- *Suggested:* at 11.6 the 0.8B is near the floor on full tau2, and the card calls it prone to thinking loops. A tau2-retail pilot there will be mostly noise. Use a metric with headroom, and distinguish "board helps" from "board does not break it."

---

## 6. Lessons for our block

1. **Zero-init the write-back and keep a scalar gate.** *(Shown)* Flamingo `tanh(α)` with α=0 beats no gate (70.7 vs 66.5). LLaMA-Adapter zero-init gating beats random init (83.85 vs 40.77 ScienceQA). Memorilla's random-init memory tokens made a frozen agent worse than no memory (15.3% vs 18.6%). In the frozen-GPT-2 memory study, scalar-zero cross-attention (β=0) worked, while a sigmoid gate with a negative bias init retained about nothing at small capacity (*suggested*, one seed, a different task). Prefer `tanh(α)` per layer, and log α per layer. Fixed or simple gates also beat input-dependent ones (BRT, LoopUS).
2. **Init at identity is not enough. Add an explicit behaviour-preservation term.** *(Shown)* INTACT without its preservation KL collapsed to short degraded outputs (GSM8K 42.9 vs 78.8). Student-rollout anchoring beat gold-CoT and frozen-rollout anchors. This matters for our RL stage, where a judge reward can drift the model. Keep a KL to the frozen model's own distribution.
3. **Write at multiple depths, not one.** *(Shown, other settings)* Flamingo's single middle cross-attention scored 59.8 vs 70.7 at every layer, and every-4th scored 68.8. LLaMA-Adapter did best with 30 of 32 layers. CALM used every 4th. For LFM, a board read at each of the attention positions from the middle on (18, 22, 26, 30, 34, 38) is a defensible first guess. *Untested* on a hybrid MoE.
4. **KV-cache slots only reach 10 of 40 LFM layers.** The conv layers cannot read slots appended to a KV cache. A residual cross-attention read (board → hidden state, gated) can sit after any layer type. If we want the frozen model to read the board natively, Liu's trick is to emit embeddings and let the frozen decoder compute their K/V, so they are in-distribution. Direct K/V synthesis (H1 in 2510.00494) was no better than that. *Untested:* which is better on LFM.
5. **Read from the whole model, not the last layer.** *(Shown, one model)* Liu: KV-cache read 26.76 vs last-layer read 23.20 GSM8K. Tap several layers (including conv-layer outputs) as keys/values for the board's reads.
6. **Board size: K=16-64 total positions is the tested sweet range, and laps beat slots.** *(Shown)* Liu's gains rise through 64. BRT saturates by 128-512 and degrades at 2048. INTACT's best width is c=4 (K=4 blocks). 2510.00494 saw GSM8K flat past about 8-12. LRT: recurrence beats a non-recurrent block of equal budget (56.7 vs 47.5 Countdown). INTACT: sequential blocks, each conditioned on the frozen model's re-encoding of earlier ones, beat joint construction (84.4 vs 82.0). Design the laps as a sequential, bounded-residual refinement of the slots (LRT: a free regeneration cost 33-44 points).
7. **Make the board instance-dependent and test for collapse.** *(Shown)* SoftCoT and EBM-CoT latents collapse to near-identical vectors across inputs. LRT's constant-prefix controls scored 12.5-28.4. INTACT's swapped-question prefix dropped GSM8K from 78.8 to 70.9. Use a swap/shuffle control in every eval, and check mean pairwise slot similarity.
8. **Training signal: distil from the same model's thinking-on outputs, then RL, and don't expect much from RL.** *(Shown for math)* INTACT is our recipe at small scale: KL on the CoT continuation, then correctness RL. It gave +1.4 to +5 over the correctly-prompted frozen baseline, with RL contributing -0.1 to +4.5. KaVa's KV-cache distillation (match the teacher's compressed K/V) is a richer teacher signal. On GSM8k-Aug it beat CODI's hidden-state matching by +0.9 (Llama-1B), +4.7 (Llama-3B) and +9.4 (Qwen-0.5B), with LoRA-tuned backbones. Teacher-forced thought supervision (Thinking States) avoids backprop through the laps, but got 42.2 vs CoT 60.5 on GSM. *Untested:* an LLM-judge reward, and agentic rewards, on a latent module. Switch's late reward hacking (100% switch rate, about 13 latent steps) is a warning to add a lap-count cost and to audit judge-reward exploitation.
9. **RL on a frozen backbone works through the frozen model's own sampling.** *(Shown)* INTACT backpropagates an advantage-weighted log-likelihood of sampled text into the encoder. Memorilla's GRPO on K=8 soft tokens worked with sparse reward. Soft Tokens/Hard Truths adds noise on the latents for exploration when the latents themselves must be sampled. Plan for the board to receive gradient only via the text policy's likelihood, so expect weak signal per update.
10. **Replicate the four things thinking does for the agent, and test each separately.** Argument grounding, policy checks, compound-request tracking, and cross-turn carry-over. These are what the failure analyses in section 4 name. Build four small probes, since the thinking-on/off gap on n=40 is only 1.7 SE. Use all 114 tau2 retail tasks with several trials, or per-failure-type diagnostics. Fix the pass marks before running.
11. **Persist the board across turns.** *(Suggested)* The official tau2 harness discards prior reasoning, and keeping the latest turn's reasoning added 3-5 points in Nemotron-Cascade 2. A board stored as state outside the text is a natural, cheap place to carry that. *Untested.*
12. **Cap the laps.** Klear's reasoning-SFT agent hit its budget before acting and scored about 0. Use a fixed lap count (or a learned halt with a hard max) so the silent loop can never replace the action.

### The three results most predictive for our case
1. **Liu et al. (2412.17747):** a frozen decoder plus a KV-reading coprocessor gives GSM8K 21.4 → 31.4 with 64 latents under pure LM loss. It beats pause tokens (22.4) and CoT prompting (23.2). The catch is scale (2e11 tokens, full-size coprocessor) and uneven gains (BBH flat).
2. **Coda-Forno et al. (2510.00494):** at small scale a frozen base capped GSM8K at 22-24 while a simple trainable-base soft-token control reached 38.5. This sets honest expectations. If the block cannot move the backbone, it must be wide, deep-injecting and multi-site.
3. **INTACT (2610.19568):** the only published recipe matching "distil from the same backbone's CoT, then RL, backbone frozen". It shows modest real gains over a correctly prompted baseline, a necessary preservation anchor, and small RL gains. It also leaves our target (tool-using agents, LLM-judge reward) wholly untested.

*Honourable mention for the agent side:* "Thinking Is Not Telling" shows that thinking only pays when it changes the visible action, which argues for training the board against action correctness, not reasoning quality.
