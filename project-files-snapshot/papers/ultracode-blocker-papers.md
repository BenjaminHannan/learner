# New papers for the arithmetic / state-tracking blocker (2026-10-05)

Scope: why a frozen LFM2.5-1.2B + ~9M looped core + 8 soft prefix vectors cannot fit multi-step arithmetic and state tracking, even on 2,000 practised rows. Not repeated: everything in learning-blocker-papers.md, arxiv-bangers-scan.md, blocker-ideas.md (including 2310.19698, 2510.00494, 2609.01117, 2412.17747).
"Read" = **abstract** (I opened the arXiv abstract page and the summary below comes from it) or **snippet** (search-result summary only, unchecked). Nobody opened a paper in full. This list only finds papers; it proposes no experiments. Claims are the papers' own, on their own (mostly from-scratch or fine-tuned) models, not shown for our setup.

## 1. Data and format for learning arithmetic without CoT

1. **2307.03381 - Teaching Arithmetic to Small Transformers (Lee et al., 2023/ICLR 2024)** - abstract
   - Plain "a+b=c" data is a poor format; reversing the output digits (least significant first) and adding step-by-step scratchpad data raise accuracy, sample efficiency and speed. Search snippet (unchecked): plain addition plateaus near 85% at 10k samples, while reversed output shows a sharp phase transition between ~1,000 and 4,000 samples to perfect 3-digit addition.
   - Relevance: our 2,000 rows may sit just below such a threshold for the plain format. Answer ordering (reverse digits) is an input/target format choice, but our LM writes the answer itself, so check whether it applies.
2. **2405.17399 - Transformers Can Do Arithmetic with the Right Embeddings (McLeish et al., 2024)** - snippet
   - Abacus embeddings (position within each number) let models trained on 20-digit operands reach up to 99% on 100-digit addition; input injection (skip from input to each layer) cuts errors ~50%; looping plus Abacus helps; gains carry to sorting and multiplication.
   - Relevance: digit-position tracking is named as the main obstacle; input injection resembles re-feeding the question to every loop of our core. Our pipe passes contextual LM features, which may blur digit positions.
3. **2405.20671 - Position Coupling (Cho et al., NeurIPS 2024)** - abstract
   - Giving digits of equal significance the same position id; trained on 1-30 digits, generalises to 200 digits; a 1-layer transformer with coupled positions provably does addition, one without position info cannot.
   - Relevance: same diagnosis as 2405.17399 (alignment of digits is the hard part). Possible reason the thin pipe from LM features loses the operands' structure.
4. **2409.15647 - Looped Transformers for Length Generalization (Fan et al., ICLR 2025)** - snippet
   - Looped transformers with an adaptive number of steps generalise to unseen lengths on tasks that are repeated applications of a simple step (addition, parity, etc.).
   - Relevance: our tasks (chain_ops, state_update) are exactly "repeat one step N times"; the paper trains with step-count supervision, which our core may lack.

## 2. Is implicit (no-CoT) multi-step reasoning learnable, and what makes it work

5. **2405.14838 - From Explicit CoT to Implicit CoT: Stepwise Internalization (Deng, Choi, Shieber, 2024)** - abstract
   - Train with CoT, then delete CoT tokens gradually while fine-tuning. GPT-2 Small reaches up to 99% on 9x9 multiplication (plain training maxes near 4x4); Mistral 7B passes 50% on GSM8K with no intermediate steps.
   - Relevance: strongest evidence that answer-only training fails but a curriculum from explicit steps succeeds. Our rows presumably train answer-only; this suggests intermediate-step data as a training scaffold.
6. **2311.01460 - Implicit CoT Reasoning via Knowledge Distillation (Deng et al., 2023)** - snippet
   - A student reads hidden states of a CoT-trained teacher and does the reasoning "vertically" across layers; solves multi-digit multiplication and GSM8K without emitting steps.
   - Relevance: gives a per-step hidden-state target (teacher states) rather than only a final-answer loss; our core gets only the answer signal.
7. **2405.15071 - Grokked Transformers are Implicit Reasoners (Wang et al., NeurIPS 2024)** - abstract
   - Implicit composition/comparison reasoning is learned only via grokking, training far past overfitting; composition fails to generalise out of distribution, comparison succeeds.
   - Relevance: 2,000 rows with early stopping may stop before any generalising circuit forms (a "fit" that is memorisation). Training much longer, or more data, is the paper's lever.
8. **2502.17416 - Reasoning with Latent Thoughts: On the Power of Looped Transformers (Saunshi et al., ICLR 2025)** - abstract
   - A k-layer block looped L times nearly matches a kL-layer model on addition and similar synthetic tasks; a looped model can simulate T steps of CoT with T loops.
   - Relevance: supports that loops can carry steps, but the claim concerns a model with the loop inside the reader; ours loops outside the LM and exits through 8 vectors.
9. **2412.01113 - Think-to-Talk or Talk-to-Think? (2024)** - snippet
   - On symbolic multi-step arithmetic, probes show models do not solve the whole problem when reading it; sub-answers appear incrementally while writing the chain.
   - Relevance: an answer-first, no-CoT format asks for something the LM does not normally do, so the frozen LM may not hold intermediate values for the core to read via a thin pipe.
10. **2507.02199 - Latent Chain-of-Thought? Decoding the Depth-Recurrent Transformer (2025)** - snippet
    - In Huginn-3.5B (depth-recurrent), probing finds limited interpretable latent CoT and inconsistent probes across recurrent blocks.
    - Relevance: warns that loops need not store stepwise intermediates; check ours with probes before trusting the loop count.

## 3. Latents handed to a decoder; forcing the latent to carry the answer

11. **2412.06769 - Coconut: Training LLMs to Reason in a Continuous Latent Space (Hao et al., 2024; COLM 2025)** - abstract
    - Feeds the last hidden state back as the next input embedding; training is a curriculum that replaces CoT steps with latent thoughts progressively (curriculum detail from memory, not the page I opened). Beats CoT on search-heavy logic tasks; weaker on arithmetic-style tasks in the paper's own results (from memory).
    - Relevance: a stage-wise replacement curriculum is the standard way to get latents to carry steps.
12. **2502.21074 - CODI: Compressing CoT into Continuous Space via Self-Distillation (2025)** - abstract
    - One model is teacher (explicit CoT) and student (latent thoughts); aligns hidden activations at the answer-generating token with an L1 loss. First implicit CoT to match explicit CoT on GSM8K at GPT-2 scale (3.1x compression, +28.2% over prior implicit).
    - Relevance: gives a direct supervised signal on what the latent must hold at the point of answering; a candidate for forcing the 8 prefix vectors to carry the answer.
13. **2412.13171 - Compressed Chain of Thought (Cheng, Van Durme, 2024)** - snippet
    - Generates variable-length continuous "contemplation tokens" as compressed versions of reasoning chains, working with off-the-shelf decoder LMs; accuracy improves with more tokens.
    - Relevance: a trained latent producer feeding a decoder, with a compression target from the chain.
14. **2505.15778 - Soft Thinking (Zhang et al., 2025)** - snippet
    - Training-free: replaces sampled tokens with probability-weighted mixtures of token embeddings; small gains (up to +2.48 pass@1) and fewer tokens.
    - Relevance: low. Shows soft inputs are readable by an LM without training, but no new computation is taught.
15. **2602.22441 - How Do Latent Reasoning Methods Perform Under Weak and Strong Supervision? (Cui et al., 2026)** - abstract
    - Many latent methods get high accuracy without relying on the latents (shortcut). Stronger supervision reduces shortcuts but narrows what latents can hold; weak supervision keeps richer latents but more shortcuts.
    - Relevance: names our failure mode (frozen LM answers alone) and the trade-off in the fix.
16. **2512.21711 - Do Latent Tokens Think? Causal and Adversarial Analysis of Coconut (2025)** - abstract
    - Steering/perturbing Coconut latents barely changes outputs; the model exploits dataset artifacts, so latents act as placeholders. Tested on MMLU and HotpotQA, not arithmetic.
    - Relevance: a test to copy: perturb or swap the prefix vectors and see whether answers change. If not, the LM is ignoring the core.
17. **2605.07106 - Retrieve, Integrate, and Synthesize: Spatial-Semantic Grounded Latent Visual Reasoning (2026)** - snippet
    - Progressive attention mask: with rising probability, answer tokens cannot attend to the original image/query and must use the latent tokens; an explicit fix for decoders bypassing latents (visual domain).
    - Relevance: the same bypass exists in ours (the LM reads the question directly). The mask idea transfers in principle, but the question is already needed by the LM; untested here.
18. **2310.02226 - Think before you speak: Pause Tokens (Goyal et al., ICLR 2024)** - snippet
    - Learnable pause tokens before answering give gains only when the model is pretrained AND fine-tuned with them (1B model: +18% EM SQuAD, +1% GSM8K).
    - Relevance: extra compute slots in a frozen LM do little for arithmetic (+1% GSM8K), so more prefix vectors alone is unlikely to be the fix.

## 4. Prefix/prompt tuning versus weight changes

19. **2405.09673 - LoRA Learns Less and Forgets Less (Biderman et al., TMLR 2024)** - snippet
    - On code and math, LoRA at standard ranks clearly underperforms full fine-tuning; full fine-tuning learns perturbations of 10-100x higher rank. LoRA also forgets less.
    - Relevance: even LoRA is a weak learner of new math skills at low rank; the prefix-only route is lower still (see Petrov 2310.19698, already in notes, and the 2609.36585 LoRA result). Use as a calibration for how much a small LoRA can be expected to give.

## Summary for Ben (plain language)
- Small models learn arithmetic from scratch when (a) the digits are lined up (position tricks), (b) the answer is written in an easy order, and (c) they are trained with step-by-step examples that are later removed. Answer-only training with 2,000 rows is the hard setting in most of these papers.
- Models that "think in hidden vectors" often learn to ignore those vectors when the decoder can read the question itself; the fixes are a matching loss on the hidden state (CODI), a mask that blocks the shortcut, or a check that perturbs the vectors.
- A prefix is a weak tool for teaching a new calculation; even LoRA is weaker than full training.
- Nothing here is shown on our setup; the shown/suggested/untested labels are in each entry's "Relevance" line (everything is suggested at best).
