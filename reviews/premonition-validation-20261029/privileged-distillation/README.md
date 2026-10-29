# Isolated context-privileged distillation primitive

Research prototype, 2026-10-29. **Default unused. No application integration,
model loads, training jobs, downloads, service calls or configuration changes.**

`privileged_kl.py` computes full-distribution, answer-token-normalized
`KL(teacher || student)` on an identical sampled answer after different prefixes.
It is a paper-inspired primitive, **not full Sleep, LTI, RL, MoE, or a demonstrated
learning/retention improvement**. Source: [Language Models Need Sleep, section
3.3](https://arxiv.org/html/2606.03979v2#S3.SS3).

## Contract and alignment

Supply ordinary causal logits `[B, T, V]`, exact input IDs, boolean attention
masks, unpadded prefix lengths and answer lengths. For answer token `j`, select
logits at `first_valid_position + prefix_length - 1 + j`. The first answer token
is predicted by the final prefix position. Prefix/BOS/thinking-marker tokens
belong in the prefix length; answer lengths contain only actual sampled tokens
(optionally including EOS), never padding. Left/right padding is supported;
interior holes are rejected. Extra valid trailing tokens are not supervised.

Both prefixes must be followed by exactly the same answer token IDs over the
supervised spans. A caller must provide the same pinned tokenizer/vocabulary ID
mapping fingerprint as well as matching vocabulary dimensions. A checkpoint's
marketing name is not that fingerprint. Different answers, out-of-range IDs,
empty spans, bad bounds, non-finite logits and oversized inputs fail explicitly.
NaN/Inf anywhere in either supplied logits tensor is rejected, including unused
positions. Ordinary finite prefix/padding logits cannot affect the objective.

Sampling/teacher targets are detached. Student logits retain autograd; no
gradient is propagated through the token-sampling distribution. The exact loss
is the sum of vocabulary KL terms across valid answer tokens divided by the
number of those tokens, not batch count or padded sequence length. FP16/BF16
inputs accumulate in FP32; FP64 is preserved. No truncation, top-k approximation,
KL direction reversal, temperature scaling or reward term is implicit.

Default caps: 8 examples, 4096 sequence positions per side, 256 answer tokens
per example, vocabulary 256000, and 64 MiB combined logical input tensor bytes.
These caps bound the input contract, not peak autograd/temporary memory. The
helper accepts already computed logits, so the caller must apply a memory cap
**before** producing model logits. Real LFM3 full-sequence logits can exceed
the default cap. Select supervised hidden states before the output head in a
future integration, then independently validate its selected-logits interface;
do not bypass this helper's alignment contract by pretending selected logits
have ordinary full-sequence positions. Toy tests use only tiny CPU tensors.

## Future integration notes for independent review

1. Pin the exact frozen base, tokenizer, template, incumbent adapter, candidate
   initialization and sampled-token provenance. Teacher evidence is a verified
   source/context prefix; student gets the ordinary question prefix. Keep the
   source evidence out of held-out evaluation. Retention and acquisition need
   separate measurements across successive synthetic learning blocks.
2. The frozen **INCUMBENT adapter** is part of the teacher state. Calling
   `disable_adapter()` restores the foundation model and discards incumbent
   personal learning; it is not a retained-memory teacher. Generate student
   answers with `torch.no_grad()` and snapshot/detach their integer token IDs.
3. A frozen base's tensor storage can be shared while teacher and candidate
   adapters remain distinct, but do not assume PEFT adapter switching is harmless
   inside autograd. One safe reference sequence is: sample detached student
   answer IDs; run the frozen incumbent teacher in eval/no-grad mode; detach and
   copy teacher answer-position targets; release the teacher computation;
   activate candidate adapter; create the student forward graph; compute KL;
   backward; finish optimizer update; release the graph. Teacher/candidate
   adapter parameters must be disjoint and only candidate parameters enter its
   optimizer. PEFT version behavior and requires-grad flags need validation.
4. **Never swap, copy, merge or modify tensors, adapters or active execution
   paths while a student graph is alive**, including during checkpointed
   recomputation. A separate immutable teacher wrapper sharing only truly frozen
   base storage is another design, requiring explicit alias/gradient tests.
5. Cache teacher targets only for their exact sampled answer/context and pinned
   teacher identity. A fresh student rollout generally invalidates that cache.
   A single generic frozen-base continuation cache is not on-policy privileged
   distillation. Source privacy and production promotion remain separate gates.
6. Keep rollout length/count small and record generation, teacher-forward,
   student-forward/backward times and memory. Evidence quality, calibration,
   prior-memory retention and native GGUF fidelity remain unproven. Do not infer
   gains from this loss passing toy tests.

## Validation

Run with the existing environment, with no installation:

```sh
cd reviews/premonition-validation-20261029/privileged-distillation
/Users/ben-hannan/learner-ops/speedbench/venv312/bin/python -m unittest -v test_privileged_kl.py
```

The tests use real PyTorch autograd and cover equality, gradient direction and
descent, teacher/sample isolation, first-token causal alignment, different prefix
lengths, padding invariance, token-normalized batches and rejection conditions.
No LFM3/model/backend is imported. No GPU is selected. The test entry point uses
one CPU thread.

Observed result on 2026-10-29: all 8 tests passed, 0.297 seconds, command exit 0.
This validates the tensor primitive only, not model learning or integration.
