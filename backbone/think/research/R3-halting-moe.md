# R3: Halting, adaptive depth, and MoE routing for a looped latent block

Sweep date 2026-10-24. All IDs resolve at `arxiv.org/abs/<ID>`.

**Labels.** shown = a number in the paper's own tables, which I read in the full text (pdftotext). suggested = the authors' interpretation, or a result in a different setting. untested = nobody has run it for our case. "Abstract only" or "second-hand" marks things I did not read in full.

**Scope warning.** Nearly everything below is from-scratch training or a full fine-tune of a dense model (0.1B to 8B). I found nothing that freezes the backbone, trains a small block, and halts it, on a hybrid conv/attention MoE. LoopUS (2605.11011) states that hybrid and MoE backbones are untested. Every transfer to LFM2.5-24B-A2B is "suggested" at best.

## 0. Bottom line

1. **Fixed laps plus a test-time sweep is the safe default.** Wherever a learned halt was compared with the maximum fixed depth, it saved compute and rarely added accuracy (HRM, Ouro, Depth-Adaptive Transformer, SUT, MoEUT). The one clear accuracy gain comes from selective token-level iteration (TaH), which is a different thing from a lap-count halt.
2. **Our symptom matches a known failure.** A halt trained jointly with the block and weighted by its own exit distribution changes which laps get supervised. Ouro describes self-reinforcing drift onto the deepest lap. The 2026 diagnostic paper (2607.20519) shows the gate entangles with the trajectory it reads, and that zero-parameter readouts often match or beat learned gates on held-out data.
3. **Looping added only in post-training usually loses to a non-looped model at matched compute** (TaH2, 2609.35748). Wins came from spending extra laps on about 6 to 7% of tokens.
4. **Per-token gating is not free.** TaH iterating on 6% of tokens still cost about 30% of decode throughput (38.9 to 27.2 tok/s on a GPU). That matters against a 30 tok/s floor.
5. **No evidence exists for lap-specialised MoE experts on a frozen backbone**, and none for what a pretrained, un-retrained MoE router does when its layer is re-run.

## A. Halting and adaptive computation

### A1. Classics (compact)

- **ACT (Graves 2016, 1603.08983) and Universal Transformer (1807.03819). Read.** The loss adds a ponder cost `τ·P(x)`. Shown: behaviour is "quite sensitive" to τ and the choice is "not obvious". At high τ the ponder time falls to 1 and ACT behaves like no ACT. UT's ponder time grew with the number of supporting facts on bAbI (2.3, 3.1, 3.8), but this was a toy task with no compute-matched fixed-depth control.
- **PonderNet (Banino 2021, 2107.05407). Read.** The halting step follows a learned distribution, regularised by KL toward a geometric prior (unbiased gradients, unlike ACT). Parity, shown: trained on 1 to 48 non-zero inputs and tested on 49 to 96, it was near-perfect while ACT sat at chance. ACT solved parity only for a few τ values, with high seed variance. Robust to the prior except λp=0.9. bAbI: 1,658 steps against 10,161 for UT+ACT. Caveat: toy tasks only, and Ouro found a geometric prior worse than a uniform one for LM training (below).
- **Depth-Adaptive Transformer (Elbayad 2019, 1910.10073). Read.** Shown: the best learned token-level halting classifier matched the 6-layer baseline BLEU with 76% fewer decoder blocks. Plain confidence thresholding "performs very well but cannot outperform it" (59% fewer blocks at baseline accuracy).
- **CALM (Schuster 2022, 2207.07061). Read.** T5 early exit calibrated with Learn-then-Test and a decaying threshold. Shown: up to about ×3 estimated speedup (layers and FLOPs, not wall-clock). State copying, shown: with an oracle exit, copying the exited hidden state into deeper layers gave ROUGE-L 38.24 against 38.32 for the full model at 1.53 layers per token. Copying projected K,V into skipped layers fell to 23.02.
- **LayerSkip (2404.16710). Abstract and skim.** Layer dropout plus a shared early-exit loss; 1.34× to 2.16× via self-speculative decoding. A speed result, not an accuracy one.

### A2. Looped LMs

**Huginn (Geiping 2025, 2502.05171). Read.**
- Setup: 3.5B parameters, prelude/recurrent core/coda, 795B tokens. The lap count is drawn per sequence from a log-normal Poisson, and backprop covers only the last k=8 laps.
- Zero-shot exit, shown: stop when the KL between successive laps' next-token distributions drops below 5e-4. Exit depth varied by MMLU category (about 3.5 steps more on moral scenarios than on high-school maths). MT-Bench: 5.56 with KL exit against 5.66 at 32 iterations and 5.69 at 64 (n.s.).
- Failure, shown: a "bad run" "learned early to ignore the incoming state", and validation perplexity was identical at 1 and 32 recurrences. The fix was the sandwich-norm layout and a lower learning rate. This is the closest analogue to our "only 2.3 of 8 laps used".

**Ouro / LoopLM (Zhu 2025, 2510.25741). Read.**
- Setup: 1.4B and 2.6B, T_max=4, 7.7T tokens. Eight laps in Stage 1a caused loss spikes, so training was cut to four.
- Stage I (shown): per-lap gates give an exit distribution p. The loss is `Σ_t p(t|x)·L_t − β·H(p)`, an ELBO with a uniform prior (β 0.1, then 0.05). The authors' account of the failure it prevents: deeper laps get more gradient, their loss falls, and mass drifts onto T_max. I found no run without the entropy term, so this is suggested.
- Stage II (shown): freeze the LM and train only the gate on `w_t = σ(50·(I_t − 0.005))`, where `I_t = max(0, L_{t−1} − L_t)`. Inference exits when the CDF of p reaches q.
- MMLU 5-shot, 1.4B, shown: laps 1 to 4 give 41.2, 60.4, 66.7, 67.5. Past the trained depth it falls (64.5 at lap 8). The 2.6B model: 51.6, 67.6, 73.6, 74.6, then 72.2 at lap 8.
- Gate against static, shown: at 2.5 average laps the Stage II gate gets about 66% against about 64% for the untrained gate. A hidden-state-difference rule lands within 1 to 2 points of it. Static exits at 2 and 3 laps give 60.4 and 66.7, so interpolating at 2.5 gives about 63.6 (my arithmetic).
- Priors, shown (776M, 20B tokens): a uniform prior beats geometric priors on loss and on the accuracy-compute frontier, and geometric priors starve laps 3 and 4 of gradient.
- Other failures, shown: RL (off-policy and fixed 4-lap) did not beat the SFT checkpoint. KV reuse from the first lap collapses GSM8K to 18.73 (full 78.92); last-lap reuse gives 78.85.

**Mixture-of-Recursions (Bae 2025, 2507.10524). Read.** From scratch, 135M to 1.7B, FineWeb-Edu.
- Expert-choice routing picks the top-k tokens per recursion. It leaks future information and needs an auxiliary loss. Token-choice has load imbalance and is clearly worse (40.0 against 42.6 few-shot average at Nr=3).
- Equal data, shown (20B tokens, 360M, Nr=2): MoR gets NLL 2.7749 with 12.3e18 FLOPs against 2.8079 for fixed-depth recursion at 16.5e18 (vanilla 2.7824). This is a rare compute-aware win for learned token-level depth over fixed recursion. Its isoflop few-shot lead (43.1 against 42.3) also uses 27B tokens against 20B.
- Recursive KV sharing hurts expert-choice. It loses to vanilla at 135M.

**HRM / TRM and the ARC Prize finding.**
- TRM (2510.04871, read): HRM's Q-learning halt needs an extra forward pass for the continue loss. TRM drops it and learns only a halt probability (Sudoku-Extreme 86.1 to 87.4). The halt mainly saves training supervision steps.
- ARC Prize (arcprize.org/blog/hrm-analysis, via page fetch; numbers are from a page summary): "while using ACT does improve performance, the difference is within a few percentage points when compared to a fixed 16-loop run". The outer refinement loop mattered most: 1 to 2 loops gave +13pp pass@2, and training with up to 16 loops gave over +15pp at single-pass inference.
- HRM follow-up (2510.00355, read): released code ignores the learned halt at evaluation. When it was applied, the authors conclude that "running the model for the maximum number of reasoning steps yields the best results" (shown on HRM only).

### A3. 2026 papers (Jan to Oct)

**Diagnosing Learned Halting Gates (2607.20519). Read. The most relevant paper.** Synthetic tasks (MANO, parity) plus released Ouro-1.4B and 2.6B.
- Claim, shown: a learned gate both picks the exit and sets how strongly each lap is trained. A fixed prior over depths produced "difficulty-aware" trajectories, and simple post-hoc readouts (max prob, margin, entropy, successive-lap hidden cosine) "often match or outperform" learned linear and MLP gates.
- Held-out, shown (Table 3, 20/80 validation/held-out split): in 5 of 12 model-benchmark pairs a post-hoc readout had higher accuracy than the pretrained Ouro gate. It used fewer loops in 7, and was better on both in 3.
- Frozen-gate test, shown: fitting a new gate on the frozen trajectory from joint training does not help. On a fixed-prior trajectory it does. So the damage comes from joint training, not from a weak gate.
- Cost, shown (Ouro-1.4B): the gate saves 1.24× to 1.58× latency for about 0.5 to 1.6 points of accuracy. Large β collapses the gate to near-fixed depth.

**Think-at-Hard, TaH (Fu 2025/26, 2511.08577; ICML 2026). Read.** Full fine-tune of Qwen3-Base 0.6B, 1.7B and 4B on 100K Open-R1 examples, with parameters matched to non-looped and Ouro baselines on the same data.
- Mechanism: a second lap (Dmax=2) is optional. A small MLP decider triggers it. Laps after the first use LoRA plus residuals, and "duo-causal" attention lets later laps read earlier-lap KV.
- Overthinking, shown (Ouro-1.7B): lap 2 fixes 8.7% of predictions and breaks 2.1% of correct ones. An oracle that iterates only on first-pass mistakes (12 to 19% of tokens) gains up to +7.3 on AMC23, but needs gold tokens.
- Results, shown: +3.0 (0.6B), +3.8 (1.7B), +1.7 (4B) average over nine benchmarks against non-looped. Always-iterating baselines sit at or below non-looped (AlwaysThink 39.9 against 47.5 at 1.7B). The gain shrinks with scale.
- Ablations, shown (0.6B): always-2 laps −16.4 against selective; training the decider on the evolving model −30.4 (collapse); a decider-based policy during backbone training −7.2; supervising every lap with next-token loss −4.3; dropping LoRA −1.3 and dropping LoRA plus residuals −4.9. The decider is trained afterwards on the frozen backbone, imitating a static oracle at about 83% accuracy.
- Cost, shown (A800, 1.7B, 8K tokens): 6% of tokens take lap 2; throughput 27.2 against 38.9 tok/s non-looped and 11.0 always-iterating.

**TaH2 (You 2026, 2609.35748). Read.** Qwen3-1.7B/4B/8B-Base post-trained on matched data. The decider trains jointly with the backbone on online "iteration gain" labels from a no-grad lookahead.
- Shown: post-trained Ouro and Huginn have steeper accuracy-per-compute slopes (2.12 to 2.27 against 1.79) "yet remain less accurate than Standard over the overlapping compute range". Ouro's exit gate, trained afterwards on a frozen backbone, did not close the gap. In Ouro, 21.7% of tokens get worse at lap 2.
- TaH2, shown: slope 2.74, and +3.4 points over the non-looped peak at matched compute (AIME, 32K). Ten-benchmark averages are +3.2 (4B) and +2.4 (8B), including BFCL tool use (29.2 to 33.6 at 4B, 38.0 to 39.4 at 8B). Costs: +22% decode FLOPs and +30% to +34% latency. M=2 is the best trade-off. Gain labels beat mismatch labels by 1.1.

**LoopUS (Park 2026, 2605.11011). Read.** Post-training recasts a pretrained dense LLM (Qwen3 1.7B to 8B, Phi-4 14B) as encoder, looped middle block and decoder, with a selective gate against drift, a monotonicity loss, "random deep supervision" (unroll B laps, gradients on a random subset), and a confidence head.
- Shown: +1.6 to +2.2 average zero-shot accuracy; the model halts after 3.39 of 8 laps on average and stays stable out to 40 to 100 laps. MMLU and HellaSwag are flat.
- Caveats: no control that fine-tunes the non-looped backbone on the same data (WikiText perplexity also improves, 21 to 16.9), 1,024 context, no maths, and hybrids and MoE are untested.

**Other 2026 work.**
- AdaPonderLM (2603.01914, read) and PonderLM-3 (2603.02023, skim): from-scratch Pythia-size models, about 10% fewer inference FLOPs at similar perplexity, and a learned policy beating uniform and geometric pruning at equal FLOPs (shown, Pile validation). A single MLP gate collapses (nobody or everybody halts), and a per-iteration bottom-K rule is needed.
- RL-Halting (Kuo 2026, 2606.29983, abstract and skim): REINFORCE hazard head on toy algorithmic tasks. Randomising the loop count cuts out-of-distribution variance, because a fixed schedule ties loop count to input length. Learned stopping "can also stabilize a suboptimal computation".
- Dense Supervision Is Not Enough (2606.24898, skim): per-loop cross-entropy through RMSNorm readouts made early exits usable but let the hidden norm grow to thousands in 44M and 129M models. Fix with a scale-visible readout or a norm penalty (small-model evidence).
- Looped LMs for tool calling (2608.18171, skim): Ouro and retrofitted looped OLMo-2-1B and Llama-3.2-1B on API-Bank, BFCL and NESTful. Gains concentrate on multi-call, dependency-aware tasks and are smaller on single calls. Adaptive exit gave a better compute trade-off (qualitative in what I read).
- Retrofitting Recurrent Depth (2608.11233, skim): Qwen2.5-0.5B with a frozen base and a 6M-parameter adapter installed a loop on a synthetic multi-step task (83.8% against 84.0% for the full block). One author, one synthetic task; depth selection is called open. It notes that a correct state "can be carried past its answer", and that the prelude must be re-injected.
- Towards Looped Models Done Right II (2610.06833, partial): terminal-lap KV sharing barely changes Huginn's GSM8K but collapses Ouro at four loops, since Huginn's states approach fixed points. A learned, entropy-regularised depth prior with a 3× smaller KV cache matches fixed-depth training at 1.6B. Fixed-depth training under sharing fell from 50.6 to 21.2 GSM8K.
- Depth-adaptive serving via continuous depth batching (2608.09444, abstract): a batched-serving method, not applicable to one stream.
- Second-hand only: Parcae (2604.12946, stable recurrence with per-sequence loop sampling) and iso-depth scaling (2604.21106, `r` recurrences worth about `r^0.46` unique blocks at fixed FLOPs).
- Tool-call "when to think": 2604.01202 (abstract) finds that a linear probe decodes the tool-call decision before any reasoning token. ALAR (2606.02871, abstract) switches per agent turn between latent and explicit reasoning, reporting up to 84.6% fewer tokens in tool use. It is author-reported, RL-trained, and a different mechanism from a lap loop.

## B. MoE-style routing for depth and "thought experts"

Everything in this section is from-scratch training unless stated.

- **SUT (Tan 2023, 2310.07096). Read.** Sparse-MoE Universal Transformer with stick-breaking halting (halted states go to a "No Op" expert). Shown: BLEU 29.2 at 787M MACs against 29.3 at 2,090M for Transformer-big on WMT14. Halting gave about 50% less compute on logical inference and 20 to 33% on CFQ. Halting ablation: valid loss 2.192 to 2.219 and BLEU 29.2 to 29.1 when removed, so it is mostly an efficiency feature.
- **MoEUT (Csordás 2024, 2405.16039). Read.** Shared-layer MoE with layer grouping (G=2, repeated about 8 to 9 times) and peri-layernorm; no ACT. Shown: slightly beats parameter-matched dense models at 44M to 1B. Against SUT, "most of this poor performance comes from the ACT mechanism". Without ACT SUT improved but still lagged.
- **Loopie-20B-A2B and 6B-A0.6B (2607.16051). Read. Same 2B active size as our target.** "Layer-loop" (each layer twice) trained on 3T plus 1.26T tokens. Shown: it overtakes a compute-matched larger vanilla MoE after about 600B tokens. The marginal gain of recurrence is largest at R=2 and decays quickly. The authors say larger R may suit adaptive computation or cheap inference compute.
- **SMELT (2609.01343, partial).** Loops the middle half twice at matched FLOPs, total parameters and KV cache (narrow hidden size, add experts). Shown: 6.8 to 18.0% training-FLOP savings up to 54B parameters. Routing, shown: the same token revisiting the same MoE layer reuses nearly all 8 experts at 0% sparsity and 2 to 3 of 8 at about 97% sparsity, far above chance. The second visit "amplifies the first rather than overwriting it".
- **Tying the Loop (Jaggi 2026, 2606.16825, partial).** Experts tied across layers, separate routers. Untying routers changes loss by at most about 0.009 while cross-loop routing agreement drops 4 to 7× (0.733 to 0.160). Its conclusion: "per-layer attention, not routing, is what differentiates layers". Keeping an untied prelude and coda mattered most.
- **CoLa, "Skip a Layer or Loop it?" (2507.07996). Read.** MCTS (200 simulations per input) over skip or repeat of 1 to 4 layer blocks on frozen Llama-3-3B/8B and OLMoE-1B-7B, with ARC and DART-Math.
  - Shown: the reward is gold-answer correctness, so these are per-sample oracle numbers. The abstract says over 60% of originally wrong samples have a better path.
  - Caveat (suggested): ARC-Easy accuracy is exactly 95.80 for all six models, whether the original scored 24.8, 27.8 or 76.0. That looks like best-of-N over 4-way multiple choice, not a learnable policy. There is no router, no compute-matched baseline and no search cost.
  - OLMoE gains are smaller than dense, which the authors attribute to existing sparse selection. Corrected samples used shallower paths ("overthinking in depth").
- **Dr.LLM (Heakl 2026, 2510.12773, ICLR 2026). Read.** Per-layer skip/execute/repeat routers (repeat at most once) trained on about 4k MCTS paths over frozen dense Llama and Qwen2.5. Shown: +2.25pp on ARC and DART in domain with about 5 fewer layers per example, and 15% less generation time at 1k tokens. Out of domain it loses 0.85pp on average against the base model. This is the realistic distillation of the CoLa oracle.
- **Router-Tuning (2410.13184) and FlexiDepth (2503.23798). Abstract and skim.** Router-Tuning reports a 21% speedup for a 0.2% drop, with attention layers the best to skip, and includes OLMoE and DeepSeek-MoE. FlexiDepth skips 8 of 32 Llama-3-8B layers at full benchmark performance but gets no wall-clock speedup.
- **Layer duplication on frozen weights.** "Layer Duplication in LLMs" (EMNLP Findings 2025, abstract only): duplicating initial attention layers once or twice often helps. David Ng's RYS posts (second-hand, self-reported) say duplicating about 7 to 12 middle layers helps dense Qwen2-72B and Qwen3.5-27B on maths and EQ, and that repeating a single layer "almost never" helps.

**Evidence gaps.** I found no measurement of re-running a pretrained MoE layer with a frozen router. SMELT and Tying the Loop measure routing in models trained to loop. A learned halt on a frozen backbone, and any halt on a conv/attention hybrid, are untested.

## Lessons for our block

1. **Default to fixed laps and sweep k at test time. Add a halt only if it earns its place.** [shown in several settings, none on a frozen backbone]
   - HRM: maximum steps was best, and ACT was within a few points of a fixed 16-loop run.
   - Ouro: a trained gate beats a static exit by about 2.4 points, and a free hidden-difference rule gets within 1 to 2 of the gate.
   - Diagnostic paper: post-hoc readouts matched or beat the gate in 5 of 12 held-out pairs.
   - SUT: halting is worth 0.1 BLEU. MoEUT: ACT hurt.
   - Expect a halt to buy about 1.2 to 1.6× fewer laps for 0.5 to 1.6 points, not accuracy.

2. **Do not train the halt jointly with the block on a lap-weighted loss.** [suggested; fits our symptom]
   - Use (a) a fixed-prior per-lap loss, then (b) a zero-parameter readout (successive-lap KL as in Huginn, max-prob, margin, hidden cosine), or (c) Ouro's Stage II gate on a frozen block with the loss-improvement target.
   - Choose the threshold on a split not used to fit the gate (the diagnostic paper used 20% validation, 80% held-out).

3. **To make the model use more laps, supervise them with a fixed, broad distribution over depth.** [shown for from-scratch or full fine-tune; evidence mixed]
   - Options: random lap count per sequence (Huginn log-normal Poisson with truncated backprop), a uniform prior with per-lap loss (Ouro: uniform beats geometric), or random deep supervision (LoopUS).
   - Mixed: in TaH, supervising every lap with next-token loss was −4.3 against final-lap-only. Run this as an A/B in the card experiments.
   - Guard against the block ignoring its input. Huginn's bad run had identical perplexity at 1 and 32 laps. Re-inject the prelude each lap, bound the hidden norm if using RMSNorm readouts, and consider a lap embedding or lap-specific LoRA (TaH: LoRA plus residual worth +1.3 to +4.9 at 0.6B).

4. **Do not over-provision laps, and compare against a compute-matched non-looped model.** [shown]
   - Loopie and SMELT found 2 loops best at matched compute. TaH2's best trade-off is M=2.
   - Ouro MMLU rises 41, 60, 67, 67.5 for laps 1 to 4, then falls beyond the trained depth.
   - TaH2 shows post-trained looped models lose at matched compute unless extra laps are selective.
   - Our "forcing 8 laps helps" result fits this only up to the trained depth. Compare against spending the same FLOPs another way.

5. **Gate tokens with a budget, not a free threshold.** [shown at small scale]
   - Top-k capacity (MoR expert-choice, Mixture-of-Depths) or a bottom-K rule (AdaPonderLM) stays stable. A single free MLP gate collapses.
   - Train the policy sequentially against a static reference (TaH: dynamic oracle −30.4, decider-based −7.2). Label tokens by measured loss gain (TaH2 beats mismatch labels by 1.1).
   - Plan for about 6 to 7% of tokens taking extra laps and about 83% imitation accuracy.

6. **Count the real cost of per-token gating.** [shown on GPU, not on an M1]
   - TaH went from 38.9 to 27.2 tok/s with 6% of tokens iterated. TaH2 added 22% FLOPs and 30 to 34% latency.
   - To hold 30 tok/s with two agents, think at a few chosen positions (first answer token, the token before a tool call) and run the decider only there.
   - A cheap trigger is plausible: tool-call decisions are linearly decodable before generation (2604.01202) [suggested].
   - Gains probably concentrate in multi-call tool use and are small on single calls (2608.18171) [abstract-level]. Measure on those.

7. **Treat KV and state for skipped laps deliberately.** [shown]
   - Copy the exited hidden state and recompute K,V (CALM 38.24 against 38.32). Do not copy projected K,V into skipped layers (23.02).
   - When sharing KV across laps, use the terminal lap (Ouro last-lap 78.85, first-lap 18.73 on GSM8K), and train with a broad lap distribution so sharing works.

8. **Do not buy lap-specialised experts on a frozen backbone as a first move.** [suggested]
   - Every positive result for experts-per-depth (MoEUT, SUT, SMELT, Loopie) trains the whole model from scratch.
   - Tying the Loop finds per-layer routers move loss by under 0.01 and that attention is what differs between layers.
   - SMELT shows a trained router reuses most experts on a second visit, so a frozen router will probably re-pick similar experts. The cheaper lever is a lap embedding, lap-conditioned LoRA or a small adapter.
   - Measure expert overlap between lap 1 and lap k in frozen LFM2.5 first. That is untested.

9. **Treat layer-skip and layer-repeat oracles as upper bounds.** [shown]
   - CoLa is gold-label MCTS. The distilled version (Dr.LLM) gained +2.25pp in domain and lost 0.85pp out of domain, on dense models.

10. **Report an overthinking curve on held-out data.** [suggested]
    - Per lap, count wrong-to-right and right-to-wrong flips (TaH: 8.7% against 2.1% at lap 2).
    - If the held-out best-lap-per-example oracle is no better than the best fixed lap, no halting policy can help.

### The three results most predictive of whether halting will help us

1. **Held-out lap-oracle headroom.** Compare the best fixed lap count with the per-example or per-token oracle lap count on held-out data. TaH's oracle headroom was +2 to +7 points. If ours is under about 2, a halt can only save compute.
2. **Whether a zero-parameter readout matches our learned halt on held-out data.** If successive-lap KL, max-prob or hidden cosine traces the same accuracy-versus-average-laps curve, drop the learned halt (the Ouro and diagnostic-paper pattern).
3. **The shape of the held-out accuracy-versus-laps curve, and its flips.** A monotone curve with few right-to-wrong flips means the maximum fixed lap count wins and halting is purely an efficiency trade. A curve that peaks early with many flips means budgeted, TaH-style token gating has real accuracy upside.

### Not verified

- Blog and forum layer-duplication numbers (RYS, the Hacker News post) are self-reported.
- Parcae, iso-depth scaling, ALAR, Switch (2606.13106), PonderLM and Prediction Dynamics (2609.21383) were not read beyond abstracts or search summaries.
- CoLa's own text and Table 1 disagree on one cell (DART-2 recurrence-only, 22.0 against 20.80), so treat its numbers with some care.
