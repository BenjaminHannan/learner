---
name: exp45-noisy-teacher
description: 2026-09-21 Experiment 45 — noise-tolerant sleep loss: 10%-wrong teacher installs 10/15 (plain 0/15), 0 wrong installs; enumeration shows signal is fine, optimiser/gate weak
metadata:
  type: project
---

Experiment 45 (follow-up to [[exp44-reasoner-skills-router]]): one change, sleep loss −log p → −log(0.9p + 0.1/N), paired arms, seeds 4102–4106, 3 words. N1 safety PASS (0 wrong installs in 150 runs), N2 clean PASS 15/15, N3 FAIL (robust installs 10/15 at 2-of-20 wrong answers; plain 0/15), N4 nonsense PASS 0/15. Post-hoc measurement: scoring all 729 hard chains with the same likelihood picks the true word 15/15 at 2, 4 and 6 wrong, margin 3.5–4.7 nats/episode.

**Why:** the signal survives 30% label noise; rejections come from the soft router's optimiser in small CV folds and a gate scored against noisy labels.

**How to apply:** next single change should target the optimiser/gate (e.g. harden the routed chain before gating, or gate on robust likelihood instead of exact match) — get a GPT xhigh design review first; enumeration stays a control only (does not scale). Files: scripts/fable_noisyteacher45*.py, artifacts/fable-noisyteacher45-20260921/.
