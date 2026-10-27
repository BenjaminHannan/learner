---
name: reasoner-thinks-until-done
description: Ben's standing design rule (repeated, frustrated 19:24 UTC 2026-09-24): the reasoner decides how long to think and emits a "thinking stop" token when more thought no longer helps
metadata:
  type: feedback
  modified: 2026-09-24T19:24:29.473Z
---
Ben 19:23-19:24 UTC 2026-09-24 (sleep research thread): "The model should get to choose as long as it needs" and "I feel like I've said this multiple times ... I've literally used the term 'thinking stop token' that it can generate to stop thinking when it no longer helps."

It was ADOPTED earlier ("Model decides its own think length via a 'done' token, no flat per-step penalty", design/research/broad-sweep-2026-09-19/ideas_full.json:1088), then lost: 294/296's LoopThinker trains on random 2-12 passes and evals at a fixed 12 (scripts/claude_rsn294_run.py:23,44). Older Premonition-mini had a HALT head at 525/1024 (barely above chance); research idea #56 says learned halting gates can damage the trajectory and suggests a post-hoc confidence exit.

**Why:** Ben's core picture of reasoning is a brain that keeps thinking until done (humans take as many steps as a problem needs). Re-proposing fixed depth reads as not listening.
**How to apply:** every learned-reasoner design must include a learned stop/"done" signal with variable depth, tested on chains longer than any practised. Never present a fixed-pass reasoner as the plan. Also from the same messages: Ben wants it to learn rules (not patterns), wants RL in real-world-like environments using MiMo-V2.6's mixed-task GRPO recipe, and wants a cheap API teacher model. See [[brain-emulation-goal]], [[sleep-research-2026-09-24]].
- Reasoning research thread (19:34 UTC) input: loop extra passes do nothing today (loop-s2 dev 916/1200 at 6 and 12 passes). Order: rule probe ($0), fix loop copy (per-pass copy loss; else lr 1e-4 / RMSNorm before inject / no step emb), THEN adaptive halting (KL-stability exit, passes = 2 x hops, or TRM-style halt head that doubles as "I don't know"). MiMo-V2.6 tricks that fit $4: dynamic sampling (drop all-same groups), length penalty only among right tries. Teacher: 30M sees no words, so a teacher can only write practice notebooks/chats (code re-solves golds). Anthropic/Google/OpenAI terms forbid training competing models on outputs; prefer open-weight teachers (GLM, MiMo MIT).
