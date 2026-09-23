# Premonition: fixes to the model and training

19 September 2026. Track A only. Analysis for Fable to challenge before implementation.

**Suggested — decision.** First teach the existing address interface to retrieve a single fact while the gold-card phase is teaching it to read. Next give the query a small, learned route to the *token identities* in the question. Reserve dependency-ordered search supervision for the remaining delayed-LINK failure. These address three different problems: losing the person, failing to reuse the relation, and choosing the wrong first operation. None has demonstrated dependable two-hop learning or removal of the seed lottery.

**Shown — scope and authority.** This review inspected source and existing text/JSON, including standard-library tabulation of saved results. No project imports, checkpoint or tensor-dataset loading, tests, training, GPU, SSH, spending, messaging, or credential inspection occurred. This is the only new file. “Shown” means a source fact or saved-result calculation, not a newly reproduced model assay; “suggested” means an inference or recommendation; “untested” means a proposed mechanism, intervention, or prediction. [08] and [09] remain the plan of record. This shortlist proposes design changes for review; it neither rewrites A4 nor admits additional experiments.

## MECHANISMS

### Read the evidence at the right resolution

**Shown.** The shared-pooling plain model has **79,748 parameters**. The wire adds 545; separate pooling adds 33. The saved pair-suite rows give:

| Recipe | G_pair passes | Fresh one-hop stuck | Historical one-hop stuck |
|---|---:|---:|---:|
| Plain, shared pooling | 0/40 | 7/40 | 7/40 |
| Plain, separate pooling | 3/40 | 1/40 | 1/40 |
| Wire, shared pooling | 21/40 | 17/40 | 16/40 |
| Wire, separate pooling | 23/40 | 6/40 | 6/40 |

Fresh stuck means c1 <1536/2048; historical stuck means validation <384/512. These are different panels, and wire seed 0 changes classification. The interface probes concern an older 15-checkpoint roster per arm, not these 40-checkpoint rosters. G_pair is not G_cert, and 21/40 or 23/40 does not establish the separate **77/80 fresh-run certificate**. [rows], [08], [09]

**Shown — two consequential corrections to the handoff.** Probe A's retrieval intervention edits the one-hop question's **own gold fact's value**. The edit is irrelevant to *which address to retrieve*, but relevant to the answer; it is not the irrelevant-fact control c6. Also, G_pair uses four fixed Think loops, with at most three retrieval opportunities and the native ASK gate; **HALT is ignored**. Its “70% mode” cannot be explained by early HALT. [probe-a], [interface-source], [fixed-eval]

### F1 — most likely mechanism: subject discrimination loses the early shared-representation competition

**Suggested.** During the gold phase, the reader/writer learns a representation that makes supplied cards easy to decode without making their subjects easy to address. In some runs that representation loses a useful subject direction between the subject token and the normalized card key. Once category-only retrieval emerges, query and key must recover person discrimination together. Hard fetching supplies poor subsequent workspaces, while answer loss has no gradient through the selected card index. This is a coupled reader–pool–key–query optimization failure, not simply insufficient width.

**Shown — code path.** `CardWriter.forward` makes one attention-weighted line summary and uses it for both `key` and `value` ([writer], lines 171–197). Gold mode preloads all evidence, sets ASK/HALT loss weights to zero, and trains answer decoding ([training-forward], lines 525–555). `CardBypassMini._decode_logits` gives the decoder the inserted card rows directly ([bypass], lines 114–121). Later, the normalized register-0 projection meets normalized keys in `CardStore.ask`; own training detaches scores before hard top-1 ([query], [store], [training-forward], lines 596–615). ASK CE itself remains differentiable to query and keys. “Search gets no gradient” would therefore be false; it gets **no answer-loss gradient through card selection**.

**Shown — evidence for.** On link lines in stuck probe checkpoints, subject readability is 0.991/0.985 at its token, but only 0.241/0.224 from the key and 0.250/0.259 from the value, plain/wire respectively. Even the LINK-token state has poor subject readability, 0.300/0.365. The loss can begin before pooling, rather than residing exclusively in the pooling scorer. Separating pooling greatly reduces stuck counts. Successful seeds show that this parameter budget can preserve subjects. [probe-b], [rows]

**Shown — evidence against an overstrong version.** A failed affine readout does not establish information destruction: the pooled vector itself was not probed, and both projections can hide information. Edited-key cosine averages remain about 0.997 even in stuck runs. The 22.8%/23.7% request-identity changes under Probe A's edit therefore do not show wildly moving keys. Both the store and contextual question are recomputed, so the assay does not identify which side moved enough to change a close ranking. Learned seeds retain both link roles in pooled values, and separate pooling still leaves almost all unprivileged runs failing G_pair. [probe-a], [probe-b]

**Untested.** Small between-person score margins, attention saturation, gradient cancellation, and the precise time the subject direction becomes unusable have not been measured here. They explain the pattern plausibly; the final-checkpoint probes do not establish the temporal cause.

### F2 — most likely mechanism: the query learns a context-specific relation decision instead of reusing the relation identity

**Suggested.** The shared Think block can implement different effective computations for a one-hop question and for a two-hop question after a LINK fetch. At the latter state, training rewards only two attribute relations. A query that distinguishes those two succeeds without learning a reusable route from any visible relation token to its address direction. Its person component can be correct while its relation component defaults to a practised relation.

**Shown — code path and evidence for.** Question states are full-story contextual reader states; Think repeatedly modifies them and the registers before `heads.query(norm(register0))` ([question-start], [query]). `toy_ladder.visit` excludes relation 2 only from two-hop training questions, while showing it in one-hop training and in fact cards ([generator], lines 119–165). Among the 33 fresh-learned plain/shared runs, held-out first-LINK retrieval is 0.8929, second-opportunity right-person/wrong-relation is 0.6368, and correct endpoint retrieval is 0.2444. The static-embedding wire substantially repairs this failure in successful learners. Six relations did not reliably induce a general relation-copy rule either, although that screen was small and harder. [rows], [wire], [six-relations]

**Shown — evidence against a stronger localization claim.** These request classes do not tell us whether relation transfer fails in the contextual row, its selection, the Think computation, or the final query geometry. The wire alters both the information route and optimization. Some plain runs already transfer partially. Probe C's contextual cut also resets recurrent state and positions; its large retrieval losses are not proof that story-free representations would fail if trained that way. [probe-c], [interface-source] The affine relation-transfer assay specified in [08] has not been supplied as a completed result. **Untested:** “the reader forgot REL” and “the reader is fine; only the selector is wrong” are both stronger than the evidence.

### F3 — most likely mechanism: a relation route without a learned dependency policy competes with person and stage information

**Suggested.** The wire helps represent the target relation but does not specify when that relation should control search. It adds a gated vector at every loop into the same normalized query used for both person and relation. Learning that addition changes their relative directions and can make the easy attribute-card route dominate before the useful LINK has been read. The unordered evidence objective supplies no explicit first-operation preference to counter that competition.

**Shown — code path.** The wire reads `q_span[:,1]-2`, then adds `sigmoid(gate(z))*W_r*E[REL]` after the legacy query in both score paths ([wire], lines 56–58 and 91–138). The store normalizes the *sum*, so the addition can reduce the influence of the legacy person's direction. The set objective is

`L_set = logsumexp(s_all) - logsumexp(s_still_missing_gold)`.

For the first two-hop search, both LINK and endpoint are positives. Its derivative is `p_j - 1[j in G]*softmax(s_G)_j`; increasing whichever positive is already preferred can satisfy it. Teacher selection is random over missing gold cards. No hop order is imposed. [store], lines 33–35; [training-forward], lines 631–654

**Shown — support and important counterevidence.** The two fresh-learned wire/shared G_pair failures fetch a wrong-relation attribute first on all questions in their aggregate trace, then the LINK at opportunity 2 with frequency 0.9995. At opportunity 3, endpoint retrieval is 0.6941 and no request occurs on 0.2815. This identifies an ASK/stage problem even with a third opportunity available. It is **not simply “two requests were allowed.”** Further, the first attributes are *wrong-relation* cards, not generally the gold endpoint; a story that the wire directly fetches the correct answer card too early is inconsistent with these counts. [rows]

**Untested.** Actual gate values, wire/legacy vector norms and their causal contributions on those traces remain unmeasured. Marginal request counts do not substitute for joint trajectories. The larger stuck fraction is consistent with the F1 competition, but the 40-run plain and wire rosters also use different hardware; their difference alone is not an isolated causal estimate of the wire's effect. Separate pooling improves some seeds and loses eight wire passes, while first-LINK rates decline; that supports a coupled optimization problem, not a monotonic architectural improvement. [08], [rows], [plain-run], [wire-run]

### F5 — most likely mechanism: early trajectory differences are amplified by thresholded retrieval and the curriculum

**Suggested.** The optimization has alternative self-reinforcing regimes: learn person-sensitive addresses and train on useful fetched states, or learn category-only addresses and keep training on wrong states. Hard top-1 and ASK's zero threshold make the subsequent training computation discontinuous at small score changes. Gold/teacher/own curriculum transitions then expose different state distributions. This explains two-peaked outcomes more economically than a capacity limit.

**Shown — code and supporting evidence.** Hard top-1, ASK gating and own/teacher Bernoulli choices appear in [training-forward], lines 608–615. The curriculum ramps to 0.75 own fetching ([curriculum], lines 81–103). The same wire seed IDs disagree on G_pair in 8/15 cross-environment comparisons. For seed 0, saved early log values are nearly identical, but the final losses and causal results diverge. Recorded environments are Torch 2.11/Windows/5070 Ti versus Torch 2.8/Linux/5060 Ti. This is consistent with amplification of small numerical differences. [08], [wire-original], [wire-run]

**Shown — limits.** The environment comparison does not isolate floating-point noise from library, source, execution or RNG differences. It does not measure repeatability on one fixed machine. Binary G_pair thresholds sharpen appearances, though continuous causal outcomes are also concentrated near the extremes. **Untested:** a literal sharp phase transition, its critical parameter, and a smooth intervention that removes it. Do not call the same integer seed the same optimization trajectory.

## RANKED FIXES

**Suggested — meaning of the ranking.** This is the order in which I would spend engineering effort and a constrained learning budget on a route toward 77/80, not measured dollars per additional certificate pass. Fix 1 is the inexpensive prerequisite aimed at the stuck population; fix 2 has the strongest direct precedent for improving held-out G_pair; fix 3 is conditional cleanup. Fix 1 alone may improve one-hop reliability without producing a single additional strict pass. No useful numerical gain estimate exists for these untrained changes.

**Suggested — comparison boundary.** Each candidate changes one stated factor against a declared control. Begin from plain/shared pooling. Do not bundle these changes into a first comparison or carry an apparent winner into the existing A4 contract. If a later comparison uses a promoted predecessor, name and freeze that new background explicitly. The new objectives/lexical route would need a reviewed amendment assigning existing slots; they are not extra authorized waves. Existing [08]/[09] pass criteria and certificate definitions remain intact.

### 1. Empty-workspace one-hop search loss during the gold phase

**CHANGE — untested specification.** Keep the original gold-card answer episode. Before its preload, make a separate fresh episode for the batch's told, singleton-evidence questions. Reuse the same reader states and store, start with no fetched cards, execute the ordinary first Think loop, and add

`L_early_search = w_ask * mean_q[softplus(-ask_q) + logsumexp(s_q) - s_q[g_q]]`,

where `w_ask=0.5` is the existing ASK weight and `g_q` is the single evidence line. Apply this term **only during the existing first 10% gold phase**, from the first update. No decoder loss, insertion, HALT loss, or rollout occurs in this auxiliary episode. Compute scores over all ordinarily eligible cards including NULL. Backpropagate into the ordinary query, keys, shared pooling and reader; do not detach them. Restore the ordinary episode bookkeeping before its decoding. The later curriculum and losses are unchanged.

**Shown — why “just turn ASK on in gold mode” is not this fix.** After the normal preload, no gold card is missing. Turning up that episode's ASK weight mostly teaches “do not ask” and supplies no positive address CE. The separate empty episode is essential. [training-forward], lines 551–555 and 596–601

**WHY — suggested.** This makes subject-sensitive addressing useful while the reader/pool is still plastic, and starts the search parameters under the existing 100-step optimizer warm-up. Every same-relation/wrong-person card is a negative, so a category-only score cannot solve this objective. It preserves easy gold-card answer teaching instead of making answer learning depend immediately on random retrieval. This is the earlier E1 proposal, now specifically motivated by Probe B's interface failure; it is not the pending gold-zero run and does not assume that run succeeded.

**COST / INITIALIZATION.** **0 parameters; 79,748 total** as a standalone change. Identical initial inference, card values, queries and decoder outputs; the total training loss and its gradients deliberately differ on update 1. It consumes no new initialization RNG. Reuse reader/store computation; add one Think loop on roughly half the gold-phase questions. That is about 25% extra *gold-phase Think-loop work*, not 25% of total training or a measured timing estimate. Include its forward/backward work in the common FLOP cap and disclose the resulting change in exposure. Training uses the existing evidence labels, with no position or role targets at inference.

**FAILURE SIGN — untested prediction.** If early singleton retrieval improves but final stuck frequency, within-relation person discrimination and address stability do not, the later losses erase the gain. If even early singleton retrieval stays category-only, this objective is not enough to escape the representation problem. Lower answer-readability would expose competition with gold-card teaching. A one-hop improvement with unchanged held-out causal performance is a limited F1 improvement, not a two-hop fix or G_pair advancement. **I do not claim this removes every bad basin.**

### 2. A learned question-token selector with static token contents, added as a zero-initialized query residual

**CHANGE — untested specification.** Add one attention head over **all valid question tokens** using the existing question-span boundary. Cache their original pre-Think contextual states `h_i` and token IDs `t_i`. No predicate mask, vocabulary role mask, relation index, or position relative to `[answer]` is supplied. With `z=norm(register0)`, use

```text
ell_i    = z^T A h_i / sqrt(32)                  for every valid question token
ell_NULL = n^T z + b_n                           NULL content is zero
alpha    = softmax([ell_i, ell_NULL])            temperature 1
u        = sum_i alpha_i E[t_i]                  existing token embedding table
q_new    = heads.query(z) + sigmoid(w^T z+b_g) B u
```

Use `q_new` in both `_step` and `_recall`; keep the ordinary store normalization and hard card retrieval. Initialize `A` from N(0,0.02), `B=0`, and `n,b_n,w,b_g=0`. Create new parameters in an isolated RNG substream after copying the baseline weights. Keep soft token attention at training and primary inference; do not introduce a hard-selector schedule or ST. Ordinary LM/answer/ASK losses train this route. Its contents are question token embeddings only; fetched information influences selection through the existing register. Reader, keys, card values, binder and decoder remain as they are.

**WHY — suggested.** The wire supplies the most direct evidence that a shared static relation-content route can repair F2. This candidate replaces its supplied location with learned selection and retains its zero-residual start. It also lets the selector choose **LINK** when LINK is the active predicate, instead of injecting the terminal REL at every stage. Selection still has to be learned; fix 3 addresses the objective's lack of an order preference if that becomes the measured bottleneck.

**Shown — the transfer property, conditional on selection.** If the selector concentrates on relation token `r`, its residual direction is `B E[r]` in both one-hop and hop 2. There is no separate hop-2 relation map to extrapolate. Relation 2 already trains that direction on one-hop examples. Context determines the attention and scalar gate, but does not replace `E[r]` with a new contextual value vector. This is a useful sharing constraint, **not a proof** that the selector will choose the correct token on held-out questions or that the legacy query will not oppose it.

**COST / INITIALIZATION.** `A`: 1,024 parameters; NULL scorer: 33; gate: 33; `B`: 512. **+1,602; 81,350 total**, about 2% above plain/shared. No new embedding table. A padded 40-token implementation adds roughly 4,160 multiply-accumulates per query evaluation, plus softmax/elementwise work and backward computation; this is arithmetic, not measured throughput. Initial queries and all baseline forward outputs are exactly preserved because `B=0`. Initial baseline gradients through the new route are zero; `B` receives a gradient, and attention/gate learning can begin after `B` moves. Do not initialize both the content projection and every mechanism that could train it to a dead zero path. Allocated parameters and optimizer memory must include the addition even while its residual is zero.

**FAILURE SIGN — untested prediction.** If it selects the relation token at hop 2 yet retrieves the wrong relation, sharing the lexical content was insufficient: inspect the gate, competing legacy query and key geometry before adding another selector. If it cannot select the token on held-out questions, its contextual selection policy did not transfer. If stuck counts rise as with the wire, the easy relation route still competes with learning the person. If first-LINK retrieval falls, it has reproduced F3. Soft mixtures may also encode contextual information in their weights instead of implementing clean token selection. These failures are possible even with high token-position accuracy in practised questions.

**Suggested — disposition of the already-built pooled selectors.** **They are not one of my three fixes.** The existing A4 remains an explicitly specified but untrained comparison under [08]/[09]; this recommendation does not silently replace it. Its two-head module adds **5,202 parameters** with the old query still allocated, for 84,950 total. It reads original contextual question vectors and fetched pooled values, and replaces the query outright rather than preserving its initial forward behavior. [recovery], lines 42–68 and 84–140

**Suggested — what A4 could and could not fix.** A4 removes repeated Think mutation from selector contents and gives a shorter, shared linear composition route; those are real optimization reasons it might help. It provides no new relation identity absent from those contents and no explicit dependency policy. If the contextual REL representation shifts in two-hop contexts, selecting that row can still yield the wrong relation. Even a successful affine transfer probe would establish accessibility, not that ASK training learns the selector. The required [08] probe is therefore sensible. My smaller residual is a different hypothesis, motivated by the wire and by the lack of established contextual transfer; it must not be called an implementation of A4.

### 3. Dependency-frontier CE for the remaining order failure

**CHANGE — untested specification.** Change only the target passed to search set CE on two-hop training questions. Let `l` be the annotated LINK evidence line, `e` its endpoint evidence line and `F` the actually fetched set:

```text
H(F) = {l}  if l is not in F
       {e}  if l is in F and e is not in F
       {}   otherwise
L_search_target = logsumexp(s_all) - logsumexp(s_H(F)), when H(F) is nonempty
```

Keep the existing ASK BCE target, weights, gold phase, one-hop loss and **random teacher insertion order** unchanged. In particular, teacher insertion must still use the ordinary missing-gold set; do not silently pass `H` into it. No order fields are stored in an inference episode. The generator's ordered gold tuple supplies training-only dependency labels, explicitly disclosed. This is one loss-target change, not a change to teacher policy as well. [generator], line 161; [ordered-source], lines 193–209

**WHY — suggested, and the new reason for revisiting ordered evidence.** The previous ordered trial changed both targets and teacher order while the relation-transfer defect was still present; it did not repair held-out relation use. I would not repeat it as a standalone cure for F2. Its new role is conditional: after an unprivileged relation route works, delayed LINK becomes a concrete remaining cause of failure. The saved learned wire failures demonstrate that such a regime can exist. A singleton frontier makes the target endpoint a negative until the prerequisite LINK is fetched, supplying the preference missing from unordered ASK and from score-only answer credit.

**COST / INITIALIZATION.** **0 parameters; no extra model forward pass**. Standalone total remains 79,748, or 81,350 on an explicitly declared fix-2 background. Tiny target-mask computation replaces the set target. Initial inference and teacher insertions match the control; non-gold training loss/gradients intentionally differ. Additional privilege is **training-time hop-order supervision**, not an inference role label. It still has to teach a learned policy; no runtime oracle ensures that the network fetches LINK.

**FAILURE SIGN — untested prediction.** If first-LINK rates rise but person/relation correctness or causal pair scores do not, ordering was not the binding constraint. If the third-opportunity ASK failure survives an earlier correct LINK, ordering alone did not repair the control policy. Random teachers can still produce endpoint-first states, so the remaining training-state mismatch may limit this deliberately isolated target change. Wrong first fetches remain possible. If ordered targets suppress useful recovery or damage one-hop/READS, reject the change at the declared budget. A reduction in F3 cannot be assumed to solve F1 or F2.

### Cost and pass marks apply to all three

**Shown.** The current half-long A4 budget is `B=3.407362074846783e13` counted model FLOPs. Historical full-long runs already exceed the 30-minute constraint: the inspected 5070 Ti wire seed 0 took 2,337.84 training seconds before evaluation. That does not establish feasibility of a new comparison. [09], [wire-original]

**Suggested.** Use Ben's stated free 5070 Ti as the preferred resource basis for any later approved work; incremental GPU rental would be $0 there, but elapsed time and compute remain costs. No current paid quote or reliable new throughput is available, so expected passes per dollar cannot honestly be numeric. Preserve the approximately $24.9 paid budget until a full wave fits the existing admission formula, including all added work. None of these fixes earns an exception to the wave limit.

**Shown — unchanged advancement rule.** Under [08]/[09], a reliability improvement requires the exact paired gain/loss test `p<=0.05`, net gain at least 10 percentage points, and all one-hop/READS/stuck/integrity safeguards, with sample size fixed before outcomes. G_pair cutoffs remain c1/c2 ≥1969/2048, c3 ≥1876/2048, c4/c5/c6 ≥945/1024. Mechanism diagnostics below are not replacement pass marks. A3's existing one-hop phase endpoint cannot automatically be assigned to fix 1: this is a different objective and needs its own reviewed slot specification. A first helpful result also cannot license bundling the three fixes. The independent G_cert/77-of-80 campaign remains separate.

## ANSWERS TO 3a–3d

**3a — suggested: let contextual attention select, but let token identity supply the relation content.** Fix 2 attends over the whole visible question span and reads the existing embedding of whichever token it selects. At hop 2, concentrating on REL produces the same `B E[REL]` trained by one-hop search. The resolved person stays on the existing fetched-card/register route, whose success is suggested by the right-person/wrong-relation counts. No supplied relation position is needed. Transfer still depends on correct token selection, person use, gating and key alignment; this is not a compositionality guarantee.

**3b — shown: nothing in unordered set CE makes LINK first. Suggested: train that preference explicitly if it is the remaining defect.** With the frontier target, `dL/ds_l=p_l-1` and `dL/ds_e=p_e` before LINK is fetched: the loss increases LINK relative to the endpoint. After LINK, the endpoint becomes the target. This does not require answer credit to guess which card is instrumental. Fix 2 provides LINK as a selectable visible token; fix 3 supplies its training-time priority. Turning the wire off on the first request would be a brittle stage rule and leaves its supplied-position privilege intact. ST's derivative `p_i g^T(v_i-mu)` specifies no prerequisite preference, so I would not spend this shortlist on it. [recovery], lines 146–157; [08]

**3c — suggested: the stuck regime is an address-learning problem amplified by timing and scaling; no basin-removal claim is justified.** At a normalized state with squared norm roughly `d`, a linear scorer initialized with independent variance `0.02^2` has output variance about `0.02^2*d`. Thus the initialization is not invariant with width: scorer standard deviation is roughly 0.113, 0.160 and 0.226 at d=32,64,128, before nonlinear and residual effects. The source keeps linear initialization scale and learning rate while changing width and key dimension. Wider runs therefore are not a controlled “more capacity, same optimization” intervention. This is a mathematical scaling observation, not a measured explanation of their larger stuck fraction. [initialization], [width-source]

**Shown.** The width-64 and width-128 rosters have 7/20 and 15/20 stuck runs, and zero G_pair passes. Their recorded parameter counts are 306,932 and 1,203,668; they are diagnostic evidence about scaling, not alternatives within the 80k budget. [rows]

**Suggested / untested.** Fix 1 starts dense singleton discrimination before value-oriented co-adaptation, during the existing optimizer warm-up. It removes the *period with no positive search supervision*, not a proven local minimum. In a degenerate category-only state with equal same-relation keys, the query gradient can cancel even though score-level target errors are nonzero; shared writer gradients can also cancel in expectation when subject features are absent. Adding an objective does not constitute a proof that all such states disappear. I cannot name an initialization, loss or curriculum already shown to remove the basin rather than improve its odds. The necessary evidence is reliable learning across fresh runs and environments, not one rescued seed or a subject probe alone. I would not widen or change initialization simultaneously with fix 1.

**3d — suggested: treat the bimodality as a feedback/optimization hypothesis, not a diagnosed physical phase transition.** There already is 100-step LR warm-up and a smooth own-fetch probability ramp. In the saved long runs, search supervision first turns on around step 1,900, well after that warm-up, and the first own phase appears around 2,850. Fix 1 brings positive search gradients into the existing warm-up and reduces the mismatch before own fetching ramps. It changes what the model learns early; simply extending the original gold-only warm-up leaves the missing search objective missing. Fix 3 removes the first-step target ambiguity, if needed. These may smooth learning without softening deployed retrieval. They remain hypotheses; the two-peaked final scores do not establish a critical threshold or guarantee that warm-up, auxiliary loss, or curriculum can make every seed converge. [curriculum], [plain-run], [wire-run]

## MEASUREMENT

**Suggested — the one measurement: the already-specified affine relation-readout transfer assay on the 40 saved plain/shared controls.** It resolves the largest uncertainty behind fix 2: whether the contextual row already exposes a relation identity that transfers. This uses frozen model weights and an external diagnostic readout, not new model training. It is proposed only; no checkpoint or probe was loaded or fitted here.

**Untested — specification.** Use [08]'s existing contract: original pre-Think contextual state at the true question relation row; 3,000 one-hop plus 2,000 practised two-hop calibration questions; independent same-composition development data; affine softmax readout with fit-only standardization and L2 chosen from {0, 1e-4, 1e-2, 1}; separate 2,048-world held-out, one-hop and practised panels. Follow its convergence and static-embedding calibration controls. The diagnostic knows the relation row and label; neither enters model inference or training. The readout fit is diagnostic-only. Report all 40 seeds and the prespecified 33 fresh-learned seeds, without selecting models by probe success. This reuses the current A4 prerequisite rather than creating another evaluation program.

**Untested — result that flips my ranking.** Use [08]'s per-seed readability flag: at least 95% held-out relation accuracy and at most a 2-percentage-point drop from that relation's one-hop accuracy. If **at least 25 of the 33 learned controls fail this flag despite valid, strong calibration/development controls and a successful static-embedding control**, move fix 2 ahead of fix 1: transferable relation content would be a broad demonstrated interface weakness even after one-hop learning, so addressing it deserves the first intervention. If at least 30/33 pass the flag, keep fix 1 first and weaken the argument that fix 2 needs different contents; its remaining case is the shorter, shared query route. That would also strengthen A4's existing downstream-selection premise, without establishing that A4 will learn it. Intermediate results stay mixed. Invalid fits or failed calibration do not change the ranking.

**Suggested — limitation.** An affine probe can miss nonlinear usable information; a successful one does not show the trained query uses it. This measurement changes which mechanism is worth paying to repair, not any G_pair threshold. Its cost is frozen reader passes plus small external readout fits on CPU; actual elapsed time is unknown and should not be advertised as a completed cheap run. It is far narrower than training another 40 full models, and no new paid resource is proposed for it.

## FOR BEN

**Suggested, with all fixes untested.** Your model often learns what kind of fact to look for before it learns whose fact it needs. Even when it learns the person, it can treat the second lookup as a separate trick that only works for relations practised in two-hop questions. The relation shortcut helps, but sometimes leaves it doing the lookups in the wrong order. I would first teach ordinary one-fact search during the same early phase that teaches reading; that adds no parameters and directly targets the stuck runs. Then I would let it learn which question word to use while carrying that word's identity into the search. These are concrete repairs to try, but we do not yet have evidence that they turn the current seed lottery into dependable learning.

## Source links

All paths below refer to inspected local text/source. Checkpoint bytes were not opened.

[08]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/08-pairsuite-adjudication.md
[09]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/09-reconciliation.md
[rows]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-pairsuite-20260919/rows.jsonl
[probe-a]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-interface-probes-20260919/probe_a.json
[probe-b]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-interface-probes-20260919/probe_b.json
[probe-c]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-interface-probes-20260919/probe_c.json
[interface-source]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_interface_probes.py:199
[writer]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:171
[training-forward]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:503
[bypass]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/answer_path.py:114
[query]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:483
[store]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/store.py:33
[question-start]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:410
[generator]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/toy_ladder.py:119
[wire]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_relation_shortcut.py:56
[recovery]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_recovery.py:42
[ordered-source]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_ordered_evidence.py:193
[fixed-eval]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_handoff_diag.py:367
[curriculum]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/train.py:81
[initialization]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:337
[width-source]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_gpu_port.py:109
[six-relations]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-ladder6-20260919/REPORT.md
[plain-run]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-20260919/control/runs/long-s12-12000.json
[wire-run]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-relcut-20260919/control/runs/relcutlong-s0-12000.json
[wire-original]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-relcut-long-20260919/runs/relcutlong-s0-12000.json
