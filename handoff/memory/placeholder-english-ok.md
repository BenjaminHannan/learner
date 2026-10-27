---
name: placeholder-english-ok
description: 2026-09-22 Ben allows an existing open transformer as a TEMPORARY placeholder for the English parts; final demo must be his own architecture + weights; web search is just a tool
metadata:
  type: project
---

Ben, 22 Sep 2026: for now the English in/out parts may be "whatever" existing transformer (e.g. Qwen 27B already on BensPC). The FINISHED version shown to anyone must be his own architecture with all weights trained by him; data need not be his (placeholder-generated training data is fine). Web search counts as a tool, not architecture (he suggested reusing Codex's; Codex is not installed on the Mac, so the GPT web bridge is the searcher in scripts/fable_thinking_m2.py).

**Why:** he wants to talk to the whole system in English soon, without waiting for from-scratch ears/mouth.

**How to apply:** build English LISTENING on the placeholder behind a narrow interface (utterance -> structured lines), then use it as data generator/labeller for the from-scratch ears/mouth and swap when they match it. This narrows [[talker-must-be-our-architecture]] (that rule is about the final deliverable) and [[ben-vision-20260921]]'s "own model only". Benchmarks goal: [[benchmark-goal]]. Demo bar: [[demo-requirements-uncle]].
