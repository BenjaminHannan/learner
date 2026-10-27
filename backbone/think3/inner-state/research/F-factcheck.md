# Fact-check report (F)

Source: arxiv.org/html pages, checked against each paper's own tables and sections.

## 1. CODI 2502.21074 (GPT-2, GSM8k-Aug ablation)
Table 2 (Section 4.4, Ablation Studies):
- CODI 43.7: CONFIRMED
- w/o L1 loss (distillation loss) 24.5: CONFIRMED
- w/o Projection 42.5: CONFIRMED
- separate static teacher 27.1: CONFIRMED
- w/ CoT last step (keeping last CoT step) 31.7: CONFIRMED

Projection layer: Section 3.3 says "a two-layer MLP followed by layer normalization." Figure A1 code is Linear -> GELU -> Linear -> LayerNorm. CONFIRMED.

KD loss: Eq. 5 is written as an absolute-difference (L1) form, averaged over layers. Figure A1 code calls `smooth_l1_loss`. The paper is internally inconsistent: L1 in the equation, smooth L1 in the code.

Normalization: CONFIRMED. Section 3.5 says activations are divided by the standard deviation of the teacher's activations within the batch. The code divides by the teacher hidden-state `std()`.

## 2. SIM-CoT 2509.20317
- LLaMA-3.2-1B, CODI 52.7 -> SIM-CoT on CODI 56.1 (Table 2, main results): CONFIRMED
- LLaMA-3.1-8B, CODI 61.1 -> 64.1 (Table 3): CONFIRMED
- Step supervision on every latent, auxiliary decoder dropped at inference: CONFIRMED. Step loss (Eq. 6) sums over all K latents, with each z_k decoding its own reasoning step. The decoder is removed at inference.
- Ablation removing the step loss: NOT FOUND. The nearest items are the decoder-size ablation (Table 4a) and the latent-count comparison with Coconut (Fig. 3). Neither removes the step loss.

## 3. KaVa 2510.02312, Table 1
Columns: AUG (GSM8k, GSM8k-Hard, SVAMP) and AUG-NL (GSM8k, GSM8k-Hard, SVAMP).
- Qwen2.5-0.5B-Instruct, CODI, AUG GSM8k 37.5: CONFIRMED
- Qwen2.5-0.5B-Instruct, CODI, AUG-NL GSM8k 20.2: CONFIRMED
- Qwen2.5-0.5B-Instruct, KaVa, AUG GSM8k 46.9 (±1.4): CONFIRMED
- Qwen2.5-0.5B-Instruct, KaVa, AUG-NL GSM8k 44.4 (±1.8): CONFIRMED
- Llama3.2-1B-Instruct, CODI, AUG GSM8k 53.9 (±0.5): CONFIRMED. The paper also lists 55.6 in parentheses, marked as copied from the CODI/PCCoT papers.
- Llama3.2-1B-Instruct, CODI, AUG-NL GSM8k 50.1 (±0.1): CONFIRMED. Parenthetical 49.7 is also copied.
- Llama3.2-1B-Instruct, KaVa, AUG GSM8k 56.5: CONFIRMED
- Llama3.2-1B-Instruct, KaVa, AUG-NL GSM8k 55.7: CONFIRMED

## 4. "Training Continuous CoT Models: A Tale of Two Regimes" 2607.16972
Table 5 ("Results on MATH across two backbones"), Qwen2.5-1.5B-Instruct:
- CoT-SFT 52.80: CONFIRMED, with the correction that the model is Qwen2.5-1.5B-Instruct, not "Qwen-1.5B".
- CODI-6 12.44, CODI-10 14.52, CODI-20 12.96: CONFIRMED. The range 12.4-14.5 matches the three CODI settings.
- The paper cites Table 14 (Appendix G.7) for this comparison. The fetched text was truncated before that table, so only Table 5 is verified.

## 5. Coconut 2412.06769, Table 1 (Section 5)
- GSM8k, Coconut with curriculum 34.1 (±1.5): CONFIRMED
- GSM8k, Coconut w/o curriculum 14.4 (±0.8): CONFIRMED
- ProsQA, Coconut 97.0 (±0.3): CONFIRMED

## 6. 2602.22441, Table 1 (Section 4.3, Interventional Analysis)
LLaMA row, GSM8K column:
- CODI clean 55.57: CONFIRMED
- CODI with Gaussian noise, sigma = 100 on latents: 27.45: CONFIRMED. Section 4.3 states sigma = 100.

## Summary
All numeric claims confirmed. Two corrections: (a) CODI's KD loss is written as L1 but coded as smooth L1; (b) the 2607.16972 model is Qwen2.5-1.5B-Instruct. One item NOT FOUND: a SIM-CoT ablation with the step loss removed.
