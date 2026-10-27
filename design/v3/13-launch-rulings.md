# A3-teacher-delay-v2 — launch rulings

19 September 2026. Astra; Track A only. Additive to [12](12-teacher-delay-contract.md), [09](09-reconciliation.md) and [08](08-pairsuite-adjudication.md); explicit amendments below prevail, all other requirements remain. These are design rulings, not measured admission or extra spending authority. Supplied approval: **two rentals, $2.50 total hard stop**, including setup, rehearsal, evaluation, retries, fees and billing increments. This review only read text and wrote this file; no tests, training, project imports, checkpoint loading, GPU, SSH, credentials, spending or messaging.

## 1. Two boxes

**DECISION — Accept with paired placement and descriptive box reporting.**

**CONTRACT**
> Two boxes may implement the one declared training configuration. Match RTX 5060 Ti model/VRAM, image digest, software/driver versions and resolved numerics. Declare CPU models and the permitted 85–96-vCPU capacity variation; rehearse both boxes and use the slower bound. Advertised specifications alone do not establish admission.
>
> Number pairs 0–47: even IDs on A, odd on B; GPU index `floor(pair_id/2) mod 4`. Both arms run on that same physical GPU in the same wave. Start them consecutively; alternate first arm across successive pairs on each box/GPU: control first when `floor(pair_id/8)` is even, delayed otherwise. This balances first-arm starts 3:3 on every GPU. Freeze the entire order/wave map.
>
> Report L_train's complete 2x2 table, gains/losses and failures by actual box and pooled; also G_pair gains/losses by box. Record actual host/GPU and recovery placement. Keep 12's pooled n=48 exact test, effect floor and bootstrap unchanged. Box summaries are descriptive: no extra acceptance hurdle, exclusion, reweighting or favorable-box selection.

## 2. Infrastructure recovery

**DECISION — Permit one blinded training recovery per affected pair, with the SAME seeds. This explicitly narrows 12's no-replacement rule.**

**CONTRACT**
> Retry only for independently evidenced external interruption or artifact loss: provider/host death, external process termination unrelated to job performance, storage failure, or unrecoverable transfer failure after re-copy was attempted where possible. A disconnect is not proof of loss. Scores, divergence, NaNs, application defects, workload OOM, time/update stops and budget failure are not retry grounds; generic error/status fields alone are insufficient evidence.
>
> If either arm lacks a recoverable budget-complete checkpoint because of an eligible incident, supersede BOTH arms and restart BOTH from the original initialization/seeds/streams at zero FLOPs; no partial resume. Keep both retries together on the original GPU index of an authorized matching host, under the frozen concurrency/order policy. Preserve available originals, including a healthy sibling. Attempt 1 becomes mandatory once elected; never select between attempts by outcome or revert if it fails. Maximum one training recovery per pair; n stays 48. Lost evaluation alone permits re-evaluation of the unchanged checkpoint, not retraining.
>
> Before retrying, append and hash: event time/evidence/cause, affected IDs, original hashes or missing markers, outcome-exposure attestation, mandatory supersession, identical seeds/config, new paths/placement and revised time/cost bound. No extra rental is authorized. Recovery must fit authorized capacity and the remaining $2.50 cap; otherwise unresolved failures block advancement. Publish every attempt and distinguish recovered incidents from unresolved failures.
>
> Recovery requires NO registered learning outcome to have been exposed to any human, LLM or agent able to influence execution. “Outcome inspected” includes loss/curves, recall, accuracy, escape timing, predictions/answer traces, gates, paired differences, or raw result/evaluation files exposing them. Frozen automated evaluation/integrity tools may process sealed outcomes without exposing them or using them for execution choices. Only section 6's health allowlist is exempt. Exposure of even one outcome closes learning recovery globally; early exposure must be disclosed and cannot earn protocol-compliant advancement under this file.

## 3. Rehearsal fallback and time/cost

**DECISION — Lower two-box concurrency is conditionally pre-approved; a third rental is not. Raising 1,200 seconds is a contract change and is rejected here.**

**CONTRACT**
> Before registered learning, rehearse disjoint streams in this fixed order: **12 processes/GPU (48 jobs/box, one wave), then 6 (24/box, two waves), then 4 (16/box, three waves), then 2 (8/box, six waves)**. Select the first fully admitted rung; stop when remaining funds cannot cover rehearsal plus completion/copy/teardown. Preserve section 1's placement; fill each GPU's waves with successive whole pairs. One selected configuration governs the entire comparison; no mid-comparison throughput tuning.
>
> Require a conservative measured per-job rate covering the slower arm/all phases on both boxes, above `B/1200 = 2.838567926e10` counted FLOP/s with operational margin. Retain `B=34062815112683.242`, tolerance .05, 20,000-update ceiling, **1,200 training seconds per attempt**, and completion = FLOP-budget stop AND `budget_ok=true`. Queueing more waves never extends an attempt's cap.
>
> Use 12's `T = s + ceil(96/C)*(B/f_rate + e)`, including all six cells, READS, serial CPU-evaluation bottlenecks, integrity/copy work and final reporting. Target 1,500 seconds; the ceiling is 1,800 seconds for the WHOLE comparison. A slower paid two-box plan is permitted by this amendment to 12's free-only fallback **only if the lowest-cost credible available plan meeting 1,800 seconds costs over $2**, with its full price/performance basis recorded. A credible qualifying option at $2 or less rules out the slower fallback. Unknown cost/throughput does not establish the exception. Cumulative spending still stops at $2.50.
>
> A third identical box at 32 jobs/box is technically acceptable only after Ben extends the two-box authorization, before learning, with a revised full placement/rehearsal/price freeze. It is not automatically authorized by a quote below $2.50. If no authorized rung qualifies, **abort admission and return to Ben**. No reduction of B, n, cells or controls, no cap increase, and no relabeling waves as separate comparisons.

## 4. Training configuration

**DECISION — Pin MPS and the rehearsed software/numerics; retain nondeterministic execution. Do not guess historical TF32 values.**

**CONTRACT**
> Pin **CUDA MPS ON**, its resource-share settings, the selected process ceiling/waves/order/tail policy, and **`--threads 1`**. Pin Torch intra-op threads to 1; freeze inter-op and BLAS/OpenMP settings at rehearsed values. Resolve `pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime` to an immutable image digest; pin actual Torch/Python/CUDA/cuDNN/library builds and host driver. No package updates after rehearsal. Pin fp32 floating-point tensors/optimizer arithmetic and **autocast OFF**, without mixed precision, quantization or a new compiler path; token IDs retain integer dtypes.
>
> Preserve that image's unmodified startup TF32 policy: capture actual CUDA-matmul/cuDNN TF32 flags, float32-matmul precision and relevant environment overrides during preflight, then require those exact values in every job. “Default,” “fp32” or “unknown” are not sufficient manifest values. These values are pinned, not merely recorded or chosen by throughput/outcomes; historical TF32 equivalence is not asserted.
>
> Keep deterministic algorithms disabled and cuDNN deterministic mode false; add no determinism-enforcing environment settings. Freeze resolved cuDNN benchmark/backend flags. Retain paired seeding; GPU trajectory identity is not required and divergence never authorizes a retry.
>
> Merely record physical instance IDs/GPU UUIDs, CPU model/count, observed clocks/temperature/utilization/memory pressure, realized concurrency and timing. These are provenance/telemetry, not adaptive controls. An intentional execution-setting change requires another disjoint rehearsal and freeze BEFORE learning.

## 5. Evaluation location

**DECISION — Rental CPU or Mac CPU is acceptable; choose ONE physical evaluation host for all 96 canonical evaluations.**

**CONTRACT**
> Before learning, choose A, B or Ben's Mac CPU. Evaluate every pair/arm's six cells and READS there with one frozen evaluator/loader, CPU/library environment, worker/thread/batch policy and fp32 configuration. Mac GPU/MPS is excluded from this CPU route. Preserve native ASK, hard top-1, K=4, label separation, twin counting and unchanged-weight/state checks. Training and evaluation may have different declared environments; canonical evaluation rows may not mix environments.
>
> Count evaluation in full admission even when deferred to the Mac. No backend change after score inspection. If the evaluation host is lost while outcomes remain sealed, a documented, admitted replacement requires re-evaluating ALL 96 unchanged canonical checkpoints on that one replacement host; retain superseded rows. Other evaluation retries retain the frozen environment and 09's complete reuse identity. Evaluation cannot select training attempts.

## 6. Outcome blinding and monitoring

**DECISION — Fable may inspect allowlisted health/status, not training curves or raw results.**

**CONTRACT**
> This applies to Fable, Ben, sub-agents and dashboards until release. Allow: opaque job/attempt ID, placement, PID/alive/heartbeat, elapsed time, update count, counted FLOPs/share, resource use, exit code, sanitized infrastructure error, checkpoint existence/size/hash, and training/evaluation/integrity completion status. Training stop reason and `budget_ok` may be projected separately. Evaluation status means computation/integrity complete, never gate pass/fail. Aggregate completed/crashed counts are allowed; arm names are unnecessary in monitoring.
>
> Hide losses, recall/accuracy, predictions, escape events, cell counts, gate/stuck flags, paired summaries and raw stdout/stderr/result.json/eval.json containing them. A frozen checker emits only the health projection and schema/integrity verdicts; retain full raw logs sealed. Health information may trigger only registered recovery or protective shutdown, never competence-based intervention.
>
> Release outcomes after an immutable roster/attempt lock identifies all 96 canonical jobs, training/evaluation/integrity checks are complete and valid, and retries are permanently closed. If completion is impossible, first irreversibly close recovery and freeze every terminal failure/missing record, then release a **non-advancing failure report**. Missing controls cannot manufacture gains.

## 7. Freeze and copy-back

**DECISION — Complete pre-learning freeze, append-only incidents, verified local custody before teardown.**

**CONTRACT — BEFORE the first registered learning update, SHA-256 hash and freeze:**

1. **Authority/statistics:** 08, 09, 12 and this file; experiment ID; complete primary/safeguard/secondary definitions, cutoffs/denominators; 100,000-resample bootstrap, 5,000th order statistic and diagnostic RNG derivation; failure/advancement rules.
2. **Executed bytes:** launcher/rehearsal, evaluator, report, monitor/recovery/integrity tools and actual transitive source closure: model/trainer/optimizer/FLOP counter, builders, tokenizer/generators, loaders and imported/frozen helpers. Include required preflight/test sources and authorized validation evidence. Git revision alone is insufficient.
3. **Recipes/environments:** all resolved CLI/config/defaults; 79,748-parameter plain/shared model, optimizer/loss/learning-rate settings, both exact schedules, B/tolerance/caps/log cadence; sections 4–5's environments, image digest and dependency inventory. No placeholders.
4. **Roster/streams:** 48 pair IDs/96 jobs/arms; initialization/training/data/evaluation/diagnostic seeds and substream derivations; historical-seed exclusion inventory/collision evidence; disjoint rehearsal assignments; expected paired initialization/preflight stream digests and digest procedure. Append actual job state/stream digests later for identity checks.
5. **Evaluation inputs:** actual fresh seed-specific six-cell and 512-world READS panel bytes/manifests, world/twin/unit identities, labels/scoring definitions, native inference/legacy-selector-N/A policy, generator provenance and 09's complete reuse-key schema. Seeds alone are insufficient. Future checkpoint hashes are appended when generated.
6. **Operations:** exact pair/box/GPU/wave/order map, concurrency/evaluation queue/natural-tail policy, fresh output paths and artifact inventory/schema, retry/supersession/replacement rules, monitoring allowlist, exposure log and outcome-release procedure.
7. **Admission/custody:** both boxes' rehearsal evidence, conservative C/f/e/s and complete T, itemized quotes and $2-exception comparison if needed, accrued/projected costs including retry contingency, copy/teardown reserve and enforced $2.50 cutoff, local destinations and copy/hash-verification procedure.

> Store the manifest's own hash in a separate timestamped freeze record before learning, with an independent local copy. Generated artifacts/incident addenda reference that hash without rewriting the freeze. Check deployed source/config bytes before each start. A late source/config fix cannot silently continue this comparison.

**CONTRACT — AFTER copy-back and BEFORE destroying instances:**

> Match local byte sizes/SHA-256 to remote inventories for the freeze, executed source/environment records, canonical checkpoints, complete logs/phase/FLOP/time records, panels/manifests, evaluation rows and paired world-unit outcomes for bootstrap, integrity/reuse records, every available failed/superseded attempt, incident/exposure/attempt locks and cost ledger. Explicitly account for lost bytes. Through the blinded checker verify roster completeness, initial/stream identities, budget-stop AND budget_ok, caps, source closure and evaluation provenance. Preserve original paths and copy mapping; do not rewrite saved identities.
>
> With rental evaluation, copy and validate all canonical evaluation/integrity records before teardown. With Mac evaluation, teardown may precede evaluation only after all 96 canonical training checkpoints and required inputs/source/metadata are locally verified, with a second verified local checkpoint copy and no remaining rental dependency. Status stays **evaluation pending**, outcomes sealed; pending/invalid evaluations cannot advance.
>
> Copy verification precedes voluntary teardown, but cannot extend the spending limit. Reserve time/cost for it; if integrity remains unresolved at the cutoff, terminate paid work and record a non-advancing failure. Record teardown confirmation and reconcile final billed charges when available.
