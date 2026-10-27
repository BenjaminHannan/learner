---
name: teachable-roadmap-fable-review
description: "2026-09-20 Fable reviewer's roadmap to a teach-then-ask demo — notebook memory, M0–M5, 'new names' is the next experiment"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-20T22:49:54.898Z
---

Fable reviewer (not Astra) wrote design/v3/21-teachable-assistant-roadmap-fable-review.md for [[teachable-assistant-goal]]. Key rulings: count-to-3 is off the demo's critical path (≤3-step questions ~64/64); persistent memory = external notebook (append-only diary + current view + symbol table), so corrections propagate by recomputation; milestones M0 notebook demo with no training (frozen operator, fixed loop, rule-based reader) → M1 new names as random codes → M2 UNKNOWN → M3 4,096 facts → M4 learned tiny-English reader → M5 learned control + practice. Next experiment to register: "new names" (16 entity tokens → per-world random codes from a 4,096 pool, 1,024 reserved; seeds 2100–2102, 2 arms, one Mac wave; reviewer's P(all-seed pass)=.35). Honest framing: Qwen + same notebook would be a better product; the project's value is tiny-model learned reasoning and teaching that changes reasoning — compare once against dictionary+rules and Qwen-with-diary.

**Why:** Ben asked for a route from the toy to an assistant he teaches in English.
**How to apply:** build M0/M1 in parallel with 19b and the concept toy ([[parallelize-when-possible]]); the fixed-loop demo must be described as "answers come from the notebook", not "the model chooses its steps" ([[focused-priorities-and-claims]]). Two cited paper claims were unverified by the reviewer.
