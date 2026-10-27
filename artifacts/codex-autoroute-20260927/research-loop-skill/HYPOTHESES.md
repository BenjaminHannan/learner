# Ranked queue at skill adoption

2026-09-27. Design queue only; no new training or calibration is authorized by this
file. AR2 finishes under its pushed protocol before choosing a successor. These
are locally discussed mechanisms, not claims that any cited paper was replicated.
The linked research notes provide context; full-paper reading must be explicitly
recorded before a paper-derived implementation. No new literature search or full
paper read is claimed in this skill-integration step.

| Priority / status | Mechanism and source | Prediction | Cost and principal failure |
| --- | --- | --- | --- |
| 1 — RUNNING, AR2 | Concentrate existing old-grid replay on grid5; [marks](../hard_replay/PASSMARKS.md) | Preregistered expected grid gain 10–40/200; actual marks unchanged | Same steps and replay counts; harder batches may take longer; grid4 retention untested |
| 2 — UNTESTED | Small learned regional gates on actual AdamW displacement, rewarded for retention and new learning; [draft](../NEXT-CONTROLLER-DRAFT.md) | Reduce old-skill damage without freezing new learning; numerical prediction still needs registration | Controller counts against capacity; fewer than 400 reward events may give inadequate credit; architecture control needed |
| 3 — UNTESTED | Learned choice of replay strata within existing slots; [research](../RESEARCH-CONSOLIDATION.md) | Spend the fixed rehearsal budget where delayed forgetting is greatest | Probe forwards and bandit state must be counted; reward may overfit difficulty or collapse coverage |
| 4 — UNTESTED | Bounded cached-gradient projection on actual optimizer displacement; [review](../PROJECTION-REVIEW.md) | Reduce interference in directions represented by old gradients | Eight vectors per old kind already cost about 100.5 MiB; stale local gradients can obstruct learning without preserving behavior |
| 5 — UNTESTED DESIGN COMPARISON | Fixed mastery anchor versus rolling old-loss reference for the controller reward; [draft addendum](../NEXT-CONTROLLER-DRAFT.md) | Keep gradual cumulative forgetting visible to the reward | Requires a viable controller first; fixed anchors can reward excessive freezing or penalize distribution shift; separate one-change comparison |
| Closed — FAIL (not proved wrong), AR1 | Move old-grid replay later; [checked result](../RESULTS.md) | Registered prediction is preserved in AR1 marks | Measured final grids +28.17/200 and total +30/600; misses M1 and M3; middle-stage damage remains |

This initial queue intentionally contains the concrete existing designs rather
than ten padded variants. After AR2, a research refresh can expand it with distinct
mechanisms and primary-paper evidence. No method is promoted solely because it
fits a brain analogy. A later candidate needs one defined intervention, full
capacity/compute accounting, fresh seeds/panels and pushed PASSMARKS before tests.
