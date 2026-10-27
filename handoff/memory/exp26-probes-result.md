---
name: exp26-probes-result
description: "2026-09-20 experiment 26 no-training dispatcher probes — D1/D3/D4 fired; STOP healthy, operation pointer counts calls; reg+ctx retired for practice waves"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-21T01:40:40.280Z
---

Experiment 26 (no-training probes on 19-awake, 19b-U5, 19b-U8 × 3 seeds + 12 v4 controls) ran under freeze; positive control passed. D1, D3, D4 fired: STOP is healthy, the operation pointer asks the final attribute early ("counts calls"), and on reg+ctx the subject pointer is a second limiter. With both pointers handed over every checkpoint is 64/64 up to 8 calls.

**Why:** settles the GPT-6 Pro adjudication ([[canonical-operator-roadmap]], file 25b): stateless-STOP fix stays VETOED; no more practice-length waves on reg+ctx ([[exp19-replay-result]], [[exp19b-u8-result]]).

**How to apply:** the only licensed dispatcher training experiment is 25b step 3 (`ctx` arm ± self-written "used" mark, 2 arms × 3 seeds, ~16 min), separately registered, must forecast that a call-counter may ignore the mark. Off the demo path; yields to talker and experiment 27. Results: artifacts/fable-dispatcher-probes26-20260921/RESULTS.md.
