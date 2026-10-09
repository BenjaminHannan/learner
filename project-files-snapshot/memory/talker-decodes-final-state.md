---
name: talker-decodes-final-state
description: Ben's design for item 1 (02:34 UTC 09-29) - reasoner loops to a final state, talker translates that state to words; talker does not read notes
metadata:
  type: project
---

Ben (02:34 UTC 09-29): the talker does not read notes. The reasoning model is trained to loop into a final state; the talker translates that state into words.

**Why:** his joined-model design. Sweep test 5 (talker reads notes) was withdrawn and its jobs moved to handoff/queue-retired/.
**How to apply:** design talker tests as state-to-words decoding; keep LongMemEval final set sealed. See [[sparse-moe-approved]].
