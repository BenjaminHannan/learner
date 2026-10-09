# Cheap READER alternatives for Premonition (literature + config check, 2026-10-04)

Labels: [shown] = a paper or a config file I fetched says it; [suggested] = reasoned from shown facts; [untested-guess] = my guess, no evidence.
Caveat: arXiv ids below are from memory; I could not resolve titles through the arXiv API in this sandbox. Check ids before citing. Configs/tokenizers were fetched directly from huggingface.co (so those are [shown]).

## 0. Where the current reader's parameters actually sit (fetched configs)
- LFM2.5-1.2B-Base: hidden 2048, 16 layers (10 conv + 6 full-attn), vocab 65536, tied embeddings, block_ff_dim 12288 which auto-adjusts to ~8192 (2/3 rule) [shown config; the 8192 is my arithmetic].
- Embedding = 65536 x 2048 = 134M params, about 11.5% of ~1.17B. Body ~1.04B, ~65M per layer (16 layers) [suggested: arithmetic from config].
- So vocab trimming saves little here (<=12%); layer truncation is the big lever.
- Other LFM2 sizes (configs fetched, all 16 layers, vocab 65536, same tokenizer family): LFM2-350M hidden 1024 (embed 67M of ~354M, 19%); LFM2-700M hidden 1536 (embed 101M of ~742M); LFM2-1.2B hidden 2048. [shown config; totals are the names + my arithmetic]
- Paper: "LFM2 Technical Report", Liquid AI, 2025, arXiv 2511.23404 [id from memory].

## 1. Smaller pretrained LMs / encoders as frozen readers
Params (total / embedding), from fetched configs unless noted:
| Reader | Total | Embed | Layers x hidden | Digits |
|---|---|---|---|---|
| LFM2-350M | ~0.35B | 67M | 16 x 1024 | groups of up to 3 [shown, regex \p{N}{1,3} in LFM2.5 tokenizer.json; LFM2 tokenizer assumed same family, untested] |
| LFM2-700M | ~0.7B | 101M | 16 x 1536 | same |
| SmolLM2-135M | 135M | 28M | 30 x 576 | individual digits [shown: pretokenizer Digits individual_digits=true] |
| SmolLM2-360M | 360M | 47M | 32 x 960 | individual digits [shown, same tokenizer] |
| Qwen3-0.6B | ~0.6B | 156M | 28 x 1024 | single digits [suggested: Qwen tokenizers are widely reported to split digits one by one; I did not fetch it] |
| Gemma-3-270M | 270M | ~170M (262k vocab x 640; from memory) | 18 x 640 | single digits [untested-guess from Gemma tokenizer lore] |
| DeBERTa-v3-small | ~44M body + 98M embed (128k vocab) | | 6 x 768 | SentencePiece, digits not systematically split |
| MiniLM-L6/L12 (384 wide) | 22M / 33M | | 6-12 x 384 | WordPiece, multi-digit chunks |
| ModernBERT-base / ettin | 149M / 17M-1B (ettin sizes 17M, 32M, 68M, 150M, 400M, 1B, from memory) | | | BPE; digit handling untested |
| T5-small / ByT5-small encoder | 60M / ~150M (ByT5 small enc is deeper) | | | ByT5 is bytes: every digit is its own token [shown by design] |

Citations: SmolLM2 "When Small is Mighty" Allal et al. 2025 arXiv 2502.02737 (reports 135M/360M/1.7B, trained on 2T-11T tokens) [shown]. Qwen3 Technical Report 2025 arXiv 2505.09388. Qwen2.5 Technical Report 2024 arXiv 2412.15115. Gemma 3 Technical Report 2025 arXiv 2503.19786. ModernBERT, Warner et al. 2024 arXiv 2412.13663. Seq2seq/encoder pair "ettin" (Weller et al. 2025, arXiv 2507.11412) trains matched encoder and decoder at equal sizes [shown by title; details from memory]. DeBERTaV3, He et al. 2021 arXiv 2111.09543. MiniLM, Wang et al. 2020 arXiv 2002.10957. ByT5, Xue et al. 2021 arXiv 2105.13626.

Speed [suggested]: forward cost is roughly proportional to non-embedding params x tokens. Against LFM2.5-1.2B body (~1.04B): SmolLM2-135M body ~107M (~10x faster by FLOPs, but 30 sequential layers so latency gain is smaller, maybe 4-6x on GPU at 160 tokens); SmolLM2-360M body ~313M (~3x); LFM2-350M body ~287M (~3.5x); Qwen3-0.6B body ~0.44B (~2.4x); MiniLM-L6 ~11M body (~90x) . Encoders also see the whole prompt bidirectionally, which a causal LM cannot [shown by architecture].
Strongest small-size numeric reading: [untested-guess] SmolLM2-360M or Qwen3-0.6B: both digit-split, both trained on math-heavy data (SmolLM2 paper reports GSM8K/MATH gains from FineMath, shown; Qwen3 trains on large synthetic math corpora, shown). LFM2 tokenizer's 3-digit groups mean a number like 1234 is "123"+"4" and alignment of place value shifts with length [suggested; known cause of arithmetic errors, see Singh & Strouse 2024 "Tokenization counts: the impact of tokenization on arithmetic in frontier LLMs", arXiv 2402.14903: right-to-left grouping and single digits beat left-to-right 3-digit groups, shown]. So the current reader itself may be disadvantaged on digits. Nogueira et al. 2021 "Investigating the limitations of transformers with simple arithmetic tasks" arXiv 2102.13019 shows digit/position representation matters for learning arithmetic [shown].
What is lost: world knowledge and paraphrase robustness shrink with size; hard-to-parse layouts (tables) are the first casualty [suggested]. A BERT-class encoder with WordPiece loses digit granularity unless you preprocess numbers (space-separate digits) [suggested].

## 2. Use only the first k layers of the big LM
- Skean et al. 2025 "Layer by Layer: Uncovering Hidden Representations in Language Models", arXiv 2502.02013: intermediate layers often beat the final layer for downstream embedding tasks across architectures, including SSMs [shown].
- Gromov et al. 2024 "The Unreasonable Ineffectiveness of the Deeper Layers", arXiv 2403.17887: up to ~half of deep layers can be dropped with small QA loss then a little healing (QLoRA); knowledge-heavy tasks degrade sooner [shown]. Note this removes layers but keeps the last, whereas truncation keeps the first k (a different regime).
- Men et al. 2024 "ShortGPT: Layers in LLMs are more redundant than expected", arXiv 2403.03853: deep layers show high cosine similarity input-to-output, removable by Block Influence [shown].
- nostalgebraist 2020 logit lens (blog) and Belrose et al. 2023 "Eliciting Latent Predictions from Transformers with the Tuned Lens", arXiv 2303.08112: early/mid residual streams already encode the content, final layers mostly refine next-token prediction [shown].
- Cost of 4 of 16 layers of LFM2.5 [suggested, arithmetic]: ~4 x 65M = 260M body + 134M embedding = ~0.39B counted, ~4x less compute. Keeping 6 of 16: ~0.52B. Trimming vocab as well (section 5) could bring 4-layer to ~0.28B.
- Risks [suggested]: LFM2's layers are conv-heavy (layers 0,1,3,4 are conv; first attention at layer 2). A 4-layer prefix has only 1 attention layer (layer 2) so long-range binding of "which number goes with which item" may be poor; k=6-8 includes 3-4 attention layers [from layer_types in config, shown]. Because the core reads hidden states, a small learned adapter or brief LoRA on the truncated reader may be needed to repair the mismatch [untested-guess]. Best k is empirical: the papers show mid-depth peaks, not a specific k for numbers [shown/untested].
- Cheap experiment [suggested]: cache layer-k hidden states for k in {4,6,8,12,16} and train the same core on each; this is one change at a time with a clean axis.

## 3. Distill the big reader into a small student
- DistilBERT, Sanh et al. 2019, arXiv 1910.01108: 40% smaller, 60% faster, keeps 97% GLUE; student initialised from every other teacher layer; loss = MLM + KD + cosine on hidden states [shown].
- TinyBERT, Jiao et al. 2019, arXiv 1909.10351: layer-wise distillation of embeddings, hidden states and attention maps, ~7.5x smaller, 9.4x faster, 96% of BERT-base on GLUE; uses large augmented corpus [shown].
- MiniLM, Wang et al. 2020, arXiv 2002.10957: distil only last-layer self-attention distributions plus value relations; allows differing student width [shown].
- Sheared-LLaMA, Xia et al. 2023, arXiv 2310.06694: structured pruning of Llama-2-7B to 1.3B/2.7B then continue-pretrain on ~50B tokens, beating same-size models trained from scratch on far more tokens [shown].
- Minitron, "Compact Language Models via Pruning and Knowledge Distillation", Muralidharan et al. 2024, arXiv 2407.14679: prune width/depth then retrain with KD using <3% of the original pretraining data (about 40x fewer tokens), 1.8x-ish compute saving; uses logit + intermediate-state distillation [shown].
- Hidden-state (feature) distillation: TinyBERT and DistilBERT above use it [shown]. A width-mismatched student needs a linear projection [shown in TinyBERT]. For Premonition the target is not logits at all but the reader's layer-k states, so a regression/cosine loss on those is natural [suggested].
- Data/compute scale [shown]: BERT-class students used full Wikipedia+Books scale (billions of tokens); Minitron/Sheared used ~1-50B tokens. Our domain is narrow, so far fewer may suffice, e.g. 10M-100M tokens of generated word problems/layouts [untested-guess]. Risk: the student only matches the teacher on the distribution it was distilled on; wording out of distribution regresses [suggested].

## 4. Tiny reader trained from scratch on a narrow domain
- Eldan & Li 2023, "TinyStories", arXiv 2305.07759: models of 1M-33M params, even 1-layer or small hidden, produce fluent coherent stories and show some reasoning/instruction following when the vocabulary and domain are restricted to what a 3-4 year-old would understand [shown]. This supports narrow-domain small LMs; it does NOT show they handle unseen wording [shown by scope].
- Related: Gunasekar et al. 2023 "Textbooks Are All You Need" (phi-1, 1.3B, arXiv 2306.11644): data quality substitutes for scale in a narrow domain (code) [shown].
- Byte/char encoders: CANINE, Clark et al. 2021, arXiv 2103.06874 (tokenization-free, 127M, downsampling) ; ByT5, Xue et al. 2021, arXiv 2105.13626 (byte-level T5; robust to noise/spelling, slower since sequences are ~4-5x longer) [shown]. For <=160 tokens the byte length is ~600-800, which is cheap for a tiny model but removes a free per-digit tokenization benefit... actually it gives one token per digit, which is good for arithmetic [suggested].
- Risks for unseen wording [suggested]: synthetic templates -> reader latches onto template cues; mitigation is paraphrase augmentation via a big LM and held-out wording splits. This is the option with the biggest "loses variety of English" risk and also the cheapest. A hybrid is more plausible: initialise a tiny reader from SmolLM2-135M or MiniLM (pretrained English) and fine-tune/distil [untested-guess].

## 5. Vocabulary trimming and quantization
- Vocab trimming: Abdaoui et al. 2020 "Load What You Need: Smaller Versions of Multilingual BERT", arXiv 2010.05609: dropping unused vocabulary rows cuts parameters (mBERT 134M -> ~ 40-60% smaller) with little accuracy loss on the target language [shown, numbers from memory]. Implementation: collect token ids that appear in the training/eval corpus (tens of thousands of words of English + digits), keep those rows, remap ids; LM head not needed for a reader [suggested].
- For LFM2.5-1.2B: the whole embedding is 134M. Keeping 8k used ids -> 17M, saving ~117M (10%) [suggested arithmetic]. For Qwen3-0.6B (156M embed of ~0.6B) and Gemma-3-270M (~170M of 270M) trimming is a large share, making Gemma-3-270M effectively a ~100M body, with ~ +10M after trimming to 8-16k ids [suggested; Gemma numbers from memory]. Caveat: "unseen wording" tokens would map to unknown, so keep a generous set (32k) or fallback byte/char tokens [suggested].
- Quantization: LLM.int8(), Dettmers et al. 2022, arXiv 2208.07339; GPTQ, Frantar et al. 2022, arXiv 2210.17323; AWQ, Lin et al. 2023, arXiv 2306.00978: 8-bit and 4-bit weight quantization keep accuracy for large LMs with ~2-4x memory cut [shown]; small models (<1B) are more sensitive to 4-bit than large ones [suggested, widely reported, not verified here]. It lowers memory/bandwidth but not the parameter count, so under the project's rule (size counts parameters) it likely does not count as shrinking unless the owner defines size in bytes [suggested]. Because the reader is frozen and only features are consumed, int8 noise might even be absorbed by the trained core [untested-guess].

## 6. Digit tokenization summary
- SmolLM2: individual digits [shown, tokenizer.json]. Qwen: single digits [suggested]. Llama-2/Mistral also single digits [suggested]. Gemma: single digits [untested-guess].
- LFM2/LFM2.5: up to 3 digits per token, left-to-right [shown, regex \p{N}{1,3}]. This is the same left-to-right chunking that Singh & Strouse found hurts arithmetic [shown, paper]. Mixed with the frozen-reader design, Premonition's core must undo this chunking [suggested]. Switching reader to a single-digit tokenizer, or splitting digits with spaces before tokenizing, may help numbers regardless of size [untested-guess].
- Note a digit-per-token tokenizer lengthens numbers; fine at <=160 tokens.

## 7. Ranking for Premonition (at-whole-system size) [suggested unless noted]
1. Truncate LFM2.5 to k=6-8 layers + trim vocab: no new tokenizer, minimal engineering, ~0.3-0.5B counted. Digits remain 3-chunked.
2. SmolLM2-135M (0.135B, individual digits, 28M embedding trimmed to ~10M) frozen or lightly fine-tuned: likely the best size/quality point if the goal is <=0.15B. Also try its first ~15-20 layers (mid-layer features per Skean).
3. SmolLM2-360M / LFM2-350M as middle ground (~0.35B).
4. Distil layer-k states of LFM2.5 into a 20-60M student, or MiniLM-L6/ettin-68M initialised student: smallest, riskiest for wording [untested].
5. Scratch tiny reader: only with paraphrase augmentation.
Suggested single first experiment with fixed pass marks written before running: swap reader only, keep core unchanged, compare layer-truncated LFM (k=8) vs SmolLM2-135M vs SmolLM2-360M on the same held-out-wording split; pass mark = within X points of the current 1.2B reader on accuracy (choose X in advance), fail = drops more than that on the paraphrase split while not failing on the template split (indicating wording fragility).
