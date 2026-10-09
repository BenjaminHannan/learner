# Cheaper reader and talker: Arm B report (Opus lead + Sonnet helpers)

Written 2026-10-04, 3:08 PM ET. Supporting files are in `reader-talker-compare/armB/`: code-map, lit-reader, lit-talker, lit-efficiency, lit-small-reasoners, citation-check and speed-probe. Labels: **shown** means measured here or reported by a paper, **suggested** means reasoned but not measured, **untested** means a guess.

## The short answer
1. **Replace the talker first, not the reader.** Today the frozen 1.2B LM runs a second time just to say a 1-4 word answer. In the "allptr" exit it also gets every raw prompt word fed back in. A ~2M copy-and-gate talker (pointer-generator style) does the same job and removes the second LM pass. It also settles the most important open question: is the core doing the reasoning, or is the LM re-reading the question and answering by itself?
2. **Then shrink the reader by cutting the LM to its first 6-8 of 16 layers.** That is 2-2.8x faster (measured) and cuts the counted reader from 1.17B to 0.52-0.66B. The papers say middle layers usually read as well as the last one.
3. Smaller ready-made models (LFM2-350M, SmolLM2) are a fallback. A distilled or from-scratch tiny reader is the long-term goal, but it is the riskiest.

## What the current system actually does (shown, code-map.md)
- **Reader.** LM pass 1 has no gradient. It takes the **last-layer** 2048-wide state for each prompt token, then a 78k-param per-token MLP squeezes it to 256 wide. The reader has no attention of its own, so all context comes from the LM.
- **Core.** 9.0M params, 4 loops.
- **Talker.** LM pass 2 runs over the full LM with gradients flowing through it. Its input is a learned prefix (8 pooled vectors + 8 pointer vectors), plus, in allptr, **all prompt-token embeddings**, then BOS and the answer. The answer is read off the LM's own 65k-vocab head. Decoding is greedy, up to 12 steps, with no KV cache. In the arithmetic recipe (PR #33) the answer is a single token.
- So the LM runs once to read and again, once per answer token, to talk. Of the 1.18B total, 99.2% is borrowed.
- **A warning about attribution (suggested).** In allptr the talker LM sees the whole question again, so it could answer without the core. Evidence both ways. For: in English round 6 the second unseen-kinds set tied the bare LM (78.2 vs 77.6). Against: zeroing the core's 8 pooled vectors at test drops allptr to 0.0% (RESULTS-R4, RESULTS-R2), but the earlier rounds call that a crude lesion, since an all-zero prefix may just throw the LM off; a shuffled-core lesion was never run. Any cheaper talker has to answer through the core, which makes it a better test of Ben's design ("talker translates the core's final state into words").

## Speed facts (shown, speed-probe.md, one 5090, bf16, hidden states only, ~$0.15)
| reader | counted params | ms/forward, batch 1, 67 tok | batch 64, 160 tok | speedup at batch 64 |
|---|---|---|---|---|
| LFM2.5-1.2B, all 16 layers | 1170M | 4.1 | 138 | 1.0x |
| first 10 layers | 787M | 2.3 | 87 | 1.6x |
| first 8 layers | 659M | 1.9 | 70 | 2.0x |
| first 6 layers | 524M | 1.5 | 52 | 2.6x |
| first 4 layers | 396M | 1.1 | 35 | 4.0x |
| LFM2-350M | 354M | 3.9 | 44 | 3.1x |
| LFM2-700M | 742M | 3.5 | 88 | 1.6x |
| SmolLM2-135M (30 layers) | 135M | 6.1 | 26 | 5.3x |
| SmolLM2-360M (32 layers) | 362M | 6.5 | 54 | 2.5x |
| Qwen3-0.6B (28 layers) | ~600M | 7.3 | 91 | 1.5x |

- At batch 1, time depends on **layer count, not size**. The 30-layer SmolLM2 models are *slower* than the 16-layer 1.2B, so truncation is the only reader change that helps speed at batch 1.
- The earlier 52 ms per question at batch 1 (speed-5090 note) is mostly **not** LM time. One bf16 LM pass takes about 4 ms. The rest comes from fp32 weights (the runners load the LM in fp32), the Python core loop and launch overhead (suggested). Cheap speed-only fixes (bf16, logits_to_keep, CUDA graphs) come before any architecture change, but they do not reduce counted size. torch.compile could not be tested because the image had no compiler.
- Embedding table: 65,536 x 2048 = 134M. Trimming the vocab therefore saves at most about 11%.

## Ranked shortlist
| # | Idea | Counted size of reader+talker | Speed vs today | What it would lose | Literature |
|---|---|---|---|---|---|
| 1 | **Copy-and-gate talker.** A pointer over prompt positions (span start/end), a small tied vocab head (yes/no, digits, a few thousand common words) and a 3-way gate (copy / word / calculator). Fixed answer slots plus a stop class; no LM pass 2. | ~1.17B + ~2M (the reader is unchanged this step; the talker shrinks from 1.17B to 2M) | Removes the second LM pass and every per-token decode pass: about 2x at batch 64, more for multi-word answers (suggested) | Free-form wording the prompt does not contain. Answers that are not a contiguous span. Any help the LM gives today by re-reading the question, which is exactly what we want to measure. | Pointer Networks 1506.03134; CopyNet 1603.06393; Pointer Sentinel 1609.07843; pointer-generator 1704.04368; BERT span heads 1810.04805; DROP/NAQANet span+arithmetic heads 1903.00161 |
| 2 | **Truncated reader.** Read LFM2.5 layer k (k = 6-8) and never run layers k+1 to 16. | 0.52-0.66B (with #1) | 2-2.8x (shown above) | Deeper semantics. At k=6 only 2 of the 6 attention layers remain (attention sits at layers 2, 5, 8, 10, 12, 14). Hard paraphrases may suffer. | Skean et al. 2502.02013 (middle layers beat the last on 32 embedding tasks); Gromov et al. 2403.17887; ShortGPT 2403.03853; Tuned Lens 2303.08112 |
| 3 | **Smaller ready-made reader.** LFM2-350M is first choice (16 layers, same tokenizer, 3x faster at batch). SmolLM2-135M/360M splits every digit but is slow at batch 1. | 0.14-0.36B | 3-5x at batch, ~1x or slower at batch 1 | General reading quality: LFM2-350M scores 30 vs 58 GSM8K for the 1.2B (model cards). Bigger risk on new wording. | LFM2 tech report 2511.23404; SmolLM2 2502.02737 |
| 4 | **Distilled student reader** (20-60M). Train it to match LFM layer-k states on lots of generated in-domain text, with a hidden-state loss and a linear projection. | ~0.03-0.06B | 20x+ | Matches the teacher only on the text it was distilled on. Paraphrase robustness is the usual casualty. | TinyBERT 1909.10351; MiniLM 2002.10957; DistilBERT 1910.01108; Minitron 2407.14679 |
| 5 | **From-scratch tiny reader + talker** (~33M, already sketched in design/v3/24). | ~0.03B | 30x+ | Language has to be learned from scratch, which conflicts with learning from few examples. Small math solvers are known to lean on shallow tricks: SVAMP shows a question-removed baseline scoring 60-77%. | TinyStories 2305.07759; SVAMP 2103.07191; GTS (Xie & Sun, IJCAI 2019); TRM 2510.04871 and HRM 2506.21734 (tiny cores, but grid input/output, not English) |

**Not on the list (speed only, size unchanged).** Prefix/KV cache reuse with the question placed first (Prompt Cache, RadixAttention) only helps if pass 2 stays, and #1 deletes pass 2. bf16 and CUDA graphs are worth doing anyway. int4 quantization saves bytes but not parameters, and it would perturb the hidden states the reader was trained on.
**Arithmetic.** The PR #33 recipe already has a calculator path, so a program head (PAL 2211.10435, PoT 2211.12588) is already partly there. #1's gate reuses it.
**Digits (suggested).** LFM2.5 groups digits left-to-right in chunks of 1-3, and Singh & Strouse 2402.14903 show left-to-right grouping hurts arithmetic in big models. Splitting digits before tokenizing is a free side test, but it is not part of the deciding test.

**Why #1 comes before #2.** While the talker is the full LM, a truncated reader does not shrink the counted size at all. #1 is also the test that tells us whether the 9M core is really doing the thinking. If it is not, every reader result after that is measuring the LM, not Ben's model.

## The cheapest fair test of #1 (marks fixed now, before anything runs)
**Testbed.** The English allptr runner from PR #30 (`reasoner_ptr/real/english/run_english.py`, branch project-thread-ajo58u), with the round-6 settings (`--gen 8000 --kinds 6`). Answers there are multi-word copied phrases, so it is the harder case for a copy talker. The arithmetic recipe would be easier.

**One change.** A new arm, `copytalk`, replaces `make_prefix` + LM pass 2 with a head on the core's final token states h:
- start/end span pointer over prompt positions;
- a word head over the answer words seen in training plus yes/no, tied to the LM input embeddings, which are frozen and unchanged;
- a 3-way gate;
- trained with cross-entropy on span/word/gate labels.

Everything else stays identical: reader, core, data, updates, seeds and eval files.

**Arms.** `allptr` (rerun, control) and `copytalk`, seeds 0-5, paired. That is 12 runs. A diagnostic third arm, `copytalk-nocore` (the same head placed directly on the reader output, core skipped; 6 more runs), shows whether the core adds anything. allptr also gets a shuffled-core lesion at test time (core states taken from a different question), which is fairer than zeroing.

**Eval sets.** The files the R4-R6 rounds already use: FRESH-EN-R3, GEN-HELDOUT-R4, NEW-KINDS-R5 and NEW-KINDS2-R6. No GOLD-PRIVATE, reserved or blind panels.

**Pass marks (6 paired seeds, mean exact match after normalization):**
- **PASS:** copytalk is at least allptr minus 5 points on the pooled unseen-kinds sets (NEW-KINDS-R5 + NEW-KINDS2-R6), at least allptr minus 5 on GEN-HELDOUT-R4, at least 5 of 6 seeds within 8 points, and the talk stage is at least 5x faster per question at batch 64 (measured, bf16).
- **CORE IS REAL (separate mark):** copytalk beats copytalk-nocore by at least 10 points on the pooled unseen-kinds sets. If it does not, the reader is doing the work, and that is reported as the headline.
- **FAILS (proves #1 wrong):** copytalk is below allptr minus 10 on unseen kinds, or below the bare LM 8-shot score on the same set (67.7% on NEW-KINDS-R5).
- Anything in between is "partial, no claim".
- Also report accuracy by answer type (yes/no, one-word copy, multi-word span, answers not in the prompt). That shows where any gap comes from.

**Cost (suggested).** allptr runs took about 40 min each on a 3090 (code-map), and copytalk is cheaper because no gradient flows through the LM. On 5090s at about $0.40/hr that is about $1.5-2 for all 18 runs, which needs Ben's OK since it is over the probe budget. The coding is about one new head class and an arm flag.
**Next test if it passes.** The same 12-run design with the reader cut to layer 8 (and layer 6) versus layer 16, with copytalk as the talker in both arms. Same style of marks: within 5 points passes, more than 10 points down fails.

## Caveats
- None of the quality claims for these alternatives were measured on this model. Only speed was measured.
- Two of the four literature helpers wrote from memory, without web access. A third helper then checked all 82 arXiv ids against arXiv. Two were wrong and are fixed above: MWP-BERT is 2107.13435, not 2110.08464, and the SmolLM2 title was wrong. One claim was garbled: the 770M T5 in "Distilling step-by-step" beats 540B PaLM on ANLI and SVAMP, and the "80% of data" figure is ANLI only. The helper files still contain those original errors. Check citation-check.md before quoting them.
- LFM2 sibling benchmark scores come from the post-trained model cards, not from the Base reader.

## Plain summary for Ben
Right now the big language model reads your question, the small core thinks, and then the big model reads the whole question *again* to say the answer. That second read is costly, and it may be letting the big model answer on its own. The cheapest fix is a tiny "copy the right words" talker (about 2M parameters). After that, keep only the first half of the big model's layers as the reader. That is about 2-3x faster, and the papers say the middle layers read just as well. One 18-run test (~$1.5-2) decides the first step. It also shows whether your core is really doing the thinking.

## How Arm B ran
- Wall clock: 2:42 PM to about 3:10 PM ET (about 28 min).
- 7 Sonnet helpers, 6 of them in parallel:
  1. mapped the reader and talker code (27 tool calls);
  2. readers literature;
  3. talkers literature;
  4. efficiency and LFM architecture;
  5. small reasoners literature;
  6. checked all 82 arXiv ids online;
  7. rented one 5090 and timed 10 reader variants (one host failed at start; both instances destroyed).
- Two literature helpers did not use the web, which is why the citation check was added.
- Spend: about $0.15 of Vast.
- Opus did the planning, cross-checked the key code lines (the allptr prefix in run_english.py lines 123-150), and did the ranking, the test design and this report.
