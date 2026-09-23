---
name: token-memory-result
description: 2026-09-20 result of the transformer-style TokenMemoryReasoner successor (3 recipes, all failed unseen-relation transfer)
metadata:
  type: project
---

Codex built `scripts/premonition_token_memory.py::TokenMemoryReasoner` (79,316 params, soft attention over every story token, no hard retrieval) to remove the original's structural bottlenecks. Finished 2026-09-20; comparison in `artifacts/codex-token-memory-20260920/COMPARISON.md`. Fresh held-out two-hop (unseen relation), mean of seeds 0-2: original Premonition 33.3%, A answer-only 8.2%, B guided (ordered supporting-line attention loss) 12.3%, C guided + width-scaled init at 6,000 updates 7.0%. B/C reach ~99% one-hop and ~97% practised two-hop; 0/9 pass the six-cell gate. Held-out with story memory disabled is ~6%, so on unseen combinations the model barely uses the story. Three-hop ~5%; 6 read steps do not help.

**Why it matters:** full token access + connected gradients + evidence supervision did NOT produce compositional reuse; the bottleneck is relation/person binding and a shared lookup operation, not retrieval access. Consistent with [[a3-teacher-delay-v2-result]] (slot shortcut, G_pair ~0).

**How to apply:** do not propose more attention/params/loops as the fix; Ben's top concern is intelligence = transfer to unseen combinations. No standard full-context transformer baseline was run; not equal compute.
