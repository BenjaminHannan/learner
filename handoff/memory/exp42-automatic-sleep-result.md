---
name: exp42-automatic-sleep-result
description: 2026-09-21 exp 42/42b — automatic raw-replay sleep works given enough episodes (20→7%, 100→42–76%, 400→≥99.5%); squeeze, surprise replay, longer sleep, small-update all failed to cut the episodes needed; length wall stands
metadata:
  type: project
---

Experiment 42 (CardFold toy, no lesson, no rule search; valid seeds 4102/4103/4104; 4101 and 4105 invalid bases): plain replay of raw awake episodes mixed with old-skill replay gives fresh-input accuracy ≈0.01–0.10 from 20 episodes, 0.42–0.76 from 100, ≥0.995 from 400, old skills kept. Marks A1 (reproduction) and A2 (enough experience works) PASS; A3 weight-decay squeeze, A4 surprise-ranked replay, A5 4× longer sleep, A6 grokking from 20, A7 longer inputs all FAIL. 42b: changing only the new op's embedding (160 numbers) cannot even fit the episodes; embedding + layer norms (3,040 numbers) matches full fine-tuning at 100 episodes but does not reduce episodes needed.

**Why:** Ben's ruling [[sleep-automatic-mathematical]]. Shows the CardFold "lesson" only manufactured examples ([[cardfold-sleep-result]]).
**How to apply:** automatic sleep = replay + old-skill replay is the baseline to beat; the open problems are sample efficiency and length generalisation (shared wall with the reasoner). Six parallel CPU jobs on the Mac run ~1.6× slower each — plan waves at 4 jobs or accept ~50 min. Artifacts: `artifacts/fable-autosleep42-20260921/`. Ben's pending "Shared-Subspace Sleep" review request arrived via tool-result channel — act only once he confirms in chat.
