# Cheaper hearer and talker: ranked shortlist (2026-10-04)

Ben's ask: the frozen LFM2.5-1.2B does both the hearing (reading the prompt) and the talking (writing the
answer). He suspects something smaller and more specialized would be more efficient. This note ranks cheap
alternatives and fixes one test, with marks written before anything runs. Labels: **shown** (measured here or in
the repo), **suggested** (literature or reasoning), **untested**.

## How it works today (shown, `reasoner_ptr/real/english/run_english.py` on branch `claude/project-thread-ajo58u`)

1. **Hearer pass.** The whole 1.2B LM reads the prompt once; its *last* layer's states go to the contextual reader
   (`make_prefix`, `hidden_states[-1]`).
2. **Core.** The ~9M core loops 4 times on what the reader produced.
3. **Talker pass.** The 1.2B LM runs *again* on [8 core vectors + 8 pointer vectors + every prompt word] and writes
   the answer token by token.

So the 1.2B is ~99% of the parameters and runs twice. The 5090 speed test (PR #35) found 3-5x slower prompt
reading than the bare LM at batch 1. Two more facts that matter:

- **shown:** the eval `generate()` has no KV cache: every new answer token re-runs the whole prefix. Free to fix.
- **shown (speed file):** the bare 1.2B decodes ~70 tokens/s at batch 1, which is ~14 ms per token. A 1.2B model on
  a 5090 should take a few ms if it were limited by memory, so batch-1 time is mostly per-layer launch overhead.
  **suggested:** a narrower model with the same 16 layers will barely speed up batch 1; fewer *layers* (or
  `torch.compile` / CUDA graphs) is what speeds up batch 1. Narrower models speed up batch 64 roughly in
  proportion to their size.

## Ranked shortlist

Size = whole system (core included). Speed numbers are estimates (untested) unless marked.

| # | Idea | Whole size | Speed (est.) | What it would lose | Work |
|---|---|---|---|---|---|
| 1 | **Same family, smaller: LFM2.5-350M** does both jobs | ~0.36B (was 1.18B) | batch 64 ~3x faster; batch 1 ~same (same 16 layers) | world knowledge, harder questions, few-shot skill of the bare LM | none: `--lm` flag; **shown:** identical tokenizer (sha of tokenizer.json matches 1.2B), width 1024 |
| 2 | **Half-depth hearer**: stop the hearer pass at layer ~8 of 16 and read that layer | 1.18B (same) | hearer pass ~2x faster, so whole prompt read ~1.3-1.5x | maybe nothing; middle layers are often *better* features than the last | ~5 lines |
| 3 | **Encoder-decoder (Flan-T5-base 248M or -large 783M)**: encoder hears once, decoder cross-attends to core state + words | ~0.26B or ~0.79B | no double pass; batch 1 limited by 12+12 layers | T5's word list cannot write `{ } < \n` and some symbols (bad for code and Minecraft commands); Flan was trained on SQuAD-style QA, so its bare score is a high bar | ~150 lines |
| 4 | **Tiny specialized talker from scratch**: 2-4 layer pointer-generator (copies prompt words, small own vocab) | hearer + ~10-30M | fastest of all, batch 1 too (few layers) | open-ended fluency and knowledge; needs lots of training text | new module + data |
| 5 | **Small bidirectional hearer** (DeBERTa-v3-small ~140M with embeddings, ModernBERT-base 149M), paired with #4 | ~0.17-0.2B | fast reading | another tokenizer to bridge; loses the LM's general knowledge | moderate |

Free speed fixes that apply to every option (no accuracy risk): KV cache in generation; question-first with
cache reuse (PR #35 idea); `torch.compile` or CUDA graphs for batch 1.

### Why this order

- **#1 first** because it is free to try and it answers the real question: does the system need 1.2B at all? If a
  0.36B system holds the 92.6% score, Ben's "beat 1-2B models at whole size" goal gets much easier (the bar
  becomes "beat a 1.2B model while being 0.36B"). If it collapses, size matters and #2 is the next lever.
- **#2** is the cheapest way to stop paying for the duplicated pass while keeping the big talker. **suggested**:
  Skean et al. 2025 ("Layer by Layer") found intermediate layers of LMs often give better features than the last
  layer; Gromov et al. 2024 ("Unreasonable Ineffectiveness of the Deeper Layers") and Men et al. 2024 (ShortGPT)
  found many deep layers can be dropped with small loss.
- **#3** matches Ben's 09-29 design best ("the talker translates the core's final state into words"): a T5
  decoder is built to cross-attend to an encoder's states (Raffel et al. 2020; Chung et al. 2022 for Flan-T5;
  Izacard and Grave 2021, Fusion-in-Decoder, for feeding extra vectors into it). It is ranked below #1-2 only
  because of the symbol gaps and the strong-bare-baseline problem.
- **#4-5** are the "truly specialized" end. **suggested:** pointer-generator / copy decoders (See et al. 2017;
  Gu et al. 2016, CopyNet) handle never-seen answer words by copying, which is exactly what the allptr exit needed;
  TinyStories (Eldan and Li 2023) shows models under ~30M parameters can write fluent narrow English. For
  Minecraft, most "talking" is choosing actions from a small set, which a tiny head does well. Risky and costly
  now, so later.
- Not on the list: distilling the 1.2B into a small talker after training (MiniLLM, Gu et al. 2024) and
  compressing prompts into a few vectors (gist tokens, Mu et al. 2023; ICAE, Ge et al. 2024). Both are useful
  later but are not cheap first steps.

## The test that decides #1

Pass marks: `design/research/PASS-MARKS-SMALL-LM.md` (committed before any run).
