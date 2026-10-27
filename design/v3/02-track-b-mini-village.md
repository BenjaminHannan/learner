# Track B — a persistent, parser-assisted mini-village

**Untested — specification.** This file defines a new finite-horizon task. It is not the existing legacy village evaluation and does not inherit any toy success. [Final amendments](07-final-resolution.md) govern the original ledger, including the change from cached-logit distillation to record-derived retrieval practice.

## World and language contract

One training stream interleaves visits to continuing worlds. A pilot world has eight people, three single-valued relations (`friend`, `shoes`, `location`), sixteen visits and four new observations per visit after an initial introduction/fact visit. Values are sampled independently of names and world IDs. Persistent state lives between visits; a visit does not recreate a random first world. Use the existing village simulator's state transition primitives behind a new continuing-world scheduler, but do not treat the current `shards.world_visit` path as persistent.

The initial diagnostic milestone uses fixed, explicit wording. Visible observations include a world header, a monotonically increasing observation number, source, effective tick and optional assertion/correction reference. Example:

```
World cedar-17.
Introduction 1: Mira, the baker.
Introduction 2: Oren, the potter.
Record R1, registry, observed 1: from tick 0, Mira's friend is Oren.
Record R2, registry, observed 2: from tick 0, Oren's shoes are blue.
Record R3, registry, observed 3: correction to R2, from tick 0, Oren's shoes are red.
```

First evaluate “What colour are Oren's shoes at tick 0, using what is known now?” Then add “What colour were they believed to be at observation 2?” These ask different questions: red and blue respectively. A true change “from tick 4 … green” leaves earlier effective-time truth intact; a correction replaces an earlier assertion's validity for its declared interval.

The generator's transition mixture for the first version is frozen: 50% assertions/repeated facts, 20% true changes, 15% explicit retrospective corrections, 10% equal-authority unresolved contradictions, 5% explicit unknown/retractions. Generate templates independently of the target value. Record attempted versus actual transitions where preconditions require resampling. Intro/alias/namesake cases are fixed contract fixtures; their frequency is not tuned after seeing a score. The sequence introduces these capabilities one at a time; the complete contract is not permission to start with every difficulty at once.

## Observable identity and parsing

Entity identity is `(visible_world_namespace, visible_introduction_ordinal)`, created from the observed introduction event, never the simulator's internal person ID. Introductions bind a spelling plus visible descriptor. Later “Oren is also called Ori” joins aliases only with an unambiguous explicit reference. Two people sharing a name require descriptors; otherwise the parser returns `ambiguous`, never a guessed identity. A spelling hash only indexes mentions. Shuffled temporary ENT tags resolve through the observed per-visit mapping and cannot redefine identity. World namespace collisions fail admission.

The deterministic parser accepts the frozen grammar and returns zero, one or several observations:

`{status, source_span, world, entity_candidates, relation, qualifiers, value, effective_interval, observed_seq, source_id, assertion_ref, supersedes_ref}`.

Statuses are `ok`, `unresolved_reference`, `ambiguous`, `unsupported`, `malformed`. Pronouns are allowed only in a later grammar version with a declared visible antecedent rule; no simulator labels fill gaps. For each accepted fact, every field has a source span or a documented literal default such as open-ended valid time. Unsupported input is retained only if the fixed storage budget permits; it cannot become a training target.

Parser assistance supplies segmentation, fields, identity links, timestamps, question addresses and gold answer generation from **observed** records. It does not claim learned extraction, learned pronouns, learned temporal reasoning or autonomous entity discovery. Include these privileges in every result. The deterministic resolver's answers are a functional reference, not a neural achievement.

## Address, assertion and version semantics

Address is `(world, entity, relation, sorted_qualifiers)`, excluding the value. `friend/shoes/location` have empty qualifiers and one applicable value; events include an explicit event ID and multi-valued relations include an observed item/role qualifier. Hashes accelerate lookup but equality checks full fields.

A stored assertion contains address, value, source, source authority policy version, source assertion ID, observed sequence, valid-from/to ticks, local revision, supersedes/retracts reference, source span digest and encoder/index version. Local revisions count ingestions; they do not assert truth. Duplicate assertion IDs with identical bytes are idempotent; differing bytes are rejected as conflict. A correction referencing an unseen record stays unresolved until that reference arrives, and cannot silently overwrite an unrelated address.

Resolve in this order:

1. Filter to the named world/address and observations available by the query's observation cutoff.
2. Apply explicit retractions and corrections visible by that cutoff to their referenced assertions/intervals. Preserve the earlier observation-time view.
3. Select assertions applicable at the requested effective time. A late-arriving old fact does not replace a later effective-time state change.
4. Apply the declared authority order: registry above named witness above unverified report. Within one source, an explicit subsequent state change closes that source's earlier open interval. Equal-authority inconsistent sources remain a conflict unless an explicit authorized supersession resolves it. Observation arrival order alone is not a tiebreaker.
5. Return one supported value, `conflict`, `not_told`, or `history_unavailable`. Do not convert expired history into a statement that the fact never existed.

An authoritative correction guards answers immediately, before any weight update. Exact address/authority guards execute before neural ranking and again before final answer release. A missed neural candidate cannot authorize a stale weight answer.

## Bounded storage, eviction and retrieval

Pilot limits are 64 active addresses, 32 assertion payload slots of at most 512 serialized bytes each, and 64 guard entries of at most 128 bytes each, plus an 8 KiB identity/dictionary allocation and an 8 KiB index allocation: total 40 KiB logical persistent storage. Record actual serialized and resident bytes separately; Python overhead is not zero. The history stream creates more than 32 assertions, so retention faces real pressure. An experiment changing capacity keeps the same byte accounting and is a different condition.

Guards store address identity/revision, known correction state, whether current authority is available, and conservative history coverage (at most four intervals). They never silently store a second unlimited fact archive. Current correction assertions are protected while possible. Evicting an ordinary payload sets its coverage unavailable. If the current authoritative correction payload must be discarded, retain a `deny_weight_fallback` guard and answer unavailable until a new complete authoritative observation restores coverage. Do not remove this guard because one weights-only probe passed. Finite probes cannot guarantee the old answer will never return.

If coverage fragmentation exceeds four intervals, mark all uncertain history unavailable. If a new address would exceed 64 entries, or protected payloads exhaust capacity, set a world-level quarantine flag in the reserved header and abstain for affected unresolved queries. Stop consolidation from that world. Clear quarantine only through an explicitly observed authoritative refresh that rebuilds the bounded world state, not a hidden simulator reset. This is a finite-capacity contract; it does not promise indefinite exact history with bounded memory.

Run FIFO first for evictable payloads, then LRU and reservoir as separate retention-policy comparisons. All share exactly the same correction guards and protection rules. Reservoir samples eligible payloads, not protected metadata. Access does not change a fact's permission to become a training target. Surprise prioritization waits until predictive losses mean something and is outside the first sequence.

Initial retrieval is exact address lookup over this tiny index. A neural retriever is a later candidate-ranking layer using frozen embeddings and the same exact eligibility/version resolver; it never defines identity. Updating it requires a separately built complete new index, validation on retained records, and an atomic `(encoder, index, policy)` swap with rollback. Charge old+new peak storage during rebuilding; fit within a preregistered temporary-memory allowance or do not re-key. No lazy mixed-encoder index.

## Output sources and evaluation cells

Track B keeps a generative model capable of answering without cards. Use the existing plain village contender architecture as the starting family, recording its actual instantiated size and the pinned tokenizer in the future implementation; the old legacy runs' 5,549,824 parameters are not a promised new-model count. Do not substitute Track A's copy-only head.

Every answer carries one source label: `card_copy`, `weights_generate`, `authority_override`, `abstain`. Exact resolver answers and corrections count as card-assisted, even if the weight model happened to agree. A guard that blocks stale weights does not demonstrate repaired weights. Record proposed neural answer and released answer separately.

| Cell | Required behavior |
|---|---|
| Current | Latest applicable supported value under the trust policy |
| Historical truth | Value at effective tick t, using observations through now |
| Historical belief | Value at effective tick t, using observations only through cutoff s |
| Corrected | New authoritative value immediately; stale proposals counted separately |
| Never told | `not_told` with genuine absence of observed evidence |
| Wrong owner / wrong relation | Irrelevant matching value does not satisfy the address |
| Contradicted | Explicit conflict/abstention when equal-authority evidence conflicts |
| Outdated | Current question rejects a superseded value; historical question may require it |
| Evicted / overflow | `history_unavailable` or guarded abstention; no stale resurrection |
| Ambiguous identity | Resolve only with visible disambiguation, otherwise abstain |

## Online learning, fair replay, and the first consolidation candidate

**Suggested:** test version correctness before weight learning. Then ordinary replay is the reference to beat. Fable's stale-logit/storage objection is a good reason to defer cached-logit distillation; its stronger claim that distillation must be useless is untested. The selected first mechanism is **closed-book retrieval practice from versioned records**. It asks whether changing the learning presentation transfers observed facts into weights more effectively than ordinary replay. Call it a replay variant.

**Untested — matched protocol.** All three arms share the same initial model, observed stream, bounded store, eligible records, optimizer, wall/compute cap and fact sampling seeds. Budget by total measured/estimated FLOPs including parsing, generation, forward/backward, evaluation, checkpointing and maintenance. Report model FLOPs separately from CPU preprocessing time, not as interchangeable units. Save curves at 25/50/75/100% budgets.

- **Online-only:** updates on the current visit's observed material; at equal total update budget, repeat current material instead of accessing old examples. It still has the same inference store, whose bytes are counted.
- **Fair replay:** replace a fixed half of update target-token allocation with retained observations, stratified 50:50 current applicable facts and valid time-labelled history when both exist (otherwise the nonempty stratum). Sample uniformly within strata. Both this and the next arm see exactly the same sampled fact IDs in the same order. Reformat old false statements as historical belief or explicitly corrected text; do not train them as current truth.
- **Retrieval practice:** change only the presentation of those replay fact units: generate fixed-wording question/answer pairs, hide store/resolver/context during the model's forward pass, and train ordinary answer CE. The target comes from the same eligible observed record and its versioned resolver. Use current/history questions with explicit cutoffs. No teacher snapshot, cached logits, generated hidden facts or additional unique fact IDs.

Use the same number of **answer/value target tokens** and same fact exposures for replay and practice; statement replay masks loss to value tokens plus EOS, to avoid adding a language-loss confound. Both include equal current-visit learning. Pad both representations to the same declared maximum input/target lengths and count actual FLOPs; if implementation costs differ, compare at the lower common compute budget and publish exposure counts. Prefix differences are the intentional presentation change. Training-only question grammar is identical to the fixed evaluation grammar; held-out wording is a later claim.

Facts eligible for the first consolidation assay are stable, randomly valued, single-hop records. Randomly assign half within each world/relation to supplemental offline practice and half to holdback; counterbalance across paired replicas. Every fact receives identical awake exposure. The fair-replay control uses the same assignment and repeats the selected facts in statement form. The held-back facts receive no supplemental offline exposure in either arm. Record-derived historical and correction repair training comes only after this attribution assay works; do not mix repair with consolidation in one claimed result.

The primary effect is the practice-vs-replay difference in `(post−pre closed-book accuracy on selected facts) − (post−pre on held-back facts)`, clustered by independent training/world stream. Evaluate at matched delays and after unrelated learning to measure retention. Include twin worlds differing only in the tested value; a rise in generic answer preference is not memory of the assigned fact.

## Weights-versus-cards attribution

Weights-only evaluation uses a fresh process-equivalent state: reader/cache/workspace/slots reset; fresh question without restating the fact; store, candidate ranking, match/margin features, symbolic resolver and correction guard output channels disconnected; no world diary reachable; all parameters/normalization statistics frozen; no optimizer step or test-time adaptation. The guard is deliberately disabled **only in this offline attribution assay**, so stale weight answers are observable and never confused with production release behavior. It receives the visible world/name identifiers needed to address a learned fact, but not its value or hidden assignment.

Measure store-only, weights-only, normal hybrid and authority-override results separately. A failure with cards hidden could reflect distribution shift; practice includes the same closed-book input contract during training. Paired-world controls and randomized supplemental exposure are needed to attribute gain beyond generic task learning. Equal-size random lesions, usage-matched lesions and sham/restoration are required if attempting localization. A dense-block lesion that hurts many facts does not uniquely locate a particular fact. Randomized exposure is the primary causal attribution; lesion localization is corroboration, not a substitute.

## Deferred memory table, diary and health gauges

A later product-key pilot uses two subkey sets of 16, one head, 256 value slots of width 128: 32,768 value parameters plus 2,048 subkey parameters for 128-dimensional concatenated keys, the query map, bias and batch-normalization parameters. Use author-code uniform subkey initialization with each 64-dimensional half bounded by `1/sqrt(64)`, values normal with standard deviation `1/sqrt(128)`, and the published query batch normalization; hold its running statistics fixed at evaluation. Do not silently replace this with the toy's cosine normalization. Full 262,144×128 values alone are 33,554,432 parameters. Count optimizer state and sparsity-induced peak memory.

Compare values-only updates with fixed routing/core before independently permitting routing or core updates. Measure drift by querying the same address before/after unrelated updates. A slot is not an exact identity address and sparse writes do not guarantee no interference. PKM and fast-weight methods stay outside the six next comparisons unless they replace a lower-priority slot after a new explicit decision.

A replay diary stores code/pattern-bank versions, configuration, RNG algorithm/seed/ranges, observed action history, external/non-regenerable inputs and exact-byte output hashes. It may regenerate only observations actually available at the recorded time. Hash mismatch excludes the run; hidden simulator state cannot repair it. Charge diary bytes and regeneration time to replay. The parser/state/index, correction metadata, model, optimizer, caches, teacher snapshots if any, and temporary rebuild memory all appear in the storage account.

Track new-fact learning speed, retained closed-book facts, stale-answer proposals, retrieval coverage, abstention calibration, gradient norms, index age and storage occupancy. Fresh-task adaptation probes operate on disposable copies and are never fed back into the main checkpoint. Keep sleep's four jobs—repair, consolidation, practice and maintenance—separate in targets and comparisons.
