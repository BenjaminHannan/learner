---
name: router-sleep-approved
description: 2026-09-21 — Ben ruled that a gradient-trained soft router over frozen callable skills fits the "automatic and mathematical" sleep rule
metadata:
  type: feedback
---

Ben approved ("Yep looks good to me") sleep that freezes known skills and trains a small router (routing logits) over them by plain gradient descent, plus the plan to replace hand-given addresses with learned relative addressing.

**Why:** nothing proposes or writes a rule; the routing weights are found by arithmetic, so it satisfies [[sleep-automatic-mathematical]].
**How to apply:** callable-skills + router is the approved sleep direction ([[exp43g-transport-router-control]]); hand-given address slots remain a control only.
