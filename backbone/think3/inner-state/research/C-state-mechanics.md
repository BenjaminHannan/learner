# C. Recurrent latent-state mechanics: evidence for the lap design

Labels: **shown** = read in a paper's text/table (HTML version); **suggested** = secondary summary or my inference; **untested** = not measured in any source found.
Caveat: arXiv abs pages were often all the fetch returned; numbers below come from HTML versions unless marked.

## 1. Norm / scale mismatch

- **Coconut (2412.06769):** last hidden state fed directly as next input embedding, no projection. Authors note the last states "have been processed by the final normalization layer, so they are not too large in magnitude." **shown** (text quote). No norm-matching ablation.
- **CODI (2502.21074 v3):** state passes through "a two-layer MLP followed by layer normalization" (Sec 3.3). **shown.** No norm-matching on the thought vector; the distillation loss is normalized by the std of teacher hidden activations. **shown.** Six latent thoughts (peak at 6, Fig 5). GSM8k-Aug: CODI GPT-2 43.7%; CODI beats Coconut by "over 20%" on GSM8k (no Coconut number in text). **shown.** Loss-weight β on LLaMA-1b (Table A4): β=1 46.5, β=5 50.2, β=10 49.1, β=20 51.9, β=30 51.4. **shown.** No per-layer ablation.
- **Huginn (2502.05171 v2):** the recurrent state is not fed back through a norm before the coda; "two norms per decoder block"; final layer norm not reused before coda. Linear adapter maps concat(2h→h). Emb-scale ablation: "negligible difference." **shown.** Muon vs AdamW: AdamW loss spikes/NaN, Muon stable at LR 1e-3 vs AdamW 5e-5. **shown.**
- **CoLaR (2505.16552, NeurIPS 2025):** does not feed raw states; a separate latent head predicts the next *compressed* embedding (merged embeddings of k consecutive tokens). Reported: 14.1% higher accuracy than latent baselines at matched compression; 53.3% shorter chains for 4.8% accuracy loss vs explicit CoT. **suggested** (from abstract-level search summary, not full text).
- **Soft Thinking (2505.15778, NeurIPS 2025):** input = probability-weighted mixture of token embeddings (training-free). Gains up to +2.48 pass@1 and up to 22.4% fewer tokens vs CoT. **suggested** (search summary). No norm handling found.
- **Mixture of Inputs (2505.14827 v3, NeurIPS 2025):** next input h = Σ w_i e_i, a convex combination (weights sum to 1), so the mixed input stays inside the embedding convex hull and its norm is smaller than a raw hidden state. Weights blend the distribution p with the sampled token y using normalized entropy H: w = [H·p + (β+1−H)·y]/(β+1). **shown** (formula). Ablation, direct mixture (w=p) vs MoI: QwQ-32B 60.96 vs 74.15; Nemotron-Super-49B 46.97 vs 55.45; Gemma-3-27B 41.36 vs 41.65; DAPO-Qwen-32B 47.90 vs 60.33. **shown.** Training-free. No norm-rescaling step described.
- Takeaway for us, **suggested:** a convex mixture of embeddings (MoI/Soft Thinking style) sidesteps the norm problem; a norm-matching step (RMS to embedding RMS after the MLP) is the cheap alternative. Not tested in any source found.

## 2. Lap-count randomization and curricula

- **Huginn:** recurrence r = Poisson(e^τ)+1, τ ~ N(log r̄ − σ²/2, σ), σ=1/2, mean r̄=32; truncated backprop through last k=8 steps; state init s₀ ~ truncated normal (3σ). **shown.** No max train depth; heavy tail. Ablation with training mean recurrence 4/8/16/32 in figures. **shown.**
- **McLeish et al. (2511.07384):** conversion of a pretrained LM to recurrent depth. Curriculum: linear over 25% of steps (two-phase) or 1−√ over first 75% (math), then constant mean recurrence 32. Table 1 (zero-shot, 4,8,4 model): GSM8K 25.6 (test rec 1, single phase) → 52.0 (test rec 32); MATH 8.8 → 14.5. Two-phase: GSM8K 26.5 → 51.2. **shown.** Authors call test-time extrapolation beyond training recurrence "one unsolved problem"; no extrapolation numbers reported. **shown.**
- **Coconut:** curriculum replaces language steps with latent steps stage by stage (c=1 for logic tasks, c=2 for GSM8k). Table 1 (accuracy %): GSM8k 34.1 (CoT 42.9); ProntoQA 99.8 (CoT 98.8); ProsQA 97.0 (CoT 77.5). Without curriculum: GSM8k 14.4, ProntoQA 52.4, ProsQA 76.1. **shown.**
- **Ouro (2510.25741):** learned per-token depth via entropy-regularized objective; 7.7T tokens; claims 1.4B/2.6B match up to 12B models. **suggested** (search summary). No extrapolation numbers found.
- Gap, **untested:** whether lognormal-Poisson sampling beats a fixed-lap curriculum for our 2-layer-MLP-plus-residual adapter on a 3.7B model.

## 3. Input re-injection

- **Huginn:** embedded input e re-injected every recurrence step via adapter concat(s, e) → h. "Concatenation works best at scale; addition works equally well only for smaller models." **shown.** Additive adapter in McLeish: higher training loss, similar eval accuracy. **shown.**
- **Saunshi et al. (2502.17416):** the looped block is defined without input re-injection; no with/without-injection ablation reported. Loop scaling: Acc = α·log(D)+β; loop-to-parameter benefit ratio 1.19× on reasoning primitives. **shown** (from HTML v1; v2 URL 404). Example: 1B Pile reasoning primitives, 4×1 loops 19.4% vs 4×6 loops 56.9%. **shown.**
- Evidence for re-injection benefit comes from Huginn only (the concat-vs-add comparison). No paper in this search isolated the effect cleanly. **untested** for our setup.

## 4. Stability

- **Parcae (2604.12946, Apr 2026):** treats looping as a nonlinear time-variant system; attributes instability in prior looped models to large spectral norms of the injection parameters; constrains them via a negative-diagonal parameterization. Up to 6.3% lower perplexity than prior looped models. **suggested** (secondary summaries; the primary PDF not read). Test-time gain from more loops follows a saturating exponential decay. **suggested.**
- **Huginn:** Muon optimizer stabilizes training where AdamW spikes. **shown.** Noise injection "not helpful in preliminary runs" (no numbers). **shown** (text).
- **Causal/adversarial test of Coconut (2512.21711):** token-swap on LLaMA 3 8B MMLU: Coconut 60.9 → 61.0 accuracy, 17.9% answer inconsistency; CoT 62.8 → 43.4, 52.8% inconsistency. Coconut latents appear insensitive to corruption, which the authors read as latents not carrying reasoning. Authors state "no formal causal link" between latents and reasoning. **shown.** Hidden-state norms and per-step trajectories are not reported. The same paper's Fig. 5 shows latents "far from the main vocabulary embedding manifold" (qualitative). **shown** (qualitative).
- Contraction/fixed-point regularizers, per-lap state normalization, and orbit/divergence measurements: no 2024–26 quantitative source found in this pass. **untested.**

## Implications for our design (suggested)

1. Keep a norm step on the state path (final RMSNorm already on the last hidden state per Coconut's remark, plus RMS-matching to embedding scale), and test it against the mixture-of-embeddings alternative (MoI-style), which the ablation supports.
2. Use a Huginn-style random-depth schedule with truncated backprop over the last ~8 laps; test extrapolation explicitly, since no source shows it working.
3. Ablate input re-injection (concat vs none); this is cheap and Huginn is the only quantitative evidence.
4. Use Muon or a lower LR if we see loss spikes; monitor state norm per lap.

Pass marks and kill tests are not set here; they belong in the experiment plan.

## Sources
arXiv: 2412.06769, 2502.21074, 2502.05171, 2511.07384, 2505.16552, 2505.15778, 2505.14827, 2502.17416, 2510.25741, 2604.12946, 2512.21711.
