---
name: overnight-loop-directive
description: "Overnight standing orders — 2026-09-19: fix failures, scale what works; 2026-09-21: after the planned list clears (before 7 am 2026-09-22), test the model, find issues, patch them, repeat"
metadata:
  type: feedback
---

2026-09-19: "fix failures; if it works scale until it breaks, fix, repeat; I may finish Astra's builds myself."

2026-09-21 22:25 (Ben): "If you happen to finish before 7am tomorrow, you should just find ways to improve the model. So test it, find issues, then patch the issues."

**Why:** Ben is asleep; idle agents are wasted; he wants a better model in the morning, not a waiting director.

**How to apply:** when the director board's Running/Next-up lists are empty, dispatch TEST agents (adversarial English turns, long inputs, paraphrases, corrections, typos, hearsay, multi-hop, abstention traps) against the wired loop; each confirmed issue → one PATCH agent (additive wrapper, sealed marks, re-test); log every issue + fix on the board under "Overnight fixes" with integer counts before/after. Never re-run a registered FAIL into a pass; patches get new experiment numbers. Report in the morning result-first: what broke, what was fixed, what still breaks. Related: [[director-role]], [[gpu-only-5070ti]].
