# Astra reconciliation for Fable — Track A, 19 September 2026

**Suggested — authority.** This is the single additive reconciliation requested by Ben. [08-pairsuite-adjudication.md](08-pairsuite-adjudication.md) governs the conflicting chat ruling A; this file corrects 08's source-provenance paragraph and supplies the operational requirements below. Earlier files remain unchanged. The resulting plan of record is **08 plus 09**, confined here to Track A. No Track B decision is made.

**Shown — scope of this review.** I read the design, recovery report, relevant source and saved manifest; used Python standard-library byte hashing and arithmetic; and wrote this file. I did not run project code, import project modules, load checkpoints or tensor datasets, run tests or training, use GPU/SSH, inspect credentials, spend, message, or control jobs. Existing implementation-test reports are historical assertions, not checks rerun here. “Shown” means a source fact or calculation; “suggested” marks a design decision/inference; “untested” marks an execution contract or unmeasured behavior. Design decisions below establish the plan, not evidence of model competence or permission to execute it.

## Q1 — Which ruling governs?

**DECISION — suggested.** Confirm **08 governs**. Withdraw ruling A's automatic separate-key-pooling background, its ≥12/16 seeds with ≥3 pp causal gains screen for A4, and its key-pool-versus-key-pool A4 arms. The recovery report's “Suggested next comparison” is superseded on the pooling choice. Retain its matched pairs, ST-off separation, failure accounting and resource-rehearsal requirements where consistent with 08. Keep A's source-level provenance conclusion with Q2's runtime qualification, and the operational requirements accepted in Q3.

**Shown — basis.** 08 reports plain/shared → plain/separate G_pair gains/losses of 3/0 among 40 pairs and wire/shared → wire/separate of 10/8. Neither meets its prospective rule; these are retrospective observations, not preregistered wins. Separately, `P(Binomial(16, 21/40) >= 12) = 0.0582236600`, independently recalculated here. That is an illustrative screen-pass probability under a plug-in independent-win model, not measured prospective power. It supports the screen criticism without showing that separate pooling is useless or shared pooling optimal.

**CONTRACT — suggested decision; execution untested.**

> 08 governs Track A's affected comparisons. Shared card pooling is the incumbent for A1–A4; separate pooling is a candidate requiring its own admitted comparison in an existing slot. A4's control is **A4-plain-shared-v1**: legacy request with shared card pooling. Its treatment is the same recipe with pooled address selectors/composer, also with shared card pooling. Separate key pooling, score-only ST, other added answer-gradient surrogates and the relation wire are off in both arms. A4 changes only the request route and does not inherit winners of A1–A3. The remaining architecture, supervision, curriculum, optimizer and compute contract are 08's fixed A4 recipe.
>
> Advance on fresh seed-specific G_pair panels only when the exact one-sided paired gain/loss test has `p_exact <= 0.05`, the observed net gain `(g-l)/n >= 0.10`, and every safeguard passes. Here `g` is control-fail/treatment-pass, `l` is control-pass/treatment-fail, `d=g+l`, and `p_exact = sum(comb(d,k) for k=g..d)/2**d`, with `p_exact=1` if `d=0`. Do not retain the ≥12/16, ≥3 pp screen as an additional A4 hurdle or substitute it for this rule.
>
> G_pair requires c1/c2 ≥1969/2048, c3 ≥1876/2048, and c4/c5/c6 ≥945/1024. Keep c6 mandatory and report all six scores, gross gains/losses and held-out `min(c4,c5)/1024`. Retain no increase in fresh c1-stuck count (`c1 <1536/2048`), and treatment-minus-control one-sided 95% lower bounds strictly above −2 pp for mean one-hop and READS. Use fresh 512-world READS panels per seed and 08's 100,000 paired hierarchical resamples, paired world units within resampled seed pairs, empirical sorted element 5,000 (one-based), and manifest-derived independent diagnostic RNG. Inconclusive is not equivalent. Retain source, privilege, integrity and budget checks.
>
> Fix n before learning results. Sixteen pairs are an exploratory, low-power screen; 80 pairs/160 jobs are 08's preferred registration for the stated 20 pp planning effect if resources permit. Do not enlarge a promising 16-pair sample. A larger follow-up requires fresh seeds and a new slot/budget decision. Keep every registered failure or missing run in the denominator; incomplete or invalid evaluation cannot support advancement. G_pair does not confer G_cert or the separate fresh 77/80 certificate.

**Shown — wire implementation.** [RecoveryMini](../../scripts/premonition_recovery.py) subclasses `S.softread_class()`; that class subclasses `answer_path.CardBypassMini` with the soft-insert mixin, not the relation-shortcut class. Its legacy route delegates into that lineage; its pooled `_step` and `_recall` both call `_request`. Thus the supplied recovery implementation has no relation wire by construction in the inspected source. **Suggested:** this satisfies 08's requirement to bypass the wire at both sites through an unwired lineage; adding a redundant wire-removal patch is unnecessary. **Untested:** runtime conformance of the final frozen launch artifact still requires its authorized preflight.

## Q2 — Correct 08's provenance paragraph

**DECISION — suggested.** Close the helper source-byte limitation. Withdraw “The old helper bytes were not recovered” and the associated unidentified-edit qualification. Keep runtime parity untested. To honor the one-additive-file format, the following paragraph replaces 08's “Shown — provenance limitation” paragraph by reference; 08 itself is not rewritten.

**CONTRACT — exact replacement text.**

> **Shown — source provenance recovered; runtime parity untested.** The current pair generator, handoff evaluator and archived toy generator match their three entries in the four-source manifest. The current `scripts/premonition_first_card_probe.py` has SHA-256 `9a39578f931506fbe072ef1b814ac66ffb36db241e03cf9e28aa52a961c2037f`. Removing only its three recovery-format dispatch lines, numbered 107–109 in that version, while preserving every remaining byte yields SHA-256 `0f12d8b5443fe5b5a548ab7c875d490f8c873da9cdde37d9fef3cd6705ee4f93`, exactly the helper hash recorded in `artifacts/claude-pairsuite-20260919/manifest.json`. Fable's reproduction was independently repeated during 09's review, entirely in memory with the standard library. The removed block recognizes `premonition-recovery-v1`, imports `premonition_recovery`, and returns `recovery.from_blob(blob), blob`. The manifest-matching helper bytes are therefore reconstructible, closing this source-level provenance limitation. This does not establish runtime parity, validate checkpoint bytes, reconstruct every dependency/environment, or newly reproduce the saved assay. The saved suite remains accepted as substantive 07:45 measurement under 08's other qualifications, not as G_cert.

**Shown — exact removed block (not removed from the working file):**

```python
    if blob.get("format") == "premonition-recovery-v1":
        import premonition_recovery as recovery
        return recovery.from_blob(blob), blob
```

**Shown — reproduction method.** Read the helper as bytes, split with `keepends=True`, hash `b''.join(lines[:106] + lines[109:])`, and compare with `manifest['generator_sources']['scripts/premonition_first_card_probe.py']`. The other three current source hashes were also checked directly against the manifest. No helper or historical artifact was edited and no checkpoint was opened.

## Q3 — Which operational requirements survive?

**DECISION — suggested.** **All five carry into the plan of record**, with the distinctions below. Soft selectors as primary were already explicit in 08; this is confirmation, not a new mode choice. The selector-position script is a launch-readiness requirement separate from 08's relation-readout transfer prerequisite.

### 3a. Eval-only selector-position diagnostic

**Shown.** `_request` can return selector attention, but `_step` discards it. The current handoff trace records card/ASK outcomes, not selector-position accuracy. Inspection found no implementation of 08's complete selector-position diagnostic in the scripts examined. Existing recovery checks do not establish that this launch artifact exists.

**CONTRACT — untested.**

> Before A4 learning starts, implement, freeze and validate an eval-only selector-position script or equivalent evaluator module. It must preserve model outputs and parameters, use label-free inference, and report 08's second-scheduled-opportunity diagnostic at loop index 1 of K=4. Per evaluated pooled checkpoint, select the diagnostic relation head by highest relation-row argmax accuracy on disjoint one-hop/practised calibration data, break ties by lower head index, and freeze that assignment before held-out scoring. Calibration selects a reporting head only; it never routes inference or chooses the deployed policy.
>
> The denominator is every held-out question. A hit requires an actual non-NULL card request and the designated head's argmax at the visible relation row. Absent ASK, NULL retrieval, selector NULL and a pooled-card-row choice are failures; never shift to the next successful fetch. Report soft attention mass at the relation row, first-LINK retrieval, second-request person/relation key match and eventual joint answers separately. Legacy selector-position accuracy is N/A. Record the calibration/head assignment and diagnostic source hash. Labels enter scoring/calibration only, never model training or inference.
>
> Prelaunch readiness means the instrument exists and has passed authorized integrity/fixture checks; it does not require a successful A4 outcome before A4 has trained. Actual per-seed selector measurements occur after the registered checkpoints exist. This instrument does not replace the separately authorized 40-checkpoint relation-readout transfer assay required by 08.

### 3b. Explicit selector mode after loading

**Shown.** `RecoveryMini.__init__` assigns `hard_selectors=False`. `from_blob` constructs that class and loads tensor state, but neither the saved `recovery_options` nor `from_blob` restores this plain Python mode attribute. `model.eval()` does not set it to hard. Thus a reloaded pooled recovery model defaults to soft, even if a previous in-memory evaluation used hard selectors. The current pair-suite scorer does not explicitly set or record selector mode.

**CONTRACT — untested evaluator integration.**

> After every load and before each evaluation pass, the evaluator must explicitly set and verify the requested selector policy: pooled soft means `hard_selectors=False`, temperature 1; pooled hard means `hard_selectors=True`, argmax. Record requested and effective policy in every result, diagnostic and integrity record. Record `selector_mode=not_applicable` for legacy request arms. A default, prior pass, checkpoint filename or tensor fingerprint is not a mode record. Check mode consistency throughout the pass and restore or explicitly reset it before the next pass. Both policies use hard top-1 card retrieval with K=4 and the native ASK gate.

### 3c. Evaluator/loader hashes and mode in reuse identity

**Shown.** `premonition_pair_suite.py:648–659` accepts successful saved rows with the current data-manifest hash and indexes them by checkpoint path/hash. `cmd_score` uses that index to skip work. The old manifest's generator-source entries do not verify the evaluator/loader bytes currently executing, and the rows have no selector-mode identity. This is insufficient for future recovery-policy comparisons.

**CONTRACT — untested.**

> A reusable evaluation row must match the complete key `(checkpoint_path, checkpoint_sha256, evaluation_manifest_sha256, evaluator_source_hashes, loader_source_hashes, selector_policy, execution_config_sha256)`. The evaluation manifest must identify the exact seed-specific panels, gate/counting rules and diagnostic/calibration artifacts used by that row. Evaluator and loader hashes must cover the actual executed source closure, including the pair-suite/handoff code, first-card loader, recovery implementation and relevant imported/frozen model helpers. `selector_policy` includes requested/effective mode and temperature/argmax semantics, or explicit legacy N/A. The execution configuration identifies hardware/numerics and resolved model/retrieval options. Verify these fields before accepting reuse, and store them with the result.
>
> Any missing or mismatched field forbids automatic reuse as a new admitted result; do not relabel a historical row with unobserved mode or execution metadata. Reuse also requires valid completion and integrity records. Preserve historical rows and dataset bytes as historical evidence. Future A4 admission uses new seed-specific development panels under 08, with new paths/manifests; it neither regenerates/overwrites the archived suite nor consumes the sealed certification test split. Reusing an unchanged panel's bytes and reusing an evaluation result are separate decisions.

### 3d. Soft selectors are the predeclared primary policy

**CONTRACT — suggested decision; learning effect untested.**

> Train pooled selectors with soft attention at temperature 1 and use that same policy for primary G_pair advancement and its safeguards. Hard argmax selector evaluation is mandatory secondary reporting with a separate mode record/reuse key. It cannot rescue a failed soft-primary comparison, replace it after outcomes are seen, or support a hard-selector claim when only soft succeeds. Standard card retrieval remains hard in both policies. No soft-to-hard schedule or ST is introduced into A4.

### 3e. FLOP completion and admission throughput

**Shown.** With an explicit `--flop-budget`, the recovery runner already requires `report['stop'].startswith('flop budget') and report['budget_ok']` for `status='complete'`. Its step-count completion branch applies only without that flag and is unsuitable for A4. The inherited trainer can stop before another batch would exceed tolerance; its `budget_ok` check remains separately necessary. The runner caps training at 1,200 seconds; calibration, saving and evaluation add elapsed time. These are source facts, not demonstrated wave throughput.

**CONTRACT — untested execution/admission.**

> Every A4 job must receive the same explicit `B=3.407362074846783e13` counted model-FLOP budget. Training completion requires **FLOP-budget stop AND `budget_ok=true`**, with the frozen accounting convention and tolerance recorded. A time stop, update-cap stop, saved checkpoint, exit marker or nominal step count alone cannot count as completion. Choose the required update ceiling high enough to permit reaching B within the admitted time; reaching that ceiling first is incomplete. Keep incomplete jobs in the registered roster as failures. A complete training record alone is not a complete G_pair evaluation or certificate.
>
> Under the 1,200 s training cap, the nominal-budget admission floor is `B/1200 = 2.839468395705652e10`, approximately **2.8395e10 counted FLOP/s per concurrent job**. This is an arithmetic requirement, not a measured rate or advertised GPU throughput. Measure a conservative full-load rate for both arms and all curriculum modes under the frozen counter; use the slowest lower-bound rate. Count added selector work under that convention and disclose its excluded elementwise work, memory and wall time. Do not hide exposure differences behind equal nominal updates.
>
> Full-wave admission still requires `T = s + ceil(2*n/C) * (B/f + e)`, including setup/calibration, queueing, checkpoint writes, primary and secondary evaluation, READS, selector diagnostics, integrity work and collation. Meet 04's 1,500 s target and its time/cost authorization rules for the entire comparison. The per-job training-rate floor alone is insufficient, especially with multiple batches of jobs. Charge rehearsal, diagnostics, restarts and discarded work to the resource ledger; obtain an actual authorized resource/price basis before claiming admission. Unknown performance or cost is not a pass. Do not shrink n, cells or controls to make a wave appear admissible.

## Q4 — Ordered A4 launch checklist

**DECISION — suggested.** A4 is specified but **not launch-ready or authorized**. “Built” below means a source/artifact exists, not that it was executed or passed validation here. “Specified only” means implementation or registration work remains. “Needs Ben's authorization” identifies future execution outside this analysis-only request; no permission is requested or inferred now.

**CONTRACT — untested ordered checklist.**

| Order | Status now | Required artifact or action before proceeding |
|---|---|---|
| 1 | **Built** — source/artifact inspection shown | Use 08+09 as the authority. Recovery has legacy/pooled switches, shared pooling when `key_pool=False`, ST off when `score_only_st=False`, the unwired lineage, versioned loading and the explicit-budget completion predicate. Q2's source reconstruction is complete. Preserve those historical artifacts; these components are a foundation, not a complete launch package. |
| 2 | **Specified only** — runtime untested | Complete the A4 launch/evaluation package: explicit mode setting/records and full reuse key; eval-only selector-position instrument; 08's affine relation-readout assay; fresh seed-specific G_pair/512-world READS generation; paired safeguards/aggregation; complete roster/failure records; resolved source/config/numerics manifests. Isolate added-module RNG substreams as 08 requires and verify shared initial weights and paired batch streams. Current `build` copies shared weights but constructs the added selectors without an explicit separate RNG context; that contract is not established by equal seed integers. Hash the finished package. |
| 3 | **Needs Ben's authorization** — checks unrun here | Run implementation preflight on authorized fixtures/development material: legacy/disabled-option parity, loading and mode round trips, absence of wire/ST paths, label noninterference, unchanged parameters/normalization and isolated episode state, unchanged outputs under passive diagnostic instrumentation, correct NULL/no-request denominators, source-key/mode reuse rejection and budget/failure accounting. Confirm shared initialization/stream matching and added-module RNG isolation. Historical smoke reports do not substitute for checking the final changed package. |
| 4 | **Needs Ben's authorization** — premise needs measurement | Perform 08's affine relation-readout transfer assay on all **40 saved plain/shared controls**, with frozen model weights and normalization. Follow its fit/dev/held-out split sizes, L2 grid, convergence rules and static-embedding calibration control; report every seed and the predeclared c1-learned stratum. The ≥95% held-out accuracy and ≤2 pp transfer drop are per-seed readability flags, not a seed filter. Invalid calibration is inconclusive; valid weak transfer defers A4 as a clean downstream-selection test. Mixed outcomes stay mixed and require an explicit interpretation decision before admission; they do not silently waive 08's prerequisite. |
| 5 | **Needs Ben's authorization** — throughput/cost needs measurement | Rehearse the complete proposed load on disjoint rehearsal streams, with both fixed arm recipes, all curriculum modes and the full evaluation/diagnostic workload. Establish f, e, s, C, memory and actual cost; apply Q3e to the entire 32- or 160-job comparison. Rehearsal is not a source of development winners or replacements for registered learning seeds. If admission fails, stop rather than launch a partial comparison. |
| 6 | **Specified only** — registration not completed | Before learning outcomes, freeze the final A4 manifest: n and its stated power interpretation, all intended jobs and independent seed substreams, matched initial/shared weights and batch streams, new paired panels, soft primary/hard secondary, full source/loader/evaluator hashes, diagnostic rules/calibration scheme, exact gate/test/safeguards, B and tolerance, update/time caps, concurrency/order, hardware/numerics, full-wave cost/time and failure policy. Select 80 pairs if admitted for the stated 20 pp planning effect; otherwise any admitted 16-pair run is explicitly exploratory. No outcome-dependent enlargement or seed replacement. |
| 7 | **Needs Ben's authorization** — learning unrun | Ben authorizes the concrete registered A4 comparison and its resources after prerequisites pass. Diagnostic or rehearsal authorization alone does not authorize this learning wave. Execute exactly the one two-arm comparison; no pooling/wire/ST grid and no implicit A1–A3 inheritance. Nothing in this handoff launches it. |
| 8 | **Needs Ben's authorization**, normally included in order 7's registered scope — results unmeasured | Complete the registered primary/secondary evaluation and per-seed diagnostics, verify every completion/integrity/reuse record, and publish one full-roster table. Apply Q1 once without omitting failures or selecting the winning selector policy. Report mechanism diagnostics separately from G_pair admission. Any later G_cert/77-of-80 campaign is distinct and needs its own frozen registration and authorization. |

**Suggested — disposition for Fable.** Q1: **resolved as policy**. Q2: **resolved at source level; runtime parity untested**. Q3: **resolved as contract**, with evaluator/diagnostic integration still required. Q4: **resolved as an ordered plan; launch prerequisites need implementation, measurement and Ben's authorization**. No conflicting pooling, screen, arm or primary-mode decision remains open; no new learning result is claimed.
