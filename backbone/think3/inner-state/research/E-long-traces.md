# E: Latent distillation with long / natural-language traces

Labels: **shown** = number read from a paper's table or abstract (via WebFetch; small-model summaries of HTML, so re-check against the PDF before citing). **suggested** = from a search snippet or inference. **untested** = proposal only.

## 1. KaVa (arXiv 2510.02312, ICLR 2026)
Distills a compressed KV cache of a CoT teacher into a latent student (self-distillation). 24 latent tokens (3 iterations).

Test accuracy, GSM8K / GSM-Hard / SVAMP (**shown**, Table 1):

| Model | Method | AUG (equation) | AUG-NL (natural language) |
|---|---|---|---|
| Qwen2.5-0.5B | CoT-SFT | 50.6 / 12.6 / 54.3 | 48.5 / 12.6 / 57.3 |
| | CODI | 37.5 / 8.1 / 47.0 | 20.2 / 4.9 / 33.3 |
| | KaVa | 46.9 / 10.8 / 50.6 | 44.4 / 10.2 / 46.5 |
| Llama3.2-1B | CoT-SFT | 63.4 / 14.8 / 67.9 | 53.2 / 13.3 / 62.9 |
| | CODI | 53.9 / 12.6 / 59.0 | 50.1 / 11.5 / 56.2 |
| | KaVa | 56.5 / 12.7 / 58.9 | 55.7 / 12.8 / 58.6 |
| Llama3.2-3B | CoT-SFT | 73.2 / 21.6 / 78.0 | 68.4 / 20.5 / 77.6 |
| | CODI | 61.0 / 15.0 / 72.4 | 55.9 / 13.6 / 70.1 |
| | KaVa | 65.7 / 15.2 / 72.7 | 60.0 / 14.8 / 66.1 |

- **shown**: CODI drops 17.3 pts on Qwen-0.5B GSM8K from AUG to AUG-NL; KaVa drops 2.5 pts. On Llama-1B, KaVa drops 0.8 vs CODI 3.8 vs CoT-SFT 10.2.
- **shown**: KaVa is not uniformly better: on Llama-3B its drop (5.7) is larger than CODI (5.1) and CoT (4.8). Only the 0.5B and 1B results clearly favor it.
- Limits: GSM-style math only. No MATH or long (~70-step) traces in the tables.

## 2. Long-trace failure and what it shows (arXiv 2607.16972)
Models: Llama-3.2-1B-Instruct, Qwen2.5-1.5B-Instruct (LoRA, warm-started from CoT).

GSM8k-Test, Llama (**shown**):

| Method | GSM8k-Aug (compact) | GSM8k-Aug-NL (~70 steps) |
|---|---|---|
| CoT explicit | 61.94 | 53.68 |
| CODI (6 latents) | 53.03 | 47.82 |
| C-MTP-2 (paper's direct method) | 53.30 | 43.49 |
| CoLaR-2 | 41.23 | 23.46 |
| C-MTP-4 | 40.70 | 25.60 |

MATH, written CoT vs latent (**shown**, Table 5):
- Llama-1B: CoT 23.80; C-MTP-2 7.40; CODI-6 8.52, CODI-10 9.92, CODI-20 7.92
- Qwen-1.5B: CoT 52.80; C-MTP-2 14.20; CODI-6 12.44, CODI-10 14.52, CODI-20 12.96

Findings:
- **shown**: changing the latent count (6, 10, 20) moves MATH accuracy by only about 2 pts and recovers none of the gap. So more latents alone does not fix long traces.
- **shown** (paper's attribution, not tested by me): direct methods fail from error accumulation under teacher forcing; indirect methods fail from limited compression.
- The paper reports no chunking or curriculum fix. Its own method is evaluated only on compact traces.

## 3. Compressing the teacher trace
- **Compress-Distill** (arXiv 2606.05988, 2026): post-hoc rewrite of about 283k verified traces per teacher (Qwen3.5-397B, gpt-oss-120B). **shown** (abstract): compressed traces are 8.6-21% of original characters; students keep up to 96% of raw-trace accuracy; raw traces give the highest accuracy at every scale. Note: this is text distillation, not a latent student. Its result is the closest evidence that shorter, rewritten targets cost a few points, not a collapse. Latent-student numbers are untested.
- **When Compression Helps and When It Hurts** (arXiv 2606.21704, 2026): **shown** (abstract, no numbers): rewriting that is more structurally disruptive hurts math; token-level pruning needs symbol-aware signals; training-time compression overstates inference savings because students keep verbose habits.
- **CoLaR** (arXiv 2505.16552, NeurIPS 2025): **shown** (Table 1, GSM8k-Aug, c=2 vs c=5): CoT 49.4 (25.6 tokens); CoLaR-2 40.1 (12.7 latent steps); CoLaR-5 26.8 (5.57). Average over 4 GSM sets: CoT 53.6, CoLaR-2 48.8 (-4.8, chain length -53.3%), CoLaR-5 41.7, Coconut 27.6, CODI repro 14.3. Compression factor c sampled from [1, 5] during training, settable at inference. **Shown**: no long or natural-language trace experiments; math only.
- **CoLaR, RL on MATH** (**shown**, Table 2, c=2, max len 128): DeepSeek-R1-Distill-Qwen-1.5B CoT 23.5 vs CoLaR 14.3 (length 209 to 9.8). Llama-1B CoT 9.71 vs 7.08.
- Teacher-side compression is **suggested** as the cheapest lever: keep the latent student's targets short (equation-like) and rewrite the natural-language teacher. The KaVa table above suggests the NL gap is about 2-5 pts when the teacher is a KV cache, not a text trace.

## 4. Chunk-aligned and hybrid supervision
- **Token Assorted** (arXiv 2502.03275): **shown** (Table, MetaMathQA fine-tune). Hybrid = VQ-VAE latent tokens replace the first CoT chunks, with L=16 CoT tokens per latent, codebook 1024, up to 16 latents, prefix capped at 256 tokens.
  - Llama-3.2-1B: MATH CoT 10.5 vs hybrid 14.7 vs all-latent 6.7; GSM8K 42.7 / 48.7 / 4.2.
  - Llama-3.2-3B: MATH 21.9 / 26.1 / 10.7; GSM8K 69.7 / 73.8 / 12.8.
  - Llama-3.1-8B: MATH 32.9 / 37.2 / 15.7; GSM8K 80.1 / 84.1 / 19.9.
  - Token count -10% to -21%. Mixed text and latent is better than either alone; all-latent is far worse. This is the strongest shown evidence that chunk-level latents work when text is kept in the mix.
- **HRPO** (arXiv 2505.18454, NeurIPS 2025): gated mixing of hidden states into token embeddings, moved in gradually; RL, no CoT traces needed. Gains reported in the abstract only. Numbers not checked. Label: **shown** (claim only, from abstract).
- **SIM-CoT** (arXiv 2509.20317, 2025): per-latent step decoder, dropped at inference; stabilizes many-latent training. Reported +8.2% on GPT-2 (Coconut) and +3.0% on LLaMA-3.1-8B for CODI. **suggested** (from search snippet; numbers not verified). This targets the instability at high latent counts, not the long-trace drop.
- Chunk-aligned supervision for CODI-style distillation on long NL traces: **untested** in the sources I read. No paper I found reports it fixing the 2607 failure.

## 5. How many latents
- **shown** (2607.16972, Table 5): CODI with 6/10/20 latents on MATH is flat (about 8-14 vs CoT 23.8-52.8). More latents do not help enough.
- **shown** (CoLaR): fewer, more-compressed latents cost accuracy (c=5 costs about 8 pts vs c=2 on average). Trace length per latent is the lever.
- **shown** (Token Assorted): 1 latent per 16 CoT tokens, up to 16 per trace, works.
- Rule of thumb from the above, **suggested**: a 100-500 token trace needs roughly 1 latent per 16-25 tokens (6-30 latents) if chunk-aligned; CODI-style global latents at 6-20 show no gain in the 2607 paper.

## Implications for the 3.7B plan (suggested)
1. Start from KaVa-style KV-cache distillation rather than CODI on hidden states. Its NL gap is smaller on 0.5B and 1B (shown). Verify on 3B, where it is not better.
2. Rewrite the teacher trace to equation-like steps first (Compress-Distill evidence), and keep a text-mixed fallback (Token Assorted: hybrid beats all-latent by a wide margin).
3. Measure against a text CoT baseline on the same traces. Fix pass marks in advance.

## Untested
- No paper I read reports KaVa or CoLaR on 100-500 token natural-language traces on a 3-4B model.
- Chunk-aligned CODI on long traces: untested here.
- Compress-Distill has no latent-student results.
