FREEZE-READY: NO

# AUDIT-27 — independent audit of experiment 27 / M1-F ("new names", name scale frozen at 1.2)

Independent auditor, 2026-09-21. I did not build any of this. Everything below that is stated as a
fact was re-derived by me from the files or from my own scratch runs; where I am quoting the
builder's own evidence I say so.

Scope of my own work: read-only inspection of the code and the design, plus my own runs in a
scratch directory outside the repository (fixture seeds 4242–4345 only, 3–30 updates each, a
16-unit fixture panel suite in a fixture namespace). **I trained nothing, scored nothing and
generated no panel for seeds 2103–2105.** I edited no file under audit, made no commit, used no
cloud machine and no BensPC, loaded no `test.pt`, and wrote exactly one file into the experiment
folder: this report.

---

## 0. Verdict

**FREEZE-READY: NO** — but narrowly, and not because of the science.

The scientific core is sound and I could not break it. The one change is the one change; the
control is bit-identical to experiment 21's control; the frozen buffer genuinely cannot move and
the INVALID path fires on a one-ULP nudge; the reserved half of the pool is unreachable from every
training sampler; every gate, every pre-named signature and the two-sided warning compute exactly
as the design words them, including at the boundaries; the trace is inert; wave 1 will take about
eleven minutes.

I am withholding freeze-ready on **one MAJOR item with two parts**: the build refuses four fixture
escapes on the registered seeds but leaves the most consequential one — the number of updates —
open, and nothing anywhere compares the source fingerprint recorded at training time against the
one in force at scoring time. Both are gate-side or guard-side additions that cannot change a
single trained number, and both are a few lines. With §2's required change applied (and the script
re-hashed, the tests re-run), this is freeze-ready.

Findings: **0 BLOCKING, 1 MAJOR (two parts), 8 MINOR.**

---

## 1. Fingerprints, provenance and the forecast ordering

### 1.1 Hashes — all confirmed

| file | claimed | mine |
| --- | --- | --- |
| `design/v3/27-new-names-followup-design-fable-review.md` | `63d2bb51…d990` | **matches** |
| `scripts/fable_newnames27.py` | `688ad94c…9387` | **matches** |
| `tests/test_fable_newnames27.py` | `6f19cd47…599f` | **matches** |
| `artifacts/…/run_data.sh` | `62b13de0…7798` | **matches** |
| `artifacts/…/run_train.sh` | `fb8dbf5a…1231` | **matches** |
| `artifacts/…/run_score.sh` | `455546e8…7b43` | **matches** |
| `artifacts/…/BUILD-NOTES.md` | `901208a6…13c1` | **matches** |

`FABLE-PREDICTIONS.sha256.txt` re-hashes correctly against `FABLE-PREDICTIONS.md`
(`5c68e806…d035`).

### 1.2 The forecasts predate the code — confirmed

Modification times on disk:

```
20:48:20  design/v3/27-new-names-followup-design-fable-review.md   (holds R27-P1..P14, §5)
20:49:18  artifacts/fable-newnames27-20260921/FABLE-PREDICTIONS.md (P118..P125)
20:49:18  artifacts/fable-newnames27-20260921/FABLE-PREDICTIONS.sha256.txt
20:49:28  artifacts/fable-predictions-ledger.md                    (rows R27-P1..P14, P118..P125)
21:00:47  scripts/fable_newnames27.py            <- the first line of experiment-27 code
21:12:07  tests/test_fable_newnames27.py
21:16–21  run_data.sh, run_train.sh, run_score.sh, BUILD-NOTES.md
```

Both forecast sets are written, hashed and entered in the ledger (all `pending`) **eleven minutes
before the first line of experiment-27 code exists**. The exposure both forecasters had — design
§0.3's fixture-seed probe F — is disclosed in both documents. I accept the ordering.

One note for the coordinator, not a defect: R27-P4 and P121 both key on "first-stage LINK accuracy
on c2 ≥ 0.50". That number is `scores/F-<seed>.json →
`scorings.reserved.cells.c2.diagnostics_by_operation.first_link_stage.accuracy`, and it exists.
R27-P9's "effective name scale in [10, 25]" is `trace_summary.final_effective_name_scale`, and it
exists. R27-P13 and R27-P14 are resolvable from `gates.json` and `readouts/*.json`. Nothing in the
forecast set is unresolvable from what the pipeline writes.

### 1.3 Source fingerprint coverage — improved over experiment 21

`source_files()` = experiment 21's set plus `fable_newnames27.py`; the set now includes
`fable_confirmation_panels.py` and `astra_canonical_operator_panels.py`, which closes experiment
21's MINOR-7/MINOR-8. Fifteen files, fingerprint `b9c5d164…f301` at audit time.

---

## 2. MAJOR — the two integrity holes the gate does not close

### 2.1 `--updates` is not refused on a registered seed, and the gate never checks it

`train_run` carefully refuses four fixture escapes on seeds 2103–2105:

```python
overrides = dict(code_scale=code_scale, code_namespace=code_namespace,
                 trace_every=None if trace_every == TRACE_EVERY else trace_every)
if seed in SEEDS:
    assert not any(v is not None for v in overrides.values()), ...
    assert not fixture_step0, ...
```

`updates` is not among them, and neither `completion.json`, `cmd_score` nor `gate_table` ever
compares the recorded `updates` against `UPDATES = 6000`.

I demonstrated the hole without touching a registered seed, by rebinding `SEEDS` to a fixture seed
and training three updates:

```
short_run_on_registered_seed: {accepted: true, updates: 3, completion_says_complete: true}
```

The run writes `final.pt`, `training.json` and `completion.json` with `"complete": true`, scores
normally, and reaches the gates indistinguishable from a 6,000-update run. This is exactly the
failure mode the brief calls "report from a partial set as if complete", and it is the one escape
the build does not refuse while refusing four less consequential ones.

Mitigation that exists: `run_train.sh` always passes `--updates 6000`, and the true value is
recorded in four places. So this is a hole in the guard rail, not evidence of anything wrong.

### 2.2 The source fingerprint is pinned but never compared

Every checkpoint carries `source_fingerprint` at training time; `training.json`, every
`scores/*.json` and `gates.json` carry the fingerprint in force when *they* were written. Nothing
compares them. I confirmed by inspection of `cmd_score`, `load_checkpoint` and `gate_table` that
the string `source_fingerprint` never appears in a comparison:

```
source_fingerprint_compared_at_scoring: false
```

So a mid-run edit to `fable_newnames27.py` (or to any frozen module) between run 3 and run 4, or
between training and scoring, is *recordable* but not *detected*: it would take a human diffing
fifteen JSON files to notice. `load_checkpoint`'s fingerprint check is a check of the **model
weights** against the checkpoint's own record, which is a different guarantee and does not cover
this.

### 2.3 Required change (one edit, gate-side only, changes no trained number)

Add to `fable_newnames27.py`:

```python
def run_integrity(exp):
    """Every scored run must be a FULL run, produced by ONE version of the source."""
    rows, problems = {}, []
    for arm in ARMS:
        for seed in SEEDS:
            path = Path(exp)/'runs'/f'{arm}-{seed}'/'training.json'
            if not path.exists():
                continue
            row = json.loads(path.read_text())
            rows[f'{arm}-{seed}'] = dict(updates=row['updates'],
                                         source_fingerprint=row['source_fingerprint'],
                                         overrides=row.get('overrides'))
            if row['updates'] != UPDATES:
                problems.append(f'{arm}-{seed}: {row["updates"]} updates, not {UPDATES}')
            if row.get('overrides'):
                problems.append(f'{arm}-{seed}: overrides {row["overrides"]}')
    prints = {r['source_fingerprint'] for r in rows.values()}
    if len(prints) > 1:
        problems.append(f'runs were produced by {len(prints)} different source versions')
    return dict(runs=rows, source_fingerprints=sorted(prints), problems=problems)
```

and in `gate_table`, immediately after `invalid = invalid_runs(exp)`:

```python
integrity = run_integrity(exp)
if invalid or bad_buffer or integrity['problems']:
    verdict, reason = 'INVALID', ('the frozen code_scale changed / a run is not a full '
                                  f'registered run: {[r["run"] for r in invalid] + bad_buffer + integrity["problems"]}')
```

with `integrity=integrity` in the returned dict and a line in `cmd_report`.

And in `train_run`, add `updates` to the refused overrides for the registered seeds:

```python
overrides = dict(code_scale=code_scale, code_namespace=code_namespace,
                 trace_every=None if trace_every == TRACE_EVERY else trace_every,
                 updates=None if updates == UPDATES else updates)
```

(the `overrides` dict is already filtered to non-`None` values before it is written, so the
registered `training.json` is unchanged).

Neither edit touches the model, the optimiser, the data stream, the scorer or any mark. After the
edit: re-run `tests/test_fable_newnames27.py`, re-hash `scripts/fable_newnames27.py`, and update
the hash table in `BUILD-NOTES.md` and in the freeze note.

---

## 3. The one change — re-derived by me, not taken from the builder's tests

### 3.1 The model

`FrozenScaleOperator` subclasses experiment 21's `NewNamesOperator`, lets the parent constructor
build the entire model (so the seeded draw is untouched), then deletes `_parameters['code_scale']`
and registers a persistent buffer of the same value. My measurements on fixture seed 4242:

| | control | F | L |
| --- | --- | --- | --- |
| trainable parameters | 79,316 | **78,533** | **78,534** |
| named parameters differing | — | `L − F = {code_scale}` | |
| every shared weight bit-identical F vs L | — | **true** | |
| initial parameter fingerprint F vs L | — | `1c998ac9…a3ee` | `1c998ac9…a3ee` (**equal**) |
| `code_scale` value at construction | — | 1.2000000476837158 | 1.2000000476837158 |
| in `parameters()` | — | **no** | yes |
| `requires_grad` | — | **false** | true |
| in `state_dict()` / `named_buffers()` | — | **yes / yes** | yes / — |
| tensors in `optimizer_for(model)` | — | **66** | **67** |
| optimiser groups / weight decay | 1 / 0.1 | **1 / 0.1** | 1 / 0.1 |

`I.rescale` touches only `nn.Linear` weights (`premonition_token_initialization_probe.py:16-20`),
so demoting the scalar to a buffer does not change what `rescale` does to anything else — and
`new_F_model` calls `check_frozen('at construction')` *after* `rescale`, which would catch it if it
did. I verified the buffer is still exactly 1.2000000476837158 after `rescale`.

`A.training_step` clips with `clip_grad_norm_(model.parameters(), 1.)`
(`astra_canonical_operator.py:127`), and `optimizer_for` is one AdamW group over
`model.parameters()` (`premonition_token_memory.py:160-161`). A buffer is in neither. Design 4.1's
stated reason for demanding a buffer rather than "a parameter left out of the optimiser" is
therefore honoured exactly.

**A caveat the report must carry, and which the design already licenses.** Arm F is *not*
"experiment 21's treatment with the scalar pinned at 1.2": it is experiment 21's treatment with the
scalar removed from the parameter set, so the gradient-clip factor is computed over 66 tensors
instead of 67 and every other parameter's update differs marginally from what a pinned-parameter
version would give. Design 4.1 demands precisely this, for precisely this reason. The claim wording
in design 4.8 ("the loudness of names fixed by hand at 1.2") is compatible. Any looser wording —
"we only changed one number" — would be an over-claim.

### 3.2 The control, re-derived independently (fixture seed 4242, 25 updates)

I ran experiment 27's control path and experiment 21's control path side by side over the same
scratch experiment folder, and separately drove the **registered** functions (`A.new_model`,
`A.training_batch`, `A.T.optimizer_for`, `A.training_step`) through `N.reference_updates`:

```
n_tensors                 65
tensors_equal             true      (exp27 control state dict == exp21 control state dict)
init_equal                true
final_equal               true
registered_init_equal     true      (== fingerprint of A.new_model(seed))
registered_final_equal    true      (== the registered-functions loop after 25 updates)
trainable                 79316
flops_equal               true
registered_params equal   true      (same grow-blind manifest)
exclusion                 registered 6656 + fresh 208 = union 6864
```

So experiment 27's control arm is experiment 21's control arm, byte for byte, in the same data
wave, and both are the registered recipe. This is my own derivation; I did not read the builder's
`control_equivalence` result before running it, and I did not rely on it.

The seeds differ (2103–2105 against 2100–2102) and the fresh panel suite makes the training
exclusion set different from experiment 21's, so the world stream is *not* the same stream
experiment 21 ran. That is by design (fresh confirmation panels) and is unavoidable: any
"bit-identity with experiment 21's registered control runs" claim would be false. The build does
not make it. C15 says so explicitly. **Ruling: acceptable.**

### 3.3 Everything on the "must not change" list (design 4.7)

Checked one by one against experiment 21 by import rather than by copy. `CELL_ORDER`, `CUTOFFS`,
`PAIRED_SLACK`, `PANEL_N`, `UPDATES`, `VISITS`, `POOLS`, `VARIANT`, `CHANCE`, `NEVER_STARTED_AT`,
`LINK_CHANCE_AT`, `ATTRIBUTES_FINE_AT`, `REGISTERED_EXCLUSION`, `REGISTERED_GROW_BLIND`,
`TRAINING_SECONDS`, `WORK_SECONDS`, `seed_verdict`, `failure_signatures`, `cell_programs`,
`cell_diagnostics`, `panel_paths`, `load_panel`, `training_exclusion`, `configure_recipe`,
`pool_subset`, `assign_codes`, `refuse_existing`, `tensor_sha`, `configure_once` are all `N.<name>`
aliases — the same code object, not a re-implementation. Cutoffs I read out directly:
c1/c2/p12-1/p12-2 = 487, the other six = 461, exactly design 4.4. World stream `random.Random(1101)`
in both `train_run` and `control_path_updates`. 6,000 updates × 16 visits. AdamW lr 1e-3, warm-up
`min(1, (step+1)/100)`, weight decay 0.1 on one group, clip 1.0 — all inside the frozen
`A.training_step`, which experiment 27 calls and does not wrap.

---

## 4. The buffer cannot move, and the INVALID path fires — tamper-tested

Three separate attacks, all in scratch:

**(a) Mid-training movement, one ULP.** I patched `A.training_step` (after `configure_variant`
rebinds it — patching before is silently undone, which is worth knowing) to nudge `code_scale` by
one float32 ULP at 1.2, i.e. 1.2000000476837158 → 1.1999999284744263, after update 3 of an arm-F
run:

```
tamper_train        raised: code_scale moved from 1.2000000476837158 to 1.1999999284744263 after update 3
failure.json        {"invalid": true, "complete": false, "updates": 3,
                     "reason": "the frozen code_scale changed; the run is INVALID"}
completion.json     absent
final.pt            absent
```

`check_frozen` compares with `!=` on the float, not a tolerance, and runs after **every** update,
so the smallest representable change is caught. (A change *below* one ULP is not a change: I first
tried `+1e-7`, which rounds away in float32 and correctly produced no violation — that is
arithmetic, not a gap.)

**(b) Reload from a differing checkpoint.** I edited `code_scale` to 0.5 in a saved state dict and
loaded it with `strict=True` into a freshly constructed `FrozenScaleOperator`:

```
tamper_load         detected: code_scale moved from 1.2000000476837158 to 0.5
```

Note the layered defence here, because `load_checkpoint` reconstructs the model from the
checkpoint's own `architecture.code_scale`: if a *moved* value had somehow been saved, `check_frozen`
alone would be satisfied (it compares against the reconstructed value), but `cmd_score` independently
asserts `|value − 1.2| ≤ 1e-6` and records `buffer_ok`, `run_score.sh` greps for `"buffer_ok": true`,
and `gate_table` turns the whole experiment INVALID on a false one. Two independent guards, and the
per-update check would have aborted the run long before.

**(c) The gate.** A synthetic `runs/F-2103/failure.json` with `"invalid": true`:

```
invalid_runs         [{"run": "F-2103", "reason": "moved"}]
gate verdict         INVALID -- the frozen code_scale changed: ['F-2103']
```

INVALID is evaluated **before** INCOMPLETE, VOID and any mark, so it cannot be masked.

**Requirement 2: MET.**

---

## 5. Held-out integrity

* **The reserved half is unreachable from training, in all three arms.** `train_run` contains
  exactly one `pool_subset` call and it is the literal `pool_subset(pool, 'train')` — there is no
  parameter, flag or namespace that can change it. The control uses no codes at all. I confirmed
  the pools are disjoint (3,072 / 1,024, intersection 0 by row hash) and that a draw from the
  training subset lands entirely inside it and zero times in the reserved subset.
* **The pool is experiment 21's, not a new draw.** `cmd_pool` writes a reference carrying the
  sha256 of `pool.json`, `pool.pt` and all three tensors; `load_pool` re-verifies all four on every
  command before a code is drawn. So "the reserved 1,024 have still never been trained on" remains
  true and is machine-checked. (C1's cost is real: this experiment cannot be run if experiment 21's
  folder is deleted. **Ruling: acceptable** — the alternative is two copies that can drift.)
* **Panels are fresh and their namespace is new.** Suite `newnames27-operator-v1-20260921`, seed
  base `202609212700`, panel codes `newnames27/panel-codes:<pool>:<cell>:<chunk>`, train codes
  `newnames27/train-codes:<seed>` — all four differ from experiment 21's. Panels are built at
  launch, not pre-built: the folder contains no `panels/` today, which I confirmed.
* **The two scorings read identical panels.** Both read the same ten `.pt` files through
  `panel_paths`/`load_panel`, which re-hash each file against the manifest before every load, and
  the binding is done in memory on `inputs.memory` tensor identity. Only the codes differ, and only
  because the assignment key carries `which_pool`. That is experiment 21's scheme unchanged
  (`fable_newnames21.py:1080-1082`), which AUDIT-21 passed under Q6. 12-person cells still get
  `ENTITIES = 16` bound codes (21b Q9). **Paired comparison intact.**
* **Run-time exclusion.** `training_exclusion` re-hashes the fresh exclusion file and hands the
  trainer the union of the registered screen exclusion and this experiment's fresh panels, at every
  one of the 6,000 updates. Measured on my fixture: 6,656 registered + 208 fresh (a 512-unit suite
  will contribute ≈ 6,656, as experiment 21's did).

**Requirement 3: MET**, with MINOR-6 below.

---

## 6. Gates, signatures and boundaries — checked at the edges

I built synthetic score tables and read the answers out. Every one matches the design's wording.

| what the design says | boundary I tested | result |
| --- | --- | --- |
| `R ≥ cutoff` on all ten cells | every cell exactly at its cutoff | **passes** |
| | c3 one below 461 | **fails** |
| paired `reserved − train ≥ −13` | delta −12, −13 | **passes** |
| | delta −14 | **fails** |
| two-sided warning at `|d| > 13` | delta −13, +13 | **no warning** |
| | delta −14, +14 | **warning on that cell**; +14 still *passes* the mark | 
| `never_started`: c1 and c2 both ≤ 64/512 | both at 64 | **fires** |
| | both at 65 | **does not fire** |
| `copy_side_failure`: every one-call attribute ≥ 0.90 **and** every first-stage LINK ≤ 0.125 | attr 0.90, link 0.125 | **fires** |
| | attr 0.90, link 0.1251 | **does not fire** |
| `name_blind`: all ten paired deltas exactly 0 **and** LINK ≤ 0.125 | one delta = +1 | **does not fire** |
| sub-label `bias_exit` if bias ≤ −3.0 | bias −3.0 | **`bias_exit`** |
| sub-label `gain_exit` if mean answer length < 3.5 | bias −2.99, gain 3.49 | **`gain_exit`** |
| else `unexplained` | bias −2.99, gain 3.50 | **`unexplained`** |
| `scale_collapsed`: **arm L only**, `|scale| < 0.05` at any logged point **from update 500** | arm L, 0.049 at update 500 | **fires** |
| | arm L, 0.050 at update 500 | **does not fire** |
| | arm L, 0.0 at update 400 only | **does not fire** (correct: the design says "from 500 on") |
| | **arm F, any of the above** | **never fires** — C8 honoured |
| `reserved_gap`: all ten met on train-pool, at least one missed on reserved | c5 one below on reserved only | **fires**, and `unnamed` correctly stays false |
| VOID if fewer than 2/3 control seeds meet the ten cutoffs | | evaluated before PASS/PARTIAL/FAIL |
| PASS = 3/3 F, PARTIAL = 2/3, else FAIL | | confirmed in `gate_table`'s chain |
| INVALID ahead of everything | | confirmed (§4c) |
| arm L moves no verdict | `gate_table` computes `l_pass` and never uses it; `missing` covers only `('control','F')` | confirmed |

The two-sided warning line that experiment 21 never emitted (AUDIT-21 MINOR-6) is now computed
(`paired_warnings`), stored in `gates.json` and printed by `cmd_report`. The control arm is now in
`signature_summary` (AUDIT-21 MINOR-9 closed).

One inherited naming oddity, not a defect: `failure_signatures` reports
`rules['copy_side_failure'] = base['scale_bug_rule']`. `scale_bug_rule` is experiment 21's internal
name for exactly this rule string, and its text is correct
("every one-call attribute relation >= 0.9 while every first-stage LINK <= 0.125"). No action.

**Requirement 4: MET.**

---

## 7. The trace is inert — re-proved by me

My own runs, fixture seed 4344, 30 updates, trace every 10 against trace off:

| arm | final fingerprint equal | every tensor equal | FLOPs equal | rows with trace on / off |
| --- | --- | --- | --- | --- |
| F | **true** | **true** | **true** | 3 / 0 |
| L | **true** | **true** | — | 3 / — |

`trace_row` runs under `torch.no_grad()` on the batch just trained on, draws no random number,
saves and restores `model.training`, and `answer_state` saves and restores `_codes/_lines/_owner`.
The trace is appended **after** `A.training_step` and **before** `clear_bindings`, so it sees the
bindings it needs and consumes nothing. Sixty rows over a 6,000-update run; the cost is
immaterial. **Requirement 5: MET.**

Trace content matches design 4.6 field for field (`TRACE_KEYS` is asserted against the row that is
built, so drift is impossible). C7's two definitional choices — LINK-vs-value read off the target
token (`target ≥ ENTITY_MIN`), and `value_row_mean_length` over tokens 12…27 rather than the filler
rows — are both correct and both defended by a test against the frozen generator. **Ruling on C7:
acceptable.**

---

## 8. Procedure safety

| requirement | status |
| --- | --- |
| refuses to overwrite | **met** — `refuse_existing` + `C.write_new` (`open(…, 'x')`) on every output; the launchers additionally refuse a folder that exists without its marker file. I saw `train_run` create its folder with `exist_ok=False`. |
| cannot score before training completes | **met** — `cmd_score` raises `SystemExit` unless `completion.json` exists; a crashed run writes `failure.json` and no checkpoint at all (confirmed in §4a). |
| cannot report a partial set as complete | **PARTLY — see §2.1.** `gate_table` returns INCOMPLETE while any gated run is unscored, and arm L's absence correctly does not trigger it. But a *short* registered run is accepted and is invisible to the gate. |
| source fingerprint pinned so a mid-run edit is detected | **PARTLY — see §2.2.** Pinned in four places; compared nowhere. |
| deterministic, single-thread | **met** — `configure_once` calls `R.configure()` and asserts `torch.get_num_threads() == torch.get_num_interop_threads() == 1`; both launchers export `OMP_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1`; all draws go through `random.Random` on a string key or `torch.manual_seed`. |
| `test.pt` never loaded | **met** — refused by name in `load_checkpoint`. |
| fixture escapes refused on registered seeds | **met for four of five** — `code_scale`, `code_namespace`, `trace_every`, `fixture_step0`; **not** `updates` (§2.1). |

---

## 9. Wall-clock — wave 1 is credibly under 30 minutes

The builder's number (≈ 11 min) rests on an integration of four measured per-update costs. I do not
need it, because a stronger anchor exists on disk: **experiment 21's own wave was the same shape** —
six single-thread jobs launched together, 6,000 updates each, same architecture, same curriculum,
same machine:

```
control 2100  659.9 s      treatment 2100  675.1 s
control 2101  659.3 s      treatment 2101  676.0 s
control 2102  659.8 s      treatment 2102  681.7 s
```

**11.0–11.4 minutes wall-clock for six concurrent jobs.** Experiment 27's wave 1 is the identical
job mix (three controls, three code arms) with one scalar demoted and sixty extra no-grad trace
rows per code run. There is no mechanism by which it could take three times as long. Even the
builder's slowest measured rate (0.1339 s/update at the end of the curriculum) held for all 6,000
updates would give 803 s = 13.4 minutes. The trainer's own watchdogs (`TRAINING_SECONDS = 1680`,
`WORK_SECONDS = 1740`) abort rather than shorten, and sit above any plausible outcome.

Wave 3 is projected, not measured, and the projection is honest about that (run_score.sh and
BUILD-NOTES §"What is unverified" both say so). Experiment 21's measured scoring at 512 units was
34.3 s for a control scoring and 69.4 s for a two-pool code scoring; at three jobs at a time that
is ≈ 4 minutes for the six wave-1 runs. Credible.

**Requirement 7: MET.** No time-based reason to hold the launch.

---

## 10. Rulings on the judgement calls C1–C16

| # | ruling | note |
| --- | --- | --- |
| C1 pool referenced, not copied | **acceptable** | Hash-checked four ways on every command; the stated cost (dependency on experiment 21's folder) is the right trade against two files that can drift. Put "do not delete `artifacts/fable-newnames21-20260920/pool/`" in the freeze note. |
| C2 no 64-person cells | **acceptable** | Design 4.2 does not ask for them; design 4.6's two read-outs replace them; it also removes the `widened_entities` path from this experiment entirely, which is a simplification in the right direction. |
| C3 audit replay borrows seed 2103 | **acceptable** | `replay_seeds` rebinds `N.SEEDS` around the audit only, runs the registered audit code object, and asserts restoration in a `finally`. I confirmed the restoration assert is `(2100, 2101, 2102)`. Nothing that decides a model number runs inside it. |
| C4 fresh namespaces and seed base | **acceptable** | All four differ from experiment 21's. |
| C5 buffer, not a parameter outside the optimiser | **acceptable — and required** | Verified directly: 66 optimiser tensors against L's 67, absent from `parameters()`, absent from the clip. See §3.1's caveat on how this must be worded. |
| C6 any movement is INVALID, not a result | **acceptable** | Tamper-tested at one ULP (§4). |
| C7 trace fields and the two definitions | **acceptable** | §7. |
| C8 `scale_collapsed` is arm-L only | **acceptable** | Boundary-tested; arm F never fires it (§6). |
| C9 `name_blind` sub-label order | **acceptable** | Boundary-tested at −3.0 / 3.49 / 3.50; the order matches the design's listing. |
| C10 `unnamed` | **acceptable** | Correctly false when a named signature fires (tested with `reserved_gap`). |
| C11 open-set rule includes the 52 base rows | **acceptable, and a genuine catch** | Without it a model dumping mass on a non-name token would score as correct. Descriptive only. |
| C12 attention read-out | **acceptable** | Descriptive only; `line_attention` is a pure function of `inputs.memory` and touches no model. |
| C13 panels are never modified | **acceptable** | Binding is by tensor identity in memory; the manifest hash is re-verified on every load. |
| C14 fixture escapes refused on registered seeds | **NOT acceptable as it stands** | Four of five. `--updates` is the fifth and the most consequential. **See §2.1.** |
| C15 both sides of every proof run against the same folder | **acceptable** | A different panel suite means a different exclusion set means a different world stream, so this is the only comparison that isolates the change. But see MINOR-1: it also means the design's literal instruction was not followed. |
| C16 three launchers, two training waves | **acceptable** | Wave 2's absence is correctly never an INCOMPLETE, since `missing` covers only `('control', 'F')`. |

---

## 11. MINOR findings

**MINOR-1 — the arm-L equivalence proof runs on fixture seed 9, not on seed 2100 as design 4.3
words it.** Design 4.3's last bullet says "50-update proof that arm L with start value 0.13856
reproduces experiment 21's treatment fingerprint **for seed 2100's first 50 updates**". `run_data.sh`
uses `L_EQUIV_SEED=9`. The substitution is defensible and I would have made it: with experiment 27's
fresh panel exclusion the world stream differs from experiment 21's registered run, so experiment
21's on-disk seed-2100 fingerprint is *unreproducible by construction*, and the same-folder
comparison the builder runs is the test that actually isolates the change. But it is a deviation
from a binding document and must be recorded as one in the freeze note, in those words. *(Optional
strengthening, not required: also run it at `--seed 2100`; that is not a registered experiment-27
seed and 50 updates into a temp folder costs 15 s.)*

**MINOR-2 — `run_train.sh` does not verify that the panels it is about to use are the registered
ones.** `cmd_panels` accepts `--namespace`, `--seed-base` and `--n`; anything but the defaults only
prints a `FIXTURE PANELS` warning and sets `"registered": false` in
`panels/newnames27-panels.json`. `run_train.sh` checks that `panels/manifest.json` and `audit.json`
exist and that the audit is clear, but never checks `registered`. Fix (shell only, no re-hash of
the scientific script): add to `run_train.sh`'s marker loop

```sh
if ! grep -q '"registered": true' "$EXP/panels/newnames27-panels.json"; then
    say "TRAIN_FAILED -- the panel suite is not the registered one"; exit 1
fi
```

The direction of the risk is benign (a 16-unit suite keeps the absolute cutoffs 487/461 and would
auto-FAIL, never auto-pass), which is why this is MINOR and not MAJOR.

**MINOR-3 — `cmd_gates` and `cmd_report` write only if the file is absent, but `run_score.sh` reads
`gates.json` for the VERDICT line.** So a `gates` run made while the set was incomplete leaves a
stale `gates.json`, and a later complete `run_score.sh` prints the fresh verdict into
`logs/gates.log` while announcing the stale one. The bias is safe (stale = INCOMPLETE), but it is
confusing. This is experiment 21's MINOR-3, uncorrected. Fix: have `run_score.sh` take the verdict
from the fresh stdout, or refuse to proceed when `gates.json` predates the newest `scores/*.json`.

**MINOR-4 — `run_score.sh` scores what it can before discovering a required run is missing.** The
three-at-a-time loop runs to completion and only then collects statuses. Experiment 21's MINOR-2,
uncorrected. Harmless (`gate_table` still returns INCOMPLETE and the script exits non-zero), but a
front-loaded presence check would be cleaner.

**MINOR-5 — `control-equivalence` runs on seed 0, not on a registered seed.** This is a *better*
choice than the design's silence implies, because seed 0 is the one seed with a registered
grow-blind run on disk, so the proof also re-derives the registered initial fingerprint. The control
path contains no seed-dependent branch, so nothing is lost. **No action**; recorded so the freeze
note does not claim the proof was done on 2103–2105.

**MINOR-6 — the panel audit does not check disjointness against experiment 21's own panels.**
`FC.development_sources()` lists the dispatcher panels, the screen panels, the token-memory stress
and fresh panels and the original pair suite — but not
`artifacts/fable-newnames21-20260920/panels`. So "fresh, disjoint from experiment 21's panels" is
asserted by construction (new namespace, new seed base) and not measured. Impact is low: no
experiment-27 model ever sees an experiment-21 panel, so an overlap would leak nothing; it would
only mean a shared item if someone later compared the two experiments cell by cell. The base rate
looks negligible — I measured zero overlap between experiment 21's 6,656 panel semantics and both
the registered screen exclusion (6,656) and my own fresh 208-semantic fixture suite. Optional fix:
add experiment 21's panel folder to the audit's source list.

**MINOR-7 — `--audit-updates 100` certifies 100 of 6,000 updates.** Inherited from experiment 21
and correctly labelled `"partial": true` with a note in the JSON. The complete guarantee is the
run-time `forbidden` check at every update, which is real. **No action**; the report must not
describe the replay as a full certification.

**MINOR-8 — `load_checkpoint` reconstructs arm F from the checkpoint's own recorded
`architecture.code_scale`.** This makes `check_frozen` at load time a self-consistency check rather
than a check against 1.2. It is fully covered by `cmd_score`'s independent `buffer_ok` assertion
and by the per-update check during training (§4b), so this is a note, not a defect. If you want one
more belt: have `load_checkpoint` pass `code_scale=CODE_SCALE` for arm F and let `strict=True`
loading plus `check_frozen` do the rest.

---

## 12. What I could not verify

1. **No registered seed has been trained, scored or panelled** — by instruction, and I confirmed
   the folder contains no `pool/`, `panels/`, `runs/`, `scores/` or `gates.json` today. Everything
   about the *outcome* is therefore untested, which is the point.
2. **Wave-3 wall-clock at 512 units for this experiment** is a projection from experiment 21's
   measured numbers, as BUILD-NOTES says.
3. **The registered panel build has not been run**, so its exclusion count and wall-clock are
   unknown. Experiment 21's 6,656 semantics at 512 units is the only guide.
4. **Whether the machine will be quiet at launch** is a launch-time check, not an audit one.
5. **The builder's own fixture evidence** (65/69 tensors, 47 tests, the four timing clocks) I did
   not re-execute wholesale; I re-derived the load-bearing parts myself and they agree.

---

## 13. Conditions for the freeze

1. **Apply §2.3** — `run_integrity` in `gate_table`, and `updates` added to the refused overrides.
   Re-run `tests/test_fable_newnames27.py`, re-hash `scripts/fable_newnames27.py`, update the hash
   table in `BUILD-NOTES.md`. *(Required. Nothing in it touches the model, the data or a mark.)*
2. **Apply MINOR-2's three-line `run_train.sh` guard.** *(Recommended; shell only.)*
3. **Record MINOR-1 in the freeze note as a knowing deviation from design 4.3**, with the reason
   (experiment 21's seed-2100 fingerprint is unreproducible under a fresh exclusion set).
4. **Record MINOR-5**: the control-equivalence proof is on seed 0, not on 2103–2105.
5. **Bind `artifacts/fable-newnames21-20260920/pool/` into the freeze manifest** and note that it
   must not be deleted (C1).
6. **Carry §3.1's wording caveat into the results write-up**: arm F removes the scale from the
   parameter set (and therefore from the gradient clip); it does not merely pin a number. Design
   4.8's compulsory clause already covers the claim; looser wording would over-claim.
7. **Do not let arm L's outcome touch the verdict, the claim or any re-labelling**, whichever way
   wave 1 goes. The code already enforces this; the prose must too.
8. Everything in design 4.7's "must not change" list stays unchanged, **including the number 1.2**,
   whatever wave 1 shows.

With condition 1 applied, I would sign FREEZE-READY: YES.

---

*Audit performed 2026-09-21 by an independent auditor who did not build experiment 27. Scratch work
in `/private/tmp/.../scratchpad/a27`; nothing in the repository was edited and no commit was made.*
