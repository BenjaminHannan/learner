# AUDIT-21 — independent pre-freeze audit of experiment 21 / M1 "new names"

Independent auditor (wrote none of this code), 20 September 2026, in the worktree
`/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27`
(hereafter **W**). Base read-only checkout **BASE** = `/Users/ben-hannan/Desktop/projects/beautiful-model`.

No commits. No existing script, test, design doc, launcher or prediction file was edited; the only
files this audit wrote are this report and the contents of
`W/artifacts/fable-newnames21-20260920/audit-scratch/` (which carries a `.gitignore` containing `*`).
A `find -newermt` sweep confirms nothing under `W/artifacts/fable-newnames21-20260920/` outside
`audit-scratch/` was touched, and the registered outputs (`pool/`, `panels/`, `runs/`, `scores/`,
`gates.json`, `report.txt`, `control-equivalence.json`) still do not exist.

Python used throughout:
`/Users/ben-hannan/.local/share/uv/python/cpython-3.12.14-macos-aarch64-none/bin/python3.12 -B`
with `OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`. Never more than six concurrent single-thread
processes. No cloud, no BensPC.

---

## 0. One-paragraph verdict

The build does what the roadmap §5 and the 21b rulings say it does. Every hash matches; all 35 tests
pass; C1 is provably logging-only; the control path is bit-identical to the registered grow-blind
recipe through 50 updates *including through `train_run` itself*, which the builder's own evidence
did not actually establish; reserved codes are unreachable from the training sampler; the two
treatment scorings see byte-identical worlds, questions, targets and order across all ten cells; the
marks are hard-coded and cannot be moved by a flag; and the gate cannot silently pass on a missing
run, a missing cell, a below-cutoff cell or a failed control. I found **no BLOCKING defects** and
**eleven MINOR** items, five of which are recommendations for the freeze manifest and the report
rather than faults in the code. Timing, measured by me with six concurrent processes (which the
builder never measured), projects **≈ 11.0 minutes** for the slowest run — comfortably inside the
30-minute rule and 2.5× inside the 1,680 s watchdog.

---

## 1. Hashes and tests

### 1.1 Claimed hashes (all confirmed)

| file | sha256 | claim |
|---|---|---|
| `design/v3/21b-new-names-rulings-fable-review.md` | `7142b9c34419014098221203b46f4b10a609b608f24b4e61b98acbd9e94fd153` | matches the task's stated hash |
| `scripts/fable_newnames21.py` | `14336a4971e2976a60e8af31b29b2393e13aba6ee6bf0b190b759a9d85dac500` | matches BUILD-NOTES §7 |
| `tests/test_fable_newnames21.py` | `f62ada7108d6a0aa7934b6ea8bfa4ba70033877e7d436345367c603bc09eb68d` | matches BUILD-NOTES §7 |

### 1.2 Tests

```
OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python3.12 -B tests/test_fable_newnames21.py
PASSED 35  FAILED 0  SKIPPED 0
```

35 pass as claimed, with **zero skips** — worth stating because the file contains a `_Skip`
mechanism and several tests (`test_control_arm_reproduces_the_registered_recipe`,
`test_both_sides_of_a_pair_share_their_codes`, `test_fixture_step0_is_refused_for_the_registered_seeds`)
would silently skip if the fixture suite were missing. They ran.

I read the tests rather than counting them. The load-bearing ones are real, not decorative:
`test_reserved_codes_are_unreachable_from_the_training_sampler` checks **pool-row identity** over a
3,000-step stream and additionally asserts the stream exercises the whole training half (so it
cannot pass by sampling nothing); `test_codes_are_frozen_through_real_updates` runs genuine
`A.training_step` calls and asserts no code tensor moved, no code received a gradient, the tied-head
stub stayed the identity, and `code_scale` *did* move; `test_the_two_treatment_scorings_read_byte_identical_panels`
compares tensor hashes of memory/questions/owner plus targets across both pools and re-hashes the
panel files afterwards to prove scoring never writes to them.

---

## 2. Implementation against roadmap §5 and rulings Q1–Q10

All checks below are mine, run against the code, not read off BUILD-NOTES.

### Q1 — frozen `random.Random(1101)`, shared by arms and seeds — **MET**

`train_run` opens `rng = random.Random(1101)` for both arms (line 824), draws the batch first
(line 848) and only then touches the code generator (lines 850–856), so the code stream cannot
perturb the world stream.

Verified empirically, not just by reading: I spied on `A.training_batch` (installing the spy from
inside `configure_recipe`, because `configure_variant` rebinds it) and ran 25 real updates of
**control** and **treatment** at seed 2100 against the fixture exp. The sequence of
(memory-hash, questions-hash, owner-hash, monolithic memory-hash, monolithic questions-hash) is
**identical batch for batch, 25 of 25**, first difference `None`. This closes the only way the
treatment's extra RNG consumption could have desynchronised the arms.

The Q1 limitation sentence is prose for the report; see condition 11.

### Q2 — control held to the same ten cutoffs; VOID rule; "failure matched in control" — **MET in code; wording is the coordinator's**

`CUTOFFS` is built from `FC.OPERATOR_CELLS` and is exactly
`c1 487, c2 487, c3 461, c4 461, c5 461, c6 461, p12-1 487, p12-2 487, p12-3 461, s3 461` —
the registered 487/487/461/461/461/461/487/487/461/461 in `CELL_ORDER` order, matching §5's
"≥ 487 on c1, c2, p12-1, p12-2; ≥ 461 on the other six".

VOID: `gate_table` tests `control_pass < 2` **before** it looks at the treatment, so the awkward case
Q2 names (control 1/3, treatment 3/3) really does come out VOID. I forced it with synthetic score
files: with treatment at 3/3 and two control seeds pushed below cutoff, the verdict is
`VOID — recipe did not reproduce`.

The "failure matched in control" line is words-only and is not emitted by `cmd_report`. Coordinator's
job (condition 11). The inputs exist: `signatures['control-2100']` etc. are computed and stored.

### Q3 — codes re-drawn every visit of every update — **MET**

`assign_codes(subset, f'{key}:{step}:{code_generator.randrange(1<<30)}', VISITS=16, ENTITIES=16)` is
called inside the per-update loop and returns a `[16 visits, 16 people, 48]` tensor, so each of the
16 visits in each update gets its own 16 distinct codes. Checked directly for the first 50 updates of
**all three registered seeds** (2100/2101/2102): shape `(16,16,48)`; 16 distinct codes within every
world; all 16 visits of an update carry different assignments; all 50 updates carry different
assignments. 50 updates already touch 3,026–3,030 of the 3,072 training codes.

### Q4 — one learned scalar, not shared with the value rows, init 0.13856 — **MET**

Measured on a real `new_treatment_model(2100)`:

* `code_scale` is `nn.Parameter` of shape `()` (one scalar), `requires_grad=True`, value
  `0.1385640650987625` = `.02 × √48` exactly as `CODE_SCALE_INIT` declares.
* `entity_output_bias` is a separate `nn.Parameter` of shape `()`, init `0.0`.
* The value rows live in `base_embedding` `(52, 48)`, an ordinary trained parameter that
  `world_weight` concatenates **unscaled**: `cat(base_embedding, code_scale·codes)`. `code_scale`
  therefore multiplies only the entity block. Nothing is shared.
* Both scalars are in the optimizer (`optimizer_for` → one group, `weight_decay = 0.1`, 67 tensors),
  which is what Q4 explicitly ruled should be left alone.
* Trainable parameters: treatment **78,534**, control **79,316**. Fewer, as §5 requires.
* `embedding.weight` is a buffer holding `eye(48)` and `output_bias` a zero buffer — neither trains.

The speed-limit flag needs `code_scale` at updates 500 and 1,000; `scale_trace` records at every
500th update, so it is computable by hand from `training.json` as Q4 intends.

### Q5 — gate at 16 candidates — **MET**

`world_weight` on a 16-code world returns `(worlds, 68, 48)`, i.e. the logit vector is 68 wide =
52 base rows + 16 entity codes, the same candidate-set size as the control's tied head. The 64-person
descriptive cells give `(worlds, 116, 48)` under `widened_entities`, and
`test_widened_entities_restores_the_frozen_range` plus my own check confirm `A.ENTITY_MIN/MAX` are
back at `(52, 68)` afterwards. The open-set scoring specified in Q5 is correctly **absent** — it is a
later additive script.

### Q6 — panel codes seed-independent, with per-world draws; reserved and train scorings share worlds, questions, order — **MET**

The panel code key is `f'{PANEL_CODE_NAMESPACE}:{which_pool}:{cell}:{chunk_index}'` — no seed in it,
so all three seeds sit the same exam. Every chunk gets its own draw, and `bind_panel` binds the *same*
codes object to both sides of a pair cell.

Verified empirically for the full ten-cell suite: I instrumented `R.score_cell` and ran a real
`score --arm treatment` over the fixture exp, recording per call the panel name, `n`, and for every
chunk and side the targets, memory hash, questions hash and owner order. The `train` and `reserved`
scorings produced **10 calls each, an identical ordered sequence, first mismatch `None`**. The two
scorings differ in the bound codes and in nothing else.

(My first pass keyed by `panel['name']` and collapsed `p12-1..3` onto `c1..c3`, which share a source
name; the result above is from the corrected, call-ordered comparison.)

### Q7 — signature thresholds — **MET**

`NEVER_STARTED_AT = LINK_CHANCE_AT = 2/16 = 0.125`, `ATTRIBUTES_FINE_AT = 0.90`.
`failure_signatures` implements never-started as `c1.R ≤ 0.125·n and c2.R ≤ 0.125·n` (64/512), and the
scale bug as `min(one-call attribute accuracies over c1 and p12-1, excluding op LINK) ≥ 0.90 and
max(first-stage LINK accuracy over every cell) ≤ 0.125`. That is Q7 word for word. Signatures are
computed on the reserved scoring **and** separately on the training-pool scoring
(`treatment-<seed>-train-pool`) and on each control seed, so P14 is scorable. Signatures never touch
a verdict — `seed_verdict` does not read them.

### Q8 — predictions — see condition 7. P1–P14 exist only in the rulings file; the ledger stops at P93.

### Q9 — 12-person cells keep 16 bound codes — **MET**

`bind_panel`'s callback always passes `ENTITIES = 16`. I asserted `codes.shape[1] == 16` for every
chunk of every cell including `p12-1/2/3`; it holds. Four codes per 12-person world therefore name
nobody and are live wrong answers, exactly as the control's four unused entity rows are.

### Q10 — one-sided paired mark — **MET in code; the two-sided warning line is not implemented**

`meets_paired = (reserved.R − train.R) ≥ −13`. Forced both directions with synthetic scores:
a −20 gap on one cell fails that seed (verdict drops to PARTIAL); a **+20** gap passes (verdict stays
PASS). One-sided, as ruled. The Q10 reporting addition — print
"paired difference larger than expected — check panel-code luck or a binding bug" when
|reserved − train| > 13 in *either* direction — is **not** emitted by `cmd_report` (MINOR-6 below);
the ruling classes Q10 as "no code change", so this is a report obligation, not a defect.

---

## 3. C1 is logging-only — re-proved from scratch

**The frozen pre-C1 script is not saved on disk. I reconstructed it** by taking
`scripts/fable_newnames21.py` and reverting exactly the three C1 hunks quoted in ruling Q4 —
(a) delete `scale_trace = []`, (b) restore the `if log_every and updates_done % 500 == 0:` heartbeat,
(c) delete the `scale_trace=...` key — into
`audit-scratch/prec1_newnames21.py`. Nothing else was changed.

**The reconstruction hashes to `f3a358e66562693810cff02f479ca38190749642d61db8c46729aa7724e9d320`,
which is exactly the pre-C1 sha256 BUILD-NOTES §7 records.** Reverting the ruling's own three hunks
and landing byte-for-byte on the recorded pre-C1 file is strong evidence that C1 touched only those
three places. *Honest limit:* this proves consistency with the builder's recorded pre-C1 hash, not
the absence of some fourth change made before that hash was taken; the protection against that is my
own line-by-line read of the file, which found no other recipe-affecting code.

The produced diff (prec1 → postc1) is three hunks, all inside `train_run`, at the lines the ruling
names. It reads two tensors with `.detach()`, converts to Python floats, appends a dict, and adds one
JSON key. No model, optimizer, RNG, batch-order, code-assignment, scoring or verdict code is touched.

### 3.1 Treatment fingerprint, before and after C1 — **identical**

50 updates, `--arm treatment --seed 2100`, both scripts, same arguments, fixture exp for pool and
exclusions (the registered pool does not exist yet; the choice is identical on both sides):

| | pre-C1 | post-C1 |
|---|---|---|
| `final_fingerprint` | `3b4cda9f8d350a2cfdb76e08141156f941ce55a54ddbc1fcf27f30299b8699ae` | **identical** |
| `trainable_parameters` | 78,534 | 78,534 |

This matches BUILD-NOTES §7(a). C1 changes no computation.

### 3.2 Control bit-identity with the registered recipe, post-C1 — **re-proved**

`train --seed 0 --equivalence 50` with the post-C1 script:

```
fingerprints_equal        true
first_differing_update    null
losses_equal              true
max_abs_loss_difference   0.0
registered anchor         rebuilt initial 111b4141b8611850a5c8edf8a296c3c09d1f29ae73bd481c509f3e1d02b1cd5a
                          == initial_fingerprint in BASE/artifacts/fable-operator-grow-blind-20260920/
                             astra_canonical_operator_seed-0/training.json
control-path final        521d6a90f9747eaa81ac7afdfbc47bef9e8e33b24129fddf28e2d3d87a585262
```

The registered grow-blind artefacts were read only, from BASE.

### 3.3 A gap in the builder's own evidence, which I closed — **MINOR-1**

`control_equivalence` compares `control_path_updates` against `reference_updates`. Both of those
compute an extra eval-mode answer-loss inside the loop; **`train_run`, the function the registered
wave actually runs, does not.** Nothing in BUILD-NOTES shows that `train_run`'s control path lands on
the same parameters. If that loss evaluation had consumed any global RNG, the proved path and the run
path would diverge.

I tested it directly:

```
train --arm control --seed 0 --updates 50   →  final_fingerprint
  521d6a90f9747eaa81ac7afdfbc47bef9e8e33b24129fddf28e2d3d87a585262
```

— bit-for-bit the equivalence run's own final fingerprint. The chain is therefore closed end to end:
`train_run` control ≡ `control_path_updates` ≡ `reference_updates` (registered functions called
directly), starting from the registered on-disk initial fingerprint. I record this because the
registered `control-equivalence.json` alone does not say it, and a reader after a VOID verdict will
want it.

---

## 4. Leakage, fairness and the gate

### 4.1 Reserved codes can never appear in training — **proved directly**

Frozen pool split: 3,072 train / 1,024 reserved, intersection **0**. Training uses
`pool_subset(pool, 'train')` and `assign_codes` samples indices only inside that subset, so a reserved
row is not reachable. Checked on the real draw sequence rather than by argument: for each of
**seeds 2100, 2101 and 2102**, the first 50 updates × 16 visits × 16 codes touch 3,026–3,030 distinct
pool rows, **0 of them in the reserved half**, all of them inside the training half. Panel scoring is
equally clean: over all ten cells, the `train` scoring touched 1,723 rows all inside the training
half, the `reserved` scoring 954 rows all inside the reserved half, zero crossings either way.
(Run against the fixture pool, since the registered pool does not exist yet; the split mechanism is
namespace-parameterised and identical.)

### 4.2 Marks and cutoffs cannot be changed at score time — **confirmed**

The `gates` subcommand's only flags are `--exp` and `--out`; `score` adds only `--run/--out/--skip-wide`.
`CUTOFFS` and `PAIRED_SLACK = 13` are module constants; `seed_verdict` reads `CUTOFFS[cell]`, not the
per-cell cutoff stored in the panel manifest, so editing `panels/manifest.json` cannot move a mark.
`test_registered_constants_match_section_5` pins the ten numbers, the seeds, 6,000 updates, the
4,096/1,024/3,072 split and `blind_lines == 16`.

### 4.3 The scorer cannot silently pass — **tamper-tested**

Tampering was done on scratch copies; nothing registered exists to tamper with.

| tamper | outcome |
|---|---|
| six synthetic score files, every cell above cutoff | `PASS — 3/3 seeds` (so the gate *can* pass; the tests below are not vacuous) |
| `scores/treatment-2102.json` deleted | `INCOMPLETE — missing runs: treatment-2102` |
| cell `s3` deleted from `treatment-2101`'s reserved scoring | raises `KeyError: 's3'` — a loud crash, never a pass |
| `treatment-2101` c3 pushed below cutoff | `PARTIAL — 2/3 seeds` |
| `treatment-2101` c4 reserved − train = **−20** | `PARTIAL` (paired mark bites) |
| `treatment-2101` c4 reserved − train = **+20** | `PASS` (one-sided, per Q10) |
| two control seeds below cutoff, treatment 3/3 | `VOID — recipe did not reproduce` |
| `runs/treatment-9/completion.json` removed | `score` exits 1: "has no completion.json (not a completed run)" |
| one byte flipped in `runs/treatment-9/final.pt` | `RuntimeError: checkpoint fingerprint mismatch` |

Each checkpoint is sha256'd before loading and its stored parameter fingerprint re-derived after;
`test.pt` is refused by name; outputs are written with `write_new`/`refuse_existing` so nothing is
overwritten.

**MINOR-2.** `run_score.sh` does not refuse the wave up front when a run is missing: it scores the
runs that *are* complete, fails that one job, and exits before `gates`. No mark or verdict can be
produced (the gate returns INCOMPLETE), but five of six scorings would exist on disk. Condition 9's
letter — "no scoring until all six training runs have written `completion.json`" — is therefore a
procedural obligation on the coordinator (run `run_score.sh` only after `TRAIN_DONE`), not something
the launcher enforces.

**MINOR-3.** `cmd_gates` writes `gates.json` only if absent but always prints the freshly computed
table. If scores were ever added after a first `gates` run, the file and the printed verdict could
disagree. Low impact given "nothing is overwritten" is the deliberate policy; worth knowing.

---

## 5. `run_data.sh` — **not run, deliberately**

The task allowed one `bash run_data.sh` **only if it builds data and nothing else**. It does more:

* **Stage 3 trains a model.** `run_data.sh` calls
  `train --seed 0 --equivalence 50`, which runs 50 real updates twice (`control_path_updates` and
  `reference_updates`, 100 updates of optimizer work in total) and writes the registered
  `control-equivalence.json`. That is training, not data building.
* Stages 1–2 would create the **registered** `pool/` and `panels/` under the experiment folder. Those
  are registration artefacts, and the launcher refuses to rebuild a folder that exists, so an
  auditor's run would consume the coordinator's one shot and make the registered data mine rather
  than the builder's.

So I did the equivalent verification without touching the registered folder:

* Built the **registered-namespace** pool twice into two different scratch folders
  (`pool --out audit-scratch/det1`, `…/det2`), with `registered: true` reported both times.
  `pool.pt` is **byte-identical** across builds.
* Built the **registered-namespace, registered-seed-base** panel suite at `--n 512` twice into those
  same two folders. Every data file is **byte-identical** across builds. (I passed
  `--audit-updates 0 --skip-dev-audit` for speed; the audit runs *after* the panels are written and
  only reads them, so the panel bytes are unaffected — but see the honesty note below.)
* Re-proved the 50-update control equivalence with the post-C1 script into scratch (§3.2).

**Honesty note.** I did **not** exercise the real audit gate: the development-source overlap sweep and
the 100-update training-stream replay were skipped in my scratch build. Whether every development
source on this machine is reachable (an unreachable one is recorded UNVERIFIED and *fails* the
launcher) is unverified by me and remains the coordinator's gate to pass.

### 5.1 Determinism results and the data hashes the freeze will bind

Two independent builds, different folders, identical bytes:

| data file | sha256 (both builds) |
|---|---|
| `pool/pool.pt` | `4e5b5d862b5832e5e410a6bc11409030a77db27be19f1d8dacf6698f4f135c1d` |
| `panels/c1.pt` | `3b836ab6f37864dd6ce3cc508f8c79d12187ae3cefb8efc730dd61f8736f078b` |
| `panels/c2.pt` | `a08d86d2afe67658cc5cd3595ce9c438a3032006ac7fa99d2d28fd5b322a2da0` |
| `panels/c3.pt` | `e7600c00bc324961cd75412dc2b8d2455d6b9ed9de67bf9c856ab413987eb4f2` |
| `panels/c4.pt` | `58f714ae9c722ea2f9f491abae0e062936607e63a96f3cab63e815596a4e7fae` |
| `panels/c5.pt` | `ac9edc6ee9c78f957c47d1baf021c46a61b304508f9d9b49fc27454d97f68022` |
| `panels/c6.pt` | `aaf61990b2bf030983f0a93b924daf1ba754a7318a4328fc4da0e983cbdd05a9` |
| `panels/p12-1.pt` | `935d8837aaed8608c75da4203ea0b3768b715596da13e5a681001fa0fe8f1e74` |
| `panels/p12-2.pt` | `3532d8904aff6fbf52fb06904365e3d298da098821c5da974f584c578c5eee2e` |
| `panels/p12-3.pt` | `5cc3ad8a721806e68da2de37cb206c988f263f262bba42a2c2f305356772e4cb` |
| `panels/s3.pt` | `8189be3e53fc2e6920b3cc62ef4686cdc1ff3e8e0680971b0a444d463ffe68c4` |
| `panels/wide64-attr.pt` | `34fde7a975c551841be2940aeb49ab74a3b84a12063b126b9656775460a9e976` |
| `panels/wide64-link.pt` | `300b159379acce2665dbcdfe3ad9d2c2199d7f8b7c62b85403fd12447517d52f` |
| `panels/wide64-two.pt` | `5408951e2220c3d4a66b41446e01db80fd14730db51d299980b4c72c019d1395` |
| `panels/forbidden-semantics.json` | `788e0a7f066ecbd597aafdc42f4b38765b0d274d6a053b87fc5c89b2db97477f` |

Pool content hashes recorded inside `pool.json` (path-independent, so these are the values the
registered run must reproduce):

```
codes_sha256           ba5fba4a29ce7d6bc62f707ef04c94e4272f4de1ae14860c9c830b86455ddb47
train_index_sha256     4cded5ad8b205ceeb2e8f58503a455fa9278144cd8b2caaac8f6388576c6e05d
reserved_index_sha256  114b4d6347f84e8663af99494497853c80a5beb0b961f0d9380c2dadf7adc5bc
code_scale_init        0.13856406460551018
unit_norm_max_error    1.19e-07
exclusion_count        6656   (union written by the panels stage)
```

**These are a prediction, not the registered artefacts.** `pool/pool.json` and `panels/manifest.json`
embed absolute paths and a `created_utc`, so their own sha256 values will differ from my scratch
copies and must be taken from the real `run_data.sh` output. If the data files above come out with
different hashes, something is wrong and the freeze should stop.

**MINOR-4 — a measured discrepancy with BUILD-NOTES §3(a).** The registered pool's maximum absolute
cosine between two codes is **0.6764**, not the 0.699 BUILD-NOTES §3(a) states and ruling §3/Q5 quotes.
(Mean |cos| 0.11576 matches the claimed 0.116 and the sphere's own 0.115.) The direction is harmless —
the real pool is slightly *better* separated than the argument assumed — but the pre-registration note
should record 0.676 so the F2/open-set reasoning rests on the true number. My guess is that 0.699 came
from a fixture-namespace pool.

---

## 6. Timing and watchdogs

The builder measured **two** concurrent processes and then *projected* six-way contention at 1.5×.
I measured six. Three control + three treatment runs, all six concurrent, one thread each, 60 updates
apiece, using `--fixture-step0` at each curriculum regime (refused for registered seeds, so fixture
seed 9), background load average 5.5–6.1 — i.e. a realistically busy machine, not an idle one.
Figures are `tail_seconds_per_update` (last 40 updates, so start-up is excluded), averaged over the
three runs of each arm:

| curriculum stage | control s/update | treatment s/update | builder (2 procs) |
|---|---|---|---|
| reduced stories (`step0 = 0`) | 0.0614 | 0.0627 | 0.0566 / 0.0583 |
| mid-ramp (`step0 = 2250`) | 0.1014 | 0.1034 | 0.0944 / 0.0964 |
| full stories (`step0 = 3000`) | 0.1356 | 0.1380 | 0.1231 / 0.1252 |

Six-way contention costs only **≈ 1.08–1.10×** over two-way, not the 1.5× assumed. Integrating over
the grow curriculum (1,500 reduced + 1,500 ramp by Simpson + 3,000 full):

* **control ≈ 650 s (10.8 min)**, **treatment ≈ 661 s (11.0 min)** per run.
* The six runs are parallel, so the wave is the slowest run: **≈ 11.0 min**.
* With the required 1.5× safety margin: **≈ 16.5 min — inside the 30-minute rule**, with more room
  than the builder's ≈ 22.7 min estimate claimed. It would take a ≈ 2.7× further slowdown to breach
  30 minutes.

**Watchdog caps confirmed at the ruling's numbers and not raised:** `TRAINING_SECONDS = 1680`
(checked every update against the run's own training clock — 2.54× headroom over my 661 s projection)
and `WORK_SECONDS = 1740` (checked every update via `R.deadline(wave_start, …)`; `wave_start` is a
`time.monotonic()` value passed in from the launcher process, which is comparable across processes on
macOS). A cap only raises `TimeoutError`, which lands in the `except BaseException` handler, writes
`failure.json` and re-raises — it never shortens a run.

**MINOR-5.** `TERMINATE_SECONDS = 1770` is defined and **never used**; `run_train.sh` wraps nothing in
`timeout`. Both live caps are checked at update boundaries, so a hang *inside* a single
`A.training_step` would not be caught by anything. The risk is small (no such hang has occurred in
this codebase) but the third cap is decorative, and the pre-registration note should not describe it
as active.

Scoring wave (outside the 30-minute training rule): the builder's fixture measurements at n = 512 with
two concurrent processes are 35.05 s (control) and 81.62 s (treatment), which I read from
`fixtures/exp512/score-*.log`. At `PARALLEL=3` that is two rounds, a few minutes. I did not re-measure.

---

## 7. What a failed result could later be blamed on

Recorded now, before any data, so none of it can be invented afterwards.

1. **Unnamed failure is the single most likely outcome among failures.** Q7's two signatures are
   deliberately strict (never-started needs *both* c1 and c2 ≤ 64/512; the scale bug needs *every*
   attribute relation ≥ 0.90 *and* every first-stage LINK ≤ 0.125). A seed at attributes 0.97 /
   LINK 0.30 fires neither and is reported as "unnamed failure" — the reviewer's own P7 puts this at
   0.35, higher than either named signature. This is by design and must not be re-labelled after the
   fact, but it means a FAIL may well arrive with no mechanism attached.
2. **No training-loss trace is recorded.** `train_run` writes timing, flops, initial/final
   fingerprints, parameter counts, the exclusion summary and (treatment) `scale_trace` — but **no loss
   curve, and no accuracy at any intermediate point**. If a treatment seed fails, there is no way to
   tell "never started" from "started at update 2,000 and collapsed" except through the end-of-run
   panel numbers and the twelve `code_scale` samples. Q4's diagnostic order ("read the `code_scale`
   trace first") will have nothing to sit beside it. Adding a loss trace now would be a second change
   after the ruling, so **my recommendation is to record this limitation, not to change the code** —
   but it should be written into the pre-registration note so that a post-hoc "we couldn't see what
   happened" is a known cost, not a surprise.
3. **One world stream.** Q1's limitation is real: the three seeds differ in initialisation, the blind
   curriculum stream and (treatment only) the name stream, but not in the training worlds. A failure
   could always be blamed on this particular `random.Random(1101)` draw. The mitigation is the
   sentence Q1 mandates, not more evidence.
4. **The control is proved identical for 50 updates, not 6,000.** §6 of the roadmap already flags that
   `v3-repro` failed 0/3 where `v3` passed 3/3, i.e. the recipe may sit on a knife edge. A VOID
   ("recipe did not reproduce") would therefore be genuinely ambiguous between "this machine" and
   "this recipe". Each run is a separate single-threaded process with its own RNG, so there is no
   cross-process non-determinism *within* the wave; the residual risk is BLAS/thread-level
   non-determinism over 6,000 updates, which no 50-update proof can exclude.
5. **The start-up lottery is shared between arms at equal seed numbers.** Q2 already says a matched
   failure points at start-up rather than names. Worth restating: `new_treatment_model(seed)` calls the
   frozen constructor first, so rows 0–51 and every Linear start from the control's draw for that seed.
6. **Disclosed exposure.** `FABLE-PREDICTIONS.md` states that the coordinator saw one builder
   observation before writing P94–P101: on a 500-update *fixture* seed-9 run, `code_scale` fell
   0.1386 → 0.0128 while `entity_output_bias` rose to +0.299. The disclosure is correct practice, but
   note that the reviewer's P1–P14 (written earlier) did not have it, and P9/P99 are about exactly that
   quantity. Both sets should be scored separately, as FABLE-PREDICTIONS already says.
7. **The 12-person cells are a slightly different task.** Q9's own note: four reserved codes name
   nobody there, and two of the four strictest 487 marks sit on `p12-1`/`p12-2`. A failure concentrated
   on the p12 cells should be read with that in mind and not as a general binding failure.

### Further MINOR items

**MINOR-6 — `cmd_report` does not emit everything condition 11 requires.** `report.txt` carries the
verdict, the per-cell R table (control and treatment-reserved), the paired-delta table, both
signatures with their raw splits, and the wide-64 cells. It does **not** carry: the `scale_trace`, the
speed-limit flag, the Q1 limitation sentence, the Q10 two-sided warning line, the "failure matched in
control" wording, or the treatment training-pool cells' absolute R (those are derivable as
`reserved R − paired delta`, and are in `scores/treatment-*.json` verbatim). All of it is available in
the JSON; condition 11 is a coordinator obligation on top of `report.txt`.

**MINOR-7 — the panel generator is not fully covered by the source fingerprint.**
`FROZEN_MODULES` includes `fable_confirmation_panels` (FC) but **not** `fable_dispatcher_v3`, which is
where the operator cells are actually built (`V3.CELLS`, `V3.build_world`, `V3.make_side`,
`V3._edit_world`, …), nor `fable_dispatcher`. Every output therefore records FC's hash but not the
generator's. The produced panels are still nailed down by their own content hashes in
`panels/manifest.json`, so this is not a hole in the data — but the freeze manifest should bind both
dispatcher files. Included in §8.

**MINOR-8 — condition 7's file list omits `scripts/fable_confirmation_panels.py`.** FC defines
`OPERATOR_CELLS`, hence `CELL_ORDER` and **the ten cutoffs the gate applies**. It must be in the freeze
manifest. Included in §8.

**MINOR-9 — `signature_summary` omits the control arm.** `gate_table` computes `control-<seed>`
signatures and stores them under `signatures`, but `signature_summary.never_started` /
`attributes_fine_link_at_chance` filter on names starting with `treatment`. P14 ("at least one control
seed shows the never-started signature") is still scorable from `signatures`, just not from the
summary — and `run_score.sh` prints only the summary. Read `gates.json`, not the launcher line.

**MINOR-10 — the machine is not currently quiet.** While auditing I observed another session writing
`scripts/fable_talker24_*.py` and `design/v3/25-*.md` in this same worktree, and a background load
average of 5.5–6.1. My timing above was measured *under* that load, so the ≈ 11 min projection already
includes it; but condition 8 ("the Mac is not running another heavy job during the wave") is a real
check the coordinator must make at launch, and a talker-24 training run would be exactly the kind of
job that breaks it.

**MINOR-11 — `assign_codes` draws with `rng.sample(range(total), people)` per world.** This is
`random.Random`, not torch, so it is unaffected by any torch seeding and is fully reproducible from the
frozen pool — which is the right property. Noted only because it means the code stream is *not*
recoverable from a torch seed in the checkpoint; it is recoverable from
`codes.code_namespace` + the pool, both of which are written into `training.json` and the checkpoint.
No action.

---

## 8. The eleven launch conditions

| # | Condition (rulings §5) | Status | Evidence / what remains |
|---|---|---|---|
| 1 | C1 applied exactly as written; no other change to `fable_newnames21.py` | **MET** | Reverting exactly the ruling's three hunks reproduces the recorded pre-C1 sha256 `f3a358e6…`; full read of the file found no other recipe-affecting code (§3) |
| 2 | Auditor confirms the C1 diff touches only the three named places (plus tests) | **MET** | Diff reproduced in §3: three hunks, all inside `train_run`, at the named lines; tests gained four cases, none changed |
| 3 | All tests pass after C1 | **MET** | My own run: `PASSED 35 FAILED 0 SKIPPED 0` |
| 4 | Post-C1: 50-update control bit-identity re-proved; 50-update treatment fingerprint equals pre-C1 | **MET** | §3.1 (`3b4cda9f…` both sides) and §3.2 (`fingerprints_equal true`, registered initial anchor reproduced, final `521d6a90…`); plus §3.3, which closes the `train_run` gap the builder's evidence left open |
| 5 | `run_data.sh` completed with the post-C1 script; `pool.json`, `panels/manifest.json`, `panels/audit.json`, `control-equivalence.json` exist and their gates passed | **COORDINATOR MUST DO** | Deliberately not run by me (§5 — it trains). Determinism of the pool and all panel data files verified twice in scratch, expected hashes in §5.1. The dev-source sweep and the 100-update replay are unverified by me |
| 6 | Auditor confirms per cell that `reserved` and `train` share worlds, questions and order, and that reserved codes appear nowhere in the training stream (first 50 updates checked directly) | **MET** | §2/Q6: 10 of 10 cells, identical ordered sequence of memory/questions/owner/targets, only the codes differ. §4.1: first 50 updates of all three registered seeds, 0 reserved rows touched; subset construction read and unit-tested |
| 7 | SHA-256 of the named files recorded in a new pre-registration note **and** in the predictions ledger; P1–P14 entered; timestamped before `run_train.sh` | **COORDINATOR MUST DO** | No pre-registration note exists in the experiment folder; `artifacts/fable-predictions-ledger.md` stops at P93, so neither P1–P14 nor P94–P101 are entered. Full path+hash list in §9 |
| 8 | The Mac is not running another heavy job; watchdog caps 1,680 / 1,740 / 1,770 s stand and are not raised | **PARTLY MET — COORDINATOR MUST DO** | Caps are in the code at exactly those numbers and are not raised (§6); `TERMINATE_SECONDS` is inert (MINOR-5). Machine quietness is a launch-time check, and another session is currently active in this worktree (MINOR-10) |
| 9 | No scoring until all six runs have written `completion.json`; heartbeats may be watched | **COORDINATOR MUST DO** | `score` refuses a run without `completion.json` (tamper-tested) and the gate returns INCOMPLETE, but `run_score.sh` would still score the completed runs before failing (MINOR-2). `S.LOG_EVERY = 250`, so the 500-update heartbeats do print, and they carry time, `code_scale` and `entity_output_bias` — no accuracy |
| 10 | M1 does not wait for the outside review; the registration is not amended after launch | **COORDINATOR'S COMMITMENT** | Nothing in the tree waits on an outside review; no code condition to check |
| 11 | Reporting: every seed, every cell, all three scorings, both signatures, the `scale_trace`, the speed-limit flag, the wide-64 cells, the Q1 limitation sentence, and only the §4 wording for the verdict | **COORDINATOR MUST DO** | All inputs exist in `scores/*.json`, `runs/*/training.json` and `gates.json`; `report.txt` covers roughly half (MINOR-6). The Q1 sentence to use verbatim: *"The three seeds differ in the model's starting weights, the blind-curriculum stream and (treatment only) the name stream. They do not differ in the training worlds. The result is therefore conditional on one world stream; it says nothing about other world streams."* |

---

## 9. The freeze manifest

### 9.1 Bind now (exists, hashed by me at audit time)

| path (relative to W) | sha256 |
|---|---|
| `design/v3/21-teachable-assistant-roadmap-fable-review.md` | `11dc2f73c01cec378b4dd6785059a059a807a44eb019dd49a7182da67f9f59d0` |
| `design/v3/21b-new-names-rulings-fable-review.md` | `7142b9c34419014098221203b46f4b10a609b608f24b4e61b98acbd9e94fd153` |
| `scripts/fable_newnames21.py` | `14336a4971e2976a60e8af31b29b2393e13aba6ee6bf0b190b759a9d85dac500` |
| `tests/test_fable_newnames21.py` | `f62ada7108d6a0aa7934b6ea8bfa4ba70033877e7d436345367c603bc09eb68d` |
| `artifacts/fable-newnames21-20260920/run_data.sh` | `7b837fdd20660cb690de6b3e5cf29c465eb060f1134aa6c069b823e8f19f9819` |
| `artifacts/fable-newnames21-20260920/run_train.sh` | `2351d4e6122b5a0477b209e197ff5032fc0ff58b705387782f82cfb471b98ff6` |
| `artifacts/fable-newnames21-20260920/run_score.sh` | `95087be9441bd2068c7582b1de8fc4f71c753a8ea4527141ba0f5470e569552f` |
| **added by this audit (MINOR-7, MINOR-8)** | |
| `scripts/fable_confirmation_panels.py` — defines `OPERATOR_CELLS`, `CELL_ORDER` and the ten cutoffs the gate applies | `c1d26dd2ce415d2c1490282b54739d6984a017556159c68f3a235982ee7414c6` |
| `scripts/fable_dispatcher_v3.py` — the actual cell generator, **not** in `FROZEN_MODULES` | `8fa4674d1b1dbcad5ae4fe51f4bfe74fe3fb6be3361569b825a4183be3aa8d53` |
| `scripts/fable_dispatcher.py` — imported by FC, **not** in `FROZEN_MODULES` | `2081a94cae4f3d152230e86d58772d4c5aeabdb03dac46be5efff85fefa91545` |
| **recommended for the record (not required by condition 7)** | |
| `artifacts/fable-newnames21-20260920/BUILD-NOTES.md` | `d28db9b945d87758c1589d93b89a89001fdd959f6ff37dbea9c11112170222db` |
| `artifacts/fable-newnames21-20260920/FABLE-PREDICTIONS.md` | `7cbf39a70493df819c9d1ba50a914fed09408a10e21f9b2839442ba59dae7526` |
| `artifacts/fable-newnames21-20260920/AUDIT-21.md` (this file) | hash after writing |

Note: BUILD-NOTES §7 says to re-hash itself once §7 is final — the value above is its hash as I read
it. If it is edited to record MINOR-4 (the 0.676 cosine), re-hash before the freeze.

### 9.2 Bind after `run_data.sh` (do not exist yet)

```
artifacts/fable-newnames21-20260920/pool/pool.json         (condition 7)
artifacts/fable-newnames21-20260920/pool/pool.pt           expected 4e5b5d86…f135c1d
artifacts/fable-newnames21-20260920/panels/manifest.json   (condition 7)
artifacts/fable-newnames21-20260920/panels/newnames21-panels.json
artifacts/fable-newnames21-20260920/panels/audit.json
artifacts/fable-newnames21-20260920/panels/wide64.json
artifacts/fable-newnames21-20260920/panels/forbidden-semantics.json   expected 788e0a7f…b97477f
artifacts/fable-newnames21-20260920/panels/{c1,c2,c3,c4,c5,c6,p12-1,p12-2,p12-3,s3}.pt
artifacts/fable-newnames21-20260920/panels/{wide64-attr,wide64-link,wide64-two}.pt
artifacts/fable-newnames21-20260920/control-equivalence.json
```

Expected content hashes for every `.pt` and `forbidden-semantics.json` are in §5.1 and were verified
byte-identical across two independent scratch builds. `pool.json`, `manifest.json`,
`newnames21-panels.json`, `audit.json`, `wide64.json` and `control-equivalence.json` embed absolute
paths and a `created_utc`, so their own hashes are only knowable from the real run. **If any `.pt`
hash differs from §5.1, stop and investigate before freezing.**

Also enter in `artifacts/fable-predictions-ledger.md`: the reviewer's **P1–P14** (from 21b §Q8) and the
coordinator's **P94–P101** (from `FABLE-PREDICTIONS.md`), each with the design-file sha256 it was
written against, before `run_train.sh` starts.

---

## 10. The registered command sequence

Run from anywhere (every launcher uses absolute paths and sets its own
`OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`; no `PYTHONPATH`, deliberately).

```bash
EXP=/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27/artifacts/fable-newnames21-20260920

# 1. data wave: pool -> panels (+ 64-person cells + audit) -> control-equivalence proof.
#    Must end with "DATA_DONE". ~2 minutes.
bash "$EXP/run_data.sh"

# 2. FREEZE.  Before any training:
#      - verify the .pt hashes against AUDIT-21.md section 5.1
#      - sha256 every path in AUDIT-21.md section 9.1 and 9.2 into a new pre-registration
#        note in $EXP, timestamped
#      - enter P1-P14 and P94-P101 in artifacts/fable-predictions-ledger.md
#      - confirm the Mac is otherwise idle (condition 8)

# 3. training wave: 6 runs (2 arms x 3 seeds), all six concurrent, one thread each,
#    6,000 updates, final checkpoint only.  Must end with "TRAIN_DONE".  ~11 min measured,
#    budget 17 min; caps 1,680 s / 1,740 s.
bash "$EXP/run_train.sh"

# 4. only after TRAIN_DONE and after all six runs/<arm>-<seed>/completion.json exist:
#    scoring -> gates -> report.  Must end with "SCORE_DONE" and print "VERDICT ...".
bash "$EXP/run_score.sh"

# 5. read the result, never the launcher summary alone:
cat "$EXP/gates.json"      # includes the control-arm signatures the summary line omits
cat "$EXP/report.txt"
```

Do not re-run a stage whose marker exists: `run_data.sh` skips a completed stage and refuses a
half-built folder, `run_train.sh` skips a run with `completion.json` and refuses a run directory
without one, `run_score.sh` skips a score file that exists. A run that dies leaves `failure.json` and
is **not** retried — per §4 of the rulings, a wave killed by the time cap may be re-run once,
unchanged, same seeds, only if no score file has been opened.

---

## 11. What I could not verify

* **The registered data wave itself.** I did not run `run_data.sh` (§5). The development-source overlap
  sweep, the UNVERIFIED-source failure path and the 100-update training-stream replay are unexercised
  by me. My determinism evidence is for the panel and pool *bytes* only.
* **Anything beyond 50 updates.** Both the control bit-identity and the C1 inertness proofs are
  50-update proofs, as the ruling specifies. Neither says anything about update 6,000.
* **The absence of a fourth pre-C1 change.** §3 proves my hunk-reverted reconstruction equals the
  *recorded* pre-C1 hash; it cannot prove that hash was taken from a clean file. My line-by-line read
  of the current script is the only guard, and it found nothing.
* **Six-way timing on a busy machine other than this one, at this moment.** Load was 5.5–6.1 during my
  measurement; a heavier wave would be slower.
* **Scoring-wave timing at n = 512.** I read the builder's fixture logs (35 s / 82 s with two
  concurrent processes) and did not re-measure.
* **The `.pt` hashes in §5.1 as *registered* artefacts.** They are reproducible predictions from two
  scratch builds, not the registered files.

---

FREEZE-READY: YES
