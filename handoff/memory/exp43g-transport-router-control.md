---
name: exp43g-transport-router-control
description: 2026-09-21 — GPT's hand-addressed transport net + 21-number router sleep: v1 fit-fail 2/3, v2 (cosine scores) perfect 6/6 incl. fresh seeds; control only
metadata:
  type: project
---

GPT review adjudicated in design/v3/30-modes/42-gpt-review-adjudication-fable.md. Built its spec as scripts/fable_transport43g.py (+ _v2), artifacts/fable-transport43g-20260921/.

Result: with six readable places GIVEN by hand, 209k params learn all six CardFold skills, 1.00 at lengths 12/16, and learn CARDFOLD from 20 raw episodes (fresh 1.00, long 1.00) by training 21 routing logits over frozen callable skills; ~70 s base, ~15 s sleep. v1 failed to fit SWAP/FOLD in 2/3 seeds (softmax saturated); fix = 10×cosine address scores. Broken bank → install correctly rejected by the CV gate.

**Why:** it isolates what the transformer lacks: length-free addressing and callable reusable skills. The hand-given places are the answer key, so it is an upper-bound control, not Ben's "model that learns" ([[human-learning-redesign]], [[talker-must-be-our-architecture]]).
**How to apply:** never present it as the architecture. Next rung = same callable-skills + router design with LEARNED relative addressing (43D style). Whether a soft router over named skills fits [[sleep-automatic-mathematical]] is Ben's ruling. Related: [[exp43e-rank4-sleep-confirmed]], [[exp43-length-gate-and-shared-sleep]].
