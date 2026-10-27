---
name: exp19b-u8-result
description: "2026-09-20 experiment 19b (practice 1–8 calls vs 1–5): registered FAIL 3/3; U8 collapsed two seeds to 2–3 calls, helped one seed to 4–6; U5 reproduced exp 19"
metadata: 
  node_type: memory
  type: project
  originSessionId: 76c622f5-1395-42cc-b432-71b65f256cf4
  modified: 2026-09-20T23:33:23.482Z
---

Experiment 19b (D controller only, U5 vs U8 practice mix, 2,000 offline updates from exp-19 awake checkpoints, seeds 1900–1902) ran once under freeze on 2026-09-20: registered FAIL in all three seeds. U8 made seeds 1900/1901 stop EARLIER (exactly 2.0 / 3.0 calls, 0 strict on every c≥4 cell, s1901 also lost retention); seed 1902 improved (c4/5 ≈ 53–61/64, c6 strict 31–39, c7/8 zero). U5 reproduced [[exp19-replay-result]]'s U arm within ±12. My big forecast miss: P87 (expected U8 to lengthen execution; it shortened it in 3/3). Write-up: artifacts/fable-novelty19b-u8-20260920/RESULTS.md.

**Why:** shows that simply widening the practice mix is not the fix for the call ceiling in [[canonical-operator-roadmap]]; the result is seed-dependent.
**How to apply:** "sparse final-answer reward + per-call cost → learn to stop early" is only a hypothesis (no isolating arm). Next control experiment is designed by a Fable reviewer ([[ask-fable-max-subagent]]), one change at a time (candidates: no call cost; staged 5→6→7→8 curriculum). The ceiling is off the demo's critical path ([[teachable-roadmap-fable-review]]).
