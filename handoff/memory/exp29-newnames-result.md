---
name: exp29-newnames-result
description: 2026-09-21 experiment 29 new names with 10,000 updates — registered PASS 3/3 (fixed scale 1.2); 6,000-update and learned-scale arms only 1/3; open-set still ~0.6
metadata:
  type: project
---

Experiment 29 (M1-F10): one change from [[exp27-newnames-result]] — 10,000 updates (LR 1e-3 held to 7,999). Fresh seeds 2106–2108, fresh panels. Arm F (fixed name scale 1.2) PASS 3/3: all ten cells 496–512/512, worst paired gap −11 (limit −13), control 3/3, integrity clean. Descriptive arms: F6 (27's 6,000 recipe) 1/3 and L (learned scale, drifted to ~0.7) 1/3, both failing only the paired mark. F makes 65–68 misses/5,120 vs F6 134–185. Open-set over all 4,096 codes still 0.57–0.60. `undertraining_supported` missed by one question (2.54% vs 2.5%) → label unclear.

**Why:** 27's 2/3 was stopping too early; fixed scale is the dependable recipe, learned scale is weaker at long training.

**How to apply:** may say "binds never-seen names 3/3 in 16-candidate worlds with fixed scale 1.2 + 10,000 updates"; never "open-vocabulary". No independent audit (GPT bridge failed 3×; see [[subagents-gpt-xhigh]]) — disclose. The wrapper scripts/fable_newnames29.py has a descriptive-overlay bug (nulls); fix before reuse. Next = scale until it breaks (16+ person worlds, open-set), fresh registration. Results: artifacts/fable-newnames29-20260921/RESULTS.md. M1 of [[teachable-roadmap-fable-review]].
