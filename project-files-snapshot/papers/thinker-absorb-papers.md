# Absorbing more context per position: reader options for a small char-level model (Oct 7, 2026)

Labels: **paper** = stated in the abstract page I opened this session (abstract-level only; no full PDFs, so no per-model param tables); **inference** = my reasoning about our model; **untested** = guess.
Skipped as already covered in gemma-reader-papers.md: BLT, ByT5, CharBERT, LLaVA/Q-Former, ColBERT, numeracy papers.
Not found: any paper that explains why a local +-k window helps cipher/lookup tasks. Closest evidence is Zoology and H3 below; the rest is inference.

## Papers (all opened)

1. **CANINE** (Clark et al., 2021) https://arxiv.org/abs/2103.06874
   - Is: char-level encoder that downsamples the character sequence, then runs a deep transformer on the shorter sequence. (paper)
   - Evidence: beats mBERT on TyDi QA by 2.8 F1 with 28% fewer params. (paper) Not small-scale. Downsample is a strided local conv (from memory, inference).
   - Plug in: keep the +-4 conv, add stride-4 pooled "word-ish" states with global self-attention, then upsample back so every letter position gets a context-rich vector. Cost: a few small transformer layers on L/4 positions, trivial at L=64. (inference)

2. **Charformer / GBST** (Tay et al., 2021) https://arxiv.org/abs/2106.12672
   - Is: learned soft subword pooling: score candidate blocks of 1..M chars at each position, mix by softmax. (paper)
   - Evidence: beats byte baselines, on par with subword models on GLUE, noisy text; 28-100% faster than byte/subword transformers. (paper)
   - Plug in: replaces the fixed +-4 window with a learned mix of block sizes 1,2,3,4,... per position; cheap (a linear scorer plus pooling). Closest direct answer to "dislike fixed window". Risk: soft pooling blurs exact letters, so keep the raw letter channel alongside. (inference)

3. **MegaByte** (Yu et al., 2023) https://arxiv.org/abs/2305.07185
   - Is: patches of bytes; local model inside a patch, global model across patch vectors. (paper)
   - Evidence: byte models competitive with subword on long context. (paper) Aimed at 1M-byte sequences, so overkill at 64 chars. (inference)
   - Plug in: the patch+local+global shape is the same as CANINE; only worth it if inputs grow long.

4. **Perceiver** (Jaegle et al., 2021) https://arxiv.org/abs/2103.03206
   - Is: a small set of latent vectors cross-attends to the whole input repeatedly, a tight bottleneck. (paper)
   - Evidence: matches ResNet-50/ViT on ImageNet from raw pixels, many modalities. (paper)
   - Plug in: our thinker already cross-attends over all reader outputs, so it is already Perceiver-shaped on the output side. A Perceiver reader would add a bottleneck we do not want, since copying letters needs per-position detail. (inference; same lesson as Q-Former in the earlier file)

5. **Set Transformer** (Lee et al., 2019) https://arxiv.org/abs/1810.00825
   - Is: induced set attention blocks, inducing points make self-attention linear in set size. (paper)
   - Evidence: multi-instance, 3D shape tasks. (paper)
   - Plug in: not useful at L<=64 where full self-attention is cheap. Skip. (inference)

6. **Recurrent Memory Transformer** (Bulatov et al., 2022) https://arxiv.org/abs/2207.06881
   - Is: special memory tokens added to the sequence; read/written each segment and passed along. (paper)
   - Evidence: on par with Transformer-XL at small memory, better for longer-range tasks; authors name algorithmic tasks as a target. (paper)
   - Plug in: add 4-8 learned memory tokens to the reader's self-attention as scratch space. Cheap (a few vectors). Segment recurrence is not needed at 64 chars. (inference)

7. **Mamba-family: MambaByte** (Wang et al., 2024) https://arxiv.org/abs/2401.13660
   - Is: selective SSM on raw bytes, fixed-size state. (paper)
   - Evidence: competitive with or better than subword transformers on LM; noise robust. (paper)
   - Plug in: bidirectional SSM layer in the reader gives O(L) global context. But a pure SSM is weak at recall (see 9), so pair with attention. At L=64 SSM has no speed advantage. (inference)

8. **Hyena** (Poli et al., 2023) https://arxiv.org/abs/2302.10866
   - Is: long implicit convolutions plus data-controlled gating instead of attention. (paper)
   - Evidence: large gains on recall/reasoning synthetics over other SSM/implicit methods, matching attention; Transformer quality at 20% less compute at 2K. (paper)
   - Plug in: a global-kernel conv (kernel = whole input) is the most literal "unfixed window" conv. Cheap in params. Efficiency advantage only appears at thousands of tokens. (inference)

9. **Zoology / MQAR** (Arora et al., 2023) https://arxiv.org/abs/2312.04927
   - Is: diagnoses why gated-conv models trail attention: associative recall. (paper)
   - Evidence: about 82% of the gap is recall; a 70M attention model beats a 1.4B gated-conv model on recall; input-dependent sparse-attention hybrids close 97.4% of the gap. (paper)
   - Plug in: lookup tasks are recall tasks, so a conv-only reader, however wide, should be the weak choice; include real self-attention. Most relevant paper for us. (inference)

10. **Hungry Hungry Hippos (H3)** (Fu et al., 2022) https://arxiv.org/abs/2212.14052
    - Is: SSM layer fixing two weaknesses: recalling earlier tokens and comparing tokens across the sequence, via local-context (shift) design plus multiplicative interaction. (paper)
    - Evidence: within 0.4 PPL of Transformers; a 125M hybrid with attention beats Transformers by 1.0 PPL. (paper)
    - Plug in: supports the best answer to "why local windows help": a local-context step before global mixing makes token comparison/recall work. Local conv then attention is the proven order. (inference, extension of paper claim)

11. **Conformer** (Gulati et al., 2020) https://arxiv.org/abs/2005.08100
    - Is: conv module plus self-attention in each block; attention for global content interaction, conv for local features. (paper)
    - Evidence: 2.1/4.3 WER LibriSpeech, a 10M-param version gets 2.7/6.3. (paper) Speech, not text.
    - Plug in: a ready template for the reader block: [self-attn, depthwise conv (kernel 9 = our +-4), FFN]. Params about 12*d^2 per block, so d=128, 3 blocks is under 1M. (inference)

## Why local windows help cipher/lookup (inference, no direct paper)
Ciphers and lookups need exact letter-to-letter comparison and neighbor structure (adjacent digits form a number, letter shifts). A local conv makes every position carry its neighbors, so later attention matches on n-gram identity rather than single letters. H3 and Zoology support the mechanism (local mixing then recall via attention); no paper tests it on ciphers. Untested: whether widening the window hurts or helps.

## Ranked ideas (15 lines)
1. Conformer-style reader: keep the +-4 conv, add global self-attention blocks (2-3, d~128). Papers 11, 9, 10. Cheapest, lowest risk.
2. Fix the window not by removing local conv but by putting attention after it (H3 order). Paper 10.
3. Learned multi-scale pooling (GBST) added as a parallel channel next to raw letters. Paper 2.
4. CANINE-style stride-4 downsample, global attention on the short sequence, upsample and add to letters. Paper 1.
5. 4-8 memory/scratch tokens in the reader's attention. Paper 6.
6. Global-kernel long conv (Hyena) as a cheap global mixer; only if attention proves too costly (it will not at L=64). Paper 8.
7. Bidirectional SSM (Mamba-style) reader; paired with attention. Paper 7.
8. MegaByte patching: only if inputs get long. Paper 3.
9. Perceiver-style latent bottleneck in the reader: avoid; copying letters needs per-position detail. Paper 4.
10. Set Transformer inducing points: not useful at this length. Paper 5.
Pre-registration suggestion (untested): change one thing, idea 1, with same params +-10%; pass = lookup and cipher held-out no worse than B2 and at least one longer-context task better; wrong if adding attention drops a cipher task over 2 points.
Not covered: retrieval and pretrained small encoders with char adapters (the earlier file covers the pretrained-encoder case; I did not search retrieval).
