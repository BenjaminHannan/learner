# 20 — Concept toy: rulings 3 (amendment `ct20-v1.2`)

**Fable reviewer, at Ben's request, 20 September 2026 — not an Astra document**

Prospective ruling on one amendment, written before any `ct20-v1.2` fit and without consulting any
accuracy, E, prediction or startup-label value from the invalid `ct20-v1.1` run, **with one accidental
exception that I disclose in §0.2 and analyse in §5**. I ran no training, no tests and no fits, edited no
existing file, and made no commit. This file is the only thing I wrote.

**Ruling in one paragraph.** Adopt **Fix 1 + Fix 3**, as the versioned amendment **`ct20-v1.2`**.
`ct20-v1.1` is closed for good with the verdict it earned, `calibration-invalid/accounting`; its tier H
is never run. `ct20-v1.2` reruns the **complete** wave-1 matrix once, on the same worlds, seeds, data
bytes and initialization bytes, with the same ratified step tables (L 370/254, H 2,163/1,588), the same
gate and the same hashed predictions. Fix 2 is rejected. The three previously disclosed cosmetic/
non-blocking items are **left alone** in this amendment. The v1.1 outputs are preserved, hashed and
quarantined unopened until the v1.2 verdict is sealed. My ruling plus Ben's own explicit "go" suffices
for this amendment; Astra is informed, not asked — but anything that would touch a number or rule Astra
ratified (including Fix 2) would need Astra.

---

## 0. What I read, what I did not, and one disclosure

### 0.1 Read

`wave1/ACCOUNTING-DIAGNOSIS.md` (sha256 `1de7eb48…225ea7`); `FREEZE-MANIFEST.md`; the prereg, rulings 1,
rulings 2 (on-disk) and `RULINGS-2-first-version-as-relayed.md`; `FABLE-PREDICTIONS-pilot.md`;
`audit/PILOT-AUDIT.md` §5, C.4.1, C.5–C.7; `audit/gate_calculator.py` (`advance_window`,
`evaluate_tier`); `scripts/fable_concepttoy20_models.py` lines 60–80, 405–445, 1090–1200, 1530–1750,
1830–2185; `scripts/fable_concepttoy20_wave1.py` lines 520–616, 695–860, 1114–1380;
`tests/test_fable_concepttoy20_models.py` lines 1560–1650. From `wave1/registered/verdict.json` I read
`tiers.L.cross_arm`, `tiers.L.gate.integrity`, `tiers.L.gate.reasons`, `tiers.L.gate.verdict`, the fit
counts, wall seconds and hash keys.

I re-hashed every bound file in the v1.1 manifest. All match (models `0b5711f4…`, driver `2db9889a…`,
simulator `c56794c5…`, loader `7139c698…`, calculator `62ec54f1…`, schema `7e9239c0…`, calibration
manifest `de3ccfec…`, fixture manifest `97fb94cf…`, predictions `420f9363…`, rulings 1 `40f65045…`,
rulings 2 `1245e46f…`, relayed first version `fac03f78…`, prereg `1bb49e07…`, audit `a2b2fa9d…`). So the
diagnosis's statement that nothing was modified after the freeze is confirmed by me.

### 0.2 Disclosure — I was not perfectly outcome-blind

While extracting the permitted accounting fields I printed the first 600 characters of
`verdict.json → two_tier`, expecting only the procedural explanation string. The slice ran past the
explanation into the start of an embedded tier-L result and showed me **two short non-numeric descriptive
fields and one truncated key name from the tier-L advance-window block**. It contained no E value, no
median, no case count and no startup label. It is nonetheless outcome-bearing: it constrains, without
determining, what tier L's scientific verdict would have been. I stopped there and opened nothing further.

I am **deliberately not restating the content here or in my report**, so that the coordinator, builders
and auditor stay blind; Ben can ask me for it, or read it himself, after the v1.2 verdict is sealed.
§5 shows why it cannot have steered this ruling (short version: the fix I choose reproduces v1.1's numbers
exactly, whatever they are; the only option that would change them is the one I reject). If Ben would
rather have the fix choice re-confirmed by a reviewer with no exposure at all, that is a reasonable
request and costs little; I do not think it is necessary, because every step below is checkable against
the documents and the code rather than against my judgement.

**A finding that follows from this, and matters to everyone:** the calculator computes every scientific
predicate *before* it looks at integrity (`evaluate_tier` calls `control_prerequisite`, `too_easy`,
`too_hard` and `advance_window` unconditionally), and the driver runs the evaluator and writes
`gate_table.json`, `verdict.json` and `report.txt` even when accounting is invalid. So the invalid run's
`verdict.json` and `report.txt` are **not** "accounting files with a few accuracy lines"; they carry the
full scientific result, including a copy nested under `two_tier`. "Read only the accounting fields" is a
fragile instruction for those files. See conditions 3 and 9.

One further small exposure to record: each ledger row carries `selection_loss` (the observed-label
selection loss, line 2019 of the models file). The diagnosing builder read the ledgers. That is a
learner-side training quantity, not an evaluator E, and the diagnosis quotes none of it — but the ledgers
are not purely accounting files, and the exposure statement (condition 4) should say so.

---

## 1. Which fix, and is `ct20-v1.2` a legitimate versioned amendment?

### 1.1 Fix 1, not Fix 2

**The registered schedule has six query panels per fit, and the code ran seven.** The texts:

- Rulings 1, under A: *"rung 1 reserves the initial fitting audit but has no separate initial query-panel
  or initialization charge… Agent 3 must reconcile initialization, both initial prediction sets, all rung
  query/selection forwards, final fitting diagnostics, loss computation and any other model work with
  actual execution."* — one initial panel, one panel per rung, and final **fitting** diagnostics.
- Prereg §3: *"Initial-checkpoint scoring is charged to the first rung; final fitting and state-use
  diagnostics are charged to the last rung."* — again a final *fitting* diagnostic, not a second query
  panel.
- Rulings 2 (first version) R5: *"Query-panel scoring passes execute and are charged at **every** rung;
  among post-fit rungs, only B=32 and B=512 feed the wave-1 accuracy predicates, alongside the initial
  checkpoint."*
- Rulings 1 C10 asks for saved *"initial query predictions, observed losses and final query
  predictions"*. The rung-512 panel **is** the final query prediction: it is taken on the final
  parameters. C10 asks for a saved value, not a separate pass.
- The auditor's §5.2 list of reconciled categories — the list Astra's R5 ratified the step tables
  against — contains no final query panel.

So the planning table is the registered object and `run_fit` line 2058 is the departure. Fix 1 brings
the code into line with the registration. Fix 2 would bring the registration into line with the code.

**I verified three things in the code that make Fix 1 safe:**

1. *The gate never reads the removed pass.* `collect_prediction_rows` (driver lines 727–737) feeds the
   evaluator from `query_predictions_by_rung[str(budget)]` for every rung including 512, plus
   `query_predictions_initial`. `lane_is_complete` likewise checks only `by_rung`. A repo-wide search
   finds `query_predictions_final` written once (models line 2131) and read only by one C10 presence
   test. No gate quantity, no E, no label depends on it.
2. *The removed pass cannot affect a trained parameter or any other prediction.* It runs after the last
   optimizer update, after the rung-512 checkpoint is already written (line 2000), under
   `@torch.no_grad()`, through `forward(...)`, a pure function of the parameters. It consumes **no RNG**:
   there is no framework-global generator anywhere in the fitting path; minibatch draws come from
   `namespace_generator(fit_namespace(world, seed, rung, update))`, a fresh stateless PCG64 per update.
   Its only side effect is the ledger charge.
3. *Fix 2 changes training; Fix 1 does not.* Fix 2 removes 8 last-rung updates from every fit in both
   tiers, so every B=512 checkpoint and every E_512 would move. It also contradicts R5: *"Freeze these
   **additional updates per rung**"* with the table 62/81/81/80/66 etc. A Fable reviewer has no standing
   to overrule numbers the design owner ratified; and choosing the one option that *changes results*,
   after a run exists on disk, would be the hardest possible choice to defend as outcome-independent.

Fix 1 is also the choice closest to the prereg's own attitude to the budget: *"a reservation is not
fictitious consumed work"* and *"not padded dummy computation"*. A duplicate forward pass on unchanged
parameters is exactly dummy computation that happens to be charged.

**Implementation notes for the builder (binding where marked):**

- **(binding)** Keep the `query_predictions_final` key in `predictions.json`, populated from the last
  executed rung's panel, so the saved artefact and SCHEMA are unchanged in shape and C10 stays satisfied.
  Prefer `rung_queries.get(last_budget)` over the diagnosis's `rung_queries.get(BUDGETS[-1])`: they are
  identical on the registered path (budget = 512), but `last_budget` also preserves v1.1 behaviour for
  test calls with `budget < 512`.
- **(binding)** No `final_query_panel` purpose may appear in `evaluation_ops_by_purpose`. The test at
  models-test line 1647 currently *requires* it; it must be inverted to require exactly six query-panel
  purposes (`initial_query_panel` + five `query_panel_rung{B}`).
- `run_fit(resume=True)` from a completed rung 512 would now save `query_predictions_final = None`
  instead of recomputing it. That path is unreachable from the registered driver (`_fit_child`:
  *"Deliberately NOT --resume"*; the unit of resumption is one whole fit). The auditor should simply
  confirm it is still unreachable; no code is needed.

### 1.2 Fix 3, sharpened

Fix 3 is required with either fix. Three corrections to the proposal as written:

- The every-row assertion must be **`rung_unused_reservation_ops >= 0`, not `> 0`**. On
  calibration-sized worlds the reservation is consumed exactly, so the correct value is `0.0` in every
  row (the diagnosis shows this for 288/288 rows). A `> 0` assertion would fail a correct run. No
  tolerance is needed or allowed: every term is an integer below 2^53.
- The driver guard must fire **before the evaluator is called**. `run_wave` already computes
  `cross_arm` from the ledgers before `run_evaluator` (lines 1220–1225), so this is a reordering of a
  few lines: if any ledger row has negative unused reservation, is over its rung allowance, or the
  per-fit/cross-arm check fails, the driver writes an accounting-only verdict
  (`calibration-invalid/accounting`, `H_permitted: false`) and **does not join truth, does not build a
  gate table and does not call the calculator's scientific predicates**. Rulings 2 R3 already says the
  coordinator *"must check both train and validation jobs **before** submitting the validation-only
  scientific gate table."* v1.1's driver submitted it regardless; that is what created the blindness
  hazard of §0.2. With this change a future accounting failure leaves no accuracy value on disk at all.
- Add one **shape-independent structural test**: the set of executed evaluation purposes must equal the
  set of reserved categories, pass for pass. The v1.1 bug was a pass with no reservation line; that is
  detectable on a world of any size, without relying on slack. Plus the diagnosis's tight-shape case
  (a synthetic world whose audit set equals the largest legal set, asserting unused == 0 at all five
  rungs, both arms, both tiers).

### 1.3 Legitimacy

**What the documents say happens to the v1.1 run.** Rulings 1 A3 step 2: *"A numerical failure, missing
required result, invalid accounting or failed integrity audit stops without escalation."* Rulings 2 R3:
*"A numerical failure, missing required fit/prediction, invalid accounting or failed integrity check
anywhere in the **required complete wave** prevents a pass and prevents H escalation as a scientific
budget treatment."* R4: *"A nonpositive denominator, absent/non-finite entry or exceeded allowance is
invalid."* Prereg §3: *"never over the allowance."* So v1.1 is invalid, permanently; it supplies neither
a pass nor the L leg of the two-tier procedure; its H is never run. The driver did exactly this. Rulings
1 also authorized *"run wave 1 **once**"*: that authorization is spent.

**What the rerun is not.** It is not resumption. R3: *"Exact continuation after a bounded infrastructure
interruption is resumption of the registered work, not a new seed or an accuracy restart"*; prereg §8:
*"Exact-state resumption is allowed only after infrastructure interruption within the registered wave
schedule."* Nothing was interrupted — all 72 fits completed — and continuing them could not un-spend the
over-allowance. Nobody should describe v1.2 as "resuming" or "finishing" v1.1.

**What the documents prescribe when a registration cannot be executed validly.** Prereg §3, on the
closest analogous case: *"the allocation is a preflight failure requiring a **revised registration**, not
padded dummy computation."* Prereg §8: *"If a recipe is revised, keep this version's failures and create
a new registration."* Prereg §5: *"Choose and preregister a new version before another pilot; **no
within-v1 retuning or final-family peeking**."* Rulings 1 D: *"Publish all implementation changes and new
hashes regardless of their classification… Do not redraw worlds or initialization just to change the
version label… Preserve the earlier artifacts."* A new, prospectively frozen version that keeps the old
failure on the record is therefore the prescribed remedy, not a loophole.

**What the documents prohibit, and how v1.2 stays clear.**

| Prohibition (source) | v1.2 |
| --- | --- |
| *"no replacements or selective restarts"* (rulings 2); *"Do not rerun only failed seeds, worlds or one arm"* (rulings 1 A3.3) | full 72-fit matrix, both arms, all seeds, all worlds, fresh output directory, zero fits reused |
| *"No seed replacement, best-of-three, failure-conditioned restart… or hardware substitution"* (prereg §2) | same three seeds, same machine and backend |
| *"Accuracy-conditioned restarting is prohibited"* (prereg §8) | cause diagnosed from ledgers; decision taken with scored outputs unopened; and the fix is outcome-neutral (§2.3) |
| *"No extra wave is silently added"* (prereg §8) | disclosed as the second execution of wave 1; v1.1's elapsed time reported |
| *"no within-v1 retuning"* (prereg §5) | no threshold, budget, allowance, cost constant, step count, optimizer, data byte, init byte or RNG namespace changes |
| *"do not present the amended run as unchanged"* (rulings 1 D) | new label `ct20-v1.2` stamped in every output |

**Classification.** Under rulings 1 D's taxonomy this is **not a substantive amendment** (it changes no
hypothesis, threshold, distribution or compute treatment); it is an implementation-conformance repair of
the kind D lists as *"fix numerical/implementation ambiguities"*. It still needs a new version label,
because a registered run already exists under `ct20-v1.1` and the two sets of outputs must never be
confusable.

**Version labels, precisely.** Change `EXPERIMENT_VERSION` in the models file to `"ct20-v1.2"` (the
driver inherits it; it is stamped into every checkpoint, ledger row, predictions file and verdict). Do
**not** touch `sim.py`, the public loader or the calculator: the simulator's `VERSION = 'ct20-v1.1'` is
written into the data manifests and now names the *data/evaluator contract*; the calculator's
`VERSION = "ct20-v1.1"` names the *gate contract*, and the driver already stamps tables with
`GATE.VERSION`. I checked that the evaluator does not reject a predictions file by version. The v1.2
manifest must state the three layers in one sentence: RNG/contract root `ct20-v1` (inherited), data and
gate contract `ct20-v1.1` (unchanged bytes), registration `ct20-v1.2`. This follows rulings 1 D's own
precedent (*"the experiment version is separate"*) and keeps the hashes of the simulator, loader,
calculator, schema and both data manifests valid.

---

## 2. The rerun, and what to do with the v1.1 outputs

### 2.1 Same worlds, seeds and initialization: not merely legitimate — required

Rulings 2: *"All seeds 20001/20002/20003 remain… Preserve the inherited RNG namespaces, initialization
and existing data bytes."* Rulings 1 D: *"Do not redraw worlds or initialization just to change the
version label."* Redrawing anything would be the violation. These are calibration worlds; the final
worlds are untouched by all of this.

### 2.2 The v1.1 outputs

- **Preserve; never delete or edit** (rulings 1 D, prereg §8).
- **Hash now**, before anything else: a sha256 list over every file under `wave1/registered/`
  (`find … -type f | sort | xargs shasum -a 256`). Hashing reads bytes but shows nobody any content.
  Bind the hash of that list in the v1.2 manifest. This is what lets anyone later prove the v1.1 outputs
  were not altered or re-scored.
- **Quarantine**: rename the directory to `wave1/registered-v1.1-INVALID-accounting/`, make it
  read-only, and put a short `README-QUARANTINE.md` beside it (not inside it) with the rules below.
- **Until the v1.2 two-tier final verdict is written and hashed, nobody opens any scored content of
  v1.1**: `verdict.json`, `report.txt`, `tierL/gate_table.json`, any evaluator output under `tierL/`,
  `fits/**/predictions.json`, checkpoints. This binds the coordinator, builders, auditor, me and Ben.
  The ledgers may be read for accounting only, through a script that projects the ops fields and drops
  `selection_loss`.
- **After the v1.2 verdict is sealed**, v1.1 may be opened for exactly one purpose: a reproducibility
  comparison against v1.2's tier L — tensor-hash equality of parameters and optimizer moments at all
  five rungs, and equality of `query_predictions_by_rung` and both audit prediction sets, for all 72
  fits. (File hashes will differ, because the version string is inside the files; compare tensors and
  values.) Report the comparison as one line in the wave-1 report.
- **Ever after**: v1.1's numbers are never reported as results, never pooled with v1.2, never used to
  fill a v1.2 cell, and never preferred over v1.2 if they differ. v1.2 is the registered result, whatever
  it says. If the comparison shows *any* difference, that is itself a finding — nondeterminism on the
  registered path, contradicting audit C.4.1 — and must be reported, not resolved by picking one.

### 2.3 Will the v1.2 fits be bit-identical, and does it matter?

**Yes, in every trained tensor and every gate-relevant prediction**, provided the same machine, the same
torch/NumPy builds, one thread, deterministic algorithms and the same shard plan (`--concurrency 6`).
Reasons: the removed pass is forward-only, after the final update and after the rung-512 checkpoint
write; RNG is stateless and namespaced per (world, seed, rung, update); `forward` is pure; and the
auditor already showed (C.4.1) that a second complete wave in a fresh directory reproduced all 72 fit
files byte for byte. The only differences will be: the version string in every file; rung-512's
`rung_executed_non_fitting_ops`, `rung_unused_reservation_ops` and `rung_counted_total_ops` (down by
exactly `query_panel_ops(arm)` = 17,172,576 G / 23,224,032 T); and the report-level `work` totals.
Keep the shard plan identical: the accepted ≤3.6e-7 batch-shape residual is only zero when the batch
shape does not change.

**Why it matters — it is the heart of the legitimacy argument, not a curiosity:**

1. A rerun that reproduces the same numbers is not a second draw. There is no lottery to re-enter, so
   "ran it, got invalid, ran it again" cannot buy a better result.
2. It makes the fix **outcome-neutral by construction**: whatever v1.1's fits would have scored, v1.2's
   will score the same. No knowledge of v1.1's outcome — mine in §0.2, or anyone's — could be exploited
   by choosing Fix 1.
3. It gives a free, strong, after-the-fact check (§2.2) that the amendment changed nothing scientific.

**What it does not do:** it does not rescue v1.1. One might ask, "if the fits are identical, why not just
re-score v1.1 with the duplicate panel subtracted from the ledger?" Because the ledger records what
executed, and what executed exceeded the allowance; R4 makes that invalid, full stop. Editing a ledger
after the fact is precisely what the accounting rules exist to prevent. The rerun costs about 20 seconds
for L. And legitimacy does not *depend* on bit-identity: if the machine state had drifted and bits
moved, v1.2 would still be the registered result.

### 2.4 Disclosure required in the v1.2 manifest and in the wave-1 report

(a) v1.1 ran once on 20 September 2026 and ended `calibration-invalid/accounting`; tier H was not run.
(b) The cause, in one sentence, with a pointer to the diagnosis and its hash. (c) v1.2 changes: one
redundant evaluation pass removed, guards added, version label; nothing else; ratified step tables
unchanged. (d) Same worlds, seeds, data bytes, init bytes, RNG namespaces, gate, predictions. (e) The
v1.1 outputs are preserved, with the hash of the hash list, quarantined unopened until the v1.2 verdict.
(f) The exposure statement of condition 4, including mine. (g) v1.1's elapsed resources (17.9 s wall,
8.4 s preflight) reported under wave 1 — prereg §9: *"failed or rejected work appears in
elapsed-resource reporting."* (h) After the verdict: the result of the v1.1/v1.2 equality comparison.
(i) Wording: "wave 1 was executed twice; the first execution was invalid for accounting and is reported
as such" — never "wave 1 was resumed" or "re-scored".

---

## 3. What carries over unchanged

| Item | sha256 | Status under v1.2 |
| --- | --- | --- |
| `calibration-v1.1/manifest.json` and its 459 files | `de3ccfec…` | unchanged; directory name stays (it names the data version) |
| `fixture-v1.1/manifest.json` | `97fb94cf…` | unchanged |
| `FABLE-PREDICTIONS-pilot.md` (P76–P82) | `420f9363…` | **stands; must not be edited, extended or re-hashed** |
| rulings 1 | `40f65045…` | binding, unchanged |
| rulings 2, on-disk | `1245e46f…` | binding, unchanged |
| rulings 2, first version as relayed | `fac03f78…` | binding, unchanged; "where one is silent the other governs" still holds |
| prereg, simulator spec, build plan | `1bb49e07…`, `aa80843c…`, `ba255726…` | unchanged |
| `SCHEMA.md` | `7e9239c0…` | unchanged (it does not mention the final panel; I searched) |
| simulator, public loader | `c56794c5…`, `7139c698…` | unchanged — do not touch |
| `audit/gate_calculator.py` + its 174 tests | `62ec54f1…`, `ce9146ab…` | unchanged — do not touch |
| `audit/PILOT-AUDIT.md` | `a2b2fa9d…` | preserved as the v1.1 audit; v1.2 gets an addendum file, not an edit |
| `FREEZE-MANIFEST.md` (v1.1) | `289b631c…` (as hashed by me today) | preserved unedited; v1.2 gets its own manifest |

**Predictions.** They may stand, and they must. The rulings-2 first version already says *"Preserve
Fable's already-hashed predictions (`420f9363…`)"*. They were written before any fit; they are about what
the baselines will do, not about accounting; and because v1.2 reproduces the same fits, they are
predictions about exactly the same objects. Re-writing or re-hashing them now — after a scored run
exists on disk, even unopened — would destroy the one property that makes them worth having. The v1.2
manifest simply re-binds the same hash. Score P76–P82 once, against the v1.2 run. For honesty, add a
footnote to the eventual report: Fable made no prediction covering an invalid run, and read literally
against v1.1, P78 ("tier H is triggered") and P79 would have resolved "no" for a non-scientific reason.

**New hashes v1.2 must bind:** models file, driver, the two changed test files, this ruling, the
diagnosis (`1de7eb48…`), the v1.1 quarantine hash list, the auditor's v1.2 addendum, and the v1.2
manifest itself.

---

## 4. Minimum sufficient re-audit, and the three leftover items

The audit must be done by the independent auditor (Agent 3), not by the builder who makes the change.

**A. Diff confinement.** Before editing, save byte copies of the frozen v1.1 `models.py`, `wave1.py`
and the two test files (their hashes are in the v1.1 manifest). The auditor diffs v1.2 against them and
confirms the change is confined to: the version constant; line 2058's replacement; the driver's
pre-evaluator guard and accounting-only verdict path; header/comment strings; and the tests. Re-verify
the hashes of every "unchanged" row in §3, including the 459 data files against both manifests.

**B. Suites.** Rerun in full: `tests/test_fable_concepttoy20_models.py`, `…_wave1.py`, `…_sim.py`,
`audit/test_gate_calculator.py` (174), and the audit checks that touch changed code —
`check_accounting.py`, `check_models.py`, `check_production_path.py`, `check_gate_end_to_end.py`,
`check_isolation.py`. New tests required: every-row `unused >= 0`; the purpose-set/reservation-set
equality test; the tight-shape case; a driver test that a deliberately broken reservation (monkeypatched
in the test, not in production code) yields an accounting-only verdict with **no** evaluator output and
**no** gate table on disk.

**C. Fixture equivalence, v1.1 code vs v1.2 code.** Run the v1.2 driver end to end on `fixture-v1.1` in
a fresh directory and compare with the auditor's existing clean v1.1 fixture run: parameters and both
Adam moments identical at all rungs in 12/12 fits; `query_predictions_by_rung`, both audit sets and
`query_predictions_final` identical; `predictions.json` identical except the version string; ledger rows
identical except the three rung-512 fields, which move by exactly one `query_panel_ops(arm)`. This is
the empirical proof that the amendment changes accounting and nothing else. (Fixture accuracy is not
registered data; this comparison is on tensors and ledgers anyway.)

**D. The calibration-sized accounting dry run — outcome-blind, and how.** This is the check v1.1 lacked,
and it is possible without fitting or scoring:

- Write it as an **audit script** (e.g. `audit/check_accounting_dryrun.py`), not as production code.
- It calls the real `run_fit` on the real `calibration-v1.1/public` directory with the real shard plan
  (`shard_plan(..., concurrency=6)` — padded audit widths depend on which lanes share a shard), for all
  72 fits, with `override_step_table=[0,0,0,0,0]`. That hook already exists, is unreachable from the CLI,
  and stamps `step_table_overridden: true` so the output can never be mistaken for a registered run.
  **Zero optimizer updates happen: nothing is fitted.**
- The script monkeypatches `Runner.predict_batch` to return zeros of the right shape. So no model
  inference runs on registered worlds, and every "prediction" written is `0.0` and carries no
  information. The real `audit_pass` / `query_pass` / `_charge_evaluation` / reconciliation code still
  executes at the real shapes, which is the point: v1.1 failed because the *executed* path differed from
  the *planned* path, so the check must go through the executed path.
- `run_fit` is given only the public directory; the private directory is never read; the evaluator and
  the calculator are never invoked. Output goes to a scratch directory outside `wave1/`.
- The script then does the arithmetic, per fit, per rung, **for both tiers**: executed non-fitting ops
  ≤ reserved; executed non-fitting + frozen steps × `update_ops(arm)` ≤ rung allowance; per-fit sum ≤
  fit allowance; per-rung cross-arm gap ≤ 0.05; and equality with the frozen planning table. The
  per-update cost is data-independent (4 episodes × 17 records, fixed), so multiplying it out is exact.
- Expected values. Tier L, per rung: G 198,883,341 / 198,837,012 / 199,910,322 / 199,827,422 /
  198,666,828, per fit 996,124,925; T 199,000,513 / 198,640,300 / 197,092,434 / 199,995,486 /
  198,646,732, per fit 993,375,465 (from the diagnosis). Tier H, by my hand arithmetic from the
  diagnosis's reservations and R5's step table — the auditor must reproduce these from `step_table()`
  rather than trust me: G 999,281,021 / 999,234,692 / 998,078,482 / 997,995,582 / 999,064,508, per fit
  4,993,654,285; T 999,838,177 / 999,477,964 / 997,930,098 / 997,833,758 / 999,484,396, per fit
  4,994,564,393; H gaps 0.000557 / 0.000243 / 0.000149 / 0.000162 / 0.000420. Unused reservation
  should be exactly 0.0 in all 720 rows. (Note that v1.1's tier H would have failed the same way:
  425 × 2,229,520 + 68,691,084 = 1,016,237,084 > 1.0e9. The dry run is the first time tier-H accounting
  is exercised at real shapes; v1.1 disclosure 4 said it never had been.)
- Why this is not an experiment: prereg §1 — *"Agent code reviews, synthetic interface tests and algebra
  checks are not experiments; accuracy measurements are."* No accuracy is measured, no parameter is
  updated, no truth is joined. It reads only public bytes the generator and leak checks already read
  before the v1.1 freeze.

**E. Timing.** No separate work: the driver repeats the bounded synthetic preflight immediately before
fitting and again before H. Fix 1 only removes work, so projections can only shrink.

**F. Auditor's output.** A short addendum file (not an edit to `PILOT-AUDIT.md`) ending
`FREEZE-READY: YES` for `ct20-v1.2`, then `FREEZE-MANIFEST-v1.2.md`.

### The three leftover items: leave all three

- **`learned_failed_to_transfer` spelling — leave.** Fixing it means editing `sim.py`, whose hash is
  bound inside both data manifests; the auditor already judged that *"a real freeze risk incurred for a
  cosmetic string"*. In v1.2 the cost is higher still: "the simulator and all data hashes are untouched"
  is the cleanest single sentence in the amendment's defence, and I will not trade it for a label. The
  one-entry alias stays, with every other label difference still fatal.
- **Shard-scoped `work` block / `initial_parameter_hashes` — leave.** Fixing it changes checkpoint
  contents. v1.2's strongest after-the-fact check is tensor-level equality of checkpoints with v1.1; do
  not muddy it. The existing instruction stands: audit costs from `tier*/ledgers/*.jsonl` only.
- **Tier-H feasibility not subtracting tier-L elapsed — leave.** It is one conservative line and I was
  tempted, since the driver is being edited anyway. But it alters the *decision whether H launches*, and
  in an amendment made while a scored run sits on disk, every change to launch logic beyond the diagnosed
  defect is a change someone can later ask about. It cannot bind (534 s of slack; L took 18 s), and
  `timing_ok` still catches a real overrun.

The auditor's "correct in the next versioned amendment" was written with a routine amendment in mind.
v1.2 is a single-defect repair, and its defensibility comes from being exactly that. All three items
move, with the stale SCHEMA §3.1 prose, to the **second freeze** the prereg already schedules after
calibration (§1), when `sim.py` must be opened anyway for the recommended secret-salt amendment. Carry
v1.1 disclosures 1–6 into the v1.2 manifest verbatim.

---

## 5. Could this amendment be, or look, outcome-dependent?

**R-a. A fully scored invalid run is on disk.** As §0.2 explains, its verdict and report files contain
the complete scientific result. *Closure:* hash, quarantine, the no-open rule, the ops-only ledger
reader (conditions 2–3); and, structurally, the driver change in §1.2 so this can never happen again.

**R-b. My own exposure (§0.2).** *Closure:* disclosed; content withheld from the blind parties;
and the neutrality argument — Fix 1 reproduces v1.1's tier-L numbers exactly, whatever they are, so no
knowledge of them can be served by choosing it. The only option that would *alter* the numbers is Fix 2,
which I reject on documentary grounds that anyone can check without trusting me. Nothing else I rule on
(quarantine, re-audit, leaving the three items alone, who ratifies) has any path to an accuracy value.

**R-c. The builder read ledgers containing `selection_loss`; the coordinator read `verdict.json`
selectively.** *Closure:* exposure statement; same neutrality argument; from now on nobody reads those
files by hand.

**R-d. Appearance: "they ran it, didn't like something, and ran it again."** *Closure:* the rerun is a
deterministic replay, not a redraw; the v1.1 hash list is committed *before* v1.2 launches; the
post-verdict equality check is published. Anyone can then verify that v1.2 = v1.1 minus one redundant
forward pass.

**R-e. Scope creep.** Every extra edit enlarges the surface over which outcome-independence has to be
argued. *Closure:* the minimal diff of §4-A, enforced by the auditor.

**R-f. Conditional willingness to amend.** Would anyone have pushed as hard for a rerun had the numbers
looked different? Nobody knows the numbers, which is the answer; but make it explicit. *Closure:* the
decision to rerun is taken now, blind, and is unconditional; **the v1.2 verdict is binding whatever it
is** — advance, too easy (stop), too hard, inconclusive, a control failure at H (ends the version), or
another invalidity. No change to v1.2 is permitted between the freeze and the verdict.

**R-g. A chain of reruns.** One blind repair is a repair; a sequence of them is a garden of forking
paths even if each is blind. *Closure:* if v1.2 itself ends invalid for any integrity reason, there is
no `v1.3` on a Fable reviewer's say-so. That goes to Astra.

**R-h. Environment drift.** *Closure:* record torch, NumPy, Python, OS and thread settings in the v1.2
manifest; run on the same Mac. If anything changed since v1.1, say so; v1.2 still stands, and the
equality check will show whether bits moved.

**R-i. Nothing timestamps the freeze.** The repo has a single initial commit and the experiment files
are untracked. *Closure:* at minimum the v1.2 manifest's own hash must be recorded somewhere outside the
files it binds, before launch (as v1.1 did). A git commit of the frozen state would be better; that is
Ben's call, not mine.

---

## 6. Must Astra ratify?

**No — for this amendment, on these terms. My ruling plus Ben's own explicit go-ahead suffices.**

- The documents do not reserve amendments to Astra. Astra's two authorizations were scoped (*"Fable may
  freeze and run wave 1 **once**"*; *"No additional Astra permission is required when those conditions
  hold"*), and the first is spent, so v1.2 needs a fresh authorization from someone. Ben owns the
  project; Astra leads the design by Ben's appointment; and Ben's standing instruction of 20 September
  routes design questions and rulings to a Fable reviewer. Ben is entitled to do that.
- The limit of that delegation is where I would be overruling Astra rather than applying Astra. v1.2 as
  ruled here changes **no number, rule, threshold, table, distribution or claim limit Astra ratified** —
  it makes the code execute the ledger Astra ratified. That is within a reviewer's competence. **Fix 2,
  or any change to step tables, allowances, cost constants, seeds, data, gate rules or predictions, is
  not**, and would need Astra through Ben. So would a `v1.3` (R-g).
- Two honest caveats. First, I am the same model family as the coordinator and the builders; Astra is
  the only genuinely outside party, and §0.2 shows I am fallible. The independent auditor's re-audit and
  the mechanical, checkable nature of every condition below are what carry the weight, not my authority.
  Second, no message from me or from any agent is Ben's consent: **Ben himself must say "go"** after the
  auditor closes, and that yes should be recorded in the manifest.
- **Inform Astra; do not wait for Astra.** Send a short, self-contained note through Ben at the next
  natural contact, and no later than the second freeze before wave 2 (which needs Astra-level design
  input anyway): what failed, the fix, that the ratified tables stand, the quarantine hash, the exposure
  statement. Astra keeps the right to object. Nothing is lost by proceeding first, because v1.1 is
  preserved with hashes and v1.2 is a deterministic replay; if Astra later requires something different,
  it can be done as a new version with v1.2 kept on the record like v1.1.

---

## Conditions that must all hold before the `ct20-v1.2` launch

1. **v1.1 is closed.** Its final verdict `calibration-invalid/accounting` stands permanently; its tier H
   is never run; nobody describes v1.2 as a resumption, continuation or re-scoring of v1.1.
2. **v1.1 outputs hashed and quarantined** before any code is edited: sha256 list over every file under
   `wave1/registered/`; directory renamed `registered-v1.1-INVALID-accounting` and made read-only;
   quarantine README beside it; the hash of the list recorded for the v1.2 manifest.
3. **No-open rule in force** until the v1.2 two-tier final verdict is written and hashed: no person or
   agent opens v1.1's `verdict.json`, `report.txt`, gate table, evaluator outputs, predictions files or
   checkpoints. Ledgers only through a script that emits ops fields and drops `selection_loss`.
4. **Exposure statement written** into the v1.2 manifest: who has seen what from v1.1 (coordinator:
   accounting fields of `verdict.json`; builder: ledgers, which include `selection_loss`; this reviewer:
   the accounting fields plus the accidental fragment of §0.2; Ben: whatever is true). If anyone has seen
   more, it is stated, not fixed.
5. **Frozen v1.1 source copies saved** (models, driver, two test files) so the v1.2 diff is auditable.
6. **Fix 1 applied as specified in §1.1**: line 2058 removed; `query_predictions_final` key kept and
   filled from the last executed rung's panel; no `final_query_panel` purpose exists; step tables
   unchanged at L 62/81/81/80/66 and 39/58/57/57/43, H 421/440/439/438/425 and 306/325/324/323/310.
   Fix 2 is not applied in any form.
7. **Fix 3 applied as sharpened in §1.2**: every-row `rung_unused_reservation_ops >= 0` (exact, no
   tolerance, `>=` not `>`); the driver's accounting guard runs **before** the evaluator and, on failure,
   writes an accounting-only verdict with no truth join, no gate table and no scientific predicates;
   purpose-set equality test; tight-shape test; broken-reservation driver test.
8. **Version label**: `EXPERIMENT_VERSION = "ct20-v1.2"` in the models file only. Simulator, public
   loader, calculator, calculator tests, SCHEMA, both data directories and all design documents
   untouched, hashes re-verified equal to the v1.1 manifest (459 data files included). The manifest
   explains the three version layers.
9. **Nothing else changes.** The label spelling, the shard-scoped `work` block, the tier-H feasibility
   arithmetic and the stale SCHEMA prose are left exactly as frozen in v1.1 and carried as disclosures;
   they move to the second freeze.
10. **Predictions untouched**: `FABLE-PREDICTIONS-pilot.md` still hashes to `420f9363…8cc9`; no
    prediction added, edited or re-hashed. Both rulings-2 documents and rulings 1 bound unchanged.
11. **Independent re-audit passed** (§4 A–C, by Agent 3, not the fixing builder): diff confined; all
    suites and audit checks green including the new tests; fixture equivalence shown — tensors and
    predictions identical to the v1.1-code fixture run, ledgers differing only at rung 512 by exactly one
    `query_panel_ops(arm)`.
12. **Calibration-sized accounting dry run passed** (§4 D): real `run_fit` path, real public calibration
    shapes, registered shard plan, zero updates, `predict_batch` stubbed to zeros, private directory and
    evaluator never touched, scratch output; all 720 rows (72 fits × 5 rungs × 2 tiers) within rung
    allowance, per-fit within allowance, unused reservation ≥ 0, per-rung cross-arm gap ≤ 0.05, and
    totals equal to the frozen planning table.
13. **Auditor's addendum ends `FREEZE-READY: YES` for `ct20-v1.2`**, and `FREEZE-MANIFEST-v1.2.md` binds:
    all carried-over hashes, the new models/driver/test hashes, this ruling, the diagnosis
    (`1de7eb48…`), the v1.1 quarantine hash list, the addendum, v1.1 disclosures 1–6 verbatim, the
    §2.4 disclosures, the environment versions, and the exact launch command. The manifest's own hash is
    recorded outside the files it binds.
14. **Launch discipline**: one launch, same machine, `--concurrency 6 --preflight-seconds 6`, a **fresh**
    `--out` (e.g. `wave1/registered-v1.2`), **no `--resume`** unless a genuine infrastructure
    interruption occurs inside v1.2. The v1.2 verdict must show `n_fits_reused_from_disk = 0` and
    `n_fits_run_now = 72` for each tier run. The driver's own preflight must pass immediately before
    fitting (and again before H).
15. **Pre-commitment recorded in the manifest**: the v1.2 verdict is binding whatever it is; tier H runs
    if and only if v1.2's own tier-L verdict requires it under the unchanged two-tier procedure; no
    amendment between freeze and verdict; if v1.2 ends invalid, any further version goes to Astra.
16. **Ben's own explicit "go"**, given after conditions 1–15 are reported met, and recorded. A note to
    Astra is prepared for Ben to relay; the launch does not wait for a reply.

After the verdict is sealed (not a launch condition, but owed): run the v1.1/v1.2 equality comparison of
§2.2 and report it; score P76–P82 against v1.2 with the P78/P79 footnote; report v1.1's elapsed
resources under wave 1.

---

## Five lines for Ben

The first run was thrown out for a bookkeeping reason, not a science reason: the code checked its answers one extra time at the very end, and that extra check pushed the last step over its compute budget.
The fix is to delete that repeated check — it gave the exact same answers as the check just before it — and to add a tripwire that stops the run *before any scoring* if the books ever fail to add up again.
Because nothing about the training changes, the rerun will train the very same models to the very same numbers; that is what makes it a fair do-over rather than a second roll of the dice.
The old run's results stay locked away, fingerprinted and unopened, until the new run's verdict is final; then they are compared once, just to prove nothing changed. (I accidentally glimpsed one small non-numeric piece of the old result while reading the cost fields; I have written down that it happened, not what it was, and the fix I chose cannot be helped by it.)
You do not need Astra's sign-off for this, because no number Astra approved changes — but the launch needs the independent auditor's OK, a full-size practice run of the bookkeeping with no training in it, and your own "go"; and Astra should be told.
