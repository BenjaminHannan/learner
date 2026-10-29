# Durable gate-finalization binding

A grader revision invalidated resumed training/gate baselines, but a saved `finalize` or `done` pass could bypass those checks and promote under its obsolete decision. The new binding closes that path without changing `gate.GRADER`, `correct`, `recall_hit`, the independent monitor, or any preregistered raw experiment report.

New finalizations contain `version: 1`, the current grader revision, and the exact night ID. `_finalize` validates the result/state/extra payload and its linked night/date/day/count before replay. It then accepts a current binding, a validated exact already-committed adapter identity, or a saved rejection that cannot promote/export. All `finalize`/`done` entries use this central guard, including missing payloads.

An uncommitted pass with a missing/stale binding returns `status: stopped`, `quiz: null`, `interrupted: true`, `blocked: true`, `stop_reason: gate_recheck_required`. No promotion, export, state/items/history write, or checkpoint cleanup occurs. Candidate weights, immutable checkpoints, item flags and journal bytes remain unchanged. Legacy passes need an explicit re-gate with comparable base-general and unchanged-incumbent recall baselines. Automatic migration is deliberately absent because legacy passed decisions changed item training flags before saving without preserving their original state.

`Checkpoints.is_committed` is read-only: it requires an integer manifest version, exact valid night ID, exact `adapters/<night-id>` manifest target, and required adapter files. A destination directory left at `promotion_ready` does not prove publication. Malformed or unprovable committed identities cannot bypass the guard.

Valid already-committed completions remain idempotent after a grader upgrade. Valid saved rejections also finish after a missing/obsolete binding: the rejection branch cannot promote/export, and its prior gate did not mark new items trained. These are completion paths for the saved outcome, not new approvals under an old grader.

Validation:

- Nine focused binding tests pass in **5.165 seconds**, using only synthetic fake backends and isolated temporary paths.
- They cover missing/wrong version, boolean version, wrong grader, missing/wrong identity; `finalize`, `done`, and export-marked uncommitted states; direct calls; missing/malformed payloads even with a committed manifest; grader change after `promotion_ready`; and completed promotion replay at `promotion_published`, state/items/history/finalized boundaries.
- Saved rejections are hard-exited at rejection-ready/state/items/history/finalized boundaries under unchanged and upgraded graders. Tests assert no promote/export, one state/history completion, and exact preservation of mixed already-trained/pending item flags.
- Before the rejection refinement, 56 focused binding/learning-correctness/sleepcheck/served-recovery/private-HTTP tests passed in 7.46 seconds. Root will run the full Python suite once its active MPS experiment restores the compute slot.
- The separate frozen audit reproduces 81 strict-3 observations in four pure tests. Original raw report hashes remain unchanged.

Source files: `sleepmlx/recipe.py`, `sleepmlx/checkpoint.py`, `sleepmlx/tests/test_finalization_binding.py`, and the finalization paragraph in `sleepmlx/README.md`. No commit or deployment was performed by this subtask.
