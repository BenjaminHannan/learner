# Source-gate failure: Astra review

Recorded 2026-09-28T02:34:09Z from `date -u`. Ben authorized one GPT-6 Astra
subagent (Kuhn) to review the failed source gate and recommend a next test.
This was a read-only review of completed seed 927401. Seed 927402 was still
training. The reviewer edited nothing and ran no training, inference, or maze
scoring. This document records advice, not a new registration or a race result.

## Shown

| Arm | Learned-stop grids | Fixed-48 grids | Required |
|---|---:|---:|---:|
| Patch | 278 of 300 | 288 of 300 | 285 of 300 |
| Ordinary loop | 274 of 300 | 281 of 300 | 285 of 300 |
| Episodic loop | 282 of 300 | 288 of 300 | 285 of 300 |
| Plain | 164 of 300 | 164 of 300 | 285 of 300 |

All four arms pass their other five kinds. The patch is within nine answers of
both own loop controls on every kind. Fixed-48 evaluation recovers ten patch,
seven ordinary-loop, and six episodic-loop grid answers, with no correct grid
answer lost in those pairs. The patch's ten recovered cases stopped at rounds
6–12. Those saved-trajectory facts show a stopping contribution for the loops.
The plain model has no stop head and still fails badly, so stopping alone
cannot qualify the complete comparison. No maze advantage, retention after
supports, or sleep absorption is shown.

## Suggested, not established

Insufficient source exposure is a stronger single intervention to test than
stop calibration. Uniformly sampling six kinds for 18,000 batches gives an
expected 3,000 batches per kind. The ruler's subsequently registered 12,000
batches across two kinds give 6,000 per kind. Doubling this experiment's
supervised budget would match that expectation while preserving the wider
curriculum for all arms. These are expected draws, not exact quotas or unique
examples. The ruler's development evidence does not prove this budget will
qualify our models. Source interference and loss of grid competence during the
2,000 episode stage remain possible because this run lacks a separately scored
pre-episode model. A single seed does not establish patch superiority.

## One proposed source-only experiment

Compare **18,000 versus 36,000** supervised batches of 64 from scratch for
all four arms and both paired seeds: 16 model runs. Keep the six kinds,
architecture, 2,000 episode objective, round sampling, losses, learned stop,
and the existing Test A bars. Seal code, seeds, schedules, development panels,
fresh untouched 300-item verification panels, source guard, and decision rules
before training. Use the same puzzle sequence for each pair's shared
supervised prefix. Separate and seal the episode-example and round RNGs so
the two budgets see identical episode evidence; the current trainer's shared
RNG would otherwise advance farther in the 36,000-batch arm. Score and report
pre-episode *development* panels and final verification panels, without using
verification results to choose the budget.

The falsification criterion for “36,000 batches alone restores full source
eligibility” is **any** 36,000-batch arm in either seed below 285 of 300 on
grids. Sums retain 285 of 300; the four extras retain 270 of 300; the patch
must remain within nine of 300 of both loops for every kind. The ruler's
separate 190-of-200 guard remains. A partial improvement is still a failed
eligibility claim. The test does not score mazes. Success would support the
sufficiency of a longer recipe; the changed cosine schedule means it would
not isolate raw exposure from learning-rate history.

For Ben: The patch sometimes quits early, but all four models also struggle
with grids under this source budget. Test a larger, equal practice budget for
all four on untouched puzzles before drawing any conclusion about maze
learning. No change to the registered run follows from this review.
