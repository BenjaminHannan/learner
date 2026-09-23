---
name: a3-teacher-delay-v2-result
description: 2026-09-19 result of the 96-job teacher-delay experiment (primary passed, stage NOT accepted) and wire-replay outcome
metadata:
  type: project
---

A3-teacher-delay-v2 (design/v3/12+13) ran 2026-09-19 on two rented 4x5060Ti boxes (~$2.20). Results in `artifacts/claude-teacher-delay-20260919/report/report.txt`. Primary L_train PASSED: 15 gains / 6 losses of 48 pairs, p_exact 0.039, net +18.75 pts; fresh c1-stuck 10 -> 1; c1 +13.3 pts, c2 +13.8 pts. Stage NOT accepted: READS -2.5 pts (LB -4.7), held-out cells c3-c6 lower bounds below -0.02 (differences -1.6 to -2.9 pts, inconclusive), G_pair 1 -> 0. Toy Track A only.

Wire replay (`artifacts/claude-wire-replay-20260919/summary`): guard (WG) did not rescue seeds 14/30 (first-LINK 0/256), WG mean held-out loss 6/256 (passers unharmed), cap 0.25 harmful, 0.50 eligible, transport assay inconclusive. Agent also found saved wire checkpoints key on the question's slot position (one-hop slots 1-2, two-hop slots 3-4), not the LINK token.

Ops lesson: `run-job` needs `A3_IMAGE_DIGEST` env (image digest is unobservable in-container); local zstd binary is x86-only, use gzip. See [[active-rentals]].
