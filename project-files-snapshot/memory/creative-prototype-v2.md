---
name: creative-prototype-v2
description: Creative prototype redo (10-03, PR #21): make-the-target puzzles, sampled call heads, placebo R, twin-target aiming test, stop gate before T1
metadata:
  type: project
  modified: 2026-10-03T15:42:45.027Z
---

Thread cmsg_01GSLCHTCnZxn7DhV19qcDvMXb95NYx3QaFBa1KiEKELrr, PR #21 (design/next-parts/creative-prototype.md v2 plus creative-prototype-notes/), explainer https://claude.ai/artifact/SmPYEtUGwLrXixB7CifczJ. Ben asked at 14:16 UTC 10-03 for a thorough redo. Five Opus passes went into it (critic, fresh design, CPU maths, check, re-check). Design only.

- Shown in code: calls are chosen by argmax heads before the LM decodes, so LM temperature can't vary solutions. A candidate is a 4-loop call trajectory, varied by sampling the heads.
- Word problems give search nothing to do: about 2 usable results, and finals come from the 27-number shelf (PR #23 F1). So v2 uses make-the-target puzzles (3 numbers, 2..40, add/sub), checked without a key. The uniform floor is 0.544% per try. A rules-only floor is 14.4 to 25.7%, which is why there is a twin-target aiming mark G0.
- Arms: N (none), W (own accepted), R (rule-valid, value-blind placebo), PC (solver control). Each has 3 seeds (5 if the S0 power check fails), with seed-level t intervals.
- Verdicts 2 and 3 (cold start, placebo too close) are decided at the end of S3, before T1 is opened.
- Flags D1, F1, F3 to F9 were taken under the autonomy note. F9 is gold-call training on 2,048 new word problems, used only for the Q2 persistence block.
- GPU estimate: about 2.5 to 4 h, plus 1 to 2 h for Q2, plus a replication. Nothing has run. The CPU stage S0 can start any time.

**Why:** Ben wanted the design "as good as it can be" before anything runs.
**How to apply:** don't run GPU stages ahead of the English pilot and the curriculum. Ben can overrule the flags before PASSMARKS is sealed. Related: [[critical-thinking-reasoner-design]].
