---
name: learned-reader-decision
description: "2026-09-22 — no more hand wording tables; wording coverage goes to the learned ear (235 SmolLM2 ≈95% vs rules ≈32%), hand table stays as inventory + safety check"
metadata:
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-22T20:46:31.061Z
---

2026-09-22 16:39, director decision logged on the board: stop adding hand-written wording tables and regexes to cover how people phrase things.
- Evidence. 237b (verb phrases), 246 (synonyms), 251 (direction verbs) and 231b (wordings) were all safe (0 added wrong values), but covered only 45–70 % on fresh blind wordings.
- Exp 235's fine-tuned SmolLM2-360M ear read 87/92 facts exactly, against 29/92 for the 138i rules. It made 3 wrong saves against the rules' 8, and ran at 56 ms per turn on the 5070 Ti (579 ms on the Mac CPU).
- 235 was a registered FAIL only on wrong saves (bar ≤ 2). All 3 were meaning errors: pronoun reference, a question shaped like a statement, and a relation picked from a noun.

**Why:** Ben wants fluent, mistake-free conversation. Hand tables stall on wording coverage, and Ben has allowed a borrowed ear for now ([[borrowed-ears-weights-ok]]).

**How to apply:**
- Wording and understanding fixes go to the ear. 235b adds a write gate (question guard plus k-best margin, with unsure frames sent to user confirmation).
- The relation table stays as the inventory and the safety check.
- Don't brief new hand-wording-coverage experiments.
- The ear must pass a fresh blind panel with at most 1 wrong save before it is wired into the loop.
- Related: [[decide-better-option]], [[conversation-first-priority]].
