# Premonition: preserve identity, but test where it fails first

19 September 2026 · Research and experiment design only · No training or model tests run

**Contribution:** a buildable proposal to carry an entity's identity directly from a retrieved card into the next request, and a preregistered diagnostic that separates that operation from getting the first card right. **Novelty:** the central computation is established neural-symbolic machinery; neither this review nor the independent research passes found a defensible new algorithm. **Most consequential uncertainty:** whether a direct handoff fixes an important remaining error, once a competent ordinary system has the same address information. Current evidence makes failure *before* that handoff a strong competing explanation.

**Recommendation:** run the bounded, read-only diagnostic in [protocol.md](protocol.md) before training another architecture. Keep the direct identity interface as a provisional candidate. Its larger opportunity is making reusable procedures easier to acquire; that opportunity remains untested. A negative diagnostic would be useful: it would redirect work toward the writer/objective instead of funding another controller.

Evidence labels throughout: **shown** means inspected source, a stated saved experiment, or a mathematical result under explicit assumptions; **suggested** means an interpretation; **untested** means a proposed mechanism or prediction. None means a general capability has been established.

## 1. Refreshed evidence

The repository resolves to `/Users/ben-hannan/Desktop/projects/beautiful-model`, although the task was opened through Downloads. The working tree already contained substantial work. It was preserved. [source-audit.json](source-audit.json) records paths, SHA-256 hashes, modification times, exact run commands and extracted counts. Inspection used source and JSON only; checkpoints were not loaded. All 49 files in the overnight frozen-source manifest match their recorded hashes.

| Observation and source | Status and implication |
|---|---|
| Five baseline and five shortcut long-run JSONs reproduce every count in the supplied snapshot. Own retrieval is `fixed_K4`; oracle reading is `gold_read_K2_no_fetch`. | **Shown in those saved validation runs.** Baseline held-out counts: 6, 13, 88, 18, 12 /171. Shortcut: 171, 32, 35, 170, 132 /171. The shortcut passes the combined advancement rule in **2/5**, not 3/5 or 4/5. |
| The ladder imports the archived model through `premonition_ovn_ladder.bootstrap()`. The GPU script adds subclasses/wrappers. | **Shown in source.** Editing the live base model would not change this experiment. Current GPU-wrapper source postdates the long runs, so its exact historical bytes are not established by the current file. |
| Static parameter formula, synthetic vocabulary 52 + 16 entity IDs, width 32, key width 16, four loops. | **Shown by source arithmetic, not checkpoint measurement:** 79,748 baseline; 80,293 shortcut; 80,326 shortcut + separate key pool. The shortcut file's “tiny = 128” prose is stale. |
| Stuck runs have the right card family but about 15–18% correct-person retrieval; linear probes are near chance on keys but strong on the person-token state. | **Shown for the saved checkpoints and probe protocol.** Suggests failed preservation/alignment/use. Does not prove that keys contain no identity information or that the pooling layer caused the failure. |
| Positive-temperature rescoring did not rescue frozen similarities. | **Shown for that inference intervention.** The report's “kappa is not the cause” is too strong; training-temperature effects were not tested. |
| New `scripts/premonition_key_pool.py` clones the original scorer into a separate key scorer, adding 33 parameters. No completed run with `key_pool=true` was found. Extra baseline seed 5–14 logs are empty. | **Shown locally.** No new result or active remote-run status can be inferred. |
| An **older** dual-pool implementation was actually trained for 1,517 steps on one seed. Saved validation answers were 37/512, 18/341, 11/171; practiced all-gold retrieval fell from 173/341 to 120/341. | **Snapshot addition. Shown in milestone-3 JSONs.** Reading was card-blind in that regime. This prevents calling separate pooling untried, but does not settle the 12k-step shortcut + key-pool experiment. |
| Separate supplied-card choosing: fresh confirmation gives 500 vs 147 /512 and 466 vs 164 /512 for address vs pooled; two-hop combining does not improve. | **Shown on two seeds with supplied cards and explicit field positions.** Useful evidence for addressing, not learned raw-text parsing or successful chaining. |
| `fixed_K3_cards_removed` invalidates cards but retains contextual reader states feeding the question workspace. | **Shown in source.** This is a card-access lesion, not proof of complete factual erasure. |
| No A→B skill-retention experiment is established by these records. | No forgetting diagnosis or continual-learning success is warranted. The separate ~4M language model is not a ladder baseline. |

The detailed counts, runtime distinctions and evidence qualifications are in [evidence-and-literature.md](evidence-and-literature.md).

## 2. What needs explaining

| Observation | Competing explanations | Discriminating observation |
|---|---|---|
| Keys in stuck runs have poor linear person decoding. | Shared pooling drops useful identity; answer-first training creates a bad optimization path; identity exists in an unusable geometry. | A raw-subject gate rescues the first own fetch; subsequently compare key pooling against an early retrieval objective, with matched labels and compute. A probe alone cannot choose among them. |
| Relation shortcut improves held-out answers in learned runs. | It preserves the requested relation; it supplies an advantageous parse/optimization path; it changes which seeds escape a bad start. | Give all comparisons the same visible fields; keep every seed; separately score relation and person errors. |
| Gold-card answers look excellent. | General composition works; the decoder simply extracts the only attribute value. | Mirrored distractors and changed-link pairs requiring different answers. |
| Longer training fixes practiced retrieval. | Sufficient optimization was missing; curriculum or loss balance was wrong; short-run architectural comparisons were misleading. | Compare at the long recipe and report both actual compute and examples. Do not revive a 4k-step baseline as the main opponent. |
| A copied entity might improve second requests. | The current workspace loses the bridge identity; explicit field hints alone help; fixing the first request already removes the problem. | Compare QD against Q: both repair first-source addressing, only QD carries the **model's own** selected link destination forward. Also compare ordinary normalized tying. |

These distinguish an operation that cannot represent a result from one that can represent it but does not reliably learn, preserve or use it. The present model's successful seeds rule out a blanket representational impossibility on this ladder.

## 3. Candidate comparison

Three internal inventors received neutral facts and different computational questions, without the project's success stories or supplied prior-art inventory. A separate critic defended ordinary solutions. Their convergence is useful, but these are related model instances, not independent scientific replications.

| Mechanism | Burden removed; distinguishing prediction | Likely failure; novelty assessment |
|---|---|---|
| **Direct entity handoff** | Carry the selected object's ID into the next source constraint; no repeated identity reconstruction. Help should grow with repeated binding use. | Wrong first card, relation, or role remains wrong. Same central operation as exact relational execution; provisional candidate. |
| **Callable procedures with frozen interfaces** | Learn a new control program without rewriting old procedures. New-skill acquisition and retention can be measured separately. | Frozen inadequacy; dispatch interference; unsupported primitives. NPI already contains the central method. Runner-up. |
| Retain tuples and enforce shared-variable constraints | Preserve correlations between several roles instead of marginalizing each entity independently. Gains should concentrate on shared-witness conjunctions. | Joins can explode; local consistency does not solve arbitrary cycles. Database semijoins/TensorLog are close equivalents. |
| Interpret candidates before averaging their results | Prevent an uncertain read from destroying nonlinear distinctions within a card. Largest benefit when retrieval is diffuse and reading is nonlinear. | Cost proportional to candidate count; independent marginalization misses cross-card correlations. Related to prediction marginalization and relation networks. |
| Separate pools / earlier retrieval learning | Remove conflict or temporal dependence between learning values and addresses. Vary answer-first duration and distractor count. | Could fix only optimization, with no deeper procedural benefit. Already proposed/implemented locally; strongest inexpensive fallback. |

Exact routing wins on inspectability, cheap falsification and relevance to future procedures. Frozen programs retain the highest direct relevance to continued learning, but require a capability the existing benchmark does not test. Neither earns a novelty claim.

## 4. Selected idea in three sentences

Let the network learn which relation to follow, while an explicit register remembers which entity it reached. When it reads “Ada's friend is Ben,” copy Ben's identifier into the next lookup instead of reconstructing Ben from a mixed hidden vector. Test whether that handoff matters after fixing first-card addressing; if ordinary tied addressing does equally well, use the simpler established implementation.

**State and computation.** Store factual tuples `(source ID, relation, destination ID or value)` inside the designated erasable store, alongside current card values. Keep an episode-local handle `b`, a learned semantic/control state `h`, and provenance. A functional lookup is

\[
i_t=\arg\max_{i:s_i=b_t}\mathrm{score}_\theta(h_t,r_i),\qquad
b_{t+1}=o_{i_t}\quad\text{if the selected object is an entity.}
\]

The no-match case returns NULL/unknown. Selecting a relation, direction, initial referent and stopping remains learned. The first experiment supplies the same synthetic source/relation/object offsets to all diagnostic variants; it makes **no claim** to learned role extraction. A later text parser would have to predict those fields, with its errors and supervision counted.

**Learning and inference.** In a future trained version, retain answer loss and disclosed evidence supervision. A discrete copy has no gradient through the selected card; retrieval must still learn through its evidence objective. Unordered evidence is not a free program trace. During inference, copy only an actually selected card's object, never a gold intermediate. The diagnostic below freezes all weights and therefore tests access/use, not improved learnability.

**Worked example.** From `friend(Ada,Ben)`, `color(Ben,blue)`, `color(Cara,red)`, ask Ada's friend's color. Selecting the first card sets `b=Ben`; source matching then permits Ben's color card. If the first selection instead finds `friend(Cara,Dax)`, the procedure carries Dax and can fail. Exact copying does not repair wrong evidence.

**Minimal argument and its strongest objection.** Suppose there are M repeated uses of a bound identity. Under the explicitly illustrative assumption of independent, unrecovered per-use error ε, successful transport is `(1−ε)^M`; exact copying adds zero such errors *conditional on correct inputs*. This is not a lower bound on neural models, and errors need not be independent.

More decisively, distinct unit entity embeddings already satisfy

\[
\arg\max_j e_j^T e_i=i.
\]

Thus **hard normalized tied lookup is already exact** when its input is the selected object's embedding. Renaming “embedding” to “handle” adds no capability. For a soft entity distribution p, tied transport scores `EᵀEp = Gp`, whereas explicit coordinates retain p. Off-diagonal Gram terms can interfere, but orthonormal codes make `G=I`. At 16 entities this is cheap. This mathematical objection defeats a broad superiority claim and is why the first result should be diagnostic.

**Distinctive prediction.** A transport benefit should be small for one-hop retrieval, grow with the number of actual handoffs, and vanish against equivalent hard tied/orthogonal addressing. It should disappear when relation selection or parsing dominates, and can reverse when uncertain identities need several jointly consistent hypotheses. The current hard-fetch ladder does not itself establish soft-mixture interference.

**Modest first prediction:** the source gate may help stuck runs more than the handoff gate helps already learned runs. The primary diagnostic nevertheless requires a large *additional* handoff benefit before promotion. **Ambitious payoff, untested:** reuse an entity-independent procedure across many bindings and conditional traversals. No tenfold claim is justified; a later efficiency claim must compare total resources at fixed quality and include all failed runs.

## 5. Runner-up: preserve callable procedures

Use a library of small programs over `LOOKUP`, `COPY`, `EQUAL`, `BRANCH`, `CALL` and `RETURN`. State is `(program, instruction state, argument handles, scratch, store)`. A shared learned controller selects operations; the executor moves handles exactly. A new procedure receives new parameters; old dependencies and their call permissions are frozen.

For example, let Ada's parent be Ben, Ben's parent Cara, Ben be explicitly unlicensed, and Cara licensed. “Nearest licensed ancestor” must fetch Ben, reject him, continue from Ben, and return Cara. Missing evidence means unknown. Learning that loop is a new procedure; adding a parent fact is a fact update; adding a predicate token is a relation/schema change; asking parent-then-home is a familiar composition.

A small controller maps `(instruction state, observed flags, argument registers)` to an operation and next state. For a feasible first acquisition experiment, use explicitly counted simulator execution traces for both contenders, then evaluate their own discrete executions; answer-only program learning is a separate harder condition. New program entries cannot contain village-specific entity constants.

**Shown analytically under fixed dispatch and unchanged inputs/dependencies:** adding unreachable new parameters leaves old outputs identical. That guarantees preservation of an execution path, not usefulness, new-skill acquisition, or natural-language routing. **Untested prediction:** attain 90% on the new procedure with half the B examples of a strong replay baseline while losing at most two percentage points on A. Counterprediction: if B requires a new primitive or improved perception, freezing can impede learning.

The minimal future A→B test and its resource envelope are in the protocol. NPI already freezes the old core/programs and protects old call scopes. This runner-up is an application hypothesis, not an invention.

## 6. Closest verified methods

| Primary work and methods | Classification; remaining difference |
|---|---|
| [Neural LP, §§3.2–3.3](https://arxiv.org/html/1702.08367#S3) | **Same central mechanism:** entity coordinates traversed through relation operators selected by a learned controller. Here the facts would be per-episode cards and the interface attached to Premonition. That is integration, not a new computational principle. |
| [Neural Symbolic Machines, §2.2](https://aclanthology.org/P17-1003.pdf) | **Same central separation:** learned variable references address symbolic intermediate results. Different learning signals and small synthetic setting; no novelty established by those differences. |
| [End-to-End Memory Networks, §2.2](https://arxiv.org/html/1503.08895v5#S2.SS2) | **Strong ordinary alternative:** adjacent output/input embedding tying. Hard normalized direct symbol matching can collapse to exact transport; mixing/transformation is the actual distinction to inspect. |
| [Key-Value Memory Networks, §§3–4](https://aclanthology.org/D16-1147.pdf) | **Shared ingredient and fallback:** distinct addressing/content representations, including structured keys/values. Separate pooling cannot be claimed as new here. |
| [Neural Programmer-Interpreters, §§3 and 4.3](https://arxiv.org/html/1511.06279v3#S4.SS3) | **Same central mechanism as runner-up:** fixed shared core, new program entries, and protection against new-call interference. Its rich trace supervision is not free in Premonition. |

Searches included 2025–19 September 2026 work, older origins and equivalent formulations; limitations and additional methods are recorded separately. This is a bounded novelty audit, not proof that no closer paper exists.

## 7. Build map and decision

Add a diagnostic harness under `scripts/`, with a **new** versioned artifact directory. Reuse `premonition_ovn_ladder.bootstrap`, the saved-data conventions and `premonition_ovn_retrieval.own_fixed`; subclass or copy the small scoring hook rather than modifying the frozen archive. Add a field view at `CardStore`/`_Episode`, instrument `_step` and `_insert`, and clear all field-derived state on wipe. The main model, weights, decoder bypass, four-loop policy, card budgets and relation shortcut remain shared. Source offsets, label exclusion, NULL handling and exact no-op parity must be validated during future implementation.

This makes learned reconstruction of an already retrieved entity unnecessary **only if the diagnostic supports adopting the interface**. It does not make the reader, relation control, evidence training or factual store unnecessary. `premonition/address_reader.py` is decode-only and explicitly rejects Think; it cannot simply be dropped into the retrieval experiment. The existing [two-lookup proposal](../../design/research/2026-09-19-two-lookup-proposal.md) already proposes learned object-to-next-query chaining; this review adds the discriminating controls and explains why direct tying may suffice.

| Outcome | Next action |
|---|---|
| Large handoff gain, correct interventions, fresh confirmation | Adopt the simplest identity-preserving interface, including equivalent tying; investigate acquisition on conditional procedures. No novelty claim. |
| Accuracy improves but wrong-handle/no-op/label-separation controls fail | Reject the causal explanation; find leakage or broader intervention effects before promotion. |
| Local gain is confirmed, but full erasure/restoration fails | Retain the local finding; reject the store-isolation claim and repair the factual interface before architectural promotion. |
| Source gate helps; handoff does not | Prioritize separate key pooling and an early retrieval objective. Do not call this a controller breakthrough. |
| Neither helps with a valid, adequately covered implementation | Investigate relation control/reading; reject this intervention at this boundary, not all explicit-symbol architectures. |
| Insufficient correct-bridge rescue opportunity, implementation mismatch, label leakage or resource cap | Inconclusive. Allow one development-only repair and a fresh freeze; never tune on confirmation. |

**Established fallback:** the long-trained relation shortcut, with the existing separate key scorer tested against an early retrieval objective. Its best advantage is practical: it directly targets the measured stuck-run symptoms, needs only 33 new parameters, and preserves the existing model. Prefer it if the handoff diagnostic offers no independent gain. See [protocol.md](protocol.md) for exact thresholds, controls, erasure, confirmation and the complete proposed budget.
