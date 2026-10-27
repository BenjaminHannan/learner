---
name: creative-stop-toy-result
description: 2026-09-22 creative stopping toy — registered KEEP_FIXED_N 3/3; checker-only FOUND + same-model guided dreamer + backlog did the work
metadata:
  type: project
---

Creative stopping toy (scripts/fable_creative_stop_toy.py, artifacts/fable-creative-stop-toy-20260921/RESULTS.md): test suite run once after freeze, verdict KEEP_FIXED_N in 3/3 seeds. 0 false FOUND when only the exact checker may say FOUND (143–154 when the filter may). Solving went ~25% → ~98% from Ben's ideas (dreamer uses the filter's judgement = one model; stronger filter) plus an unchecked-idea backlog — not from the stop rule. Smart "out of ideas I believe in" (Good-Turing) rule: ≥95% of never-stop's solves, 73–80% correct give-ups, but never beat "think 11 rounds then ask Ben".

**Why:** decides CREATIVE mode's ending per [[three-modes-goal]] and doc 33.
**How to apply:** build CREATIVE with checker-only FOUND, fixed round cap, backlog, then ASK-BEN; don't re-propose the EV/stall rule. Ben (22 Sep): thinking time is not a cost to penalise; checker/filter/worker are one model; wants a provably good design to show family for funding — see [[ben-vision-20260921]].
