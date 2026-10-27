# Does the source of the written trace matter for latent-CoT students?

Scope: web search and abstract-level fetches only. I did not read full papers, method sections or result tables, so most numbers below are from search summaries and are labelled accordingly. No paper found directly compares (a) templated traces, (b) the model's own sampled reasoning and (c) LLM-rewritten short traces as sources for a latent student. That gap is the main finding.

## Labels
- **shown**: stated in an abstract I fetched.
- **suggested**: from a search-result summary, not checked against the paper.
- **untested**: my recollection, or a claim I could not find.

## 1. Trace format effects on latent-CoT accuracy

- **SIM-CoT, arXiv 2509.20317 (ICLR 2026).** Coconut and CODI degrade as the number of latent tokens grows (Coconut collapses at 8 or 16 tokens in the v1 preprint). The paper attributes this to missing step-level supervision, and adds an auxiliary decoder that aligns each latent to an explicit step. Gains: +8.2% for Coconut on GPT-2 and +3.0% for CODI on LLaMA-3.1-8B (**suggested**, from the abstract summary). A review gives +0.6% for CODI on GPT-2, so the table should be checked.
- **C-MTP, arXiv 2607.16972 ("A Tale of Two Regimes").** Shown in the abstract: direct supervision (each latent = mean embedding of the CoT tokens it compresses) is competitive with indirect methods on CoT traces under about 100 tokens. On traces of a few hundred tokens or more, both direct and indirect methods do poorly (a "roughly 65%" drop is reported). This is the closest evidence that trace length, not only trace source, drives latent-student failure.
- **Coconut on GSM8k and ProsQA (arXiv 2412.06769).** Recalled, **untested**: GSM8k CoT 42.9, Coconut 34.1, no-CoT 16.5, and iCoT around 30.0 on GPT-2. ProsQA: Coconut 97% vs CoT 77.5%, with 14.2 vs 49.4 tokens (**suggested** from a search summary, which matches the paper as I recall it). Both use templated or short traces, so they are a baseline for option (a), not a test of it.
- **Curriculum ablation, arXiv 2602.01148 ("Capabilities and Fundamental Limits of Latent CoT").** Suggested: removing curriculum drops ProntoQA accuracy from 99.8% to 52.4%. Curriculum, not trace source, is the bigger lever in this summary.
- **Coconut sensitivity, arXiv 2512.11816.** Suggested: latent SFT is highly sensitive to design choices and struggles on math; the authors propose RL.
- **Critique, arXiv 2512.21711 ("Do Latent Tokens Think?").** Suggested: Coconut exploits dataset artifacts on MMLU and HotpotQA. This matters for any claim that a trace source improves reasoning rather than shortcuts.

## 2. Evidence sentences / supporting facts as rationales

- Searches returned only the original HotpotQA paper (arXiv 1809.09600), which provides sentence-level supporting-fact labels (about 2–3 per question). **shown** for the dataset description only.
- I found **no 2024–2026 paper** that uses bAbI or HotpotQA supporting facts as CoT for a latent student. Treat this as untested. A sensible experiment would use supporting facts (a) as the latent trace and (b) as a textual rationale with the same token budget.

## 3. CoT-SFT warm start, then internalise

- **arXiv 2607.16972** (above): warm-start and multi-task training gave similar results on GSM8k-Aug structured traces with Llama-3.2-1B-Instruct. The authors call warm-start more principled and use it in the main table. Both regimes fall short of standard CoT-SFT on realistic traces (**suggested**).
- **Abstract-CoT, arXiv 2604.22709.** Shown: a warm-up alternates bottlenecked SFT (verbal CoT with the verbal reasoning masked, so the abstract tokens carry the information) with self-distillation, then RL. Reports up to 11.6× fewer reasoning tokens. The abstract does not say whether the verbal CoT was gold or model-generated.
- **Segment-level distillation, arXiv 2512.21002.** Shown in the abstract: training on the first 50% of each sequence keeps about 91% of full-sequence performance on math, while cutting training time, memory and FLOPs by about 50%. The paper finds that distilling only the CoT tokens can work when the CoT already contains the prompt and answer. It does not name the models in the abstract.
- **Curriculum, arXiv 2602.01148** (above): curriculum is theoretically argued to be necessary. This suggests warm-start is one form of the same idea.

## 4. Gold-but-short vs model-generated traces for the latent student

- **Small Models Struggle to Learn from Strong Reasoners, arXiv 2502.12143.** Shown in the abstract: models at or under 3B do not reliably gain from long CoT or from distillation from larger models. They do better on shorter, simpler chains. The proposed Mix Distillation (long and short, or large and small teacher traces) beats either alone (**suggested**, numbers not checked). This is the strongest support for option (c), with the caveat that it is about explicit students, not latent ones.
- **Munkhbat et al., Findings of ACL 2025** (search summary): self-generated concise traces from best-of-N sampling and few-shot conditioning cut output tokens by about 30% with average accuracy maintained. This supports option (b) as a source of short traces, for explicit models (**suggested**).
- **iCoT, arXiv 2405.14838** (stepwise internalisation). Its method drops one explicit token per stage. It uses gold explicit CoT (the GSM8k-style traces), so it is an example of option (a). I did not confirm its GPT-2 GSM8k number.

## Summary of what is and is not known

- Shown or suggested: trace length and curriculum matter more clearly than a trace's origin. Short traces help small students. Warm-start and curriculum are roughly equivalent in one ablation.
- Untested: no head-to-head of templated vs self-sampled vs LLM-rewritten traces for Coconut, CODI, iCoT or SIM-CoT was found. A minimal test would hold trace length fixed and vary only the source, on GSM8k with GPT-2 and CODI, and report accuracy against the Coconut 34.1 / CoT 42.9 baseline.
- Pass marks, untested proposal: the source effect is real only if the best source beats the worst by more than 2 points on GSM8k across 3 seeds, and the result would be wrong if the three sources fall within seed noise.

## Limits
- Search results only, plus three abstract fetches (2607.16972, 2512.21002, 2604.22709). Full method and result sections were not read.
- Related but not checked: 2406.14511 ("Investigating Mysteries of CoT-Augmented Distillation"), which asks whether rationales must be coherent and whether a few key tokens suffice (**suggested**).
