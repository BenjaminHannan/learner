# Premonition v3 — decisions and authority

**Suggested — decision.** Build two separate research systems: a bounded iterative lookup controller on the card toy, and a parser-assisted persistent mini-village. Promote only changes that survive their matched controls. The minimum implementable v3 contracts are fixed below; their learning efficacy is not established.

**Shown — evidence vocabulary.** `Shown` means inspected source, saved output or explicit arithmetic in that setup; `suggested` means interpretation or design judgment; `untested` means a proposed behavior or absent measurement. Literature `established` is limited to the cited work; `your inference` marks transfer to this project. In all v3 documents, normative requirements, pseudocode, shape choices, thresholds and expected timings inside an **Untested — specification** section inherit that label unless a narrower label is given. They are requirements to build, not claims that existing code already implements them.

**Shown — navigation.** [Evidence audit](../../reviews/astra-design-2026-09-19/evidence-audit.md), [generated toy table](../../reviews/astra-design-2026-09-19/toy-results.md), [Track A](01-track-a-lookup.md), [Track B](02-track-b-mini-village.md), [evaluation](03-evaluation.md), [six-experiment decision trees](04-sequence.md), [red team](05-red-team.md), [plain-language summary](06-for-ben.md), [literature](../../reviews/astra-design-2026-09-19/literature.md). Reviewer prompts are in the review directory. No historical file is changed by this design.

## Decisions from the walkthrough

| ID | Disposition | Decision, evidence and label |
|---|---|---|
| D01 | Accept | **Suggested:** dependable fresh-world two-hop use is the milestone. **Shown:** original 50% held-out gate is only a screen. Use causal pairs and all-seed reporting. |
| D02 | Amend | **Shown:** addressing help is assay-specific. **Suggested:** reject the common-cause story as a conclusion; retain it as an **untested** sharing hypothesis. |
| D03 | Accept | **Shown:** detached hard top-k and ASK threshold block direct answer credit through choices. **Suggested:** disclose answer and evidence supervision separately; both are legitimate. |
| D04 | Accept | **Suggested:** delayed search supervision is a plausible stuck-run cause; **untested** until the pending phase-order comparison survives matched hardware/budget confirmation. |
| D05 | Accept | **Untested:** preserve fetched token states and token IDs as separate immutable evidence, with who/relation selection conditioned on state. **Suggested:** this gives selectable locations, not guaranteed role learning. |
| D06 | Amend | **Suggested:** pooled vectors can encode roles; “cannot offer the object” is too strong. **Untested:** the equal-parameter pooled-row selector arm tests whether token locations are needed here. |
| D07 | Accept | **Untested:** ASK/HALT use control register 0; request selectors use register 1; answer addressing uses register 2. No gold role masks in learned arms. |
| D08 | Amend | **Untested:** target implementation deletes the binder and global loop-step embedding, but neither deletion accompanies the first pointer comparison. Independent necessity/rollback contrasts must earn deletion. Keep compatibility flags and inactive state keys. Arrival/followed flags are based only on observable execution. |
| D09 | Accept | **Untested:** baseline, supplied-relation shortcut, pointer and pooled-row falsifier are defined. Shortcut is a privileged reference, not a mathematical upper bound. Semantic relation position, not `q_end-2`, defines its supplied privilege on new arrangements. |
| D10 | Accept | **Untested:** first/second person and relation selection, key match, answer-card choice and final answer are distinct metrics. Train on several distinguishable layouts; hold out complete arrangements. |
| D11 | Accept | **Untested:** address-select one fetched card before copying; abstention is always available, independent of NULL fetching. Distractor, owner, relation, value and version swaps are mandatory. Clean gold reads are only a reading ceiling. |
| D12 | Amend | **Suggested:** differentiable credit first, reward later. **Shown:** existing ST adds value gradients too. Preserve its registered result; a score-only ST follow-up isolates that explanation. Soft access is charged as access to the whole eligible store. |
| D13 | Reject as named; replace | **Shown:** teacher gold insertions are an evidence channel. A `{all evidence labels off} × {gold teacher assistance on}` cell is contradictory. **Untested:** use direct ASK losses on/off × gold insertions on/off, with gold-based answer weights/counts off throughout. Only the off/off cell is evidence-label-free. |
| D14 | Accept | **Untested:** separate answer timing, ordered teacher insertion, ordered ASK target and LM weight. Do not bundle them with pointer introduction. Their exact contracts are in Track A; six slots limit how many can be attempted next. |
| D15 | Accept | **Untested:** separate key pooling, search supervision from the first empty workspace, and subject-propagation auxiliary loss remain alternative stuck remedies. Check intermediate representation/retrieval curves. A temporal lead does not alone establish cause. |
| D16 | Amend | **Untested:** competence gates use a dedicated development set and a fixed compute cap, never certification data. Label them evidence assistance if they consult evidence. Failure to qualify is a failed run. Fully-own finishing is a separate non-inferiority comparison after recovery is defined. |
| D17 | Accept | **Untested:** expose score, margin, repeat attempts and occupancy; introduce missing evidence, variable useful depth and failed searches before claiming failure awareness. No reward for endlessly asking. |
| D18 | Accept | **Untested:** intervene on the same trained model's full factual paths, including contextual questions, slots and caches, then restore. A separately trained no-store model is a separate capacity control. |
| D19 | Accept conditionally | **Untested:** if path probes show question-state leakage, use a story-blind question encoder shared across both compared arms. Cost: questions cannot resolve pronouns or omitted context; those tasks wait for an explicit reference mechanism. |
| D20 | Accept | **Suggested:** call Think a bounded iterative lookup controller. **Untested:** extra thinking earns a stronger name only on evidence-combination and variable-depth tasks with retrieval and FLOPs independently controlled. |
| D21 | Accept with target correction | **Untested:** checker predicts free-running answer correctness; stopper predicts expected benefit of continuing from present state only. Full bounded rollouts, no compute penalty, ties stop early; censored horizons cannot prove no future gain. Latent loops first; decoded traces are inspection data. |
| D22 | Accept | **Untested:** start the persistent mini-village alongside Track A with fixed wording, repeated visits, corrections and historical queries. Parser-assisted results claim store/version behavior, not learned language understanding. |
| D23 | Accept | **Untested:** persistent identity comes from visible introductions and explicit alias evidence, scoped by world. Working tags can change; identity cannot silently change with them. Learned embeddings only rank candidates. |
| D24 | Accept | **Untested:** `(world, entity, relation, qualifiers)` excludes value; assertions carry value, source, valid time, observed time and version. Events and multi-valued facts have separate qualifiers. |
| D25 | Amend | **Untested:** a true state change and a retrospective correction are different operations. “Newest wins” is restricted to valid-time applicability and declared authority; equal-authority contradictions abstain unless an explicit supersession resolves them. |
| D26 | Accept | **Untested:** known corrections immediately veto stale weight answers. Repair of weights is later, separately scored. A missing neural candidate cannot bypass exact correction guards. |
| D27 | Accept | **Untested:** frozen retriever initially; replacement trained separately, all retained records re-indexed, validated, and encoder/index swapped atomically. No mixed or lazy versions. |
| D28 | Accept | **Untested:** extraction is distinct from retention; parser returns zero/one/many facts and explicit unresolved references. FIFO/LRU/reservoir face actual pressure with the same protected correction reserve. Surprise is deferred. |
| D29 | Accept with scope | **Untested:** version correctness precedes online-only training, fair replay, then one additional mechanism: cached-logit distillation. **Suggested:** call it a retention/consolidation candidate, not proof of a special sleep faculty; replay itself can teach facts into weights. |
| D30 | Accept | **Untested:** compare cards and weights with full path isolation, matched resource accounts and targeted versus equal-size control lesions; repair, consolidation, practice and maintenance are distinct experiments. |
| D31 | Accept | **Shown:** 262,144×128=33,554,432 value parameters before routing/core/optimizer. **Untested:** defer PKM; specify a 256-slot pilot only after replay baselines pass. Separate value, routing and core drift. |
| D32 | Amend | **Untested:** diary identity includes generator code, pattern bank, config, random streams and ranges, action history, external inputs and exact-byte hashes. Regeneration is charged. A simulator seed must not let replay reconstruct never-observed hidden facts. |
| D33 | Accept | **Untested:** early health gauges, with fresh-task adaptation only on disposable copies. No maintenance intervention just because a gauge looks unusual. |
| D34 | Accept | **Untested:** paired worlds, question-only, evidence removal and irrelevant changes precede village verdicts. Chance is per answer type and sampling design, not a universal 1/16. Fixed wording first; unseen wording and name substitutions are independent axes. |
| D35 | Accept | **Untested:** bridge through the village generator one difficulty at a time, retaining earlier tests; single-card multi-token copying is separate from two-card composition. |
| D36 | Accept | **Untested:** generated results, exact gate definitions, explicit privilege columns, matched-budget curves and independent data streams for reliability. Source-detected identities and parsed fields are privileges too. |
| D37 | Amend | **Shown:** 36/40 is a screen; 77/80 yields a 90.593% exact one-sided lower bound. **Untested:** certify only a frozen recipe, fixed gate and fresh seed/data distribution. Do not label this 95% reliability. |
| D38 | Accept | **Suggested:** leave paused work paused; read completed reporting/probes, interpret the soft screen, resolve the first active confound, then add the smallest useful mechanism. Track B starts independently. No duplicate pending experiments. |

## Additional decisions

| ID | Disposition | Decision and reason |
|---|---|---|
| D39 | Add | **Untested:** manifest-complete results outrank DONE files; record failures, missing jobs, actual updates, calibration and evaluation time. Failed runs stay in denominators. |
| D40 | Add | **Untested:** explicitly budget token rows, soft candidate access, decoder companions, metadata, protected tombstones and temporary re-index buffers. An unchanged parameter count is not unchanged computation or information. |
| D41 | Add | **Untested:** bounded stores must fail visibly when protected metadata fills. Do not silently resurrect a stale answer or borrow an unlimited diary. |
| D42 | Add | **Untested:** strict copy heads need finite, differentiable training loss when the correct token is absent. The soft companion and smoothing contract in Track A prevents an infinite-loss dead end. |
| D43 | Add | **Untested:** no hidden gold scheduling, future timestamps, loss-dependent early exit, simulator IDs, or answer-bearing metadata may enter inference. Hash every input contract. |
| D44 | Add | **Suggested:** within a six-comparison sequence, omitted confounds remain explicitly untested. Do not hide a factorial grid or simultaneous deletions inside one experiment name. |
| D45 | Add | **Untested:** aliases, ambiguity, future-effective facts, equal-authority conflict, metadata overflow, duplicate updates and transaction replay are specified before implementation. |

## Exact supersession map

**Suggested — document authority.** v3 governs new work only; historical run definitions retain their original meaning.

| Prior location | Replacement |
|---|---|
| `04-architecture.md` “One picture”, parts 3–5 and build steps 2b/3a | Track B starts small with explicit version logic and frozen retrieval; no required large PKM, EMA retriever or automatic scale ladder. |
| `04-architecture.md` parts 5, 8, 11 | Identity ≠ embedding; change ≠ correction; exact temporal/authority rules, bounded protected metadata and full diary contract replace newest-wins, surprise priority and seed-only regeneration. |
| `04-architecture.md` parts 6–7, 10, build steps 5–6 | Latent bounded lookup; independent checker/stopper targets; separated sleep jobs; replay-first and controlled lesions. |
| `04-architecture.md` part 1 / build step 1 | Fixed wording is the next diagnostic milestone; whole-structure language holdouts remain a later, separately named generalisation claim. |
| `06-premonition-mini-spec.md` §§1–3 | Track A's optional token-row/request/copy modules, explicit workspace caps and supervision ledger replace the mandatory pooled-card/binder/step design and implicit NULL abstention. Legacy mode is preserved. |
| `06-premonition-mini-spec.md` §2 identity/store | Episode tags remain valid for the toy; persistent identity and versioning come only from Track B. |
| `06-premonition-mini-spec.md` §§4–8 and §§9–10 contender schedule | v3 evaluation and six-slot conditional sequences replace the large contender catalogue, nominal-step matching and three-seed finalist rule. |
| `06-premonition-mini-spec.md` §11 | Preserve label-free preprocessing, tokenizer/checkpoint identity checks and fail-closed primary admission. Extend them to v3 metadata and persistent state. No legacy village score is promoted. |

## Genuinely open, with one closing observation each

**Untested — research questions, not implementation ambiguities.**

| Open question | Single observation that decides the next action |
|---|---|
| Is the factual answer path actually store-dependent? | Pending full five-condition same-checkpoint intervention, with exact restoration. |
| Does key pooling or early search reduce stalls? | Complete predeclared roster and matched-budget per-seed gates from the owned waves; cross-hardware gold-zero remains screen evidence until replicated. |
| Does a useful answer-only retrieval route exist here? | Hard-read causal performance from a fully-own, all-evidence-channels-off arm with a verified gradient route. |
| Do token locations add usable object information? | Equal-budget token-row versus pooled-row selector contrast on changed-link pairs. |
| Does sharing help? | Tie only request-selector weights in an otherwise identical successful system; compare at the fixed gate and budget. |
| Can replay already solve persistence? | Cards-hidden retention curve for fair time-labelled replay versus online-only at equal total FLOPs. |
| Does distillation earn its cost? | Distillation minus the strongest eligible replay control at equal storage, information access and total compute. |
| Can the proposed waves fit the cap? | Full-load rehearsal including serialization/evaluation on a subsequently available authorized host; smoke speed is insufficient. |

**Suggested — preferred next measurement.** The already-owned path intervention has the highest decision value. If both cards and contextual question paths can be removed with little effect, redesigning the card request head is the wrong immediate priority. Reading alone cannot close these empirical questions.
