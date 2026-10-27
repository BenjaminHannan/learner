# Experiment 21 / M1 "new names" — build notes

Built, not run. The registered pool, the registered panels and the six registered runs do **not**
exist on disk: everything below was exercised on disposable fixture seeds in `fixtures/`, with
fixture RNG namespaces, so nothing registered has been pre-computed.

Design of record: `design/v3/21-teachable-assistant-roadmap-fable-review.md` §5. Where §5 is silent
or ambiguous, the choice made here is written down in §3 and §4 of this file and **is not settled** —
they are questions for the reviewer, not decisions taken on the reviewer's behalf.

---

## 1. The recipe that was identified and reused

| what | where |
| --- | --- |
| variant | `grow-blind` (label-free curriculum *and* label-free record construction) |
| configuration | `scripts/fable_operator_startup.py` → `configure_variant('grow-blind', seed=S, **registered_params('grow-blind'))` |
| hyper-parameters | read from the frozen launch manifest by `registered_params`, never re-typed: `balance=False, hint_updates=1000, grow_g1=1500, grow_g2=3000, distractors=2, blind_lines=16, startup='hintwarm-onehop', marg_visits=0, terminal_dedupe=True, single_forward=True` |
| model | `astra_canonical_operator.new_model(seed)` → `CanonicalOperator()` + `premonition_token_initialization_probe.rescale`; 79,316 parameters (asserted) |
| architecture | `premonition_token_memory.TokenMemoryReasoner`: vocab 68, width 48, 4 heads, 3 read steps, one `nn.Embedding(68,48)` shared between the input embedding and the **tied output head** |
| optimizer | `premonition_token_memory.optimizer_for` — AdamW, lr 1e-3, betas (.9,.99), eps 1e-8, weight decay .1; grad clip 1.0 |
| schedule | `fable_operator_variants.lr_at` — warm-up to 1e-3 over 100 steps, flat to 4,000, linear to 1e-4 at 6,000 |
| loss | pure answer cross-entropy, .75 canonical + .25 monolithic |
| batch | `A.training_batch(rng, 16, forbidden)` = `fable_operator_startup.training_batch_blind`, 16 visits, six-person worlds |
| world stream | `random.Random(1101)`; the blind curriculum's own stream is `random.Random(f'fable-startup-grow-blind:{seed}')` |
| updates | **6,000**, final checkpoint only |
| the loop | `astra_canonical_operator_run.worker`'s loop, call for call |
| scoring | `astra_canonical_operator_run.score_cell` (unmodified) → the fixed external loop `astra_canonical_operator.execute`, the single-forward `M` baseline, `truth_paths`, `oracle_inputs` |
| panels | `fable_confirmation_panels.build_operator_suite(folder, n=512, namespace=…, seed_base=…)` — the registered ten operator cells `c1…c6, p12-1…3, s3` with cutoffs 487/487/461/461/461/461/487/487/461/461 and its own `forbidden-semantics.json` |
| exclusions | the **union** of the registered screen's `forbidden-semantics.json` and this experiment's fresh panel exclusions, handed to the trainer as `forbidden` and checked at **every** update |

Everything in that table is **imported**, not copied. `scripts/fable_newnames21.py` contains no
re-implementation of the recipe; the only recipe-shaped code in it is the six-line training loop,
which exists because the treatment needs one extra call inside it (binding this update's codes).

### Registered timing anchor

`artifacts/fable-operator-grow-blind-20260920/astra_canonical_operator_seed-{0..5}/training.json`:
6,000 updates in 623.6, 627.3, 628.1, 669.7, 670.5, 673.0 seconds, three processes per wave.

---

## 2. Control-equivalence evidence

Two independent anchors, both produced by `fable_newnames21.py train --equivalence N` and both
checked as hard gates inside `run_data.sh`:

1. **Registered initial fingerprint, from a file nobody here wrote.**
   `astra_canonical_operator.new_model(0)` rebuilds to
   `111b4141b8611850a5c8edf8a296c3c09d1f29ae73bd481c509f3e1d02b1cd5a`, which is exactly the
   `initial_fingerprint` recorded in the registered grow-blind seed-0 run.
2. **Update-by-update equality of the whole parameter vector.** 50 updates (12 in the unit test,
   8 in the fixture launcher run) of this file's control path against
   `reference_updates`, which drives the registered functions directly. Compared after **every**
   update by `premonition_memnn_compare.fingerprint` (sha256 over the sorted state dict), plus the
   answer loss before every update.
   Observed: `fingerprints_equal: true`, `first_differing_update: null`, `losses_equal: true`,
   `max_abs_loss_difference: 0.0`.

Fingerprint equality is strictly stronger than the loss equality §5's brief asked for as a fallback:
two runs can share a loss curve and differ in parameters, but not the reverse.

---

## 3. Judgement calls where §5 is silent

Each of these is a real scientific choice. None of them is hidden in the code; each is written into
the pool summary or the run manifest, and each is listed again in §4 as a question.

**(a) Code distribution.** §5 says "random codes" and gives no distribution. Chosen: each code is an
independent standard-Gaussian direction in R^48 **normalised to unit length** — uniform on the unit
sphere. Rationale: it puts every person's identity entirely in a direction and every person's
loudness entirely in the one learned scale, which is what makes "one learned scale" a meaningful
single knob. Measured over the 4,096 codes: max |cosine| between two codes 0.699, mean |cosine|
0.116 (the sphere's own √(2/π·48) = 0.115).

**(b) Code scale rule, fixed before training.** `code_scale` is initialised to
`0.02 × √48 = 0.13856`, i.e. the root-mean-square norm of a control entity row at initialisation
(`TokenMemoryReasoner._initialize` draws every embedding row from N(0, .02²)). Sanity check on a
real control model: the mean entity-row norm is 0.1409 against this 0.1386. This is the *only*
scale rule in the file and it is recorded in `pool/pool.json` before a single update.

**(c) How many codes are bound, and what the answer candidates are.** The treatment always binds
**16** codes per world, including on the 12-person cells, so the answer candidate set is the same
size as the control's (68 = 52 shared rows + 16 entity rows) in every gated cell. A 12-person world
therefore carries four codes that name nobody, exactly as the control carries four entity rows that
name nobody. The alternative — scoring against all 4,096 pool codes — is a much harder and arguably
more interesting test, and it is **not** what is implemented; see question Q5.

**(d) 64-person worlds.** Worlds are built by hand (people 0…63, entity tokens 52…115) and passed to
the **frozen** generator `premonition.toy_ladder.visit(spec, rng, training=True, world=…)`, which is
the same escape hatch `fable_story_size_stress.build_world` already uses. 64 people × (3 attributes
+ 1 link) = 256 facts, as §5 says. Codes come from the **reserved** half. Scoring reuses the
registered executor under a `widened_entities` context manager that rebinds `A.ENTITY_MAX` (which
`execute` and `truth_paths` read at call time) and restores it even on an exception — so the *same
code object* runs, not a copy. This is used for the descriptive cells only; the ten gated cells are
always scored with the module untouched, and a unit test asserts the range is restored.
The descriptive panels are split by question shape (`wide64-attr`, `wide64-link`, `wide64-two`)
because `score_cell`'s per-stage LINK diagnostic indexes every record's link list by position and is
only meaningful within a homogeneous panel.

**(e) Tied-output handling.** `TokenMemoryReasoner.forward` ends with
`F.linear(answer, self.embedding.weight, self.output_bias)`. Rather than copy that forward, the
treatment replaces `embedding` with a constant identity matrix and `output_bias` with a constant
zero vector, so the frozen forward returns the **answer state**; `embed` is overridden to index a
per-world table, and the per-world tied head is applied afterwards as
`einsum(answer, code_scale·code) + entity_output_bias`. Verified numerically: with the codes set to
a control model's own entity rows and `code_scale = 1`, the treatment's logits equal the control's
to 1.0e-7 (up to the per-entity output bias that §5 deliberately replaces by one shared scalar).
Rows 0…51 (structure, relations, values, filler) remain ordinary trained parameters.

**Parameter count.** 79,316 − 68·48 − 68 + 52·48 + 52 + 1 + 1 = **78,534** trainable, against the
control's 79,316. Fewer, as §5 requires. Asserted in a unit test.

**(f) "Re-drawn for every world".** Read as: a fresh 16-code assignment for **every visit of every
update** (16 worlds × 6,000 updates = 96,000 assignments per run), drawn from one
`random.Random(f'newnames21/train-codes:{seed}')` stream so the whole sequence is reproducible from
the frozen pool. Codes are distinct within a world and independent across worlds. See Q3.

**(g) Panel code assignment.** Keyed by `(namespace, pool, cell, chunk)` and **not** by seed, so all
three seeds are scored on exactly the same names and the reserved-vs-training-pool comparison is
paired down to the chunk. Both sides of a pair cell always get the same codes (unit-tested), so the
edited-pair cells stay valid. See Q6.

**(h) Watchdog caps.** `TRAINING_SECONDS=1680`, `WORK_SECONDS=1740`, `TERMINATE_SECONDS=1770`. These
are **not** part of the recipe (the registered manifest's own caps were set for a three-process
wave; this one runs six). A cap only ever aborts a run; it never shortens one.

**(i) Failure-signature thresholds.** §5 names the two signatures but gives no numbers. Chosen:
*never started* = c1 **and** c2 both at or below 2× chance (64/512); *attributes fine, LINK at
chance* = every one-call attribute relation at or above 0.90 **while** every first-stage LINK
accuracy is at or below 2× chance. Both are emitted with the raw per-relation split behind them, so
the reviewer can re-judge them from the JSON without re-running anything. See Q7.

**(j) The audit's scope, stated honestly.** `panels` writes `audit.json` with three checks:
within-suite disjointness (the builder's own hard failure), overlap against every development panel
and exclusion file on this machine (an unchecked source is recorded as UNVERIFIED and fails the
launcher), and a **partial** replay of the training stream (100 of 6,000 updates by default), which
certifies only the updates it replayed and says so. The complete guarantee that these runs'
training worlds never appear in the panels is the run-time `forbidden` check applied at all 6,000
updates, which raises `RuntimeError('training/validation semantic overlap; run invalid')` and kills
the run.

---

## 4. Open questions for the reviewer — please rule before the wave is launched

**Q1 — "per-seed world stream", but the frozen recipe's world stream is seed-independent.**
§5 says "per-seed world stream shared by both arms". The registered grow-blind recipe draws worlds
from `random.Random(1101)` — the *same* stream for every seed — and only the blind-curriculum RNG
and the model initialisation depend on the seed. Making the world stream seed-dependent would change
the control from the frozen recipe, which §5 forbids in the same breath. **Built as: the frozen
`random.Random(1101)`, shared by both arms, identical across seeds.** If the reviewer meant a
genuinely per-seed world stream, the control arm is no longer "exactly as is" and both arms need a
new pre-registration.

**Q2 — the control's "own marks" are not defined.** §5 says "the control must meet its own marks in
≥ 2/3 seeds or the run is void". **Built as: the same ten cutoffs (487/461).** If the control is
meant to be held to the marks the *registered* grow-blind runs actually achieved on the registered
screen panels, that is a different and probably stricter test, and it needs numbers.

**Q3 — how often are codes re-drawn?** "Re-drawn for every world" is built as every visit of every
update (§3f). The alternative readings are once per update (all 16 visits share a draw — clearly
wrong) or once per *world identity* held fixed across the run (which would defeat the point). Please
confirm.

**Q4 — should `code_scale` learn at all, and should it be shared with the value rows?** §5 says "one
learned scale", so it is a trainable scalar initialised by the §3b rule and nothing else about a
code moves. Note the interaction with the predicted failure: §5's own scale-mismatch story is that
"trained value embeddings grow during training, fixed codes do not" — a single learned scale is
exactly the knob that could absorb that, so if the LINK-at-chance signature *does* fire, the first
thing to check is whether `code_scale` moved (it is recorded in the checkpoint). If the reviewer
wants the harder version — codes at a *fixed* scale, nothing learned — that is a different arm.

**Q5 — answer candidates: 16 world codes, or the whole pool?** Built as 16 (§3c), matching the
control's candidate set exactly, which is what "one change" implies. But a model that must pick the
right person out of 4,096 unseen codes is the claim the milestone is really about. If the reviewer
wants that, it is a second scoring, not a change to this one.

**Q6 — should panel codes differ per seed?** Built as seed-independent (§3g), which makes the paired
reserved-vs-training comparison exact but means one unlucky draw of names is shared by all three
seeds. Per-seed panel codes would decorrelate that at the cost of a less clean pairing.

**Q7 — the failure-signature thresholds (§3i) are mine.** Please confirm or replace the numbers;
they are named in advance precisely so that they cannot be chosen after the fact.

**Q8 — the predictions in §5 are "to be hashed" and have not been hashed.** The file writes no
prediction record. If those four probabilities (3/3: 0.35; ≥1 seed: 0.65; training-pool passes but
reserved fails: 0.05; control reproduces ≥2/3: 0.85) are to be registered, they need to be written
and hashed **before** `run_train.sh` is started; this build deliberately did not do that on the
reviewer's behalf.

**Q9 — the 12-person cells and the reserved half.** §5 asks for the reserved-code scoring on all ten
cells, including `p12-1..3`. Built that way. Worth noting that a 12-person world with 16 bound codes
means four reserved codes appear as distractor answers that name nobody; that is faithful to the
control but it is a slightly different task from the six-person cells, and it is where the 487 mark
sits for two of the four strictest cells.

**Q10 — nothing in §5 says what happens if the control passes 3/3 and the treatment passes 3/3 on
reserved codes but *fails the paired mark* because it is better on reserved than on training-pool.**
The paired mark as written is one-sided (≥ −13/512), so "better on reserved" passes. Built literally.
That is almost certainly right, but it is the kind of asymmetry worth confirming.

---

## 5. What is in this folder

```
BUILD-NOTES.md     this file
run_data.sh        pool -> panels (+ 64-person cells + audit) -> control-equivalence proof
run_train.sh       6 one-thread runs (2 arms x 3 seeds), sentinels TRAIN_DONE / TRAIN_FAILED
run_score.sh       score 6 runs -> gates -> report, sentinel SCORE_DONE
fixtures/          DISPOSABLE. fixture seeds, fixture RNG namespaces, tiny update counts.
                     exp/        n=16 panel suite + seed-9 runs + scores (unit-test fixture)
                     exp512/     n=512 panel suite, used only to time a full-size scoring
                     exprun/     produced by fixtures/launchers/*.sh, an end-to-end rehearsal
                     launchers/  the three launchers with EXP/seeds/sizes rewritten for fixtures
                     timing/     per-regime seconds-per-update measurements
```

Nothing registered is present: there is no `pool/`, no `panels/`, no `runs/`, no `scores/`,
no `gates.json` and no `report.txt` at the top level of this folder.

## 6. Timing (measured, then projected)

Measured on this Mac (10 logical cores, 8 performance + 2 efficiency) with **two** concurrent
one-thread processes, background load already at 6–9, fixture seed 9, 80 updates at each curriculum
regime (`--fixture-step0` pre-advances the curriculum clock; it is refused for the registered seeds):

| curriculum stage | control s/update | treatment s/update |
| --- | --- | --- |
| reduced stories (step < 1,500) | 0.0566 | 0.0583 |
| mid-ramp (step 2,250, fraction 0.5) | 0.0944 | 0.0964 |
| full stories (step ≥ 3,000) | 0.1231 | 0.1252 |

Integrating over the 6,000-update grow curriculum (1,500 reduced + 1,500 ramp by Simpson + 3,000
full): **control ≈ 593 s, treatment ≈ 605 s per run.** The six runs are parallel, so the wave is the
slowest run, not the sum. The treatment costs about 2 % more per update than the control.

Cross-check: the registered three-process grow-blind wave took 623–673 s for the same 6,000 updates,
so the projection is in the right place.

**Projection for the wave.** Nominal ≈ **10.1 min**. Six processes on an already-loaded 10-core Mac
will contend more than two did; at a 1.5× contention penalty the wave is ≈ **15.2 min**, and
applying the required 1.5× safety margin on top gives ≈ **22.7 min** — under the 30-minute cap, but
not by a wide margin. It would take a 3× contention penalty to breach 30 minutes.
*Caveat, stated plainly:* the fixture budget allowed at most two concurrent processes, so six-way
contention on this machine was **projected, not measured**. If the Mac is busy when the wave is
launched, watch the first `{"updates": 500}` heartbeat in `logs/train-*.log`: at 0.06 s/update the
first 500 updates should take about 30 s, and anything past 60 s means the wave will not fit and
should be stopped and re-launched on an idle machine. The recipe must not be shortened.

Scoring (a separate wave, not inside the 30 minutes): measured at 512 units per cell with two
concurrent processes — 35 s for a control run, 82 s for a treatment run (two scorings plus the
64-person cells). `run_score.sh` runs three at a time; the whole wave is a few minutes.

Data wave: the pool takes under a second; the 512-unit panel suite about 3 s; the audit is dominated
by the development-source sweep and the 100-update replay, a few tens of seconds; the
control-equivalence proof about 60 s at 50 updates.

---

## 7. C1 applied (rulings 21b) — 20 September 2026

`design/v3/21b-new-names-rulings-fable-review.md` §Q4 orders one code change, C1, logging only. It
is applied. Nothing else in `scripts/fable_newnames21.py` was touched; no other file in the
repository was edited except `tests/test_fable_newnames21.py` and this section.

### What changed in `scripts/fable_newnames21.py`

Three places inside `train_run`, exactly the three the ruling names, with the ruling's own code:

1. `scale_trace = []` on the line after `flops, intervals = 0, []` (now line 841), before the
   training loop.
2. The 500-update heartbeat block (now lines 862–872) replaced by the ruling's version: the
   `updates_done % 500 == 0` test no longer depends on `log_every`; on the treatment arm the beat
   gains `code_scale` and `entity_output_bias` (both read with `.detach()` and converted to Python
   floats) and a row is appended to `scale_trace`; the `print` is what `log_every` now guards, so
   the trace is recorded even with the heartbeat print switched off.
3. `scale_trace=scale_trace if arm == 'treatment' else None,` added to the `training = dict(...)`
   that becomes `training.json`, between `trainable_parameters=` and `exclusion=`.

**Deviation from the ruling's text: none.** The ruling's snippets matched the source verbatim
(names, indentation and the surrounding lines), so all three were applied as written. The only
freedom taken is the *position* of the new key inside the `training` dict, which the ruling leaves
open.

Cost of the one behavioural difference: on a run with printing off, the loop now builds and throws
away a small dict once every 500 updates (12 times in a 6,000-update run). It consumes no random
number, allocates no tensor and touches no parameter.

### Tests

`tests/test_fable_newnames21.py` gains four tests (31 → **35**; the whole file still runs in about
4 s) and one paragraph in its header docstring. No existing test was changed.

* `test_scale_trace_is_recorded_at_every_500th_update_with_printing_off` — 1,000 updates with
  `log_every=0`: the trace has rows at 500 and 1,000, each with exactly the keys `updates`,
  `code_scale`, `entity_output_bias`, each value a Python `float` and equal to the parameter value
  those updates must have produced; nothing is printed.
* `test_treatment_heartbeat_prints_the_scale_and_the_bias` — with printing on, the printed beat
  carries the two extra keys and matches the recorded row.
* `test_scale_trace_is_none_for_the_control_arm` — the control writes the key as `null` and its
  beat keeps its original four keys.
* `test_scale_trace_is_empty_before_the_first_heartbeat` — a run shorter than 500 updates records
  an empty trace and does not crash.

These four stub `A.training_batch` / `A.training_flops` / `A.training_step` (installed from inside
a wrapped `configure_recipe`, because `configure_variant` rebinds the first and third itself) so
that 1,000 loop turns cost nothing: C1 is loop bookkeeping, and the stub moves `code_scale` and
`entity_output_bias` by a known amount per update so the recorded numbers can be checked exactly.
The stubs are removed again in a `finally`. A **real** 500-update treatment run (fixture seed 9, not
a registered seed, in a scratch folder) was also done by hand as an end-to-end check: the heartbeat
line printed `code_scale` and `entity_output_bias` and `training.json` carried the matching
single-row trace.

Full suite after C1: `PASSED 35  FAILED 0  SKIPPED 0`
(`OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 python3.12 -B tests/test_fable_newnames21.py`,
fixture exp at its default path). Before C1 the same command gave `PASSED 31  FAILED 0  SKIPPED 0`.

### Proof by run, before and after (condition 4 of §5 of the rulings)

Both proofs were run twice with identical arguments — once with the pre-C1 script, once with the
post-C1 script — into a scratch directory. No registered output folder was created or written:
`pool/`, `panels/`, `runs/`, `scores/`, `control-equivalence.json` are still absent from this
folder. Both runs used this folder's `fixtures/exp` for the pool and the exclusion set, because the
registered pool and panels do not exist yet (`run_data.sh` has not been run); that choice is
identical on both sides of the comparison, which is all the proof needs.

**(a) 50-update treatment run, seed 2100** (`train --arm treatment --seed 2100 --updates 50`):

| | before C1 | after C1 |
|---|---|---|
| `initial_fingerprint` | `735c04107fad0568768db55769879ce9beb443f7926c5cf0f11e1962dd84207d` | same |
| `final_fingerprint` | `3b4cda9f8d350a2cfdb76e08141156f941ce55a54ddbc1fcf27f30299b8699ae` | **identical** |
| `flops` | 51,519,045,888 | same |
| `trainable_parameters` | 78,534 | same |

The only keys of `training.json` that differ between the two runs are `scale_trace` (absent → `[]`,
since 50 < 500), the provenance keys `source_fingerprint` / `source_files` / `created_utc`, the
timing keys and `peak_rss_bytes`, and `checkpoint_sha256` — which moves only because the checkpoint
embeds the script's source fingerprint, exactly as the ruling anticipated. The script's source
fingerprint is `d3ebd511c2362affc78039bc5dd6f9903c9c361b57339a6924eb3964a821967c` before C1 and
`ef6444768b373da6356413a6e8eff77004ff3887189fc664db544c7514fc2451` after it.

**(b) 50-update control equivalence, seed 0** (`train --seed 0 --equivalence 50`), re-proved with
the post-C1 script:

| | before C1 | after C1 |
|---|---|---|
| `fingerprints_equal` | `true` | `true` |
| `first_differing_update` | `null` | `null` |
| `losses_equal` / `max_abs_loss_difference` | `true` / `0.0` | `true` / `0.0` |
| registered grow-blind seed-0 `initial_matches` | `true` (`111b4141…cd5a`) | `true` (`111b4141…cd5a`) |
| control-path 50-update `final_fingerprint` | `521d6a90f9747eaa81ac7afdfbc47bef9e8e33b24129fddf28e2d3d87a585262` | **identical** |

So after C1 the control path is still the registered grow-blind recipe, update by update, and the
treatment's 50 updates land on the same parameters as before. C1 changes no computation.

**Still outstanding for §5's condition 5:** `control-equivalence.json` in this folder must be
produced by the post-C1 script during `run_data.sh` against the *registered* pool and panels. The
scratch proof above is evidence that C1 is inert; it is not the registered artefact.

### Hashes after C1

| file | sha256 |
|---|---|
| `scripts/fable_newnames21.py` | `14336a4971e2976a60e8af31b29b2393e13aba6ee6bf0b190b759a9d85dac500` |
| `tests/test_fable_newnames21.py` | `f62ada7108d6a0aa7934b6ea8bfa4ba70033877e7d436345367c603bc09eb68d` |

(Their pre-C1 values were `f3a358e66562693810cff02f479ca38190749642d61db8c46729aa7724e9d320` and
`e8be02bbe8ddb6b33996e81e701937b0a1c21ae8122a3652356e16dd863b1b74`. The post-C1 hashes above are
the ones to record in the pre-registration note of §5 condition 7; re-hash this file itself after
this section is final.)
