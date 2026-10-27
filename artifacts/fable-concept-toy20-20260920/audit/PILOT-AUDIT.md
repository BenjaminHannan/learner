# concept-toy20 — Agent 3 independent pilot audit

Agent 3 (independent auditor and scorekeeper) · 20 September 2026 · target version **`ct20-v1.1`**

I did not co-author or repair any builder code. Everything under `audit/` is mine; every
other file was read only. No learner was fitted, scored or evaluated on the registered
calibration worlds. No M-family trace, curve or score appears here — the M checks below
are truth-table algebra only.

## 0. What I audited, and the hash problem

Astra's rulings identify the reviewed inputs by these prefixes:
`32f2dc6b` (simulator), `1ed617e1` (loader), `e21b0fde` (models), `581ef7ce` (schema).

At the time of writing, the files on disk are:

| File | sha256 | vs. Astra's reviewed build |
| --- | --- | --- |
| `design/v3/20-concept-toy-rulings-1.md` | `40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de` | **matches** the announced `40f65045…` |
| `scripts/fable_concepttoy20_sim.py` | `c79796a11b3477c79da992165d6513748e738dfc7d133dd370c6476b17a46aef` | changed from `32f2dc6b…` (B1 patch) |
| `scripts/fable_concepttoy20_public.py` | `7139c6989f8618dcca9d4ef2e31b5c667424e3fca8a183e8f30b36a1e3b567fe` | changed from `1ed617e1…` |
| `scripts/fable_concepttoy20_models.py` | `20be25cd3862029ab493ec2fbecf9a1354870ff65ec8a6fe2b001cf1ffe1832a` | changed from `e21b0fde…` (tier/ledger patch) |
| `artifacts/…/SCHEMA.md` | `d9164faf02c7f7ed3ec4d87015e72cfaba5efbe2022ae0ebc99d6a96f9dfe4b1` | changed from `581ef7ce…` |

**Reported sha mismatch:** four of the five reviewed inputs no longer match the build
Astra reviewed. That is expected — they are the ruling patches — but it means Astra's
`ct20-v1` code review does not transfer to these files, and the models module changed
**twice while this audit was running** (`7b8ffb71…` → `20be25cd…`). Every result below is
therefore tied to the hashes in the table; they must be re-verified against the final
frozen bytes. This is the first reason the freeze verdict is NO.

Data: `calibration/` and `fixture/` are the ct20-v1 builds; `calibration-v1.1/` and
`fixture-v1.1/` are the regenerated B1 builds. Both were audited.

My scripts, all under `audit/`:

| Script | What it is |
| --- | --- |
| `independent_oracle.py` | my re-implementation of the whole generator from the spec text; imports nothing from the simulator |
| `check_generator.py` | 21 independent generator checks (`python check_generator.py calibration-v1.1`) |
| `check_leaks.py` | 11-entry data-boundary review |
| `check_models.py` | 24 model-side invariants on synthetic episodes and the published fixture |
| `check_accounting.py` | independent op-ledger recomputation under three conventions |
| `check_v11_audit_set.py` | the new public `audit_*` tensors |
| `gate_calculator.py` | the pure numerical gate calculator |
| `test_gate_calculator.py` | 112 hand-built boundary tests |

---

## 1. Verdict table

| # | Item | Verdict | Evidence |
| --- | --- | --- | --- |
| 1 | Independent generator checks | **PASS** (v1.1) | 21/21; `generator_check_results-calibration-v1.1.json` |
| 2 | Data-boundary / leak review | **AMBIGUOUS — needs ruling** | one undisclosed leak (L6); the public/private boundary is procedural, not cryptographic |
| 3 | Models: causality, rollout, lanes, resume, counts | **PASS** | 24/24; `model_check_results.json` |
| 4 | Accounting / cost ledger | **PASS on arithmetic, FAIL on the timing preflight** | 14/14 arithmetic checks; the L+H second-level projection does not exist |
| 5 | Gate calculator + boundary tests | **PASS** | 112/112; `gate_calculator_test_results.json` |
| 6 | Unflagged spec ambiguities | **AMBIGUOUS — needs ruling** | 9 items below, 3 of them gate-affecting |

**FREEZE-READY: NO** — see §8 for the exact closing conditions.

> **SUPERSEDED.** The line above, and every `FREEZE-READY` line before the Closure
> section, is the verdict of an earlier dated pass and is retained only as history. The
> **single operative verdict for `ct20-v1.1` is the last line of the document**, in
> "Closure — `ct20-v1.1` final bytes". Read that one.

---

## 2. Item 1 — Independent generator checks · PASS

I wrote `independent_oracle.py` from `20-concept-toy-simulator-spec.md` alone. It never
imports the simulator, so the simulator is the thing under test and my file is the oracle.
Five conventions the spec does not fix (internal verb order, action draw order, mask draw,
episode public stream, RESET destination) are declared at the top of that file as copied
from the builder's ruling constants — an "independent" derivation cannot invent them, and
Astra's "Other stream choices: accept as implemented" paragraph now registers them.

Against `calibration-v1.1/`, all 21 checks pass:

* **World tuples** — all 12 calibration worlds reproduce from the namespace
  `premonition/concept-toy20/v1/world/{split}/{family}/{index}`: family, split, index, all
  five coefficients to exact float equality, both world IDs, the verb permutation and the
  16-hex public alias.
* **Collisions** — over the full registered universe of 36 worlds (train 6 + validation 6 +
  final 24), all 36 canonical tuples, all 36 permutation-free hashes and all 36 aliases are
  distinct.
* **Support episodes** — for each world, all 64 discovery episodes reproduce exactly:
  latent trajectories, noise-free responses, noise draws, observed targets after the
  float32 cast, present masks, the action-rejection attempt counts, and the full
  64×17×44 public record tensor rebuilt by my own tokenizer.
* **C-family conservation** — under `contact` the sum of `q` is preserved to <1e-12 and
  only objects *i* and *j* change; `pulse` and `invert` touch exactly one object;
  `read` and `wait` are bit-for-bit inert. Checked on every transition of every C world.
* **M-family truth tables** — verified exhaustively over all 16 states × all (i,j) pairs:
  `pulse +1` flips, `pulse −1` clears, `contact` XORs the source into the **destination
  only**, `invert` flips, `read`/`wait` inert. M contact does **not** conserve a sum, which
  is the structural contrast with C. Equations only; no M trace, curve or score is emitted
  anywhere in this audit.
* **O/N no hidden storage** — latents are identically zero, and the response is a pure
  function of the source object's public properties with no history dependence.
* **Reset scope** — `latent[:, 0, :] == 0` for every episode of every world.
* **Mask independence** — over 12×64×8 = 6,144 draws, present rate 0.7469 and
  |corr(present, noise-free)| < 0.02.
* **Nesting** — the 32/64/128/256/512 prefixes are genuinely nested (rung ≤ r is exactly
  the first B/8 episodes) and the 3:1 fit/selection split holds inside every prefix, with
  index 3 of every group of four being the selection episode.
* **Split disjointness** — no property signature is shared between any support episode and
  any query episode.
* **Panels** — all 96 targets per world reproduce exactly, including the hash ordering key
  `sha256("<wpid>/order/<panel>/<unit>/<branch>")`, the record IDs, panel/unit/branch
  labels, horizons, prefix lengths, detector indices, and both the noise-free and noisy
  truth values.

**Ruling B1 is correctly applied.** In the ct20-v1 build, **1 of 288** genuinely ordinary
action strings contained the reserved composition (world `b6b482aeb1c7e58c`, panel 4,
ordinary unit 5) against an analytic expectation of ≈2.3. In `calibration-v1.1/` the count
is **0 of 288**. I counted only *genuinely* ordinary strings — panel-1 units and panel-4
ordinary units 0–7 — because panel-2 and panel-4 units 8–15 carry the reserved suffix by
construction, and the panel-4 `edited` branch is an object relabelling of `base` with an
identical verb string.

A byte-level diff of the two builds confirms the amendment is minimal and correctly scoped:
**exactly one world's** `query_records.npy` / `query_truth*` / `query_detector.npy` changed
— `b6b482aeb1c7e58c`, the world I had flagged — and every `support_*` file, every
`world_config.json` entry and `normalization.json` are byte-identical. That is what B1's
"preserve unchanged world tuples and discovery supports" requires. The redraw is invisible
in the other 11 worlds because attempt 0 already satisfied the grammar there.

One implementation trap worth recording, because getting it wrong is silent: B1 says
"apply discovery-grammar exclusion to the four-action prefix of composition units … keep
their required suffix" and "do not reject a forced composition suffix". Rejecting on the
*concatenation* would reject every draw forever, since the suffix **is** the reserved
string. Rejecting on the prefix alone is safe and equivalent here, because the forced
suffix begins with `pulse`, so no occurrence of `(pulse, contact, invert, read)` can
straddle the prefix/suffix join. The builder did it correctly — my oracle rejects on the
prefix alone and reproduced the tensors byte-for-byte.

### New in v1.1: the public `audit_*` tensors · PASS

`calibration-v1.1/public/<wpid>/` now publishes the deterministic fitting audit set
(`audit_records`, `audit_episode_index`, `audit_horizon`, `audit_endpoint`,
`audit_observed_label`, `audit_keys.json`, …), which ruling C10 requires for stable
episode/horizon/endpoint keys. Publishing it is safe: I rebuilt the set from the
**public** support tensors alone — for each fit episode in the B=512 prefix and each
h ∈ {1,2,4}, the last eligible observed endpoint — and it reproduces exactly for all 12
worlds. Published labels equal the public support observations, and the forecast window is
blanked (sensor = 0, present = 0). No evaluator-side value is published.

It does make the public file-size signature non-uniform (previously 1 signature across all
12 worlds, now 2 audit-set sizes: 144 rows for 11 worlds, 143 for `db0d29339a47b284`).
That is not a leak — the audit-set size is a function of the already-public present mask —
but it is a change worth recording in the schema. It also produces exactly the situation
ruling A1 legislates for: the frozen reservation charges the **largest legal** set of 144,
so the step table stays data-independent, and the one-row shortfall is an **unused
reservation** that must be reported separately and must not be spent on extra fitting. The
builder's `audit_targets()` is data-independent, so this is compliant as implemented.

---

## 3. Item 2 — Data-boundary and leak review · AMBIGUOUS, needs ruling

Eleven entries in `leak_review-calibration-v1.1.json`. Three findings matter.

### 3.1 The public/private boundary is procedural, not cryptographic — *note, but it must be said plainly*

There is no secret seed, salt or key anywhere in this design. Every quantity the
experiment treats as private is a deterministic function of publicly documented namespace
strings. Working from the design document alone I regenerated, for all 12 calibration
worlds: the family, all coefficients, the verb permutation, the normalization constant `V`
(to <1e-12 on all 6 published values), every latent state, every noise draw, every
noise-free response, every noisy target, and the full panel/unit/branch identity of every
one of the 96 records — including the `QUERY_ORDER_BY_HASH` ordering, whose key uses only
public inputs and is therefore fully invertible.

This is not a defect in the builders' work: the prereg's confidentiality model is
procedural ("the evaluator holds hidden responses"), and inside a single honest pipeline
that is adequate. But **the identical procedure applies verbatim to the 24 FINAL worlds**,
which wave 3 depends on being untouched. Anyone with the design document can compute the
wave-3 answers today. The protection is that nobody does it, not that nobody can.
Recommend an explicit statement to that effect in the manifest, and — if wave 3 is ever to
carry weight — a secret salt for the final split, introduced now, before those worlds are
generated.

### 3.2 L6 — undisclosed pair-membership leak · **must fix before the freeze (disclosure)**

`SCHEMA.md` §4 discloses only that the action sequence *partly* reveals panel membership.
It does not disclose that pair membership is recoverable from the public query tensor with
no generator access at all:

* **Panel 3** (relevant-intervention pairs): both branches of a pair share an **identical
  24-float property block**. Grouping the 96 query sequences by that block recovers all 16
  pairs per world exactly, in every world, and identifies them as panel 3.
* **Panel 4** (irrelevant-change pairs): the edit permutes objects and refreshes channels
  2–5, but channels 0 and 1 travel with the object. Matching the **multiset** of
  (channel 0, channel 1) rows recovers 16 of 16 pairs per world.

In the current Phase-A architecture each query sequence is forwarded independently, so
there is no exploitation path today. The risk is at wave 3: prereg §7 guard 7 requires
that on irrelevant pairs "normalized MSE between its two mapped predictions is ≤ 0.02".
Any batch-level or set-level model — and P/T-pool are exactly the arms that carry
cross-unit state — could satisfy that guard by *detecting the pair and copying the
prediction*, without any invariance. The guard would then be measuring pair detection, not
invariance.

Two acceptable resolutions, both cheap: (a) disclose it in SCHEMA.md §4 and add a
registered architectural constraint that no arm may condition on more than one query unit
at a time, enforced by the harness; or (b) redraw panel-3 branch properties independently
and refresh all six panel-4 channels. Option (b) changes the panel semantics and would be
a further versioned amendment, so (a) is the proportionate fix. Ruling B8 already forbids
routing to panel-specific predictors; this extends the same reasoning to pair-specific
behaviour that the model could discover for itself.

### 3.3 L5d — N is separable from the public tensors by a one-line statistic · *note*

Max |y| over present observations separates the noise-only family cleanly:
N ∈ {0.075, 0.090}, O ∈ {0.391, 0.555}, C ∈ {0.620 … 0.919}. This is intrinsic — the
learner is *meant* to see y — but it does mean "no model gets a family tag" is a statement
about code discipline, not about the data. Worth one sentence in the report so that a
control arm's restraint on N is not over-claimed.

### 3.4 Checks that came back clean

* No float32 equal to a record's noisy target occurs anywhere in its own public query
  sequence (12 × 96 sequences). QUERY rows carry sensor = 0 / present = 0 and the target's
  OBSERVED row is never built.
* Prefix length (16), query index (15) and detector-b (NONE) are constant across the whole
  pilot, so padding length and the detector cannot separate panels or families.
* Pulse rate 0.178–0.240, contact rate 0.158–0.221, present rate 0.740–0.775 — all
  consistent with the family-free 1/5 and 3/4 draws. `dose ≠ 0 ⇒ pulse` and
  `destination ≠ NONE ⇒ contact` remain the registered, accepted public hints (ruling B8).
* Support and query tensor layouts are byte-identical across worlds apart from the
  audit-set size discussed above.

### 3.5 L8 — `outer_split` in the public index · *note only, already flagged by the builder*

`public/worlds.json` carries `outer_split`, and the public loader returns it from
`worlds()` / `worlds_in_split()`. Ruling B8 permits it "in coordinator bookkeeping only,
never in model features or split-conditioned fitting choices". Nothing but code discipline
enforces that today. A one-line change — having the loader's per-world feature accessor
refuse to return it — would make the ruling mechanical rather than aspirational.

---

## 4. Item 3 — Models · PASS

All 24 checks in `model_check_results.json` pass, run against
`fable_concepttoy20_models.py` @ `20be25cd…`. Nothing here touched the calibration worlds:
every learner-touching check used synthetic episodes or the published fixture.

* **Causality**, two independent tests per arm: perturbing observations *after* the
  endpoint, and perturbing records strictly after the endpoint, change the prediction by
  exactly 0.0 for both G and T (`max|d| = 0.000e+00`, not "small"). Ruling C2's
  self-inclusive mask (`j <= i`) is what is implemented.
* **Blank rollout**: the forecast substitutes OBSERVED tokens with sensor = 0 and
  present = 0, keeps properties/action/source/destination/dose and the OBSERVED type
  (ruling C1), and never builds the target's own OBSERVED record. QUERY tokens never carry
  a measurement.
* **Lane isolation**: a vectorised lane equals the same unbatched run to `max|d| = 0.0`
  after 6 updates, and lane 0's output has **exactly zero** gradient into lane 1's
  parameters. Optimizer moments carry the lane dimension, and clipping reduces over the
  lane axis only — a global norm would have broken the unbatched-equality test.
* **Exact resume**: weights, both Adam moments and the update cursor reproduce bit-for-bit
  across a save/load at step 9 (`max|dw| = max|dm2| = 0.0`).
* **Minibatch stream** is a pure function of (world, seed, rung, update), matching ruling
  C6's draw order and ruling D's "no tier salt in shared data streams".
* **Parameter counts recomputed from the instantiated tensors**, not from a constant:
  G = 5,040 + 881 = **5,921**; T = 6,000 + 881 = **6,881**. Both match the spec.
  The decoder's 8 pool-coordinate columns are exactly zero in Phase A — reserved storage,
  not active capacity.
* **Trainer/evaluator separation** by AST import analysis: the model module imports no
  simulator or evaluator module and references no evaluator-side file or field name
  (`noise_free`, `query_truth`, `world_config`, `support_latent`, `normalization.json`,
  `private/`). The public loader's AST imports are `__future__`, `dataclasses`, `json`,
  `numpy`, `pathlib`, `typing` — nothing from the simulator. Loaders refuse any field
  outside the public contract.
* **Fixture agreement**: Agent 2's tokenizer reproduces Agent 1's records 0–15 bit for bit
  on both fixture worlds (`max|d| = 0.0`), with the endpoint at the final QUERY.

### 4.1 Padding convention divergence · *note, but it will bite a byte-equality assertion*

Agent 1 pads query rows past `n_records` with all-zero rows. Agent 2's `build_sequences`
leaves the static 24-float property block on those rows. This is mathematically harmless —
the causal mask plus the endpoint gather means padded rows cannot reach the prediction, and
I verified that directly — but the two tensors are **not byte-identical past the
endpoint**. Ruling C11 freezes "the amended SCHEMA.md as the single serialized-data
contract" and requires the driver to use the boundary-checked public path. Either the
schema must state which convention is normative, or any future cross-producer byte-equality
assertion will fail for a benign reason and be "fixed" in the wrong direction.

### 4.2 A comment that contradicts its own code · *note only*

In `fable_concepttoy20_models.py` (near the RESET record construction) a comment states
that destination NONE "is *also* zero here" while the next line sets it to 1.0. The code
is correct and agrees with Agent 1 and with ruling B4. The comment is wrong and invites a
breaking "fix". One-line deletion.

---

## 5. Item 4 — Accounting · PASS on arithmetic, FAIL on the timing preflight

`check_accounting.py` recomputes the ledger from the declared constants and the
architecture shapes without calling the builder's cost functions as the oracle.

### 5.1 The declared conventions reproduce exactly

| Quantity | Mine | Builder |
| --- | --- | --- |
| G forward, one 17-record sequence | 178,881 | 178,881 |
| T forward, one 17-record sequence | 241,917 | 241,917 |
| G, one complete update | 2,229,520 | 2,229,520 |
| T, one complete update | 2,999,392 | 2,999,392 |

Dense 17×17 attention is charged, as ruling A1 requires "when that is what executes".

### 5.2 The ruling A1 reconciliation is complete

Astra required initialization, **both** initial prediction sets, all rung query/selection
forwards, final fitting diagnostics and loss computation to be reconciled with actual
execution. The current build itemises exactly those categories in `rung_reservation()`:
`initialization`, `initial_audit_forward`, `initial_audit_loss`,
`initial_query_panel_forward`, `rung_query_panel_forward`, `selection_forward`,
`selection_loss`, `final_audit_forward`, `final_audit_loss` — no category missing for
either arm. The fitting loss is inside the per-update charge. The gap Astra named (rung 1
reserved the initial fitting audit but charged neither initialization nor the **initial
query panel** that the calibration gate needs for initial query E) is closed.

### 5.3 The headline: 378/262 is superseded

Under the reconciled ledger, a complete tier-L fit buys:

| Tier | G updates / fit | T updates / fit | G examples | T examples |
| --- | --- | --- | --- | --- |
| **L** (2.0e8/rung, 1.0e9/fit) | **370** | **254** | 1,480 | 1,016 |
| **H** (1.0e9/rung, 5.0e9/fit) | **2,163** | **1,588** | 8,652 | 6,352 |

My independent recomputation reproduces the builder's frozen step table exactly for all
four tier×arm combinations. The provisional 378/262 figures were computed before
reconciliation — without initialization, the initial query panel or loss — so they were
upper bounds, exactly as ruling A1 anticipated in calling them provisional. **Both tiers'
tables must now be frozen at 370/254 and 2,163/1,588.**

### 5.4 Sensitivity to the op-counting convention

| Convention | L/G | L/T | H/G | H/T |
| --- | --- | --- | --- | --- |
| Registered (MAC=2, dense attention, backward=2×, AdamW=11, clip=3) | 370 | 254 | 2,163 | 1,588 |
| Alternative (MAC=1 fused, causal-triangular attention, all non-MAC ops = 1) | 773 | 618 | 4,177 | 3,403 |
| Third (registered operators, backward=1×, no optimizer charge) | 577 | 394 | 3,372 | 2,461 |

The update total moves by a factor of ~2.1 between the most and least generous
conventions, and — importantly — **the G/T ratio moves too** (1.46 registered, 1.25
alternative, 1.46 third). So the convention is not merely a scale factor: it changes how
much more training the GRU gets than the transformer. That is an argument *for* Astra's
A1 decision to freeze one disclosed convention and label it an estimate, and *against* any
later claim that the arms received "equal compute" in any hardware sense. The report must
say "equal counted operations under the registered estimate", never "equal compute".

### 5.5 The per-rung 5% cross-arm rule · PASS

Checked with my own calculator, not the builder's, on the planned reservation at every
rung of both tiers:

* Tier L: gaps 0.0006, 0.0010, **0.0141**, 0.0008, 0.0001 — worst 1.41% at B=128.
* Tier H: gaps 0.0006, 0.0002, 0.0001, 0.0002, 0.0004 — worst 0.06%.

Both are inside 5% at every rung, and no arm exceeds its per-rung or per-fit allowance.
This is the *planned* view; ruling A1 also requires the same test on **executed**
operations from the run ledgers, which cannot be checked until wave 1 runs.

### 5.6 Would a "toy too hard" verdict be confounded by the budget? · **Yes, at tier L**

Stated plainly, because this was the question: tier L buys **370 (G) / 254 (T) complete
optimizer updates for an entire fit across all five nested rungs** — 1,480 and 1,016
sampled (episode, endpoint) examples in total — for models of 5,921 and 6,881 parameters
on an eight-step forecasting task with 25% missing observations. That is two to three
orders of magnitude below what a small sequence model normally needs. A tier-L "too hard"
verdict is therefore **not separable from simple under-training on its own evidence**.
Ruling A3 already forbids reading it that way and mandates tier H, which is the correct
remedy; my recomputation supports that ruling rather than qualifying it.

Tier H buys ~5× more (2,163 / 1,588 updates), which is a genuine controlled increase but
still small in absolute terms. So ruling A3 step 5's wording is the maximum claim an H
failure can carry: *"not learned by these baselines under either registered budget"* —
not "the toy is intrinsically too hard", and not any convergence statement. My gate
calculator emits exactly that sentence and no stronger one.

### 5.7 The worst-case L+H timing preflight · **MISSING — must fix before the freeze**

Counted work for the complete fallback schedule (12 worlds × 3 seeds × both arms):

* tier L: 1.99e9 ops per world×seed for both arms → **7.16e10** for the wave
* tier H: 9.99e9 per world×seed → **3.60e11** for the wave
* combined worst case: **4.31e11** counted operations; H alone is 5.0× L.

Ruling A3 requires this projection **in seconds**, from a synthetic-timing fixture at the
real vectorised shapes, including all scoring and file writes, with the registered 1.5×
margin and the 300-second reserve, inside the 1,200-second soft stop — *before* launching
tier L, with `resource-infeasible` reported if it does not fit.

That projection does not exist. And it cannot be obtained by scaling: the ~80 seconds
reported for tier L is not a measurement of the combined schedule, and for models this
small the elapsed time is dominated by per-kernel launch overhead rather than arithmetic,
so the 5.0× op ratio is a lower bound on the time ratio, not an estimate of it. **This is
a blocking must-fix.**

---

## 6. Item 5 — `audit/gate_calculator.py` · PASS

A pure calculator: no builder imports, no file reads, no network, no global state, no RNG.
Written before any result exists. `test_gate_calculator.py` runs **112 hand-built boundary
tests, 112 passing**.

The input schema is documented in the module docstring: a result table of
`{version, tier, integrity, cases[]}`, one case per world × seed × arm carrying
`status`, `E` per budget, `E_initial`, `L_initial`, `L_final`, `E_fit_final`.

### 6.1 Ruling C9, exactly

```text
never_started = (r < 0.10 - 1e-12) AND (E_fit_final >= 0.80)
r = (L_initial - L_final) / L_initial
```

Covered by test: the named float artifact — `(1.0-0.90)/1.0` really does evaluate to
`0.09999999999999998`, which *is* < 0.10, and the calculator correctly does **not** call it
`never_started`. Also tested: `r` exactly on the boundary `0.10 − 1e-12` (not never_started,
strict `<`); just inside at `0.10 − 1e-13` (not never_started); just outside at
`0.10 − 1e-11` (never_started); exactly `0.10`; far below; and negative improvement. The
conjunction is tested from both sides — `E_fit_final = 0.79` with `r = 0.01` is not
never_started, `E_fit_final = 0.80` exactly is. No tolerance leaks onto the other E
thresholds: `E_fit = 0.25` exactly is learned, one ulp above is not; `E_query = 0.50`
exactly transfers, one ulp above does not.

The unchanged initial-floor boundary is tested at exactly `1e-8` (→ `initially_at_floor`)
and one ulp above (→ falls through to the predicate), and `initially_at_floor` is resolved
**before** the evaluator quantities, so it never depends on a pending E. `L_initial = 0.0`
is caught by that branch, so the ratio never divides by zero.

Precedence is tested: `numerical_failure` and `infrastructure_incomplete` outrank
everything; non-finite losses or non-finite E are `invalid_measurement`, never a successful
startup; missing evaluator E is `pending_evaluator_E` (ruling C10 permits that in fit
output, and the two-tier driver refuses it in a completed report); missing **losses** are
invalid, not pending.

### 6.2 The calibration gate, in the registered order

Integrity → control prerequisite → too easy → too hard → advance window → inconclusive.
Every threshold is tested on, just inside, and just outside its boundary: control
`E_512 ≤ 0.10` at exactly 0.10 and one ulp above; exactly 5/6 and 4/6 control cases
passing; median `E_32 ≤ 0.05`; exactly 10/12 and 9/12 cases at `E_32 ≤ 0.10`; exactly 9/12
and 8/12 learned C cases; better-arm median `E_32` at exactly 0.15 and one ulp below;
median `E_512` at exactly 0.50; and the learned rule's 25% clause at exactly
`0.75 × E_initial` and one ulp above.

Also tested: train worlds are excluded from the gate (a train world at E = 0 does not drag
the median); "better arm" is the **lower** median at B=32, so a good arm cannot be rescued
by a bad one; a failed seed, an `infrastructure_incomplete` seed, a dropped cell, a missing
arm, a NaN E cell and a duplicated cell each produce the right invalid verdict; a timeout
and invalid accounting are separate stops; and **a numerical failure outranks the too-easy
rule**, so a broken run cannot be laundered into "stop, too easy".

### 6.3 The two-tier procedure

`evaluate_two_tier(table_L, table_H=None)` implements ruling A3 steps 2–6 and is tested for:

* advance at L → adopt L, H **not permitted**; supplying an H table anyway is flagged
  `protocol-violation`.
* too-easy at L → stop, H not permitted; supplying H is a protocol violation.
* numerical failure / missing result / invalid accounting / failed integrity → stop
  **without** escalation, even when the scores would otherwise read "too hard".
* too-hard, inconclusive, or a **complete and finite** control-competence failure → escalate
  **exactly once**. With no H table yet the status is `awaiting-tier-H` and **no verdict is
  final** — the explanation says in terms that a tier-L failure is never evidence of
  intrinsic task difficulty.
* L too-hard → H advance ⇒ adopt H and report *budget-limited learning at L*.
* L and H both too-hard ⇒ *not learned under either registered budget*; no tier adopted.
* control failure surviving H ⇒ calibration-invalid, not a difficulty result.
* inconclusive at both tiers ⇒ inconclusive.
* H never escalates again — there is no third tier.
* a `ct20-v1` table is rejected outright by the `ct20-v1.1` calculator.

### 6.4 The 5% rule and the median convention

`cross_arm_rule_per_rung` is tested per rung, not on the total: one bad rung fails the
whole ledger and only that rung is marked; a gap of exactly 0.05 passes; exceeding the
per-rung allowance invalidates the accounting; a missing rung, a zero denominator and a
NaN in the ledger all fail rather than silently passing. `median` is tested for the even
and odd conventions and raises on an empty sample rather than inventing a value.

---

## 7. Item 6 — Ambiguities the builders did not flag

The builders' own list is 14 constants in `SCHEMA.md` §7 and the code's ruling table; Astra
resolved all of them. These are additional, and the first three change gate outcomes.

**A1 (gate-affecting). Which panels enter the E the gate thresholds are applied to.**
Prereg §4 says "For each world/seed/B, average ordinary and composition E equally", which
reads as panels 1 and 2. But panel 4 also contains ordinary and composition units, and
ruling B6 fixes `V` on "panels 1/2" without saying the same about `E`. Every §5 threshold
(`E_32 ≤ 0.05`, `E_512 ≤ 0.50`, `E_512 ≤ 0.10`, median `E_32 ≥ 0.15`) is applied to a
quantity whose panel membership is not pinned down. Panel-4 units are harder (they include
the held-out composition and the edited branches), so including them would raise E
materially and could flip a too-easy or advance verdict. **Needs a ruling before the
freeze.** My calculator takes E as given and does not compute it, so it is unaffected —
but the number fed into it is currently underdetermined.

**A2 (gate-affecting). The median convention for an even number of cases.** "Median C
E_32" is taken over 12 cases. Lower, upper and interpolated medians differ, and every
threshold is an exact comparison with no tolerance (ruling C9 restricts the one tolerance
to the improvement ratio). My calculator uses the mean of the two central order statistics
and says so in the docstring; that choice must be registered rather than inherited from
whichever library the scorer happens to call.

**A3 (gate-affecting). Rule precedence when the control prerequisite and the too-easy rule
both fire.** Under ct20-v1.1 this is no longer cosmetic: prereg §5's order puts the
prerequisite first, giving `calibration-invalid/startup-or-implementation`, which ruling A3
says **escalates to H**; but ruling A3 also says "a too-easy result stops". So the same
result table either stops v1 or spends the single H tier, depending on the order. My
calculator implements prerequisite-first (the prereg's own order) and documents it.
**Needs a ruling.**

**A4. The 5% cross-arm denominator.** "Within 5% across arms at each rung" does not say
relative to max, min or mean. The builder and I independently chose `(max−min)/max`. At the
observed gaps (≤1.41%) no denominator changes the outcome, so this is a *register it*
item, not a blocker.

**A5. Tie-breaking for "the better arm".** "Better means lower median at that budget" is
undefined when the two medians are exactly equal. Harmless in effect — with equal medians
the condition evaluates identically either way — but it should be stated.

**A6. The advance window mixes arms.** §5 item 5 requires "the better arm's median C E_32
is at least 0.15, **and at least one arm** has median C E_512 ≤ 0.50". The second clause
says *any* arm, so the window can be satisfied by arm G's B=32 behaviour together with arm
T's B=512 behaviour, with neither arm satisfying both. Whether that cross-arm combination
is intended is not stated.

**A7. Scope of "and no numerical failures" in §5 item 1.** Is it the arm's six control
cases, that arm's cases, or the whole wave? I treat any numerical failure anywhere in the
gate split as invalidating, which is the strictest reading and the one ruling A3 seems to
assume ("a numerical failure … stops without escalation").

**A8. `E_initial` on control worlds.** The learned-case rule requires E_512 to be "at
least 25% lower than that arm's untrained initial checkpoint". On N worlds the noise-free
response is identically zero and `V` floors at 0.05, so an untrained model's initial query
E can already be near zero, making a 25% relative drop nearly unsatisfiable. Wave 1 applies
the learned rule to C cases only, so there is no impact now — but prereg §6 reuses "the
calibration definition" of *learned* for P and T-pool, and wave 3 applies `never_started`
across families. Worth pinning before wave 2.

**A9. Which quantity `E_initial` is measured on.** §5 item 3 says "25% lower query E than
that arm's untrained initial checkpoint on the same world/seed" without naming the budget.
The surrounding clause is about `E_512`, so E_512-vs-initial is the natural reading and the
one I implement; it is worth one sentence because the initial checkpoint is measured once,
before rung 1, and is therefore shared across all five budgets.

---

## 8. Must fix before the wave-1 freeze, versus note only

### Must fix (blocking)

1. **Freeze and re-verify the hashes.** Four of the five inputs Astra reviewed have
   changed, and the models module changed twice during this audit. Every verdict above is
   tied to the hashes in §0 and must be re-run against the final bytes. Ruling C11 requires
   the schema and adapter hashes to be frozen together.
2. **Produce the worst-case L+H timing preflight in seconds** (§5.7), from a synthetic
   fixture at the real vectorised shapes, including scoring and writes, with the 1.5×
   margin and 300-second reserve inside 1,200 seconds. Report `resource-infeasible` if it
   does not fit. Ruling A3 requires this *before* launching tier L.
3. **Rule on ambiguity A1** — which panels enter the gate's E. The §5 thresholds are
   currently applied to an underdetermined quantity.
4. **Register ambiguity A2** — the even-count median convention.
5. **Rule on ambiguity A3** — precedence between the control prerequisite and the too-easy
   rule, because it decides whether the single H tier is spent.
6. **Disclose the L6 pair-membership leak** in SCHEMA.md §4, and register the constraint
   that no arm may condition on more than one query unit at a time (§3.2). Without this,
   the wave-3 irrelevant-pair guard measures pair detection rather than invariance.
7. **Freeze both step tables at the reconciled totals** — L: G 370 / T 254; H: G 2,163 /
   T 1,588 — and retire the provisional 378/262 figures from every document.
8. **State the normative padding convention** (§4.1) so the two producers' tensors have a
   single contract.

### Note only

9. The public/private boundary is procedural, not cryptographic, and the same procedure
   reproduces the 24 final worlds (§3.1). Recommend an explicit manifest statement, and a
   secret salt for the final split if wave 3 is to carry weight.
10. N is separable from the public tensors by a one-line statistic (§3.3). Report wording.
11. `outer_split` reaches model code only by discipline (§3.5). A loader-side refusal would
    make ruling B8 mechanical.
12. Record the new public `audit_*` tensors and the two audit-set sizes (144/143) in the
    schema, and report the one-row unused reservation separately per ruling A1 (§2).
13. Delete the RESET-destination comment that contradicts its own code (§4.2).
14. Register ambiguities A4–A9 (§7); none of them changes a pilot outcome at the observed
    numbers, but A8 should be settled before wave 2.
15. Say "equal counted operations under the registered estimate", never "equal compute" —
    the G/T ratio itself moves with the convention (§5.4).

---

## 9. Verdict

The generator is correct and independently reproducible, ruling B1 is correctly and
minimally applied, the model-side invariants that matter — causality, blank rollout, lane
isolation, exact resume, trainer/evaluator separation — hold exactly rather than
approximately, the ruling A1 ledger reconciliation is complete and its arithmetic
reproduces under independent recomputation, and the numerical gate calculator exists with
112 passing boundary tests written before any result.

What is not yet in place is a frozen set of hashes, the L+H timing preflight that ruling A3
requires before tier L may launch, three gate-affecting rulings, and one disclosure.

**FREEZE-READY: NO**

I will re-run every check in this document against the final frozen bytes, and will then
additionally verify — as ruling C11 requires and as byte agreement on the fixture alone
cannot establish — the production adapter path end to end: the real fit/predict entry
points, the query index and padding, the nested support prefixes, and observation blanking
on the forecast paths. On that evidence I will issue the final
`FREEZE-READY: YES/NO` for `ct20-v1.1`.

---

# Re-check 1 — `ct20-v1.1` final bytes (2026-09-20)

Everything below was re-run by me against the announced final builds. Nothing in this
section is carried over from the first pass; where a number is unchanged, it is unchanged
because I re-computed it and got the same answer.

## R1.1 Hash verification — no mismatch

All eight announced hashes reproduce exactly on disk.

| artifact | sha256 (verified) |
| --- | --- |
| `scripts/fable_concepttoy20_sim.py` | `9ae4921ddae792943c63a1ee7003dc30598670f44e32f04fad57947c99530a4f` |
| `scripts/fable_concepttoy20_public.py` | `7139c6989f8618dcca9d4ef2e31b5c667424e3fca8a183e8f30b36a1e3b567fe` |
| `scripts/fable_concepttoy20_models.py` | `3632e2ecd292ce2aa84e3b28cc6e233c16034b28e6f42605c8fef5b0fc6a641c` |
| `tests/test_fable_concepttoy20_sim.py` | `af9e1b2356da4b9919e030774dfcb7269f2affbcb578cbee5658ac911920dff9` |
| `tests/test_fable_concepttoy20_models.py` | `aaae8702ac8280e9be20bafb491be28a5533b6cc3abc2abe831de83a0ea60e49` |
| `SCHEMA.md` | `c3a2a01e3c551ab125d5c3bf9e6e34cf7a486d6f38fb91c1ff04e443db11fa9e` |
| `calibration-v1.1/manifest.json` | `5cb70340068b2a17a92f33edfa0505e4b6eef8d753faaea9e828ef879a28de36` |
| `fixture-v1.1/manifest.json` | `ead13b5c931b90b05e09a3a537d50958358ff6a8a11190cbbc7e74c488e6114a` |

**No sha mismatch to report.** The rulings file is unchanged at
`40f650451b6b1404e352c900fabb9a6f56fa1696aaac31e90fdc4cac2779c6de`, and both the models
module and the timing preflight stamp that value into their own output.

## R1.2 Re-run of every first-pass check — PASS

| suite | file | result |
| --- | --- | --- |
| independent generator oracle | `check_generator.py` | **21/21 PASS**, 0/288 contaminated ordinary strings |
| v1.1 public audit set | `check_v11_audit_set.py` | **5/5 PASS** |
| model-side invariants | `check_models.py` | **25/25 PASS** |
| cost ledger | `check_accounting.py` | **14/14 PASS**, 6 notes |
| gate-calculator boundary tests | `test_gate_calculator.py` | **112/112 PASS** |
| data-boundary / leak review | `check_leaks.py` | 11 entries, findings unchanged |

Two corrections to my own instruments, both the same bug class, both mine and not the
builders':

* `check_models.py` reported one new FAIL ("references no evaluator-side file or field
  name `['private/']`"). It was a false positive: a raw-text grep was matching the word
  inside a module docstring that *asserts* the loader reads no `private/` path, and a
  second use of "private" meaning module-internal. I replaced the raw-text scan with an
  AST walk that excludes docstring constants. I had already fixed this exact class of
  error once, for the import check. **A raw-text grep over source is not evidence**, and I
  am recording that here rather than quietly repairing it.

## R1.3 Ruling A3 — the timing preflight. My judgement: SATISFIED

I ran `timing-fixture --lanes 36 --seconds 6 --project-wave1` myself, twice, under a load
average of 5.49 with three long training jobs already running — which makes the
measurement conservative rather than optimistic.

| quantity | G | T |
| --- | ---: | ---: |
| measured throughput at 36 lanes | 28.01–28.43 upd/s | 26.87–27.24 upd/s |
| peak memory | 397.75 MB | 480.74 MB |

Projection: **L 43.52 s + H 157.16 s = 200.68 s raw**, **301.02 s with the registered 1.5×
margin**, against **900 s usable** (1,200 s soft stop − 300 s reserve). Verdict `fits`,
`fits_within_wave: true`, headroom **3.0×** beyond the margin. My independent figures agree
with the builder's reported 201–217 s raw / 302–326 s with margin.

Against ruling A3 point by point: the fixture runs the **real vectorised shapes** (36
lanes, 17 tokens, 44 channels, both arms), it exercises **scoring** (itemised
`audit_pass_seconds` and `query_panel_seconds`) and **file writes**
(`checkpoint_write_seconds_per_lane`), it applies the **1.5× margin** explicitly, it
honours the **300 s reserve** by projecting against 900 s and not 1,200 s, and it stamps
both `source_sha256` and `rulings_sha256` so the measurement cannot be silently detached
from the code it measured. That is the whole of what A3 asks for.

Two caveats to record, neither blocking:

* The preflight's own ~16 s elapsed time is itself chargeable to the wave under prereg §9.
* Prereg §9 requires the preflight to be **re-run immediately before the registered fits,
  on the actual machine state**. Today's number licenses the freeze; it does not license a
  launch onto a differently-loaded machine.

## R1.4 SCHEMA.md verification

* **§4.0** discloses the L6 pair-membership leak accurately: both mechanisms (panel-3
  pairs sharing an identical 24-float property block; panel-4 pairs recoverable by
  multiset-matching channels 0–1), the registered constraint that **no arm may condition on
  more than one query unit at a time**, and the wave-3 exposure. Marked pending Astra
  ratification, which is the right status.
* **§2.3.1** makes all-zero padding normative and correctly limits byte-equality to rows
  `0 … n_records − 1`, explicitly permitting a different *internal* convention. This
  matches what `build_sequences` actually does and what the frozen `.npy` files contain;
  I verified both sides (R1.5 C2/C4).
* **§8.1** carries only the reconciled ledger — L 370/254, H 2,163/1,588 — and states that
  the provisional 378/262 figures are superseded and must not be quoted.
* **§2.3** note 12 documents the 144/143 audit-set sizes, names the short world
  (`db0d29339a47b284`), explains that `A` is a pure function of the already-public
  `support_observed_present` and so is not a leak, and binds the one-row shortfall as an
  **unused reservation** that must be reported and must not be spent.
* **Note 13 is fixed**: `SLICE_DESTINATION` is now commented `one-hot j=0..3 or NONE=4`,
  no longer claiming all-zero at RESET, which matches the encoding `build_sequences`
  writes and ruling B4.

**One new documentation defect (non-blocking).** SCHEMA §3.1 still contains the paragraph
"Audit-key reconciliation with the models builder", asserting that the models builder
writes `e{episode_index}/h{horizon}/t{endpoint}` and that "the two spellings **do not
match**". That is no longer true of the frozen build: `fable_concepttoy20_models.py` now
sets `AUDIT_KEY_FORMAT` to the canonical spelling and delegates to
`PublicDataset.audit_key`, and I verified 36/36 key equality against the frozen
`audit_keys.json` (R1.5 A4c). The frozen contract therefore **misdescribes the frozen
code**. The evaluator's legacy-spelling tolerance is harmless — it requires
`world_public_id` and refuses to guess without it — so this is a stale-prose defect, not a
correctness defect. It should be corrected in the next documentation-only pass; it does
not block the freeze.

## R1.5 Ruling C11 — production-path check. 42/42 PASS

`check_production_path.py`, results in `production_path_results.json`. Learner-touching
work ran on `fixture-v1.1` only (families `o` and `c`; **no M-family world was touched**).
The calibration worlds were read for index and role structure alone — no parameters, no
forward pass, no scoring. **No prediction value is published.**

**A. Loader (4 checks).** `load_world_support` with its default
`allow_semantic_fixture=False` reads the serialized layout; the C11 guard genuinely raises
on a directory without `support_records.npy`; an AST walk of `run_fit`, `run_predict`,
`run_predict_agent1` and `main` finds **no call site** that enables the semantic adapter,
positionally or by keyword; the public loader imports and all **36/36** frozen audit keys
reproduce through `models.audit_key`.

**B. Nested support prefixes (7 checks).** On the fixture, rungs 32/64 give contiguous
prefixes of 4 and 8 episodes, nested, with selection at index 3 of every group of four. On
**all 12 calibration worlds**, all five rungs give sizes 4/8/16/32/64, **every rung nests
in the next**, and the 3:1 split sits at index 3 mod 4 inside every rung. The
discovery-validation partition is therefore genuinely inside the budget and is not free.

**C. Query index and padding (7 checks).** `query_index` and `audit_index` equal
`n_records − 1` everywhere; across **228 serialized rows** every row at index ≥ `n_records`
is all-zero, confirming §2.3.1 as written; every endpoint row is a QUERY with `sensor = 0`
and `sensor_present = 0`; the loader pads to 17 rows with zeros and its endpoint tensor
equals the published index; 96 unique record ids. Then the operational form: **poisoning
every padded row with 7.5 leaves the predictions bit-identical** for both arms, and all 96
predictions are finite. Padding cannot reach a prediction — demonstrated, not assumed.

**D. Observation blanking on the forecast paths (10 checks) — the decisive group.**
Across **20 distinct (prefix, horizon) shapes**: every forecast OBSERVED token carries
`sensor = 0` and `present = 0`; every prefix OBSERVED token carries the real masked
measurement; the endpoint is the final QUERY at `1 + 2·(prefix + horizon − 1)`; the target
OBSERVED record is never constructed.

Structure alone is not proof, so I also perturbed the sensor stream and watched the real
forward pass, for both arms, at prefix 3 / horizon 4:

* adding 13.0 to the sensor and forcing `present = 1` across the **entire forecast region**
  → predictions **bit-identical**;
* the same perturbation on the **target transition itself** → predictions **bit-identical**;
* the same perturbation on the **observed prefix** → predictions **do change**.

That is the check byte agreement on the full-history fixture could not give: no future or
target observation can influence a forecast, and the path that should carry information
demonstrably does.

**E. Real predict entry point (9 checks).** `run_predict_agent1` ran end to end for both
arms on the fixture: one finite value per frozen record id, all 96 ids matched exactly,
deterministic across two runs, and the written file carries only
`{contract_version, arm, checkpoint, predictions}` — no private field.

## R1.6 Gate calculator against the real evaluator output. 11/11 PASS

`check_gate_end_to_end.py`, results in `gate_end_to_end_results.json`. The chain run was:
real initial parameters → real `forward` → the **real** `evaluate_predictions` from
`fable_concepttoy20_sim.py` → a mechanical adapter → `gate_calculator.evaluate_two_tier`.
912 prediction rows, **0 unknown record ids**, 4 start-up diagnostic rows.

Two things I explicitly do **not** claim. This is a **format** check: both "stages" are
untrained parameter draws (seeds 0 and 1) — nothing was fitted, and the E and L numbers
are meaningless as accuracy and are not published. And the fixture's `outer_split` is
`fixture`, which the gate arithmetic does not read, so the adapter relabels it
`validation` purely so the gate path executes; that relabelling applies to no registered
run.

What is established:

* Every field my CASE schema requires exists in the evaluator's output under a **named**
  field (`startup_diagnostics[].L_initial`, `.L_final`, `.E_fit_final`, `.outer_split`,
  `.family`; `groups[].worlds[].E_primary` per rung and stage). The adapter is **total** —
  nothing defaulted, inferred or invented — and reported **no gaps**.
* `evaluate_tier` and `evaluate_two_tier` both accept the evaluator-derived table and
  return well-formed output. On this deliberately incomplete fixture table the verdict is
  `calibration-invalid/missing-required-result` with `escalates_to_H: False`, naming the
  absent cells. That is the correct refusal: an incomplete table must not produce a
  scientific verdict, and an invalid one must not buy a tier-H escalation.
* **Two independent implementations of the ruling-C9 predicate agree.** The builder's
  `startup_classification` and my `classify_startup` produce the **same label on every
  case**, the relative-improvement ratio `(L_initial − L_final)/L_initial` matches **bit
  for bit**, and the three constants are identical on both sides (`0.1`, `1e-12`, `0.8`).
  Neither implementation chose these numbers; they came out of the real evaluator.

## R1.7 Standing findings, carried forward unchanged

* **The public/private boundary is procedural, not cryptographic.** There is no secret
  seed or salt. I regenerated every "private" quantity — families, coefficients, `V`,
  latents, noise-free responses, panel identity, hash ordering — from the design document
  alone. The same procedure applies verbatim to the 24 FINAL worlds that wave 3 depends
  on. This is not a defect in the build; it is a property of the design, and it should be
  stated in the writeup rather than discovered later.
* **A "too hard" verdict at tier L is confounded by the budget.** 370/254 updates is
  1,480/1,016 examples for an entire five-rung fit, two to three orders of magnitude below
  what a small sequence model normally needs. Ruling A3's mandated H tier is the right
  remedy, and no "too hard" reading may be published from tier L alone.
* **The convention sensitivity of the ledger is not a scale factor.** Across my three
  conventions L/G ∈ {370, 773, 577} and L/T ∈ {254, 618, 394}, and the G/T ratio itself
  moves (1.46 / 1.25 / 1.46). Any cross-arm claim must name the convention. The cross-arm
  5% rule passes at every rung under the registered convention (L worst 1.41% at B=128,
  H worst 0.06%).

## R1.8 Verdict

Every must-fix item I raised against the build itself has been addressed and independently
re-verified against the final bytes: the generator reproduces from spec, B1 contamination
is 0/288, the model-side invariants hold, the ledger reconciles, the A3 timing preflight
exists and passes on my own measurement, the disclosures are in the frozen schema, and the
two checks I promised but had not yet run — the C11 production path and the gate-calculator
join — now pass at 42/42 and 11/11.

What remains is **not code**. It is the five rulings with the coordinator's recommended
defaults (my calculator's choices: prerequisite-first ordering, mean-of-central median,
`(max − min)/max` for the cross-arm gap), plus Astra's ratification of the §4.0 leak
disclosure. Those are decisions, not repairs, and my gate calculator is written to be
re-parameterised without touching the data if any ruling lands differently. One stale
paragraph in SCHEMA §3.1 (R1.4) should be corrected in a documentation-only pass and does
not block.

I record one residual risk for the coordinator rather than burying it: the timing
projection was measured today, under today's load, and prereg §9 requires it to be re-run
on the actual machine state immediately before the registered fits. A freeze is not a
launch clearance.

**FREEZE-READY: YES conditional on Astra rulings R1–R5**

---

# Re-check 2 — rulings 2 conformance (2026-09-20)

Scope: `audit/` only. The two builders' concurrent work on SCHEMA.md,
`fable_concepttoy20_wave1.py` and the R4 isolation tests is **deliberately not audited
here**; that closes with the final hashes.

## R2.1 SHA MISMATCH on the rulings-2 file — reported, unresolved

The coordinator announced `design/v3/20-concept-toy-rulings-2.md` as sha256
`8a62ef050e2120209761e858109aa9195b87c88790fb7827dd5b547a56defc8d`. The bytes on disk
hash to:

```
1245e46f567dd1a265d6b05d8482f0267052c735159b8d05864dd6b861a110f2   8,687 bytes
```

Confirmed with two independent tools (`shasum -a 256` and `openssl dgst -sha256`). My
standing instruction is to report any sha mismatch, so I am reporting it rather than
assuming which value is stale.

I have pinned the calculator to **the bytes I actually read**: `RULINGS_2_SHA256` in
`gate_calculator.py` carries `1245e46f…`, `RULINGS_2_SHA256_ANNOUNCED` carries the
announced value, and `RULINGS_2_SHA_MISMATCH` is `True`. Two tests assert both facts, so
the discrepancy cannot be lost. **The coordinator must resolve which byte sequence is the
registered ruling before the freeze**; if the announced hash corresponds to a different
text, every conformance statement below must be re-checked against it.

A related, lesser point: the coordinator's message numbers the cross-arm cost gap as R5
and the query-isolation requirement as R4. In the file as written, **R4 is the cross-arm
cost gap** and **R5 is arm ties and the advance window**; the isolation requirement is in
the unnumbered "Public-interface ratification" section. I have used the file's own
numbering throughout. The substance is not in doubt, but the labels should be aligned
before they appear in a frozen document.

## R2.2 Conformance, point by point

`gate_calculator.py` → sha256 `315c841f20c929fa65bc7f530a7b23c3d187743527ae64ffb764cac68c381908`
`test_gate_calculator.py` → sha256 `85e0ebda6ce264f04f46a9728c1a9038d2bdc33dea7b9938450f4d09a18e9dab`
**172 tests, 172 passing** (was 112; 60 added for rulings 2).

| ruling | status before | change made |
| --- | --- | --- |
| **R1** learned-case `E_512 ≤ 0.50` **and** `≤ 0.75·E_initial`, exact, no floor | **already conformed** | docstring now quotes R1; 12 boundary tests added |
| **R1** controls judged on absolute marks only | **already conformed** | test added proving the two rules are separate |
| **R2** median = mean of two central order statistics | **already conformed** | docstring cites R2; 6 tests added |
| **R2** non-finite must invalidate, not shorten the denominator | **already conformed** | test added |
| **R3** precedence order | **already conformed** | — |
| **R3** "print both predicates and identify which takes precedence" | **did not conform** | prereq failures now print `too_easy=` and `too_hard=` and name the precedence |
| **R3** at H, competence failure ends the version, no third tier | **already conformed** | explanation strengthened; tests added |
| **R3 / A7** complete-wave requirement over train **and** validation | **did not conform** | new `complete_wave_check()`; see below |
| **R4** `(max−min)/max ≤ 0.05`, inclusive, per rung | **already conformed** | docstring cites R4; 7 tests added |
| **R5** exact tie names G as display ID | **already conformed** | tie is now *reported* as a tie in its own right |
| **R5** window reads `min` across arms; arms may differ across budgets | **already conformed** | explicit `min_median_E32` / `min_median_E512` / `arms_differ_across_budgets` fields |

**The one substantive gap was R3/A7.** The calculator previously validated only
`outer_split == "validation"` rows, so a numerical failure or missing fit in a *train*
world was invisible and a too-hard tier-L verdict would still have bought the tier-H
budget treatment. R3 forbids exactly that. `complete_wave_check()` now does both halves
the ruling allows: it scans every non-validation case for a failed or incomplete job
(**never reading train-world accuracy**, so the difficulty window is untouched as R3
requires), and it requires an explicit `integrity.complete_wave_valid` attestation.

Absence is **not** treated as truth. An unsupplied attestation leaves the outer
requirement unverified, escalation is blocked, and `evaluate_two_tier` returns the new
status `blocked-incomplete-wave` with `final_verdict: None` — no pass, and explicitly no
difficulty statement. This is the conservative reading, and it is the one R3's closing
sentence asks for: "the coordinator's complete-wave checks must enforce the outer
requirement explicitly and be included in the frozen audit."

**Coordinator action required:** every submitted result table must now carry
`integrity.complete_wave_valid`. A table without it will not certify an escalation.

## R2.3 A binary64 boundary worth keeping

My first draft of the R1 boundary test asserted that `E_512` one ulp above `0.30` fails
against `E_initial = 0.40`. It does not: `0.40 × 0.75` is `0.30000000000000004`, not
`0.30`, so the decimal literal a reader expects sits *below* the real threshold. The
calculator was right and my test was wrong. The test now builds the boundary from the
product exactly as R1 writes it, and a dedicated test pins the artifact. Anyone
re-deriving these thresholds from decimal literals will get a different answer at the
last bit.

## R2.4 Status

The operative verdict is still the one at the end of Re-check 1 — **YES conditional on
Astra rulings R1–R5** — with the conditions now discharged on the calculator side and the
sha mismatch of R2.1 added as an open item. The single final operative `FREEZE-READY`
line will be written after the builders' final hashes land and I have verified R1 on the
evaluator by hand, verified R4 query isolation myself on fixtures, run the new driver's
`--fixture` mode end to end, and confirmed the gate wiring implements rulings 2.

---

# Closure — `ct20-v1.1` final bytes, conditional verdict discharged (2026-09-20)

This section closes the conditional verdict. Everything below is a check I ran myself
against the final bytes, on the published fixture or on synthetic data of my own. **No
learner was fitted, scored or evaluated on the registered calibration worlds at any
point in this audit**, and no M-family trace or score appears anywhere in it.

## C.1 The rulings-2 sha mismatch is RESOLVED — my own comparison agrees

R2.1 reported a mismatch between the announced rulings-2 hash
(`8a62ef05…`) and the file on disk (`1245e46f…`). The coordinator's explanation is that
two separate Astra chats wrote the same path two minutes apart and the second overwrote
the first. **I checked the comparison myself rather than accepting it.** I read both
documents in full: the on-disk governing file (8,687 bytes, 55 lines) and the preserved
first version at `artifacts/fable-concept-toy20-20260920/RULINGS-2-first-version-as-relayed.md`
(`fac03f78…`, verified by me against the bytes on disk).

**I find no conflict on any operative point.** Both agree on the E definition, the
mean-of-central-two median, the prerequisite-first precedence, the `(max−min)/max ≤ 0.05`
inclusive per-rung gap, the A5 tie rule, the A6 advance window, the A7 complete-wave
requirement, the isolation rule, the padding ratification, the step totals and the
authorization. The two differ only in what each spells out:

| Spelled out only in the FIRST version | Spelled out only in the ON-DISK version |
| --- | --- |
| the three cost constants (`OPS_INIT_PER_PARAMETER=2`, `OPS_LOSS_PER_TARGET=4`, `OPS_LOSS_PER_BATCH=2`) | the complete-wave requirement covering **train and validation** jobs |
| per-rung query scoring (charged at every rung; only B=32/512 + initial feed the predicates) | |
| the per-rung step table (L/G 62·81·81·80·66=370; L/T 39·58·57·57·43=254; H/G 421·440·439·438·425=2,163; H/T 306·325·324·323·310=1,588) | |
| the launch preflight instruction | |
| the secret-salt recommendation for wave 3 | |

I verified each step row sums to its stated total. The freeze should bind **both**
documents, as the preserved file's provenance header states: where one is silent the
other governs. Treating only the on-disk file as binding would silently drop the three
cost constants and the step table, which the ledger and the driver both depend on.

**Two corrections to my own earlier work fall out of this.**

1. My R2.1 "numbering confusion" flag is **withdrawn**. The coordinator's R4 = isolation
   and R5 = ledger numbering is exactly the first version's numbering. There was never a
   numbering error; I was comparing against the only version I could then see.
2. My claim that dividing by `max` is "the more conservative denominator" was **wrong**,
   and the first version corrects it explicitly. For `a < b`, `(b−a)/a > (b−a)/b`, so
   dividing by max yields a *smaller* gap and is the *permissive* choice. The docstring
   in `gate_calculator.py` no longer makes the claim. The rule itself is unchanged and is
   the registered convention either way.

`RULINGS_2_SHA_MISMATCH` has been replaced in the calculator by a provenance block
recording the governing hash, the unreproducible announced hash as a named historical
value, and the first version's path and hash. Three tests pin this, including one
asserting the old flag no longer exists.

## C.2 Ruling R1 on the evaluator, by my own hand computation — 18/18 PASS

`audit/check_r1_evaluator.py` recomputes R1 from the frozen private truth with plain
arithmetic and compares against `evaluate_predictions`. The "predictions" are a fixed
deterministic function of the record id, so nothing here measures any learner.

- `V` matches exactly for both fixture worlds: population variance over panels 1+2 with
  the 0.05 floor.
- `E_panel1` matches the **horizon-weighted** mean of the h=1/2/4 means, and I confirmed
  that this is genuinely different from the flat 6/5/5 mean R1 forbids:
  `1.6456482504009966` (horizon-weighted) vs `1.6649476788499569` (flat). The evaluator
  implements the one R1 requires.
- `E_panel2` matches the equal average of its 16 units; `E_primary = (E_panel1+E_panel2)/2`
  matches; `E_primary ≠ E_all_targets`, so panels 3/4 are excluded structurally.
- **Operationally**, adding +50 to *every* panel-3 and panel-4 prediction leaves
  `E_primary` bit-identical while visibly moving the panel-3 guard. The guards are real
  and they are outside primary E.

**Null `E_primary` on truncated predictions.** Dropping a subset of targets makes the
evaluator report `complete: False`, `E_primary: None` and the partial count — it does not
silently return a partial number. My calculator then treats that null as a *missing
required result*, never as `0.0`: `is_learned_case` returns `False` with a reason
containing "missing", and the table-level path yields
`calibration-invalid/missing-required-result`. This is the correct direction: a truncated
run cannot masquerade as a low error. **PASS.**

## C.3 Ruling R4 query isolation, verified by me — 15/15 PASS

`audit/check_isolation.py` is an **independent witness**: it drives the real forward pass
directly and does *not* call the builder's `isolation_guard`. It locates a real panel-3
pair in the fixture private truth and perturbs the target's context in six ways.

| perturbation | arm G | arm T |
| --- | --- | --- |
| replace all 15 companions | `0.0` | `0.0` |
| reverse batch order | `0.0` | `0.0` |
| remove the paired counterpart | `0.0` | `0.0` |
| different partition, **same** batch size | `0.0` | `0.0` |
| **corrupt a companion's content (+5.0)** | `0.0` | `0.0` |
| batch size 1 vs 96 | `5.96e-08` | `1.49e-08` |
| batch shape, worst over sampled rows | `1.19e-07` | `1.79e-07` |

### Ruling on the ≤3.6e-7 batch-shape residual: **ACCEPT**

The coordinator asked me to rule on whether a residual under a *changed* batch shape
satisfies "unchanged under the frozen numerical convention". It does, for three reasons,
in increasing order of force.

1. **Magnitude.** 1.19e-07 to 1.79e-07 is 1–3 ulp of float32 (`eps = 1.19e-7`). This is
   the signature of GEMM tile-size selection, not of information flow.
2. **The decisive negative control.** Corrupting a companion's *content* — not merely its
   identity or position — moves the target by **exactly 0.0**. If any information were
   crossing between sequences, poisoning a neighbour by +5.0 across all 44 channels would
   move the target by vastly more than 1e-7. It moves it by nothing at all. Every
   information-bearing perturbation is exactly zero; only the arithmetic *grouping* moves
   anything.
3. **The residual is never incurred.** This is the point that settles it. I verified
   below (C.4) that the driver's registered runs are bit-reproducible end to end, so the
   changed-shape case does not arise in a registered wave. The bound is a safety margin
   on a path the experiment does not take.

I therefore rule that the isolation requirement is satisfied and that the builder's
`isolation_guard` — which raises `RuntimeError` and refuses to launch on failure, with
`ISOLATION_EXACT = 0.0` for the information-bearing perturbations and
`BATCH_SHAPE_TOLERANCE = 1e-6` reserved for shape alone — draws the boundary in the right
place. The strict `0.0` is applied exactly where it must be.

## C.4 The driver, `scripts/fable_concepttoy20_wave1.py` — run end to end on the fixture

Run as instructed on **`--fixture` only; never on calibration-v1.1**, at
`--concurrency 3`. Two complete waves plus four resume experiments, all in `audit/`.
Evidence retained at `audit/_fixture-run-A-resume-experiments/` and
`audit/_fixture-run-B-clean/` (checkpoints deleted after hashing; verdicts, reports and
gate tables kept).

**Clean run.** 12.3 s wall, preflight charged 5.8 s, 6 shards, 12 fits, all ok,
accounting valid at worst per-rung gap `0.044376`, complete wave 12/12, startup labels
agreeing, verdict `calibration-invalid/missing-required-result`.

**That verdict is the correct result, and it is informative.** The fixture worlds carry
`outer_split: "fixture"`, so `n_gate_worlds = 0` and `missing_arms: ['G','T']`. The
driver refuses to manufacture a scientific verdict from a non-calibration dataset. At the
same time `complete_wave` reports **12/12 cells present**. That contrast is a direct
operational demonstration of the separation R3 demands: **every fit is checked for
completeness, and none of the non-validation fits reaches a scientific predicate.**

Point by point on what I was asked to confirm:

- **`integrity.complete_wave_valid` is set from all fits per tier, train and validation.**
  `complete_wave_check` iterates `world_ids × seeds × ARMS` — on calibration that is
  12 × 3 × 2 = **72 fits per tier**, and `verdict["n_fits_per_tier"]` is computed the same
  way. On the fixture it required and found 12/12. `run_wave` writes the result into
  `table["integrity"]["complete_wave_valid"]` and additionally forces
  `audit_passed = False` when it fails. My calculator's own
  `complete_wave_check` then *requires* that attestation: absent is not true, and the
  verdict field `escalation_blocked_by_complete_wave` reports it. **PASS.**
- **It never reads train accuracy for the gate.** `complete_wave_check` reads only
  presence, the job's own `status`, and `math.isfinite` on `E_initial`/`E[budget]`. No E
  value is compared to any threshold. Demonstrated operationally above:
  `n_gate_worlds = 0` while 12 cells were checked. **PASS.**
- **Null `E_primary` is treated as missing.** `build_gate_table` records a null
  `E_primary` as a gap, never as a number; C.2 confirms the evaluator emits null and the
  calculator refuses it. **PASS.**
- **H runs only on `awaiting-tier-H`, with a fresh preflight.** The tier loop breaks
  immediately unless `two_tier["status"] == "awaiting-tier-H"`, and `preflight(...)` is
  called at the top of *each* tier iteration with `remaining_tiers = ["H"]`, charging its
  own elapsed time onto the running total. `run_wave` additionally overrides the status to
  `complete` with `H_permitted: False` whenever accounting, the complete wave or any shard
  failed — R3 ahead of every scientific predicate. **PASS on code reading and on my 174
  calculator tests; the H branch itself was not exercised end to end**, because the
  fixture cannot produce `awaiting-tier-H` and fabricating a calibration-shaped table to
  force it would not test the driver's real path. I state this rather than imply
  otherwise.
- **Resume is fit-granularity only.** `resume_shards` rejects a fit unless all five rung
  checkpoints and a predictions file carrying the initial panel, every rung's panel and
  both audit sets are present; an incomplete fit is re-run whole from its initialization
  bytes, never continued from a mid-trajectory checkpoint. **PASS.**
- **Overwrite is refused.** Re-running into a directory holding `verdict.json` without
  `--resume` raises `FileExistsError` with an explicit message. Verified by running it.
  **PASS.**
- **Both rulings-2 shas are stamped**, along with nine others. Verified against the files
  on disk: `rulings_2_sha256 = 1245e46f…`,
  `rulings_2_first_version_relayed_sha256 = fac03f78…`. **PASS.**

### C.4.1 Determinism, tested four ways

- **Cross-run.** A second complete wave in a fresh directory reproduced the first
  **byte for byte across all 72 fit files**.
- **Tamper detection.** Flipping one byte inside a checkpoint caused that fit to be
  refitted on resume rather than trusted, because `lane_is_complete` re-verifies every
  recorded sha. **PASS.**
- **Same-shape refit.** Deleting two fits and resuming at the original lane count
  reproduced all 72 files byte for byte.
- **Changed-shape refit.** Deleting *one* fit re-shards that `(arm, seed)` group from two
  lanes to one. The five checkpoint files then differ — so I compared them field by field:

  | field | lanes=2 vs lanes=1 |
  | --- | --- |
  | `parameters` | max abs delta **0.0** |
  | `moment1` | max abs delta **0.0** |
  | `moment2` | max abs delta **0.0** |
  | `predictions.json` | **identical** |
  | `work` (op counts) | differs — exactly 2× at lanes=2 |
  | `initial_parameter_hashes` | differs — hashes of lane-stacked tensors |

  **The science is lane-count invariant.** Every fitted parameter, every optimizer moment
  and every prediction is bit-identical. Only two shard-scoped bookkeeping blocks move.
  I then confirmed the accounting is unaffected: ledger rows are written **per fit**, and
  `executed_cross_arm_check` keys on `(world_id, seed) → arm → rung` using
  `rung_counted_total_ops`, so the worst per-rung gap came out at
  `0.044375603930256004` — identical before and after the lane change, with
  `accounting_valid: True`.

This is what licenses the third leg of my isolation ruling in C.3: with the registered
path bit-reproducible, the batch-shape residual is never incurred.

## C.5 Two non-blocking defects I found in the driver

Neither can change a scientific verdict. Both are recorded so nobody relies on the
wrong field later.

**C.5.1 The checkpoint's `work` block is shard-scoped, but lives in a per-fit file.**
At two lanes each fit's checkpoint records the *shard's* totals — `initialization_ops`
23,684 rather than 11,842, and so on, exactly double. Likewise
`initial_parameter_hashes` hashes the lane-stacked initial tensors, so it changes with
sharding and cannot serve as a per-fit provenance anchor. Nothing in the gate reads
either field — the accounting reads the per-fit ledger rows, which are correct — so this
is a reporting hazard, not an error. **Recommendation: audit costs from
`tier*/ledgers/*.jsonl`, never from a checkpoint's `work` block, and do not cite
`initial_parameter_hashes` as evidence that a fit began from the registered bytes.**

**C.5.2 The tier-H feasibility test subtracts preflight seconds but not elapsed fitting
time.** `preflight` computes `usable = 1200 − 300 − charged`, where `charged` accumulates
only the synthetic fixtures' own elapsed time. Tier L's actual fitting time is not
subtracted, so the tier-H feasibility test is optimistic by roughly tier L's duration.
`timing_ok` does compare true elapsed against the soft stop and feeds `audit_passed`, so
an actual overrun is caught — as an integrity failure after the fact rather than a
refusal to start. At the registered scale it cannot bind: the projection is 51.7 s for L
and 202.9 s for H, so the honest arithmetic gives `304.4 s` needed against `838.7 s`
available — **534 s of slack**. The optimism would need a ~10× projection error to
matter. **Recommendation (non-blocking): pass the wave's elapsed seconds into
`elapsed_charged` at the tier-H call.**

## C.6 Question 4 — the `learned_failed_to_transfer` spelling. Ruling: **ACCEPTABLE AS IS**

The simulator emits `learned_failed_to_transfer`; the calculator, the models module and
prereg §8 use `learned_and_failed_to_transfer`. The driver maps the one string through
`STARTUP_LABEL_ALIASES`, reports it in the verdict as
`label_aliases_applied` and in the text report as "12 spelling reconciliations", and keeps
**every other** label difference fatal via `startup["agree"] → audit_passed`.

I rule this acceptable, and I do not require the simulator to be corrected before the
freeze, for four reasons:

1. **No gate predicate branches on the string.** I traced it: `evaluate_tier` computes its
   own labels from `classify_startup(L_initial, L_final, E_fit_final, E_512, status)` —
   numbers, under C9's binary64 predicate — and only *reports* them. The
   `calibration-invalid/startup-or-implementation` verdict is a fixed constant, not
   derived from any label text. The simulator's spelling cannot reach a verdict.
2. **The alias is where the cross-check lives, not where the science lives.** Its only
   function is to let the driver's *independent* recomputation of the label be compared
   against the simulator's. Narrowing one known spelling difference does not weaken that
   cross-check, because every other difference remains fatal.
3. **It is named, single-entry and disclosed** in the verdict JSON and the human report.
   It is not a silent normalisation.
4. **Correcting it costs more than it buys.** Changing the simulator source changes
   `simulator_source_sha256`, which is bound in two already-verified manifests, and would
   require re-verifying all 459 data files to show that no data byte moved — a real freeze
   risk incurred for a cosmetic string.

**Condition attached:** the alias must remain exactly one entry with all other differences
fatal (verified in the final bytes), and the reconciliation must stay visible in the
wave-1 report (verified). **Recommendation: correct the simulator in the next versioned
amendment, alongside the SCHEMA §3.1 stale prose, not now.**

## C.7 Question 5 — a fresh preflight before tier H. Ruling: **CONSISTENT, AND REQUIRED**

The rulings-2 first version instructs: *"Repeat the bounded synthetic preflight
immediately before fitting on the actual machine state, charge its elapsed time, retain
the 300 s reserve and 1,200/1,500 s limits, and stop `resource-infeasible` if the
remaining complete schedule no longer fits."*

Three words settle it. **"Repeat"** authorises more than one preflight. **"immediately
before fitting"** attaches it to each fitting phase, and tier H is a distinct fitting
phase begun later, after the machine state has changed. **"remaining"** is explicit that
the projection covers what is still ahead, not what has already been done — projecting
L+H again at the H preflight would double-charge tier L and could refuse a tier the
rulings permit.

The driver does exactly this: `preflight(remaining_tiers=["H"], …)` with the same margin,
reserve and limits, charging its own elapsed time onto the cumulative total, stopping
`resource-infeasible` with precisely the rulings' phrasing. **Consistent.** The one
qualification is C.5.2 — "remaining" should ideally also subtract tier L's elapsed fitting
time from the budget, which the driver does not do. That is a defect in the arithmetic,
not in the decision to repeat the preflight, and with 534 s of slack it cannot bind.

## C.8 Final state of the audit tooling

All eight suites re-run green against the final bytes, after the calculator edit:

| suite | result |
| --- | --- |
| `test_gate_calculator.py` | **174/174** (was 172; +3 provenance, −1 retired mismatch test) |
| `check_generator.py` | 21/21 |
| `check_v11_audit_set.py` | 5/5 |
| `check_models.py` | 25/25 |
| `check_accounting.py` | 14/14 + 6 notes |
| `check_production_path.py` | 42/42 |
| `check_gate_end_to_end.py` | 11/11 |
| `check_r1_evaluator.py` | 18/18 |
| `check_isolation.py` | 15/15 |
| `check_leaks.py` | 11 reviewed, 0 leaks |

New hashes for the two files I changed in this pass:

- `audit/gate_calculator.py` → `62ec54f10ed2acec9faa97d4abdbda2bb5a43cccb5924016d08a0a4e79738f71`
- `audit/test_gate_calculator.py` → `ce9146abdf76222ee870c74d43ed3daf88d790ff06258b5094314d75f54a82b6`

The driver stamps the new calculator hash automatically; `_fixture-run-B-clean/verdict.json`
already carries it. All twelve hashes the coordinator supplied were verified by me against
the files on disk with no mismatch, and 459 data files were verified against their
manifest-recorded hashes with 0 mismatches and 0 missing.

## C.9 Standing findings carried into the freeze

These are disclosed, not blocking, and all three are already ratified by Astra:

1. **SCHEMA §3.1 stale prose** about the audit-key spelling — a non-blocking documentation
   correction.
2. **Public/private separation is procedural, not cryptographic.** The public design can
   regenerate private quantities. A secret salt is recommended as a separately versioned
   amendment before wave 3.
3. **The cost claim is "equal counted operations under the registered estimate"**, with the
   permitted 5% spread disclosed — never "equal compute". The driver enforces this phrase
   and forbids the other.

Plus the two new non-blocking driver defects at C.5, and the recommendation at C.6 to fix
the simulator spelling in the next amendment.

## C.10 What this verdict does and does not say

It says the instrument is sound: the data are internally consistent and leak-free, the
production path is the registered one, the evaluator implements R1, query branches are
isolated, the ledger is honest, the gate implements rulings 2 in the registered order, and
the driver is bit-reproducible and refuses to overwrite or to manufacture a verdict from
data that cannot support one.

It says nothing whatever about whether the baselines learn anything. I have deliberately
never measured that. No learner has been fitted, scored or evaluated on the registered
calibration worlds in this audit; every learner-touching check ran on the published
fixture or on synthetic data I generated myself. The accuracy question is exactly what
the wave-1 freeze exists to answer, and it remains unanswered.

FREEZE-READY: YES
