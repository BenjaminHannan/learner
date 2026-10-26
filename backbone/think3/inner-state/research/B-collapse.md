# B: latent collapse / shortcutting in continuous latent reasoning (2024-2026)

Labels: **shown** = number from a paper's table or text I read; **suggested** = paper's interpretation or a secondary source; **untested** = my idea, no evidence found.
Caveat: I read abstracts and search snippets, not full papers, except where a table value is quoted via an HTML fetch (2602.22441). Verify numbers before citing.

## 1. Collapse and shortcutting: evidence and diagnostics

- **2512.21711** "Do Latent Tokens Think?" (Zhang et al., Dec 2025). COCONUT latents are "uninterpretable placeholders." Diagnostics: steering (perturb token subsets; COCONUT shows minimal sensitivity, unlike explicit CoT) and shortcut tests on biased/OOD inputs (MMLU, HotpotQA). Shown: COCONUT exploits dataset artifacts. No numbers in the abstract, model sizes not stated in the abstract. Lesion and probing not used.
- **2605.18445** "What's Holding Back Latent Visual Reasoning?" (2026, multimodal). Shown (abstract): swapping latents for dummy tokens leaves accuracy unchanged; generated latents drift from oracle latents and cluster in a narrow region. Diagnostics: token replacement (lesion-style), oracle-latent analysis, and fine-tuning on a diagnostic dataset. Closest to your "swap" finding.
- **2602.22441** "How Do Latent Reasoning Methods Perform Under Weak and Strong Supervision?" (Feb 2026). Models: GPT-2 (full FT) and Llama-3.2-1B-Instruct (LoRA). Shown:
  - Depth-0 test (latent steps removed at inference): ProsQA barely changes for most methods; GSM8K CODI keeps ~30% on Llama.
  - Gaussian noise σ=100 on latent before answer, Llama GSM8K: Coconut 36.97→20.61; CODI 55.57→27.45; SIM-CoT 56.03→10.08; CoLaR 25.23→3.32. Explicit CoT with noise on its token: 61.74→0.03.
  - Strong supervision reduces shortcuts but narrows diversity (GPT-2 mean distinct answers: Coconut 15.84, CODI 12.96, SIM-CoT 13.57, CoLaR 3.21). The Llama pattern is not uniform (CoLaR 7.63 vs SIM-CoT 7.46).
  - Coconut GPT-2 GSM8K 34.09%; under noise 3.79%.
- **2602.10229** Latent Thoughts Tuning (2026). Shown: removing curriculum stage costs and Coconut latents collapse to near-identical representations across samples within a few steps; removing Stage 2 costs 3.9 pts (3B) and 6.7 pts (8B) average accuracy. Details from search snippet only.
- **2604.04902** Dilgren & Wiegreffe (Apr 2026). Shown: on logical datasets, LRMs (Coconut/CODI, two models, sizes not in abstract) often give the same final answer without latents; when latents matter, gold traces decode from them 65-93% of the time. Diagnostic is decoding, not a fix.
- **2509.20317** SIM-CoT (ICLR 2026). Suggested (paper's account): failed runs have homogeneous latents, decoded tokens mostly numbers, operators lost, inter-latent distance shrinks; instability appears as latent count grows from 3 to 5. Diagnostics: decoding each latent onto a vocabulary, inter-latent distance.
- **2606.12689** "Observable Patterns Are Not Explanations" (Jun 2026, Aswal et al.). Only a third-party blurb read. Suggested: latent traces are hidden computation; establish causality before reading geometry. Read the full paper before citing.
- **2606.01243** "Unlocking the Black Box of Latent Reasoning" (2026). Suggested: structural, causal and geometric probes; training-free decode-time interventions. No numbers read.

## 2. Fixes that force latents to carry information

| Fix | Paper | Evidence | Label |
|---|---|---|---|
| Step-level aux decoder (per-latent decode to its explicit step, dropped at inference) | SIM-CoT 2509.20317 | Coconut +8.2 pts GPT-2; CODI +3.0 pts LLaMA-3.1 8B; GPT-2 beats explicit CoT by 2.1 pts with 2.3x token efficiency; 8B gap closed, not surpassed | shown (abstract) |
| Curriculum replacing written steps | Coconut 2412.06769; iCoT 2405.14838 | iCoT: Mistral 7B >50% GSM8K with no steps (no CoT baseline in abstract). Coconut: abstract gives no numbers; ablations need full paper | shown (iCoT abstract), untested for Coconut numbers here |
| Curriculum removal hurts | LTT 2602.10229 | 3.9 (3B), 6.7 (8B) pts | shown (snippet) |
| Orthogonality penalty on latents | 2510.00494 | Countdown accuracy grows with latent count under strong penalty; validation perplexity worsens | shown (snippet) |
| Contrastive diversity on latents | SoftCoT++ (secondary source) | ablation credits contrastive loss with most gain | suggested (unverified source) |
| Context-Prediction Fusion | cited in 2605.29068 | mitigates inter-sample collapse vs Coconut | suggested (secondary) |
| Stronger supervision | 2602.22441 | less shortcut, less diversity: a trade-off | shown |
| Noise injection as a probe, not a fix | 2602.22441 | exposes which latents are used | shown |
| Question masking / answer dropout / information bottleneck | none found | no paper located | untested |
| Probe-decoded intermediate results as an aux loss | none exact; LOTUS (hyper.ai summary) uses an aux decoder for the chain, dropped at inference, 2.5-6.9x speedup | secondary only | suggested |

## 3. Scale and cost

- Pretrained 1-8B, shown: SIM-CoT (LLaMA-3.1 8B, +3.0 CODI); 2602.22441 (Llama-3.2-1B LoRA); 2602.10229 (3B, 8B); iCoT (Mistral 7B).
- GPT-2 only, shown: 2412.06769 (per search), most SIM-CoT gains are GPT-2.
- Cost: SIM-CoT decoder is training-only, zero inference overhead, but extra training compute not quantified in abstract. Curriculum methods need multi-stage training. Orthogonality and contrastive losses add a hyperparameter (weight). Noise and depth-0 tests are free at inference.

## 4. Diagnostics to borrow for our thinking block

Ranked by what they separate, using numbers reported above:
1. Depth-0 and swap (2602.22441, 2605.18445): if accuracy holds with latents removed or replaced by another example's latents, the answer ignores them. Our flat 0-12 laps result matches this pattern.
2. Gaussian noise on latents (2602.22441): sensitivity test; CODI and SIM-CoT stayed higher under noise than Coconut or CoLaR in Llama GSM8K.
3. Inter-latent distance and decode (2509.20317, 2604.04902): collapse check.
4. Answer diversity (2602.22441): a count of distinct answers under sampling.

## Gaps

- No paper found that tests question masking or an information bottleneck on latent reasoning. Treat as untested.
- Full-paper verification still needed for 2606.12689, 2606.01243, Coconut ablation numbers, and 2510.00494.

## Plain summary

Many latent-reasoning models learn to skip their latents. Papers check this by removing, swapping or adding noise to the latents, and seeing whether the answer changes. The best-supported fixes make each latent answer to a specific intermediate step (SIM-CoT, shown +8.2 on GPT-2 Coconut, +3.0 on 8B CODI) and use a step-by-step curriculum. Stronger supervision reduces shortcuts but also lowers diversity.
