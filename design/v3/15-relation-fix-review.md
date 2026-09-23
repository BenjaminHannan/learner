# Premonition: review of Fable's attack on the relation fix

19 September 2026. Astra. Track A only; analysis before implementation.

**Decision — suggested.** Accept the decomposition: examine **wire → wire plus real-fetch guard → guarded wire plus cap → supervised lexical typing**, before considering the complete B-versus-plain comparison. Withdraw B's immediate priority and the unconditional choice `eta=.25` in [14]. Keep one-hop first-request activation in the first two comparisons, explicitly retaining its risk. Removing the contextual gate and detaching the embedding are further changes, not consequences of adding a guard or learning a vocabulary partition. Candidate A remains deferred.

**Scope — shown.** I read [14] and [wire] first, then the relevant local source, designs, saved pair-suite JSONL and the two historical 40-run JSON rosters. I used standard-library text tabulation and arithmetic and added only this document. No project imports, tests, training, checkpoint or tensor loading, GPU, SSH, spending, messaging, job control or credential inspection occurred. I did not inspect the active teacher-delay experiment's outcomes. Measurements below are specifications, not results. VERIFIED means inspected source, saved-record arithmetic or a stated mathematical derivation; it does not mean a runtime reproduction. This file revises [14], not the active A3 contract in [12]/[13], and authorizes no execution.

## Attack 1 — decompose B on the existing wire

**VERIFIED.** The wire reads the static token embedding at `q_span[:,1]-2`, adds `g(z) W_r E[r]` after the legacy query, and uses that route in both `_step` and `_recall`. It has no fetch guard or cap. At d=32, k=16, its extra parameters are `512+33=545`. B in [14] replaces the supplied location with a 99-parameter classifier, adds a guard/cap, **removes the 33-parameter contextual gate, and stops the residual's gradient into E**. The last difference is absent from Fable's three-item decomposition: [wire] calls `self.embed(...)` without detaching it; [14] uses `stop_gradient(E[t])`. Neither gate removal nor detachment should be silently bundled into “+cap.”

The generator has exactly three attribute token IDs; relation 2 is excluded from two-hop training questions but present in one-hop questions. Context-free typing from generator labels is supervised vocabulary classification. It is scientifically much closer to an externally taught vocabulary partition than to discovering a contextual relation selector. Its success is plausible, **not verified or certain**: the embeddings move, a linear classifier need not meet .99 confidence everywhere, and a false confident classification can matter.

**VERIFIED — historical records, not a new experiment.** Re-tabulation gives:

| Shared-pooling roster | G_pair | Historical stuck: one-hop <384/512 | Fresh stuck: c1 <1536/2048 | First logged recall >.3 before step 2850 | Never logged >.3 |
|---|---:|---:|---:|---:|---:|
| Plain | 0/40 | 7/40 | 7/40 | 21/40 | 7/40 |
| Wire | 21/40 | 16/40 | 17/40 | 12/40 | 16/40 |

The current plain and wire runs report RTX 3060 and RTX 5060 Ti respectively, both Torch 2.8.0+cu128. This is not an environment-matched estimate of wire harm. The gate/escape definitions are those in [11]; saved logs do not locate an exact escape time.

Among the **two** fresh-learned, G_pair-failing wire/shared seeds, 14 and 30, request 1 is a non-LINK attribute on all 4,096 questions; request 2 is the correct LINK on 4,094. The .669189 “other/wrong-relation” frequency is one category, not the entire non-LINK frequency. Here the zero first-LINK count does establish a non-LINK→correct-LINK sequence on 4,094/4,096 questions even without individual traces. It does not establish why that order occurs or whether disabling the residual fixes it.

**Verdict: SUCCEEDS as a design/attribution objection; efficacy and cost/power superiority NEED MEASUREMENT.** A wire control provides successful transfer to preserve and a concrete order defect to perturb. But “more power per dollar” is not established by its nonzero pass rate. If a guard merely rescues those two learned failures, its historical ceiling is 21→23/40: 5 points, with two gains/no losses giving p=.25. That fails both the existing exact-test rule and its 10-point effect floor. The guard must also improve reliability elsewhere, or earn only a narrow diagnostic result. Historical rows are valuable for frozen-weight interventions and planning; they cannot replace fresh matched training controls under [08]/[09].

**Revised design/sequence.** Define privileged prototypes, retaining the original wire's gate, embedding gradients, initialization, pooling, losses and teacher order:

```text
q0 = heads.query(z)                     # includes the existing bias
v  = W_r E[r]
g  = sigmoid(w_g z + b_g)
m  = any(episode.fetched[:, :store.null])
h  = (question contains no LINK token) OR m

W:    q = q0 + g*v
WG:   q = q0 + h*g*v
WGC:  q = q0 + h*clip(g*v, eta*stop_gradient(||q0||))
```

For WG/WGC, identify LINK from the visible fixed-grammar input using its supplied lexical identity, and disclose that additional parsed role. Do not read evaluator `hops`, gold fields, the true friend or the fetched card's correctness. This is deliberately a privileged mechanism experiment. Use the real-card mask, not `episode.count`, which also counts NULL insertions. No-ASK/NULL alone cannot open the guard; any real insertion, including a teacher distractor, can. Implement the same query rule at both call sites while retaining `_recall`'s existing distinct eligibility convention. For WGC's cap only, bypass addition when the legacy-query norm is at or below the store normalization epsilon; freeze that epsilon and the clip's zero-vector derivative convention. WG retains W's norm handling.

Cap **the applied vector `g*v`**, not just `v`, so its measured dose and cap agree. A later typing-only substitution retains g and the residual's gradient into E: classify detached embeddings as in [14], then project the selected undetached embedding. Retain [14]'s confidence/uniqueness rules and type-CE definition. It adds 99 parameters to the wire, for +644 / **80,392 total**, rather than being [14]'s +611 B. Gate removal and embedding detachment each need an explicit subsequent ablation if the claim concerns their effects. Original B would still total 80,359. No new implementation is made here.

A final B-versus-plain comparison can establish the complete package's net benefit over the unprivileged incumbent and account for its extra supervision/compute. The decomposition establishes effects conditional on a working wire; it cannot by itself establish that end-to-end comparison. Both questions are legitimate, in that order. Keep A3-teacher-delay-v2's current work separate; any future trained relation contrast freezes one common schedule in both arms after that result, with a new contract if its background changes.

## Attack 2 — measure residual size and bound what the cap can do

**VERIFIED.** `gate_report` currently logs mean gates by loop/hop class plus norms of learned weights. It does not record the per-request residual/query norm ratio. A gate average and `||W_r||` cannot reconstruct it. No requested ratio is available in the inspected saved text; no checkpoint was loaded here.

**Verdict: SUCCEEDS against an ungrounded eta; the claim “large ratio predicts failure, small ratio proves safety” FAILS as a general implication.** A large residual parallel to q0 can be clipped without changing the normalized query at all. Conversely, a modest rotation can reverse a tiny card margin. At fixed weights and state, a residual below the cap is unchanged; that limited preservation statement is exact. It is not a guarantee about a newly trained, guarded, gate-free or detached-embedding model.

**Revised pre-build assay — specified, unrun.** Add the norm instrument to the relation-swap/transport assay, preserving its comparisons. Use all 40 saved wire/shared checkpoints, with all 40 plain/shared checkpoints for the original donor assay. Keep the 21 historical wire G_pair passers and the historical fresh-learned strata as named descriptive strata; retain every other seed. On a new, manifest-fixed 256-world development panel, record at each scheduled opportunity:

```text
a = ||q0||
b = ||g*v||
r = b/a
cos(q0, g*v), gate g, ||v||,
native/capped endpoint and best-wrong margins, cap activation,
ASK, selected card/NULL/no-ASK, real-fetch history and correct-LINK history
```

Report request 1 and request 2 separately for one-hop relations 0/1/2 and two-hop practised/held-out questions; also retain request 3 for recoveries. Report all held-out request-2 states and the native-correct-LINK-first subset separately. “Hop 2” must not silently mean “second successful fetch.” Ratios exist even when ASK is off; publish that stratum. Near-zero q0 and tiny residual directions are separate counts, not finite ratios manufactured by division clamping. Per seed, publish medians, 90th/95th percentiles, maxima, histograms and sample counts; do not average gates before forming ratios or pool questions into independent seeds. Exclude diagnostic `_recall` calls from native request telemetry.

At the **same frozen states**, score the unchanged query and caps .25 and .50 with identical keys, eligibility, age biases and ASK. Record actual endpoint/wrong-person/ranking changes, not only norms. Separately replay whole native episodes under W, WG, WG+.25 and WG+.50: changed first fetches change later states, so a cached-state intervention is insufficient. Add c4 and c5 twin edits to this diagnostic panel, 256 world pairs each, preserving the existing edit semantics and joint-correct counting. These smaller panels are developmental diagnostics, not G_pair or certification. All labels remain in the evaluator. Measure and charge the added CPU work; no throughput/cost claim follows from this specification.

**Eta decision fixed before those measurements.** Consider only `{.25, .50}`; no outcome-driven expansion of the grid. Call a cap *eligible* when, relative to **uncapped WG**, every one of the 21 historical passing wire seeds has at most a 5/256 reduction in each of one-hop relation-2 accuracy, held-out native accuracy, c4 joint accuracy and c5 joint accuracy on the new diagnostic panel. Require the same per-cell limit for the equally weighted mean across all 40 seeds, and no more than a 5/256 loss in correct-LINK-conditioned endpoint selection in any of those 21 seeds with at least 128 such states. Insufficient subset coverage, invalid denominators or invalid instrumentation is inconclusive, not a pass. These are conservative engineering screens, not confidence-certified non-inferiority.

| Measurement outcome | Pre-fixed choice |
|---|---|
| Applied ratios are all ≤.25 on relevant WG states, and .25 is eligible | eta=.25; clipping is inactive there. Check numerical boundary/parity explicitly. |
| Some ratios exceed .25, but .25 is eligible | eta=.25. Large dose was not necessary for the measured outputs; report how often clipping changed margins. |
| .25 fails, .50 is eligible | eta=.50, explicitly relinquishing the .25 geometric bound. |
| Neither qualifies, ratios/states are invalid, or necessary coverage is inadequate | No cap is selected; defer WGC and original B. Do not silently remove the cap or exceed .50. |

Thus high ratios trigger a necessity check, not an automatic larger eta. A low mean or 95th percentile alone never earns “safe.” The final eta is development-selected by this disclosed fixed rule, then frozen before any fresh training comparison; that comparison is independent validation. A failure of WG itself cannot be repaired or relabeled by a cap screen. Norms of the trained gated wire also do not authorize removing its gate.

**Cosine bound — VERIFIED by geometry, not by training.** Let `u=q0/||q0||`, `e=delta/||q0||`, `||e||<=eta<1`, and `u'=(u+e)/||u+e||`, outside the normalization-epsilon region. The ball of possible `u+e` is tangent to a ray at angle `arcsin(eta)`, giving the tight bounds

```text
angle(u,u') <= arcsin(eta)
u·u'       >= sqrt(1-eta^2)
||u'-u||   <= sqrt(2-2*sqrt(1-eta^2)) = D(eta).
```

At .25: at most **14.4775 degrees**, cosine at least **.9682458**, and `D=.2520086`. For any unit person direction or unit card key p, `|(u'-u)·p|<=.2520086`; for a two-card score margin, the absolute change is at most **`.5040172*kappa`**, with unchanged age bias. A pre-existing margin larger than that is protected at this fixed state; smaller margins are not. “Only 3.18% person harm” would confuse alignment with the old query with alignment to the correct person.

Under the extra assumption `delta` is perpendicular to q0, projection onto the old query shrinks by at most `1/sqrt(1+.25^2)=.9701425`, about **2.99%**. If the residual is only known to be perpendicular to a separate person direction, its positive person projection can shrink by as much as a factor `1/(1+.25)=.8` from normalization; perpendicularity to the full query was the stronger assumption. In entangled learned keys even that person-orthogonality assumption is unverified. At eta=.50 the general query cosine bound weakens to .8660254 and the single-direction bound to .5176381.

**Plateau prediction — NEEDS MEASUREMENT.** If excessive applied residuals reduce person discrimination, WGC should have more teacher-window escapes and fewer fresh stuck runs than WG, while preserving post-LINK endpoint retrieval. WG alone need not restore escapes because one-hop request 1 is still exposed. A cap limits a single state's geometric disturbance; it does not bound cumulative gradient changes, a top-1 trajectory, or the number/probability of training escapes. It may also prevent a needed correction. Final checkpoints cannot establish what residual magnitudes were during the plateau; later authorized training needs passive norm/margin telemetry at the existing log cadence. Escape timing remains secondary and cannot rescue failed advancement.

## Attack 3 — one-hop activation versus relation-2 supervision

**VERIFIED.** [14]'s `n_link=0 OR m` leaves one-hop request 1 active. Under the original losses, a teacher one-hop fetch supplies its sole gold card; subsequent missing-evidence CE then has no target. In gold mode search loss has zero weight. The type loss updates T,c only and is not a signal teaching `B E[2]` where to point.

**NOT VERIFIED.** The proposition that the one-hop residual causes the wire's additional stuck runs. Plain's successful one-hop retrieval shows that an eventual solution can do without the residual; it does not show that the residual is harmless or dispensable along all training trajectories.

**Verdict: SUCCEEDS as an unresolved risk in [14]; FAILS as a cost-free proposal to switch off all first requests.** My choice for the initial WG/WGC comparisons is **no**: do not additionally disable one-hop request 1. It supplies the ordinary, reliable evidence-CE training path for relation 2's projection. That path is precisely why the transfer argument can refer to a relation-2 vector trained on one-hop addressing. The risk is retained and measured, not claimed away by the guard.

If the branch is off until any real fetch for *all* questions, relation-2 gradients are not mathematically zero everywhere: an own one-hop episode that fetches a wrong real card while its answer remains missing can train B on a later request. But correct teacher/own first fetches remove that loss, and NULL/no-ASK leaves the branch off. This is an error-dependent supply of later states, not the first-request training signal asserted in [14]. Training B on relations 0/1 at practised two-hop states does not by itself determine its action on E[2]. There are maps that agree on those practised embeddings and differ on the held-out one. Withdraw the original transfer justification for an all-first-off version.

**Revised boundary.** If WG/WGC cannot satisfy the fresh stuck and one-hop safeguards, stop their advancement. Do not silently turn off one-hop inference and retain the same training claim. A possible *separately specified successor* would use a training-only one-hop query branch: first-request q0 and store keys/temperature/age bias detached, relation embedding detached, the bounded B residual active, and ordinary one-hop evidence CE updating B alone. That would give relation 2 an explicit signal without using its residual for native first retrieval. It adds an auxiliary objective and compute; its coefficient, shared-gradient/global-clipping policy and controls would need a new contract. It is not the current B, not built, and not part of the proposed first comparisons. This explains where the missing supervision could come from without pretending it is already present.

## Attack 4 — any real card can open the guard

**VERIFIED, with two corrections.** Across the 33 fresh-learned plain/shared seeds, request-1 counts on 67,584 held-out questions are:

| First card | Count | Fraction of all questions |
|---|---:|---:|
| Correct LINK | 60,345 | .892888849 |
| Asker, requested relation | 3,726 | .055131392 |
| Another person's LINK | 887 | .013124408 |
| Correct endpoint | 57 | .000843395 |
| Other attributes | 2,569 | .038011955 |
| NULL / no request | 0 | 0 |

Thus `.107111151` fetched a real card other than the correct LINK, while `.093986742` fetched a literally non-LINK card. “About 11% non-link” conflates the latter with wrong-owner LINK cards. A wrong card need not leave register 0 representing the asker: insertion/binding/Think can change it. The register's semantics were not measured by these class counts.

More importantly, `CardStore.eligible` excludes previously fetched real cards, and the wire `_step` passes that mask. **The 5.513% that already fetched A(asker,r) cannot fetch that same decoy again at request 2** in this one-card-per-fact toy. It can still contaminate the workspace/answer and the residual can misdirect other choices. Diagnostic `_recall` omits the fetched mask; its top-1 is not evidence of a native repeat fetch. Both [14]'s counterexample and Fable's literal decoy story require this correction.

**Verdict: SUCCEEDS as a guard-validity objection; a numerical expected c4/c5 loss NEEDS MEASUREMENT.** The saved diagnostics are c3 marginals, not twin trajectories under WG, and first errors need not be fatal. The strongest defensible arithmetic is a conditional risk calculation, not an observed effect:

* If both twins had marginal early-exposure rate `p=.107111151`, the fraction with at least one exposed twin lies between **10.711% and 21.422%**. Independent exposure would give `2p-p^2=20.275%`, about **208/1024 pairs**. These are potential affected pairs; they become loss estimates only under the added assumption that every affected pair would otherwise pass and is made to fail.
* Narrowing to a **wrong first card with the exact asker decoy still available** excludes the 3,726 consumed decoys and the 57 already-correct endpoints: `p*=3456/67584=.051136364`. Its analogous pair-exposure range is **5.114–10.227%**, independence value **9.966%**, about **102/1024 pairs**. This is one failure route, not a bound on all possible guard harm.
* G_pair permits only **79/1024 failed pairs**, 7.715%, in either c4 or c5. Under the broad independent-exposure scenario, at most about **38.1%** of exposed pairs could be fatally affected even if there were no other errors. Catastrophic exposure at these rates is plainly not an acceptable assumed cost.

Neither c4/c5 marginal exposures, twin correlations, counterfactual recoverability nor treatment-induced changes are known. The unconditional mathematical bounds on actual new loss are much weaker; the figures above depend on transferring the c3 rates to twins and fixing the exposure population. In particular, they do not prove that c4/c5 will lose 20 points, or even that either will decline. Native K=4 permits a third retrieval, so a bad first card can sometimes be recovered from.

**Revised decision.** Retain the simple guard for the narrow mechanism diagnostic, **not as an accepted reliability fix**. Require the diagnostic c4/c5 preservation screens above and the prospective relative no-harm safeguards below. Log first-card classes jointly with later guard openings, decoy availability, eventual LINK/endpoint coverage and both-twin correctness. Compare factual and changed-link twins separately from changed-value twins. A measured failure of these safeguards blocks advancement; it is not waived by aggregate endpoint gains.

A perfectly typed card-side LINK guard would remove openings caused solely by attribute cards, but would still open after another person's LINK: the historical `.013124408` marginal gives up to **2.625%** pair exposure, about 27/1024, under the same transfer assumptions. LINK type is not proof of the correct owner or completed dependency. A learned card-side classifier also introduces errors, supervision and cost. Do not add it now or call it sufficient; reconsider a separately specified card-type/owner condition only if the measured false-opening route is consequential. None of these guard variants receives a gold LINK check at inference.

## Attack 5 — privilege ledger and allowable claim

**VERIFIED.** [03] requires disclosure of training role targets and supplied inference locations, and distinguishes privileged certificates. B's type targets come from the generator; its hard classification receives no answer/search gradient. This is a new privilege entry even though runtime lookup uses learned weights instead of a hard-coded attribute-ID mask.

**Verdict: SUCCEEDS.** Add a separate **token-type targets** column, rather than concealing it in generic ASK supervision:

| Recipe/mode | Supplied inference relation/LINK roles | Token-type targets | Other supervision/privileges |
|---|---|---|---|
| W/WG/WGC training and native eval | Relation location supplied; WG/WGC also use supplied lexical LINK detection | None | Existing evidence targets/teacher policy in training; own fetch history at eval |
| Typed successor training | No supplied relation position or token-ID role mask; learned classifier deployed | ATTRIBUTE/LINK/OTHER from generator, class-balanced CE, explicit weight | Existing evidence/answer targets and teacher policy; full added compute disclosed |
| Typed successor native eval | Learned lexical classifier and own real-fetch mask | None supplied at eval; training privilege persists in the recipe | No gold roles/cards/hop tags/true friend; labels only for external scoring |

After a successful **fresh G_pair comparison only**, the exact earned label is:

> **Track A fixed-layout G_pair improvement with generator-supervised lexical typing, evidence-supervised training, and a shared relation residual.**

Only after satisfying the complete separate G_cert contract and its independent 77/80 campaign could a B-based recipe earn:

> **Track A fixed-layout autonomous hard-card retrieval and held-out-relation two-hop composition, with generator-supervised lexical typing and evidence-supervised training; G_cert reliability certificate under the registered toy distribution and compute budget.**

Attach the exact deployed gate/cap/gradient policy, ledger, seed population, failure record and statistical statement. At 77/80, [03]'s one-sided 95% lower bound is about .90593 for passing that *specified per-seed gate*. Neither the title nor that bound claims universal reasoning or 95% reliability. No such certificate has been earned here.

**It cannot be called “learned relation selection.”** “Supervised lexical type classification with a learned shared relation projection” is accurate. It learns numerical weights for an externally taught fixed-vocabulary partition; it does not demonstrate contextual selection or discovery from answer loss. Context-free lexical typing of these toy IDs does not transfer as specified to Track B's real text, polysemy or contextual roles. **No Track B inference is permitted.**

## Candidate A and the requested wire-direction transport

**VERIFIED / decision.** Accept the request. A's practised-only alignment objective still admits [14]'s exact counterexample; matching those examples does not constrain the held-out two-hop branch. Keep A deferred. Its donor/transport diagnostic remains useful even when A is not the next treatment.

Add the actual learned wire direction for each p in {0,1}:

```text
dW = W_r E[2] - W_r E[p]
qW_p = q0_p + g_p W_r E[p]                # raw wire request at native p state
uW_transport = normalize(qW_p + g_p*dW)   # hold register and gate fixed
```

This substitutes the relation vector at a fixed state and preserves its learned scale. Do not add raw dW directly to a normalized query: that invents units. Report dW's norm, the actual normalized displacement `uW_transport-normalize(qW_p)`, and its cosine with the **within-wire** one-hop difference d1. Include the two p contrasts separately, undefined tiny differences, matched-native-correct-LINK coverage, margins, ungated top-1 and native-ASK-gated selection, endpoint/person/relation errors and all seed strata. Use held-out target-state keys/eligibility/age bias as in [14]; retain native held-out and within-model donor/transport controls.

**Important limitation.** Same seed does not align the query/key coordinate systems of separately trained plain and wire checkpoints. Run dW transport inside its own wire checkpoint, with that checkpoint's d1 beside it; run the original d1 assay separately inside the paired plain checkpoint. Compare their scalar retrieval/margin effects by seed. A raw wire vector inserted into a plain query is not an interpretable transfer intervention without an additional independently justified alignment, which is outside this assay. A gate-free B inference cannot be validated simply by demonstrating successful gated transport.

## Sources and reproducibility

Saved-record calculations select rows by the exact `.../claude-keypool-20260919/control/ckpt` and `.../claude-keypool-relcut-20260919/control/ckpt` directories; fresh-learned means c1≥1536. Request fractions use `cells.c3_own_heldout_two_hop.diagnostics.by_request` class counts divided by all `diagnostics.questions`, equally weighting the equal-size seed panels. Historical stuck uses each run JSON's `validation.fixed_K4.one_hop.correct<384`; escape is the first `curve` entry with `gold_recall_at_4>.3`, with the teacher-window boundary at step 2850. Exact hypothetical power sums the multinomial probabilities over all (g,l) satisfying the declared test/floor; it is arithmetic, not model execution.

Text input SHA-256 identities read in this review:

```text
14-relation-fix.md: e8b74a07bdd107bb0f7b1df8c9780ee63cb76ff6e3c301eef308bd66ab7ec10a
premonition_relation_shortcut.py: 6a692136bf6d00a2b4ba7545e28a6e1d8bbd44fc6b88a0d9776b8c9da82343e5
frozen/model.py: f6d8c36093f8d392a7a680db3ab46b5dc6b28bee3475d6cb9e3e58be6404fda5
frozen/store.py: 62c75d70b369daf61cf862b28f87aa64bf6037314dd1a39a7df994b81d2b9531
rows.jsonl: e3eb5bccdcf885910fae36913c1edaa54b1ce7ba6eedfa9f7c87bb58f09a727e
```

[03]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/03-evaluation.md
[08]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/08-pairsuite-adjudication.md
[09]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/09-reconciliation.md
[11]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/11-fix-review.md
[12]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/12-teacher-delay-contract.md
[13]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/13-launch-rulings.md
[14]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/14-relation-fix.md
[wire]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_relation_shortcut.py

Supporting source: [frozen model](/Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:446), [store eligibility/normalization](/Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/store.py:83), [generator](/Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/toy_ladder.py:111), [pair edits and counting](/Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_pair_suite.py:174), [native fixed-loop evaluation](/Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_handoff_diag.py:367), [saved rows](/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-pairsuite-20260919/rows.jsonl), [plain run records](/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-20260919/control/runs), [wire run records](/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-relcut-20260919/control/runs).

## Ordered build sequence, controls and pre-fixed pass marks

These are proposed design gates, not permission to build, load checkpoints or run anything in this analysis-only turn. The full future launch freeze still needs explicit resources, source/runtime identities and integrity validation. Existing historical rows remain untouched.

1. **First relation work: additive passive ratio/transport instrumentation plus frozen-weight WG/cap replay.** Control: the same saved wire checkpoint with its unchanged W query; within-model donor/native controls for transport, and WG as the cap control. Use all 40 saved seeds and the diagnostic panels specified above. Instrumentation passes only with unchanged outputs/weights when observation alone is enabled, intact episode isolation, correct NULL/denominator handling and no diagnostic labels entering native inference. The guard's pre-fixed positive mechanism signal is first-LINK at least **244/256** and a held-out native answer gain at least **20 points**, separately in historical seeds 14 and 30, while every historical G passer loses at most **5/256** in each of one-hop relation-2 accuracy, held-out native accuracy, c4 and c5 relative to W. Require that same no-harm limit in the all-40 mean. Choose eta only by Attack 2's rule. Publish negative/mixed results; failure defers the positive mechanism claim and any combined B build, but does not prove that training with a guard cannot work. This diagnostic earns no G_pair advancement and says nothing causal about training escapes.

2. **First trained relation contrast, if subsequently admitted: WG versus freshly trained W.** This implements the one guard change only, on one frozen shared-pooling schedule/background, after A3's current independent work is resolved. Historical saved wire runs are planning evidence, not controls to be mixed with new jobs. Register **80 fresh independent seed pairs** before results, with matched initial shared tensors, training streams and execution environment, both arms paying the same frozen model-FLOP budget and reporting exposure differences. Primary: fresh seed-specific G_pair with `c1/c2>=1969/2048`, `c3>=1876/2048`, `c4/c5/c6>=945/1024`. With g gains, l losses, d=g+l, advance only if **`sum(comb(d,k), k=g..d)/2^d <=.05`** (p=1 if d=0), **`(g-l)/80>=.10`**, no increase in fresh c1-stuck count, and every integrity/budget/safeguard check passes. Retain [08]/[09]'s one-hop and 512-world READS lower-bound requirements **strictly >-.02**, using 100,000 paired hierarchical bootstrap resamples and the 5,000th sorted difference. For this relation sequence add the same >-.02 safeguard for each continuous c2–c6 score, keeping twin pairs intact. Missing/invalid jobs remain failures and block advancement; no outcome-based expansion or selective rescue. Under the illustrative historical .525→.725 pass rates with independent arm outcomes, exact primary power is **49.73% at n=40, 79.78% at n=80**; safeguards reduce overall power and the new schedule may change both rates. This is why the old 40-run baseline is not a claim of adequate power or a funded launch plan.

3. **Then WGC versus WG, with the selected eta frozen.** Use a separately registered fresh matched roster and the same primary/safeguard pass mark as item 2; never compare only surviving/learned checkpoints. This tests whether bounding the applied vector improves whole-roster reliability while preserving transfer. More escapes alone is a mechanism observation, not advancement. If WG only earns a diagnostic result and cannot advance, a cap rescue experiment requires an explicitly new contract; it cannot silently treat WG as an accepted background or bypass its failed safeguards.

4. **Only then substitute supervised lexical typing.** Control: the accepted guarded/capped privileged wire; treatment changes the source of relation/LINK identification and adds disclosed type CE, retaining the contextual gate and embedding-gradient policy. This is primarily a **privilege-replacement/non-inferiority** question, not a mandatory additional 10-point superiority claim. Pre-fix paired one-sided lower bounds >-.02 for every c1–c6 score and READS, **G_pair pass-probability difference lower bound >-.05**, no increase in fresh stuck count, correct inference-label noninterference, and complete type acceptance/error reporting. Use the same 100,000-resample seed-pair method for the binary probability difference, without treating worlds as independent seeds. Its fresh roster size and precision planning must be frozen in its own later contract; no claim of adequate power follows from reusing n=80. If gate removal or embedding detachment is still desired, give each an explicit subsequent preservation contrast under those same gates. Do not call the typing-only treatment original B.

5. **Last: complete selected recipe versus the unprivileged incumbent**, both freshly trained on the same declared background and budget, using item 2's superiority rule and safeguards. This is the package claim the decomposition cannot supply. Keep A/Q3/separate pooling and teacher-policy changes out of the treatment. G_pair advancement still does not grant G_cert; any certificate remains a separately frozen, fresh 77-of-80 campaign under [03]. Adaptive developmental contrasts do not collectively become one familywise 95% claim.

## For Ben

Fable is right that we should first find out whether delaying the existing relation shortcut until a real fetch fixes its order mistake, then whether limiting its strength helps training. Teaching a filter the three relation words would not answer either question. The guard still has failure cases, and turning the shortcut off on all first lookups would remove its reliable training signal for the held-out relation. I have replaced the fixed .25 recommendation with a declared measurement rule, kept the stuck-run safeguard, and separated a useful diagnostic result from a reliable-model claim. This review adds no code and launches nothing.
