---
name: test-time-limit-30min
description: "Ben's rule (2026-09-19) — every experiment/test wave must finish in under 30 minutes wall-clock unless it would cost more than $2 to make it so"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: c8a8b82f-df85-4a56-b83a-ffb6edbe02ff
  modified: 2026-09-19T21:22:49.391Z
---

Every test or experiment wave I launch must finish in **under 30 minutes wall-clock**, unless getting it under 30 minutes would cost more than **$2** (then say so and ask).

**Why:** Ben said on 2026-09-19 "all your tests, unless they cost above 2$, should be under 30 mins" after I queued ~50-60 min Mac runs and a ~40 min sequential BensPC job. He is brainstorming live and wants fast turnaround; cheap parallel vast.ai boxes are approved for this (see [[compute-availability]], [[gpu-budget-cap]]).

**How to apply:** size runs before launching: parallelize across cores/boxes (toy-ladder runs are CPU-launch-bound, ~4 steps/s per M1 core, so 12,000 steps = ~50 min; use a ~6,000-step recipe with the phase fractions rescaled to keep phase lengths in steps, or faster cores), run GPU arms concurrently instead of sequentially, and prefer the cheapest vast offers by cost-per-run (many fast cores, not big GPUs). State expected wall-clock and cost up front. Destroy rentals immediately after copying results ([[vast-rental-active-20260919]]).
