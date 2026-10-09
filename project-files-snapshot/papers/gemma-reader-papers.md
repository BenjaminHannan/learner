# Why a frozen EmbeddingGemma reader lost to B2, and what to test (Oct 6-7, 2026)

Labels: **shown** = I read the abstract or page and the claim is there; **suggested** = my reading of how it applies to us; **untested** = a guess.
Search was done from abstracts and search snippets. I did not read full PDFs, so exact numbers inside papers are not quoted. Our own numbers come from `custom-io/EG2-and-loops-2026-10-06.md` and the EGW result in project memory (pooled-5 -3.39 and -5.30 vs same-box B2; chain-5 98.3 and 97.6).

## For Ben (plain version)

**Why can a 270M model made by Google lose to our 3M one?**
- "Bigger and pretrained" only helps if the pretraining taught the thing we need. EmbeddingGemma was trained to put sentences with the *same meaning* near each other, so "2%" and "20%" can look almost the same to it. Our tasks are the opposite: one wrong digit or letter is a wrong answer.
- The 270M is also mostly a lookup table of word pieces (about 200M of the roughly 300M is the table, about 100M is the thinking layers; shown in the Google write-up). So it is not 100 times more "brain" than B2.
- B2 was built for these exact tasks: it sees every letter, and a calculator does the digits. EGW threw away B2's letter reader and gave the thinker Gemma's word-piece view instead. Made-up words like `sune` get chopped into odd pieces, and the letters are no longer visible.
- This is a known pattern. Papers find that sentence-embedding models are bad at exact numbers, and that models that see characters or bytes beat word-piece models on spelling-type tasks.

**So can Gemma still win?** Probably yes, but as a helper next to B2's letter reader, not a replacement. Gemma supplies meaning (what the sentence is about, which words go together). B2's letters supply exactness. That is the same shape as how Minecraft agents use pretrained encoders: the pretrained part gives a rich summary, and a small trained policy does the exact acting.

## Top 3 fixes (one change at a time, marks fixed before any run)

1. **Probe first (CPU, no training).** Freeze EmbeddingGemma and fit a tiny linear probe on its per-token states: "which digit is this?", "which letter is at this spot?", "is this the same word as an earlier one?", for the last layer and a middle layer. Shown-wrong mark (fixed in advance): last-layer digit/letter probe accuracy below B2's own letter embedding on the same rows. If the middle layer is clearly better, use it. This costs minutes and tells us whether the information is even there. (Papers 1, 2, 3, 12.)
2. **Hybrid input: keep B2's letter reader and add Gemma, starting at zero (EGE).** This is the byte-plus-token idea. It is already built and queued in q38; run it before any more Gemma-only work. Mark: pooled-5 at least +1 on both seeds vs same-box B2, chain-5 at least 99, nothing drops over 2. It cannot be much worse than B2 by construction (starts identical). (Papers 4, 5, 6.)
3. **Fix the junction: scale, layer, learning rate.** Put a LayerNorm and a small learned gate in front of Gemma's states, take a middle layer if probe 1 says so, and train the adapter at a higher rate than the thinker (or train the adapter alone first, then everything: LP-FT). EGW had no adapter, so Gemma's state size and scale went straight into a thinker that was learning from scratch. (Papers 8, 9, 10, 11.)

If all three miss, the next idea is partial unfreezing (last 2 Gemma layers or LoRA), then Gemma only for the "meaning" tasks and B2 for digit tasks. Untested.

## Papers

### A. Numbers and characters in word-piece models

1. **Revealing the Numeracy Gap: An Empirical Investigation of Text Embedding Models** (2025, EACL Findings 2026). https://arxiv.org/abs/2509.05691
   - Finding (shown): 13 widely used text embedding models generally struggle to capture numerical detail, e.g. "grew by 2%" vs "20%" should embed differently and often does not. Embedding benchmarks do not test this.
   - Suggests (suggested): this is the most direct explanation of EGW. Test: probe 1 above, plus a sanity pair test "same sentence, one digit changed" on EmbeddingGemma's token states.

2. **Do NLP Models Know Numbers? Probing Numeracy in Embeddings** (Wallace et al., 2019). https://arxiv.org/abs/1909.07940
   - Finding (shown): GloVe/word2vec encode magnitude up to about 1,000; character-level embeddings (ELMo) are more precise; BERT's word pieces are less exact.
   - Suggests (suggested): character-aware inputs carry number information better than word pieces. Keep B2's letter reader (fix 2).

3. **Value-Aware Numerical Representations for Transformer Language Models** (2026). https://arxiv.org/abs/2601.09706
   - Finding (shown, from search snippet): standard subword tokenization is ill-suited to numerals, whose meaning depends on digit identity and place value; the paper proposes value-aware number representations.
   - Suggests (untested): we already hand-split numbers and run an exact executor in B2, so give EG a number side-channel too (feed the parsed value, not Gemma's pieces).

3b. **A Triadic Suffix Tokenization Scheme for Numerical Reasoning** (2026). https://arxiv.org/abs/2604.11582 and **Are Non-BPE Tokenizers Ready to Improve LLM Numeracy?** (ICML 2026). https://icml.cc/virtual/2026/82628
   - Finding (shown, snippets): how numbers are tokenized changes arithmetic accuracy; single-digit tokenization is what PaLM, early Llama and Qwen use.
   - Suggests (suggested): before blaming Gemma, check how its tokenizer splits our digit strings and made-up words (untested: I did not run the tokenizer). If digits come out one by one, the loss is the embedding's training goal, not the split.

4. **Byte Latent Transformer: Patches Scale Better Than Tokens** (Meta, 2024, ACL 2025). https://aclanthology.org/2025.acl-long.453/
   - Finding (shown): byte-level model matches token-based Llama 3 at scale and is better on noisy input and character-level understanding.
   - Suggests (suggested): supports "letters plus a coarser summary" as the input. Our hybrid = letters (B2) + Gemma's word-piece summary.

5. **ByT5: Towards a token-free future with pre-trained byte-to-byte models** (2021). https://arxiv.org/abs/2105.13626
   - Finding (not re-read this session; from memory, check before citing): byte-level models are more robust to noise and do better on spelling- and pronunciation-sensitive tasks than word-piece models of the same size.
   - Suggests (untested): same as paper 4.

6. **CharBERT: Character-aware Pre-trained Language Model** (2020). https://arxiv.org/abs/2011.01513
   - Finding (not re-read; from memory): adds a character channel next to word pieces and fuses the two, improving robustness to misspellings.
   - Suggests (suggested): this is almost exactly EGE: character channel + pretrained word-piece channel, fused. Use their fusion as a second design if plain addition is weak.

### B. Putting a frozen encoder in front of a reasoner

7. **Visual Instruction Tuning (LLaVA)** (2023). https://arxiv.org/abs/2304.08485 and **BLIP-2** (2023). https://arxiv.org/abs/2301.12597
   - Finding (shown, from a survey snippet): LLaVA's two-layer MLP applied per token beat BLIP-2's Q-Former as the connector, because a query bottleneck loses information; Q-Former is 188M by itself.
   - Suggests (suggested): our EGM (2-layer adapter) is LLaVA-style and is the right adapter shape; do NOT add a resampler, since we need position-by-position information to copy letters. Keep it per token.

8. **Fine-Tuning can Distort Pretrained Features and Underperform Out-of-Distribution** (Kumar et al., 2022). https://arxiv.org/abs/2202.10054
   - Finding (shown): full fine-tuning gains about 2% in-distribution but loses about 7% out of distribution against linear probing; LP-FT (fit the new head first, then fine-tune all) is about 10% better out of distribution than full fine-tuning.
   - Suggests (suggested): fix 3's ordering: train the adapter alone first, then release everything. Relevant because our unseen-kinds splits are exactly the out-of-distribution part.

9. **LoRA+: Efficient Low Rank Adaptation of Large Models** (2024). https://arxiv.org/abs/2402.12354
   - Finding (shown, from snippet): giving the two LoRA matrices the same learning rate does not allow efficient feature learning; a well-chosen ratio between them fixes it. Related snippets say adapter and head often do best at different learning rates.
   - Suggests (untested): try adapter lr at 3x to 10x the thinker's lr, one value, pre-registered.

10. **Efficient Reinforcement Learning Through Adaptively Pretrained Visual Encoder** (2025). https://arxiv.org/abs/2502.05555
   - Finding (shown, from snippet): freezing early encoder layers and training the last one preserves generalization; pixel-level reconstruction matters even with strong frozen features.
   - Suggests (untested): if probing says the last Gemma layer is the bad one, unfreeze only the last 1-2 layers.

### C. Using an embedding model token by token

11. **ColBERT** (2020) https://arxiv.org/abs/2004.12832 and **ColBERTv2** (2021) https://arxiv.org/abs/2112.01488
   - Finding (shown): per-token vectors from an encoder (kept, not pooled) carry fine-grained information and can be matched token to token, which a single pooled vector loses.
   - Suggests (suggested): our per-token use (not the pooled vector) is the right idea. ColBERT also adds a small linear projection down to 128 dims, a hint that a narrow bottleneck per token is fine.

12. **LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders** (2024). https://arxiv.org/abs/2404.05961
   - Finding (shown): turning a decoder into an encoder takes bidirectional attention, masked next-token training, and contrastive training; token-level hidden states are pooled for sentence use.
   - Suggests (untested): embedding models are tuned at the end for the pooled vector (contrastive), which may wipe out token-level exactness in the *last* layer. Probe a middle layer too (fix 1).

13. **EmbeddingGemma: Powerful and Lightweight Text Representations** (Google, 2025). https://arxiv.org/abs/2509.20354 and https://developers.googleblog.com/gemma-explained-embeddinggemma-architecture-and-recipe/
   - Finding (shown): about 300M total, trained by distillation plus a spread-out regularizer, mean-pooled to one 768-number vector; the Google write-up lists about 100M transformer and about 200M embedding-table parameters.
   - Suggests (suggested): it was optimized for meaning-similarity retrieval (MTEB), not exact tokens. Using it token by token is our choice, not what it was tuned for.

### D. Pretrained encoders in Minecraft agents (the long-term path)

14. **VPT: Video PreTraining** (OpenAI, 2022). https://arxiv.org/abs/2206.11795; **MineDojo / MineCLIP** (2022). https://arxiv.org/abs/2206.08853; **STEVE-1** (2023). https://arxiv.org/abs/2306.00937
   - Finding (shown for STEVE-1): STEVE-1 fine-tunes the VPT policy to follow commands in the space of a **frozen MineCLIP encoder**, and trains a small prior that maps text to that space. MineCLIP is trained on YouTube videos with subtitles.
   - Suggests (suggested): the working recipe is a frozen pretrained encoder giving a *summary of meaning* (goal and scene), with a trained policy doing the exact control. That matches "Gemma for meaning, B2-style exact parts for precision", not "Gemma replaces the exact parts".

15. **GROOT** (2023) https://arxiv.org/abs/2310.08235; **JARVIS-1** (2023) https://arxiv.org/abs/2311.05997; **OmniJARVIS** (NeurIPS 2024) https://proceedings.neurips.cc/paper_files/paper/2024/hash/85f1225db986e629289f402c46eff1a4-Abstract.html; **Optimus-1** (NeurIPS 2024) https://arxiv.org/abs/2408.03615; **Optimus-2** (CVPR 2025) https://arxiv.org/abs/2502.19902
   - Finding (shown, snippets): STEVE-1's goal space (one MineCLIP vector) cannot solve long process-oriented tasks, so JARVIS-1 and Optimus put a language model on top for planning and memory and keep a low-level policy for control. Optimus-2 keeps a separate behavior encoder for the observation-action history.
   - Suggests (suggested): a single pooled embedding as the goal is too weak even in Minecraft; the successful agents keep a token- or step-level history plus a planner. Support for using Gemma per-token, with a planner (our thinker) on top.

## What I could not settle
- I did not run the Gemma tokenizer on our rows, so "digits split one by one" is untested here.
- I did not check which Gemma layer EGW used. The probe in fix 1 should print it.
- I did not read full texts, so exact accuracies inside these papers are not quoted.
