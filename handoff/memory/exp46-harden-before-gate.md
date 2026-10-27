---
name: exp46-harden-before-gate
description: 2026-09-21 Experiment 46 — snapping the sleep router to one chain before the install gate: 15/15 installs at 0/2/4 wrong of 20, 0/15 at 20 wrong, 0 wrong installs in 120, confirmed on fresh seeds
metadata:
  type: project
---

Experiment 46 (follow-up to [[exp45-noisy-teacher]], GPT xhigh's pick): one change — after each CV fold fit and the refit, phi is snapped to its argmax chain before prediction/scoring. Two batches (4102–4106, fresh 4107–4111), 3 words: installs 15/15 at 0, 2 and 4 wrong answers of 20, 0/15 at 20 wrong; 60-start audit 0 disagreements; 0 wrong installs / 120. H1–H5 all PASS, confirmed.

**Why:** Exp 45's rejections were half-converged soft mixtures below the 0.9 answer threshold, not wrong chains.

**How to apply:** this is the sleep recipe to wire into the live loop (robust loss + harden-before-gate + unchanged 0.80/0.90 gate). Open: noise-rate sweep for the fixed 10% allowance; scaling of the soft router to 100+ skills (consider sparse/top-k routing if hardened argmaxes start being wrong). Files: scripts/fable_hardgate46.py, artifacts/fable-hardgate46-20260921/.
