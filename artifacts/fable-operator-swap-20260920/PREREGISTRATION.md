# Frozen operator swap — development replication (written 2026-09-20, before any swap was scored)

Registered from [18-validation-and-operator-swap-v2-preregistration-draft.md](/Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/18-validation-and-operator-swap-v2-preregistration-draft.md) and section 5 of [18-audit-before-fable-continues.md](/Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/18-audit-before-fable-continues.md). Scorer: [scripts/fable_operator_swap.py](/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/scripts/fable_operator_swap.py), sha256 `0104c7ae567bdb64e2fb9559fa4a3e99a342d81aac002db45989ba2847f936d2`, additive: it imports [fable_dispatcher_v3.py](/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/scripts/fable_dispatcher_v3.py) (`8fa4674d1b1dbcad5ae4fe51f4bfe74fe3fb6be3361569b825a4183be3aa8d53`) and [fable_dispatcher.py](/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/scripts/fable_dispatcher.py) (`2081a94cae4f3d152230e86d58772d4c5aeabdb03dac46be5efff85fefa91545`) and edits no registered file.

**What is being asked.** Do the three primary v3 dispatchers, which were trained against the ORIGINAL hinted operator, still execute correctly when their lookup tool is replaced by a grow-blind operator trained without supporting-line loss? No retraining, no operator selection, no seed substitution, no checkpoint selection. The pieces are frozen; only the pairing is new.

**The three predeclared pairings.** Dispatcher seed i is paired with operator seed i; nothing else is permitted.

| Pair | Dispatcher (v3 rl-cost01) | sha256 | Replacement operator (grow-blind) | sha256 |
| --- | --- | --- | --- | --- |
| 0 | `rl-cost01/seed-0/dispatcher.pt` | `2425c52dc1b44447…` | `astra_canonical_operator_seed-0/final.pt` | `db40c2452ea31fe9…` |
| 1 | `rl-cost01/seed-1/dispatcher.pt` | `422f04f0587431a5…` | `astra_canonical_operator_seed-1/final.pt` | `c02c12d64319aae5…` |
| 2 | `rl-cost01/seed-2/dispatcher.pt` | `fd2feff974dfdd7d…` | `astra_canonical_operator_seed-2/final.pt` | `ed498799fba6ce82…` |

All six full hashes, both architectures, the panel-file hashes and the source hashes are written to `manifest.json` by `fable_operator_swap.py freeze` BEFORE any scoring, and `run` re-verifies every one of them and aborts on any mismatch. All three dispatchers were historically trained against `astra-canonical-operator-screen-20260920/astra_canonical_operator_seed-1/final.pt` (`e7e5b6f3a6bfecf3…`), which is the hinted operator; that is recorded per pair as `dispatcher_training_operator`.

**Panels and status.** The 25 existing v3 cells, 64 units each, at `artifacts/fable-dispatcher-v3-20260920/panels`, manifest sha256 `5c9b4507cf4197beccd933d2cb27b424cbbec13bdbb0f774d8b3bd9ca83867e7`. These are DEVELOPMENT benchmarks: v3's recipe, call cost, seeds and checkpoint rule were chosen with their outcomes visible. This screen is therefore registered as a **development integration replication**, not as confirmation and not as an untouched test. Confirmation is a separate, later, once-only read on the fresh suite registered in [fable-confirmation-panels-20260920/PREREGISTRATION.md](/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-confirmation-panels-20260920/PREREGISTRATION.md).

**Execution conditions, all unchanged from v3.** Greedy (argmax) episodes from the final fixed checkpoints only; the v3 supplied features (token, source flag, most-recent-result flag, the two clipped relative offsets) with the checkpoint's own ablation flags; full-vocabulary operator argmax; evaluation cap 16 calls; no retries, no beam search, no forced actions, no altered stopping; an episode that reaches the cap without stopping is `over_cap` and counts as a failure; an illegal action is `invalid_action` and counts as a failure. Units where the replacement operator is wrong are never discarded.

**Pass marks.** Per cell and per pairing, on the replacement operator: **answers ≥ 58/64 AND strict path ≥ 58/64 AND unit pass ≥ 58/64**. 58/64 is the ORIGINAL registered mark ([fable_dispatcher_v3.py:107](/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/scripts/fable_dispatcher_v3.py#L107)), not the subsequently observed 59/64. Strict path = subjects, operations, stop point and every returned token equal the true chain, with a voluntary stop. A pair unit counts only when both twins are correct, and additionally identical on the invariant (irrelevant-edit) cell. A pairing passes only when all 25 cells pass; a missing pair, a missing cell or any integrity failure means the registered screen did not pass. Every seed is reported separately: no averaging, no best-seed replacement, no pooling.

**The reporting defect this fixes.** `fable_dispatcher_v3.py score --operator X` really does change which operator native execution calls ([native rollout, line 1183](/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/scripts/fable_dispatcher_v3.py#L1183)), but it then copies `operator_chain_hits` from the panel file and `frozen_operator_on_true_chains` from the panel manifest ([line 1319](/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/scripts/fable_dispatcher_v3.py#L1319)); both were computed with the original hinted operator. Those fields never enter the executor, so native answers were not corrupted — the defect is mis-attribution, not contamination. This scorer removes both fields from the loaded panels before scoring (`strip_stale_diagnostics`, recorded as `stale_panel_diagnostics_dropped: 25`) and recomputes every chain audit by calling the exact loaded operator (`operator_calls`), keeping each call's predicted token. The recomputed audits are written to `pair-N/operator_chain_audit.json`, keyed by operator SHA-256, cell and side. The registered panel directory is opened read-only and is never written to; a test re-hashes all 27 panel files after a scoring run.

**What is recorded.** Per pairing: `scores.json` (before/after dispatcher and operator fingerprints, checkpoint and panel hashes, per-cell answers/strict/loose/unit-pass/identical-twins/answered/over-cap/invalid/mean-calls under both the replacement operator and the oracle control, the recomputed chain audit, the per-metric marks and the cell verdict), `transcripts.json` (every native transcript and pointer sequence), `operator_chain_audit.json` and `failures.json` (every failing unit with its native transcript, its recomputed per-call operator errors and the oracle-operator execution of the same input). `run_meta.json` records the pairings scored and whether the screen passed.

**If a pairing fails.** Report it; do not retrain first. The report prints the oracle control beside the native column for each failing cell — a cell that passes under the oracle and fails natively is an OPERATOR failure, a cell failing under both is a CONTROLLER failure — plus the per-call operator errors (entity, operation, predicted token, true token) and the native transcripts of failing units. Any dispatcher retraining is a separately registered adaptation experiment and cannot rescue the claim that the frozen pieces were compatible.

**Claim scope, on success.** A passing screen establishes **deployment with an operator trained without supporting-line loss**, on this validation distribution, for these three frozen pairings, at these marks. It does **not** establish a hint-free training history: the reused dispatcher was trained against a hinted operator. It does not establish a label-free system: grow-blind removes supporting-line loss and label-informed line selection but still trains gold intermediate people as LINK answers, and the v3 bookkeeping features (candidate tokens, source flag, most-recent-result flag, relative offsets), the canonical query interface and the entity/operation validation remain supplied throughout. The stronger claim — that no supporting-line hint occurred anywhere in training — requires new dispatchers trained against fixed grow-blind operators from the first update, with unchanged v3 settings and a separately frozen fresh stream and confirmation suite. A successful swap does not replace that experiment.

**Uncertainty.** Three pairings are a screen, not a reliability certificate. Even a clean 3/3 over 25 correlated cells leaves a wide interval on any population success rate, and the cells share worlds, a generator and an interpreter. Report per-cell counts with uncertainty and the paired gains and losses against the original operator, never "nearly guaranteed".

**Development replication check already run (not a registered reading).** With the ORIGINAL operator `e7e5b6f3a6bfecf3…` and dispatcher seed 0, this scorer reproduces the registered v3 `scores.json` exactly on all 25 cells — answers, strict, loose, unit pass, over-cap and invalid all identical — in about 40 s. That is a re-score of already-seen development panels and fixes the scorer's own calibration only.

**Resource rules.** One process at a time while Mac training waves are active; `torch.set_num_threads(1)`, `OMP_NUM_THREADS=1`. Projected cost: about 40 s per pairing, about 2 minutes for all three, single process.

**Commands.**

```
PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12
W=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
OUT=$W/artifacts/fable-operator-swap-20260920
cd $W
OMP_NUM_THREADS=1 $PY -B scripts/fable_operator_swap.py freeze --out $OUT
OMP_NUM_THREADS=1 $PY -B scripts/fable_operator_swap.py run   --out $OUT
OMP_NUM_THREADS=1 $PY -B scripts/fable_operator_swap.py report --out $OUT --write
```

## Fable's predictions

Written 2026-09-20 by Fable before freeze. I have not seen any swap score (the build agent disclosed reading the grow-blind operator on three development cells while
testing report paths; it did not report those numbers to me). Known: grow-blind operators are 512/512 on their own ten cells (≤ 3 hops, ≤ 12 people); they have never
been run on 16-person worlds or chains longer than 3. The hinted operators were perfect to 10 hops / 16 people in 2/3 seeds.

| id | forecast | p | falsified by |
|---|---|---|---|
| P39 | all three pairings clear all 25 cells (answers, strict, unit-pass ≥ 58/64) | 0.55 | any pairing misses any cell |
| P40 | if a pairing fails, the failures are operator lookup errors on 16-person stories (oracle-operator execution passes), not dispatcher errors | 0.75 | a failing cell that still fails with the oracle operator |
