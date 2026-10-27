# CODI distillation loss and follow-ups (research note A)

Labels: **shown** = paper table/equation as read; **suggested** = authors' argument or weak evidence; **untested** = not checked. Numbers came from WebFetch summaries of the arXiv HTML, so re-check the exact tables before quoting them in a paper.

## 1. CODI (arXiv 2502.21074, EMNLP 2025)

**Distillation loss (shown, Eq. 5 in v3 HTML)**
- L_KD = (1/M) Σ_{l=1..M} | sg[h_teacher^l] − h_student^l |, averaged over all M LLM layers.
- Position: the colon in "The answer is:", i.e. the token just before the answer. Only this one position is matched.
- Layers: all layers, averaged. No last-layer-only variant is described. No per-layer ablation.
- Normalization: each layer's activations are divided by the std of the teacher's activations in the batch (Sec. 3.5).
- Stop-gradient on the teacher hidden states.
- Distance: Eq. says L1, but the Appendix H code uses smooth_L1 (inconsistency to note).
- Total loss (Eq. 1): L = α·L_student + β·L_KD + γ·L_teacher. α = 1 always. GPT-2: β = 1, γ = 1. LLaMA-1B: the paper is inconsistent (Appendix F says β = 20, Appendix A says γ = 20, β = 1).
- Projection on continuous thoughts (Sec. 3.3, Fig. A1): Linear → GELU → Linear → LayerNorm. Hidden width not stated.
- Latents: 6 continuous thoughts between <bot> and <eot>.

**Ablations (shown, GPT-2, GSM8k-Aug, Table 2)**
| Variant | Acc (%) |
|---|---|
| No-CoT SFT | 19.1 |
| CODI (full) | 43.7 |
| Separate static teacher | 27.1 |
| Multitask student (shared model also learns CoT) | 42.2 |
| w/o L1 distillation loss | 24.5 |
| Keep last CoT step in teacher | 31.7 |
| w/o projection layer | 42.5 |

- Number of latents: Fig. 5 only, no numbers in text; the authors say peak is at 6 (shown, qualitative).
- LLaMA-1B β sweep (Table A4): β=1 46.5, β=5 50.2, β=10 49.1, β=20 51.9, β=30 51.4.
- GPT-2 γ sweep (Table A5): γ=0.5 36.3 (20 ep) / 38.2 (40 ep); γ=1 38.4 / 43.7; γ=2 41.6 / 41.9; γ=3 40.8 (20 ep).
- Layer-wise analysis: none reported (shown, absence).

## 2. Follow-ups

**SIM-CoT (arXiv 2509.20317, v2)**
- Matches: per-step last-layer hidden state at the final position of each latent step (one latent per textual step, not per chunk). Other layers not matched.
- Loss: L = λ_step·L_step + λ_lm·L_ans. L_step = decoder cross-entropy over each textual step, conditioned on the latent (decoder is a throwaway auxiliary). No stop-grad. λ values not in the text I read.
- Gains (shown, their tables; CODI numbers as they list them):
  - GPT-2 GSM8k-Aug 42.0 → 42.6 (+0.6); OOD avg 48.0 → 48.3.
  - LLaMA-3.2-1B GSM8k-Aug 52.7 → 56.1 (+3.4); OOD 55.8 → 56.8.
  - LLaMA-3.2-3B 60.8 → 62.3 (+1.5); OOD 62.1 → 62.8.
  - LLaMA-3.1-8B 61.1 → 64.1 (+3.0); OOD 64.4 → 65.2.
- Ablations: decoder size (1B 56.1, 3B 50.4, 8B 50.0; shown). No ablation removing per-step supervision. No layer ablation.

**KaVa (arXiv 2510.02312)**
- Matches: KV cache, not hidden states. Teacher K/V per layer and head on the ground-truth CoT, compressed to latent length by R-KV-style eviction (λ=0.1, training only). Student K/V of latent tokens. Lp (L1 or MSE) with stop-grad on teacher, slot-wise matching. Also keeps CODI's hidden-state loss (α1 = 0 for MetaMathQA).
- Gains (shown, Table 1, Llama3.2-1B-Instruct, CODI → KaVa): GSM8k AUG 53.9 → 56.5; GSM-Hard 12.6 → 12.7; SVAMP 59.0 → 58.9; GSM8k AUG-NL 50.1 → 55.7; GSM-Hard NL 11.5 → 12.8; SVAMP NL 56.2 → 58.6.
- Llama-3B: GSM8k AUG 61.0 → 65.7; AUG-NL 55.9 → 60.0; SVAMP NL 70.1 vs KaVa 66.1 (KaVa loses).
- Forward passes (Table 2, Llama-1B): CODI 11.9 vs KaVa 6.9 on GSM8k AUG.
- Ablation (Table 3, GSM8k, Llama-1B): full 56.5; w/o CODI loss 52.8; w/o projection 52.2 (column labels garbled, mapping inferred).
- Last trace step kept: 51.2 vs 56.5 dropped (shown, Table 4). Same direction as CODI's own result.
- Layers: no layer-count ablation. Latent-count: Fig. 7, no numbers.

**PCCoT (arXiv 2506.18582)**
- Not a matching-target paper. Keeps CODI's last-answer-token L1 distillation on prediction distributions, adds Jacobi-iteration parallel latents (24 latents, T=3). Only embeddings of special tokens trained (LoRA r=128).
- Accuracy (shown, GPT-2 small): PCCoT GSM8K 49.48 ± 0.31, GSM8K-NL 49.23 vs CODI literature 43.7 / 35.3. Llama-1B: PCCoT 53.35 vs CODI 55.6 on GSM8K (CODI wins); NL 50.72 vs 49.7.
- Speed (shown): GPT-2 training 13.72 h vs continuous CoT 24.91 h; inference 0.199 s vs 0.443 s.
- Ablation: fixed latent embeddings 47.31 vs 49.48.

**Tale of Two Regimes (arXiv 2607.16972, Jul 2026)**
- Abstract only read. Proposes C-MTP: direct supervision of each latent as the mean embedding of the CoT tokens it compresses. Claims beats a prior direct-supervision method; on short traces competitive with indirect (CODI-style) methods; both degrade on long traces (~65% reported). No CODI gain number in the abstract. Loss form not read. Treat as untested for our purposes.

**Other 2026 candidates checked**
- No clean 2026 "improves CODI on GSM8k" paper found in search. Closest was 2607.16972 above. MarCos (arXiv 2509.25020) is a transformer change compared against CoT, not CODI.
- CoLaR (arXiv 2505.16552, NeurIPS 2025): merges consecutive token embeddings, latent head predicts next compressed embedding. Gain is +14.1% over latent baselines (Coconut and CODI pooled), not a CODI-only number. Shown as authors' claim.
- Mechanistic check of CODI (arXiv 2602.00449, Liang & Pan): bridge states decodable on 2-3 hop tasks, but no reliable full latent rollout at longer hops. Shown (their analysis).

## 3. Which layers carry signal; multi-position matching

- CODI itself: matches all layers at one position. No ablation of layer subsets. (shown, absence)
- SIM-CoT: matches only last layer, per step. Authors give no layer ablation. (shown, absence)
- KaVa: matches K/V of all layers and heads, the cache rather than states. No layer ablation. (shown, absence)
- Coconut/CODI analyses (2512.21711, 2602.00449): the latent tokens show little steering sensitivity in Coconut; CODI has partial bridge decoding. No middle-vs-last-layer comparison found. (suggested at best)
- Multiple positions: SIM-CoT is per-step, which is the closest thing to chunk-level matching in this set. CODI and PCCoT match only one token. No paper I found matches many chunks of the written trace against latent laps with a sweep. (shown: absence)
- Untested: whether matching middle layers beats last layers, or whether chunk-level matching beats single-point matching at our 3.7B scale.

## Notes for our design
- CODI's own choices are mostly untested beyond GPT-2/LLaMA-1B. The loss scale normalization (divide by teacher std) and β vary by appendix. Pin them ourselves.
- Biggest reported lift over CODI is SIM-CoT per-step supervision (+3.0 to +3.4 on 1B/8B). Its ablation of the step loss itself is missing.
- Verify numbers above against the arXiv tables before citing.
