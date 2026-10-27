# Canonical operator screen: rulings and prospective design

20 September 2026 UTC. **Design only; no new model, panels, training or evaluation have been run.** This responds to Fable's audit of [note 16](16-transfer-diagnostic.md). Numeric predictions and pass marks are fixed in [PREDICTIONS.md](../../artifacts/astra-canonical-operator-screen-20260920/PREDICTIONS.md). Implementation and training await Ben's explicit go, as requested in the handoff. This is a Track A toy screen.

**Ruling.** Accept the central objection. Successful canonical calls would establish that a learned lookup works inside a supplied program. At the operator interface, the held-out two-hop relation is an ordinary trained one-hop relation. Three calls test reuse at an untrained program length, but the third application is still chosen by the controller. Neither result demonstrates that the model discovered composition. The new LINK output is a substantive learning risk; shared-weight interference, errors passed between calls and larger memories are additional risks.

**Shown — chronology correction.** The follow-up registration was saved at **2026-09-20 02:08:49 UTC**, after **all six** primary result files existed; the last was saved at **02:08:17 UTC**. These are September 19, 22:08:49 and 22:08:17 EDT. Note 16's “after B0's initial result” understates this chronology. The follow-up text says only B0 had been read; filesystem timestamps cannot verify what was read. It remains a separately registered follow-up preceding its own runs. This is an additive erratum: retain the original report, prediction files, manifests and their historical hashes unchanged, including the old report hash in `final-verification.json`.

The original prediction and manifest SHA-256 values were independently rechecked and match the audit: `4b864c3920800738cac958f4e71c13dbdba2a74d27837a5ba5dcad847b90b20f` and `0349a82d2928491e31fabba09012e98b6a791900891441684a67678a2ff07354`. The accepted six-checkpoint diagnosis and its failed universal predictions stand. No new causal localisation claim is added here.

**1. Accept three-hop and 12-person admission requirements, with a narrower interpretation.** Every cell has 512 units. All thresholds apply separately to every seed; averages cannot rescue a failure.

| Cell | Evaluation | Required correct units |
| --- | --- | --- |
| c1 | Fresh six-person one-hop | 487/512 |
| c2 | Fresh six-person practised two-hop | 487/512 |
| c3 | Fresh six-person held-out two-hop | 461/512 |
| c4 | Fresh held-out changed-link pairs | 461/512 pairs, both answers correct |
| c5 | Fresh held-out changed-endpoint-value pairs | 461/512 pairs, both answers correct |
| c6 | Fresh held-out irrelevant-edit pairs | 461/512 pairs, both correct and identical |
| s3 | Existing three-hop held-out stress | 461/512 answers; also 461/512 complete correct entity paths and answers for the controller arm |
| p12-1 | Existing 12-person one-hop stress | 487/512 |
| p12-2 | Existing 12-person practised two-hop stress | 487/512 |
| p12-3 | Existing 12-person held-out two-hop stress | 461/512 |

Training uses six-person worlds and questions of at most two hops. **Zero three-hop questions and zero 12-person worlds enter training**, including auxiliary losses. The 12-person test uses the same existing 16 entity IDs; it is a test of more people/facts, not unseen vocabulary. The three-hop test adds both a LINK and a new question length. Retain the existing stress files byte-for-byte; their outcomes were already known, so they are reused benchmarks with new prospective acceptance rules, not newly blinded evidence. Also report three-hop results split by whether the second link returns to the original asker; do not change the panel or exclude those cases.

For controller execution, require each autonomous LINK stage to predict the true entity in at least 487/512 questions on every applicable cell/side. An early abort counts as wrong at all missing stages. Also require canonical terminal accuracy given the true endpoint of at least 487/512 on each applicable cell/side. Report LINK accuracy with gold input separately at every stage, and full native intermediate/answer joint counts. These oracle-input diagnostics cannot substitute for an autonomous answer or pair pass. Score the common checkpoint's canonical diagnostics once and attach them to both inference arms; the monolithic arm has no emitted intermediate path at inference, so its native path score is **not applicable**, not inferred from attention.

The raw cutoffs are roughly 95% and 90% screening criteria, not confidence-bound certifications. No G_pair or G_cert claim is attached to them.

**Panel freshness correction.** Seeds **202609202001–2004 already occur** in the old [stress manifest](../../artifacts/codex-token-memory-20260920/stress/manifest.json). Keep the requested integer seeds 202609202001–2006 for fresh c1–c6, but use a new, explicitly frozen RNG namespace:

```text
random.Random("canonical-operator-screen-v1:{cell}:{seed}:{unit_index}")
```

Here `{cell}` is the full c1–c6 key in `premonition_pair_suite.CELLS`, `{seed}` is its corresponding requested integer, and `{unit_index}` runs from 0 to 511. Generate with the existing single/pair construction semantics and a new additive wrapper; do not change the registered generator. This is a different effective RNG seed, not a claim that the integer suffix alone is unused. Before training, audit answers, edits, eligibility, duplicate units and overlap with the relevant old panels, comparing canonicalized visible facts/question semantics as well as tensor content. Freeze panel files, hashes, source closure and the audit. Any cross-panel duplicate aborts preparation for an explicit amendment; no outcome-driven resampling. During the fixed training stream, check semantic overlap with these panels without consulting their targets; an overlap invalidates the run, rather than silently skipping a training example. Exact overlap checks do not establish independence of underlying generation processes.

**2. Accept a label-matched control, with common composition training.** A control trained only on six canonical queries and then asked to answer full compositions would face a new inference format. Its failure would not isolate the controller. Therefore amend the training recipe for **both** arms before comparing them:

| Training records per visit | Count | Supervision |
| --- | --- | --- |
| Original one-hop questions, in canonical form | 2 | Value plus sole supporting line |
| LINK questions derived from practised two-hop questions | 2 | Intermediate entity plus link line |
| Terminal questions derived from those practised two-hop questions | 2 | Value, gold entity as input, endpoint line |
| Original practised two-hop questions in their full monolithic form | 2 | Final value plus ordered link/endpoint/endpoint evidence |

The first six records are exactly the proposed canonical examples. The last two teach the control its normal composed input format and are present with identical weighting in the controller arm. There are eight records, not ten: original one-hop questions are not duplicated again. All eight use the original shared 68-token output; no intermediate classifier or additional trainable head is introduced. Intermediate entity supervision is supplied through the same canonical LINK records in both arms.

For each record, use answer cross-entropy plus 0.5 times evidence loss. Evidence loss is the mean negative log supporting-line attention mass over three internal read steps, averaging heads at the final question row before taking the log, as in the existing evidence objective. Canonical records repeat their sole line three times; monolithic two-hop records use link/endpoint/endpoint. **The total loss is the mean of all eight record losses**, with no extra loss or reweighting by arm.

Use identical initialization, world stream, optimizer, updates and targets for both inference arms:

- **R (recursive execution):** generic controller and fresh canonical call for each operation.
- **M (monolithic control):** one unchanged `TokenMemoryReasoner.forward` on the original question, with its original three internal reads and anchor. No intermediate re-query or reset between internal reads.

Because training is identical, the cheapest and strongest match is **one trained checkpoint per seed, evaluated under both policies**. That gives three seeds per arm, with three total training trajectories, not six independent weight samples. Count shared training cost once; do not present six fits or six independent successes. Independently repeating an identical deterministic fit would add no experimental contrast. The sole within-seed intervention is inference policy, including its parsing, reset and additional calls. Both arms receive precisely the same learned competence and supervision.

This changes note 16's standalone six-example recipe to a common eight-example recipe. It intentionally gives up a test of that original training recipe in exchange for an interpretable control. Any interference caused by the common composition loss is part of this registered candidate; a failure cannot trigger removal of that loss and reuse of the same results as confirmation.

**Predeclared reading.** Report both arms on every cell and the paired per-world/pair gain, loss and net difference for each seed. R passes only if all answer, native-path, diagnostic and integrity requirements pass in all three seeds. M's answer screen uses the same ten answer cutoffs; native intermediate-path requirements do not apply to its single-output interface.

| Result | Permitted conclusion |
| --- | --- |
| R passes, M fails | The supplied inference policy makes this common trained system cross the screen; it does not show learned decomposition. |
| Both pass | The common training recipe supports monolithic transfer too; the controller is not required to cross this screen. This does not isolate the new labels from all other changes versus historical B/C. |
| R fails, M passes | Reject this recursive candidate; retained intermediate and terminal diagnostics may localize its failure. |
| Both fail | Neither policy meets the screen under this recipe and budget. More training accuracy or gold-endpoint accuracy is insufficient. |
| Any missing/incomplete seed or integrity failure | The planned comparison fails to complete; retain partial results without a successful-arm comparison claim. |

Separately predict a **substantial policy advantage**: R minus M at least **52/512 net correct units** on each of c3, c4, c5, c6 and s3, in each seed; R must also pass its absolute screen, with no more than **5/512** net harm on c1 or c2. Keep this prediction separate from absolute sufficiency. If only some cells or seeds meet it, the universal advantage prediction fails. These are descriptive, prospectively chosen effect sizes, not a population-level significance claim.

**3. Accept a generic executor; reject the claim that it eliminates grammar privilege.** For a visible question `[question, subject, op_1, ..., op_k, answer]`:

```text
x = subject
for each op in the visible left-to-right token sequence:
    t = full_68_token_argmax(F(memory, [question, x, op, answer]))
    if unread operation tokens remain:
        if t is not an entity token: fail this question
        x = t
    else:
        return t
```

There is no branch for LINK, relation 2, two hops or three hops. The same procedure makes one, two or three calls as dictated by the visible operations. Malformed questions or early non-entity outputs fail without repair; the final token is scored as emitted, including invalid types. There is no entity-only argmax, value-only argmax, truth-dependent fallback or beam search.

**Declared executor privileges:** delimiter recognition and padding removal; the first body token is the initial subject; all remaining body tokens are operations in execution order; the static entity-token class (IDs 52–67, all 16 IDs, not only people present); whether unread tokens remain; exact query formatting; token passing and reset; and a shared story with the original causal eligibility. It does not parse story facts, choose supporting lines, receive gold entities or decide which operation should be next. It still supplies the sequence semantics and continuation rule. Call it generic over this tokenized path grammar, not a learned parser or grammar-free reasoner.

Each call initializes its own question encoder, anchor and recurrent state. Retain the existing 79,316-parameter module, width 48, four heads, three internal reads and full vocabulary; use one module repeatedly. Initially re-encode story memory on each call to keep isolation simple, and charge that computation. Caching is deferred to a separate parity-checked change.

**Precise leakage contract.** “No terminal REL or asker in either call” cannot be literal: the first call needs its subject, and the final call needs its requested REL. The contract is that the operator receives **only story, owner/causal eligibility and the four current query tokens**. A LINK call cannot receive any unread terminal REL, question length/depth, previous anchor or hidden state. Later calls cannot receive the original question/asker through an extra channel; they receive the preceding emitted entity, which may legitimately equal the asker on a cycle. The unchanged story naturally contains all its people and relations. No query-dependent story filtering, depth-conditioned steps, original-question padding width or retained question rows may smuggle context into the canonical call. All canonical queries have width four.

Required implementation checks, before training: +0 parameters and unchanged state-dict schema; identical input tensors and logits for first LINK calls across matched terminal-REL variants and depths; exact equivalence of any call to a standalone canonical query on the same story/entity/op; fresh anchors/states per call; no carried latent state; full-vocabulary behavior under injected non-entity outputs; every eligible fact retained and labels absent from inference; exact eight-record training accounting and absence of held-out compositions, three-hop or 12-person training. These are **untested requirements**, not verification already performed on a new implementation.

**4. What the strongest outcome would mean for Ben.** If R passes every seed, edit, three-hop and larger-world requirement, and beats the label-matched M control, we would have shown that a small learned lookup can be reused reliably on this toy when a supplied program organizes its calls, including at a program length never trained. That is useful evidence of a reusable component and of the effect of the supplied execution policy. It would not show that the model learned how to break a question into steps, chose those steps, learned when to stop, or transfers broadly beyond this grammar and vocabulary. Even success is not evidence of general intelligence. If M also passes, that is additional evidence of monolithic transfer under stronger supervision, whose scope must be reported separately.

**Next harder test — design only.** Freeze a successful lookup operator and train a small learned dispatcher that receives the full raw question and its own prior query/result transcript. It must emit the subject and operation for the next sub-query and choose CONTINUE or STOP. The executor only validates actions, calls the frozen operator and returns its result; it must not slice out the next operation, maintain an oracle unread-token pointer, choose a subject or terminate according to question length. Give the dispatcher no direct story access: facts are available through its chosen queries. At STOP, return the latest lookup token. Use a uniform four-call maximum for all questions, with exceeding the cap counted as failure. Freeze the operator, disclose the dispatcher's added parameters and train from final-answer feedback on one-hop and practised two-hop examples only, without gold action sequences, intermediate entities or evidence targets. A learned stop bit on top of the present fixed parser would be a weaker test and would not meet this proposal.

The cheapest decisive next check is a bounded dispatcher pilot, not retraining the lookup: three fixed seeds, at most 6,000 dispatcher updates each and the same local CPU/wave caps, with an independently registered training method before launch. On new 64-unit panels require, in every seed, **61/64** one-hop and practised two-hop answers; **58/64** held-out two-hop answers; **58/64** three-hop held-out answers with all three entities/values queried in the correct chain and a learned stop after the third result; and **58/64 pairs** on each of changed-link, changed-value and irrelevant-edit three-hop checks. Use distinct-person three-hop chains here to exclude two-link cycles. Zero three-hop training and no action supervision. The required answer is whether the learned dispatcher chooses the new-length procedure from the question and follows changed facts, without an executor that specifies its decomposition. Passing would support learned composition over a supplied tool interface, still not general intelligence. Pilot failure rejects that attempt; it does not prove impossibility. No dispatcher implementation or run is authorized by approval of the current screen alone.

**5. Budget and launch contract.** Confirm local CPU only; no GPU, remote run or paid compute. Use the installed project runtime, seeds 0–2 for initialization and the existing `random.Random(1101)` training stream, 16 visits per update and exactly 6,000 updates per common checkpoint. Preserve the stream's extra `rng.randrange(1 << 30)` after each batch so it matches the current evidence runner. Use the existing scaled linear initialization and AdamW: learning rate 0.001, 100-update linear warmup, betas (0.9, 0.99), epsilon 1e-8, weight decay 0.1, gradient clipping at 1.0. No scheduler or loss changes after outcomes.

Use three sequential seed waves, each fitting one checkpoint and evaluating both policies. Each process uses one Torch compute thread and one inter-op thread. Set a **1,200-second training cap**, a **1,740-second work deadline** including evaluation and artifact checks, and an external **1,770-second termination deadline** including cleanup, measured from wave launch. Thus each wave must finish in under 30 minutes; the three-wave maximum is 88.5 minutes, not a promise that the full screen takes under 30 minutes. A stopped training run, missing final score or missing final verification fails the entire screen; retain partial data, with no resume, replacement seed or checkpoint selection. Build and panel preparation also use bounded work waves; any unfinished required launch check prevents training.

Historical C training took about 498–502 seconds per 6,000-update seed with four questions per visit. That is measured historical timing, not a measurement of this eight-record recipe or recursive evaluation. Do not promise “ten extra minutes” or inherit the old FLOP ceiling silently. Record actual matmul FLOPs for each training and inference path, operator call counts, wall time and peak memory. Training is shared and equal by construction across the two inference policies; inference computation differs. There is no equal-total-compute claim or comparison to historical budgets.

After Ben's go, add new model/adapter, runner and tests under `astra_canonical_operator` names; do not edit existing registered code, plans or artifacts. Freeze launch sources, runtime versions, this design's hash, predictions and all panels/audits in a new manifest **before training**. Score only the final update-6,000 checkpoint, once per policy and panel; no validation-based choice or early stopping. No `test.pt` is loaded. Save every seed's per-unit predictions, emitted-token trajectories, pair outcomes, diagnostics, counts, costs, model fingerprints and source/panel/checkpoint hashes. Report all six arm/seed rows, including failures, using shown / suggested / untested, in an append-only results addendum to this note; the launch manifest should retain a separate immutable copy of this pre-run design so the report can grow without invalidating registration.

**Current status:** R0, R1, R2, M0, M1 and M2 are all **untested**. Only source/document inspection, historical JSON reads and file-integrity checks were performed in this turn. The runtime and interference risks remain open.


## Append-only execution addendum — 20 September 2026 UTC

**Shown.** Predeclared reading: **Both fail**. P1: **FAIL**; P2: **FAIL**. P3 implementation checks passed before launch; they are construction checks, not learned-transfer evidence.

**Shown.** Three common checkpoints supply six inference-arm rows. All-complete: True. The parallel model-execution wave took 899.918 seconds; source/panel/checkpoint integrity and final-checkpoint-only evaluation were checked. This independent model-free report reconstructed 19,968 side records against panel truth.

| Arm/seed | c1 | c2 | c3 | c4 | c5 | c6 | s3 | p12-1 | p12-2 | p12-3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R0 | 414 | 414 | 370 | 277 | 300 | 344 | 368 | 300 | 319 | 225 |
| R1 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 |
| R2 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 | 512 |
| M0 | 414 | 374 | 40 | 0 | 2 | 30 | 33 | 300 | 209 | 30 |
| M1 | 512 | 512 | 52 | 0 | 20 | 51 | 36 | 512 | 512 | 44 |
| M2 | 512 | 512 | 76 | 23 | 48 | 91 | 38 | 512 | 511 | 61 |

All denominators above are 512. c4–c6 count complete pairs. Raw thresholds: c1/c2/p12-1/p12-2 ≥487; all other answer cells ≥461. No averaging across seeds.

**Shown — paired policy changes.** Each entry is R-only correct / M-only correct (net R−M).

| Cell | Seed 0 | Seed 1 | Seed 2 |
| --- | --- | --- | --- |
| c1 | +0/−0 (+0) | +0/−0 (+0) | +0/−0 (+0) |
| c2 | +76/−36 (+40) | +0/−0 (+0) | +0/−0 (+0) |
| c3 | +343/−13 (+330) | +460/−0 (+460) | +436/−0 (+436) |
| c4 | +277/−0 (+277) | +512/−0 (+512) | +489/−0 (+489) |
| c5 | +299/−1 (+298) | +492/−0 (+492) | +464/−0 (+464) |
| c6 | +326/−12 (+314) | +461/−0 (+461) | +421/−0 (+421) |
| s3 | +340/−5 (+335) | +476/−0 (+476) | +474/−0 (+474) |
| p12-1 | +0/−0 (+0) | +0/−0 (+0) | +0/−0 (+0) |
| p12-2 | +156/−46 (+110) | +0/−0 (+0) | +1/−0 (+1) |
| p12-3 | +212/−17 (+195) | +468/−0 (+468) | +451/−0 (+451) |

**Shown — intermediate diagnostics.** Each side has 512 questions. L = autonomous LINK correct counts; O = gold-input LINK correct counts; T = gold-endpoint terminal correct; J = complete autonomous entity path and answer. These canonical diagnostics belong to the shared checkpoint; M has no native emitted path.

| Seed | Cell/side | L | O | T | J |
| --- | --- | --- | --- | --- | --- |
| 0 | c1/a | — | — | 414 | 414 |
| 0 | c2/a | 501 | 501 | 424 | 414 |
| 0 | c3/a | 501 | 501 | 377 | 368 |
| 0 | c4/a | 494 | 494 | 381 | 368 |
| 0 | c4/b | 498 | 498 | 390 | 379 |
| 0 | c5/a | 499 | 499 | 385 | 374 |
| 0 | c5/b | 499 | 499 | 371 | 360 |
| 0 | c6/a | 502 | 502 | 376 | 367 |
| 0 | c6/b | 502 | 502 | 382 | 373 |
| 0 | s3/a | 497, 490 | 497, 501 | 379 | 362 |
| 0 | p12-1/a | — | — | 300 | 300 |
| 0 | p12-2/a | 472 | 472 | 339 | 311 |
| 0 | p12-3/a | 461 | 461 | 233 | 214 |
| 1 | c1/a | — | — | 512 | 512 |
| 1 | c2/a | 512 | 512 | 512 | 512 |
| 1 | c3/a | 512 | 512 | 512 | 512 |
| 1 | c4/a | 512 | 512 | 512 | 512 |
| 1 | c4/b | 512 | 512 | 512 | 512 |
| 1 | c5/a | 512 | 512 | 512 | 512 |
| 1 | c5/b | 512 | 512 | 512 | 512 |
| 1 | c6/a | 512 | 512 | 512 | 512 |
| 1 | c6/b | 512 | 512 | 512 | 512 |
| 1 | s3/a | 512, 512 | 512, 512 | 512 | 512 |
| 1 | p12-1/a | — | — | 512 | 512 |
| 1 | p12-2/a | 512 | 512 | 512 | 512 |
| 1 | p12-3/a | 512 | 512 | 512 | 512 |
| 2 | c1/a | — | — | 512 | 512 |
| 2 | c2/a | 512 | 512 | 512 | 512 |
| 2 | c3/a | 512 | 512 | 512 | 512 |
| 2 | c4/a | 512 | 512 | 512 | 512 |
| 2 | c4/b | 512 | 512 | 512 | 512 |
| 2 | c5/a | 512 | 512 | 512 | 512 |
| 2 | c5/b | 512 | 512 | 512 | 512 |
| 2 | c6/a | 512 | 512 | 512 | 512 |
| 2 | c6/b | 512 | 512 | 512 | 512 |
| 2 | s3/a | 512, 512 | 512, 512 | 512 | 512 |
| 2 | p12-1/a | — | — | 512 | 512 |
| 2 | p12-2/a | 512 | 512 | 512 | 512 |
| 2 | p12-3/a | 512 | 512 | 512 | 512 |

**Shown — three-hop asker-cycle split.**

| Seed | Chain | n | R | M | Native joint |
| --- | --- | --- | --- | --- | --- |
| 0 | distinct_chain | 408 | 294 | 22 | 289 |
| 0 | asker_cycle | 104 | 74 | 11 | 73 |
| 1 | distinct_chain | 408 | 408 | 30 | 408 |
| 1 | asker_cycle | 104 | 104 | 6 | 104 |
| 2 | distinct_chain | 408 | 408 | 28 | 408 |
| 2 | asker_cycle | 104 | 104 | 10 | 104 |

**Shown — costs.** FLOPs count actual padded/compacted matmuls under the existing convention, validated against Torch instrumentation before training. Elementwise operations, optimizer arithmetic and file I/O are excluded from FLOPs. Policy seconds time their forwards; total job/wave time includes training, audits and I/O. Peak RSS is per process. Shared training is charged once.

| Seed | Updates | Train seconds | Train FLOPs | Job seconds | Peak RSS bytes |
| --- | --- | --- | --- | --- | --- |
| 0 | 6000 | 860.287 | 17118733418496 | 897.2415026660019 | 566755328 |
| 1 | 6000 | 859.547 | 17118733418496 | 896.4542334169964 | 577208320 |
| 2 | 6000 | 861.801 | 17118733418496 | 898.7189747909724 | 573341696 |

| Seed | Policy | Seconds | FLOPs | Question calls | Batched forwards |
| --- | --- | --- | --- | --- | --- |
| 0 | R | 13.938 | 335833620480 | 12800 | 400 |
| 0 | M | 7.543 | 179714795520 | 6656 | 208 |
| 0 | oracle | 13.915 | 335833620480 | 12800 | 400 |
| 1 | R | 13.941 | 335833620480 | 12800 | 400 |
| 1 | M | 7.530 | 179714795520 | 6656 | 208 |
| 1 | oracle | 13.895 | 335833620480 | 12800 | 400 |
| 2 | R | 13.893 | 335833620480 | 12800 | 400 |
| 2 | M | 7.492 | 179714795520 | 6656 | 208 |
| 2 | oracle | 14.016 | 335833620480 | 12800 | 400 |

**Shown — failures retained.**

- R0 c1: 414/512 < 487
- R0 c2: 414/512 < 487
- R0 c3: 370/512 < 461
- R0 c4: 277/512 < 461
- R0 c5: 300/512 < 461
- R0 c6: 344/512 < 461
- R0 s3: 368/512 < 461
- R0 p12-1: 300/512 < 487
- R0 p12-2: 319/512 < 487
- R0 p12-3: 225/512 < 461
- M0 c1: 414/512 < 487
- M0 c2: 374/512 < 487
- M0 c3: 40/512 < 461
- M0 c4: 0/512 < 461
- M0 c5: 2/512 < 461
- M0 c6: 30/512 < 461
- M0 s3: 33/512 < 461
- M0 p12-1: 300/512 < 487
- M0 p12-2: 209/512 < 487
- M0 p12-3: 30/512 < 461
- seed 0 c1/a terminal oracle: 414/512 < 487
- seed 0 c2/a terminal oracle: 424/512 < 487
- seed 0 c3/a terminal oracle: 377/512 < 487
- seed 0 c4/a terminal oracle: 381/512 < 487
- seed 0 c4/b terminal oracle: 390/512 < 487
- seed 0 c5/a terminal oracle: 385/512 < 487
- seed 0 c5/b terminal oracle: 371/512 < 487
- seed 0 c6/a terminal oracle: 376/512 < 487
- seed 0 c6/b terminal oracle: 382/512 < 487
- seed 0 s3/a terminal oracle: 379/512 < 487
- seed 0 p12-1/a terminal oracle: 300/512 < 487
- R0 p12-2/a native LINK 1: 472/512 < 487
- seed 0 p12-2/a terminal oracle: 339/512 < 487
- R0 p12-3/a native LINK 1: 461/512 < 487
- seed 0 p12-3/a terminal oracle: 233/512 < 487
- R0: three-hop native joint gate failed
- seed 0: P2 substantial-policy-advantage prediction failed
- M1 c3: 52/512 < 461
- M1 c4: 0/512 < 461
- M1 c5: 20/512 < 461
- M1 c6: 51/512 < 461
- M1 s3: 36/512 < 461
- M1 p12-3: 44/512 < 461
- M2 c3: 76/512 < 461
- M2 c4: 23/512 < 461
- M2 c5: 48/512 < 461
- M2 c6: 91/512 < 461
- M2 s3: 38/512 < 461
- M2 p12-3: 61/512 < 461

**Suggested — interpretation.** Neither execution policy meets the complete registered screen. Retain any local successes without promoting them to full sufficiency.

**Untested.** Learned decomposition and the dispatcher remain untested. No dispatcher was built or run. No broad intelligence, equal-total-compute or certification claim follows.

Artifacts: [launch manifest](../../artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_launch.json), [pre-launch amendment](../../artifacts/astra-canonical-operator-screen-20260920/astra_canonical_operator_PRE-LAUNCH-AMENDMENT.md), [raw seed folders and verification](../../artifacts/astra-canonical-operator-screen-20260920/).
