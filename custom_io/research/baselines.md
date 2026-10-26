# baselines (Sonnet reader, 2026-10-05)

VERIFICATION. I checked every id below on 2026-10-05 against huggingface.co/api/models/<id> (weights, license tag, config) and the repo's own tokenizer.json. "Total" counts weights. "ne" is non-embedding (total minus the input/output tables, which hold most of a small model's weights). The API total over-counts for older repos because attention-mask buffers are counted: GPT-2 reads 137M and Pythia-70m reads 95.6M. I counted weights instead, so GPT-2 is 124M. TinyStories sizes are computed from config and file size, since there is no safetensors count. Benchmarks come from model cards, the Qwen3 report (Table 8, fetched through a summariser) and the old Open LLM Leaderboard result files (lm-harness GSM8K 5-shot).

1) MODELS (params total, ne in brackets, in M)
~10-30M
- EleutherAI/pythia-14m: 14.1 (1.2). Apache-2.0. ctx 2048. GPT-NeoX BPE 50k, digits merge. No GSM8K.
- EleutherAI/pythia-31m: 30.5 (4.7). Same licence, ctx, tokenizer. No GSM8K.
- roneneldan/TinyStories-8M: 19.7 (6.3). No licence tag. ctx 2048. GPT-2 BPE 50k. Stories only. TinyStories-33M (68.5 total, MIT) scores 0.0 GSM8K.

~70-90M
- EleutherAI/pythia-70m: 70.4 (18.9). Apache-2.0. ctx 2048. GSM8K 0.3 (card).
- tiiuae/Falcon-H1-Tiny-90M-Base: 91.1 (74.4). Falcon-LLM License. 32k BPE, single digits. Attention+Mamba hybrid. No GSM8K on card.

~125-160M
- HuggingFaceTB/SmolLM2-135M (+ -Instruct): 134.5 (106.2). Apache-2.0. ctx 8192. 49,152 BPE, single digits. GSM8K 1.4 (5-shot, both).
- EleutherAI/pythia-160m: 162.3 (85.1). Apache-2.0. GSM8K 0.2.
- openai-community/gpt2: 124 (85). MIT. ctx 1024. 50,257 BPE, digits merge. GSM8K 0.7.
- state-spaces/mamba-130m-hf: 129.1 (90.5). No licence tag. No fixed context. 50,280 vocab. A non-transformer. No GSM8K.
- facebook/MobileLLM-R1-140M (+ -base): 140.2. "FAIR Noncommercial Research", gated. ctx 32k post-trained, 4k base. 128k vocab. GSM8K 4.1 (0-shot, post-trained; 360M 24.5, 950M 67.5). MobileLLM-125M/350M/600M/1B exist, also gated.
- Also: EleutherAI/gpt-neo-125m (125.2, MIT, GSM8K 0.3); facebook/opt-125m (125M, licence "other", GSM8K 0.1).

~270-360M
- google/gemma-3-270m (+ -it): 268.1. Gemma terms, gated. ctx 32k. No GSM8K on card.
- HuggingFaceTB/SmolLM2-360M: 361.8 (314.6). Apache-2.0. GSM8K 3.2 base, 7.4 instruct.
- LiquidAI/LFM2.5-350M (+ -Base): 354.5 (287.4). LFM Open License (lfm1.0). ctx 32k on card (config 128k). 65,536 vocab, digits grouped up to 3. No GSM8K on the LFM2.5 card; the older LFM2-350M card lists 30.1.
- ibm-granite/granite-4.0-350m (+ -base): 352.4. Apache-2.0. ctx 32,768. 100,352 vocab, digits up to 3. GSM8K 30.7 (8-shot, instruct).

~0.5-0.6B
- Qwen/Qwen2.5-0.5B (+ -Instruct): 494.0 (357.9). Apache-2.0. ctx 32,768. 151,936 vocab, single digits. GSM8K 41.6 (4-shot CoT, Qwen3 report); 33.4 base / 26.8 instruct (SmolLM2 card, 5-shot).
- Qwen/Qwen3-0.6B-Base: 596.0 (440.5). Apache-2.0. GSM8K 59.6 (4-shot CoT). The post-trained Qwen3-0.6B scores 36.5 in the LFM2 card's table.
- tiiuae/Falcon-H1-0.5B-Base: 521.4. Falcon-LLM License. GSM8K 60.2 (card). The same table gives Qwen3-0.6B 50.0 and Qwen2.5-0.5B 34.8, so setups differ between papers.

~1-1.7B
- LiquidAI/LFM2.5-1.2B-Instruct / -Base: 1,170.3 (1,036.1). lfm1.0. 32k. No GSM8K on card (LFM2-1.2B card: 58.3).
- HuggingFaceTB/SmolLM2-1.7B: 1,711.4. Apache-2.0. GSM8K 31.0 (5-shot).
- Qwen/Qwen3-1.7B-Base: 1,720.6. GSM8K 75.4. Qwen2.5-1.5B: 1,543.7, GSM8K 68.5.
- EleutherAI/pythia-410m (405.3, GSM8K 0.7) and pythia-1b (1,011.8) fill the gaps.

Reading: no general-purpose base LM at or below 160M scores above 1.4% on GSM8K, so published numbers cannot separate this class. Only our own runs on our rows can. I found no dedicated arithmetic score for any of these. Pythia-14m/31m were re-uploaded on 2026-02-27 (the old deduped weights moved to -deduped), so pin the revision hash.

2) FAIREST BASELINES AND HOW TO RUN THEM
(a) 10-30M custom model. A model with its own small vocabulary spends all its weights on compute, whereas Pythia-31m is 85% embedding table. So report both axes.
- Compute-matched: Pythia-31m (4.7M ne) and Pythia-70m (18.9M ne).
- Total-matched: Pythia-31m and TinyStories-8M.
- Pythia-14m is the floor.
- The most important control is a random-init plain transformer (6 layers, width 256-384) trained on the same rows with the custom model's own tokenizer. It isolates "reasoner versus ordinary transformer".

(b) 100-150M.
- Primary: SmolLM2-135M (modern, Apache, single-digit tokens, 106M ne).
- Secondary: Pythia-160m (85M ne, merged digits) and GPT-2 124M.
- Add Mamba-130m as the non-transformer comparison, and a random-init copy of SmolLM2-135M's architecture.
- The "beats a bigger model" bars are SmolLM2-360M, LFM2.5-350M, Qwen3-0.6B-Base, and the bare LFM2.5-1.2B.

Protocol (both arms, every model):
- Few-shot: plain "Q: ... A:" text for base models, chat template for instruct ones. Draw k=8 examples from the training rows (the repo's lm_fewshot arm uses 8 fixed examples). Greedy decode, max 8 new tokens, exact match on the same held-out and unpractised-kind rows.
- Full fine-tune: same 200k rows, same order and seed, same batch (rows per update) and number of updates. AdamW, wd 0.1, cosine with warmup, bf16, loss on answer tokens only. Same small LR grid for everyone (3 values, factor 3 apart), chosen on a dev split of the training distribution, never on the test rows. 3 seeds, then report mean and interval.
- Add one longer-budget arm. The earlier Fable baseline (branch claude/ultracode-learning-blocker-gh011t, artifacts/fable-baseline-transformer-20260920) matched 94,629 vs 94,838 params. Its dev run was still under-trained at the matched 6,000 updates (sequence accuracy 0.062), which would have made it a weak test.
- Extra floors: majority answer per family (the sandwich's core mostly carries a family signal), and a shuffled-answer fine-tune (should sit at chance).
- Report per family. Digit tokenisation differs (GPT-2/Pythia merge digits; LFM2.5 and Granite group up to 3; Qwen, SmolLM2, Falcon-H1 use single digits). That changes arithmetic and should be visible.

Rough time on one RTX 5090 (UNTESTED estimate). Basis: 6 x matmul-params x tokens, 5.6M tokens per epoch, bf16, logits computed only at the 3 answer positions, 5-35% utilisation, small models overhead-bound.
- Per epoch: 14-31M about 0.5-1 min; 70M 1-2 min; 135-160M 2-5 min; 360M 6-10 min; 0.6B 10-15 min.
- 1.2B full fine-tune: 20-35 min per epoch, about 17-19 GB with AdamW states, so it fits in 32 GB.
- At 3-5 epochs a 135M run is 10-25 min. 3 LRs x 3 seeds is 2-4 h per model. Few-shot evaluation takes minutes.

3) EXISTING BARE-LM NUMBERS IN THE REPO
Skills rows, frozen LFM2.5-1.2B-Instruct, zero examples, greedy (DIAG-bare.json, 8 min). The 8 families are the sandwich's worst. Trainfit is the first 320 of seed-1's 2,000 practised rows. Held-out is 320 in-distribution rows (40 per family).
- Chat direct ("reply with only the final answer", 16 new tokens): trainfit 5/320 (1.6%), held-out 9/320 (2.8%).
- Chat with worked steps then "Answer:" (256 new tokens): trainfit 138/320 (43.1%), held-out 144/320 (45.0%).
  - Held-out by family: chain_story2 80.0, state_update 72.5, var_chain 70.0, chain_ops 62.5, fewshot_number_rule 55.0, seq_cycle 17.5, cipher_map 2.5, group_induct 0.
  - Several stored samples end mid-sentence, so the cap probably cuts some answers (not checked). Treat 45% as a floor.
- Raw copy-path format (no template, no prefix, 12 tokens): 0/320 on both. The LM just continues text, so this is a format artefact, not a capability measure.

Context (same branch):
- The sandwich main2 scored 121/320 (37.8%) on that trainfit slice at update 0 (DIAG-v4.md).
- It reached 48.1% on its 2,000 practised rows after training.
- It scored 68.5% on all 1,360 in-distribution rows (34 families x 40) but 24.4% on family-shift rows (RESULT-v1.md).
- With worked steps the bare LM is in the same range as the sandwich on these 8 families (43-45% vs 38-48%). With direct answers it is near zero.
- Suggested, not tested: the LM's own step-by-step reasoning is the engine.
- No 8-shot bare run on the skills rows exists. That is the missing baseline.

Fair scaling (branch claude/project-thread-6qsyg1, scaling_test/RESULTS-SCALE.md). This is English reading comprehension, not the skills rows.
- On NEW-KINDS-S (192 new-kind questions), core 9.0M / 17.9M / 35.8M scores 64.4 / 65.3 / 66.3% (6 seeds). Bare 1.2B shown 8 examples scores 62.5% (one run).
- S3 minus S1 is +1.9 (interval -0.95 to +4.77): in between, no scaling claim.
- On FRESH-R3: system about 92.5%, bare 8-shot 75.0%. Zeroing the core drops FRESH-R3 to 0% at every size.
- Separately (notes/hearer-talker/RESULTS-SMALL-LM.md): bare LFM2.5-350M scores 33.9% zero-shot and 50.0% 8-shot against 75.0% for bare 1.2B, and the 350M system reached 66.1%.
- Other bare 8-shot figures in notes/reader-talker-compare/verdict.md: 67.7% (NEW-KINDS-R5) and 77.6% (round-6 second unseen set).
