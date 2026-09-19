# Opus handoff: build binding controls, then conditional H1 training

**Current delegation: Opus through Claude Desktop, controlled by the lead.** Ben's final instruction supersedes Luna delegation. This file is ready for lead dispatch; the synthesis editor has not sent it or activated training.

Workspace: `/Users/ben-hannan/Desktop/projects/beautiful-model`. Opus implements; the lead directs/reviews. Once delivered as instructions, this replaces the overlapping [pool prompt](/Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-final-sweep-next-experiment.md), with no parallel budget. Preserve any active job. Reconcile ownership, processes, artifacts, and cumulative ledger first.

**Current snapshot, 19 September:** Claude's “Opus execution correctness review” is idle at the overnight completion. [card_pools.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/card_pools.py) already defines mean/separate writers and bypass variants, with distinct identities and RNG-preserving initialization. Six focused tests exist and were reported passing overnight; no fresh execution occurred here. No pool harness, trained pool results, or H1 option was found.

The lead reports Luna interrupted. `premonition/paired_objectives.py` and matching test files were absent at inspection, but recheck before writing. If partial Luna files appear, inspect/hash/preserve them; do not overwrite, delete, or recreate them. Confirm no writer remains before integrating them. Absence in this snapshot is not a lock.

**One budget across both stages:** proposed **1,800 seconds total local experimental compute**, including all training arms, baselines, calibration, probes, evaluations, checks, failures, and reruns. Never 30 minutes per stage. Local Mac only; no rental, BensPC, paid services, further agents, or external messages. Carry forward work already charged to an activated overlapping handoff; never reset its ledger silently. Before running, allocate the remaining budget and predeclare comparisons, seeds, exposure, and stopping rules. If meaningful completion cannot fit, stop incomplete and report what remains.

**Stage 1 — integrate and evaluate the existing pool controls.**

Reuse existing writers through new `scripts/premonition_pool_controls.py` and `tests/test_premonition_pool_controls.py`, after checking those paths remain free. Import the current ladder/retrieval paths; leave existing model, trainer, writer, and overnight scripts unchanged. Preserve defaults and checkpoint compatibility; record writer/source/config identities, costs, and checkpoint reconstruction.

Keep these comparisons separate:

- **Answer-only supplied-card choosing:** original versus contextual mean, identical supplied cards and answer cross-entropy. No separate-pool third arm: its unused retrieval key adds no answer pathway.
- **Evidence-supervised retrieval:** original versus mean versus separate pools, with identical answer/evidence/ASK/HALT objectives, bypass architecture, initialization, curriculum, data/card ordering, optimizer, top-1 retrieval, four fixed loops, and no teacher distractors. Label evidence privilege explicitly.

Mean aggregates the same contextual reader states over identical line boundaries. The current model inserts **value + age + row type**, not retrieval keys, into decoder-visible card rows. Existing entity-slot binding is indirect and does not guarantee card-specific identity. Preserve this issue in interpretation: split pools can improve addressing without fixing choosing. Do not add key exposure, extra rows, new controllers, or semantic-role labels in this comparison.

Inspect completed runs first. Reuse accepted evidence/checkpoints only with compatible source, tokenizer, preprocessing, data, architecture, objective, seed, exposure, and selection identities. Never rerun a completed compatible arm merely for this handoff; unmatched historical results remain context.

Measure gold/no-fetch reading, decoy choosing, own-retrieval accuracy, evidence coverage, and second-fetch person/relation separately. Include relevant-pair both-correct, invariant-pair both-correct, and card-removal diagnostics. Probe scores alone cannot establish usable binding.

**Stage 2 — independently switchable H1, only after adequate readable representations.**

Proceed only when validation supports a usable decoder-visible identity/value path and reliable single-fact reading, yet choosing remains weak. Predeclare that behavioral gate; probe recovery alone is insufficient. Hold the selected writer/reader architecture fixed. If representations remain unreadable, report the blocker and stop this stage.

Add a default-off H1 training option with recorded coefficients and data identity. Use single-token answers initially. Generate verified complete-world triplets for one fixed question: original `x`; irrelevant sibling `u` with answer `a` unchanged; relevant sibling `v` with answer `b≠a`. Include subject-value swaps preserving the word inventory: Mira blue/Oren red becomes Mira red/Oren blue. Keep wording fixed, balance bindings, and preserve composition exclusions.

Every example receives CE. Add:

`Δ = log[p_x(a)/p_x(b)] − log[p_v(a)/p_v(b)]`

`L = CE(x)+CE(u)+CE(v)+λ JS(p_x,p_u)+μ max(0,m−Δ)`

Use consistent CE normalization in both arms. The essential control is **grouped CE on exactly the same examples, targets, minibatches, initialization, and schedule**, versus grouped CE plus H1. Shuffled CE on the same examples is optional only if budget remains. Fix coefficients on development data within the ledger. Pair roles, oracle bridge labels, evidence IDs, and change flags stay loss-side metadata, never model inputs or inference rewards. Score both-correct changed and invariant pairs, not agreement alone. H1 cannot directly train detached top-k scores or binary ASK; shared-feature effects are indirect.

**Focused checks Opus must run:** pooling initialization/RNG preservation, uniform contextual mean and padding boundaries, retrieval/value gradient separation, variant checkpoint identity round-trip; verified triplet labels and constant-wordbag swaps; exclusion of labels/structural metadata from inputs; H1-off grouped-CE loss/gradient parity; finite losses and gradients on extreme logits; constant answers failing changed-pair metrics. Charge execution to the same ledger.

Freeze source/data before comparisons. Preserve label-free/cache-v2 and exact tokenizer identities, original baselines, fingerprinted `read_only`, visit-clustered paired uncertainty, and `full_verdict: false`. Primary preferences require three precommitted finalist seeds and adequate project-margin bounds; small screens may remain inconclusive. Keep test out of selection. Defer shared-reader/query reuse and H2 until choosing is reliable; no architecture bundle.

Deliver source/data/checkpoint identities, exact ledger, all results including failures, passed/failed gates, and one next-step recommendation. Implemented, tested, trained, and validated are separate statuses; report them separately.
