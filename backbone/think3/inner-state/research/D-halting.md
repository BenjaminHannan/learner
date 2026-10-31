# D: Adaptive halting for latent CoT and looped LMs (2025-2026)

Labels: **shown** = stated in an abstract or table I read; **suggested** = my inference; **untested** = proposal only.
Caveat: most numbers below come from abstracts (arxiv.org/abs fetches). Full tables were not read, so no accuracy-vs-laps curves for Ouro or Coconut were obtained.

## 1. Learned / adaptive halting

- **Ouro / LoopLM, arXiv 2510.25741.** Pretrained looped LMs, 1.4B and 2.6B, T_max = 4 recurrent steps (shown, via 2607.20519). Trained on 7.7T tokens. Claims parity with up to 12B SOTA models (shown, abstract). Exit depth is learned with an entropy-regularised objective under a uniform prior over exit steps, because adaptive exits otherwise collapse to shallow depths or overuse long loops (shown, via 2607.20519 summary). Stage II freezes the backbone and trains only the gate, using the marginal utility of one more iteration as a BCE target (shown, via 2608.18171 summary). No accuracy-vs-average-laps numbers were available from the abstract.
- **Diagnosis of Ouro-style gates, arXiv 2607.20519 ("Adaptive Depth in Looped Transformers").** Simple post-hoc confidence readouts often match or beat learned linear and MLP gates (shown, abstract). Failures come mainly from the trajectory induced by joint gate training, not gate capacity (shown, abstract). Pretrained Ouro ponder gates are competitive but not uniformly Pareto-optimal (shown, abstract). Lower average exit depth gives measured latency savings (shown, abstract).
- **Token-level adaptive latent CoT, arXiv 2602.08220.** Each token gets its own variable-length latent trajectory, learned end-to-end in pretraining. Lower perplexity and better downstream accuracy than recurrent baselines, with fewer FLOPs (shown, abstract; no numbers read).
- **AdaAnchor, arXiv 2603.15051 (ICLR 2026 LIT workshop).** Latent anchor vectors; halts when anchor change converges. Up to +5% accuracy over fixed-step refinement and 48-60% fewer average latent steps on three math word-problem sets (shown, abstract). Benchmarks not named in the abstract.
- **Learning When to Stop, arXiv 2511.21581.** Post-SFT RL shortens latent reasoning. Llama 3.2 1B on GSM8K-Aug. 52% reduction in total reasoning length with no accuracy penalty (shown, abstract). Per-question adaptivity is not explicit in the abstract.
- **FR-Ponder, arXiv 2509.24238.** Sub-1M-parameter halting controller reads frozen-model hidden states and decides halt vs one more "ponder" step (steering vector added). Trained with GRPO. Evaluated on GSM8K and MATH500. Claims a better compute-accuracy frontier and lower FLOPs than early-exit baselines at matched accuracy (shown, abstract). This is the closest match to a frozen model with per-question halting. Its numbers are not in the abstract.
- **PonderLM-3, arXiv 2603.02023.** Per-token allocation via a differentiable attention mask in pretraining, with a matching hard pruning rule at inference. Matches PonderLM-2 at the same max extra steps, with fewer FLOPs (shown, abstract; no numbers).
- **PonderNet, arXiv 2107.05407 (2021, background).** Geometric-prior halting with an exploration regulariser. The Ouro uniform-prior idea is a close relative.
- Not found: a learned stop token for Coconut or CODI with reported numbers. CODI (2502.21074, EMNLP 2025) uses 6 latent tokens, a 29-50x token compression vs explicit CoT, and has no adaptive count (shown, via search snippet).

## 2. Training-free exit rules

- **Huginn, arXiv 2502.05171, appendix.** Per-token zero-shot exit when KL(successive latent states) < 5e-4. Warm-starting from the previous token saves about 1-2 steps. Exits are earlier on easy MMLU categories, and moral scenarios take about 3.5 more steps. MT-Bench 5.63 (full) vs 5.56 (early exit). No accuracy-vs-average-steps curve (shown, via WebFetch of HTML; the paper does not state a max recurrence).
- **AdaAnchor (2603.15051)** uses the same kind of rule, convergence of latent change, and reports the 48-60% step cut above (shown).
- **2607.20519** finds that simple confidence readouts often match learned gates (shown). This is the strongest evidence that training-free rules are competitive. Which readouts were used is not stated in the abstract.
- Gap: no paper I found compares KL, cosine and entropy exits head-to-head against a learned halting head on the same model and benchmark. This is untested in the literature I could see.

Suggested for our setup: use the Huginn KL threshold and the 2607.20519 finding as the baseline. Measure against the learned gate on the same card set.

## 3. Test-time extrapolation

- **Huginn, 2502.05171.** Recurrence count is sampled per sequence from a log-normal Poisson, mean r̄ = 32, with a heavy tail and backprop through the last 8 iterations (shown). Perplexity improves from depth 1 to 64 (shown). Accuracy at r = 64 on GSM8K is 47.23% flexible (shown). On ARC-C, zero-shot accuracy saturates around 8-12 iterations (shown). So more iterations help but saturate by task.
- **2606.29983 (Kuo et al., June 2026), "Stabilizing Extrapolation in Looped Transformers via Learned Stochastic Stopping."** Length generalisation is brittle. A spurious correlation between sequence length and loop count drives OOD variance. Randomising loop count in training sharply reduces OOD variance (shown, abstract; no figures). RL-Halting improves the accuracy-stability trade-off on binary addition, Dyck-1, Unique Set and Copy (shown, abstract). It can also stabilise a suboptimal computation (shown). This is the most direct support for randomised K.
- **2605.18797, Fully Looped Transformer (May 2026).** Parameter-free fixes: spread inter-loop signals across layers, and reuse the attention block as input injection. Stable training up to 12 loops where baselines collapse. Up to 13.2% downstream gain in milder settings (shown, abstract).
- **2604.15259, Stability and Generalization in Looped Transformers (April 2026).** Recall plus outer normalisation give stable fixed points and stable backprop (shown, abstract). Looped nets without recall have weak input dependence (shown, abstract).
- **2604.11791, mechanistic analysis of looped reasoning LMs (April 2026).** Retrofitted Llama with input injection settles within a few recurrences and keeps the same stages for any number of loops. Ouro 1.4B does not: its late-recurrence layers keep changing (shown, abstract).
- **Latent-CoT specific.** 2602.22441 reports that shortening Coconut's latent sequence at inference can make the model skip to the answer, because the curriculum overrides earlier stepwise behaviour (shown, search snippet; not verified). 2026 CODI mechanistic work finds that at longer hop lengths CODI runs only a partial latent path, which collapses under regime shifts (shown, search snippet). Overall: more latents than trained is not reliably better for Coconut or CODI. I found no direct Coconut/CODI "more latents at test time" table.

## Implications for a 3.7B model with K-laps (suggested, untested)

1. Randomise K in training (e.g. Huginn-style sampling around a mean, capped). This is the best-supported trick for extrapolation (2606.29983, Huginn).
2. Add input injection or the Fully Looped normalisation if laps must extend past training K (2605.18797, 2604.15259).
3. Baseline the halting head against a KL-threshold or confidence exit before trusting it (2607.20519, Huginn).
4. Pass criterion, to fix in advance: learned halting must beat fixed-K accuracy at equal average laps on the card set, and the KL exit must reach within 1 point of the learned gate. Failure result: if the KL exit matches the learned gate within 1 point at the same laps, drop the learned gate.

## Gaps

- No Ouro accuracy-vs-laps table was read. Read 2510.25741 Section on depth scaling if needed.
- No KL vs learned-halting head-to-head on the same benchmark found.
- No Coconut/CODI learned-stop result with numbers found.
