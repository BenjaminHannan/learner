# Borrowed backbone, stage 1: pre-registration (written 2026-10-23 before any run)

Labels: **shown** = checked in code/files; **suggested**; **untested**.
Scope: the VILLAGE model only (`learnlab/village`). The small card experiments are not touched.
Never read: the village `test` split (sealed) or creative `test.jsonl`.

## Question
Ben's plan: borrow a pretrained open model (Qwen3.8-27B class) and fine-tune the useful parts.
Stage 1 asks the cheapest version of that question on a model from the same family:
does a borrowed pretrained language model close premonition's held-out gap, and can
premonition's looped "thinking" step be built out of borrowed layers?

Why this question first (shown, `design/v1/results2/full/final_dev.json` via REPORT-V1): D (FULL, ~2.1M, own
vocab, trained from scratch on 95,000 visits) scores 80.1% on dev but 44.7% on `validation`, which holds out
whole names, templates, teacher styles and rule families. A pretrained model already knows English names and
phrasings, so it is the natural candidate to close that gap.

## Model family (shown, Hugging Face configs fetched 2026-10-23)
- `Qwen/Qwen3.8-27B`: model_type `qwen3_5`, 64 layers, hidden 5,120, vocab 248,320, 3 linear-attention
  (Gated DeltaNet) layers per full-attention layer, Apache 2.0, ~55.6 GB in bf16. Ben's PC already runs an
  IQ4_XS GGUF of it in llama.cpp (handoff/HANDOFF.md).
- `Qwen/Qwen3.5-0.8B` (hidden 1,024, 24 layers) and `Qwen/Qwen3.5-2B` (hidden 2,048, 24 layers): same
  `qwen3_5` architecture and same 248,320 vocab, so code and tokenizer carry over to 27B unchanged.
- There is no small Qwen3.8 dense model on the hub (only 27B, Flash-Next, 2.4T-A95B).

## Data
- TRAIN: village `train` shards 0-39 only (10,000 visits, about a tenth of what D saw). Built with the v1
  generator (seed 0, 250 visits/shard) so shards are identical to v1's.
- DEV: a fixed seeded sample of 4,000 questions from shards 380-399 (same pool as D's dev).
- VALIDATION: all questions of the `validation` split (D: 8,675 questions).
- Input: the visit text before the question (left-truncated to fit), then the question. Target: the
  canonical answer. Score: exact match after the same normalisation for every arm, greedy decoding.

## Arms (one change between neighbours)
- A0: Qwen3.5-0.8B, no training, few-shot prompt. Reference only, no mark.
- A: Qwen3.5-0.8B + LoRA, answer-only loss, fixed step budget.
- B: A + a looped middle block: a contiguous block of the model's own pretrained layers is run K=3 times
  (shared weights, same LoRA), i.e. premonition's thinking loop built from borrowed layers. Same steps, data,
  seed as A.
- A2 (only if time and money allow): Qwen3.5-2B + LoRA, otherwise identical to A.

## Pass marks (fixed now)
- P1 borrowed knowledge: A validation >= 55.0%. **Wrong if** A validation < 45.0% (no better than D's 44.7%).
- P2 gap: A (dev - validation) <= 25 points (D: 35.4). **Wrong if** >= 35 points.
- P3 borrowed thinking loop: B validation >= A validation + 2.0 AND B scored with the loop forced to 1 pass
  drops >= 3.0 points below B. **Wrong if** B <= A, or the 1-pass lesion changes B by < 1 point (the loop is
  not used).
- P4 size trend (A2 only): A2 validation >= A validation + 3.0. **Wrong if** A2 <= A.

Caveat written now: D answers from its own written memory over the whole visit stream; the LM arms read
the text directly. A win for A is evidence that borrowed language knowledge helps on held-out wording and
names, not that the LM has premonition's memory.

## Budget
Vast, one GPU box at a time, stage 1 cap $8.
