# Fable's attack on the fixes: revised decision

19 September 2026. Track A only. Analysis before implementation.

**Suggested — decision.** Fable's main attack succeeds. Put a **fixed longer teacher window** ahead of the new early-search loss. Keep the token residual unbuilt until an unprivileged recipe has addressed the plateau; its contamination risk is real and its benefit remains untested. Keep dependency-frontier CE unbuilt until an unprivileged model actually exhibits the delayed-LINK defect. Withdraw the relation-identity-probe rule that flipped fixes 1 and 2.

**Shown — scope.** I recomputed statistics from 190 existing run JSONs, read the relevant source and pair-suite JSONL, and wrote this file. No training, tests, project imports, checkpoint/tensor-dataset loading, GPU, SSH, spending, messaging, or credential inspection occurred. “Shown” denotes source facts and saved-record calculations, not a fresh runtime reproduction; “suggested” denotes an inference or decision; “untested” denotes a prediction or proposed execution. This file revises [10]'s recommendations. [08] and [09] continue to govern evaluation; no new run is authorized and no evaluation hurdle is relaxed.

## Evidence audit: VERIFIED, with qualifications

**Shown — exact roster and calculation.** The four current directories [plain], [plain-pool], [wire], [wire-pool] each contain 40 run JSONs with seed IDs 0–39 once each. Adding the 15 old plain and 15 old wire runs gives the 190-record reading-loss comparison. For each record I used `validation.fixed_K4.one_hop.correct <384` for historical stuck status, and the first logged `curve[*].gold_recall_at_4 >0.3` for escape. No escape means no qualifying saved log through that run's end. These are retrospective summaries; the 190 rows include related seeds/recipes and are not 190 independent identical trials.

**Shown — what the recall metric means.** Despite its name, `gold_recall_at_4` here is the first opportunity's **ungated top-1 gold recall**, averaged in the training logs. It is not four-card recall, not necessarily an actual ASK, and not a fixed development-panel score. `_recall` divides each hit by the question's gold-set size ([model], lines 656–667). With equal one-/two-hop question counts, perfect first retrieval has ceiling `0.5*1 + 0.5*(1/2) = 0.75`. If the right category is found but the person is uniformly random among six, the analogous expectation is `0.75/6 =0.125`. That arithmetic explains the plateau's interpretation; recall alone does not directly classify every request's kind/person.

### E1 — plateau verified; universal 100-step timing not verified

**Shown.** Plain/shared medians reproduce the handoff:

| Logged step | Eventually stuck (7) | Eventually learned (33) |
|---:|---:|---:|
| 1,900 | 0.04250 | 0.03875 |
| 2,000 | 0.08891 | 0.08641 |
| 2,200 | 0.12375 | 0.12406 |
| 2,400 | 0.12234 | 0.12719 |
| 2,800 | 0.12469 | 0.37297 |
| 3,200 | 0.12469 | 0.51313 |
| 3,800 | 0.12812 | 0.59922 |
| 12,000 | 0.12453 | 0.74906 |

**Shown.** The wire/shared medians have the same qualitative shape: stuck/learned are 0.12461/0.12359 at 2,200 and 0.12523/0.74906 at 12,000. All 160 current runs first log teacher at 1,900 and own mode at 2,850. However, even using the lower threshold recall ≥0.10, the interval from the first teacher log to threshold ranges from 100–400 updates for plain, 100–500 for plain+pool, 50–150 for wire, and 50–100 for wire+pool. **Withdraw “every run reaches ~0.12 within ~100 steps.”** This does not weaken the evidence for a common early plateau. Logs average training observations and occur every 50 updates, so they do not identify exact transition times.

### E2 and E3 — verified, including the omitted thirtieth stuck run

**Shown.** The handoff's 29 stuck runs never exceed 0.6. Adding the single plain+pool stuck run gives **30/160 stuck runs; none ever exceeds even 0.3 in a saved log**. Their maximum logged recalls are all ≤0.15625. Thus there is no logged high-retrieval-then-collapse trajectory in this stuck population. Brief unlogged excursions are not excluded, nor is loss of a reader feature before search starts.

**Shown.** Escape histograms match exactly. Numerical bin boundaries below are half-open, with 8,000 included in the final finite bin:

| Recipe | <2400 | [2400,2850) | [2850,3300) | [3300,3800) | [3800,5000) | [5000,8000) | ≥8000 | Never |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Plain | 0 | 21 | 3 | 4 | 2 | 0 | 3 | 7 |
| Plain + pool | 14 | 23 | 2 | 0 | 0 | 0 | 0 | 1 |
| Wire | 0 | 12 | 4 | 2 | 5 | 0 | 1 | 16 |
| Wire + pool | 14 | 14 | 2 | 0 | 2 | 2 | 0 | 6 |

**Shown.** Of the 12 plain runs unescaped at 3,800, five subsequently cross 0.3 and seven never do. This rules out a literally closed opportunity to escape after the ramp. It does not distinguish reduced escape probability from a remaining population of intrinsically slower trajectories. Separate pooling's earlier escapes are real, but do not override its failure to earn automatic promotion under [08]/[09].

### E4 — counts verified; “rejected hypothesis” is too strong

**Shown.** Among the 190 records, last-gold-log answer loss >0.1 occurs in 12, with 3 stuck (25%); the other 178 have 38 stuck (21.35%). These counts provide little descriptive support for using that reading-loss threshold to predict failure. They do **not** exclude all reading-related mechanisms: the slow group is small, recipes/environments differ, the threshold is coarse, and answer loss is not subject-address readability. I withdraw slow gold-card answer learning as a supported predictor here, not every possible interaction between reading and search.

### E5 — early same-environment divergence verified; clean repeatability rate not verified

**Shown.** All 15 old plain/wire seed pairs report RTX 5070 Ti, Torch 2.11.0+cu128 and the same curriculum. Seed 1's step-1,800 answer losses are **0.0661621 versus 0.3639599**. Historical stuck sets reproduce exactly: plain `{0,8,12,13}`; wire `{1,2,6,7,8,9,14}`. [old-plain], [old-wire]

**Shown — precision qualification.** At step 50 all 15 pairs have identical saved answer loss; at step 100, 14/15 agree when rounded to six decimal places. Not all loss fields agree to six decimals: the maximum step-50 total-loss difference is about 9.54e-7. By step 200 the maximum answer-loss difference is 1.52e-4; by 1,800 the median is 0.00532 and maximum 0.29780. The claimed pattern is verified, but literal equality of every early curve entry is not.

**Shown — source-level inertness, not verified tensor parity.** The wire projection starts at zero. Gold mode preloads all gold cards and gives the search/HALT losses zero weight; the wire has no answer/LM route ([wire-source], lines 75–106; [model], lines 525–555). Under that source contract its added query term remains zero during gold training. Extra computation, parameter allocation and execution scheduling still differ. The common reader also contains floating-point reductions such as `index_add`; attributing the divergence to a particular CUDA operation would require measurement. I did not inspect weights, optimizer states or original runtime execution.

**Suggested — implication.** Different hardware/Torch versions are not necessary to see divergence in the saved learning curves. Hard retrieval is not necessary for divergence to *begin*: it is already visible during gold training. Retrieval/curriculum feedback can still amplify its consequences later. These files undermine “same seed means the same trajectory”; they do not isolate nondeterminism in identical executions or the causal effect of the active wire on final success.

## A — the early-search loss

**VERIFIED:** E1–E4 as qualified above; unchanged first empty workspace; later-loss paths and their normalization; decoy frequencies. **NOT VERIFIED:** a schedule-caused reduction in escape hazard, or benefit/harm from the unbuilt early loss. **Verdict: the attack SUCCEEDS against my priority and confident temporal explanation; the rival causal explanation NEEDS MEASUREMENT.**

### A1 / question 1: longer teacher window first

**Suggested.** I now prefer a **fixed schedule delay** over implementing fix 1 first. Keep the gold fraction 0.10 and translate the own-fetch ramp later:

| Setting | Control | Proposed treatment |
|---|---:|---:|
| Gold ends | 0.1000 | 0.1000 |
| Own-fetch ramp begins / pure teacher ends | 0.1833 | **0.3000** |
| Ramp reaches its maximum | 0.2667 | **0.3834** |
| Maximum own-fetch probability | 0.75 | 0.75 |

**Untested — exact factor.** For FLOP share `f`, use `p_own(f;t)=0.75*clip((f-t)/0.0834,0,1)` after the gold phase, with `t=0.1833` versus `t=0.3000`. This is one intervention—the ramp's start time—not two independently tuned settings. It preserves the ramp width, endpoint and initial model; it adds no parameters or loss. The pure-teacher FLOP share grows from 0.0833 to 0.20, approximately 2.4 times as much. Less of the same total budget remains at maximum own fetching. Failure on native retrieval from reduced own-state exposure is a real counterprediction.

**Suggested — why this takes precedence.** The curves show both successful and stuck runs entering the category plateau, and the existing teacher regime already escapes it for many seeds. Extending that regime is a simpler intervention on a newly observed bottleneck than adding a separate training episode. This does not prove the teacher window causes escape, or that gold training did not shape the bad representation. It changes the ranking on intervention cost and evidence, not by declaring the earlier explanation impossible.

**Shown / suggested — qualify “zero code.”** The model, losses and curriculum implementation already support these fractions through the GPU-port flags. However, the current GPU CLI derives its FLOP budget from requested steps and uses the historical training stream; the recovery CLI offers explicit B and independent data seeds but hard-codes the old curriculum. For this top-1/K=4 toy, planned teacher and own loops are both four, so a change in their relative shares does not itself change planned loop cost at fixed gold share. Nevertheless, [08]/[09]'s explicit common B, fresh streams and complete evaluation still need a suitable launch adapter. This is **zero new model/loss code**, not a claim that the entire compliant experiment is launch-ready without engineering. [gpu-port], [budget-helper], [recovery]

**Suggested.** Do not add a D16 competence gate now. That would require a development-panel policy, threshold, cap/failure behavior and adaptive phase lengths, and can introduce evidence-assisted scheduling. D16 permits such a separately specified design; it is not already a demonstrated fix. A fixed delay asks the simpler question first. [decisions]

### A2 / question 2: survival confounding is real; the code supplies a plausible schedule mechanism

**Shown.** Fable is right that, given the same parameters and batch, the first Think step starts with the same empty card workspace in teacher and own modes. Own fetching does not contaminate that first workspace within the current episode. I retract any explanation that says it does.

**Shown — an additional relevant code fact.** The first request's **unnormalized** CE is the same, but its share of the total search loss need not be. `set_terms` contains one scalar per question/loop with missing evidence, and the code takes one mean over their concatenation ([model], lines 597–623):

`L_set = sum_(q,t with missing gold) CE_(q,t) / N_need`.

For Q questions split equally between one and two hops, top-1 teachers with no distractors complete their evidence after one or two insertions. Therefore `N_need=1.5Q`. In the limiting own trajectory where every fetch misses, every question still needs gold at all four training loops, including the final loop: `N_need=4Q`. The coefficient of each first-request CE is then **3/8 of its teacher-only coefficient**, before adding the different later-loop gradients. This is a source-derived limiting example, not the measured average at `p_own=0.75`. ASK BCE has a separate mean over all question-loops and does not have this particular denominator change.

**Suggested.** Later search losses also see wrong cards and different missing sets; answer loss changes with card contents and with the `have_all` multiplier, and HALT targets depend on answer correctness. All update shared reader/pool/Think parameters. Global gradient clipping and Adam operate on the combined gradient. Thus own fetching can dilute the useful first-request score loss and alter the other gradients acting on that route, even while its first forward input remains clean. This is a concrete mechanism for a softer teacher-to-own learning window. Its net effect, including possible beneficial hard-example learning, remains **untested**. Do not add a normalization fix alongside the proposed schedule change.

**Untested — observation that distinguishes the explanations.** Compare continuation from the **same unescaped pre-transition training state**, including weights, optimizer, counters and RNG state, under randomized/matched teacher continuation versus the normal ramp, using the same future batch stream and equal additional compute. Define unescaped status before branching, not after seeing either result. If delayed-own continuation produces more escapes from those same states, there is a causal schedule effect that depletion of fast seeds cannot explain. If the two continuations have similar escape distributions at adequate precision, the original temporal histogram does not establish a closing window and heterogeneous learning times become a stronger account. A null with low power is inconclusive; both mechanisms may coexist.

**Suggested — scope.** This is the identifying observation, not another prerequisite experiment to add now. The proposed whole-run schedule comparison estimates the average effect of delaying own fetching. The historical histogram alone cannot establish a hazard change, and a faster unconditioned curve under treatment would not by itself identify the mechanism above.

### A3 / question 3: add the decoy failure sign; do not bundle hop-order labels into fix 1

**Shown.** Among fresh-learned plain/shared pair-suite checkpoints, `request1.classes.asker_same_rel` is **0.0551314**; with separate pooling it is **0.0698618**. The strata contain 33 and 39 different learned populations, so their difference is not a controlled estimate of a one-hop-loss effect. The generator includes the asked person's target-relation attribute in each two-hop world. [pairs], [generator]

**Suggested.** The counterexample succeeds as a plausible failure mode: earlier one-hop address learning may favor `(asker, terminal REL)` on a two-hop question. If fix 1 is reconsidered later, retain its one-hop-only definition and add **first-opportunity `asker_same_rel` rate** as an explicit failure diagnostic, alongside first-LINK, no-request/NULL, one-hop stuck count and causal pairs. Use every held-out question as the denominator, not only actual requests. Increased decoy fetching accompanied by lower LINK/causal performance is a mechanism failure, not evidence that early retrieval helped two-hop learning.

**Suggested.** Do not now include two-hop first requests in that auxiliary loss: choosing LINK as their singleton target adds hop-order supervision and merges fixes 1 and 3. The new teacher-delay comparison keeps the old unordered labels and teacher selection unchanged. Early-search loss remains a distinct, unbuilt alternative, not an automatic next step if the schedule fails.

## B — the static-token residual

**VERIFIED:** the proposed equation admits asker content; zero B preserves initial forward values only; the saved escape counts and same-environment direction of the stuck-count difference; the difference between identity and selection assays. **NOT VERIFIED:** the residual's trained behavior or its effect on stuck frequency. **Verdict: B1 and B3 SUCCEED; B2 SUCCEEDS as a sequencing objection, while its empirical prediction NEEDS MEASUREMENT.**

### B1 / question 4: nothing currently prevents contamination; explicit adverse prediction

**Shown — algebra of the unbuilt proposal.** Ignoring the NULL option for exposition, near-uniform attention on a two-hop question gives

`delta q ≈ g B (E[QUESTION]+E[a]+E[LINK]+E[r]+E[ANSWER])/5`.

With NULL included the denominator changes, but the asker component remains. Once B moves, the `E[a]` term is present unless attention suppresses it or B learns to remove it. A scalar gate cannot separately retain REL and remove ENT from the same mixture. At initialization B=0 makes the whole residual zero; it does **not** protect subsequent updates from this failure.

**Suggested — exact limit of the counterexample.** Inclusion of `E[a]` does not mathematically guarantee movement toward `key(a,r)`: the sign depends on the learned B and key geometry. But early one-hop ASK rewards person discrimination, so mapping that component into an asker-address direction is an available and plausible solution. The useful hop-2 person is b, while this residual's token contents contain a, not b. Calling the contents “static” prevents contextual mutation of each embedding, not injection of the wrong entity.

**Untested — prediction for the unchanged proposed module.** Before attention learns to concentrate on the active predicate, it will tend to raise **second-opportunity `asker_same_rel`** on two-hop questions relative to the same background without the residual. A relation benefit may coexist with more stuck runs or worse first-LINK behavior. Score this over all questions and report practised and held-out relations separately; also inspect attention mass on the asker token. These are adverse predictions, not measured outcomes or a claim of inevitable harm.

**Suggested — revision.** I withdraw the implicit expectation that the gate/attention would reliably solve this through ordinary ASK alone. They *could* learn suppression or an entity-insensitive B, but there is no supporting learning result. I am not adding a supplied-role content mask, new auxiliary role targets, or another architectural fix to save the proposal. Its +1,602 parameters and zero-start equation remain an **unbuilt research candidate with this explicit failure prediction**, not the recommended implementation.

### B2 / question 5: sequence after a plateau remedy, and keep the safeguard

**Shown.** Teacher-window escapes drop 21→12 and never-escaped counts rise 7→16 between the current plain and wire rosters. Those rosters differ in hardware. The old 5070 Ti rosters have stuck counts 4/15 versus 7/15, but the earlier numerical divergence prevents treating this as identical shared training until wire activation. Neither comparison identifies the causal effect of my different, unbuilt residual. Its additional selection freedom does not protect it from wire-like bad solutions.

**Suggested.** Do **not** evaluate this residual first on plain/shared merely because a relation-identity probe is poor. Establish the plateau remedy before allocating a module comparison. A later residual contrast must use fresh seeds in **both** arms on one explicitly declared, accepted unprivileged background; it is not fine-tuning only rescued checkpoints or selecting successful seeds. Starting the module from zero in a fresh run on a better schedule can still reintroduce the plateau, so sequencing reduces uncertainty but does not guarantee safety.

**Suggested — no trade exception.** Retain [08]/[09]'s no-increase-in-fresh-stuck-count safeguard. If the residual raises stuck count, it fails advancement even if held-out relation use improves among survivors. Do not substitute the historical `<384/512` classification for the registered fresh threshold `<1536/2048`, average away the failures, or change the gate after seeing a “known trade.” Separate pooling also remains a candidate rather than an inherited background. Existing A4's fixed recipe is not silently changed by this sequence.

### B3 / question 6: withdraw the ranking flip; do not enlarge the assay now

**Shown.** The affine identity probe receives the **true relation row**. My attention instead must rank that row against ENT, LINK, delimiters and NULL using `z^T A h_i`. The probe neither tests that ranking nor observes the same decision rule. The unseen training configuration is relation 2 after LINK; the after-LINK question pattern does occur for the practised relations. [08], [10], [generator]

**Suggested — attack succeeds.** Withdraw [10]'s rule “25/33 learned controls fail identity readability ⇒ move fix 2 first,” and its companion 30/33 interpretation as a selection argument. Even a failed affine identity probe is not proof that a trainable selector cannot use the rows; a successful probe is not proof that it can select the right row in the unseen combination.

**Suggested.** Keep [08]'s existing identity assay in its limited A4 role, with its stated qualifications. Do not add a row-selectability probe to the next-action workload. Any later claim about selection must be supported by the actual selector or an explicitly matched row-ranking assay with disjoint fitting/scoring, not inferred from known-row classification. No probe result overrides B2's sequencing or the reliability safeguards.

## C — dependency-frontier CE

**VERIFIED:** the location of the measured delayed-LINK failures and the actual training targets in endpoint-first teacher states. **NOT VERIFIED:** the persistence of that defect in a future unprivileged residual or the frontier loss's benefit. **Verdict: C1 SUCCEEDS; C2 FAILS as a claimed conflict with an ASK-stop target, but SUCCEEDS as a warning about answer utility versus evidence completeness.**

### C1: agreed—keep it unbuilt

**Shown.** Fresh-learned plain/shared first-LINK frequency is 0.8929, versus 0.7158 with separate pooling. The striking delayed-LINK pattern is in the learned wire failures: the two shared-pooling failures have essentially no first LINK and approximately 0.9995 second LINK. These are selected failure strata, not proof that all unprivileged models need an order change. [pairs], [08]

**Suggested.** Keep fix 3 unbuilt until a specific unprivileged recipe actually fails through delayed LINK and loses useful request opportunities. Do not build it alongside the token residual or assume the wire's failure will transfer. If the new recipe gets LINK first reliably, skip this fix. This is now an explicit condition, not merely “third in a queue.”

### C2: ASK still targets search; the completeness/utility mismatch already exists

**Shown.** With two unfetched gold cards and random top-1 teacher selection, about half of two-hop teacher episodes first receive the endpoint. In the state `F={endpoint}`, both old and proposed search targets are already identical:

```text
old missing-gold set = {LINK}
new frontier H(F)   = {LINK}
ASK BCE target     = 1, because evidence remains missing
```

There is **no ASK “stop searching” label** to conflict with here. Fix 3 changes the target when both gold cards are missing, not this singleton-missing state. [model], lines 596–601

**Shown / suggested.** If the supplied endpoint already lets the decoder answer correctly, the HALT target can be 1 while ASK targets 1; answer loss is still scaled by `early_ans=0.2` until all gold evidence is fetched ([model], lines 581–588). The heads can mathematically emit both labels, but they serve different notions of completion and update shared state. The pair suite ignores HALT at evaluation, yet its training gradient remains present. Also, reading an endpoint can supply the answer token without establishing that it belongs to the asked person's LINK chain; “cannot change the answer” is not a universal claim about a learned decoder or counterfactual correctness.

**Suggested — disposition.** This state is not automatically harmless. It exposes a pre-existing preference for completing the evidence set even when a current answer is already correct. It is not a new opposing ASK gradient introduced by frontier CE. I retain the narrowly defined frontier-only proposal, conditional and unbuilt, and do not bundle teacher ordering, HALT targets or answer weights into it to answer this objection.

## What E5 changes about the 64-job repeatability proposal

**Suggested.** E5 is sufficient to retire any need to spend 64 jobs merely to show that same-seed trajectories *can* diverge on the reported same GPU/software setup. It is not sufficient to estimate a clean within-recipe G_pair flip probability. The prior [08] repeatability assay would additionally repeat each **identical arm** from matched initial/data RNG states under one execution manifest and estimate within-seed outcome disagreement, rather than comparing two programs whose active mechanisms differ after gold training. It would clarify whether particular seed “rescues” reproduce and how much precision pairing provides.

**Suggested.** Defer that 64-job study. It is not required to choose the next model intervention. Record initialization, data, environment and failure outcomes in the next comparison and treat marginal fresh-run reliability as the objective. Do not attribute all final plain/wire differences to numerical noise merely because the inert-prefix curves diverged.

## Single next action and fixed pass mark

**Suggested — next action for Ben: prepare one schedule-only, fixed-budget longer-teacher comparison for the free RTX 5070 Ti.** Build only the minimal **additive launch adapter** needed to pass an explicit curriculum, common B and fresh data seeds into the existing plain/shared trainer and existing evaluation contract. Do not implement the early-search episode, token residual, frontier loss, adaptive competence gate, or repeatability study first. This is one experiment package, with the schedule specified in A1 as its only learning change. Nothing is built or launched by this analysis.

**Suggested — proposed slot decision.** Use the existing A3 slot for this newly specified schedule contrast, replacing its pending remedy choice if this proposal is accepted; do not call it the old gold-zero/phase experiment or add a seventh comparison. Apply [08]'s causal-improvement rule to this named contrast. This is a proposed choice of intervention under unchanged evaluation rules, not a declaration that the old A3-phase one-hop-only endpoint automatically applies.

**Untested — frozen comparison specification.** Name it `A3-teacher-delay-v1`. Use **16 fresh seed pairs / 32 jobs**, explicitly an exploratory low-power comparison, with independent streams across pairs and matched shared initialization and batch streams within each pair. Both arms use `bypass-k1`, d=32/key_dim=16, shared pooling, original unordered evidence/teachers, decoder/binder/step embeddings, fp32, LR 1e-3 and 100-step warm-up. Wire, pooled selectors, static-token residual and ST are absent. Count 79,748 parameters in either arm. Set the same explicit **B=3.407362074846783e13** counted model FLOPs in each job. Do not infer B from a “6000 steps” filename or equate FLOP shares with literal update fractions.

**Untested — pass mark fixed here, before learning outcomes.** Advance only if all of the following hold:

1. Classify each evaluated seed as a G_pair pass only when all six fresh panels meet [08]/[09]'s existing counts: c1/c2 ≥1969/2048, c3 ≥1876/2048, c4/c5/c6 ≥945/1024. This defines each seed's binary outcome for the comparison below; it does not require every control/treatment seed to pass.
2. Across the 16 pairs, with `g=control-fail/treatment-pass`, `l=control-pass/treatment-fail`, `d=g+l`, require `sum_(k=g..d) choose(d,k)/2^d <=0.05` (1 if d=0), and `(g-l)/16 >=0.10`. Five gains and no losses pass this primary comparison; four gains do not.
3. Fresh one-hop stuck count does not increase, and the paired one-sided 95% lower bounds for mean one-hop and READS changes both exceed −2 percentage points, using [08]/[09]'s specified panels/resampling. Keep all registered failures/missing runs; invalid or incomplete evaluation cannot support advancement. Preserve the source, label-noninterference and execution-integrity requirements.

**Suggested — interpret the result honestly.** Escape times, one-hop-only improvement and decoy rates explain a result; they cannot rescue failed G_pair advancement. A schedule that improves plateau escape but leaves held-out failures unchanged is useful mechanism evidence, **not a promoted reliable recipe** and not automatic permission to attach fix 2. This may happen because schedule delay does not explicitly teach relation transfer. Sixteen pairs can miss a useful effect; do not extend the roster after inspecting results. The separate G_cert/77-of-80 certificate is unchanged.

**Untested — resource admission remains a real prerequisite.** Before learning, the adapter's complete-load rehearsal must establish `T=s+ceil(32/C)*(B/f+e) <=1500 seconds`, leaving the existing margin under the 30-minute ceiling, with all primary evaluation, READS, diagnostics, saving and collation counted. Preserve the 1,200-second per-job training cap and require FLOP-budget completion plus `budget_ok`, not a time-stopped checkpoint. The known old 5070 Ti runs do not establish this throughput. If the full comparison does not fit, the package remains unadmitted; do not shrink B, n, controls or panels, split one comparison to conceal its elapsed time, or switch to paid machines under this recommendation. The next **build** is concrete, but I cannot honestly label the GPU **run** feasible yet. Incremental rental on Ben's stated free GPU is $0; no money was spent here.

## For Ben

**Suggested, with the remedy untested.** Fable changed my mind about what to try first. The saved runs all struggle at roughly the same early search stage, and the successful ones often get past it while teachers are still giving them the right cards. I would first give that stage more of the existing training budget, then check whether the model works better when it must fetch for itself. My proposed word shortcut can accidentally keep pointing at the original person after the question needs their friend, so I would not build it yet. The curves give us a simpler first change to try; they do not prove that extra teacher time will solve the problem.

[08]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/08-pairsuite-adjudication.md
[09]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/09-reconciliation.md
[10]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/10-fixes.md
[plain]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-20260919/control/runs
[plain-pool]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-20260919/keypool/runs
[wire]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-relcut-20260919/control/runs
[wire-pool]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-keypool-relcut-20260919/keypool/runs
[old-plain]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-long-20260919/runs/long-s1-12000.json
[old-wire]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-relcut-long-20260919/runs/relcutlong-s1-12000.json
[pairs]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-pairsuite-20260919/rows.jsonl
[model]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py:503
[wire-source]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_relation_shortcut.py:75
[generator]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/toy_ladder.py:119
[gpu-port]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_gpu_port.py:136
[budget-helper]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/train.py:460
[recovery]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_recovery.py:199
[decisions]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/v3/00-decisions.md:28
