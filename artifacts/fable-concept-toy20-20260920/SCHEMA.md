# concept-toy20 `ct20-v1.1` — the single frozen serialized-data contract

Agent 1 (simulator and panels), pilot stage, 20 September 2026.

Produced by `scripts/fable_concepttoy20_sim.py`; read by `scripts/fable_concepttoy20_public.py`.
Contracts: `design/v3/20-concept-toy-rulings-1.md`
(SHA-256 `40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de`),
`design/v3/20-concept-toy-rulings-2.md`
(SHA-256 `1245e46f567dd1a265d6b05d8482f0267052c735159b8d05864dd6b861a110f2`
**as measured in this worktree** — the coordinator quoted
`8a62ef050e2120209761e858109aa9195b87c88790fb7827dd5b547a56defc8d` for the same file; the
discrepancy is unresolved and is recorded rather than reconciled, and the hash above is of
the bytes actually read and applied),
`design/v3/20-concept-toy-simulator-spec.md`,
`design/v3/20-concept-toy-preregistration-draft.md`,
`design/v3/20-concept-toy-build-plan.md`.

**Ruling C11 freezes this file as the single serialized-data contract**: file layout,
offsets, dtypes, masks, IDs and join conventions. Where the rulings resolve the three
earlier contracts, the rulings win; this file records what the generator actually writes.
It cannot override a ruling or the scientific contract. Every constant is also
machine-readable in `manifest.json -> generator_config`.

`ct20-v1.1` is a **versioned amendment** (ruling D). Its one distribution change is B1.
The earlier `ct20-v1` artifacts are preserved untouched; the amended data live in new
directories with new hashes. Section 9 is the change log.

---

## 1. Directories

```
artifacts/fable-concept-toy20-20260920/
  SCHEMA.md                     this file
  calibration/                  ct20-v1 data, PRESERVED, not regenerated
  fixture/                      ct20-v1 fixture, PRESERVED, not regenerated
  calibration-v1.1/             ct20-v1.1 pilot data: 6 train + 6 validation worlds
    manifest.json               generator config, file hashes, tensor hashes, boundary
    collision_report.json       cross-split world-tuple disjointness audit
    audit_report.json           output of `audit --data`
    public/                     the ONLY tree a learner may read
      worlds.json
      <world_public_id>/*.npy, query_record_ids.json, audit_keys.json
    private/                    evaluator only
      world_config.json, normalization.json
      <world_public_id>/*.npy, query_truth.json, audit_truth.json
  fixture-v1.1/                 readable synthetic interface fixture (same layout)
    fixture.md                  decoded records, field by field
```

`world_public_id` is an opaque 16-hex alias, `sha256(world_id + "/public-alias")[:16]`.
The true `world_id` (SHA-256 of the canonical world tuple) never appears in a public
file. Worlds are listed in the public index sorted by `(outer_split, world_public_id)`,
so listing order carries no family information. **The world aliases are byte-identical
to `ct20-v1`**: the tuple hash is pinned at the inherited label (section 6).

## 2. Public batch contract

All public tensors are little-endian `'<f4'` unless stated otherwise. The simulator
computes in float64 and casts once at serialization. Files are `.npy` (dtype/shape
header only, no timestamp), so hashes are byte-reproducible across devices. **Use the
frozen files as cross-device data; do not regenerate per device.**

### 2.1 Record vector, width 44

| offsets | field | width | dtype | encoding |
| --- | --- | ---: | --- | --- |
| `0:24` | `public_properties` | 24 | `<f4` | four rows of six, row-major, sorted by local public ID; identical on every record of an episode |
| `24:29` | `action_id` | 5 | `<f4` | one-hot **public** action ID; all zero at RESET |
| `29:33` | `source_id` | 4 | `<f4` | one-hot source object i; all zero at RESET |
| `33:38` | `destination_id` | 5 | `<f4` | one-hot j=0..3, or `NONE` at index **4** |
| `38:39` | `dose` | 1 | `<f4` | −1/+1 on pulse, exactly 0 otherwise |
| `39:40` | `sensor` | 1 | `<f4` | returned y; exactly 0 if missing, and on QUERY and RESET |
| `40:41` | `sensor_present` | 1 | `<f4` | 1.0/0.0 observation mask; 0 on QUERY and RESET |
| `41:44` | `record_type` | 3 | `<f4` | one-hot, token ids **RESET=0, QUERY=1, OBSERVED=2** |

A padding row is all-zero, so `record_type.sum() == 0` identifies padding.

**RESET (ruling B4, confirmed).** `destination_id` index 4 (`NONE`) **is 1.0 on the RESET
record**; action and source blocks are all zero; dose, sensor and `sensor_present` are
zero; properties are populated; `record_type = RESET`. Constant
`RESET_DESTINATION_IS_NONE = True`.

**Public hints (ruling B8, accepted as intended).** Public action IDs are a per-world
random bijection of the five internal verbs; internal verb names never appear in a public
file. `dose != 0` publicly identifies pulse and `destination != NONE` publicly identifies
contact. The registered wording for this is **"randomly relabeled action IDs with public
argument/dose structure"**, *not* fully anonymous action semantics: read and wait share
dynamics, so five IDs do not imply five distinguishable effects, and panel membership is
partly inferable from action patterns. Hash ordering (section 4) hides explicit grouping,
not semantic membership.

### 2.2 Causal order

* Support episode: `RESET`, then `(QUERY_t, OBSERVED_t)` for t = 0..7 → **17 records**.
* Forecast unit (query panel or fitting audit): `RESET`,
  `(QUERY, OBSERVED)` × `prefix_length`, then `(QUERY, blank OBSERVED)` × `(h−1)`, then
  the final `QUERY`. The prediction is read at that final QUERY, **before** its blank
  OBSERVED. Blank OBSERVED = `sensor = 0, sensor_present = 0`, `record_type = OBSERVED`.
  No intermediate measurement, predicted value, future mask or label is ever supplied.

**Ruling B5 (confirmed): exactly one scored prediction per branch**, at the final QUERY
after rolling forward h actions. Intermediate QUERY records are processed but are not
additional scored targets. "Four-step forecast" means a four-action-ahead **endpoint**
prediction, not accurate prediction of every intermediate response.

Because `prefix_length + h = 8` for every panel unit, every pilot **query** sequence has
exactly 16 real records and its prediction at index 15. Fitting-audit sequences may stop
earlier (section 2.6). Sequences are padded to 17 rows so support, query and audit
tensors share one width and one sinusoidal position table (positions 0..16).

### 2.3 Per-world public files

| file | dtype | shape | meaning |
| --- | --- | --- | --- |
| `support_records.npy` | `<f4` | `(64, 17, 44)` | nested discovery stream, B=512 prefix |
| `support_padding_mask.npy` | `uint8` | `(64, 17)` | all ones (support is never padded) |
| `support_episode_role.npy` | `int8` | `(64,)` | `0` = gradient fitting, `1` = discovery-validation (selection) |
| `support_budget_rung.npy` | `int8` | `(64,)` | 0..4; episode enters at `BUDGETS[rung]` |
| `support_observed_target.npy` | `<f4` | `(64, 8)` | masked observed A target per transition; exactly 0 when absent |
| `support_observed_present.npy` | `uint8` | `(64, 8)` | actual observation mask |
| `query_records.npy` | `<f4` | `(96, 17, 44)` | the 96 scored prediction points |
| `query_padding_mask.npy` | `uint8` | `(96, 17)` | 1 for the 16 real rows |
| `query_n_records.npy` | `int32` | `(96,)` | 16 for every pilot unit |
| `query_index.npy` | `int32` | `(96,)` | 15 for every pilot unit; row at which to read the prediction |
| `query_detector.npy` | `<f4` | `(96, 9)` | detector query, one-hot a (4) ⧺ one-hot b incl. `NONE`=4 (5) |
| `query_record_ids.json` | JSON list | 96 strings | opaque join keys, `<world_public_id>-qNNNN` |
| `audit_records.npy` | `<f4` | `(A, 17, 44)` | fitting-audit sequences, section 2.6 |
| `audit_padding_mask.npy` | `uint8` | `(A, 17)` | 1 for the `audit_n_records` real rows |
| `audit_n_records.npy` | `int32` | `(A,)` | `2 × endpoint` |
| `audit_index.npy` | `int32` | `(A,)` | `audit_n_records − 1`; row at which to read the prediction |
| `audit_detector.npy` | `<f4` | `(A, 9)` | `(last_action.source, NONE)` |
| `audit_observed_label.npy` | `<f4` | `(A,)` | the training label; already public in `support_observed_target` |
| `audit_episode_index.npy` | `int32` | `(A,)` | support-episode index |
| `audit_horizon.npy` | `int32` | `(A,)` | 1, 2 or 4 |
| `audit_endpoint.npy` | `int32` | `(A,)` | 1-based endpoint t |
| `audit_keys.json` | JSON list | A objects | `audit_id`, `episode_index`, `horizon`, `endpoint`, `endpoint_transition_index`, `n_records`, `query_index` |

`support_observed_target` duplicates `support_records[:, 2::2, 39]` exactly; the audit
asserts it.

**Audit-set size and the unused reservation (audit note 12).** `A` is **144** for eleven
of the twelve pilot worlds and **143** for `db0d29339a47b284`, because that world has one
fit episode with no eligible endpoint at one horizon (its present mask has no observation
at or after that horizon). Consequences, all registered:

* The public file-size signature is no longer uniform across worlds: there are now two
  audit-set sizes where `ct20-v1` had one. This is **not a leak** — `A` is a pure function
  of `support_observed_present`, which is already public — but it is a visible
  per-world difference and is recorded here for that reason.
* Per ruling A1 the frozen step reservation charges the **largest legal** set, 144, for
  every world, so the step table stays data-independent. The one-row shortfall in
  `db0d29339a47b284` is an **unused reservation**: it must be reported separately and
  **must not be spent on extra fitting**, extra evaluation, or any other work.
* `audit_targets()` on the models side is data-independent for the same reason.

### 2.3.1 Padding convention — **normative, ratified** (audit §4.1; rulings 2)

Rulings 2 ratifies this: *"Keep all-zero serialized padding as normative, while permitting
audited internal padding conventions that cannot affect outputs."*

Rows at index ≥ `n_records` in `query_records.npy` and `audit_records.npy` are
**all-zero rows**, every one of the 44 channels. This serialized convention is normative:
it is what the frozen `.npy` files contain and what any byte-level comparison against
these files must expect.

A consumer may use a different **internal** convention — for example carrying the static
24-float property block forward onto padded rows while building sequences — and that is
explicitly permitted, because such rows are excluded by the padding mask and by the
endpoint gather at `query_index`, and therefore cannot reach a prediction. Agent 2's
`build_sequences` does exactly this.

Consequently **byte-equality between a producer's in-memory tensor and the serialized file
is asserted only over rows `0 … n_records − 1`.** A cross-producer equality check that
compares padded rows will differ for this benign reason, and must not be "fixed" by
changing either convention. **Cross-producer equality over the real rows is checked
separately**, by the independent auditor's own rebuild of the tensors, and that check is
the one that must hold; an internal padding convention is admissible only once it has been
audited to be unable to affect an output.

Budgets are nested prefixes of the episode axis: `B=32 → episodes 0:4`, `64 → 0:8`,
`128 → 0:16`, `256 → 0:32`, `512 → 0:64`. In every group of four, indices 0,1,2 are
fitting and index 3 is selection, so the discovery-validation partition is **inside** the
budget and is not free. At B=512: 48 fit + 16 selection episodes.

### 2.4 Public index — `public/worlds.json`

```json
{"version":"ct20-v1.1","budgets":[32,64,128,256,512],"episodes_per_budget":[4,8,16,32,64],
 "n_support_episodes":64,"n_query_records":96,"record_width":44,"n_records_full":17,
 "detector_width":9,
 "worlds":[{"outer_split":"train","world_public_id":"149e30247f4b35ec",
            "n_audit_records":144}, ...]}
```

The audit key format is **not** repeated in this index. The public forbidden-word scan in
`audit --data` is a plain substring test over the public index, and the template string
literally contains the word `horizon`, which the scan cannot distinguish from a leaked
per-record horizon. The format is fixed in section 3 of this file, in
`PublicDataset.audit_key()`, and in `manifest.generator_config.fitting_audit_set.key_format`;
those three are the normative statements of it.

**Ruling B8:** `outer_split` is coordinator bookkeeping only. It appears in this index so
a driver can pick a pool. It is in **no tensor**, in no batch object, and may not
condition any fitting choice. The prereg likewise forbids file IDs, seed strings, family
tags, normalization constants and episode indices as model features.

### 2.5 Task-B fitting batch (shape only; no pilot data generated)

`TaskBFittingBatch` in the public loader: the **same** `records`/`padding_mask`/
`observed_target`/`observed_present` as task A, plus `b_detector` `(n, 8, 9)` and
`b_label` `(n, 8)` in a **target-only field**. `b_label` is never concatenated into
`records` and must never reach a state updater or encoder. The test
`task-B labels are absent from encoder inputs` asserts both that no `b_label` value
occurs anywhere inside `records` and that `records` is byte-identical to the same
episode built with no B labels.

Task-B **query** panels are not generated in this pilot. When they are, they must be
built with `build_source_panels(world, stream=STREAM_REUSE_QUERY)`, which applies ruling
B1 identically (the exclusion switch is shared, not per-stream).

### 2.6 Fitting-audit set (prereg §8, rulings C9/C10)

Deterministic, sampled from nothing: **for each fit episode and each h ∈ {1,2,4}, that
episode's last eligible observed endpoint.** Fit episodes are the `ROLE_FIT` episodes of
the 512-transition prefix (48 of 64).

Named conventions, because the prereg fixes no index convention. Both were raised for
ruling; rulings 2 did not object to either, so both are now **registered as implemented**
and are no longer open questions:

* `AUDIT_ENDPOINT_INDEXING` — 1-based: endpoint `t ∈ h..8` names the **t-th action**;
  the scored response is the one produced by that action (`noise_free[t−1]`).
* `AUDIT_ELIGIBILITY` — `t >= h` **and** `present[t−1]` is true, because the fitting loss
  uses the observed label. The **last** such `t` is used. If no `t` qualifies, that
  (episode, h) case does not exist — the set is shorter, and no substitute is chosen.
* `prefix_length = t − h`, so `n_records = 2t` and the prediction index is `2t − 1`.

The set is a pure function of already-public support episodes and already-public presence
masks, so it adds no RNG stream, consumes no draw and discloses no hidden state. The
observed label is the same number the learner already received in
`support_observed_target`. Only the **noise-free** response is evaluator-only.

**Join key (the one supported format):**

```
audit_id = f"{world_public_id}-fit{episode_index:04d}h{horizon}e{endpoint}"
# e.g. 149e30247f4b35ec-fit0000h1e8
```

`PublicDataset.audit_key(...)` and `fable_concepttoy20_sim.audit_key(...)` build it, and
`load_predictions` also accepts the four fields `world_public_id`, `episode_index`,
`horizon`, `endpoint` and folds them into the same string.

Score this set **twice with identical cases**: once at initialization (`stage="initial"`)
and once at the fixed B=512 endpoint (`stage="final"`). Save both prediction sets.

## 3. Private evaluator contract

Scoring needs only these files — **no in-process simulator object**.

| file | contents |
| --- | --- |
| `private/world_config.json` | alias → `world_id`, permutation-free hash, `family`, `outer_split`, `world_index`, coefficients `{a,beta,g,b,c}`, `verb_to_public` |
| `private/normalization.json` | per `"{split}/{task}/{family}"`: `panel_response_variance`, `V`, `analytic_sensor_floor = 0.0009/V`, `n_responses` |
| `private/<wpid>/query_truth.json` | one row per query record ID (below) |
| `private/<wpid>/query_truth_noise_free.npy` | `float64 (96,)`, aligned with the public query axis |
| `private/<wpid>/query_truth_noisy.npy` | `float64 (96,)` |
| `private/<wpid>/audit_truth.json` | one row per fitting-audit case (below) |
| `private/<wpid>/audit_truth_noise_free.npy` | `float64 (A,)`, aligned with the public audit axis |
| `private/<wpid>/audit_truth_observed.npy` | `float64 (A,)` — the training label, in float64 |
| `private/<wpid>/support_truth_noise_free.npy` | `float64 (64, 8)` — evaluator-only fitting-set responses |
| `private/<wpid>/support_truth_noise.npy` | `float64 (64, 8)` |
| `private/<wpid>/support_latent.npy` | `float64 (64, 9, 4)` — q or m after RESET and each transition |
| `private/<wpid>/support_action_attempts.npy` | `int32 (64,)` — reserved-composition redraw count |

`query_truth.json` row:

```json
{"record_id":"<wpid>-q0000","world_public_id":"...","world_id":"...","family":"c",
 "outer_split":"validation","task":"A","panel":1,"panel_name":"ordinary","unit":0,
 "branch":"single","pair_key":null,"horizon":2,"prefix_length":6,
 "detector_a":3,"detector_b":null,
 "noise_free_response":0.1234,"noisy_target":0.1301}
```

`audit_truth.json` row:

```json
{"audit_id":"<wpid>-fit0000h1e8","world_public_id":"...","world_id":"...","family":"n",
 "outer_split":"train","task":"A","episode_index":0,"horizon":1,"endpoint":8,
 "prefix_length":7,"detector_a":1,"detector_b":null,
 "noise_free_response":0.0,"observed_label":-0.0229}
```

### 3.1 Prediction file

`evaluate --predictions FILE --private DIR --out FILE` accepts JSON
(`[{...}]` or `{"predictions":[...]}`) or CSV with the same header.

| field | required | meaning |
| --- | --- | --- |
| `prediction` | yes | float64 |
| `record_id` | yes* | a query record ID **or** an `audit_id` |
| `world_public_id`, `episode_index`, `horizon`, `endpoint` | yes* | audit rows only; an alternative to `record_id` |
| `stage` | no | `"initial"` or `"final"`; **missing means `"final"`**, so a `ct20-v1` file still scores unchanged |
| `arm`, `seed`, `rung` | no | grouping labels |

\* exactly one of the two join forms.

Query rows group by `(arm, seed, rung, stage)`. Audit rows group by `(arm, seed, stage)`,
because ruling C10 defines exactly two audit scorings per fit. Unknown IDs are counted
and reported, never silently dropped.

**Audit-key spelling — one spelling only (rulings 2).** An earlier draft of
`fable_concepttoy20_models.py` used `"e{episode_index}/h{horizon}/t{endpoint}"`. The
**frozen models build now calls `PublicDataset.audit_key` itself**, so producer and
consumer agree by construction rather than by convention, and rulings 2 directs this file
to correct the stale assertion that the spellings differ. They do not.

The one legal key is:

```
{world_public_id}-fit{episode_index:04d}h{horizon}e{endpoint}
```

emitted by `audit_keys.json`, `PublicDataset.audit_key()` and the simulator's
`audit_key()`, which are asserted equal by test. The compatibility reader that briefly
accepted the retired spelling **has been removed**: it is not needed by the frozen build,
and leaving it would have registered a second legal spelling in a frozen contract. A
prediction row still carrying the retired spelling is now treated as an **unknown record
ID** — counted and reported, never silently rewritten or dropped.

### 3.2 Query scoring

Per world: `raw_noisy_mse`, `raw_noise_free_mse`, `V`, `analytic_sensor_floor`,
`E_all_targets`, `E_panel1_ordinary`, `E_panel1_by_horizon`, `E_panel2_composition`,
`E_primary`, the two pair-panel blocks, and `complete`.

#### The gate quantity — `E_primary` (rulings 2 R1)

**`E_primary` is the one unambiguous key** for the pilot's gate error. It is written under
exactly that name in every per-world row of the evaluator report, at both stages, and
nothing else in the report should be read as "the" E.

```
e(S)        = mean over S of (prediction − noise_free_response)^2 / V
E_panel1    = ( e(panel1, h=1) + e(panel1, h=2) + e(panel1, h=4) ) / 3
E_panel2    = e(panel2)                       # 16 units, one target each
E_primary   = ( E_panel1 + E_panel2 ) / 2
```

Every clause matters and each is asserted by a hand-computed test:

* **`E_panel1` is the equal average of the three horizon-specific means, NOT a flat mean
  over its 6/5/5 targets.** The two differ whenever the horizons differ; h=1 carries six
  targets and h=2 and h=4 five each, so a flat mean would over-weight h=1.
* **`E_panel2` is the equal average of its 16 units.** Each unit has exactly one target,
  so a flat mean over those 16 targets *is* that equal average.
* **`V` is the fixed evaluator-only constant from ruling B6** — panels 1 and 2, equal
  panel weighting, population variance (`ddof=0`), floor 0.05 — looked up per
  `(outer_split, task A, family)`. It is never recomputed from predictions.
* **Panels 3 and 4 are scored and reported separately as guards, and neither enters
  `E_primary`.** In particular **no panel-4 branch enters it even though panel 4's
  recipes are ordinary and composition**: a target carries the panel that *owns* it
  (panel 4), not the panel its recipe imitates.
* **All 96 targets are still scored**, and `E_all_targets` reports the flat mean over all
  of them — a descriptive figure, never the gate.
* **`E_initial` uses this identical definition on identical panels.** Stage is part of the
  grouping key, so the initial and final passes run the same code; the learned-case
  comparison in R1 (`E_512 ≤ 0.50` and `E_512 ≤ 0.75 × E_initial`) therefore compares
  like with like.

**A missing case invalidates rather than shortening a denominator** (R2). If any horizon
is short of its registered count, or panel 2 short of 16, that term and `E_primary` are
non-finite and serialize as `null`; `complete` is false. A truncated prediction file can
never produce a valid-looking gate number.

Training and selection use observed y and the public constant 0.25; `V` and the noise-free
responses are evaluator-only and never enter a public file.

**Ruling B2 (confirmed): all 96 targets are always present to the evaluator.** Prefix-A
observations keep their Bernoulli(0.75) missingness and forecast observations stay blank;
availability never removes a target or half a pair. B2 is an evaluator-availability rule
and never an unmasked sensor fed into a rollout.

**Ruling B6 (confirmed):** `V` stays evaluator-only, from panels 1 and 2 with equal panel
weighting, population variance (`ddof=0`) and the 0.05 floor.

### 3.3 Start-up diagnostic — ruling C9, evaluated in binary64

The evaluator finalises this **after predictions are sealed** (ruling C10). Nothing here
can reach a trainer or change an update schedule, and a per-case label never authorizes
extra updates or a selective restart.

From the audit predictions, per `(arm, seed, world)` and per stage:

```
L      = mean((prediction − observed_label)^2) / 0.25      # the training-label loss
E_fit  = mean((prediction − noise_free_response)^2) / V     # evaluator-only diagnostic
```

Then, with `L_initial`, `L_final`, `E_fit_final` and the final query `E_primary`:

```text
r = (L_initial - L_final) / L_initial
never_started = (r < 0.10 - 1e-12) AND (E_fit_final >= 0.80)
```

binary64, **no rounding and no library `isclose`**, and no tolerance is applied to any
other threshold. Consequently `L_initial=1.0, L_final=0.90` is **not** `never_started`
(its `r` is `0.09999999999999998`, above `0.099999999999`).

Status precedence, highest first:

| status | condition |
| --- | --- |
| `infrastructure_incomplete` | an audit case or a required final query E is missing at either stage |
| `numerical_failure` | `L_initial`, `L_final`, `E_fit_final` or `r` is NaN/Inf |
| `initially_at_floor` | `L_initial <= 1e-8` |
| `never_started` | the predicate above |
| `started_not_yet_learned` | `E_fit_final > 0.25` |
| `learned_failed_to_transfer` | `E_fit_final <= 0.25` and final query `E_primary > 0.50` |
| `learned_with_generalization` | `E_fit_final <= 0.25` and final query `E_primary <= 0.50`; also reports `reached_query_0_25` |

A non-finite or absent measurement serializes as JSON `null`; its meaning is carried by
`status`, never by a rounded number. A missing or non-finite required measurement can
never become a successful start-up.

Each row also carries `E_fit_initial`, `E_query_initial`, `n_audit_cases_expected`,
`n_audit_cases_initial`, `n_audit_cases_final`, `V`, `family`, `outer_split` and the rung
label each stage's query E came from. When several rungs supply query predictions at one
stage, the largest numeric rung is used (the registered B=512 endpoint); non-numeric
ambiguity is reported as incomplete rather than guessed.

## 4. Panels — 64 units, 96 targets per world

| panel | id | units | targets | prefix / horizon | detector |
| --- | ---: | ---: | ---: | --- | --- |
| ordinary | 1 | 16 | 16 | `8−h` / h ∈ {1×6, 2×5, 4×5} | `(last_action.source, NONE)` |
| new composition | 2 | 16 | 16 | 4 / 4 | `(j, NONE)` |
| relevant intervention pairs | 3 | 16 | 32 | 4 / 4, branches `treated`/`control` | `(i, NONE)` |
| irrelevant-change pairs | 4 | 16 | 32 | mixed, branches `base`/`edited` | `(a, NONE)` / `(σ(a), NONE)` |

16 + 16 + 32 + 32 = 96. Panel 3 pairs share properties, masks and sensor-noise draws, so
the noisy difference equals the noise-free difference. Panel 4's edited branch permutes
local IDs, carries public channels 0 and 1 with their object, replaces channels 2..5 with
independent `U[−2,2]`, maps actions and the detector with the same permutation, and reuses
the base branch's noise — the edited branch is **re-simulated, not copied**, so the audit
check that `r` is unchanged is a real check.

**Ruling B3 (confirmed):** panel-4 ordinary horizons are `(1,1,1,2,2,2,4,4)` on units
0..7, with equal pair-unit weighting. **Ruling B7 (confirmed):** panel 4's eight ordinary
and eight composition recipes are fresh and independently keyed from panels 1/2; the two
branches of a pair are one unit. The 64 units are independently sampled conditional on
their world — they are **not** 64 independent world replications.

### 4.0 Disclosure — pair membership is recoverable from the public tensors alone

*(Agent 3 pilot audit §3.2, finding L6. **Ratified by rulings 2, "Public-interface
ratification".** Documentation only; no generated byte changes.)*

Rulings 2 ratifies this disclosure in terms: pair membership can be recovered by comparing
public property blocks, and action inputs partly reveal panel membership; the private
boundary is procedural, not cryptographic; **these identities must not be described as
impossible to reconstruct**.

Section 4.2 discloses that the action sequence partly reveals panel membership. That
understates it. **Pair membership is recoverable from `query_records.npy` with no
generator access at all**, in every world:

* **Panel 3** (relevant-intervention pairs): the two branches of a pair share an
  **identical 24-float property block** (channels 0–5 of all four objects), because the
  pair is defined by an intervention on an otherwise identical world state. Grouping the
  96 query sequences by that block recovers all 16 pairs exactly and identifies them as
  panel 3.
* **Panel 4** (irrelevant-change pairs): the nuisance edit permutes objects and replaces
  channels 2–5, but **channels 0 and 1 travel with the object**. Matching the multiset of
  (channel 0, channel 1) rows across sequences recovers 16 of 16 pairs per world.

This is intrinsic to the panel definitions; removing it would mean redrawing panel-3
branch properties independently and refreshing all six panel-4 channels, which changes the
panel semantics and would be a further versioned amendment. It is therefore disclosed
rather than fixed.

#### Registered architectural constraint — **ratified** (rulings 2)

In Astra's words: **"Each query branch must be predicted independently."**

* No prediction may inspect another query branch, **including its paired counterpart**.
* No cross-query state, batch statistics, pair detection, joint fitting or prediction
  copying is allowed. Episode-local state is reset per sequence.
* **Shared fitted weights and the registered support history are allowed.**
* Vectorized inference is allowed **only with independent lanes and the same results as
  separate inference**.
* *"One query unit at a time" must not be interpreted as permission to give a predictor
  both branches of a paired unit.*
* This applies to **every later arm** as well as pilot G/T, and must be verified in their
  interface audits.
* **The evaluator alone rejoins paired predictions for scoring**, after predictions are
  sealed.

The earlier phrasing — "no arm may condition on more than one query unit at a time" — is
superseded by the sentence above, because a paired unit contains two branches and that
phrasing could be read as permitting both. Why it matters: prereg §7 guard 7 requires
normalized MSE ≤ 0.02 between a pair's two mapped predictions, so a batch- or set-level
arm carrying cross-unit state could satisfy the guard by **detecting the pair and copying
the prediction**, and the guard would then measure pair detection rather than invariance.
Ruling B8 already forbids routing to panel-specific predictors; this extends the same
reasoning to pair-specific behaviour a model could discover for itself.

### 4.1 Reserved composition — ruling B1 (the versioned change)

`APPLY_COMPOSITION_EXCLUSION_TO_PANELS = True`.

* Every **complete** ordinary action string — panel 1's sixteen units and panel 4's units
  0–7 — is redrawn whole until its eight verbs contain no `[pulse, contact, invert, read]`
  window.
* Every **composition unit's four-action prefix** — panel 2 and panel 4 units 8–15 — is
  redrawn whole under the same test. Its forced four-action suffix is **never inspected
  and never rejected**, so the complete string deliberately contains the reserved
  composition exactly once, at positions 4..7.
* Rejection is **action-only** (verbs only), irrespective of arguments or outcomes;
  whole-string redraw; `MAX_ACTION_ATTEMPTS = 10000`; each attempt has its own namespace
  `.../actions/{attempt}`.
* Panel 3's strings are fully forced and contain no contact, so nothing can be rejected.
* The same rule governs source and task-B query recipes.
* The discovery and discovery-validation streams already excluded it in `ct20-v1` and are
  **unchanged**.

Measured effect, for the **twelve worlds actually generated** into `calibration-v1.1`
(24 complete ordinary strings + 24 composition prefixes per world per stream):

| scope | complete ordinary | redrawn | composition prefixes | redrawn |
| --- | ---: | ---: | ---: | ---: |
| `source-query` (the panels that are written) | 288 | **1** | 288 | **0** |
| `reuse-query` (task-B recipes; shape only, not generated in the pilot) | 288 | 2 | 288 | 0 |

The single affected written recipe is panel 4, unit 5, in validation C world
`b6b482aeb1c7e58c`; it moves both the `base` and the `edited` branch of that pair from
−0.22805 to −0.15013. Every redraw that occurred needed exactly **two** attempts; no
recipe anywhere came near `MAX_ACTION_ATTEMPTS`. Panel 1 and panel 2 were uncontaminated
in all twelve worlds, so every `V` — and therefore `private/normalization.json` — is
byte-identical to `ct20-v1`. The change is still a versioned amendment because it changes
the evaluation distribution.

For completeness, across the **full 36-world pool** (28 non-M plus 8 held-out M worlds,
most of which are never generated in the pilot) the same rule rejects 15 of 1,728 complete
ordinary strings and 1 of 1,728 composition prefixes, both streams combined.

### 4.2 Ordering

Panel identity, unit, branch, pair membership and query horizon are **private**. Query
records are emitted in a deterministic hash order, not panel order, so position does not
disclose the panel: the ordering key is `sha256("<wpid>/order/<panel>/<unit>/<branch>")`,
derived by hashing rather than by a new RNG stream, because the registered namespace
table has no ordering stream. Honest limit (ruling B8): the action sequence itself still
partly discloses panel membership — the reserved four-verb suffix is recognisable — so
this hides grouping, not membership. The harness may not route to panel-specific
predictors or expose private panel/pair labels.

Fitting-audit records are **not** hash-ordered: ruling C10 requires their
episode/horizon/endpoint key to be public, so they are emitted in
`(episode_index, horizon)` order. They carry no panel.

## 5. Seeds and namespaces

Stream seed = unsigned little-endian integer of the first eight bytes of
`SHA256(namespace)`; generator is `numpy.random.Generator(PCG64(seed))`. NumPy 2.5.3,
CPython 3.12.14 (both recorded in the manifest).

**Ruling D: the RNG namespace root stays `premonition/concept-toy20/v1`**, inherited
unchanged. The experiment version label is separate and does not enter any namespace. No
world, support episode, mask or noise draw is redrawn by the amendment.

| purpose | namespace |
| --- | --- |
| world tuple | `premonition/concept-toy20/v1/world/{split}/{family}/{index}` |
| episode properties + ID permutation | `.../episode/{world_id}/{stream}/{episode_index}/public` |
| action draws | `.../episode/{world_id}/{stream}/{episode_index}/actions/{attempt}` |
| masks | `.../episode/{world_id}/{stream}/{episode_index}/mask` |
| sensor noise | `.../episode/{world_id}/{stream}/{episode_index}/noise` |
| task-B detector / label noise | `.../episode/{world_id}/reuse-fit/{episode_index}/detector-b` , `.../noise-b` |
| panel-4 edit | `.../panel/{world_id}/4/{unit}/edit` |

**Streams.** ACTIVE: `discovery` (support), `source-query` (panels), `reuse-fit`
(task-B fitting), `reuse-query` (task-B panels, unused in the pilot).
RESERVED / UNUSED WITH ZERO DRAWS: `normalization` — **ruling B6** drops it from the
active list. Removing it perturbs no other stream because every stream is an independent
SHA-256 namespace, not a position in a shared sequence.

Query `episode_index` serialization is `"{panel}/{unit}"`, so a panel episode namespace
reads `.../episode/<world_id>/source-query/1/0/public`. Panel-specific extras (panel 2's
`i`,`j`; panel 3's `i`) continue on that unit's registered `public` generator after the
properties and the ID permutation, because the namespace table registers no separate
stream for them.

**Frozen draw order** (`manifest.json -> generator_config.accepted_stream_constants`):

* world = five coefficients in the order `a, beta, g, b, c`, then `permutation(5)` for the
  public verb map;
* episode `public` = `uniform(−1,1,(4,6))`, then `permutation(4)`, then any panel extras;
* action = verb `U{0..4}`, source `U{0..3}`, then contact destination `U` over the other
  three, or pulse dose `= +1 if U{0,1}==1 else −1`;
* masks = `rng.random(8) < 0.75`; noise = `rng.normal(0.0, 0.03, size=8)`;
* panel-4 edit = `permutation(4)`, then `uniform(−2,2,(4,4))`;
* `p_public = p_internal[perm]`.

Noise, masks, actions and properties never share an RNG object. The ruling accepts these
as implemented and forbids substituting distributionally equivalent draws after freeze.

## 6. Determinism and hashing

* `manifest.json -> file_hashes`: SHA-256 of raw file bytes for every generated file
  (excluding `manifest.json` and `audit_report.json`).
* `manifest.json -> tensor_hashes`: the registered tensor hash for every `.npy`,
  `SHA256(canonical_json({dtype, shape}) + b"|" + contiguous little-endian bytes)`.
* World metadata is canonical JSON: sorted keys, `(',',':')` separators, `allow_nan=False`,
  round-trip float repr, **no timestamps**. `world_id` hashes `(version, family, verb
  permutation, coefficients)`, so cross-split duplicates are detectable; a second hash
  removes the permutation. Collisions abort generation.
* **`WORLD_TUPLE_VERSION` is pinned at `"ct20-v1"` and must never track `VERSION`.** The
  tuple hash is part of the inherited RNG identity — every episode namespace is keyed by
  `world_id` — so letting the experiment-version label into the tuple would redraw every
  world, support episode and alias, which ruling D forbids.
* Regenerating with the same configuration reproduces every hash byte for byte
  (test `generation is deterministic`).

### 6.1 The public/private separation is **procedural, not cryptographic**

Registered explicitly, because the alternative reading would overstate what the pilot
guarantees. Ratified by rulings 2: *"The private boundary is procedural, not
cryptographic. Do not describe these identities as impossible to reconstruct."*

* The split is enforced by **code discipline and audit** — the public loader's path
  checks, the forbidden-array and forbidden-key scans, the `audit --data` boundary checks
  — not by encryption, authentication or any secret.
* **Nothing in the published design is hidden.** The generator source, the seed
  namespaces, the RNG root and every registered constant are public, so anyone holding
  them can **regenerate the private quantities** — latent states, noise draws, noise-free
  responses, `V`, world coefficients and families, and **the final-split worlds**, whose
  tuples this pilot already derives for the collision audit.
* What the boundary buys is therefore that **a model cannot reach those quantities
  through its own inputs**, and that a person following the procedure will not leak them.
  It is not a claim that a determined party could not reconstruct them.
* A **secret evaluator salt** — the change that would make reconstruction genuinely hard
  — is **not** part of `ct20-v1.1`. Introducing one would change world identity and every
  derived namespace, so it is a **separately versioned amendment, to be decided before
  wave 3**, and is out of scope here.

## 7. Rulings as applied

Machine-readable at `manifest.json -> generator_config.ambiguity_rulings` and
`-> accepted_stream_constants`.

| item | ruling | status in this build |
| --- | --- | --- |
| B1 reserved composition | exclude from complete ordinary strings and composition prefixes; never reject a forced suffix | **applied**, `APPLY_COMPOSITION_EXCLUSION_TO_PANELS = True`; data regenerated |
| B2 query targets | all 96 always present to the evaluator | confirmed, unchanged |
| B3 panel-4 horizons | `(1,1,1,2,2,2,4,4)` | confirmed, unchanged |
| B4 RESET | destination = NONE, other fields zero | confirmed, unchanged |
| B5 full suffix | one scored prediction at the final QUERY | confirmed, unchanged |
| B6 normalization stream | reserved/unused, zero draws | applied: removed from `ACTIVE_STREAMS`; no other stream perturbed |
| B7 panel-4 recipes | fresh, independently keyed | confirmed, unchanged |
| B8 public hints | accepted; fixed claim wording; `outer_split` bookkeeping only | applied in wording and in the loader docstring |
| C9 start-up boundary | exact binary64 predicate, tolerance 1e-12 | applied in `startup_classification` |
| C10 evaluator boundary | evaluator finalises from sealed predictions | applied: fitting-audit set + two stages + `startup_diagnostics` |
| C11 schema | this file is the single serialized-data contract | applied |
| D version | `ct20-v1.1`, inherited RNG root, preserve earlier artifacts | applied |
| other stream choices | accept as implemented | recorded verbatim with values and draw order in section 5 |

### Rulings 2, as applied

| item | ruling | status in this build |
| --- | --- | --- |
| R1 primary error | `E_primary = (E_panel1 + E_panel2)/2`; panel 1 = equal average of the h=1/2/4 means; panels 3/4 are separate guards | **already conformed**; documented in §3.2 and now asserted by a hand-computed test |
| R1 initial reference | `E_initial` on identical panels, same definition, measured once before fitting | applied: stage is part of the grouping key, so both stages run the same code |
| R2 missing cases | a missing case invalidates rather than shortening a denominator | **code change**: a short horizon or a short panel 2 now yields `null`, not an average over what arrived |
| R2 median, R3 precedence, R4 cross-arm gap, R5 arm ties | gate-calculator and coordinator work | **not simulator work**; not implemented here |
| R4 step totals | reconciled L 370/254, H 2,163/1,588; retire 378/262 | recorded in §8.1 |
| public interface: pair recovery | ratify the §4.0 disclosure; do not call these identities impossible to reconstruct | applied in §4.0 and §6.1 |
| public interface: independence | each query branch predicted independently; no cross-query state; evaluator alone rejoins pairs | applied verbatim in §4.0 |
| public interface: padding | all-zero serialized padding normative; audited internal conventions permitted | applied in §2.3.1 |
| public interface: audit key | correct the stale claim that the spellings differ | applied in §3.1; the compatibility reader was **removed** |
| freeze | preserve prior frozen documents; record the clarified schema by a new hash; no redraw for a prose correction | applied: `ct20-v1` and the `ct20-v1.1` tensors are untouched; only this file's hash moves |

Everything previously listed as **[ruling needed]** is now resolved. The two named
conventions that a literal reading still required — `AUDIT_ENDPOINT_INDEXING` (1-based
endpoint) and `AUDIT_ELIGIBILITY` (`present[t−1] and t ≥ h`, last such `t`) — were put to
Astra, drew no objection in rulings 2, and are **registered as implemented** (§2.6).
Nothing in either rulings file was implemented non-literally.

## 8. Scope not covered here

No learner, optimizer, difficulty tuning or final-world data. Final-split world **tuples**
are derived for the cross-split collision audit only; no final episode, panel or target
exists. Family M's equations are implemented behind the evaluator boundary and
unit-checked; `calibration-data` refuses to emit an M world and no mode-family trace,
score or curve is published. Ruling A (budget tiers L/H, cost ledger, timing preflight)
is not simulator work and is not implemented here.

### 8.1 Step totals — use the reconciled ledger only

No file in the simulator, the public loader or this schema computes, stores or depends on
a step total; nothing here has ever carried the provisional figures. For the avoidance of
doubt, and because this file is the single frozen contract, the **only** step table that
may be quoted anywhere in this track is the reconciled one:

| Tier | G updates / fit | T updates / fit | G examples | T examples |
| --- | --- | --- | ---: | ---: |
| **L** (2.0e8/rung, 1.0e9/fit) | **370** | **254** | 1,480 | 1,016 |
| **H** (1.0e9/rung, 5.0e9/fit) | **2,163** | **1,588** | 8,652 | 6,352 |

The provisional **378 / 262** figures are **superseded and must not be quoted**. They were
computed before reconciliation, without initialization, the initial query panel or the
loss, and were therefore upper bounds. These totals are Agent 3's and the accounting
owner's; this table is reproduced here for freeze-time consistency, not independently
recomputed by me.

## 9. Change log — `ct20-v1` → `ct20-v1.1`

| area | v1 | v1.1 |
| --- | --- | --- |
| experiment version | `ct20-v1` | `ct20-v1.1` (manifest `experiment_version`, plus `rulings_sha256`) |
| RNG namespace root | `premonition/concept-toy20/v1` | **unchanged** |
| world tuple label | `VERSION` | pinned `WORLD_TUPLE_VERSION = "ct20-v1"`, so aliases are unchanged |
| panel exclusion | off | on (B1) |
| active streams | 5 incl. `normalization` | 4; `normalization` reserved with zero draws (B6) |
| fitting-audit set | none | `audit_*` public tensors, `audit_keys.json`, `audit_truth.json` |
| evaluator | query groups `(arm, seed, rung)` | adds `stage`, audit groups, `startup_diagnostics` |
| directories | `calibration/`, `fixture/` | preserved; new `calibration-v1.1/`, `fixture-v1.1/` |

Byte-level effect on `calibration/` → `calibration-v1.1/`, for the files present in both:

| file class | result |
| --- | --- |
| `public/<wpid>/support_*.npy` (all six, all 12 worlds) | **identical** |
| `private/<wpid>/support_*.npy` (latent, noise, noise-free, attempts) | **identical** |
| `private/world_config.json`, `private/normalization.json` | **identical** |
| `public/<wpid>/query_index`, `query_n_records`, `query_padding_mask`, `query_record_ids.json` | **identical** (12/12) |
| `public/<wpid>/query_records.npy`, `query_detector.npy` | identical for 11/12; changed for one validation C world |
| `private/<wpid>/query_truth*.{json,npy}` | identical for 11/12; changed for the same world |
| `public/worlds.json` | changed (version label, added `n_audit_records`) |
| `collision_report.json` | changed (version label only) |

The `fixture/` → `fixture-v1.1/` comparison changes only `fixture.md` (version line),
`public/worlds.json`, `manifest.json` and `audit_report.json`; every fixture tensor that
exists in both is identical. Both folders additionally gain the new `audit_*` files
(13 per world, 156 in the calibration folder and 26 in the fixture); **no file present in
`ct20-v1` disappeared in `ct20-v1.1`**, which is the byte-level proof that no world
directory was renamed and therefore that no world was redrawn.

### 9.1 Documentation-only additions after Agent 3's pilot audit

Folded in at the coordinator's request; **none changes a generated byte** (verified by
regenerating both folders and diffing: 0 of 389 and 0 of 72 files differ).

| item | audit ref | where |
| --- | --- | --- |
| Pair membership is recoverable from the public query tensor; branch-independence constraint (**ratified by rulings 2**) | §3.2 / L6 | §4.0 |
| Serialized padding convention declared normative; byte-equality asserted only to `n_records` | §4.1 | §2.3.1 |
| Public `audit_*` tensors, the 144/143 sizes and the one-row unused reservation | note 12 | §2.3 |
| Reconciled step ledger (L 370/254, H 2,163/1,588); provisional 378/262 superseded | §5.3 | §8.1 |

### 9.2 Rulings 2 incorporation

Applied after `design/v3/20-concept-toy-rulings-2.md`. **No tensor byte changed**, in
either folder: `calibration-v1.1` and `fixture-v1.1` were regenerated and every data file
compared identical. The only generated files that moved are the two `manifest.json`s and
the two `audit_report.json`s, and the manifests moved by exactly two added provenance
fields, `rulings2_file` and `rulings2_sha256`. Each manifest's own `file_hashes` block —
which covers every data file — is unchanged, which is the byte-level proof.

| item | where | effect |
| --- | --- | --- |
| R1 `E_primary` documented under one unambiguous key | §3.2 | documentation; the definition already conformed |
| R2 a missing case invalidates rather than shortening a denominator | §3.2, evaluator | **the one code change**: short horizon or short panel 2 → `null`, and `E_primary` with it |
| §4.0 ratified; branch-independence stated in Astra's words | §4.0 | documentation |
| §2.3.1 padding ratified; cross-producer real-row equality checked separately | §2.3.1 | documentation |
| stale audit-key-mismatch prose corrected; compatibility reader removed | §3.1, simulator | dead code removed; a retired-spelling key is now an unknown record ID |
| audit endpoint indexing and eligibility registered as implemented | §2.6, §7 | documentation |
| public/private separation registered as procedural, not cryptographic | §6.1 | documentation |
| rulings-2 hash stamped beside rulings 1 | header, all three manifest sites | two added manifest fields |

The compatibility reader described in the previous revision of §3.1 — which accepted the
models builder's earlier `e{ep}/h{h}/t{t}` spelling — **no longer exists**. The frozen
models build calls `PublicDataset.audit_key` itself, so there is one spelling and one
only.

**Unresolved:** the coordinator quoted rulings 2 as SHA-256 `8a62ef05…`; the file in this
worktree hashes to `1245e46f…`, measured twice. Everything above was applied from the
bytes that hash to `1245e46f…`. This must be reconciled before the freeze.
