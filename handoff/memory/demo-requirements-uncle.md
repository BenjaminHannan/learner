---
name: demo-requirements-uncle
description: 2026-09-22 Ben's demo bar before showing uncle/dad — $30 total budget, model must answer questions about itself and demonstrate why it beats a plain transformer
metadata:
  type: project
---

Ben, 22 Sep 2026: the budget before showing his uncle/dad (possible funders) is $30 (I treat this as the existing cap in [[gpu-budget-cap]], ~$27 left, unless he says it is a fresh $30). He thinks that is enough for a "good enough" model.

Demo requirements:
- Whoever talks to it can ask about the model itself ("what did you train on?") and get a correct answer.
- While explaining, it should DEMONSTRATE why it is more impressive than a normal transformer (not just claim it).
- Must be our architecture: see [[talker-must-be-our-architecture]].

**How to apply:** put self-facts in the notebook as a taught "self" entity (training data, parts, sizes) so answers are true by construction and updatable; build a live demo script: teach a new fact -> immediate two-hop answer -> correction -> restart persistence -> "I don't know" instead of making things up, side by side with a same-size plain transformer that fails these. As of 22 Sep there is NO end-to-end model yet. Related: [[conversation-first-priority]], [[talker-route-b]].
