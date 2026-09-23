---
name: benchmark-goal
description: 2026-09-22 Ben wants benchmark results that impress an expert — beat state-of-the-art models of equal size
metadata:
  type: project
---

Ben, 22 Sep 2026: wants to "beat state-of-the-art models on benchmarks of models of equal size" so that someone who understands the field says "that's pretty impressive".

**How to apply:** I told him general LM benchmarks (MMLU, HellaSwag, GSM8K) are not winnable on $30 against SmolLM2-class models trained on trillions of tokens; the winnable, expert-recognised targets are what the architecture is built for: MQuAKE / CounterFact / zsRE (fact editing + multi-hop), two-hop curse and reversal curse tests, CLUTRR (longer chains than trained; blocked by our length-generalisation wall), abstention/hallucination rate, accuracy per parameter. Must include honest baselines: same-size plain transformer AND a retrieval (RAG / MeLLo-style) baseline, because an expert will ask "how is this not just a database?". See [[demo-requirements-uncle]], [[focused-priorities-and-claims]].
