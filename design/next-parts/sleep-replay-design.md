# Sleep replay: learning from verified experience (design only)

Thread: "Design: sleep replay". Written 2026-10-03. Nothing here was run. No training, GPU, vast spend or queue change is requested or implied.
Labels: **shown** (a result on main, file named), **suggested** (reasoning or literature), **untested**.
Small card experiments and the village model are kept out of every claim. The earlier sleep results below come from the older small loop solver (sums, Latin grids, mazes), not from the current Premonition model, so they are evidence about recipes, not about this model.

## 0. Status of inputs (read this first)

- (Superseded by section 13, which reconciles against CURRENT.json and design v5.) Originally `docs/premonition-status/CURRENT.json` and integrated design document v5 were **not on any pushed branch I could read** (`origin/claude/premonition-launch-recovery-96c708` ends at a163a3163, 2026-10-01). I asked the channel session to get them. Everything below about the current model comes from Ben's brief (frozen LFM2.5-1.2B, contextual reader, ~9M latent core with 4 loops, 8 prefix vectors, calculator return unchanged). Anything that depends on v5 details (exact trainable parameter groups, checkpoint pins, data pins) is **unverified** and must be checked against v5 before sealing.
- Dependencies on other parts: the English pilot (what the model can do at current size), fair scaling (which sizes), notebook (facts live there, so sleep protects skills only), creative prototype (supplies the attempt-checker-accept loop this part reuses).
- Consumed fresh questions (the 128 outputs / 8 checkpoints evaluation) are never replay or tuning data.

### Reconciled against CURRENT.json (commit 42552d9ee, confirmed 2026-10-03 00:56 UTC; design v5 still unread)
- Matches the brief: English TRAIN bank `english_training_candidates_v3.json` sha256 f2f5cce3...; English CPU successor status SOURCE_READY_NATIVE_NOT_RUN (native qualification unrun, no native success claimed); partial benchmark mean control update 0.4134 s, no gain or generalisation claimed.
- The file's GPU hold text predates Ben's 11:59 decision to give Premonition the PC GPU full time; the design assumes the later decision.
- Still unverified: trainable parameter groups, loss placement across loops, optimizer and clipping settings, checkpoint pins. Those need v5 before sealing (section 10a).

## 1. What earlier work already tells us (all from the older small solver)

| finding | label | file |
|---|---|---|
| After a new kind (mazes), old kinds fell to 0 of 200; replaying 128 true old examples per kind recovered sums about 150, grids about 90 | shown | `design/research/standing/03-sleep-keeps-old-skills-without-heavy-replay.md`, `artifacts/claude-distill-20260928/RESULTS.md` |
| A store of 16 per kind collapsed every arm to 3-26 of 200 | shown | same |
| Matching the model's own earlier answers on the same stored items added only +4.5 / +9.75 of 200 (bar 20) | shown | `artifacts/claude-distill-20260928/RESULTS.md` |
| Short night (300 steps) gained +49 to +86 on day grids and lost 0 old-skill items in 24 cells; a night 20x longer at the same step size lost the grid gain (L-S -76 / -94 of 400) | shown, 2 seeds for the long night | `artifacts/claude-dir-h6-sleeplen-20260928/DESIGN.md` |
| Same-seed noise: about 10 on sums, about 20 on grids per 400; night-to-night SD about 11 | shown | same |
| Fresh generator-made rehearsal across 3 nights kept old skills (0 lost of 300) | shown, other reasoner | `scripts/claude_slp358n3_nights.py` as cited in `design/research/lead-sweep-2026-09-29/angle-5-sleep.md` |
| T1 (fresh questions), T2 (model picks its own replay), T3 (newer-weighted), H6 arm B (smaller steps) are sealed designs; I found no result files for them on main | untested | `artifacts/claude-dir-t{1,2,3}-*/`, `artifacts/claude-dir-h6-*/` |
| Nothing measures learning speed on a new kind after several nights (loss of plasticity) | untested | angle-5 note |

Lessons carried into the design (suggested): keep nights short and the step budget fixed; never use a night length as the thing being compared; keep a measured noise floor before fixing bars; compare on the same checkpoint in the same run; always have a plain-fine-tune row.

## 2. What counts as verified experience

An **experience** is one record: question, the model's full attempt (calculator calls, returns, final answer), a checker verdict, and, for failures, a checked correction. It enters the sleep store only if the verdict comes from a checker that meets all of these:

1. **Independent of the model.** It does not read the model's reasoning, and it is not the model or the frozen LM judging itself.
2. **Independent of the gold key at run time for live items.** A key-lookup (gold scoring) is allowed only on TRAIN items whose key was authored and checked before the run, and is labelled **V1-key**. For items whose answer is unknown at attempt time, the checker must verify the answer, not look it up (recompute with the calculator, execute a program against tests, check constraints, check a derivation step by step). Labelled **V2-check**.
3. **Frozen before the night.** Checker code and version hash are recorded; a night never mixes checker versions.
4. **Step-level where possible.** Calculator call and final answer are verified separately. The 71 of 86 correct-call-wrong-final-answer outputs seen earlier show these fail apart, so a record whose call is right and whose final is wrong is its own class, **tool-ok-answer-wrong**.

Classes of record, each with a fixed cap in the night mix (section 4):
- **A. accepted**: attempt passes its checker.
- **B. corrected**: attempt fails; the checker supplies the right result (calculator output or checked key); the stored target is the correct complete solution through the normal generation path, not copying inserted into the architecture.
- **C. partially accepted** (tool-ok-answer-wrong): kept as B, tagged, so it can be analysed alone.
- Rejected without a correction (checker cannot say what is right) are logged and never trained on.

What does not count: unchecked attempts, majority votes by the model, a teacher model's opinion, agreement between two samples of the model, any item from an evaluation panel, any consumed question. Sampling many candidates is not learning; only checked ones are stored.

Claim levels: V1-key results may be reported as "learning from checked TRAIN experience". Only V2-check results support "learns from live verified experience". The report must say which one each night used.

## 3. The day and the night

```
DAY    stream of new questions (kind K_d, plus a few older kinds)  ->  model attempts (frozen weights)  ->  checker  ->  experience log
NIGHT  experience log + earlier nights' verified store + anchor set ->  fixed mix  ->  short update  ->  new checkpoint
MORNING  fresh evaluation forms, sealed, one-use  ->  scores per kind  ->  next day uses the new checkpoint
```

- **What the night trains.** Only the parts already trainable in the pilot (reader, ~9M core, prefix generator), per v5 to be confirmed. The frozen LM stays frozen, the causal mask and loop count are untouched, no new heads. Gradients flow through the frozen LM into the prefixes exactly as in training today. This is training data and schedule, not an architecture change.
- **Step budget.** Small, fixed per night (suggested start: 256 updates at the pilot optimizer and a learning rate at or below the pilot's final rate; time per update about 0.41 s measured on the disposable benchmark, so a night is minutes of GPU, inferred). Decided in advance, identical across arms, never extended after seeing a result (earlier long-night loss, section 1).
- **Idle-only, stops cleanly.** The nightly job holds the same GPU lock as every other job and may not start while the execution owner's queue is running. Not specified further here.

## 4. Replay mix (fixed before any run)

Per night, fixed total examples U, fixed shares:

| share | source | why |
|---|---|---|
| 50% | the day's own experiences: class A and B in ratio at most 1:2 (failures are the new information), class C included inside B | learn the day |
| 30% | earlier nights' verified store, equal weight per earlier night (arm "uniform"); one-change variants later: newer-weighted 1:2:4, weakest-first | keep and transfer |
| 20% | anchor set: original curriculum (TRAIN English pilot items, calculator items) with their keys, fixed size | keeps the base behaviour from drifting through the model's own mistakes |

Rules:
- Dedup by exact input hash and by paraphrase family: a family contributes at most a set number of records per night (anti-memorisation, so repetition does not stand in for coverage).
- No record is trained on after its question has been used in any evaluation form (hash check at assembly).
- Replay targets are the stored correct solutions through normal generation. No copy-the-answer path, no extra reasoning depth, no auxiliary heads, no latent matching.
- Store growth: capped by a fixed budget per kind (the earlier 16-per-kind collapse is the warning, so the cap and the mix are results to be measured, not assumed). Fresh code-made items are allowed for kinds with generators and are labelled "generator replay: disclosed advantage, an upper bound for kinds without one".

## 5. Schedule across nights and kinds

5 nights, one new kind introduced per day, earlier kinds stay in the log and mix. Kinds are drawn from what the pilot and creative prototype can already check, in this order of preference (proposal, to be fixed with the pilot's real families): K1 an English comprehension family from the pilot; K2 a calculator word-problem family (independently checked, Luna-style); K3 a second English family; K4 a paraphrase or meaning-transfer family; K5 a kind with a code checker from the creative prototype. Each kind is introduced only after the **yield gate**: on a probe of the day's items, the model's accepted-plus-correctable rate must be in a usable band (suggested 10% to 90%); below 10% there is nothing verified to learn from, above 90% nothing to learn.

## 6. Controls (each differs from the sleep arm in one thing)

All arms start from the same parent and optimizer state, see the same questions each day, use the same night step budget and learning-rate schedule, run on two matched seeds, and are evaluated on the same forms in the same event.

| arm | what it is | what it isolates |
|---|---|---|
| **S** sleep | the design above | the thing under test |
| **F0** no sleep | frozen parent, same days, attempts logged, no update | baseline and evaluation noise |
| **PF** plain fine-tune | same budget, same day's verified experiences only, no earlier-night mix, no anchor | value of replay and retention mix |
| **PG** gold-label fine-tune (reference) | same prompts, authored gold solutions, same budget | does own verified experience come close to direct teaching; a ceiling, not a claim |
| **SU** sleep, unchecked | same mix but built from all attempts, accepted or not | value of the checker |
| later single changes | newer-weighted; weakest-first; failures capped differently; night length at fixed lr x steps | one at a time after S is shown |

The matching rule to avoid a false win: S and PF get the same number of updates and the same number of distinct training examples per night.

## 7. Evaluation

- **Fresh forms.** Each evaluation form is authored independently of the model, the checker and the replay data, reviewed by a second reader, numerics and word problems independently recomputed, hash-sealed before the run, and used once in one evaluation event (all arms and seeds together), then marked consumed. Using the sealing kit under `handoff/uncle-questions/` and Ben-supplied questions where Ben wants them. Reserved user and blind panels are never opened.
- **Per night d, forms for:** (a) the day's kind (learning), (b) each earlier kind (retention, parallel forms, not the items trained on), (c) one never-trained kind (transfer, introduced from the next day onward), (d) a general probe: ordinary English behaviour, calculator call format, output length and stopping (side effects), (e) a plasticity probe: a copy of the checkpoint learns a fixed new kind from a fixed small number of checked examples, and is scored on a fresh form (a learning-speed curve across nights).
- **Size.** Items per cell set from the measured noise (below). With only 48 questions across 6 families in the TRAIN qualification bank, per-night forms of that size cannot carry 5 nights; the fresh-form pool is a real cost to plan (about 5 nights x kinds so far, up to 15 retention forms plus transfer and plasticity forms). Ben supplies or approves the authoring budget.
- **Noise first.** Before any bar is used, run two identical repeats of the same arm on the same data (the repo's S-versus-S rerun) and set margin = max(floor, 2 x SE). The floor is a number frozen with the pilot's own noise, not copied from the older solver.
- **Leak check.** Automated hash and n-gram overlap between every evaluation form and every replay, anchor and attempt-log record. Any overlap voids that form for that arm.

## 8. Pass criteria (rules fixed now; numbers frozen after the noise run)

| id | criterion | needed |
|---|---|---|
| P0 | no leak, yield gate met, checkers frozen, arms matched | all, or the run is void |
| P1 learns | on the day's kind after night d, S beats F0 and PF by more than the margin | both seeds, nights 1-5 |
| P2 keeps | each earlier kind: S at least PF plus margin, and S not below F0 minus tolerance | both seeds, after night 5 |
| P3 transfers | on the never-trained kind, S beats F0 by more than the margin (or the pre-stated smaller bar) | both seeds |
| P4 improves with use | plasticity probe after night 5 not below the night-0 probe by more than the margin, and the night-by-night retention gap S minus PF is not shrinking | both seeds |
| P5 checker matters | S beats SU by more than the margin on at least the day's kind | both seeds |
| P6 no harm | general probe, call format and stopping within tolerance of F0 | both seeds |

Every-seed rule: a pass needs both seeds above margin; a fail on either seed is reported as a fail.

**Would prove it wrong:** S within noise of PF on earlier kinds on both seeds (replay is not doing the retaining); S within noise of SU (checking adds nothing, so the claim reduces to "more training on own attempts"); plasticity probe falling by more than the margin in both S and PF (many nights hurt learning, so the next single change is a plasticity fix); S below F0 on the general probe (night training harms base behaviour); PG far above S on every kind (own experience is a poor substitute for teaching at this size).

**What each result permits.** P1 alone: "the model improves on a kind from checked experience". P1+P2: "keeps earlier kinds better than plain fine-tuning". Adding P3 and P4: "improves with use across nights". None of these says the model understands, reasons, or generalises beyond the tested kinds; completing nights, fitting TRAIN experiences and generating data do not establish generalisation. Generator-replay results are an upper bound for kinds without a generator.

## 9. Rollout, one change at a time

| phase | what | gate to the next |
|---|---|---|
| 0 | CPU only: record schema, checker interfaces, mix assembler, leak checker, fixtures. No training claims | fixtures pass; v5 facts confirmed |
| 1 | noise repeats; one night, one kind: S vs F0 vs PF | P0, P1 |
| 2 | 3 nights, two kinds | P1, P2 |
| 3 | 5 nights, all kinds, transfer and plasticity probes | P1-P4, P6 |
| 4 | one-change ablations: SU, newer-weighted, weakest-first, night length at fixed lr x steps | each judged alone |
| 5 | repeat at the sizes chosen by the fair-scaling part; facts go to the notebook, so replay carries skills only | scaling comparison |

Compute and cost: none requested here. Phase 1 needs only what a pilot night needs on the PC GPU, which the execution owner controls. Any spend of 50 cents or more goes to Ben first.

## 10. Decisions (answered 2026-10-03 by the channel session under Ben's broad-autonomy message; none of these is Ben's explicit sign-off on this design)

1. Nightly training of the reader, core and prefix generator with the frozen LM untouched: approved as a training method.
2. Question-writing head: deferred.
3. Checkpoint blend toward yesterday, or a low-rank day piece: allowed later as a single-change arm without asking again.
4. Fresh evaluation forms: written by a separate authoring subagent, every item checked by a second independent subagent, numerics and word problems recomputed independently, forms sealed by hash before any run and excluded from all training data. Authoring is Opus-class work per Ben's architecture rule.
5. Reasoning depth: Ben removed the extra-depth and scaling approval rules (2026-10-03 12:09). The loop count may therefore be a night-time variable, but only as its own one-change arm (section 6 "later single changes"): same sleep recipe at a larger loop count, never changed together with the replay mix. The base design keeps 4 loops so that S, F0 and PF stay comparable with the pilot. Still off without approval unless Ben says otherwise: LM fine-tuning, causal-mask changes, forced answer copying, digit auxiliary heads, latent-matching objectives.

## 10a. Opus architecture review (read-only subagent, 2026-10-03; every point suggested or untested, v5 unread)

Method points to settle as "same as the pilot" before sealing (the "not an architecture change" claim in section 3 holds only if they are):
- **Loss placement.** Which loops get the loss and whether gradients run through all 4 loops: copy the pilot exactly.
- **Day decoding equals evaluation decoding.** No best-of-N at answer time; sampling many candidates is for logging only, and only checked ones are stored.
- **Who writes class B steps.** The checker supplies a result, not steps. Targets are built by a fixed, pre-registered rule (the model's own attempt with the checked result substituted at the failing point, or a checked reference solution from the authoring pipeline), never a teacher's free text. Open.
- **Class C and forced copying.** Training "tool right, answer wrong" records on a target whose final equals the calculator return teaches copying through the data, not the architecture. Treated as an ablation arm (C included vs excluded) until Ben says it is not the forbidden forced answer copying. Open question to Ben.
- **Optimizer state.** One choice (reset with a short warmup, or carry over), applied identically in S, PF, SU and PG, saved with each checkpoint.

Guards added to every night's log, with stop thresholds fixed before the run:
- Prefix drift on a fixed anchor set: prefix norm, cosine similarity to the parent's prefixes, and KL of the frozen LM's next-token predictions against the parent's. The prefix is the only channel into the LM, so drift can degrade everything at once.
- Per-loop latent norm and step-to-step change; keep the pilot's gradient clipping.
- Cap on repeats per record, matched between S and PF.
- Per-kind anchor-set scores to catch reader drift.

## 11. Risks

- Self-training can reinforce its own mistakes; the anchor share and checker independence are the guards, and SU measures the effect.
- Checker coverage bias: kinds that are easy to verify get replayed more. Log the share per kind.
- Checker gaming or leakage of keys into attempts. Keys stay outside the attempt path.
- Small store collapse (shown on the old solver at 16 per kind): cap and mix are measured.
- Plasticity loss over nights: probed, not assumed.
- Evaluation pool cost is large relative to the 48-question bank; the authoring and checking subagents carry it.
- All numeric starting values (256 updates, shares, yield band) are guesses from the older solver and are replaced by the noise run and v5 facts.

## 12. Plain-language summary for Ben

Each day the model tries problems. A checker that does not trust the model marks the attempts, and fixes the wrong ones with the right answer. At night the model trains briefly on the day's checked work, mixed with older checked work and a little of the original lessons, so new learning does not push out old learning. We then test with brand-new questions nobody has trained on. To believe it works, the sleeping model must beat a model that never sleeps and a model that just trains on the same day's work with no mixing, on both seeds, over five nights, while still learning a new kind quickly and not getting worse at ordinary English. Earlier sleep tests on a smaller solver warn us: short nights worked, long nights hurt, a tiny memory forgot everything, and nobody has yet measured whether it still learns well after many nights.

## 13. Reconciled with integrated design v5 (the .docx under `DESIGN-WORKING-v6/` on branch claude/premonition-launch-recovery-96c708, commit c5cfd9176)

Agrees with v5: verified experience needs a trusted correction or an independently checked outcome per target; consumed evaluation panels and answers never enter positive replay; a check that reads an evaluation question's gold answer is not answer-hidden; balanced replay against new-only learning is the first comparison (my S vs PF); learned selectors, interference-aware selection and schedulers come later; facts stay in the notebook and superseded facts are never replayed as current truth; lower training loss or better recall of replayed answers is not a pass; a gain must survive context reset and intervening learning; a gain only on replayed instances is memorization evidence; feedback used to choose updates is selection information, not final evidence. Trainable parameters are about 9.0M of 9.0M total for the reasoner (v5 table), so "reader, core, prefix" is the whole learned part.

**Conflicts and changes needed (made here):**
1. **Order.** v5 puts context reuse first, then a small adapter with the core frozen, then replay into a candidate core, and says the proposed adapter, scheduler and consolidation changes "await approval". My design jumps to weight updates of the core. Resolution: sleep replay here is the third stage and only starts after the context-reuse and adapter stages exist; the channel session's approval of nightly weight training is recorded in section 10 and Ben then confirmed v5's consolidation approval himself (2026-10-03 13:35 UTC, "ok say yes to v5", answering the coordinator's question naming nightly weight changes by sleep replay). The v5 order still holds: this stage runs third. Phase 0-1 (CPU plumbing, noise run) do not depend on it.
2. **Versioned pair.** If an adapter exists, a core update must revalidate, replace or reset it, and the previous compatible core-adapter pair, experiences and training manifest are kept for rollback. Added as a requirement on every night's promotion: a night produces a candidate, promoted only after P1-P6; otherwise rolled back.
3. **What a record establishes.** A calculator validates executed arithmetic, not that the operation fits the problem, and a correct final number does not validate its explanation. So class A/B targets are the call plus final answer only; free-text explanation is never marked verified. Records must store problem, action, result, evidence versions and checking method.
4. **Reset test.** Add to P2/P3: after a context reset and after intervening nights, the gain must remain.
5. **Retained-output and unresolved items.** Unresolved examples (no trusted feedback) are retained but never trained on, as in section 2. Known mistakes are never distilled: the anchor share may not include the model's own failed outputs.
6. **Nine correct-call trials all ended in wrong final answers (v5).** v5 treats this as diagnosis, not a proven copying repair, and notes that expected values were absent from the training-answer targets. This supports keeping class C as an ablation arm, not a default, as in section 10a.
7. **Depth.** v5 describes a completed depth comparison between 8 experts x 8 visits and a 16-block shared stack reused over 4 loops (about 9.0M vs 8.6M parameters). Which core a night trains is whichever the pilot adopts; the design does not assume either.
8. **Loss placement, optimizer, clipping, checkpoint pins**: still not found in v5; they must be copied from the pilot before sealing.
