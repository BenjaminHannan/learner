# Premonition: evidence audit and a short route to dependable two-hop reasoning

Research review, 19 September 2026. Small-card and village tracks are separate throughout.

**Suggested — decision.** Finish the existing key-pooling comparison; use its surviving recipe to measure complete two-hop behavior on fresh, causally paired worlds; add training machinery only at the first demonstrated failure. The current evidence favors an addressing cold start followed by a partly separate relation-reuse problem. It does not justify replacing Think, enlarging memory, or waiting indefinitely for a lucky seed.

**Shown — current position.** Recomputed across 45 card runs, the long relation-shortcut recipe passes the original three screen criteria in **2/5 seeds**, although 3/5 exceed its weak held-out threshold. The saved handoff diagnostic is **inconclusive for the shortcut panel**, with its large gain concentrated in seed 4. Its baseline panel rejects a useful effect of that specific intervention. Neither key-pooling result directory existed at the recorded audit snapshot. [Computed screens][screens] [Handoff rows][handoff] [Snapshot][snapshot]

**Shown — work performed.** This review reads source, reports, saved JSON and primary literature; calculations use JSON, arithmetic and hashing of text/JSON files. No model, tensor artifact or checkpoint was loaded, no repository test or training script was run, and no remote machine was accessed. New deliverables are confined to this review directory. Saved evaluation results are evidence reported by their original evaluators, not evaluations rerun here.

**Evidence labels.** “Shown” means directly supported by inspected code, saved outputs, or a stated calculation; its scope is the inspected setup, not universal truth. “Suggested” means an interpretation with live alternatives. “Untested” marks a proposed intervention, forecast or missing measurement. For papers, “established” means demonstrated in that paper's stated setting; “your inference” marks my proposed transfer. Labels at the start of a paragraph or table row apply to its project claims unless a narrower label appears inside it. Mathematical planning calculations are labeled shown, conditional on their assumptions.

## 1. What the card experiments actually establish

**Shown — task and split.** The standard toy uses six people sampled from 16 identity tokens, three attributes with 16 possible values, one friend link per person, four noise lines, a 128-token filler gap, and four questions per world. Facts and bindings change between visits. Training includes A0(x), A1(x), A2(x), A0(F(x)) and A1(F(x)); the held-out composition is A2(F(x)). Here F means “friend of” and Ar means “attribute r of.” It is a new position for a familiar attribute lookup in a fixed two-operation chain. It is not an unseen primitive, unseen name vocabulary, reversed chain, arbitrary program, or natural-language test. [Frozen generator][toy]

**Shown — evaluation population.** The usual validation panel contains 256 worlds and 1,024 questions: 512 one-hop, 341 practiced two-hop, 171 held-out two-hop. Multiple questions share a world. These are not 1,024 independent training replications. Six-relation runs have different question denominators, including only 78 held-out questions. All old validation-driven choices make this panel development evidence. New worlds can test fresh instances of the known A2-chain shift; they cannot make that already-consulted shift an untouched research hypothesis. [Evaluation source][retrieval] [Computed runs][runs]

**Shown — model and source identity.** The small baseline has about 79,748 parameters; the relation shortcut adds 545. The frozen source uses a recurrent reader with local attention, line cards, learned requests, a shared Think block and an answer decoder. The separate-key-pool variant adds 33 stored scalars, but only **32 effective degrees of freedom**: its shared scalar bias cancels in the token softmax. It clones the existing scorer and preserves initial outputs by construction. This reconciles “+33 parameters” with Ben's “+32 effective parameters.” Current additive source is not automatically a byte-identical record of every historical run. [Model][model] [Shortcut][shortcut] [Key pool][keypool]

| Component | What is supported | Interpretation and unresolved alternative |
|---|---|---|
| Reader | **Shown:** a fitted linear probe recovers card-subject identity from the subject-token state at about 98–100% in the three stuck long runs. Later states and the pooled key are much worse. | **Suggested:** the local identity signal exists before pooling. **Untested:** a general language parser, role binding, or robust identity propagation. Reading an identity at its own token is easier than using it after compression. |
| Card writer / pooling | **Shown:** a scalar scorer pools contextual states once; separate key and value projections consume that same vector. The in-flight variant separates the scorers, not the entire reader. | **Suggested:** answer training and addressing may want different summaries. A late contextual token can retain the subject even when its explicit pooling weight is tiny. Attention mass alone cannot identify information loss. |
| Keys and queries | **Shown:** stuck runs choose the correct first-hop card family but roughly a random person within that family; their one-hop set loss is about ln(6). Linear person decoding from keys is near six-person chance. | **Suggested:** a coupled learning failure on the two sides of the address match. Weak keys, weak queries, bad geometry and their interaction remain open; no single one is proven the originating cause. |
| Think / registers | **Shown:** shared computation updates registers and query state across loops, with step embeddings. Four fixed loops permit at most three insertions in this evaluation. | **Suggested:** an interface failure can coexist with an adequate compute block. Removing step embeddings did not establish a held-out solution. **Untested:** whether extra recurrent compute earns its cost against a matched simpler controller. |
| Entity slots | **Shown:** fetched lines can update slots for every mentioned person using the card value; source and destination roles are not cleanly separated by that operation. | **Suggested:** this is a plausible source of ambiguous role binding. Small effects of slot removal in supplied-card models do not establish that slots are unused in every autonomous retriever. |
| Decoder / bypass | **Shown:** the bypass supplies the decoder the inserted, pre-Think card rows while Think still controls retrieval. Supplied-card copying can become perfect in the earlier small assays. | **Suggested:** decoder damage is avoidable. Perfect copying from the only answer-bearing attribute card does not require finding the friend or selecting the correct person's attribute. |
| Curriculum | **Shown:** gold cards are initially preloaded, then teacher insertions train requests, then own insertions are mixed in. The maximum own-insertion probability is 0.75. | **Suggested:** delayed addressing supervision is a plausible cold-start cause. **Untested:** whether removing teachers improves or harms reliability. Gold preloading makes simply turning on ASK loss an invalid test of empty-workspace lookup. |
| Losses | **Shown:** language-model and answer losses are active early; ASK and HALT loss weights are zero in the gold phase. Later ASK combines a binary request loss and marginal set cross-entropy over unfetched gold evidence. Early answers receive reduced weight before evidence completion. | **Shown:** after one gold card is fetched, the missing gold card is supervised. **Suggested:** unordered early targets and answer-first teacher insertions still make the learned route ambiguous. |
| Discrete retrieval | **Shown:** selected indices and the ASK threshold are discrete/detached. Answer loss does not differentiate through the choice of index. | **Shown:** gradients still reach selected values and shared reader features. **Suggested:** indirect pressure can change retrieval, but a paired answer objective is not a direct remedy for wrong retrieval scores. |
| Evaluation | **Shown:** saved fixed-loop accuracy checks the generated answer sequence, including termination, against the target. Learned-halting results are also saved. | **Suggested:** single-token values, fixed fields and reusable validation can make the task look more general than it is. Gold-only reads and oracle-conditioned subsets are diagnostic ceilings, not autonomous success. |

Sources for the component table: [model][model], [store][store], [trainer][train], [bypass][bypass], [retrieval][retrieval], [person probe JSON][personjson], [stuck probe JSON][stuckjson], and the [milestone-3 reports][m03].

### Recomputed screen table

**Shown.** These are counts of passing seeds, each out of five. The original READS rule is at least 307/341 supplied-card practiced answers; practiced own retrieval is at least 171/341; held-out is at least 86/171. “Not stuck” is at least 384/512 one-hop answers. “All three” means READS, practiced and held-out together, not a modern reliability gate. For six-relation runs the corresponding fractional rules use their own denominators. [Screen CSV][screens]

| Recipe | READS | Practiced | Held-out | Not stuck | All three | Held-out correct, seeds 0–4 |
|---|---:|---:|---:|---:|---:|---|
| Short baseline | 5 | 2 | 0 | 2 | 0 | 12, 26, 28, 19, 13 /171 |
| No step embedding | 5 | 4 | 0 | 4 | 0 | 25, 64, 12, 15, 19 /171 |
| Ordered evidence | 5 | 3 | 0 | 4 | 0 | 34, 9, 12, 10, 17 /171 |
| Learning-rate cooldown | 5 | 3 | 0 | 3 | 0 | 18, 17, 12, 9, 51 /171 |
| Six relations | 5 | 1 | 0 | 2 | 0 | 14, 18, 6, 5, 6 /78 |
| Six relations + ordered | 4 | 1 | 0 | 1 | 0 | 3, 2, 7, 20, 6 /78 |
| Long baseline | 5 | 4 | 1 | 4 | 1 | 6, 13, 88, 18, 12 /171 |
| Short relation shortcut | 5 | 2 | 1 | 2 | 1 | 26, 57, 138, 38, 31 /171 |
| Long relation shortcut | 4 | 3 | 3 | 3 | 2 | 171, 32, 35, 170, 132 /171 |

**Suggested.** The shortcut has a substantial signal for relation-position transfer in successful runs, but the five-seed comparison cannot isolate a precise change in success probability. Longer training helps some runs without fixing the common failure. The six-relation result is a failed recipe, not evidence that task diversity cannot help: number of facts, search difficulty, exposure per relation and evaluation counts change together.

**Shown — long runs, exact counts.** P means practiced; H means held-out; “both” records retrieval of both gold facts, whether or not the answer is correct. [Run CSV][runs]

| Recipe / seed | One-hop /512 | Gold READS P /341 | Own P /341 | Own H /171 | Both facts P / H | Learned-halt H /171 |
|---|---:|---:|---:|---:|---|---:|
| Plain 0 | 115 | 341 | 84 | 6 | 25 / 0 | 8 |
| Plain 1 | 512 | 341 | 341 | 13 | 341 / 0 | 13 |
| Plain 2 | 512 | 337 | 341 | 88 | 341 / 84 | 88 |
| Plain 3 | 512 | 341 | 340 | 18 | 340 / 3 | 17 |
| Plain 4 | 489 | 332 | 341 | 12 | 341 / 1 | 12 |
| Shortcut 0 | 506 | 341 | 339 | 171 | 340 / 171 | 171 |
| Shortcut 1 | 99 | 341 | 69 | 32 | 19 / 10 | 32 |
| Shortcut 2 | 92 | 341 | 75 | 35 | 19 / 11 | 45 |
| Shortcut 3 | 512 | 323 | 338 | 170 | 340 / 171 | 170 |
| Shortcut 4 | 473 | 306 | 257 | 132 | 275 / 136 | 132 |

**Shown.** Successful shortcut seeds 0 and 3 have the same total answer accuracy under learned halting and fixed four loops: 1,016/1,024 and 1,020/1,024 respectively. Their held-out counts also agree. Thus “learned halting has never been checked” is wrong for these runs. **Untested:** whether halting preserves accuracy and saves meaningful compute across fresh interventions and seeds. Strong endpoints already make halting a lower priority than addressing.

**Shown — schedule correction.** “12,000 steps” is the requested budget label; actual long runs stop at 12,250 or 12,251 updates. Curriculum boundaries use estimated FLOP share, not a fraction of the final update count. Long curves last log gold at step 1,850, first teacher at 1,900, first own phase at 2,850, and saturated own probability 0.75 at 3,800. The exact transitions lie between logs. The usual short curves first log teacher at 1,550, own at 2,350, and 0.75 at 3,150, stopping at 3,745. The cooldown does not reach its nominal terminal 0.1 multiplier at that stop. Gold-phase nonzero ASK numbers in logs are computed diagnostics, not proof that their gradients were weighted into training. [Observed schedule CSV][curves] [Trainer][train]

### The handoff result that is now available

**Shown — intervention meaning.** The saved diagnostic uses 512 paired worlds whose queried friend changes to someone with a different answer. U is untouched execution; Q restricts the first request to cards whose parsed subject is the question's subject; D restricts the second request to the object person of the link actually fetched first; QD combines them; QW uses a wrong in-world person for the second restriction; N applies an all-allowed mask. These masks do not force the correct relation. D is inactive if the first fetched card is not a usable link. The masks parse the toy fields and supply structure unavailable to the plain learner. [Diagnostic source][diag] [D1 JSON][d1]

**Shown — both members answered correctly, out of 512 pairs.** I recomputed these counts from saved per-example correctness bits and pair IDs, rather than rounding the aggregate percentages. [Recomputed pairs][handoff]

| Shortcut seed | U | Q | D | QD | Wrong-person QW | QD−Q |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 507 | 508 | 511 | 512 | 174 | +4 |
| 1, stuck | 0 | 0 | 0 | 0 | 0 | 0 |
| 2, stuck | 1 | 0 | 1 | 0 | 0 | 0 |
| 3 | 495 | 495 | 512 | 512 | 232 | +17 |
| 4 | 293 | 340 | 443 | 511 | 52 | +171 |

**Shown.** The predeclared five-seed effect is +7.5 percentage points, with the saved world-bootstrap one-sided 99% lower bound +6.45 points. It fails the required +15-point mean, the required gain in at least two seeds, and the requirement that QD reach 80% in at least four seeds. The controls pass. There is insufficient opportunity coverage for its no-useful-effect rejection rule. Its recorded decision is **INCONCLUSIVE**, not pass and not no effect. The interval is conditional on this fixed training panel; it is not a confidence interval over future training seeds.

**Shown.** In the separately reported learned stratum, U is 84.31%, Q is 87.43%, and QD is 99.93%; QD−Q is +12.5 points. The two stuck seeds gain zero from QD over Q. Seed 4 accounts for 171 of the panel's 192 newly correct pairs. Q already repairs part of its first addressing problem; D then repairs much of the remainder. The learned-only descriptive result does not replace the registered all-seed decision. [Stratum CSV][strata]

**Suggested.** Passing the returned identity explicitly is useful for at least this partially competent shortcut seed. It is not the common explanation of the two stuck shortcut seeds, and the near-perfect seeds leave little headroom. Pooling repair could remove precisely those upstream failures and change the panel-level conclusion; it could also remove the residual handoff problem. Do not commit to a new handoff training arm before seeing that.

**Shown.** In the plain panel QD−Q is only 2 extra correct pairs across 2,560 seed-pairs, +0.0781 points. Opportunity coverage is adequate under the saved rule and its upper 99% bound is +0.2344 points: **REJECT_NO_USEFUL_EFFECT** for this boundary intervention on this panel. Its wrong-person contrast is weak as well. **Suggested:** correct-person routing cannot compensate for the plain model's remaining relation errors. This is not proof that identity handling never matters.

**Shown — diagnostic limits.** D0 reports passing parity/fixture checks. D1's interpreter gets all 1,024 individual answers and 512 pairs correct. Deterministic question-blind, relation-only and direct-subject shortcut strategies cannot get both changed-link answers correct in this panel. But overlap reconstruction against training was skipped, as were 12-person, three-lookup, longer-gap, full store-wipe/restore and exact-code/soft-distribution controls. D2 was not scored; the inspected implementation explicitly refuses because D2 scoring is not implemented. The manifest records an earlier generator-script hash than D1's evaluation-script hash; the latter matches the source snapshot I inspected. That is disclosed provenance, not automatic evidence of a wrong result, and it limits verification of historical script identity. [D0][d0] [Manifest][manifest] [Snapshot][snapshot]

### Supplied-card work is a different assay

**Shown.** Earlier milestone-2 repairs make supplied-card copying perfect across two seeds, but the gold set contains an answer-bearing attribute card whose value can be copied without chaining. Milestone 3's answer-only models with distractor cards are a stronger binding assay: original pooled choosing is 164/512 and 161/512; mean pooling scores 138/512 and 125/512 while also harming reading. A direct reader scores 170/512 and 162/512 and gets neither member pair right on the relevant-change test (0/256). Removing cards changes many predictions, proving influence, not correct use. [M03][m03] [Direct reader][direct]

**Shown.** Adding explicit subject/relation address features raises choosing to 503/512 and 467/512, with relevant-pair scores 239/256 and 222/256. In fresh confirmation, choosing is 500/512 and 466/512 against pooled 147/512 and 164/512. Relevant pairs are 238/256 and 218/256 against 1/256 for each control. Yet practiced two-hop confirmation remains 132/337 and 111/337 versus 136/337 and 114/337. Held-out two-hop is 65/175 and 55/175 versus 61/175 and 62/175. Better supplied-card choosing did not establish chained execution. [Address report][address] [Confirmation report][confirm] [Saved comparisons][compare]

**Shown.** Consistent renaming preserves answers on only 483/512 and 416/512 confirmation questions; reversing card order preserves 512/512 and 508/512. Renaming should preserve the answer value when all identities are consistently permuted. The 96 changed answers in seed 1 are a remaining equivariance failure, not desirable evidence that the model notices people. These permutations reuse the same 16 name tokens. They do not test novel spellings or a new entity inventory.

**Suggested.** This is strong evidence that binding information helps the choosing interface, with supplied parsing and additional parameters as confounds. It is weaker evidence for repairing the autonomous card retriever. A short, one-seed dual-pool result in a different regime cannot settle the ongoing long, 40-seed key-pool study.

## 2. Corrections and live alternative explanations

**Shown — scope.** The following ledger covers the material claims encountered in the named screens, stuck reports, milestone-3 reports, prior briefs and research sweeps. It is not a claim to have checked every sentence of every repository document. “Overclaim” includes a once-reasonable statement that has become stale.

| Claim or shorthand to retire | Correction and remaining uncertainty |
|---|---|
| “The shortcut passes in 3/5 seeds.” | **Shown:** held-out threshold passes 3/5; the registered conjunction passes 2/5. **Suggested:** neither is dependable behavior. |
| “The 50% held-out gate means two-hop reasoning works.” | **Shown:** it is a low screening threshold on 171 questions. **Untested:** robust paired behavior across seeds. |
| “3/10 are stuck, so the failure rate is 30%.” | **Shown:** 3/10 across two different recipes. **Suggested:** a descriptive mixture, not one recipe's precisely estimated failure rate. |
| “Five seeds tell us nothing.” / “This will not survive more seeds.” | **Shown:** five seeds give a very uncertain estimate. Three successes out of five have a one-sided 95% lower bound of 18.9%. **Untested:** either future success or failure. |
| “All stuck pooling is 97–99% on the value.” | **Shown:** STUCK_PROBE says this, but the earlier mass table gives attribute-value masses 49%, 98%, 47% for plain-0, shortcut-1, shortcut-2. Link-object masses are 91%, 99%, 58%. These reports disagree. No matching raw mass JSON resolves it here. |
| “Little weight on the name means no identity.” | **Shown:** successful runs can also place little explicit mass there; states are contextual. **Suggested:** inspect identity accessibility and causal effect, not weights alone. |
| “The key contains no identity.” | **Shown:** the tested linear readout is weak. **Untested:** absence of all decodable identity. The probe itself fits a decoder, even though original model weights remain frozen. |
| “The query has no identity.” | **Shown:** stuck query probes vary, including about 31% in-story for shortcut-2, above six-person chance; register probes reach about 52–55%. **Suggested:** loss or misalignment between components, not uniformly zero signal. |
| “No hidden partial solution.” | **Shown:** measured first-hop identity hits are near chance across reported groups. **Untested:** absence of latent progress or other useful computations. |
| “Not a position habit.” | **Shown:** earliest/latest heuristics do not explain the aggregate hits. **Untested:** more complex positional correlations. |
| “Kappa is not the cause; it is low because matching failed.” | **Shown:** rescaling existing scores does not repair rankings. **Untested:** how temperature affected gradients and the earlier training trajectory; reverse causation is not established. |
| “Answer-only for the first 1,225 steps.” | **Shown:** gold phase also has LM loss; long logs remain gold through 1,850. The 1,225 conversion confuses FLOP share with update share. |
| “Own phase means no teacher.” | **Shown:** own probability saturates at 0.75, so teacher insertion remains. |
| “There is no second-hop target.” | **Shown:** the existing loss targets remaining gold evidence after a fetch. **Suggested:** reusing the relation/identity representation is the issue, not complete absence of supervision. |
| “The unordered set loss forces equal probability on both gold cards.” | **Shown:** it is marginal set likelihood; total mass on any remaining gold card suffices. Teacher sampling/order is a separate source of trajectory ambiguity. |
| “Ordered evidence isolated the target loss.” | **Shown:** the variant changes teacher order as well as the evidence target. **Suggested:** negative results cannot identify which change helped or harmed. |
| “Answer loss has no path to retrieval features.” | **Shown:** it has no derivative through selected indices, but it changes shared features and selected values. |
| “Key/value separation is missing.” | **Shown:** projections are already separate. Pooling is shared; that is the specific intervention. |
| “More dimensions, keys, or raw text will fix held-out requests.” | **Untested:** these cannot be inferred from failures that request the wrong relation before obtaining the answer card. |
| “The bypass removes Think.” | **Shown:** it bypasses transformed card rows on the decoder path; Think still runs and forms requests. |
| “Fixed four loops means four cards or k=4 retrieval.” | **Shown:** top-1 selection, at most three insertions here; loop count and retrieval breadth are different. |
| “Halting is unmeasured.” | **Shown:** saved learned-halting scores match the best shortcut endpoints. **Untested:** a reliable compute-saving policy under shifts. |
| “Both facts fetched proves the answer used them.” | **Shown:** recall only measures presence. **Untested:** causal use; unrelated context and the answer-bearing card alone may suffice. |
| “Answer unchanged / same accuracy after removal means unused.” | **Shown:** equal aggregate accuracy can hide prediction swaps; small differences have uncertainty. **Untested:** universal irrelevance of entity slots or cards. |
| “Explicit addresses solve the model.” | **Shown:** supplied-card choosing improves; two-hop confirmation does not. Parsing and parameter additions are privileges. |
| “Renaming changes predictions, so person dependence is right.” | **Shown:** consistent renaming should preserve value answers. Such changes reveal incomplete symmetry under renaming. |
| “Correct-first intervention has not been done.” | **Shown:** saved first-card probes and now D1 exist. Earlier broad-sweep priorities are stale on this point. |
| “Handoff passes after dropping stuck seeds.” | **Shown:** learned-only +12.5 points is descriptive; registered all-seed D1 remains inconclusive. |
| “A significant handoff interval proves future seed reliability.” | **Shown:** that bootstrap resamples paired worlds within a fixed seed panel. It does not resample the population of trained models. |
| “Fresh generator seed proves no training overlap.” | **Shown:** D1 explicitly skipped overlap reconstruction. **Suggested:** overlap may be unlikely, but that is not a checked identity claim. |
| “All long training data are hashed by the manifest.” | **Shown:** checked_train verifies the saved prefix of batch digests; generation continues after those digests end. The frozen prefix covers 4,000 batches, not all long updates. |
| “These results settle the village model.” | **Shown:** different model, tokenizer, data, objectives and privileges. Cross-track causal attribution is unsupported. |
| “The village window was the main bug / capacity is ruled out.” | **Shown:** context, batch, parameters, exposure and evaluation population changed together. **Suggested:** window fit matters, but the pilots do not isolate it. |
| “The village forgetting gate passed, so retention works.” | **Shown:** it records a probe history, not a mastered A→B retention experiment with controlled storage and replay. |
| “Residual-question closure is a new demonstrated solution.” | **Established / your inference:** latent transition prediction has precedents; exact closure in this reader and H2 score alignment remain untested transfers. See literature discussion. |

Sources: [STUCK_PROBE][stuckreport], [earlier pool table][pooltable], [long shortcut report][longreport], [source files][model], [prior discovery brief][brief], [broad sweep][broad], [final sweep][finalsweep], [M03 confirmation][confirm]. Numerical corrections are also in this review's CSVs.

## 3. Bottleneck map and measurements that need no new training

**Suggested — ordering.** Trustworthy examples → usable subject/relation representation → correct first request → preserved returned identity and requested relation → correct second request → correct answer from selected evidence → stable behavior under interventions → success across new seeds. Failure early in this chain makes later conditional success an unreliable overall score.

| Priority and blocker | Evidence | Cheapest discriminating evaluation, when evaluation is authorized |
|---|---|---|
| 0. The test can reward shortcuts | **Shown:** fixed schema, small vocabulary, old validation reuse; supplied-gold copying is easy. | **Untested:** interpreter-check fresh paired worlds and question-only, family-only, bag-of-values and direct-subject baselines; inventory-preserving edits; output before model results are inspected. |
| 1. Addressing fails to start in some runs | **Shown:** three long runs have chance-person first requests and weak key probes. | **Untested:** on completed key-pool checkpoints, count empty-workspace own one-hop requests by person and relation, plus separate key/query score margins and the unchanged stuck criterion. No newly fitted probe is necessary for the behavioral check. |
| 2. A familiar attribute is not reused in the held-out position | **Shown:** competent plain runs read one hop/practiced chains but mostly miss A2 chains; relation shortcut improves this. | **Untested:** from an identical fact prefix compare ordinary A2(Oren) scores with second-hop scores after an actually own-selected correct Mira→Oren link, on identical eligible candidates. Score correct person and relation separately. |
| 3. Returned identity is not used reliably | **Shown:** D1 seed 4 has a large QD−Q gain; other shortcut seeds are ceiling or upstream failures. | **Untested:** apply the already specified diagnostic to the newly completed recipe only if it has residual eligible errors; retain all seeds and the registered learned/stuck strata. This is not rerunning old D1 to seek a pass. |
| 4. Correct evidence is present but binding/decoding fails | **Shown:** supplied-card choosing has been weak, and explicit addressing helps it. | **Untested:** stratify errors by exact retrieval provenance, then edit only the target attribute, an off-path same-relation attribute, or swap two bindings while preserving the value inventory. Report the whole population as well as correct-evidence subsets. |
| 5. Dependence on relevant facts / resistance to irrelevant facts | **Shown:** D1 adds held-out changed-link evidence for ten long models. **Untested:** a complete autonomous long-model suite including endpoint edits and irrelevant edits. | **Untested:** both answers correct after bridge edits; both correct after endpoint edits; both correct and identical after off-path edits. Mere prediction change/stability is insufficient. |
| 6. Training and inference distributions differ | **Shown:** 25% teacher insertions remain late; successful endpoints can nevertheless run autonomously. | **Untested:** teacher-versus-own error decomposition and own-state recovery rates on fresh worlds before changing the schedule. |
| 7. Reliable learning, rather than selected demonstrations | **Shown:** strong seed variation; current seeds largely share one data-generation stream. | **Untested:** lock the recipe and measure fresh independent initialization/data seeds without checkpoint selection. Treat a training run, not each answer, as the reliability unit. |
| 8. Fixed-template dependence | **Shown:** relation reads a known offset; only 16 identity tokens and single-token values. | **Untested:** consistent renaming, card order, field-order paraphrases, longer gaps, more people, and unfamiliar names as separately labeled stress cells. Do not mix every shift into one failure score. |

**Untested — minimal paired suite.** For each held-out chain, make three separately generated pair types: (i) change the queried person's friend to a person with a different target value, (ii) change the actual friend's requested value to a different value, (iii) change another person's same-relation fact, with the true chain unchanged. Keep questions identical within each pair. Include value-preserving swaps across irrelevant records so bag-of-values shortcuts cannot exploit answer-frequency changes. Check constraints with the world interpreter before scoring; log rejection rates so filtering does not silently simplify the task. Do not require the model's original answer to be correct before admitting a pair.

**Untested — state isolation.** Independently reset cards, slots, reader state and registers between worlds, including twins. Fork chain and standalone suffix from the same label-free fact prefix, never by placing the answer-revealing suffix before the chain. At evaluation use no gold evidence IDs, edit flags or oracle bridge inputs. Wrong-person masks and gold preloads remain separately marked diagnostics. Full store wipe with restoration is still needed to establish what storage a claim depends on; masking only decoder card rows is not a full memory lesion.

**Suggested.** The highest-value measurement is the joint per-seed result on this suite for the completed key-pool comparison. It simultaneously prevents a “not stuck” win from being mistaken for a reasoning win and tells us whether residual errors belong to request formation or evidence use.

## 4. Crutch audit

**Suggested — rule.** A structural bias is acceptable for the narrow toy milestone when disclosed and shared with the comparator. It becomes a crutch when the claimed learned capability is supplied by the interface, or when the claimed deployment would not have that interface. “Not label leakage” is necessary but not sufficient for a fair generalization claim.

| Mechanism | Judgment for the toy | What a general version must do |
|---|---|---|
| Separate learned pooling for keys and values | **Suggested:** fair learned architectural bias; no answer or parsed field is added. | **Untested:** select useful spans from varied text and resolve mentions; test whether shared reader coupling still causes collapse. |
| Relation shortcut at question-end minus two | **Shown:** supplies the location of the requested relation. **Suggested:** legitimate diagnostic shortcut, not learned question understanding. | **Untested:** content-based selection over question states, trained without field-position labels and tested on varied forms. |
| D1 subject/object masks | **Shown:** parse source/object and impose an exact matching restriction. **Suggested:** strong diagnostic, not an autonomous free-text solution. | **Untested:** learned mention grounding plus role-aware, reusable entity handles; handle aliases, pronouns and ambiguous references. |
| Shared person codes on key/query sides | **Suggested:** sharing an identity representation is a fair bias once identity/role grounding is learned. | **Untested:** if codes are added from known ENT offsets, success includes privileged parsing; new-name handles must be constructed within each world. |
| Gold cards and teacher insertions | **Shown:** supply evidence selection during training. **Suggested:** a disclosed instructional curriculum, but evidence/sample costs belong in comparisons. | **Untested:** remove insertion help at inference and demonstrate learning without permanent teacher dependence; obtaining evidence labels in village text is a separate cost. |
| Ordered evidence targets | **Shown:** provide an execution order as well as relevant facts. **Suggested:** procedural supervision, not discovered decomposition. | **Untested:** learn alternative routes and ordering from a common interface before claiming open-ended reasoning. |
| H2 suffix alignment | **Untested:** the proposed training pair reveals which remaining standalone problem is equivalent. A useful teaching signal, with extra structural supervision. | **Untested:** get suffixes from valid training provenance; never provide oracle suffix text to the evaluated chain or include held-out chain alignments. |
| Persistent decoder access to original inserted values | **Suggested:** fair information-preserving path if alternatives have equal evidence. | **Untested:** selecting and combining multi-token values, revisions and distractors instead of copying the sole answer-bearing card. |
| 16 fixed names and 16 single-token values | **Shown:** greatly restrict identity and output domains. **Suggested:** suitable unit task, weak evidence of language competence. | **Untested:** episode-local handles for novel strings and multi-token answers; separate tokenizer errors from reasoning errors. |
| Known fact lines, three relation types, one fixed two-hop order | **Shown:** supply segmentation and a tiny program family. | **Untested:** learned event/fact segmentation, role assignment, negation, temporal updates and variable compositions before village transfer. |

## 5. Literature that changes the decision

**Your inference — reading strategy.** The strongest precedents are controlled memory-network and compositional-learning studies, not billion-parameter retrieval systems. “Small” in papers often means millions or roughly GPT-2 scale, far above this 80k model. The sources below were opened directly. Results are restricted to their demonstrated domains; none establishes a cure for this exact architecture. The point of this section is to select discriminating interventions, not accumulate architecture names.

### Cold-start addressing and hard versus soft access

**Established.** Sukhbaatar et al.'s [End-to-End Memory Networks](https://arxiv.org/html/1503.08895v5) train differentiable, repeated memory reads on small synthetic QA tasks using answer supervision. Their ablations include positional encoding, weight tying and “linear start,” which temporarily removes the attention softmax. On the 1k-example bAbI setting, the reported mean error drops from 20.3% with positional encoding to 16.3% with linear start. They also select among ten restarts by training error, so the best result is not a demonstration of reliable learning from an arbitrary seed. Models use low-dimensional embeddings, but their smooth memory mixtures and encoding differ from this recurrent reader plus hard card insertion.

**Your inference.** This supports a cold-start optimization hypothesis and a smooth-training diagnostic, not the specific claim that a separate pool will work. Premonition already has evidence supervision, so enabling that supervision earlier is a smaller first change than replacing the retrieval mechanism. A future soft-read comparison should train both arms from scratch, include every candidate score/value read in compute, and evaluate the intended hard top-1 route separately. Success only with mixtures may use superposed evidence that a discrete card system cannot reproduce.

**Established.** [Neural LP](https://arxiv.org/html/1702.08367) learns compositions of differentiable relation operators over an explicitly structured knowledge base; entities and relations already have symbolic identities. Its distribution over entities can preserve multiple possibilities instead of committing to one bridge. **Your inference.** It is a useful structured upper bound and precedent for shared identity spaces. It does not show how a small reader learns identities and roles from text, nor justify a cost-free transition from soft distributions to hard pointers.

**Suggested — project consequence.** Do not currently spend an experiment slot on soft retrieval. If early direct addressing supervision and key separation both fail, an eval-only comparison between existing hard choices and a clearly privileged exact-identity route can locate an interface ceiling. A newly trained soft route would answer a different, later question. No checkpoint rescaling experiment alone tests the optimization benefit of soft training.

### Separating what locates a fact from what answers a question

**Established.** Miller et al.'s [Key-Value Memory Networks](https://aclanthology.org/D16-1147.pdf) explicitly separate addressing representations from output representations. On their movie-QA benchmark, document-memory accuracy is 69.9% for the compared memory network and 76.2% for the key-value system; their document representation ablations also change windows, titles and value centering. The setting has a large fixed collection and substantial engineered structure. These are not isolated 32-parameter pooling experiments.

**Your inference.** The transferable principle is to let addressing preserve subject/relation identity while values retain answer content. The ongoing key-pool comparison is a particularly economical test of this principle because initialization is matched. A positive result would show a useful intervention, not prove the previous pool irreversibly erased identity. A negative result would leave shared-reader coupling and query formation open. The movie result's language/representation dependence also argues against assuming toy addresses solve village grounding.

### Reusing a lookup after the first answer

**Established.** Lee et al.'s [Mathematical Reasoning in Latent Space](https://arxiv.org/html/1909.11851v1), [published at ICLR 2020](https://research.google/pubs/mathematical-reasoning-in-latent-space/), predicts representations of rewritten formal expressions and evaluates further rewrite judgments from those representations. Its controlled setup uses graph-based formula encoders, 1,024-dimensional representations, a fixed embedding network and alignment between representation spaces. It explicitly leaves merging the networks into a single end-to-end predictor of its own future embedding for future work.

**Your inference.** “The chain workspace should equal this reader's encoding of the residual question” is a stronger, untested adaptation, not the paper's demonstrated algorithm. A full-vector equality constraint may suppress useful history or force arbitrary coordinate choices. H2's narrower score-distribution alignment asks only whether the next lookup behaves like a competent standalone lookup, over identical candidates. Its strongest competitor is additional ordinary evidence cross-entropy at that same step, not an untreated model.

**Established.** The [Neural Data Router](https://arxiv.org/html/2110.07732) studies systematic generalization with gated updates and geometric attention, including compositional lookup tasks and ablations. Copy gating alone does not solve every ordering condition; combined routing matters. Its configurations are much larger/deeper than this toy, and hyperparameters vary across compared architectures.

**Your inference.** Preserving data identity while reusing operations is a sound design direction. The paper does not identify Premonition's missing component, and stacking its gates and routing onto this system would lose the single-change test. First compare the existing second request with a known-good standalone request.

### Held-out composition and instructional coverage

**Established.** [The Devil is in the Detail](https://aclanthology.org/2021.emnlp-main.49.pdf) shows that Transformer compositional-generalization results change greatly with training and architectural details, including positional representations, embedding scaling and stopping decisions; reported COGS/PCFG gains reflect configurations, not one universal switch. **Your inference.** Old validation selection cannot settle generality, and a failed step-embedding ablation does not rule out position dependence.

**Established.** [Data Factors for Better Compositional Generalization](https://arxiv.org/html/2311.04420) uses controlled Transformer experiments to examine diversity, scale, difficulty and repetition. More data is not equivalent to more varied compositional support; some repetition manipulations harm generalization. **Your inference.** Randomizing person/value assignments already creates many fresh bindings here, but hardly broadens the operator grammar. Adding three more attributes also changes memory size and exposure, so that negative screen does not refute a carefully controlled coverage intervention.

**Established.** Lake and Baroni's [human-like systematic generalization study](https://www.nature.com/articles/s41586-023-06668-3) uses episodic meta-learning with standard Transformer machinery, approximately 1.4M parameters, and training episodes that teach adaptation to new instruction mappings. **Your inference.** Training across task families can produce transfer, but the episode distribution supplies strong structure and substantially more capacity. This belongs after the narrow fixed-order milestone; it is not a reason to silently include A2 chains in training and keep calling them held out.

### Seeds, long training and apparent phase changes

**Established.** [Grokking](https://arxiv.org/html/2201.02177) demonstrates delayed generalization in small algorithmic tasks after fitting their training examples. [Nanda et al.](https://arxiv.org/abs/2301.05217) show, for modular addition, that continuous formation of a structured circuit can underlie an abrupt accuracy change. **Your inference.** Log continuous person margins, relation margins and first/second evidence ranks; a flat answer score alone need not mean no progress. Conversely, fresh-world search failure is not automatically memorization followed by grokking, and a modular-arithmetic mechanism does not transfer by analogy.

**Established.** [Wang et al.](https://arxiv.org/html/2405.15071v2) train scratch Transformers on synthetic facts and inferred facts. In their composition experiment, much longer training improves in-distribution inference but does not produce their out-of-distribution composition generalization, even at two million updates. Their main model has eight layers and width 768, not 80k parameters. **Your inference.** “Train longer” is not a principled answer to the missing relation-position transfer. Increased reuse and coverage can matter independently of late optimization.

**Suggested — project consequence.** The existing long-run comparison already buys useful information: some seeds escape and others remain stuck. A fixed extension would only become attractive after a reproducible predeclared progress measure predicts a near transition. Selecting the longest lucky checkpoint after viewing held-out scores is not a reliability intervention.

### Curriculum and removing teacher dependence

**Established.** Yao et al.'s [2025 multi-hop study](https://aclanthology.org/anthology-files/pdf/emnlp/2025.emnlp-main.490.pdf) compares progressively harder curricula with mixed lower-/higher-hop examples, using the same auxiliary examples and equal total update counts. Their four-hop large setting reaches perfect accuracy with a ×5 target-data budget under curriculum versus ×100 for the baseline. Main experiments train GPT-2-small-style models from scratch, with 12 layers, width 768 and three seeds. Facts are memorized entity profiles; this is not fresh-world card access, and their curriculum begins with lower-hop problems, not oracle insertion of cards.

**Your inference.** This is a useful controlled reason to teach a reliable elementary lookup before composition. It is not evidence that Premonition should keep a teacher forever, nor a small-scale power study of seed failure. Early empty-workspace one-hop addressing supervision tests the closer mechanism without adding held-out chains.

**Established.** [DAgger](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf) addresses the state-distribution shift caused by acting with one's own policy instead of an expert; its guarantee depends on its assumptions and learning reduction. [Scheduled Sampling](https://arxiv.org/abs/1506.03099) gradually exposes sequence models to their own inputs, while [Huszár's analysis](https://arxiv.org/abs/1511.05101) identifies a statistical inconsistency in that formulation. **Your inference.** These support checking errors on the learner's own states, not assuming a probability ramp is a cure. Premonition's state-dependent evidence supervision is not identical to scheduled token sampling, so that critique does not by itself invalidate this curriculum.

### Causal sensitivity and the eventual retention baseline

**Established.** [Teney et al.](https://arxiv.org/html/2004.09034) use counterfactual examples and gradient-based paired supervision, including controls trained on the same augmented examples. **Your inference.** The transferable control is crucial: compare the same fact-edit triplets under ordinary answer cross-entropy and under an added paired objective. The proposed invariance divergence plus relevant-change margin is not the same loss as theirs and remains untested here; both correct answers matter more than any sensitivity statistic.

**Established.** [Dark Experience Replay](https://papers.nips.cc/paper/2020/file/b704ea2c39778f07c617f6b7ce480e9e-Paper.pdf) uses bounded reservoir memory and replay of stored outputs, with an added label-replay term in DER++. Its experiments concern continual classification, not this card system. **Your inference.** A bounded ordinary replay baseline is mandatory before attributing A→B retention to sleep or consolidation. Stored examples, labels and logits all consume the declared storage budget.

**Established — recent scale check.** The authors' [GRITHopper project](https://ukplab.github.io/eacl2026-GritHopper/) presents a 7B multi-hop retriever and compares post-retrieval objectives under controlled retrieval sequences. **Your inference.** Its matched-data/compute discipline is useful; its performance is not evidence that a mechanism will bootstrap an 80k scratch model. This is why recent large-model retrieval results do not outrank the small, direct tests above.

## 6. The decision tree: at most six single-change experiments

**Untested — status.** Everything in this section is a proposed future experiment, not authorized execution or a claim of efficacy. The two in-flight studies are inputs to the tree and must not be duplicated. The six slots are alternatives/conditional continuations, not a six-arm shopping list.

### Lock the outcomes before choosing a branch

**Untested — K definition.** Keep the key-pool study's registered endpoint: stuck means one-hop <384/512 and its registered two-sided Fisher test has p<0.05, separately for plain and shortcut comparisons. Call K+ a reduction in stuck runs under that rule. For planning only, define a useful reduction as at least ten percentage points: K− requires the upper endpoint of a separately reported 95% score interval for that reduction to be below ten points; otherwise a non-significant result is K?. This supplementary classification does not replace the registered test. A non-significant result is not proof that pools are equivalent. Do not select whichever of two recipes happens to be significant and call that one unadjusted confirmatory test.

**Untested — H definition.** H+ means the registered handoff advancement requirements and fresh confirmation are met in the relevant, competent parent recipe. H− means the no-useful-effect rule is met with enough eligible errors. H? means inadequate opportunity, failed controls or an inconclusive effect. The observed shortcut result is H?, with a useful local effect; the observed plain result is H− for this intervention. Pooling changes can alter either status.

| Pooling outcome | H+ after competent first addressing | H− with adequate opportunity |
|---|---|---|
| K+ | **Untested:** skip E1 if first addressing is reliably competent; E2 only if identity failures remain. If the full paired gate already passes, skip E2–E4. | **Untested:** compare standalone versus second-hop scores; E3 only for a residual-query mismatch, E4 only when correct evidence is obtained but paired answers fail. |
| K− or no useful pooling benefit | **Untested:** E1 first. An identity handoff cannot rescue missing or wrong first facts; E2 waits for competent first addressing. | **Untested:** E1 first, then the same score comparison. E3 follows only if the failure is specifically reuse; no broad handoff module. |

**Untested — H? branch.** Complete the existing result interpretation, then use the new parent recipe's residual eligible errors to decide whether one fresh diagnostic panel is informative. Do not rerun the old five seeds until a significance threshold is crossed. If almost every competent seed is already correct, no training experiment on handoff is needed. If most seeds are stuck, E1 takes precedence. If a mask intervention fails its controls, fix the diagnostic before attributing a mechanism.

### Common pass marks and power

**Untested — freeze a per-seed gate G.** Use one scored question per independently generated world for each single-question cell. Use independent paired worlds for each intervention cell; score both twins jointly. Test without teacher insertion, gold preloads or correctness filtering, at the declared deployment loop budget. Primary narrow-domain cells:

| Cell | Fresh observations per seed | Minimum correct to pass |
|---|---:|---:|
| Own one-hop | 2,048 worlds | 1,969 |
| Own practiced two-hop | 2,048 worlds | 1,969 |
| Own held-out A2 two-hop | 2,048 worlds | 1,876 |
| Held-out changed-link pair | 1,024 pairs | 945 both correct |
| Held-out changed-endpoint-value pair | 1,024 pairs | 945 both correct |
| Held-out irrelevant-fact pair | 1,024 pairs | 945 both correct and invariant |

**Shown — calculation.** These cutoffs reject accuracy at or below 95% for the first two cells and 90% for the other four using exact one-sided binomial tails at 0.05/6 per cell. Bonferroni makes the six within-seed lower bounds jointly at least 95% under independent-world sampling; pair members are never treated as independent. They are deliberately stronger than observing 90% once. At true 93% accuracy, a 1,024-pair cell clears its cutoff about 83.1% of the time; at true 95%, about 99.99%. Thus marginally adequate models can fail this demanding operational gate. [World-gate calculations][worldpower]

**Untested — experiment pass.** Unless stated otherwise below, treatment must pass G in at least 90% of its independently trained seeds, outperform its control on seed-level G success by the predeclared two-sided Fisher test, and show the mechanism-specific change. Record the original stuck count as a secondary, directly comparable endpoint. A reduction in stuck rate without held-out/pair success is a useful component result, but it does **not** pass this complete experiment gate or the milestone. It may justify using that component as a transparently provisional parent for a subsequent targeted fix.

**Untested — independence and selection.** Future trials use independent training random seeds, including data-generation streams, with matched distributions and budgets. Freeze recipe selection on development results and keep the final cohort sealed. Shared old data seeds measure initialization sensitivity only. If using matched seeds in a future comparison, predeclare a paired analysis and recalculate its power from discordance assumptions; do not quietly apply the independent-arm power table to it. Preserve the already registered Fisher analysis of the in-flight study.

**Shown — exact power calculation.** For each possible pair of success counts, compute its probability under independent binomial arms and sum probabilities where the two-sided probability-ordering Fisher p-value is <0.05. These are scenario calculations, not an estimate that a proposed treatment will achieve the assumed effect. [Full power table][power]

| Independent seeds per arm | Success 70%→95% | 70%→90% | 80%→95% | 90%→97% |
|---:|---:|---:|---:|---:|
| 40 | 82.1% | 53.4% | 41.1% | 8.0% |
| 80 | 99.0% | 86.7% | 79.3% | 31.0% |
| 100 | 99.8% | 93.5% | 88.3% | 42.4% |

**Shown.** This power is for the Fisher contrast alone, not the conjunction of significance, at least 90% passing G, and mechanism checks. At true seed success 95%, the count rule alone passes 36/40 about 95.2% of the time. Joint power is lower than either marginal power and depends on mechanism-effect assumptions that are not available from the old runs. Exploratory branch tests do not collectively establish familywise significance; the independent final confirmation is the protection against selecting lucky recipes.

**Untested — final reliability confirmation.** After locking one recipe, use 80 new independent training replications and fresh sealed world panels. Require at least **77/80 to pass G**. This gives a one-sided exact 95% lower bound above 90% for the probability that a fresh training run passes the specified benchmark. For comparison, 36/40 only yields a 78.6% lower bound; 76/80 yields 88.9%. This is a bounded claim about this toy distribution, not every future environment. [Seed bounds][bounds]

**Shown.** The 77/80 certification rule passes with probability 42.8% if true seed success is 95%, 78.1% at 97%, and 92.3% at 98%. It is intentionally demanding. Failure to certify a genuinely 95% recipe is possible and is not proof it is poor; report the interval and do not add seeds opportunistically until the threshold passes. [Gate probabilities][gatepower]

**Untested — cost convention.** Using Ben's supplied capacity/rate, 80 ordinary runs take one 30–45 minute wave, costing $0.24–$0.36 of rental time. A 200-run comparison needs three scheduled waves: 1.5–2.25 hours and $0.72–$1.08 before evaluation/setup. These are conditional planning calculations, not current rental quotes or spending authorization. The expanded paired suite, CPU work, transfers and auxiliary forwards are additional; record actual concurrency and billable wall time. Reserve up to twice the ordinary training allowance for extra-pass experiments and stop for review if that bound is insufficient, rather than calling their teacher computation free.

### E1 — Start empty-workspace one-hop addressing supervision during the gold phase

**Untested — trigger and single change.** Run only if key pooling leaves a material stuck rate. During the existing gold phase, add one auxiliary empty-workspace one-hop pass with the existing ASK binary loss plus evidence set cross-entropy, weight 0.5. Restrict it to ordinary training one-hop questions; use no new data or two-hop teacher targets. After the gold phase, remove this auxiliary term. Keep the original answer/LM path, initialization, phase boundaries, updates and later curriculum identical.

**Untested — control.** Compute the same auxiliary pass but multiply its loss by zero; both arms receive the same examples, accounting and diagnostic logging. Do not merely enable ASK after gold cards have already been inserted, because that teaches “nothing remains to fetch.” Charge the auxiliary pass and freeze the reference update/phase schedule, so adding its FLOPs does not silently move every curriculum boundary.

**Untested — mechanism, sample size and pass.** Forty seeds per arm initially; 82.1% Fisher power for a large 70%→95% success change. G must pass in ≥36/40 treatment seeds, with a significant seed-level G contrast. Separately, the intended mechanism requires fewer original-definition stuck runs and earlier correct-person own requests, without sacrificing relation selection. There is no basis to predict the actual effect size, and 40 is not a strong negative test for smaller gains.

**Untested — strongest objection / cheap discriminator.** Answer/value specialization may not be the cause; a weak key-query interface can receive more supervision and still fail. Before training, inspect completed pooling runs' first-request person accuracy and the saved transition curves. If even a separated key remains chance-person after substantial supervised retrieval, a purely late-onset explanation becomes less compelling.

**Untested — falsifier, cost and what disappears.** If the address margin/first-hop success does not improve under the early signal, the proposed timing mechanism fails at this budget; if it improves but G does not, it is a partial bootstrap fix. Ordinary base cost $0.24–$0.36 plus measured auxiliary/evaluation overhead, planning ceiling twice that training amount. Success makes more random restarts, temperature sweeps and longer uninstrumented warmups unnecessary.

### E2 — Supply only the returned identity at the second request

**Untested — trigger and single change.** Only after reliable first addressing and a confirmed useful handoff effect in the chosen parent. Activate the existing D-style destination-subject restriction after an actually own-selected link, during training and inference; leave all relation scores, ASK decisions, first requests, losses and other steps unchanged. This is an explicit structured identity route, not proof that the model learned the binding operation.

**Untested — control.** Parse and compute the same mask but do not apply it. No Q mask in either deployed arm, no forced correct first card, no oracle answer or correct bridge substituted. If the first card is wrong, the transported destination must be the wrong one actually returned. The contrast isolates identity transport once the first retrieval is competent.

**Untested — sample size and pass.** One hundred seeds per arm if training is actually needed; 88.3% Fisher power for 80%→95% G success, only 42.4% for 90%→97%. Require ≥90/100 passing G, significant improvement, and removal of the observed wrong-person second-request errors. A 90% point pass rate is an experiment advancement mark, not the separate final reliability certification.

**Untested — strongest objection / cheap discriminator.** The observed effect could be peculiar to seed 4, and the restriction may route errors confidently after wrong links. First evaluate D alone on the completed competent parent. If it already passes the full suite, a new training comparison may be unnecessary for the narrow structured upper bound. If D has no benefit with sufficient residual opportunities, do not train this arm.

**Untested — falsifier, cost and what disappears.** No gain in unconditional G despite fixing second-person selection falsifies identity transport as the remaining sufficient fix. Base $0.72–$1.08 plus mask/evaluation cost. Success can remove H2 or added entity-register machinery from the narrow toy path; it does not remove the need to learn the parsing interface before village use.

### E3 — Align the second request with a competent standalone suffix

**Untested — trigger and single change.** Use H2 only when standalone lookup works, first addressing is competent, and the second request differs on identical eligible evidence. On training A0/A1 chains, after an own-selected correct link, replace an auxiliary second-request evidence-CE term by a stop-gradient KL alignment to the same model's standalone suffix distribution. Fix weight 0.5 and temperature 1. Keep ordinary losses unchanged.

**Untested — strong control.** Both arms see identical allowed chain/suffix pairs, extra forwards, eligibility filtering, evidence labels and auxiliary weight; control uses additional ordinary evidence cross-entropy at that same second request. Thus the one experimental difference is the auxiliary target/objective, not more evidence exposure. No A2 chain, A2-chain suffix-alignment example, or bridge-conditioned A2 auxiliary target is allowed in training.

**Untested — implementation contract.** Fork from the same label-free fact prefix with separate question states. Align candidate identities, causal cutoffs, age buckets, NULL and the chain's exclusion of previously fetched cards. Capture the existing forward's next scores; an extra Think step would change the intervention. Distill only where the masked teacher is correct, log that eligible fraction, and evaluate every chain unconditionally. A teacher that is rarely correct or an own policy that rarely reaches the correct first card makes this an unsuitable experiment.

**Untested — sample size and pass.** One hundred seeds per arm, 88.3% power for 80%→95% G success. Require ≥90/100 passing G, significant improvement over extra evidence CE, and improved actual second-card selection rather than just smaller KL.

**Untested — strongest objection / cheap discriminator.** This can be ordinary stronger evidence supervision in disguise; a nearly one-hot teacher makes KL close to ordinary CE, and a wrong teacher or enforced similarity can damage useful context. An eval-only comparison of standalone and second-hop ranks on common candidates is the cheapest discriminator. If they already agree but the policy still fails, do not run H2.

**Untested — falsifier, cost and what disappears.** If CE matches or beats KL, distinctive distribution reuse is unsupported; if KL decreases without improving own retrieval and G, reject the objective as a practical fix. Three base waves cost $0.72–$1.08; extra forwards may require up to the declared 2× training allowance, plus evaluation. Success avoids a full latent-workspace equality loss, fresh modular architecture, or wider relation shortcut.

### E4 — Teach relevant change and irrelevant stability with the same examples

**Untested — trigger and single change.** Only if the model usually retrieves both required facts but fails the paired answer cells. Construct valid base/relevant-edit/irrelevant-edit triplets using permitted training compositions. Compare ordinary answer CE on the triplets with the same CE plus 0.1 times a Jensen–Shannon penalty for invariant answer distributions and 0.1 times a relevant-change log-odds margin penalty, margin 1. This grouped paired objective is the single intervention.

**Untested — control.** Exactly the same triplets, batching, tokens, loss opportunities and evidence supervision. Match total processed tokens/compute, not merely the number of triplet groups. A grouped-CE improvement by itself belongs to the data intervention, not the new loss. No edit flag or pair role enters the model's input; no held-out chain is generated.

**Untested — sample size and pass.** One hundred seeds per arm, 88.3% power under 80%→95% G success. Require ≥90/100 passing G, significant superiority to same-triplet CE, and gains in both relevant-pair cells without losing the irrelevant-pair cell or standalone competence.

**Untested — strongest objection / cheap discriminator.** The decoder may learn to react to superficial editing cues; answer loss cannot differentiate through hard selection. First inspect the unconditional fraction of failures with both facts already selected and use inventory-preserving edits. If retrieval failure dominates, skip this arm.

**Untested — falsifier, cost and what disappears.** Improvement only in changed-output frequency, or no improvement beyond identical-data CE, rejects the distinctive paired-loss claim. At a matched ordinary token budget, base $0.72–$1.08 plus paired-loss overhead and evaluation; preserving 12,000 full triplet updates instead would increase exposure/cost and must be declared separately. Success can make a more complex binding decoder or token-level reread unnecessary.

### E5 — Remove the remaining teacher insertions

**Untested — trigger and single change.** Only after the parent passes G reliably. Keep the first 60% of the reference training compute schedule unchanged; over its final 40%, ramp own-insertion probability from 0.75 to 1.0. Control stays at 0.75. Hold evidence losses, HALT supervision, data and total reference budget fixed. This tests the effect of removing insertion help; it does not remove oracle evidence labels from the training loss.

**Untested — sample size and pass.** One hundred independent seeds per arm. This is a non-inferiority test, not a demand for superiority at a ceiling: predeclare a one-sided 95% score interval for the difference in G success, with its lower bound above −0.10, and require treatment G ≥90/100. G already includes the fixed held-out and paired-accuracy bounds. Under equal true success of 95%, the usual normal planning formula gives about 59 seeds per arm for 80% power at a 10-point margin; 100 gives approximately 94.5%. This is an approximation, unlike the exact Fisher table, and actual discrete-test power depends on the chosen interval implementation.

**Untested — strongest objection / cheap discriminator.** Teachers may be useful training scaffolding even though inference is already autonomous; removing them could hurt without answering any current inference failure. Inspect own-state error/recovery rates first. If the goal is only autonomous inference and those rates already meet G, this experiment is optional, not a condition for acknowledging that result.

**Untested — falsifier, cost and what disappears.** Failure of non-inferiority at this schedule means the proposed removal is not established safe; it does not prove teachers are inherently necessary. Base $0.72–$1.08 plus evaluation. Passing supports a simpler late curriculum and removes speculation about hidden dependence on teacher-selected cards at the end of learning.

### E6 — Replace the fixed relation-position hint with learned question selection

**Untested — trigger and single change.** After the narrow task works, test interface generality before village transfer. Both arms receive the same canonical plus varied question forms and the same permitted compositions. Replace the supplied relation selector by learned content-based pooling over question states, feeding the existing relation projection/gate. Do not add field-position supervision.

**Untested — fair control.** Use a supplied *correct relation span* in every form, not a deliberately broken end-minus-two offset on reordered questions. The control is a disclosed parsing upper bound. Match the remaining architecture and account for the small pooling parameter difference; constrain the learned pool to the same question input region. This comparison changes the selector while holding the new data distribution common to both arms.

**Untested — sample size and pass.** One hundred seeds per arm, using the same planned 10-point non-inferiority margin and approximate 94.5% power at equal 95% seed success. Require ≥90/100 to pass G separately on canonical and held-out wording panels; no A2 chains in training. Report wording and composition transfer separately, not as one average.

**Untested — strongest objection / cheap discriminator.** Fixed ENT tokens and a tiny relation vocabulary can let the pool learn another shallow cue; removing one shortcut is not learned free-text understanding. First inspect performance when the requested relation moves within otherwise familiar wording. If the interface needs broader role/coreference learning, admit that as a new research stage rather than expanding this arm.

**Untested — falsifier, cost and what disappears.** A canonical-only pass or persistent dependence on the relation's position fails the intended transfer. Base $0.72–$1.08 plus evaluation. Success removes this one known-position hint; if E2's parsed identity mask remains, free-text readiness is still unestablished.

**Suggested — stopping rule for the sequence.** Use the first applicable arm, not all six. Stop architecture changes when a frozen recipe passes the independent reliability confirmation on the declared narrow task. Retain a component only with its measured benefit and remaining limitation stated. An unsuccessful low-powered contrast should narrow the effect range, not launch six more loosely related variants.

**Untested — novelty.** No new learning mechanism is claimed for these six slots. They apply auxiliary supervision, explicit routing, distillation, paired consistency, curriculum scheduling and learned attention to a tightly specified failure. The useful contribution would be a reliable result and an explanation that survives its control.

## 7. Beyond the milestone: admission gates

### A bounded fair trial of Think

**Untested — entry conditions.** First require a locked, reproducible parent with reliable autonomous addressing, fresh paired evidence, a credible decoder, and no correctness-conditioned primary metric. If the error is still “wrong person's card” or “wrong requested relation,” adding generic compute does not isolate reasoning. Avoid an accuracy ceiling by reserving a separately declared task where combining or updating information is actually needed.

**Untested — two distinct questions.** Measure (a) whether extra Think computation improves decisions given identical available evidence, and (b) whether the complete Think-controlled policy beats a simpler repeated-lookup controller per unit of total compute. For (a), keep retrieved facts, their order, retrieval opportunities and answer interface identical and vary only the extra state updates; include a comparable feedforward-compute control. For (b), permit each controller its own choices but charge all retrieval and encoding, and give the simpler controller the same inputs and supervision. A result in (a) does not establish (b).

**Untested — accounting and stopping.** Lock a small set of compute budgets before seeing held-out results. Report accuracy, seed success, actual reader/Think/decoder FLOPs, measured latency, peak memory and training/search cost, including failed trials. Report end-to-end cost for one, ten and one hundred questions per world so amortized fact encoding is visible. Do not equate recurrent weight sharing with free compute, or attention dot-product savings with whole-system speed. Select extra Think only if it improves the accuracy–cost frontier on fresh data with uncertainty across seeds; no frontier gain at the bounded budgets is a useful negative result.

**Suggested — likely toy distortion.** Because one answer-bearing attribute card contains the single-token final answer, the toy can reward retrieval plus copying while leaving little useful work for further Think. Conversely, more loops grant more retrieval opportunities, so a gain from loop count need not be a gain from better reasoning over an unchanged evidence set.

### Early A→B retention, with weights and cards distinguished

**Untested — entry conditions.** Establish that A was learned before teaching B, and that B is learned after the intervention. For an early operational gate, require A ≥95% before B, B ≥90% after B, and A ≥90% afterward with a decline no greater than five percentage points, on fresh held-out worlds and the relevant paired cells. Failure to learn B cannot count as successful retention. Use multiple independent training replications and retain their individual trajectories.

**Untested — first define what is retained.** For *procedural retention*, A is a learned lookup/composition skill and B is a distinct, noncontradictory skill that uses overlapping model machinery; evaluation supplies newly randomized facts. The retained procedure should live in weights, while those new facts legitimately live in the episode input/cards. For *factual retention*, A is a fixed set of facts taught before B. If answering A depends on keeping its cards, report external-memory retention; it is not evidence that the facts were consolidated into weights.

**Untested — explicit pilot budget.** A workable first budget is 256 KiB of all persistent A-derived storage, with replay capped at 10% of B's total processed training tokens. Count raw source text, token IDs, cards, source offsets, metadata, stored labels/logits and teacher snapshots that differ between arms. Freeze the total B training compute; replay consumes it rather than increasing it. Include zero-replay and ordinary bounded-replay references before a proposed consolidation method. Model/optimizer bytes should also be reported, with equal treatment where they are common costs.

**Shown / suggested — storage implication.** A 16-float key plus a 32-float value is 192 bytes at FP32, before metadata or source text; 24 such fact cards have 4,608 bytes of vector payload. That is not the total memory footprint. Persistent raw text kept “just in case” can dominate the apparent compressed memory advantage. [Store source][store]

**Untested — readouts that identify the storage location.** Measure A immediately before B and after B with the normal store, with all A cards/source caches removed, and after exact store restoration. Clear entity slots and reader states too. For factual A, a collapse after the wipe assigns credit to external storage. For procedural A, use fresh facts in every evaluation; do not demand answers to absent facts as a weights test. Compare stored old vectors with any explicitly budgeted re-encoding scheme because B's updates may make old keys incompatible with new queries. Rebuilding silently from an uncounted diary would invalidate the storage comparison.

**Suggested.** Sleep or consolidation becomes meaningful only if it beats ordinary replay on retained A *and* learned B within the same total memory, replay and compute budgets. It need not be novel to be useful.

### Admission to the village track

**Shown — village-only results.** Three saved 600-second pilot artifacts use nominal “4M”/“28M” labels, one seed, a 7,289-ID tokenizer, and different context/batch/exposure settings. The actual parameter counts differ from those labels. Every saved gate is FAIL and every leak status is “leaking.” [Separate village CSV][village] [Pilot interpretation][village_report]

| Village pilot | Actual parameters | Context / batch | Updates | Held-out visible | Train-held-in |
|---|---:|---|---:|---|---|
| Nominal 4M, old window | 5,222,144 | 768 /32 | 16,100 | 677/3,782 =17.90% | 382/991 =38.55% |
| Nominal 28M | 29,345,280 | 768 /32 | 4,857 | 632/3,782 =16.71% | 356/991 =35.92% |
| Nominal 4M, aligned window | 5,549,824 | 2,048 /16 | 10,128 | 881/3,763 =23.41% | 475/991 =47.93% |

**Shown.** The visible totals pool validation and test; excluded answer-repeat counts change from 45 to 64. Unseen template and style metrics use the same visible population in these pilots rather than isolated shift interventions. The “forgetting baseline” has seven logged time points. The tokenizer identity is 2460b134… with 7,289 IDs, not the primary admission identity described in the prior audits. These artifacts do not support a fresh, label-free, controlled retention or architecture verdict. [Village CSV][village] [Final-sweep audit][finalsweep]

**Untested — conditions before transferring a card mechanism.** Lock preprocessing/tokenizer/world-generator identities, label-free inputs, non-overlapping development/test visits, verified evidence visibility and a non-leaking evaluation. Separately establish literal copying, person/role grounding, one-hop selection and the narrow two-hop intervention suite in that language interface. Keep the village model's trainable parameter, compute, exposure and evidence budgets comparable. Start with the minimal demonstrated card change, not the whole sleep/codebook/motivation design. A learned question selector does not by itself solve fact segmentation, coreference, temporal changes, negation or multi-token outputs.

**Suggested — the largest transfer traps.** Atomic ENT tokens hide name processing; fixed positions hide parsing; one fact per line hides segmentation; one value token hides generation; an immutable visit hides contradiction/update semantics; a tiny fixed relation grammar hides program discovery; rebuilding every episode's cards hides persistent-index drift. These are not reasons to abandon the toy. They are reasons to name exactly which interface has been validated before moving outward.

## 8. What to stop doing

- **Suggested:** stop using gold-only read accuracy, card sensitivity or one lucky seed as evidence of complete two-hop reasoning.
- **Suggested:** stop treating the old 50% held-out screen as the milestone; keep it for historical comparability.
- **Suggested:** stop explaining every plateau as grokking, every weak probe as absent information, or low temperature as a proven root cause.
- **Suggested:** stop rerunning step-embedding, cooldown, relation-count or ordered-evidence variations without a measured intermediate failure they would fix.
- **Suggested:** stop adding memory width, raw-text rereads, a new decoder or more Think loops while the request still asks for the wrong fact.
- **Suggested:** stop promoting a handoff story from a learned-only subset while hiding the stuck seeds; keep both strata and the unconditional score.
- **Suggested:** stop paying for H2 teacher forwards or richer data in only one arm and attributing the difference to the special loss.
- **Suggested:** stop calling persistent cards weight learning, or calling an uncounted diary free memory.
- **Suggested:** stop optimizing on the same held-out relation panel and presenting it as an untouched generalization test.
- **Suggested:** stop searching for novelty as a prerequisite. The available evidence calls for a few known mechanisms, careful controls, and a reliable result.

## 9. Audit trail and calculation notes

**Shown.** The following new tables contain the recomputed results. They preserve source paths and counts instead of relying only on rounded percentages:

- [45 card runs][runs], [screen summary][screens], and [observed curriculum transitions][curves].
- [Handoff pair counts rebuilt from bits][handoff] and [learned/stuck strata][strata].
- [Village pilots, separately tabulated][village].
- [Exact Fisher power scenarios][power], [one-sided seed reliability bounds][bounds], [count-gate probabilities][gatepower], and [within-seed accuracy-gate probabilities][worldpower].
- [Read-time source hashes and missing in-flight paths][snapshot].

**Shown — reproduction rules.** Screen counts apply the original integer thresholds to saved validation counts, not rounded accuracies. “Both facts” comes from all_gold_fetched. Learned-halting counts are saved slice accuracy times its saved denominator, rounded back to an integer. Handoff twins are grouped using pair_of; each condition passes a pair only when both correctness bits are 1. No tensor files are involved.

**Shown — statistical formulas.** For n seeds per arm and success counts a,b, Fisher's null conditional probability is C(n,a)C(n,b)/C(2n,a+b). Its two-sided p-value sums feasible tables with conditional probability no greater than the observed table's probability. Power sums Binomial(n,p0)[a] × Binomial(n,p1)[b] over tables with p<0.05. One-sided exact reliability lower bounds solve P_p(X≥k)=0.05. Gate operating characteristics are P_p(X≥required count). Accuracy-cell cutoffs use the same binomial tail with alpha=0.05/6. These formulas assume independently sampled units at the level stated; they are not valid if repeated correlated questions are substituted for independent worlds or training seeds.

**Shown — source hierarchy.** Numerical JSON and actual source take precedence over a prose summary when they disagree; saved outputs still require trust in their original evaluation implementation. The source snapshot includes the 45 run JSONs, D0/D1 manifest/output, relevant frozen files and additive scripts. It is not a claim to have verified all historical model binaries, every external dependency, or every later edit by another agent.

[runs]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/card_runs.csv
[screens]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/screen_summary.csv
[curves]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/curriculum_observed.csv
[handoff]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/handoff_pairs_recomputed.csv
[strata]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/handoff_strata.csv
[village]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/village_separate.csv
[power]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/power_exact_fisher.csv
[bounds]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/seed_reliability_bounds.csv
[gatepower]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/gate_operating_characteristics.csv
[worldpower]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/world_gate_operating_characteristics.csv
[snapshot]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-deep-dive-2026-09-19/source_snapshot.json
[model]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/model.py
[store]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/store.py
[train]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/train.py
[toy]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/toy_ladder.py
[bypass]: /Users/ben-hannan/Desktop/projects/beautiful-model/archive/opus-ovn-20260918-235851/frozen/premonition/answer_path.py
[retrieval]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_ovn_retrieval.py
[shortcut]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_relation_shortcut.py
[keypool]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_key_pool.py
[diag]: /Users/ben-hannan/Desktop/projects/beautiful-model/scripts/premonition_handoff_diag.py
[d0]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-handoff-20260919/d0.json
[d1]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-handoff-20260919/d1.json
[manifest]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-handoff-20260919/manifest.json
[personjson]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-relcut-long-20260919/person_probe.json
[stuckjson]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-relcut-long-20260919/stuck_probe.json
[stuckreport]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-relcut-long-20260919/STUCK_PROBE.md
[pooltable]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/astra-stuck-runs-prompt-2026-09-19.md
[longreport]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/claude-relcut-long-20260919/REPORT.md
[m03]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-milestone-03-m03-20260919-071009.md
[direct]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-milestone-03-continuation-direct-reader.md
[address]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-milestone-03-address-keys-results.md
[confirm]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-milestone-03-address-confirm.md
[compare]: /Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/opus-m03-20260919-071009/confirm/compare.json
[brief]: /Users/ben-hannan/Desktop/projects/beautiful-model/reviews/premonition-discovery-2026-09-19/brief.md
[broad]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/research/broad-sweep-2026-09-19/README.md
[finalsweep]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/research/final-sweep-2026-09-19/README.md
[village_report]: /Users/ben-hannan/Desktop/projects/beautiful-model/design/06-step1-pilot-results.md

## 10. For Ben: thirteen sentences in plain language

1. **Untested — target:** If Mira's friend is Oren and Oren's shoes are blue, Premonition should answer “blue” when asked about Mira's friend's shoes.
2. **Shown — definition:** This is a two-hop problem, meaning it needs one lookup to find Oren and another to find his shoes.
3. **Shown:** Some saved runs do this very well, but others never reliably choose the right person's fact.
4. **Shown — definition:** A seed is the starting random setup for a training run, and changing it currently makes a large difference.
5. **Shown — definition:** A card's key is its search label, while its value is the information returned when that card is selected.
6. **Suggested:** Giving keys their own way to summarize a sentence may help preserve whose fact it is, but the large comparison has not yet supplied results here.
7. **Shown — definition:** The handoff test means explicitly passing the person found in the first lookup to the second, and it helped one partly successful run much more than the others.
8. **Suggested:** That makes handoff a possible remaining problem, rather than an explanation of every failed run.
9. **Untested:** A proper check should change Oren's shoes and require the right new answer, then change someone else's shoes and require the original answer.
10. **Untested — definition:** A control is a matching run without the proposed change, so we can tell whether that change helped.
11. **Untested:** If separate key summaries do not fix the early failures, my first training change would teach the model to find the right person's card from the start.
12. **Untested:** We should call the system dependable only after many new runs pass both the ordinary questions and those fact-change checks.
13. **Shown:** The village model uses different text and a different model, so success with these little cards would not yet prove that the village model can do the same thing.

## 11. What reading alone cannot decide, and the single next measurement

**Untested.** Reading cannot decide whether separate pooling reduces the stuck rate; whether the remaining weak runs fail first on subject identity, relation reuse or decoding; whether untested irrelevant edits fool the successful autonomous models; or whether teacher removal preserves learning reliability. The mismatched pooling summaries cannot be reconciled without their original mass outputs or a newly authorized evaluation. Saved linear probes cannot prove absence of information, and source inspection cannot validate the bytes/behavior of unloaded historical checkpoints.

**Untested.** Reading also cannot establish whether extra Think earns its compute, whether learned procedures survive B training, whether stored vectors remain useful after weight changes, or whether this interface can learn free-text grounding. Those are later empirical questions, not evidence against the present narrow design.

**Suggested — the single measurement I most want next:** **the fraction of seeds in the completed key-pooling comparison that pass the full fresh-world two-hop paired suite, reported separately for plain/shortcut and pool/control, with first- and second-request error counts attached.** Keep its registered stuck-rate test intact. This one joint behavioral measurement would tell us whether the cheap change reaches Ben's milestone, only fixes the cold start, or leaves a specific failure worth the next single-change experiment.
