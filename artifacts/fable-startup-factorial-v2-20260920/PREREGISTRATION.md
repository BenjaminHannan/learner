**Start-up factorial v2 — preregistration · 20 September 2026 · Track A validation only**

This file restates the fixed numbers of
`/Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/18-startup-factorial-v2-preregistration-draft.md`
(the spec, which governs) and records the scheduling decisions the spec left open. The
frozen v1 experiment is untouched: new source, new tests, new manifest, new output folder.
`plan` hashes this file into `launch.json`, so nothing below may change after the freeze.

**Question.** At fixed questions and supervision, does adding eight fact rows, adding
filler-only/gap rows, or their interaction change learning within 2,500 updates? This does
not by itself establish the microscopic gradient mechanism.

## Fixed numbers

| Arm | Fact rows | Filler-only/gap rows |
| --- | ---: | --- |
| A | 16 | none |
| B | 16 | all |
| C | 24 | none |
| D | 24 | all |

D is "full context with subset-selected questions", not e0. Historical e0/grow-blind runs
are context, not matched controls.

- Seeds 1300, 1301, 1302. Namespaces `astra-startup-factorial-v2-world:seed` and
  `astra-startup-factorial-v2-plan:seed`; one world stream and one subset/question stream
  per seed, shared by all four arms and drawn before any arm is chosen.
- Within a seed, question tokens, answers, record weights, support facts, model
  initialization, world draws and the optimizer schedule are identical across arms;
  inline filler inside a kept fact row is retained in every arm.
- 79,316-parameter rescaled canonical operator, 16 worlds/update, canonical/monolithic
  loss 0.75/0.25, AdamW (lr 1e-3, betas 0.9/0.99, eps 1e-8, weight decay 0.1), clip 1.0.
- Learning rate: warm up to 1e-3 over 100 updates, then hold 1e-3 for all 2,500 updates.
  No context growth.
- Onset: a fixed 512-question attribute-only validation probe from its own namespace,
  scored at updates 0, 50, …, 2500. First qualified onset = the earliest t ≥ 200 whose
  five scheduled probes t−200, t−150, t−100, t−50 and t are all present and each ≥ 461/512.
  Missing probes never qualify. First onset, later regressions and final-window status are
  recorded separately. At the final update a second untouched 512-question probe is scored;
  ≥ 461/512 makes onset "independently confirmed in that condition". This is an operational
  threshold, not literal first learning and not a reliability certificate.
- Routing diagnostics every 50 updates on a small fixed probe whose question plan is shared
  across arms and separately excluded: raw and uniform-normalised correct-line mass by each
  of three reads and four heads and by question-token position; unrounded double-precision
  gradient inner products, norms and cosines for the attribute, LINK and monolithic
  components and for their registered 0.75/0.25 sum; the analytic plain-SGD derivative
  validated by central finite differences at eta = 1e-3, 1e-4 and 1e-5 on disposable
  copies; and, separately, one hypothetical AdamW update on a disposable copy of the model
  *and* the optimizer state with an independent training-distribution batch, with the live
  training state asserted byte-identical afterwards; prediction distributions for attribute
  and LINK separately, plus per-relation answer accuracy.
- Exclusions: for every training record the audit hashes five conditions — the full source
  story and each arm's reduced presented story — against a union frozen before the first
  update (the registered v1 exclusion set, both validation probes, the routing probe and
  every transfer cell). A collision raises and invalidates the run; a record is never
  silently skipped, because skipping would change the frozen RNG stream.
- Freeze-before-growth transfer of each seed's final arm-A checkpoint, with no updates:
  six-person cells 16/24 facts × filler 0/0.5/1 and sixteen-person cells 16/24/64 facts ×
  the same filler fractions (including the genuine full 64-fact world), 512 paired units
  per cell, one question per unit fixed across all of that unit's cells, pass ≥ 461/512.
  Checkpoint fingerprints are verified before and after.
- Long run, a separate question: arm D from initialization for 18,000 updates, warmup 100,
  flat to 16,000, linear decay to 1e-4 at 18,000; its own frozen 6,000-update checkpoint is
  compared with the 18,000 checkpoint. An extension under a declared schedule, not a
  continuation of historical e0.
- Capacity: at most three audit-experiment workers and at most six total registered
  training workers, counted as worker processes; each resumable chunk ≤ 1,200 seconds; a
  capacity refusal is a scheduling result (exit 3), not a model failure. The default
  command never spawns a wave.
- Reporting: every seed and arm separately, never averaged; paired filler effects B−A and
  D−C, fact effects C−A and D−B, and their interaction, on onset and on final/512, with
  censoring shown rather than dropped. Statements stay conditional on these sizes and this
  budget.

## Fable's predictions

*(intentionally empty until the predictions are written in, before any registered run)*

## Commands, in order

Run from `/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`
with `PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12`
and `export OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`.

```
# 0  checks (5 s, disposable seeds only)
$PY -B tests/test_fable_startup_factorial_v2.py

# 1  freeze the plan: probes, exclusions, transfer cells, cross-arm audit, launch.json
$PY -B scripts/fable_startup_factorial_v2.py plan --seeds 1300,1301,1302

# 2  wave 1 - arm D, three seeds (3 workers)
for s in 1300 1301 1302; do $PY -B scripts/fable_startup_factorial_v2.py \
    train --arm D --seed $s --budget-seconds 1100 & done; wait

# 3  wave 2 - arm B, three seeds
for s in 1300 1301 1302; do $PY -B scripts/fable_startup_factorial_v2.py \
    train --arm B --seed $s --budget-seconds 1100 & done; wait

# 4  wave 3 - arm C, three seeds
for s in 1300 1301 1302; do $PY -B scripts/fable_startup_factorial_v2.py \
    train --arm C --seed $s --budget-seconds 1100 & done; wait

# 5  wave 4 - arm A, three seeds
for s in 1300 1301 1302; do $PY -B scripts/fable_startup_factorial_v2.py \
    train --arm A --seed $s --budget-seconds 1100 & done; wait

# 6  freeze-before-growth transfer of the final arm-A checkpoints (no updates)
for s in 1300 1301 1302; do $PY -B scripts/fable_startup_factorial_v2.py \
    transfer --seed $s; done

# 7  long run - arm D, 18,000 updates, three seeds, ONE chunk each per round.
#    Repeat this round until each seed prints "complete": 3 rounds are expected.
for s in 1300 1301 1302; do $PY -B scripts/fable_startup_factorial_v2.py \
    longrun --seed $s --budget-seconds 1100 & done; wait

# 8  report (per seed, per arm, never averaged)
$PY -B scripts/fable_startup_factorial_v2.py report --seeds 1300,1301,1302
```

A `train`/`longrun` command that prints `INCOMPLETE` is rerun verbatim; it resumes from the
saved model, optimizer, both data streams, the torch RNG, the data cursor and the recorded
diagnostics, and the resumed trajectory is bit-identical to an unchunked one (checked in
`tests/test_fable_startup_factorial_v2.py --only resume`). `check-manifest` runs inside
every training command; a changed registered file aborts the run.

## Measured throughput and the wave plan

Measured on this Mac (10 cores: 8 performance, 2 efficiency) on 20 September 2026 with
disposable seeds 9980/9981/9982 and the registered settings (16 worlds/update, the
five-condition signature audit, the 512-question validation probe and the full routing
diagnostics every 50 updates), while the machine was already carrying other work
(load average ≈ 7). Each job is one thread. Outputs were deleted.

| Arm | updates/s, 6 jobs | updates/s, 3 jobs | 2,500 updates at the 3-job rate |
| --- | ---: | ---: | ---: |
| A | 12.15 | ~14.5 (scaled) | ~2.9 min |
| B | 6.44 | 7.68 | ~5.4 min |
| C | 9.57 | 11.64 | ~3.6 min |
| D | 5.55 | 6.63 | ~6.3 min |

The 6-job columns are two independent measurements per arm for A and D (12.15/12.14 and
5.55/5.53), so the numbers are repeatable to about 0.5%. Arm A was not re-measured under
3-job load; its 3-job rate is scaled from arm D's 6→3-job ratio and is used only to bound a
wave that is already the shortest.

**Waves.** The spec caps audit-experiment workers at three, so each wave is three one-thread
jobs, one seed each, and the whole factorial is four waves. Every factorial run is a single
chunk well under the 1,200-second cap, and every wave is far under 30 minutes:

| Wave | Jobs | Expected wall clock |
| --- | --- | ---: |
| 1 | D × {1300, 1301, 1302} | ~6.3 min |
| 2 | B × {1300, 1301, 1302} | ~5.4 min |
| 3 | C × {1300, 1301, 1302} | ~3.6 min |
| 4 | A × {1300, 1301, 1302} | ~2.9 min |

Total factorial compute ≈ 18 minutes of wall clock over four waves. The transfer step is a
scoring pass over 15 cells × 512 units with no updates, a few minutes per seed.

**Long run.** 18,000 arm-D updates at 6.63 updates/s ≈ 45 minutes per seed, so each seed
needs three chunks of ≤ 1,100 seconds. The three seeds run together as three workers, so
the long run is three rounds of ~18, ~18 and ~9 minutes — each round under 30 minutes, each
chunk under the 1,200-second cap.

## Decisions the spec left open (registered here)

1. **Long-run seeds.** The spec fixes arm D and 18,000 updates but not how many seeds. All
   three registered seeds are run, after the factorial waves, with the schedule fixed in
   advance and no seed chosen on the basis of any earlier validation result.
2. **Long-run routing cadence.** The validation probe stays on the 50-update grid; the
   expensive routing diagnostics (deep copies, central differences, a hypothetical AdamW
   step) run every 250 updates in the long run. The spec's "every 50 updates" is stated for
   the 2,500-update factorial.
3. **Validation-probe construction.** Each of the 512 units is one world with one
   attribute-only question drawn from that world's label-free 16-fact core, so the question,
   the answer and the supporting row are identical in all four arms while the presented rows
   follow the arm — the spec asks for matched questions/worlds and for onset to be confirmed
   "in that condition".
4. **Probe scoring mode.** Probes are scored with the model in eval mode; the architecture
   has no dropout or batch norm, so this changes no number.
5. **Central differences** validate the derivative of the registered 0.75/0.25 objective
   (the loss actually trained); the component gradients are reported as inner products,
   norms and cosines but are not separately finite-differenced.
6. **Filler fractions** of 0.5 keep `round(0.5 × filler rows)` rows, taken from a fixed
   random order per unit, so the cells are nested by construction.
7. **Chunk budget** defaults to 1,100 seconds in the commands above, under the 1,200-second
   cap; `train`/`longrun` refuse any `--budget-seconds` above the cap.
8. **Worker counting** matches a python process whose command line runs a repository
   `scripts/*.py` with one of the verbs train/longrun/worker/wave/extend/supervise; `ps`
   output is read as data and never executed.

## Known limitations, stated before the runs

- `A.visible_signature` hashes the sorted 4-token fact tuples plus the visible question, so
  **filler rows do not change a signature**. Arms A and B therefore share a presented-input
  signature, as do C and D, and transfer cells that differ only in filler share one. The
  reduced-input audit distinguishes fact-set reductions, not filler reductions; the full
  source story is audited as well. This is exact task-semantic identity over named tokens,
  not alpha-equivalence.
- FLOPs are not counted. Updates, wall time, updates/second and peak RSS are recorded; the
  frozen training code has no FLOP counter and none was added.
- The frozen v1 `ARMS` table carries the note "the full story (= e0)" for arm D and is
  reproduced verbatim in `launch.json` because v1 is imported unedited. The spec rejects
  that equation, and no v2 text, table or reading treats D as e0.
- A positive derivative in all arms would not refute dilution, a flat average final-token
  mass would not prove that no head or position learned retrieval, and temporal association
  between a diagnostic and onset is not a causal proof.
