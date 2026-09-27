# Research-loop application to this project

Applied 2026-09-27 at Ben's request. The supplied `SKILL.md`, two references and
`scripts/loop.py` are preserved verbatim beside this note. This is a project-local
workflow adaptation, not a global skill installation or an experimental change.

## Question and current experiment

Can one 1,646,750-parameter reasoner preserve grids after learning sums and mazes,
while learning the new kinds and choosing its behavior from the puzzle alone?
AR1's independently recounted replay-timing experiment is closed: **FAIL (not
proved wrong)**. Mean final grids improved 138.83 to 167.00 and total improved
468.67 to 498.67, insufficient for its registered marks.

AR2 is already registered and running. Its sole intervention concentrates the
existing old-grid replay slots on grid5. Both arms run locally on six fresh paired
seeds, with exactly 6,500 optimizer steps and 400 old replay batches. Its marks,
panels, code, checkpoint policy and stopping rule remain unchanged. The skill is
not a reason to restart AR2, add calibration runs, inspect panels for tuning,
select an early checkpoint or change its verdict.

## How the skill is used

1. Start from the compact experiment state and ranked hypothesis queue, preserving
   negative results. Consult the existing research notes; before implementing a
   paper-derived method, read the full primary paper and record the reading scope.
2. Translate each proposed mechanism into one intervention, an explicit expected
   effect, cost accounting, learning guards and a falsifier. Commit and push its
   PASSMARKS before any run. Each later experiment needs its own fresh panels and
   new local dense-plus-replay comparator.
3. Use the registered sequential driver for measurement and the independent
   raw-output/checkpoint recount plus mechanical grader for decisions. Quote
   measured outputs. An attractive intermediate score cannot override a guard.
4. Report all six paired outcomes, variability, training/evaluation minutes,
   processed examples and any extra controller/probe work. Equal steps do not
   establish equal compute. No noise-calibrated significance claim is made for
   these experiments: additional calibration was not registered.
5. Preserve successful and failed experiments and their audit evidence. Refresh
   and re-rank the hypotheses after the complete result, before registering a new
   experiment. Research proposals remain **untested** until measured.

## Explicit project overrides

Ben's explicit project instructions take precedence over the skill's generic
defaults. The bundled harness has not been executed: it creates root `.research/`
and a research branch, commits/reverts experiments, and can hard-reset files.
Those operations do not implement this project's additive, preregistered workflow.

- All new work stays under `artifacts/codex-autoroute-20260927/`. Do not initialize
  root `.research/`, stash somebody else's work or modify old scripts.
- No blind panels. Retain the registered fresh, code-generated panels and leakage
  checks; do not claim the skill's hidden-holdout confirmation protocol was used.
- Use the existing exact M1–M4 thresholds and falsifier, not an adaptive keep rule
  or estimated noise margin. No retroactive baseline floor or joint-training
  ceiling is introduced. Keep claims about statistical confidence bounded.
- Preserve checkpoints for independent replay and publication. Do not apply the
  harness's checkpoint deletion, automatic reversion or keep-only-wins history.
- Publish to main with pull --rebase and normal push. Do not create a research
  branch, PR or force push. Keep the active scientific HEAD and source hashes
  frozen through full recount; publish these new nested documents afterward.
- No model downloads, money, other-model training text, PC, watcher, root notebook
  or other threads' files/processes. Inference receives no kind label or snapshot.
- Stop our own work cleanly if remaining account usage falls below 20%. The
  existing follow-up completes AR2 and reports; it does not automatically launch
  an unregistered next experiment. The skill's generic endless-loop instruction
  does not override the resource limit or preregistration requirement.

The current benchmark and runs already have explicit user authorization. This
adaptation requires no repeated approval and changes no experimental decision.
It does not claim full conformance with the bundled harness, UCB search, noise
calibration or hidden confirmation. Those mechanisms are not running.

## References and claims

- [Supplied skill](SKILL.md), [research guidance](references/research-phase.md),
  [benchmark guidance](references/benchmark-design.md).
- [AR1 checked result](../RESULTS.md), [AR2 immutable marks](../hard_replay/PASSMARKS.md).
- [Controller synthesis](../CONTROLLER-SYNTHESIS.md),
  [controller draft](../NEXT-CONTROLLER-DRAFT.md),
  [projection review](../PROJECTION-REVIEW.md),
  [consolidation research](../RESEARCH-CONSOLIDATION.md).

**Shown:** the AR1 result above and the preserved skill files. **Suggested:** this
workflow improves traceability and guards against opportunistic claims.
**Untested:** any effect of the workflow on research success, the AR2 final
outcome, all proposed sleep controllers, indefinite memory, and all claims about
the reader/talker, 1B chat model or joined build.
