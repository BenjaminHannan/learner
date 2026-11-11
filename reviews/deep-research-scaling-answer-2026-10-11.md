# Why your small looped thinker gains little from more parameters, and what to test

## Short answer

Your clearest clue is the training loss. It barely moved (1.139 → 1.128) even though the thinker roughly tripled in size. When a bigger model cannot even fit its own training data better, the added parameters are not where the limit is.

The papers I found point to four likely causes that fit your numbers:

1. **You grew depth, the axis that helps a looped stack least.** Your stack already runs 24 to 96 block passes.
2. **The parts around the thinker stay the same size while it grows:** the frozen embedder, the 44 latent tokens and the parallel answer writer.
3. **The learning rate was not re-tuned** for a much deeper looped stack.
4. **Exact-match scoring has a ceiling** that hides progress.

Running short of data is probably not the main cause at 10M (a data-starved model would lower its training loss by memorising). It will become the main limit at 100M.

Labels used below: **shown** = a paper measured it; **suggested** = inferred from papers or theory; **untested** = my hypothesis for your setup.

## 1. What your own numbers imply (my arithmetic, untested)

- **Headroom:** 42% of rows are already at 100%, so only 58% can move. Going from 73.0 to 74.7 overall equals about 53.4% → 56.4% on the rows that can move (+2.9).
- **Noise:** each size was one seed with seed noise sd ≈ 1, so the difference between two runs has sd ≈ 1.4. A gain of +1.6 is about 1.1 sd, which is not a reliable measurement. Your earlier 6-seed result (+0.5) suggests the true gain is small.
- **Data per parameter:** 60M word pieces × 4.3 passes ≈ 258M token-passes. That is about 74 per parameter at 3.5M, 26 at 10M and 2.6 at 100M. Counting only unique tokens: 17, 6 and 0.6.
- **Depth:** 2 blocks × 12 loops = 24 block passes; 8 blocks × 12 loops = 96.

## 2. Known causes of flat scaling, and how well each fits

**Looping adds depth, not storage.**
- **Shown:** for synthetic reasoning problems like addition, p-hop induction, and math problems, a k-layer transformer looped L times nearly matches the performance of a kL-layer non-looped model.
- **Shown:** looped language models end up with worse perplexity than iso-flop baseline, since perplexity depends strongly on number of parameters, and have a tendency to improve tasks that require reasoning a lot more than memorization tasks.
- **Shown:** Ouro's controlled experiments found the looped model's advantage stems not from increased knowledge capacity, but from superior knowledge manipulation capabilities.
- **Shown:** an iso-depth scaling study measured a recurrence exponent of 0.46, between r unique blocks of a non-looped model (full equivalence, φ=1) or to a single block run repeatedly with no capacity gain (φ=0).
- **Suggested fit:** the extra blocks may be adding more reasoning steps your task doesn't need, rather than the storage it does need.

**Dense shared layers scale poorly; capacity that differs per loop helps.**
- **Shown:** looped models do not scale as favorably as standard transformers with unique layers; Looped-MoE models scale better than the standard baseline while dense looped models do not.
- **Shown:** earlier work on Universal Transformers notes that layer-sharing comes with a practical limitation of parameter-compute ratio.
- **Shown:** adding loop-specific, low-rank adapters that facilitate layer specialization substantially improved recursive models.

**Depth beyond a threshold set by width is inefficient.**
- **Suggested (theory on a simplified model):** Levine et al. identify a "depth threshold" that is logarithmic in $d_x$, the network width: $L_{\textrm{th}}=\log_{3}(d_x)$, because stacking self-attention layers is so effective that it quickly saturates a capacity of the network width. log₃(256) ≈ 5, and both of your sizes are far past it.
- **Shown:** in Petty et al., deeper models generalize more compositionally than shallower models do, but the benefit of additional layers diminishes rapidly.
- **Shown:** the TRM paper (tiny recursive models) found that adding layers decreased generalization due to overfitting.
- **Shown:** models with higher recurrence count r prefer wider widths and fewer training tokens per parameter.
- **Counter-evidence (shown):** a 16-layer, 576-dim transformer solves harder problems (in reasoning length) than a 4-layer, 1920-dim one, despite the latter being twice as large, and MobileLLM found that depth is more important than width for small LLMs. Those were non-looped models of 4 to 42 layers. **Suggested:** your loop already supplies that much depth.

**Deep or looped stacks need re-tuned training settings.**
- **Shown:** deeper models suffer under SP/µP due to hyperparameter detuning and instability (SP is the standard parameterisation).
- **Shown:** looped training recipes can be unstable, suffering from residual explosion and loss spikes.
- **Shown:** truncated backpropagation through time weakens the power of loops due to inaccurate gradients.
- **Untested fit:** you kept the learning rate at 1e-3 while effective depth went from 24 to 96.

**The parts around the thinker may be the bottleneck.**
- **Shown (text-to-image):** with frozen text encoders, increasing the size of the language model in Imagen boosts both sample fidelity and image-text alignment much more than increasing the size of the image diffusion model.
- **Shown:** EmbeddingGemma was trained with a noise-contrastive estimation (NCE) loss with in-batch negatives applied after mean pooling P is then employed, averaging the token embeddings along the sequence axis. **Suggested:** so its per-token outputs, which your thinker reads, were never trained directly to keep exact characters and positions.
- **Shown:** a two layer transformer can copy strings of exponential length while GSSMs are fundamentally limited by their fixed-size latent state (GSSMs are state-space-style models with a fixed-size memory).
- **Shown:** in parallel (non-autoregressive) decoders, the conditional independence assumption prevents a model from properly capturing the highly multimodal distribution of target translations.
- **Untested but consistent:** your weak families (table lookup, if/otherwise rules, few-shot, sequences, passages) are exactly the copy-and-write-a-sequence tasks. The plain decoder wins there, and it attends directly to the input tokens and writes its output autoregressively.

**Exact match hides progress.**
- **Shown:** apparent jumps come from a metric that nonlinearly or discontinuously deforms per-token error rates, and secondarily by possessing too few test data.
- **Suggested:** the plain recipe's +15.8 (starting about 26 points lower, near 47%) and your +1.6 (starting at 73%) are not directly comparable.

## 3. What makes parameter scaling strong at small scale

- **Data must grow with parameters (shown).**
  - For compute-optimal training, for every doubling of model size the number of training tokens should also be doubled. A common reference point is 20 tokens per parameter.
  - Repeating data is fine at first: up to 4 epochs of repeated data yields negligible changes to loss compared to having unique data. However, with more repetition, the value of adding compute eventually decays to zero. A secondary summary reports that excess parameters decay faster than repeated data.
  - For looped models specifically, looping and data should be increased in tandem.
- **Learning rate and initialisation across sizes (shown).**
  - Under muP, the optimal learning rate is stable with width in µP (right) but far from so in standard parametrization.
  - For depth, CompleteP scales each residual branch as hℓ+1 = hℓ+ L−α Fℓ(hℓ), and only α = 1 enables depthwise HP transfer.
- **Loops versus parameters (shown).** accuracy on downstream tasks scale as logarithm of the effective depth. On small data, TRM found that using 2 layers (instead of 4 layers) maximized generalization.
- **Evaluation design (shown).** performance differences between these models are typically invisible on the IID data split, so held-out shifted rows like yours are the right test.

## 4. Gains on new template variants: size, data diversity or architecture?

- **Size, if training covers enough of the task space (shown):** simply scaling data and model size leads to compositional generalization, but only as long as the training distribution sufficiently covers the task space.
- **Data diversity (shown):**
  - Richer datasets provide more diverse examples so compositional understanding becomes more effective, and they also prevent ungeneralizable memorization of the examples due to reduced example repetition frequency.
  - For in-context learning there is a task diversity threshold for the emergence of ICL. This is directly relevant to your few-shot "find the rule" family.
- **Architecture (shown):**
  - Simple choices such as scaling of embeddings, early stopping, relative positional embedding, and Universal Transformer variants drastically improve systematic generalization.
  - On out-of-distribution data, transformers fail to systematically generalize for composition but succeed for comparison.
- **Suggested synthesis:** the most reliable fix for your structural-variant misses is training on more distinct variants. Extra size helps on top of that once coverage is broad.

## 5. Three single changes to test on one 16 GB GPU, ranked

**Step 0: measurement fixes (cheap; do these first).**
- Run 3 seeds per size.
- Report exact match on the rows that are not saturated, plus the average log-probability of the correct answer.
- Capacity probe: train both sizes on about 20k rows for many epochs. If the 10M model cannot fit them better than the 3.5M model, the limit is outside the thinker.

**1. Grow width instead of depth (untested).** Keep 2 blocks and 12 loops, and widen to about 450–512 to reach roughly 10M parameters. Scale the learning rate with muP and run a 3-point learning-rate sweep. Widening also enlarges the 44-latent workspace and the cross-attention channel; adding depth leaves both fixed.
- **Confirms it:** across 3 seeds, the wide 10M model beats the deep 10M model by at least 2 points on non-saturated rows, and its training loss is clearly lower.
- **Rules it out:** all three models land within about 1 sd of each other with equally flat training loss. Then the limit is in the input/output parts; go to test 2.

**2. The planned autoregressive writer, run as a scaling experiment (untested).** Give the writer copy/pointer attention into the embedder's token positions, and train it with the 3.5M and 10M thinkers.
- **Confirms it:** the five weak families close most of their gap to the plain decoder, and the size gain on non-saturated rows reaches at least 3 points.
- **Rules it out:** both sizes improve by the same amount. Then the writer fixes the level of the score but not how it grows with size.

**3. More structural variants, crossed with size (untested).** Keep the number of rows fixed but use 2–3× more distinct structural variants per family, with separate held-out variants, and use fresh web text instead of repeat passes.
- **Confirms it:** the gap between sizes on the "new structural variant" rows widens.
- **Rules it out:** both sizes gain equally.

**Runners-up:** per-loop capacity (unshared first and last blocks, per-loop adapters, or a mixture-of-experts feed-forward layer); CompleteP residual scaling; LoRA on the top embedder layers.

## 6. Rough recipe for growing 10M → 100M (suggested or untested)

- **Shape:**
  - Grow in steps of about 3× (10M → 30M → 100M) and put the new parameters mainly into width: 512 → 768 → 1024.
  - Use 2–4 shared blocks plus one unshared block before and one after the loop. Keeping the first and last layers unshared has better perplexity and more uniform improvements.
  - From your numbers, each added block costs about 1M parameters at width 256. That puts 100M at about 6 blocks of width 1024.
  - Sweep loop counts of 8, 12 and 16 once, at the small size.
- **Learning rate:** muP rules for width; CompleteP-style 1/L residual scaling for depth. Whether L should count loops is untested.
- **Data:** grow unique rows at least as fast as parameters and stay at about 4 passes or fewer. At 100M that means at least 10× today's unique data, mostly new synthetic variants and new web text.
- **Evaluation:** 3 seeds per size. Add harder variants so the saturated families stop hiding gains.

## Plain-language summary

When the thinker got bigger, it didn't even get better at its own practice questions, so the new parts weren't being used. Three things probably matter most:

- **We made it "taller" in a way that barely helps.** It already repeats its thinking 12 times, so extra layers mostly add more thinking steps it doesn't need. Making it "wider" gives it more room to hold information.
- **Its "eyes" and "pen" stayed small.** It reads through a frozen tool built to judge which texts mean similar things, not to copy exact words. It also writes all the characters of an answer at once, which is bad for copying from a table or a passage.
- **We need more and more varied practice questions,** especially new kinds of question patterns, as it grows.

Next steps: run each test 3 times, widen instead of deepen, try the new step-by-step writer, and add more varied questions. Then check whether each size step clearly helps.

## Sources

- Saunshi et al., looped transformers: https://arxiv.org/html/2502.17416v1 and https://arxiv.org/pdf/2502.17416
- Ouro (looped language models): https://arxiv.org/abs/2510.25741
- Iso-depth scaling laws for looped models: https://arxiv.org/html/2604.21106v1 and https://huggingface.co/papers/2604.21106
- Sparse layers in looped models: https://arxiv.org/abs/2605.09165
- MoEUT: https://arxiv.org/abs/2405.16039
- Relaxed recursive transformers: https://deepmind.google/research/publications/122290/
- TRM (tiny recursive models): https://arxiv.org/html/2510.04871v1
- Parcae: https://arxiv.org/abs/2604.12946
- Levine et al., depth vs. width: https://arxiv.org/abs/2006.12467v1
- Petty et al., depth and compositional generalization: https://arxiv.org/abs/2310.19956
- Physics of Language Models 2.1: https://arxiv.org/html/2407.20311v1
- MobileLLM: https://arxiv.org/html/2402.14905v2
- CompleteP: https://arxiv.org/html/2505.01618v1 and https://pehlevan.seas.harvard.edu/sites/g/files/omnuum6471/files/2025-11/Dey_etal_NeurIPS_2025.pdf
- muP (Tensor Programs V): https://openreview.net/pdf?id=Bx6qKuBM2AD
- Chinchilla: https://arxiv.org/abs/2203.15556
- Data-constrained scaling: https://arxiv.org/abs/2305.16264
- Secondary summary of data-constrained scaling: https://hunterheidenreich.com/notes/natural-language-processing/language-models/scaling-data-constrained-language-models/
- Emergent abilities as a metric effect: https://arxiv.org/pdf/2304.15004
- Non-autoregressive translation: https://arxiv.org/pdf/1711.02281
- Copying with fixed-size state: https://arxiv.org/abs/2402.01032
- Imagen: https://imagen.research.google/
- EmbeddingGemma: https://arxiv.org/pdf/2509.20354 and https://ritvik19.medium.com/papers-explained-465-embeddinggemma-076b2bc8b460
- Csordás et al., systematic generalization tricks: https://aclanthology.org/2021.emnlp-main.49/
- Data factors for compositional generalization: https://aclanthology.org/2023.emnlp-main.898/
- Scaling and compositional generalization: https://arxiv.org/abs/2507.07207
- Task diversity and in-context learning: https://arxiv.org/abs/2306.15063
- Grokked transformers: https://arxiv.org/abs/2405.15071