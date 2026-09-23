---
name: outside-review-28-adjudication
description: 2026-09-21 outside review of the 44 problems received and adjudicated — hard-code the hop loop, notebook contract first, Ben writes 30 natural turns, cut 90M/209M; talker timing is Ben's call
metadata:
  type: project
---

Ben relayed a 19-page outside review (saved verbatim: design/v3/28-outside-review-answer-verbatim.txt; my rulings: design/v3/28-outside-review-adjudication-fable.md). It predates experiments 26/27/29; its M1–M3 worries (candidate set, reserved codes as negatives, code collisions) checked out clean.

Accepted: deterministic hop loop for the assistant (learned dispatcher = ablation only; if reopened, supervised traces not RL); notebook contract as plain software first (stable IDs + aliases, append-only log, discrete failure statuses, templated "I don't know"); Ben writes 30 natural turns before more talker tuning, sealed 100 later; gist has no factual authority; no 6 h Windows run before save–kill–resume test; cut 90M/209M, keep the $27; lighter manifests for cheap diagnostics; concept toy, dreamer, web, tools stay parked.

**Why:** the review separates "useful teachable assistant" (achievable with exact execution) from "learned length-general controller" (no evidence) — keep them separate.

**How to apply:** open decision for Ben — does the learned talker ([[talker-route-b]]) wait until a deterministic-reply assistant works end to end (review's advice, my recommendation) or continue in parallel. Best novelty candidate = the zero-trap mechanism from [[exp21-newnames-result]]. See [[teachable-roadmap-fable-review]], [[exp29-newnames-result]].

**Decided by Ben 2026-09-21:** yes — the learned talker waits until the fixed-reply (template) assistant works end to end; it is then trained against the same interface.
