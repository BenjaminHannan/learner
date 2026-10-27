# Experiment 27 / M1-F — build notes

**"New names" with the name-code scale frozen at 1.2.** Built 2026-09-21. Nothing
registered has been trained, scored or generated: this folder contains the code, the
launchers, the fixture evidence and these notes. The registered panels are built at
launch by `run_data.sh`, as the design asks.

Binding design: `design/v3/27-new-names-followup-design-fable-review.md`
sha256 `63d2bb51c412336fd54bdcc5d012a7da9ac01ae4d01ff2b52497a95052c5d990` (verified before
the build started and again at the end — unchanged).

Parent experiment: `artifacts/fable-newnames21-20260920/` (pool, panels, runs, AUDIT-21).

## Files written

Hashes as of the AUDIT-27 fixes (2026-09-21); the first-build hashes the audit checked
are in the right-hand column.

| file | sha256 | at first build (AUDIT-27 §1.1) |
| --- | --- | --- |
| `scripts/fable_newnames27.py` (1,495 lines) | `69d54c04fdb54172ea737a4ecf0c316d7e3b5056dac4c20e3494b075f14f1530` | `688ad94c…9387` |
| `tests/test_fable_newnames27.py` (1,021 lines) | `f300b38f4a5328cadc1b95350f7e7b68316389b52ca61c58fdc37e60f2f9ecfb` | `6f19cd47…599f` |
| `artifacts/fable-newnames27-20260921/run_data.sh` | `62b13de0950f94c62713312e41003900972680d4b4270c2a24801541d1917798` | unchanged |
| `artifacts/fable-newnames27-20260921/run_train.sh` | `2729e4af9e374a00b9b3653c9089f7ca092bc4fa51a7142105fa1912040cf39f` | `fb8dbf5a…1231` |
| `artifacts/fable-newnames27-20260921/run_score.sh` | `21e47fae8cc75a0d1b8e72dba0e3dcddd79ef7900e958ea6e95da06547ba371a` | `455546e8…7b43` |

Source fingerprint (this script plus the fourteen frozen modules it uses):
`6bb75f53575a0b776072fce5a28083d4408bf430d2892f490ca0d190b0e8878e`
(`b9c5d164…f301` before the AUDIT-27 fixes). Every run records the fingerprint in force
when it was trained, and `run_integrity` now refuses a set produced by more than one — so
the whole experiment must be launched against this one version.

Nothing else was touched. `fable_newnames21.py`, its artifacts folder, the ledger, and
everything under `archive/`, `premonition/`, `learnlab/` and `artifacts/opus-*` are
unchanged; `FABLE-PREDICTIONS.md` in this folder was not opened for writing.
`fable_newnames27.py` imports `fable_newnames21` and reuses its model class, its pool
functions, its panel builder, its audit, its scorer, its verdict function and its two
failure signatures, so the only scientific difference is the one the design names.

## The one change (design 4.1)

`code_scale` is a **constant buffer** at **1.2** in arm F: `FrozenScaleOperator` deletes
the `nn.Parameter` after construction and registers a buffer of the same value, so the
scalar is not in `parameters()` at all and therefore cannot enter the optimizer *or*
`clip_grad_norm_` — which is the design's stated reason for a buffer rather than a
parameter left out of the optimizer group. It stays in `state_dict()`, so a checkpoint
reload is exact.

| | control | F (gated) | L (descriptive) |
| --- | --- | --- | --- |
| model | `CanonicalOperator` | `FrozenScaleOperator` | `NewNamesOperator` |
| `code_scale` | — | buffer, 1.2, never moves | parameter, starts at 1.2 |
| trainable parameters | 79,316 | 78,533 | 78,534 |
| gated? | yes (≥ 2/3 else VOID) | yes (3/3 = PASS) | **no** |

F and L are built from the same construction stream and have **identical initial
parameter fingerprints** for a given seed; only `requires_grad` differs (test
`test_F_and_L_start_from_the_same_weights`).

## The registered procedure — exact command lines

All of it runs from the worktree
`/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`
with `OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1` and
`PY=/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12`.
**No `PYTHONPATH`** — `fable_newnames21` puts the base checkout on `sys.path` and
`premonition_memnn.py` reads `runtime.local.json` for torch; a `PYTHONPATH` could shadow
that. `EXP=$W/artifacts/fable-newnames27-20260921`.

The three launchers run exactly these commands, with skip-if-complete and
refuse-if-half-built around each one.

```sh
# wave 0 -- data, about 4 minutes (bash run_data.sh)
$PY -B scripts/fable_newnames27.py pool   --out $EXP --source $W/artifacts/fable-newnames21-20260920
$PY -B scripts/fable_newnames27.py panels --out $EXP --n 512 --audit-updates 100
$PY -B scripts/fable_newnames27.py control-equivalence   --exp $EXP --seed 0 --updates 50 \
      --out $EXP/control-equivalence.json
$PY -B scripts/fable_newnames27.py treatment-equivalence --exp $EXP --seed 9 --updates 50 \
      --out $EXP/treatment-equivalence.json
$PY -B scripts/fable_newnames27.py inertness --exp $EXP --seed 9 --updates 200 \
      --out $EXP/inertness.json

# wave 1 -- GATED, 6 jobs in parallel, about 11 minutes (bash run_train.sh 1)
for arm in control F; do for seed in 2103 2104 2105; do
  $PY -B scripts/fable_newnames27.py train --exp $EXP --arm $arm --seed $seed \
        --updates 6000 --wave-start $WAVE_START &
done; done; wait

# wave 2 -- DESCRIPTIVE, 3 jobs, about 11 minutes (bash run_train.sh 2)
for seed in 2103 2104 2105; do
  $PY -B scripts/fable_newnames27.py train --exp $EXP --arm L --seed $seed \
        --updates 6000 --wave-start $WAVE_START &
done; wait

# wave 3 -- read the runs, about 7 minutes (bash run_score.sh)
$PY -B scripts/fable_newnames27.py score    --exp $EXP --arm <arm> --seed <seed>   # 9 runs, 3 at a time
$PY -B scripts/fable_newnames27.py readouts --exp $EXP --arm <F|L> --seed <seed>   # DESCRIPTIVE
$PY -B scripts/fable_newnames27.py gates    --exp $EXP --wave 1
$PY -B scripts/fable_newnames27.py report   --exp $EXP --wave 1

# any time: the source fingerprint of this file and every frozen module it uses
$PY -B scripts/fable_newnames27.py fingerprint
```

`run_data.sh` is a hard gate on all four of its checks: an audit that is not clear (or
that could not check a development source), a control path that is not bit-identical to
experiment 21's, an arm L at 0.13856 that is not experiment 21's treatment, or a trace
that is not inert, all abort before a registered update is trained. `run_train.sh`
re-checks those four markers before it starts.

## Evidence produced during the build (fixture only)

Measured on a scratch copy of the pipeline (n = 16 panels, fixture namespaces, fixture
seeds), not on any registered seed:

- **control equivalence**, 50 updates, seed 0: identical parameter fingerprints after
  every update, identical losses (max |Δ| = 0.0), all **65 tensors** equal to
  `fable_newnames21.train_run('control', ...)`, and the registered grow-blind seed-0
  initial fingerprint `111b4141b8611850a5c8edf8a296c3c09d1f29ae73bd481c509f3e1d02b1cd5a`
  reproduced from disk.
- **treatment equivalence**, 50 updates, arm L started at `0.13856406460551018`: all
  **69 tensors** equal to `fable_newnames21.train_run('treatment', ...)`, same initial and
  final fingerprints, both 78,534 trainable parameters. So 1.2 is the only change.
- **inertness**, 200 updates, arms F and L: identical initial and final fingerprints and
  identical FLOP counts with the every-100-update trace on and off.
- **panel audit**, fixture suite: clear, every development source checked, 100-update
  partial replay of this experiment's own training stream, 208 excluded signatures.
- **unit tests**: `python3.12 -B tests/test_fable_newnames27.py` → **54 passed, 0 failed,
  0 skipped** (about 95 s). 47 at the first build, plus seven for the AUDIT-27 fixes.
- **the whole pipeline end to end on a scratch fixture** (16-unit panels, fixture
  namespaces, seed 9, 40-update runs): data wave clean, both training waves, scoring,
  read-outs, gates → `INCOMPLETE` (correct: no registered seed is scored), report written.
  Re-run after the AUDIT-27 edits with identical results.

## Timing

Measured on this Mac with **six** concurrent single-thread processes, fixture seed 9,
60 updates at each of four curriculum clocks (`--fixture-step0`), three jobs per arm:

| curriculum clock | control s/update | arm F s/update |
| --- | --- | --- |
| 0 | 0.0631 | 0.0652 |
| 2,000 | 0.0889 | 0.0895 |
| 4,000 | 0.1310 | 0.1339 |
| 5,900 | 0.1308 | 0.1333 |

Integrated over the 6,000-update grow-blind curriculum that is ≈ 640 s per run, and the
six run in parallel, so **wave 1 ≈ 11 minutes wall-clock** (well inside the 30-minute
rule and inside the trainer's own 28-minute watchdog). Experiment 21's registered
three-process wave took 628–715 s for the same 6,000 updates, which is the anchor these
numbers were checked against. Wave 2 is three jobs and no slower. Wave 3 is projected at
≈ 7 minutes from experiment 21's measured 35 s (one-scoring control) and 82 s
(two-scoring code arm) at 512 units — **projected, not measured for this experiment**.

## Judgement calls

**C1 — the pool is referenced, not re-drawn.** Design 4.3 says experiment 27 reuses
experiment 21's frozen 4,096-code pool and its 3,072 / 1,024 split. `pool` writes
`pool/pool-ref.json`: the source folder plus the sha256 of `pool.json`, `pool.pt` and all
three tensors. Every command re-verifies all of them before use and aborts if anything
moved. The alternative — copying `pool.pt` here — would have made two files that could
drift apart. Cost: this experiment cannot be run if experiment 21's folder is deleted.

**C2 — no 64-person descriptive cells.** Experiment 21 built them; design 4.2 does not
ask for them, and experiment 21 found them uninformative. Leaving them out keeps the
panel suite to exactly the ten gated cells and removes the `widened_entities` path from
this experiment entirely.

**C3 — the audit replay borrows seed 2103.** `fable_newnames21.panel_audit` replays the
training stream to look for panel collisions, and that stream's RNG is keyed
`fable-startup-grow-blind:<seed>` off `fable_newnames21.SEEDS`. A context manager
(`replay_seeds`) rebinds that module constant to (2103, 2104, 2105) for the duration of
the audit and asserts it is restored afterwards, even on an exception. This runs the
**registered** audit code object, not a copy. It is used for the audit only; nothing that
decides a number for a model ever runs inside it. The complete guarantee is still the
run-time `forbidden` check the trainer applies at every one of the 6,000 updates.

**C4 — fresh namespaces and a new panel seed base.** Train codes
`newnames27/train-codes:<seed>`, panel codes `newnames27/panel-codes:<pool>:<cell>:<chunk>`,
panel suite `newnames27-operator-v1-20260921` with seed base `202609212700`. The seed base
is arbitrary (date-like, ending in 2700 to be visibly distinct from 21's); its only job is
to be a number nothing else on this machine has used. A test asserts all four differ from
experiment 21's and that the seed sets are disjoint.

**C5 — a buffer, not a parameter outside the optimizer.** Design 4.1's wording is
explicit and the reason is `clip_grad_norm_`: a parameter that is merely excluded from
the optimizer still contributes its gradient norm to the clip factor and would change
every *other* parameter's update. Verified two ways: `code_scale` is absent from
`named_parameters()` and no object in `parameters()` is that tensor; and the arm-F
parameter count is exactly one less than arm L's.

**C6 — any movement at all is INVALID, not a result.** `check_frozen` compares with `!=`
on the float, not a tolerance, and runs after **every** update and again at the end of
training. A violation raises, the run writes `failure.json` with `"invalid": true`, the
scorer records `buffer_ok: false`, and `gate_table` returns INVALID for the whole
experiment before it looks at any mark. `run_train.sh` and `run_score.sh` both say so in
plain words and exit non-zero.

**C7 — trace fields (design 4.6).** Logged every 100 updates under `torch.no_grad()`, on
the batch just trained on, drawing no random numbers: `updates`, `code_scale`,
`entity_output_bias`, `mean_answer_length`, `effective_name_scale` (= `code_scale` ×
`mean_answer_length`), `answer_norm_gain_rms`, `value_row_mean_length`, `answer_loss`,
`link_accuracy`, `attribute_accuracy`, `name_mass_link`, `name_mass_value`. Two
definitions I had to fix:
  - *LINK versus value.* A stage is a LINK stage if its gold ANSWER token is an entity id
    (≥ `ENTITY_MIN` = 52); otherwise it is an attribute/value stage. This is read off the
    targets, not off the question, so it needs no extra generator call.
  - *`value_row_mean_length`* is the mean row norm of `base_embedding` over the sixteen
    **value** tokens 12…27, taken from the frozen `LadderSpec` (`spec.value(0)` …
    `spec.value(15)`), not over the filler tokens 28…51. A test asserts this window
    against the frozen generator so it cannot silently drift.

**C8 — `scale_collapsed` is an arm-L label only.** Design 4.5 defines it as
|`code_scale`| < 0.05 at any logged point from update 500. In arm F the buffer cannot move,
so a movement there is not a signature but a bug: `trace_summary` refuses to set the label
for arm F and the gates turn INVALID instead.

**C9 — `name_blind` sub-labels.** Fired when all ten paired differences are exactly 0
**and** every cell's first-stage LINK accuracy is ≤ 0.125. Sub-label `bias_exit` if the
final `entity_output_bias` ≤ −3.0, else `gain_exit` if the final mean answer length < 3.5
(half its start), else `unexplained` — in that order, which is the order the design lists
them.

**C10 — `unnamed`.** A seed that failed and fired none of the five named signatures. It
exists so that "we did not predict this" is recorded as such rather than left blank.

**C11 — the open-set read-out's correctness rule.** A stage counts as correct when the
person's own code beats *every* candidate code (1,024 reserved in read-out A, all 4,096 in
B) **and** every one of the 52 base vocabulary rows. Without the second half, a model that
put all its mass on a non-name token would score as correct. A test asserts that read-out
B can never score higher than A (more distractors cannot help).

**C12 — the attention read-out.** Cross-attention from the **last** read step, averaged
over the four heads, taken at the final question token, grouped back to story lines by
recomputing the token→line map outside the model (the NULL key is dropped; the remaining
mass is ≈ 0.996 of the total). "Right line attended, wrong name emitted" counts wrong
first-stage LINK answers whose largest line mass is the gold fact's line. Both read-outs
are descriptive: they are printed in the report and no mark, verdict or claim uses them.

**C13 — the read-outs and the scorer never modify the panels.** Codes are bound by tensor
identity on `inputs.memory`, which `A.select` / `canonical_input` reuse, so a stage built
from a panel side keeps its names. A test re-hashes every panel file after both scorings
and asserts byte identity.

**C14 — fixture escapes are refused for the registered seeds.** `--updates`,
`--trace-every`, `--fixture-step0`, a code-scale override and a code-namespace override
all abort on seeds 2103–2105. `test.pt` is refused by name anywhere. There is a test for
each. (`--updates` was added after AUDIT-27 §2.1; see the audit section below.)

**C15 — the equivalence proofs both run against the same experiment folder.** A different
panel suite implies a different exclusion set, which changes the world stream; so both
sides of every proof are run against the *same* folder, which isolates the only difference
that is being tested. For the arm-L proof the code namespace is additionally overridden to
experiment 21's, so the comparison is about the number 1.2 and nothing else.

**C16 — the launchers.** Three scripts rather than experiment 21's three-wave split,
because this experiment has two training waves: `run_train.sh` takes `1` or `2`. Wave 2 may
be run at any time after wave 0; it does not have to follow wave 1, and its absence is
never an INCOMPLETE (arm L is descriptive, so `gate_table` only requires the control and F
runs).

## AUDIT-27 follow-up (2026-09-21)

`AUDIT-27.md` (sha256 `abfe12bf2c35d5080085d3d48b158933fa60c6d84b5c8c988c5b75345f800c99`)
returned **FREEZE-READY: NO** with 0 blocking, 1 major and 8 minor findings. What was
done about each. **Nothing in this section changes a trained number, the data stream, the
scorer or any mark; the control arm's bit-identity with experiment 21 is re-proved after
the edits** (50 updates, 65 tensors, registered anchor reproduced).

**MAJOR §2.1 / §2.3 — fixed.**
  - `train_run` now refuses `updates` as a fixture override on seeds 2103–2105, alongside
    `code_scale`, `code_namespace`, `trace_every` and `fixture_step0`. A short run on a
    registered seed writes a `completion.json` that says "complete" and is otherwise
    indistinguishable from a full one; it is now impossible to make one by accident.
  - New gate-side `run_integrity(exp)` reads every `runs/<arm>-<seed>/training.json` and
    reports a problem when a run records anything other than 6,000 updates, records any
    override at all, or carries a source fingerprint that differs from the other runs'.
    `gate_table` evaluates it in the INVALID branch, before INCOMPLETE, VOID and every
    mark; the table carries `integrity`, `cmd_gates` prints `integrity_problems` and
    `cmd_report` prints a `run integrity` line. This closes §2.2: the source fingerprint
    was pinned in four places and compared nowhere; it is now compared across runs.
  - Five new tests: a 3-update (and 5,999- and 6,001-update) run on a registered seed is
    refused and creates nothing; a doctored `training.json` with the wrong update count,
    with a recorded override, or with a second source fingerprint each give INVALID; a
    full nine-run set gives no problems and still PASSes; and an experiment with no
    `runs/` folder at all is silent.

**MINOR-2 — fixed.** `run_train.sh` now refuses to train unless
`panels/newnames27-panels.json` says `"registered": true`, so a fixture panel suite (a
different namespace, seed base or unit count) cannot consume a wave. Verified: the guard
fires on a 16-unit fixture suite.

**MINOR-3 — fixed.** `run_score.sh` refuses to run when `gates.json` or `report.txt` is
older than the newest `scores/*.json` — a verdict computed for a smaller set — instead of
announcing the stale one while writing the fresh one only to the log. Checked twice: once
before scoring and once after, since the run may add scores in between.

**MINOR-4 — fixed.** `run_score.sh` checks that every gated run is finished before it
spends minutes scoring the ones that are.

**MINOR-8 — fixed.** `load_checkpoint` rebuilds an arm-F model at the registered 1.2
rather than at the number the checkpoint records (and asserts the recorded number is 1.2
to float32 precision), so `check_frozen` at load time compares against the design's value
instead of against the file's own claim. Tested with a doctored checkpoint.

**MINOR-1 — recorded, not fixed. An explicit deviation from design 4.3.** The design's
last bullet in 4.3 asks for the arm-L equivalence proof on **seed 2100's first 50
updates**. `run_data.sh` runs it on **fixture seed 9** instead. The reason: experiment 27
builds a fresh panel suite, the fresh suite changes the training exclusion set, and the
exclusion set changes the world stream — so experiment 21's on-disk seed-2100 fingerprint
is unreproducible here **by construction**, and a comparison against it would fail for a
reason that has nothing to do with the number 1.2. Both sides of the proof are therefore
run inside experiment 27's own folder, where the only difference left is `code_scale`
(C15). Seed 9 rather than 2100 also keeps a registered seed out of a scratch run. This is
a knowing deviation from a binding document and is recorded here and in the freeze note in
those words.

**MINOR-5 — recorded, no action.** The control-equivalence proof runs on **seed 0**, not
on 2103–2105, because seed 0 is the one seed with a registered grow-blind run on disk, so
the proof also re-derives the registered initial fingerprint. The control path has no
seed-dependent branch. The freeze note must not claim the proof was done on the registered
seeds.

**MINOR-6 — left unfixed, disclosed.** The panel audit's source list comes from
`fable_confirmation_panels.development_sources()`, a frozen module, and does not include
`artifacts/fable-newnames21-20260920/panels`. Adding it would mean editing a frozen module,
which this build is not allowed to do. So "disjoint from experiment 21's panels" is
asserted by construction (new namespace, new seed base, new code namespaces) and not
measured. Impact: no experiment-27 model ever sees an experiment-21 panel, so an overlap
would leak nothing; it would only matter to someone later comparing the two experiments
cell by cell. The auditor measured zero overlap on a fixture suite.

**MINOR-7 — left unfixed by design, disclosed.** `--audit-updates 100` certifies 100 of
6,000 updates and is labelled `"partial": true` in the JSON. The complete guarantee is the
run-time `forbidden` check the trainer applies at every update. The report must not
describe the replay as a full certification.

**Wording caveat the results write-up must carry (audit §3.1).** Arm F is not "experiment
21's treatment with the scalar pinned at 1.2": the scalar is **removed from the parameter
set**, so the gradient-clip factor is computed over 66 tensors instead of 67 and every
other parameter's update differs marginally from a pinned-parameter version. Design 4.1
demands exactly this and 4.8's claim wording is compatible; "we only changed one number"
would be an over-claim.

**Freeze-manifest note (audit C1).** `artifacts/fable-newnames21-20260920/pool/` must be
bound into the freeze manifest and must not be deleted: experiment 27 references it rather
than copying it.

## What is unverified

1. **No registered seed has been trained or scored, and no registered panel exists.** All
   evidence above is from fixture seeds (0, 9) and fixture panel suites of 16 units.
2. **Wave-3 timing is projected**, by analogy with experiment 21 at 512 units. The fixture
   suites here were 16 units, so scoring cost was not measured at registered size.
3. **Wave-1 timing is an integration**, not a measured 6,000-update run: per-update cost
   was measured at four curriculum clocks under six-way load and integrated. It agrees
   with experiment 21's registered anchor (628–715 s) to within a few per cent.
4. **The registered panel build has not been run**, so its wall-clock at 512 units (and
   the number of excluded signatures) is not known; experiment 21's comparable step is the
   only guide.
5. **The failure signatures have been exercised on synthetic score tables only.** Their
   arithmetic is tested; whether the real runs fire them is exactly what the experiment
   asks.
6. **The open-set and attention read-outs have been exercised on a 120-update fixture
   model**, which unsurprisingly scores 0. Their plumbing is verified (mass sums, line
   indices, candidate counts, monotonicity); their usefulness at 6,000 updates is not.
7. **`buffer_ok` is checked to float32 precision** (|value − 1.2| ≤ 1e-6): 1.2 is not
   representable in float32, so an exact `== 1.2` would always be false. The stricter
   check — that the buffer never moved from whatever float32 value it was frozen at — is
   exact, and runs after every update.
8. **Arm L's failure modes are not predicted here.** Design 4.2 makes it descriptive, and
   the gates ignore it entirely, including when it fails 0/3.

## Folder inventory (after the build)

```
artifacts/fable-newnames27-20260921/
  FABLE-PREDICTIONS.md            registered before the build; untouched
  FABLE-PREDICTIONS.sha256.txt    untouched
  AUDIT-27.md                     the independent audit; written by the auditor, untouched
  BUILD-NOTES.md                  this file
  run_data.sh  run_train.sh  run_score.sh
  fixtures/exp/                   DISPOSABLE fixture experiment (16-unit panels, seed 9):
                                  pool/ panels/ runs/{control,F,L}-9/ scores/ readouts/
```

At launch, `run_data.sh` adds `pool/`, `panels/`, `logs/`,
`control-equivalence.json`, `treatment-equivalence.json`, `inertness.json`;
`run_train.sh` adds `runs/<arm>-<seed>/`; `run_score.sh` adds `scores/`, `readouts/`,
`gates.json` and `report.txt`. The fixture folder is not read by any registered command.

## Claim wording (design 4.8)

If wave 1 comes out 3/3 with the control at ≥ 2/3, the most that may be said is: *holding
the name-code scale fixed at 1.2 lets this model answer questions about people it has
never seen named before, on three of three seeds, on reserved codes, in this toy world.*
Not "the model learned names", not "label-free operator", and nothing about arm L beyond
what arm L is — a descriptive check of whether the scale stays up when it is allowed to
move.
