# Premonition: relation transfer without an asker shortcut

19 September 2026. Track A only. Design for Fable to attack before implementation.

**Recommendation — suggested.** Prefer candidate B, a **learned lexical type filter with a shared relation projection**, unless the measurement below shows that the existing hop-2 query already carries the correct relation direction and mainly needs alignment. In that case try candidate A, a zero-parameter training auxiliary, first. A has the smaller implementation footprint but cannot enforce the missing compositional generalization. B enforces sharing of the selected relation's content, conditional on correct learned typing; it does not guarantee successful retrieval or reliable training. Neither is a demonstrated fix.

**Scope — shown.** This turn read local design files, source and the saved pair-suite text table, and added this file. No project imports, training, tests, checkpoint/tensor loading, GPU, SSH, spending, messaging or credential inspection occurred. The measurement is specified, not run. Existing files and concurrent changes are untouched. No implementation or execution is authorized by this document. “Shown” refers to inspected source or previously reported results, “suggested” to decisions, and “untested” to the proposed mechanisms and measurements.

## CANDIDATES

### Shared facts and notation

**Shown.** The relevant model has `d=32`, query/key width `k=16`, and 79,748 parameters. It computes an unnormalized request `q0 = Wq z + bq`, where `z` is normalized register 0, then the store computes

```text
u = normalize(q0)
s_j = kappa * u^T k_j + age_bias_j
```

over eligible cards, including NULL. ASK gates the hard top-1 fetch. K=4 evaluation supplies three fetch opportunities; HALT does not stop this evaluation. Card eligibility, ASK, query direction and answer correctness are different quantities. [model], [store], [fixed]

Write `a` for the question's person, `b=friend(a)`, `r` for its terminal attribute, `L(a)` for its link card, and `A(b,r)` for the endpoint card. These are **analysis/training-label notation**, not new inference inputs. Relation 2 occurs in one-hop training and story cards but never in two-hop training questions. [generator]

**Shown, from earlier reports.** Among the 33 fresh-learned plain/shared checkpoints, request 1 retrieves LINK at .892889, while request 2 retrieves the right person/wrong relation at .636808 and the endpoint at .244377. These are marginal frequencies, not a joint correct-LINK/incorrect-endpoint trajectory assay. Plain/shared passes G_pair in 0/40 runs. The wire's stuck count is 16/40 on historical validation and **17/40 on fresh c1**; those classifications must not be mixed. [08], [11], [table]

### A. Teach an existing second request to match an equivalent one-hop request

**CHANGE — untested, training only.** Add one stop-gradient query-consistency loss. Do not add a module, change the teacher order, supply a new inference input, or expand the held-out training combinations.

At the second scheduled opportunity of an ordinary non-gold training episode, retain a question for this auxiliary only if its actual fetched **real-card set is exactly `{L(a)}`**. This condition uses training evidence labels. It includes link-first teacher episodes and successful link-first own episodes. It does not force a LINK insertion, filter the run roster, or alter the normal episode. NULL is not a real card. Let this batch subset be `J`.

For each retained practised two-hop question, create an auxiliary one-hop donor question `[question] b r [answer]`. Use the same causal prefix before the original question, including the same story, and a fresh empty workspace at loop index 0. Recompute the donor's question reader states; changing an entity token in an already contextualized row is not an equivalent donor. No answer/feedback from the target question may enter that prefix. The pre-question store can be reused because it is causally unchanged. The donor receives ordinary input text, not preloaded evidence. Its entire computation is stop-gradient; its `b` was obtained from the training evidence, never by an inference-time rewrite.

```text
u2_i = normalize(q0_theta(original episode, loop index 1))
u1_i = stop_gradient(normalize(q0_theta(donor, loop index 0)))

L_align = mean_(i in J) [1 - u2_i^T u1_i]       (zero if J is empty)
L_A     = L_existing + 0.5 * L_align            (non-gold only)
L_A     = L_existing                            (gold)
```

Use the existing normalization epsilon. The coefficient .5 is a proposed fixed design choice, not a tuned result. Normalize over J once per update, independently of the existing missing-evidence CE denominator. No confidence-based donor selection or additional donor answer/search loss is included. Ordinary one-hop training, which covers **all three relations**, continues to train the donor computation through its existing losses; this particular donor forward contributes no gradients.

**WHY — suggested.** At the useful second state, both questions should request the same address `(b,r)`. Matching normalized requests teaches the existing Think-to-query path to reuse the one-hop geometry, including the correct person. Across matched practised relations, small alignment error also makes the relation difference `u2(r)-u2(r')` match `u1(b,r)-u1(b,r')`. This is a training signal for a shared computation, stronger than simply giving more one-hop examples.

It adds **no question-token content to inference**, so the shelved residual's algebraic `B E[a]` term is absent. The donor explicitly concerns b, and its query must distinguish `A(b,r)` from `A(a,r)` during ordinary one-hop learning. This is not a proof that the trained legacy query becomes asker-independent: a bad donor or shared-parameter interference can still teach the wrong address.

**COST / INITIALIZATION.** **+0 parameters; 79,748 total.** Initial inference, queries, keys, values, scores and decoder outputs use exactly the original computation and tensors. The model adds no initialization RNG consumption. At equal weights the ordinary training forward is unchanged, but the total non-gold loss and gradients differ whenever J is nonempty. Gold has no added loss. Extra work is one no-gradient donor reader/first-Think computation per retained question, plus the alignment backward through the existing student graph. Prefix reuse is an optimization to validate later, not a claim that full-reader replay is free. Charge this work to the common budget; equal FLOPs will reduce ordinary training exposure. J may be scarce in poor runs, so this is not a plateau remedy.

**OWN COUNTEREXAMPLE — decisive limitation.** A sufficiently expressive legacy Think block can implement

```text
u2(a, r, after LINK) = u1(b,r)    for r in {0,1}
u2(a, 2, after LINK) = u1(b,0)
```

while retaining excellent one-hop relation-2 retrieval. Its auxiliary loss can be zero and held-out transfer can still fail completely. No loss evaluated only on the two practised two-hop relations excludes this function. Stop-gradient also prevents only instantaneous target chasing; because donor and student share weights, both can drift across updates. An immature donor can pull useful second queries toward a bad one-hop address and worsen reliability.

**FAILURE SIGN.** Alignment loss and practised query mismatch decrease, but held-out relation-swap sensitivity, endpoint retrieval and c4/c5 remain poor. A rise in second-opportunity `asker_same_rel`, deterioration of one-hop/READS, or any increase in fresh stuck count is an additional failure, even if alignment improves. Report the fraction of episodes contributing to J; a nearly empty J makes a null result weak evidence about the objective.

**Why not a simpler data-only change?** More one-hop examples or more relations does not force parameter sharing at the second state. Renaming/permuting relations so that relation 2 now occurs in two-hop training would remove the specified holdout, not solve it. Supplying `[question] b r` at evaluation would provide the answer to the first hop. Candidate A uses that rewrite only as disclosed training supervision on practised combinations.

### B. Learned lexical typing, a shared relation vector, and an empty-workspace guard

**CHANGE — untested.** Replace the shelved all-token soft mixture with a learned, context-free **ATTRIBUTE / LINK / OTHER** classifier. Inspect every valid token in the existing question span. Do not read a fixed offset, token-ID range, relation list, oracle role mask, hop tag or gold card in the inference module.

For each token `t_i`, cache its static embedding and classify it once per episode:

```text
x_i = stop_gradient(E[t_i])                         x_i in R^32
p_i = softmax(T x_i + c)                            T: 3 x 32, c: 3
y_i = argmax p_i                                    ties -> OTHER
confident = all_i max(p_i) >= .99
I_attr = {i : y_i = ATTRIBUTE}
n_link = count_i [y_i = LINK]
accepted = confident AND |I_attr| = 1 AND n_link <= 1

v = B x_(the sole member of I_attr) if accepted, else 0
                                                      B: 16 x 32
m = any(episode.fetched over real store-card columns)
h = accepted AND ((n_link = 0) OR m)
```

Here `m` excludes NULL. Do **not** use `episode.count > 0`: the inspected insertion code increments that count for nonnegative card indices, including NULL. `episode.fetched` already exists, and distinguishes real columns from NULL. No test of whether the fetched card is correct is available to this module. [model]

At both request call sites, use the following bounded residual, with `eta=.25` fixed:

```text
clip(v,R) = v * min(1, R / ||v||)    for ||v|| > 0
clip(0,R) = 0                       with derivative identity at v=0 when R>0

q_new = q0                                      if h=0 or ||q0||=0
q_new = q0 + clip(v, eta * stop_gradient(||q0||)) otherwise
```

For the zero-radius case bypass the addition. Keep the store's ordinary normalization after the sum, eligibility, age biases and ASK unchanged. The diagnostic `_recall` must use the same module and current episode guard; its pre-existing eligibility convention is otherwise unchanged. There is no contextual scalar gate and no all-token embedding average. The .99 confidence threshold, unique-attribute condition, real-fetch guard and norm cap are part of this single proposed module, not knobs to rescue after results.

**Training supervision — explicitly stronger than stock ASK.** Initialize `T,c,B` to zero in an isolated initialization path. Train T,c from a class-balanced token-type CE on the distinct token identities occurring in valid training question spans in the current batch:

```text
L_type = mean_(types represented in batch)
           mean_(distinct tokens of that type) -log p(type | token)
L_B = L_existing(q_new) + 0.1 * L_type
```

The training generator supplies the type target: attribute token, LINK token, or other question token. This is **new training-time role supervision**, in addition to the existing evidence supervision; it must be disclosed as such in any comparison. It does not label which attribute relation is present. Relation 2 obtains ATTRIBUTE examples from its ordinary one-hop questions; no held-out two-hop question, target request or answer enters training. The label-production helper must be absent from the inference call path, not consulted to construct a saved lookup table or runtime mask. This proposal therefore meets the stated ban on **supplied inference roles**, but must not be advertised as learning the type distinction from answer loss alone.

Type CE acts only on T,c because x is detached. It runs from the first gold update, so the hard confidence filter is not a permanently dead branch. Hard classification receives no ASK gradient and uses the same policy during training and evaluation; no straight-through estimator or soft-training/hard-evaluation switch is included. Once accepted tokens exist, ordinary evidence-search CE trains B, including on relation-2 one-hop questions. The new branch does not send direct gradients into E. Existing losses still train E, the reader, keys and the legacy request; changes in E can require the classifier to track them. ASK BCE, answer/LM/HALT losses and teacher choices retain their original definitions.

**WHY — the precise transfer property.** Suppose every entity/delimiter is classified OTHER, LINK is classified LINK and every attribute is classified ATTRIBUTE at sufficient confidence. In both `[question] b r [answer]` and `[question] a LINK r [answer]`, the sole selected content is **exactly the same `E[r]`**, independent of question position, asker, story context and Think mutation. After a real fetch the added direction is `B E[r]`, the same map trained by one-hop relation-r requests. Only its nonnegative norm cap can rescale it; there is no separate hop-2 relation map or register-dependent content gate. This is conditional parameter sharing, not extrapolation by a new contextual selector.

For a confidently typed link question with an empty real-card workspace, h is exactly zero, so the terminal relation cannot directly change its first query. For a one-hop question it can help from the first request. The guard uses the learned LINK classification and the model's own fetch history, **not a supplied hop number or a claim that the link was successfully read**. It is an explicit stage bias appropriate to this toy, not a general dependency planner.

**Asker contamination: exact conditional exclusion and limits.** With correct typing, changing a to another correctly rejected entity changes neither v nor its direction. No `E[a]` passes through B. Thus the uniform-attention counterexample does not apply. Incorrect but confident typing remains possible: if the asker is accepted as the sole ATTRIBUTE while the true attribute is rejected, the bad path is back. Confidence is not a calibrated error guarantee. Requiring one attribute disables the common case where both asker and relation are classified ATTRIBUTE; it does not eliminate every error.

Let F denote false accepted content, and `rho=Pr(F)` on the reported evaluation distribution. The direct bad addition satisfies `||delta_bad|| <= eta ||q0|| 1_F`. For nonzero q0, its normalized-query deviation from disabling that addition is at most `2 eta`; thus the expected direct cosine-score deviation per card is at most `2 kappa eta rho`, and a two-card margin deviation at most `4 kappa eta rho`, for a fixed checkpoint. These bounds concern the immediate erroneous addition, **not cumulative training damage**, and rho must be measured. A cap this size cannot preserve an arbitrarily small top-1 margin.

Even perfect typing does not make the full request entity-free or guarantee person-neutral key scores. The legacy query still holds entity information, and a constant relation vector can favor the asker decoy in entangled key geometry. Removing the explicit asker vector is a narrower, defensible claim than removing every possible asker error.

**COST / INITIALIZATION.** `T,c`: `3*32+3=99`; B: `16*32=512`. **+611 parameters; 80,359 total**, including the training-supervised classifier deployed at inference. No new embedding table or relation-ID output head. The raw extra matrix work is approximately `96*L+512` multiply-accumulates per question with L valid tokens, plus softmax/filter/cap work and training backward; cache the static selected vector for the episode. This is arithmetic, not measured throughput.

At initialization p is uniform, so accepted is false and the new query call returns the original q0 directly. Shared parameters, all inference queries/scores/fetches, card values and decoder outputs are bit-identical under the same deterministic execution. Added tensors must not consume the baseline initialization/training RNG stream. Runtime numerical parity still requires later verification; additional GPU work does not prove identical future trajectories. Initial type CE is nonzero. Initial **unclipped gradients on shared parameters** match the baseline because the branch is bypassed and x is detached, but the existing global gradient clip includes the classifier gradient and can change the first optimizer update. Do not claim an identical gold-training prefix or immunity to the wire's reliability failure.

**OWN COUNTEREXAMPLE — strongest even with perfect typing.** Suppose all token types are correct, but an own episode first fetches a wrong attribute instead of LINK. The real-fetch guard opens. The terminal-relation residual now reinforces attribute fetching while the register still represents a; nothing verifies a completed link. More fundamentally, even after a correct link the legacy query may strongly point to a practised relation. A bounded B residual learned mostly on one-hop states may be too small to reverse that margin. Removing the cap after observing this would be a different design. Shared training can also make the correct `B E[r]` favor asker-specific keys or increase stuck runs. Correct lexical typing alone cannot refute these cases.

**FAILURE SIGN.** Report, over every question and separately for practised/held-out relations: accepted-correct/accepted-wrong/abstained content; entity acceptance; LINK-type errors and erroneous first-opportunity guard openings; first-LINK, first/second `asker_same_rel`, no-ASK/NULL; second endpoint and right-person/wrong-relation; and cap activation. If typing is correct and active after native correct LINK but endpoint/c4/c5 do not improve, the route's claimed sufficiency fails. If typing frequently abstains, a weak result does not establish that selected lexical content was unhelpful. Any increase in fresh stuck count blocks advancement regardless of survivor gains.

### Why not just subtract the original person?

**Considered, not a third candidate.** The model already computes entity mentions and has entity slots, but its slots and contextual rows contain mixed content. There is no demonstrated query-space vector equal to “the asker's contribution.” Subtracting `B E[a]` with an estimated attention weight can oversubtract or remove useful information. Projecting static content with `P_a=I-E[a]E[a]^T/||E[a]||^2` gives `B P_a E[r]`, which **depends on a** and differs from the one-hop `B P_b E[r]`. It breaks the sharing we need, and orthogonality to E[a] before B says little about asker-key scores afterward. Projecting away all entity embeddings can remove relation directions too. Reusing entity token-ID ranges as an exact content mask would avoid learning the type distinction and would reintroduce the supplied-role concern. B instead uses the already-computed real-fetch mask only for stage gating and learns lexical exclusion from disclosed training targets.

## MEASUREMENT

**One proposed eval-only assay: matched relation swaps with query-direction transport.** Use all 40 saved plain/shared checkpoints, with frozen weights and normalization state. No probe fitting, new trained selector or optimization. This measures the request's actual effect on card ranking, not just identity at a known row. It is diagnostic intervention, never a deployable oracle fix or a G_pair result.

Predeclare one new 256-world panel, separate from training, certification and previous diagnostic panels, with a fixed asker per world and all three terminal-relation variants. For each world create six independently reset episodes: native `a LINK r` for r=0,1,2, and ordinary one-hop `b r` for r=0,1,2. Each starts after the **same complete causal pre-question prefix**. Only the question changes; use the same pre-question store. Obtain b from evaluator labels solely to construct the donors. Use normal K=4/ASK/top-1 native traces, not supplied first cards. For donors only their first request vector is required.

Record native first-LINK outcomes for every question. For each practised p in {0,1}, analyze the matched subset on which **both native two-hop variants p and 2 actually fetched the correct LINK at opportunity 1**. Never force this condition. Report subset size and unconditional coverage for every seed, and retain all 40 seeds plus the predeclared historical 33 fresh-learned stratum. Do not silently turn the subset into a selected successful-run roster.

On that subset record normalized native request vectors `u2(p),u2(2)` at opportunity 2 and donor vectors `u1(b,p),u1(b,2)`. Compute

```text
d1 = u1(b,2) - u1(b,p)
d2 = u2(2)   - u2(p)
C  = cosine(d1,d2)
R  = ||d2|| / ||d1||
u_transport = normalize(u2(p) + d1)
u_donor     = u1(b,2)
```

Mark tiny differences (`norm < 1e-6`) undefined rather than inventing a cosine. Mark a near-zero transported vector invalid. Score **native u2(2), u_transport and u_donor** against the actual held-out second state's same keys, eligibility and age bias. Keep that state's native ASK decision in all three conditions. Report both ungated top-1 and ASK-gated selections, endpoint-versus-best-wrong margin, right-person/wrong-relation and asker-decoy rates. Also report relation margins among b's three attribute cards; diagnostic restriction to these cards is for a reported statistic only, never the main fetch rule. p=0 and p=1 are correlated views, not independent worlds; retain them separately and average worlds, then seeds equally.

**Interpretation and a result that changes the recommendation — suggested, not an advancement gate:**

* **Switch to A first** if most informative learned seeds (at least 22 of the historical 33, each with at least 128 matched worlds for both p values) show donor endpoint top-1 at least .95, median C at least .9 and median R between .5 and 2 for both contrasts, while transport raises held-out ASK-gated endpoint retrieval by at least 20 percentage points without an asker-decoy rise exceeding 2 points. That says the existing request responds in the useful relation direction, but its alignment/magnitude is wrong enough to change selection. A is then a reasonable first way to repair it without a new content route.
* **Keep B preferred** if donor/transport select the held-out endpoint well but the native held-out contrast is absent, weak or points elsewhere—for example median R below .25 or C at/below zero with strong d1. A still might learn a repair, but its practised-only alignment leaves exactly this unseen branch unconstrained. B supplies shared lexical content regardless of whether the legacy path responds to it.
* **Support neither mechanism yet** if even the donor request cannot select the endpoint in the same target store, or if transport fails despite good donor retrieval. The latter shows that one-hop relation differences need not compose with the two-hop address geometry; a simple added relation direction is not established. Low subset coverage is also inconclusive, not evidence for B. If native relation-correct endpoint retrieval is already high across the allowed opportunities but failures arise from ASK timing or answer decoding, defer both relation fixes and localize that failure instead.

These numerical flags are proposed decision aids fixed before this assay, not confidence-certified causal conclusions. Publish per-seed continuous results and paired world-level uncertainty, including near-zero and low-coverage cases; an intermediate pattern remains mixed. The assay cannot prove that A will train, that B's classifier will learn, or that the observed failure originates specifically in the reader rather than Think. It tests **used relation sensitivity and selection** and is more directly matched to this choice than 08's known-row identity readout. It does not silently replace that readout's formal prerequisite for the separately registered old A4.

The panel entails 61,440 question episodes across 40 checkpoints, with donor work limited to the first request and store scoring reused for interventions. It is small relative to a training comparison and requires no optimizer or GPU; actual CPU time and memory are unmeasured. Checkpoints and tensor panels were not loaded in this turn. Future execution must record source/panel/checkpoint identities and unchanged-weight/episode-isolation checks under 09.

## SEQUENCING

**Q3 normalization should be independent of the relation fix, not a mandatory predecessor.** Its proposed

```text
L_set = (2/3) mean CE_first + (1/3) mean CE_later
```

holds first-request weight steady as later missing-evidence terms multiply. It neither identifies the terminal relation nor ties one-hop and hop-2 content. It can indirectly change learned geometry and plateau escape, so independence means **a separate causal comparison**, not a claim of zero interaction. Preserve 12's teacher-delay-first decision; do not add this normalization to the relation treatment or quietly change its control. [12]

Under this handoff, use the accepted A3-teacher-delay-v2 plateau-stage background if it passes; otherwise use plain/shared. This fallback does not require A3 to solve held-out transfer first. If plateau failure remains the dominant practical obstacle, Q3 is a reasonable separate next plateau contrast after the delay result, but neither its success nor its failure decides the relation mechanism. If a Q3 background is later promoted, comparing a relation fix there requires a newly named, frozen contract; it is not automatically inherited here.

Choose **one of A or B**, never A+B in the first comparison. Candidate B's type loss and guard are disclosed parts of its single module specification; do not describe it as the old residual trained with unchanged supervision. No frontier CE, key-pooling change, ST, wire, teacher-order change or Q3 normalization is bundled. Both arms train afresh, with the complete seed roster including potential stuck runs. Historical learned checkpoints are diagnostic material, not treatment initializations or admission filters.

Any later relation comparison needs its own reviewed registration, sample size/power, explicit budget and complete resource accounting. Keep 08/09's fresh G_pair advancement endpoint, published cell cutoffs, exact paired gain/loss rule and effect floor, one-hop/READS safeguards and **no increase in fresh stuck runs (`c1 <1536/2048`)**. Stage acceptance and better survivor retrieval do not waive that safeguard. Keep G_cert and its independent 77/80 campaign separate. This file is a design choice for review, not a launch contract.

## FOR BEN

The model often finds the right person, then asks for the wrong kind of fact. One possible repair is to teach its second lookup to match an equivalent one-step lookup, using only the relations it is allowed to practise. That adds no parameters, but it could still memorize those examples. My preferred alternative is a small learned filter that recognizes relation words, carries the selected word through the same path for both kinds of question, and keeps that addition off while a link question is still waiting for its first real card. This avoids mixing the original person's name into the added content when the filter is correct. We should first check how changing the relation actually changes the saved models' card choices; either proposal still fails if it creates more stuck runs.

## Sources

[08]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/08-pairsuite-adjudication.md
[09]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/09-reconciliation.md
[10]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/10-fixes.md
[11]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/11-fix-review.md
[12]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/12-teacher-delay-contract.md
[model]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:410
[store]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/store.py:106
[generator]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/toy_ladder.py:141
[fixed]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_ovn_retrieval.py:63
[table]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-pairsuite-20260919/table.txt
