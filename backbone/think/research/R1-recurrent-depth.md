# R1: Recurrent-depth / looped transformers and retrofitting recurrence (sweep dated 2026-10-24)

Labels: **(S)** shown in the paper with numbers; **(Sg)** suggested/argued, not tested directly; **(U)** untested. Numbers were read from arXiv HTML pages or GitHub through a summarising fetch tool. I re-checked the McLeish tables against the raw HTML. The other numbers are as extracted. Papers with 2026 IDs (2601-2610) are beyond my training data, so I relied on fetched text only.

Skeptic's headline: every clean positive retrofit result below used full-weight training on 1e9 to 1e11 tokens. The only LoRA-on-frozen-backbone retrofits are (a) a synthetic rule-chain task with per-lap labels (2608.11233) and (b) a negative result against compute-matched 1-pass LoRA (GitHub "Newt", single author, not peer reviewed). That is the closest published evidence to our setup.

---

## 1. Foundational from-scratch work

### Huginn (Geiping et al. 2025), arXiv:2502.05171
- **Setup:** from scratch, 3.5B params, ~800B tokens, prelude 2 / core 4 / coda 2 layers (S). Effective depth is 2+4r+2, so 132 layers at r=32.
- **Mechanism (S):**
  - Input embedding e is re-injected every lap through a linear adapter on concat(state, e) (2h to h). Concat beat add at scale.
  - State init is random (truncated normal). Sandwich RMSNorm. Lap count r per sequence ~ log-normal Poisson (mean 32, sigma 0.5). Backprop through only the last k=8 laps.
  - Wrong norms or init caused representation collapse. One run learned to ignore the state, with validation perplexity identical at 1 and 32 laps.
- **Lap curve (S, Table 1):**

| Task | r=4 | r=8 | r=16 | r=32 |
|---|---|---|---|---|
| ARC-E | 49.1 | 65.1 | 69.5 | 69.9 |
| HellaSwag | 43.5 | 58.5 | 64.7 | 65.2 |
| MMLU | 23.4 | 25.3 | 31.3 | 31.4 |
| OBQA | 28.2 | 35.4 | 37.6 | 38.8 |
| SciQ | 80.0 | 92.1 | 93.9 | 93.5 |

  - Most of the gain comes between r=4 and r=8. After r=16 the gain is under 1 point (SciQ drops slightly).
  - HellaSwag and ARC-C saturate at about 8-12 laps. GSM8K-CoT keeps rising. GSM8K flexible is 28 at r=32 and 47 for an EMA checkpoint at r=64. MATH ~12. HumanEval 23.
  - At 180B tokens versus a fixed-depth baseline trained on the same tokens: GSM8K-CoT 9.0 vs 1.8, ARC-E 53.6 vs 46.4. That baseline is matched on tokens, not on inference FLOPs (the recurrent model runs up to 32 laps), so it is not compute-matched.
- **Exit and KV (S):** KL-based exit at 5e-4. MT-Bench goes from 5.63 to 5.56 with early exit. KV cache slot (i mod k) with budget 4 gives 5.86. Both are single MT-Bench checks that the paper calls preliminary.
- **Failure modes (S):** weak factual recall (open-book minus closed-book OBQA is +11). Some latent trajectories orbit instead of converging. Under-trained overall.
- **Independent check (S for the negative):** Lu et al. 2025, arXiv:2507.02199, probed Huginn with logit lens and coda lens on arithmetic. They found no clear latent chain-of-thought, only marginal gains from more laps, and well below explicit CoT.

### Saunshi et al. 2025, arXiv:2502.17416 (ICLR 2025)
- **Synthetic (S):** a k-layer block looped L times nearly matches kL layers on addition, p-hop induction and i-GSM. Examples: addition at n=32: loop 2x6 gives 99.5 vs non-looped 2-layer 38.8. i-GSM: loop 1x8 gives 73.2 vs 1-layer 24.5.
- **1B LM on the Pile (S, Table 3):**
  - 12-layer block looped x2: perplexity 7.90 vs the 24-layer baseline's 7.40 (worse), but math word problems 34.3 vs 29.3 and reasoning primitives 51.2 vs 47.5.
  - A middle-loop design (4 layers, then 4 looped, then 1 more) is 7.81 perplexity with primitives 56.5.
  - Looped models are worse at closed-book QA than the equal-FLOP baseline.
- **Regulariser (S):** pushing a k-layer block of a normal model to resemble a looped one (k=4, lambda=10) raised the all-task average from 26.0 to 30.0 at unchanged perplexity. This is single-seed, from scratch.
- **Take-away:** looping buys reasoning, not knowledge. Perplexity is the wrong yardstick.

### Mixture-of-Recursions (Bae et al. 2025), arXiv:2507.10524
- **Setup:** from scratch, 135M to 1.7B, a router assigns each token a recursion depth (S).
- **Result (S, Table 3, 16.5e18 FLOPs):**
  - Vanilla 315M: few-shot avg 42.3.
  - MoR expert-choice at Nr=2 (167M params): 43.1.
  - Plain recursive at Nr=2: 42.6. At Nr=4 it falls to 41.0.
  - Token-choice routing is clearly worse (40.0).
- **Limits:** the recursive rows use slightly different token counts, so matching is approximate. It is below vanilla at 135M. Uptraining a pretrained model is listed as future work (U). Accuracy falls as Nr rises from 2 to 4.

### Relaxed Recursive Transformers (Bae et al. 2024), arXiv:2410.20672 (ICLR 2025)
- **Setup:** retrofit. Gemma-2B (18 layers) is tied into 9 layers looped twice, then uptrained with distillation on 15B-60B tokens (S).
- **Result (S):**
  - Tied "Recursive" Gemma at 15B tokens: 51.7 avg vs 38.2 for the same size pretrained from scratch.
  - Per-loop LoRA (rank 512) recovers 58.4 vs the full model's 58.6. Rank 64 recovers much less.
  - Stepwise init beat other inits for tied models. Average init was best for the relaxed (LoRA) ones.
  - SVD init of the LoRA is worth up to 6.5 points over zero init at rank 512.
- **Caveat:** this is parameter compression, not extra compute. The 2-3x throughput claim is an oracle-exit analysis, not measured (S as stated by the authors).

---

## 2. Retrofitting pretrained models (most relevant to us)

### McLeish et al. 2025, arXiv:2511.07384 (NeurIPS 2025)
- **Setup:** full-weight conversion of TinyLlama-1.1B (22 layers), OLMo-2-1B and Llama-3.2-1B. Layers are dropped (S).
  - TinyLlama: (4 prelude, 8 core, 4 coda), keeping layers 0-3, 10-17, 18-21 and dropping 4-9. About 72.7% of parameters remain.
  - OLMo and Llama: (4, 6, 4), dropping layers 4-5.
  - All kept layers start from pretrained weights. Keeping early layers as prelude and late layers as core/coda beat ShortGPT-style pruning. Widening prelude/coda to (7,8,7) gave negligible gain.
- **Mechanism (S):**
  - Linear adapter on concat(prelude output, state), 2h to h, at every lap. The initial state is Gaussian noise.
  - Poisson-lognormal lap count. Backprop through at most 8 laps.
  - The curriculum raises the mean lap count over training (1-sqrt schedule for 75% of training, then constant). Scheduling the mean was efficient in data and compute. Scheduling the max backprop depth was cheaper in FLOPs but worse per step.
  - An additive adapter gave higher training loss but similar eval accuracy.
- **Data (S):** ~50B tokens of Nemotron-CC-Math for the main math runs. Mixture study: 26B tokens, with a two-phase variant that adds 26B FineWeb-Edu "healing" first. Init study: 120B tokens.
- **Results (S, raw tables, GSM8K / MATH, "Non-recurrent" = parent trained on the same data):**

| Model | Non-recurrent | train-rec 4, test 4 | train 8, test 8 | train 32, test 1 | train 32, test 2 | train 32, test 32 |
|---|---|---|---|---|---|---|
| Llama-1B | 37.1 / 27.4 | 39.4 / 29.0 | 44.3 / 29.3 | 6.4 / 10.5 | 25.5 / 23.0 | 49.4 / 31.5 |
| OLMo-1B | 35.3 / 25.1 | 38.7 / 27.8 | 44.4 / 28.2 | 10.4 / 11.2 | 30.6 / 22.0 | 51.6 / 29.3 |
| TinyLlama | 26.6 / 24.0 | 38.0 / 25.9 | 40.9 / 26.1 | 5.6 / 9.1 | 24.2 / 19.1 | 45.0 / 27.1 |

  - Reading the table: the recurrent model is far worse than the parent at 1 lap and roughly equal at 2 laps (about 30 GSM8K for OLMo train-32). It breaks even at ~4 laps and gains +7 to +16 GSM8K at 8-32 laps.
  - Higher training recurrence gives a higher ceiling but a worse low-lap floor.
  - Beyond the training recurrence, accuracy is flat to slightly rising. It does not collapse.
  - Equal-FLOPs claim: the paper says recurrent models "efficiently outperform" the baseline per training FLOP. The curves are in figures. The inference claim is only "competitive with the fixed depth baseline and can outperform it by using more FLOPs." No equal-inference-FLOP comparison against a larger or deeper non-recurrent model.
- **What did not move (S):**
  - Non-math tasks are flat or worse than the parent. Llama ARC-C is 38.2 for the parent vs ~36-37 recurrent. MMLU is 38.7 vs ~36-38.5.
  - Math-only single-phase training dropped TinyLlama ARC-C and MMLU below the static baseline. Two-phase healing recovered most of it.
  - Math-only training also cut HellaSwag for both recurrent and static models (TinyLlama 59 to 43-45), so the damage is from the data, not the loop.
- **From-scratch vs retrofit (S):** a retrofit initialised from Llama beat a random-init scratch model after 120B tokens. Extrapolated crossover is ~950B tokens, "an underestimate".
- **Limits the authors name:** ~1B scale and ≤50B tokens. Only math was targeted. No adaptive stopping. Layer choice is a heuristic. Seeds and variance are not reported. LoopUS (below) notes that this paper's TinyLlama average went 52.1 to 49.3.

### Ouro / LoopLM (ByteDance et al., Oct 2025, v5 Jul 2026), arXiv:2510.25741
- **Setup:** from scratch, 1.4B (24 layers x 4 laps) and 2.6B (48 layers via upcycling). 7.7T tokens over 5 stages (S).
- **Mechanism (S):** sandwich RMSNorm. One shared stack looped 4 times. Per-lap LM loss weighted by exit probability, with an entropy term against a uniform prior (KL beta 0.1 then 0.05). A learned exit gate trained in a second stage with the LM frozen. The target is based on per-lap loss improvement. I could not confirm from the text I read whether the original embedding is re-injected. The paper describes the loop as passing the latent state forward (U).
- **Lap training (S):** 8 laps caused loss spikes, so they trained at 4.
- **Results (S):** 1.4B R4: GSM8K 78.9, MATH500 82.4, MMLU 67.4. These beat Qwen3-4B on math (72.9 and 59.6) but trail it on MMLU (73.2) and HumanEval.
- **Lap curve (S, base 1.4B):**

| Lap | ARC-C | MMLU | Winogrande |
|---|---|---|---|
| 1 | 37.6 | 41.2 | 57.0 |
| 2 | 54.9 | 60.4 | 66.7 |
| 3 | 59.5 | 66.7 | 71.4 |
| 4 | 60.9 | 67.5 | 72.3 |
| 5 | 59.0 | 66.6 | 70.3 |
| 8 | 58.2 | 64.5 | 69.3 |

  - Overthinking is mild for base models. For the thinking-SFT 1.4B, AIME24 goes 65.0 at lap 4, 60.7 at lap 5, 38.7 at lap 8, and OlympiadBench 71.6 to 66.8. The 2.6B thinking model degrades faster at laps 6-8.
  - The thinking-model numbers come from a different eval setup than the main table.
- **Exit (S):** the learned gate gives ~66 vs ~64 for the standard gate at 2.5 average laps (MMLU, read from a figure).
- **KV (S):** sharing KV across laps in prefill costs >10 GSM8K points. At decode, a last-lap-only cache costs ~0 (78.85 vs 78.92 GSM8K). First-lap-only collapses (18.7).
- **Knowledge (S):** looping does not raise storage capacity (Capo, ~2 bits/param, both ways). It helps knowledge manipulation (Mano, multi-hop).
- **Failure (S):** RL did not beat the SFT checkpoint. vLLM and SGLang assume a fixed path.

### Closing the Loop, Marchenko et al. Oct 2026, arXiv:2610.00673 (read in full text)
- **Setup:** 1.4B from scratch with a 24-layer block x 4 laps, 310B tokens (versus Ouro's 7.7T). Also a retrofit of Qwen3-1.7B-Base to 3 laps ("Looped Qwen") with 60B (curated) and 84B (web) tokens. Controls are an identically continued dense model and a compute-matched Qwen3-4B-Base (S).
- **Key recipe (S):** scalar input mix at each lap, z_t = w·e + (1-w)·h_{t-1}, with w = sigmoid(a) and w0 ~0.99. This is the only added parameter. Smoothed exit loss, epsilon 0.05.
- **Ablations (S):**
  - Naive recurrence leaves laps 2-3 about 0.01-0.02 nats worse than lap 1. Scalar injection makes them ~0.02 better. Injection is "most important for retrofit."
  - Post-norm and sandwich-norm did not train (loss plateau ~7.4) in their from-scratch setup. Pre-norm, Ouro-norm and MagicNorm did (1.98-2.11). An identity final norm gave 5-11 loss spikes.
  - Concatenating the embedding was 0.12-0.13 nats worse than the scalar mix. Step-specific LoRA gave little. A learned per-step projection failed.
  - Exit-gate collapse (all mass on lap 1) is invisible in LM loss (2.38 vs 2.36 vs 2.39). Monitor the exit distribution directly.
  - T=8: laps 5-8 change loss by ≤0.01 nats, so T=4.
- **Results (S):**
  - From scratch vs the parameter-matched dense model: GSM8K 83.3 vs 69.1, MATH 63.8 vs 54.1, DROP 60.6 vs 38.6. Wins on all 12 benchmarks at 3 laps. At 3 laps it is close to a 3.9B dense model that costs the same inference compute (GSM8K 81.6 vs 82.8).
  - Retrofit (instruction mix, 2 of 3 laps) vs continued dense: GSM8K 71.0 vs 66.6, MATH 53.3 vs 51.1, MMLU-Pro 34.5 vs 30.8. It is still far below Qwen3-4B-Base (GSM8K 82.9). On the web mix, gains are within ~2 points. Lap 3 adds <0.001 nats over lap 2 on the instruction mix, so evaluation fixed 2 laps.
  - The parameter-matched dense baseline is not compute-matched (it uses ~T times fewer FLOPs). The 3.9B comparison is the compute-matched one.

### LoopUS, arXiv:2605.11011 (May 2026)
- **Setup:** full post-training of Qwen3-1.7B/4B/8B, Phi-4 and TinyLlama on 3B FineWeb-Edu tokens. Layout: 1-6 encoder layers, a looped middle block, 1 decoder layer. Boundaries come from cosine similarity across depth (S).
- **Mechanism (S):**
  - Selective decay gate: h <- alpha·M(h) + (1-alpha)·h, with alpha = exp(softplus(W·delta)·A) and A<0 learned per channel.
  - Random deep supervision: unroll 20 laps, supervise 5 random ones, detach the rest.
  - Monotonicity loss SiLU(L_b - L_{b-1}). Confidence-head halting.
- **Ablations (S):** removing the gate gives a higher final loss. Sigmoid instead of the decay gate is less stable. TBPTT plateaus at a much higher loss.
- **Results (S):** zero-shot average Qwen3-4B 60.3 to 62.1 and Qwen3-8B 63.2 to 65.4. Qwen3-8B MMLU drops 72.8 to 71.5. Average halting is 3.39 of 8 laps. It stays stable at 40/80/100 laps with diminishing returns and no reported collapse. The gain is clearest on ARC-C and OBQA.
- **Caveats:** no compute-matched baseline. The intro's "+3.0%" does not match the table (+1.6 to +2.2). The paper's own comparison to McLeish is "not a controlled head-to-head". Gain is likely a continued-training effect of 3B tokens as much as a loop effect (Sg).

### Shapiro, arXiv:2608.11233 (Aug 2026): frozen-backbone LoRA retrofit
- **Setup:** Qwen2.5-0.5B-Instruct with prelude 0-5, a 12-layer tied core, coda 18-23. Two budgets: full-block (181M trainable) and rank-16 LoRA plus bridge (6.0M trainable, base hash unchanged) (S).
- **Mechanism (S), three needed pieces:**
  - Loop-1 is exactly the base model (identity).
  - A split re-entry bridge that re-injects the prelude output through an identity-biased gate.
  - Gates get their own parameter group and a raised learning rate. Gates folded into a projection "fail silently".
  - A first parameter-efficient attempt failed because the prelude was not re-injected and the zero gate locked itself shut.
  - Training used exact per-lap intermediate-state labels (lap t graded against the t-th state), then 1,000 outcome-only steps.
- **Task and results (S):** synthetic rule-table composition. Rank-16 adapter 83.8% vs full-block 84.0% pooled over depths 1-14. Dense 0.5B direct is 27.7%, dense 1.5B direct 36.6%, and a dense scratchpad (explicit CoT) 72.1%. The recurrent model is 7.6x faster than the scratchpad at depth 14.
  - Extrapolation is ~1.5x supervised depth (70.3% at depth 18 when supervised to 12). It then hits a ceiling (10.9% at depth 22).
- **Retention (S):** ARC-E/C non-inferior at loop 1 for the full-block arm. The adapter arm is "preserved by construction". At 8 laps off-task, ARC-C fell sharply (71 vs 155 correct).
- **Halting failed (S):** a supervised halt head picked the right depth on 70/768 rows (9.1%). PonderNet collapsed to maximum depth.
- **Caveats:** single seed. No compute-matched non-looped LoRA baseline (the paper says arms "do not match training tokens, FLOPs, or inference compute"). Zero-shot transfer to verbal tasks is minimal (16-17%). Deep-tail accuracy fell from 54.7% to 19.5% with more verbal training.

### GitHub "Project Newt" (wfzyx/newt, closed 2026-10-17): the closest negative result to ours
**Single-author, not peer reviewed. Treat as a lead, not a finding.** I checked its summaries of 2608.11233, 2610.00673 and 2605.11011 against the sources and they matched.
- **Setup (S, author's own):**
  - FrogNano-4B (a Qwen3.5-family Gated-DeltaNet + attention hybrid), frozen. Prelude 0-7, core 8-23 looped 3x with LoRA r=64, coda 24-31. Loop 1 is exactly the base.
  - Data was Python plus competitive programming. About 4M loss-bearing tokens, one A10G.
- **Result (S):** every looped arm failed a pre-registered bar. The bar was to beat a 1-pass LoRA control with matched wall-clock on all three held-out slices.
  - The best reinject arm (w0=0.99, one shared LoRA) tied the compute-matched control on both out-of-distribution slices and won only the in-distribution one.
  - Its mix weight opened only to 0.977/0.973, so ≤5% of the signal went through the recurrence in all arms.
  - Original design: gates saturated at 0.963 for 10k steps. Loop 2 was worse than base on every slice.
- **Qwen3.5-0.8B follow-up (S):** core unfrozen (286M trainable), 30M tokens, 3-loop reinject. Loop-3 vs its own loop-1 was TACO -0.002 (CI includes 0), pretrain -0.005, function -0.020. Its margin over a 1-pass LoRA came from its 1-pass column, which had 268M more trainable parameters. Concat bridge (McLeish style) spent its capacity re-encoding the prelude and was stopped.
- **Training-free rerun (S):** 204 configs of re-applying a window. The best (layers 8-11, K=2, beta 0.5) gave +6/164 on HumanEval, but a matched-norm random-noise control gave +5. The author concluded the gain was a greedy-boundary perturbation.
- **Take-away:** the author's diagnosis is "budget, not architecture". Papers reporting gains used full-weight training with ≥1e9 tokens. The cheapest thing the optimiser found was to use the loop as a noisy 1-pass LoRA (Sg).

### Encode-Think-Decode (Koishekenov, Lipani, Cancedda, FAIR/UCL, Oct 2025), arXiv:2510.07358 (ICLR 2026)
- **Setup:** OLMo-2-1B (16 layers) in mid-training only (5e10 tokens, about 5-10% of FLOPs). Layout is 7 encoder, a 4-layer block looped k times, 5 decoder. Boundaries come from angular distance between layers (Kneedle). No new parameters (S).
- **Baseline:** the same model with the same mid-training, k=1, so it is data-matched but not FLOP-matched.
- **Results (S):**
  - GSM8K 44.1 to 51.1 (k=2), 54.4 (k=3), 56.6 (k=5). MATH 4.6 to 6.2 at k=3 (headline +36%), but 3.7 at k=4 and 4.3 at k=5. MATH is tiny in absolute terms.
  - Reading comprehension and multi-disciplinary tasks gain 4-6 points. Factual QA is flat (Natural Questions down at every k).
  - Placement matters (S, matched FLOPs): looping a 4-layer reasoning band (7-4x2-5) gives math avg 29.3 at 28-layer cost. Looping all 16 layers twice (0-16x2-0) gives only 25.0 at 32-layer cost vs ETD k=5's 30.5.
- **Adaptive depth (S, from a figure):** ACT with a linear+sigmoid router matched or beat fixed k=5 on DROP and OBQA with fewer laps. Others just follow the fixed-depth curve.

### Other training-light / frozen-backbone loops
- **Training-Free Looped Transformers**, arXiv:2605.23872 (S): looping a contiguous mid-stack block with damped sub-steps gives +2.64 pp MMLU-Pro (Qwen3-4B-Instruct), +1.14 pp CommonsenseQA (Qwen3-30B-A3B MoE), +1.20 pp OBQA (Moonlight-16B-A3B). Naive reapplication "usually degrades". (Window 4 layers at 40-50% depth, K=2 and the cliff at ≥6 layers come only from Newt's summary of this paper, so (Sg).)
- **Inner Loop Inference**, arXiv:2602.14759 (S): frozen Gemma-2/Llama-3. Gains "modest but consistent", e.g. WinoGrande 68.75 to 69.53 (inside the ±1.3 CI per Newt).
- **Program-of-Layers**, arXiv:2606.06574 (ICML 2026) (S): per-input skip/repeat programs on frozen LLMs. Often shorter programs match the full forward, and skipping beat repeating. "Fixed-depth execution captures only a narrow subset."
- **Layer-duplication / RYS** (ACL Findings 2025) (S per Newt's summary): duplicating 7 layers in Qwen2-72B gave +2.6 average on the Open LLM Leaderboard but IFEval -2.1.
- **"Transformers Stop Thinking Too Early, and a Tiny LoRA Fixes It"**, arXiv:2609.36585 (S): a rank-8 LoRA (65k params) at one early layer on frozen Qwen3-8B takes 24-line variable-chain accuracy from 15.5% to 99%. Placement is critical: moving it from layer 20 to 21 drops reach 20.5 to 5.2 lines. Extra laps in Ouro/Huginn add little without it. Synthetic and in-context only, with one LoRA per task format.
- **Think-at-Hard**, arXiv:2511.08577 (ICML 2026) (S): a decider iterates ~7% of tokens, and LoRA is active only on pass ≥2. +3.8-4.4% over always-iterate and +3.0-3.8% over single-pass Qwen3 at the same parameters, with 300M tokens of math SFT. It names "latent overthinking": uniform looping flips correct tokens to wrong. The oracle for which tokens to iterate gives up to +7.3%.
- **PonderLM-2**, arXiv:2509.23184 (ICML 2026) (S): one extra latent "thought" step per token, from scratch. At comparable inference FLOPs a 1.4B model beats a 2.8B baseline (58.5 vs 57.3 avg on Pythia arch). Continual pretraining of LLaMA-3-3B on 5B tokens: 0-shot 65.2 to 66.2 (plain continued pretraining stays at 65.2). Throughput is about half. Gains saturate near 3 Jacobi iterations in a 70M ablation. PonderLM (ICLR 2026) is the earlier version that re-feeds an expected embedding.

---

## 3. Small-model recursion: HRM, TRM and what actually drove HRM

- **HRM**, arXiv:2506.21734 (S): 27M params, ~1,000 training examples, claimed 40.3% ARC-AGI-1, near-perfect Sudoku and Maze.
- **ARC Prize verification** (arcprize.org/blog/hrm-analysis) (S):
  - Semi-private ARC-AGI-1 was 32%, and ARC-AGI-2 was 2%.
  - A same-size plain transformer came within ~5 points of HRM with no tuning. The hierarchy added little.
  - The outer refinement loop was the driver. One to two loops gave +13 points (pass@2). One to eight loops roughly doubled the score.
  - Training with 16 refinement loops and testing with 1 beat train-1/test-1 by >15 points. Training with refinement matters more than extra inference loops.
  - Training on only the 400 evaluation tasks gave 31% pass@2, versus 41% with the full mix, so most of the score is test-set memorisation via puzzle-ID embeddings.
- **TRM**, arXiv:2510.04871 (Jolicoeur-Martineau, Oct 2025) (S):
  - A single 2-layer net with latent z and answer y. n=6 latent updates per answer update, T=3 cycles (two without grad, one with), deep supervision up to 16 steps.
  - Sudoku-Extreme 87.4 (HRM 55.0); ARC-AGI-1 44.6 and ARC-AGI-2 7.8 (7M params, with 1,000x augmentation per task).
  - Ablations on Sudoku: 1-step gradient approximation 56.5, no EMA 79.9, 4 layers 79.5, self-attention instead of MLP 74.7, T=2/n=2 73.7.
  - More layers hurt generalisation (overfitting). Weight tying and MoE hurt.
  - A follow-up note (arXiv:2512.11847) says a blank or random puzzle ID gives 0% accuracy and most accuracy appears at the first recursion step.
- **Caveats:** these are toy grid puzzles with ~1k tasks and heavy augmentation, with no language modelling or tool use. The transferable points are only: per-cycle (deep) supervision matters more than architecture, and backprop through the full cycle beats a 1-step approximation (Sg for transfer to LMs).

---

## 4. 2026 work on laps, overthinking, MoE and agentic use

- **Overthinking is real and consistent (S):**
  - Loop, Think & Generalize (arXiv:2604.07822, from scratch): the logit margin peaks and then decays; too many laps hurt 10-hop compositions, though extrapolation from 5 to 10 hops works with more laps.
  - "Right Direction, Wrong Step" (arXiv:2609.16665, two model families, math and commonsense tasks): the update direction is fine but the full step is too large. A fixed quarter-step recovers positive gains in 72-83% of failures.
  - LoopCoder-v2 (arXiv:2606.18023, 7B from scratch, 18T tokens): 2 laps beat the non-looped baseline (SWE-bench Verified 43.0 to 64.4, Multi-SWE 14.0 to 31.0). 3+ laps regress, with later laps giving "diminishing, oscillating updates". The baseline is a non-looped model of the same size, not the same FLOPs.
  - Loopie (arXiv:2607.16051): from-scratch 20B-A2B and 6B-A0.6B MoE, layer-loop (each layer run twice) with R=2. Marginal benefit is largest at R=2, and returns decay fast. It overtakes a FLOP-matched vanilla MoE only after ~600B tokens. IFEval 84.7 vs Qwen3-30B-A3B's 85.6. No agentic or tool-use evaluation (U).
- **Iso-depth exchange rate (S, arXiv:2604.21106):** one recurrence is worth φ=0.46 of a unique block. A 410M looped model at r=4 matches a 580M dense model but costs the training compute of 1B. TBPTT lowers φ to 0.38.
- **Scale/readout (S, arXiv:2606.24898, 44M/129M):** per-lap cross-entropy through an RMSNorm readout lets final hidden norms grow into the thousands. Scale-visible readouts or norm penalties keep them in the tens and lower perplexity at matched depth.
- **Stability (S/Sg):**
  - arXiv:2604.15259: without "recall" (input re-injection) plus outer normalisation, fixed points can't depend on the input. Toy tasks.
  - arXiv:2605.18797: training stays stable up to 12 loops with parameter-free "fully looped" and attention-injection changes.
  - LoopFormer (arXiv:2602.11451): trains on variable-length trajectories with time/step-size conditioning and a shortcut-consistency loss. Numbers not read.
- **Looped MoE (S):**
  - LOOM (arXiv:2610.01153, 100M-1.7B): looping MoEs fails under matched FLOPs past two loops because of hidden-state variance growth and expert-selection collapse (routers pick the same experts every lap). Fixes are residual scaling, input re-injection every loop, per-loop routers and a "looping residual". 700M near-iso-FLOP at 5 loops: perplexity 18.36 to 16.54, avg 38.84 to 39.53. 1.7B at 9 loops without FLOP matching: avg 42.4 to 47.7.
  - Intern-S2-Mobius (arXiv:2608.14290): 1T tokens of continual pretraining of Qwen3.5-35B-A3B. General average 67.9 vs 65.1. The "nearly 4x speedup" is attributed to shorter chain-of-thought, not a cheaper loop. No agentic benchmark.
  - Allocating Recurrent Compute (arXiv:2608.18230, 15M/110M Gated-DeltaNet from scratch): looping only the mixer keeps 41.5% of the full-loop gain at 54% of FLOPs. Hybrid/softmax untested (U).
- **Tool calling (S, with caveats): "Looped Language Models Improve Compositional Tool Calling", arXiv:2608.18171.**
  - Ouro-2.6B SFT beats Qwen3-4B SFT on BFCL Parallel (83.0 vs 2.5) and NESTful (0.371 vs 0.063 win rate).
  - Retrofitted Llama-3.2-1B BFCL overall goes 21.4 to 32.9 (Parallel 14.0 to 31.0). OLMo-2-1B goes 39.1 to 41.8.
  - Gains are largest on multi-call and nested calls, and small or negative on single-call API-Bank (retrofit Parse and Exact dropped).
  - Static single-turn only. No seeds, no CIs, no compute matching. Depth is reported to saturate with no overthinking, and the paper's caption on depth (8 for Ouro) is inconsistent with Ouro's max of 4.
  - **No looped model has been evaluated on a multi-turn agent benchmark (tau-bench, tau2 or BFCL multi-turn) as far as I found (U).**
- **Thinking Deeper, Not Longer**, arXiv:2603.21676 (S, toy): "silent thinking" supervises only the final output. An identity-biased gate, LayerScale and normalisation give stability over 20+ laps. Per-step supervision hurt extrapolation on the graph task, which conflicts with Shapiro's per-lap labels.
- **Attractor Models**, arXiv:2605.12466 (S, abstract only): a fixed-point refiner trained by implicit differentiation, with constant training memory. 770M beats a 1.3B Transformer trained on 2x tokens. Not read in detail.

---

## 5. Lessons for our block

Context: frozen LFM2.5-24B-A2B (hybrid conv/attention MoE), small trained looped block, target tau2-bench retail (multi-turn tool use).

1. **Re-inject the clean pre-loop state every lap, with an identity-initialised gate.** Evidence: naive recurrence leaves laps 2-3 worse than lap 1, and a scalar mix fixes it (2610.00673, S). Huginn and McLeish also re-inject. Shapiro's LoRA retrofit failed until prelude re-injection plus a non-zero gate were added (S). Make lap 1 an exact copy of the base model so there is a free reference. Injection is necessary but not sufficient: Newt's injected arms still routed ≤5% through the loop.
2. **Give the gate its own parameter group and learning rate, and watch it.** Gates initialised near saturation never moved in 10k steps (Newt, S). Gates folded into a projection "fail silently" (Shapiro, S). Log the fraction of signal carried by recurrent state every few hundred steps.
3. **Damp the update.** Use h <- h + alpha·(F(h) - h) with small learned alpha, per channel (LoopUS, S). A quarter-step recovers most failures (2609.16665, S). Monitor hidden-state norm per lap and add a norm penalty or scale-visible loss (2606.24898, S).
4. **Loop a short mid-depth band, not the whole stack, and leave prelude and coda frozen and intact.** Looping a 4-layer band beat looping all layers at matched FLOPs (ETD, S). Choose boundaries from layer-to-layer similarity (ETD, LoopUS). Training-free gains need windows of ~2-4 layers (Sg, from Newt's summary of 2605.23872). For a MoE, plan for expert-selection collapse across laps (LOOM, S) and test per-lap router bias or lap-specific router LoRA (U).
5. **Train at the lap count you will deploy, around 2-4, with random lap sampling and a ramp.** Returns are front-loaded in every study: Huginn flattens after 16, Ouro peaks at 4, Loopie and LoopCoder-v2 peak at 2, Closing the Loop sees ≤0.01 nats beyond 4. Our from-scratch block using 2.3 of 8 laps matches this (Sg). McLeish: higher training recurrence raises the ceiling but destroys the 1-lap floor (Llama 6.4 GSM8K at 1 lap vs 37.1 for the parent), so a 1-lap lesion hurting is expected for any trained loop and is not evidence the loop is good. Use random lap sampling with truncated BPTT of at least 4-8 laps, but TBPTT lowers capacity per recurrence (φ 0.46 to 0.38, S).
6. **Supervise every lap, and keep the smoothed weights.** Use per-lap LM loss with epsilon ~0.05 on all laps (2610.00673), Newt's 0.25/0.75 weighting, or random deep supervision (LoopUS). Without per-lap loss, later laps get little gradient. A concrete per-lap target for tool calls (e.g. the tool name or argument tokens) is untested (U). Toy work conflicts: Thinking Deeper says per-step labels hurt extrapolation, while Shapiro used them and then removed them. Start with outcome loss on all laps and treat per-lap labels as an ablation.
7. **Do not expect a learned halt to help.** A supervised halt head chose the right depth 9% of the time and PonderNet collapsed to max depth (Shapiro, S). This matches our "halt made it think longer without gains." Exit gates collapse invisibly (2610.00673, S). Ouro needed entropy regularisation plus a separate stage with the LM frozen. Huginn's KL-based exit cost 0.07 MT-Bench. Use a fixed lap count chosen on held-out data. If you want a gate, train it on per-lap loss improvement after the LM is frozen (Ouro) and plot the exit distribution.
8. **Choose the right comparator, and budget tokens honestly.** The baseline that decides this is a one-pass LoRA with the same wall-clock (Newt, S), plus a perturbation control for any training-free baseline (the noise control reproduced the "gain"). Every full-weight retrofit that beat its control used ≥3B (LoopUS) to 84B tokens, and gave +2 to +4 points on GSM8K/MATH vs a continued dense model at 2 laps (S). Whether a LoRA-sized loop on a frozen 2B-active backbone can clear that bar is open (U).
9. **Mix general data and test lap 1, not just lap k.** Math-only retrofits lost ARC-C and MMLU until healed with 26B tokens of FineWeb-Edu (McLeish, S). LoopUS lost 1.3 MMLU points on Qwen3-8B. Evaluate IFEval, MMLU and BFCL single-call at lap 1 and at the deployed lap count. A non-inferiority margin of ~3 points is the practical standard (Shapiro).
10. **Aim the loop at composition, not recall.** Looping helps multi-step composition (Mano, BFCL Parallel, NESTful, GSM8K) and not knowledge storage (Capo, Natural Questions, SimpleQA-style tasks, single-call API-Bank). tau2 retail mixes policy lookup (recall) with multi-step tool sequencing (composition), so expect gains only on the latter. Build a held-out slice that separates multi-call from single-call turns.
11. **Treat KV and conv state per lap as a design item.** Ouro: separate KV per lap in prefill (sharing costs >10 GSM8K points), but a last-lap-only cache at decode costs ~0. Huginn: a ring buffer of 4 slots is fine. How LFM2.5's conv state should be handled per lap is untested (U). Per-token cost is roughly (1 + (laps-1)·window_fraction) of the base forward pass. In MoE decoding the cost is dominated by re-reading expert weights per lap, so measure latency (WaveFront decoding, arXiv:2609.23033, addresses this; not read).
12. **Be wary of depth extrapolation claims.** Retrofits extrapolate ~1.5x the supervised depth (Shapiro, S) or stay flat past training depth (McLeish, S), while thinking-tuned Ouro degrades sharply at 6-8 laps and off-task laps cost ARC-C heavily (Shapiro, S). Our "forcing 8 laps helped" is a win beyond the usual pattern and deserves a repeat on new seeds before it shapes the design.

### The 3 results most likely to predict whether our frozen-backbone block beats plain re-running of the middle layers
1. **Paired lap-k vs lap-1 loss on held-out data inside the same model, plus the fraction of signal flowing through carried state.** This is Newt's decisive metric: the loop-3 vs own loop-1 deltas were ≈0 (CI includes zero) and mix weights stayed near 0.97. If our block's lap-3 beats its own lap-1 with a CI that excludes zero on out-of-distribution slices, the loop is doing recurrence work and not acting as a noisy extra adapter. This is more informative than the 1-lap lesion (-7.7), which every trained loop shows.
2. **Equal-training-compute, equal-parameter 1-pass control with a pre-registered bar, run on the same held-out slices** (Newt's control-1200 design), plus a matched-norm-perturbation control on the plain "re-run the middle layers" baseline. Our tie of tied-LoRA vs plain LoRA on 3 seeds says the baseline is already strong, and the training-free literature says re-running gains are small (+1 to +3 points) and noise-sensitive.
3. **The lap-sweep curve on multi-call (compositional) held-out turns vs single-call turns, including 1.5x the training lap count.** Papers that find a real loop effect (Ouro, BFCL Parallel/NESTful, Huginn GSM8K) see a monotone rise to 3-4 laps that is largest on composition. Flat curves or gains only on single-call turns would match Newt's "noisy adapter" reading, and a drop past the training laps would match the overthinking papers.

*Not read in full / lower confidence:* LoopFormer, Attractor Models, Allocating Recurrent Compute, WaveFront decoding, Beyond Depth Truncation (arXiv:2609.19934), Prediction Dynamics (arXiv:2609.21383, Huginn and Ouro: finite-depth answers can stabilise while scores still move), and the Newt details beyond its README (checkpoints are not public).
