# 25 — GPT-6 Pro's answer to the eight-problem prompt (outside review, verbatim)

**Not a Fable or Astra document.** Pasted by Ben on 20 September 2026 from a ChatGPT (GPT-6 Pro) chat that had no repo access and one response. Saved verbatim by Fable (coordinator); nothing here is a ruling or a registration until adjudicated. It was written without knowledge of the 19b result, the M0/M1 builds or the talker decision.

---

Ben,

Below is the full research-design response I sent in ChatGPT.

## 1. Why counting wins

Yes: reg+ctx can represent the desired controller over the tested length range; the three-call ceiling is a learned shortcut, not an unavoidable consequence of STOP reading the GRU state.

I interpret “strict” as the correct sequence of executed subject-token/operation-token pairs, followed by an explicit model-chosen STOP. Two pointers to indistinguishable copies of the same person token are equivalent under that definition. Exact pointer-index correctness is a different—and sometimes impossible—requirement, discussed below.

All probabilities I give are subjective forecasts fixed before these proposed experiments, not measured success rates.

### Where the necessary information exists

| Signal | What it can represent | What can go wrong |
|---|---|---|
| Bidirectional question vectors c_i | Position relative to the beginning, proximity to the final relation, and distinctions between otherwise identical LINK positions. | Recurrent encodings can become nearly indistinguishable beyond trained distances. |
| Selected-operation position vector | The identity of the question position just used, rather than merely “I used LINK.” | The state update can ignore this information or encode it only for familiar positions. |
| Selected-subject position vector | Which question/transcript candidate was selected, to the extent those candidates have distinct vectors. | Identical transcript slots remain indistinguishable if their keys contain only identical token embeddings. |
| Register r | The current person, a cursor representation, or both. | Its learned gate can overwrite useful information, retain stale information, or become another counter. |
| GRU state h | Cursor, current-person information, execution history, and a done bit. | A small finite-horizon clock can explain all rewarded training trajectories. |
| Last operation/result embeddings | LINK versus attribute; person versus value. | The state must preserve their significance for STOP rather than burying it in other updates. |

The important correction is: STOP is not information-starved. Its state has received the result token. It can learn a done bit from that token, from the operation token, or from both.

There is also an important qualification to “result type is a perfect done-signal”: it is perfect on a valid execution prefix. An incorrect early attribute lookup also returns a value. Stopping after that value is locally sensible, but the preceding operation choice was wrong.

### A constructive representability argument

An existence construction needs only three ingredients.

First, let the question encoder represent position using two approximately rotating coordinates. For example, successive positions can have coordinates proportional to:

c_i = (cos(iθ), sin(iθ)), θ = 2π/64.

A recurrent cell can approximate that shared rotation over the relevant finite range; this does not require a separately learned parameter for every index. Store the selected position’s coordinates. A query obtained by rotating them once more has its largest dot product with the next position’s coordinates.

Second, store a representation of the current person in the register. Select any candidate carrying that person token. The next operator result replaces the current-person representation.

Third, write a done bit into the state when the selected operation is an attribute relation—or, on valid prefixes, when the result is a value—and let STOP read that bit.

The register and 32-dimensional state have ample representational room for these finite-range functions. This is an existence argument, not a recommendation to install hand-authored positional coordinates.

Two limits matter:

• Unbounded length: this does not establish reliable operation at arbitrarily large lengths. Finite-precision recurrent position encodings eventually collide or lose usable separation.
• Exact newest-slot indices: if two transcript slots have identical keys, every query assigns them identical scores. A register containing the person’s identity cannot identify which identical copy is newest. If the existing strict metric demands the newest slot’s particular index, that requirement is unrepresentable without an additional slot-distinguishing signal. Report semantic trace correctness and exact-index correctness separately.

### Why the shortcut is attractive

The training distribution admits both of these rules:

Stop when the final attribute has been read.

and

Stop on familiar short endings; otherwise stop by call three.

They agree on every correct training trajectory. Training contains no correct example of taking a third LINK and then continuing.

Thus, counting is not necessarily a better optimum on the training distribution. It is an easier way for this particular optimization process to reach a good training solution.

The causal chain I would investigate is:

1. Recurrent dynamics acquire a rough execution-age signal.
2. Every successful three-call training trajectory ends at that age.
3. Continuing after a correct short answer usually incurs extra cost and often destroys the correct final answer.
4. Terminal REINFORCE credit reinforces the successful short trajectory without specifying which internal representation made it successful.
5. Once stopping becomes confident, trajectories that could challenge that representation become rare.
6. Entropy annealing reduces the remaining opportunity to leave that solution.

The per-call penalty therefore discourages exploratory survival; it does not, by itself, prove that counting must beat a content-based stopping rule.

The two handed v3 features change this optimization problem substantially. “Most recent result” supplies the current subject without learning an identity-preserving memory update. Relative offsets make “next operation” a local, stationary relation rather than a recurrent extrapolation problem. They make the desired procedure easier to discover.

But v3-repro shows that they do not guarantee its discovery. “The features escape the shortcut” should be replaced with “the features made successful discovery possible in the original runs.”

### Two checkpoint-only predictions

1. Premature stopping after a correct prefix: on k=4 questions, replay three correct LINK calls and then inspect the unforced STOP probability. I predict p(STOP) ≥ 0.9 on at least 59/64 cases in at least two of the three reg+ctx checkpoints. Probability: 0.65. Failure of this prediction moves suspicion toward premature attribute selection rather than an independently faulty STOP decision.

2. Execution-age intervention: in matched self-loop worlds, replace the pre-update state at the third LINK with a state from after the first LINK, while holding the current token and selected-position inputs fixed. I predict a reduction in STOP probability of at least 0.5 on a majority of cases in at least two checkpoints. Probability: 0.60. A much larger effect from position-vector replacement than from state-age replacement would instead favor encoder saturation.

### Rival explanations

“The controller cannot know that it is done.” This loses because both operation identity and result type enter the state update. The problem can be learning to preserve or use the signal, not its absence.

“The register needs more dimensions.” This loses as the first explanation because the required finite-range state is small, and v3 succeeds with modest machinery. Extra width could improve optimization, but the evidence does not identify insufficient storage capacity.

“The call cost mathematically makes three calls optimal.” This loses because correct stopping is equally economical on the training distribution. The cost helps stabilize a shortcut; it does not uniquely select that shortcut.

Most likely way this account is wrong: the third operation is already an incorrect attribute lookup, and STOP is correctly responding to its value result. I assign 0.30 probability to that being the dominant explanation rather than an independently learned stopping ceiling.

Self-grade: SOLVED for finite-range representability and a falsifiable causal account; the proposed mechanism is not yet experimentally established.

## 2. Diagnostics

Four no-training probe families can localize the failure, but no probe on these fixed checkpoints can distinguish an internal counter from a counter learned specifically because of the old training cap when both implement the same function.

That last distinction is an identification limit, not a lack of diagnostic ingenuity. The cap is not among the stated network inputs. A checkpoint implementing “stop at three” contains no observable label saying whether three meant “largest rewarded depth” or “training cap minus one.”

The hypotheses also need not be exclusive. Saturated positions can cause pointer errors, and those pointer errors can trigger a result-type-based STOP.

### Fixed probe panel

Use the three original reg+ctx awake checkpoints, seeds 0, 1, 2. Generate a diagnostic panel with seed 21000:

• k in {3,4,5,8}.
• Final relations 8 and 10.
• 64 questions per cell: 512 questions total.
• Sixteen-person worlds.
• A separate set of 64 self-loop worlds, seed 21001, for identical-token history interventions.

Log complete pointer distributions, selected tokens and indices, register states, GRU states, position vectors, STOP logits, and whether termination was voluntary or caused by the evaluator.

Forced actions below are diagnostic interventions only. They never count as autonomous successes.

### The four probe families

P1 — Gold-prefix replay plus cap audit.
Run freely and identify the first incorrect call or premature STOP. Then replay each correct prefix while ignoring STOP only to reach the diagnostic state. Inspect the native STOP probability and next-pointer distributions. Repeat with evaluator caps 4, 8, 16, comparing identical prefixes before any cap is reached.

P2 — Cross operation and result type.
At correct-prefix states after calls 2, 3, 4, 6, hold the pre-update state and selected-position vectors fixed. Independently substitute:

• operation embedding: LINK versus an attribute;
• result embedding: person versus value.

This produces a 2 × 2 intervention. Use all three attribute embeddings and matched token substitutions. Contradictory combinations are artificial, so interpret them as circuit interventions, not as valid task examples.

P3 — Execution age versus current evidence.
In self-loop worlds, repeatedly feed identical LINK/person token inputs and identical selected-position vectors, inspecting STOP after 1 through 8 updates. Separately transplant first-call versus third-call pre-update states while holding the next update’s inputs fixed.

P4 — Position separation and causal position patches.
Measure adjacent LINK-vector separation at trained and untrained distances. Also measure the actual pointer-score margins; small Euclidean differences alone are not a diagnosis.

Flag numerical saturation when both:

• median long-range adjacent-vector separation is ≤10% of its trained-range counterpart; and
• relevant next-position logit margins are ≤0.01.

Then replace, one channel at a time, the selected-position feedback or candidate-position keys with corresponding vectors from a short question having the same local tail. A causal rescue means a ≥0.5 change in the relevant STOP probability or a switch from incorrect to correct next-operation preference on ≥48/64 cases.

### Predicted signatures

The signatures below are conditional predictions under a dominant, relatively pure version of each hypothesis. I assign 0.80 probability to each qualitative signature, except the cap-input invariance, which follows deterministically from the stated wiring.

| Probe | A: internal counter | B: saturated position vectors | C: pointer error mistaken for STOP error | D: STOP keyed to result type | E: learned training-cap prior |
|---|---|---|---|---|---|
| P1: correct-prefix replay | Premature STOP survives a correct third LINK. | Failure can survive replay if the state still receives collapsed position information. | Premature STOP disappears, or the first failure is clearly an early attribute/wrong subject. | Correct LINK/person prefixes continue; an early attribute/value explains free-run stopping. | Same signature as A if the prior is implemented by a counter. |
| P1: change evaluator cap | Identical logits before censoring. | Identical logits before censoring. | Identical logits before censoring. | Identical logits before censoring. | A historical prior stays unchanged; a real runtime-cap input would shift behavior. |
| P2: operation/result cross | Small effect compared with execution age. | Small effect unless type information also contributes. | Shows whether the incorrect pointer created the decisive terminal-looking token. | Large, consistent type effect; the crossed conditions distinguish operation type from result type. | Small effect for a pure cap counter; mixed policies can also use type. |
| P3: identical-input repetition/state-age swap | STOP rises with repetition; a younger state delays it. | No necessary fixed-age transition when position evidence is held constant; position patches matter more. | Gold replay need not show the free-run stopping transition. | Repeated person results do not acquire a new stopping meaning merely through age. | Indistinguishable from A when implemented as the same counter. |
| P4: geometry plus causal patch | Position geometry can remain usable while stopping remains age-dependent. | Collapsed functional margins and a substantial rescue from position patches. | Identifies whether position failure is upstream of the wrong pointer. | Type response survives position patches. | Same as A unless the cap prior itself uses position cues. |

### Pairwise separation table

| Pair | What separates it |
|---|---|
| A versus B | P3 state-age intervention versus P4 position intervention. |
| A versus C | P1: does premature STOP remain after a correct prefix? |
| A versus D | P2 type crossing, supported by P3 identical-person repetition. |
| A versus E | Not identifiable from the existing checkpoints when E is implemented by A. |
| B versus C | P1 locates the wrong pointer; P4 tests whether collapsed positions cause it. Both can be true. |
| B versus D | P4 position intervention versus P2 type intervention. |
| B versus E | Position-dependent versus age-dependent intervention effects, unless the cap prior uses position cues. |
| C versus D | P1 plus P2 distinguishes the wrong call from the stopping response it causes. Both can be true. |
| C versus E | Correct-prefix replay removes pointer-caused failure but not an independently retained cap prior. |
| D versus E | P2 and P3 distinguish type sensitivity from age sensitivity in their pure forms. |

### What each outcome changes

If correct-prefix STOP is already right on ≥61/64 cases in every seed, and free-run failure begins with a wrong pointer, do not describe the problem as a STOP-head failure.

If position patches rescue behavior, prioritize positional addressing. If a repeated identical input produces the same sharp third-update transition, prioritize clock dependence. If correct prefixes work and type crossing explains free-run stopping, the stop decision is downstream of a planning error.

For the unidentifiable cap-versus-depth distinction, the smallest useful additional training design is:

| Arm | Practised lengths | Cap |
|---|---:|---:|
| A | 1–3 | 4 |
| B | 1–3 | 8 |
| C | 1–5 | 8 |

Use seeds 2300, 2301, 2302, 6,000 updates per arm, unchanged costs and other settings. A versus B changes only the cap; B versus C changes only practised lengths. That examines causal sensitivity to training history rather than trying to read history out of fixed weights.

### Rival designs

Training a linear probe on the hidden state loses because it violates the no-training requirement and establishes decodability rather than causal use.

Only forcing continuation loses because continuing after the wrong attribute lookup does not repair the earlier pointer error. It can make an already-invalid trajectory longer without diagnosing anything.

Only plotting attention or vector similarity loses because apparent saturation can be harmless if downstream weights amplify the remaining differences.

Most likely failure of this diagnostic package: artificial state/vector combinations create misleading effects outside the model’s familiar state distribution. Probability: 0.25. Require agreement between free-run fault localization and at least one intervention.

Self-grade: PARTIAL. The existing-checkpoint bar cannot separate A from an observationally identical E. Closing the causal question requires the cap/length interventions above; no additional fixed-checkpoint probe can recover an otherwise unobservable training-history explanation.

## 3. The one fix

My single chosen change is to replace the state-only STOP head with a learned, stateless head that reads only the raw last-operation and last-result embeddings, thereby removing execution age from the stopping decision.

Specifically, replace:

p_stop = sigmoid(w_h^T h_t + b)

with:

p_stop = sigmoid(w_o^T e(o_t) + w_y^T e(y_t) + b).

Do not concatenate the state as well. That would preserve the counter route.

Use context-free embeddings from the frozen operator, not contextual position vectors or result-slot states. Assuming embedding width 48, the new head has 97 parameters, replacing 33, for a net increase of 64. If the actual embedding width is d, the increase is 2d−32.

This is learned stopping, not a programmed “attribute means stop” rule. The learner still chooses the subject, operation and STOP bit. A generic executor runs until the learner stops or a safety cap is reached; it does not traverse the question on the learner’s behalf.

### Why this one

The existing task provides an unusually strong, length-independent local stopping cue. The current architecture forces that cue through a state also responsible for other work. The replacement makes the cue directly usable and makes an internal stopping clock impossible in this head.

It does not make the whole controller incapable of counting. The operation pointer can still choose the final relation after three calls. That is the principal risk.

P2 can veto the experiment as a proposed treatment: if STOP is already correct on gold prefixes in all seeds, this is not the observed defect. A veto means “not run for this diagnosis,” not permission to quietly substitute a different fix under the same registration.

### Which other proposals are honest?

| Proposal | Status under Ben’s rule | Why I do not choose it first |
|---|---|---|
| Self-written consumed mask | Honest if it records the learner’s actual selections. Not honest if code marks gold positions or forces exhaustion before STOP. | Useful for addressing, but it does not itself prevent premature attribute selection or stopping; more memory/interface changes are needed. |
| Direct learned STOP inputs | Honest. A hard-coded type-to-STOP rule would not be. | Chosen: smallest removal of a plausible shortcut. |
| Prefix credit | Honest if the learner receives only scalar outcome feedback, not target actions or intermediate target tokens. Must be disclosed as dense intermediate supervision. | It changes the learning signal and still leaves the finite-horizon shortcut available. Exposing longer prefix questions also counts as practising those lengths. |
| Hindsight relabelling | Honest with correct on-policy resampling or a justified off-policy estimator. | Reusing old REINFORCE trajectories after changing the question is biased; relabelling three-call truncations can reinforce the three-call ceiling. |
| Recursion | Honest if CALL, RETURN and tail selection are learned. | A host function that strips one LINK and recursively calls itself has already supplied the solving loop. A genuinely learned recursive interface is a larger experiment. |
| Random caps/costs | Honest without revealing a remaining-step count. | With only k≤3, changing the cap does not create a legitimate fourth step. It may improve exploration, but it does not remove the ambiguity. |
| Mixture versus temporal curriculum | Both honest. | A good separate optimization experiment, not a substitute for a missing stopping invariant. Temporal curricula also require explicit retention checks. |

### Registration

Arms. A is reg+ctx with state-only STOP. B differs only by the stateless STOP input described above.

Initialization and randomness. Use initialization seeds 3100, 3101, 3102, giving six runs. Shared parameters start bit-identically within each pair. Initialize both STOP heads to zero weights and zero bias, so both initially choose STOP with probability 0.5. This is a matched comparison, not an exact reproduction of the legacy initialization.

Use separate, paired streams for worlds, question selection and rollout sampling: 3200–3202, 3300–3302, and 3400–3402, respectively. Index rollout randomness by update, question, rollout and step so a shorter trajectory does not change later training-world draws.

Training:

• 6,000 updates per run.
• 16 worlds × 4 questions × 16 rollouts per update.
• Six-person worlds; k uniform on 1, 2, 3.
• Relation 10 appears only as a one-step ending.
• Cap 4.
• Reward, entropy schedule, learning rate, warm-up and clipping exactly as in the brief.
• For unspecified AdamW details, register β=(0.9,0.999), ε=10^−8, weight decay 0.01, identically in both arms.
• No prefix rewards, masks, new curriculum, forced continuation or oracle actions.

Each run has 6,144,000 rollout attempts, with at most 24,576,000 operator calls. Memoization may reuse the frozen operator’s own deterministic result for the same world and input, but must not replace it with a dictionary oracle.

Wave rule for every training design in this answer. Run at most six processes, with computational and inter-operation thread counts set to one. A wave ends at 500 updates or 24 minutes, whichever comes first; an external deadline terminates it at 27 minutes. Save model, optimizer and every random-state stream. Resume until the fixed update total is reached. An interrupted, uncommitted update is replayed from the saved state. This respects the wall-clock requirement without inventing unavailable throughput measurements. Cloud allocation: $0.

### Locked evaluation

Generate two independent panels using seeds 35000 and 35001. Do not inspect either during training.

Each panel contains:

• 27 ordinary cells: k in {1,2,3,4,5,6,7,8,12} × final relation {8,9,10}, with 64 questions per cell.
• 18 edited-twin cells: k in {5,8,12} × final relation {8,10} × LINK edit, terminal-value edit, irrelevant-row edit, with 64 pairs per cell.
• Sixteen-person worlds. Include both non-repeating paths and unrestricted random walks. Reject “answer-changing” edits whose true answers accidentally remain equal.

Evaluation is greedy, with deterministic tie-breaking and cap 16. A cap termination without an explicit model STOP is a strict failure.

Every-seed capability marks, on both panels:

• All k≥4 ordinary cells: ≥59/64 answers and ≥59/64 strict.
• Every edited-twin cell: ≥59/64 strict pairs.
• All k≤3 cells: ≥61/64 answers and strict.
• Short-cell decline from a saved update-3,000 checkpoint: no more than 2/64.
• Relation-10 cells meet the same marks; no pooling with practised relations.

To attribute improvement specifically to the change, also require B to exceed A by ≥13/64 strict on both the k=8 and k=12, relation-10 cells, for every paired seed on both panels.

The capability mark and the causal-improvement mark are separate. Both arms passing would establish capability, not superiority of the new head.

### What a pass licenses

“A controller trained only on one- to three-call questions chose its own calls and stopping decisions on fresh questions requiring up to twelve calls, including withheld endings and counterfactual edits, across three preregistered seeds.”

It does not license arbitrary-length generalization, general English reasoning, or an advantage over all same-size transformers.

### Forecasts and rivals

I assign 0.90 probability to all three treatment seeds retaining strong short-question performance, 0.55 to at least one passing the k=12 strict cells, 0.30 to all three meeting the complete capability registration, and 0.25 to meeting the additional causal-improvement marks.

The strongest rival is the self-written consumed mask: it wins if P2 finds addressing failure, but loses as the first unconditional change because the observed stopping shortcut remains possible. Prefix credit is the other strong rival: it may improve learning speed, but adds supervision without removing the shortcut.

Most likely failure: the operation policy selects an attribute too early and the new head correctly stops afterward. Probability: 0.45.

Self-grade: SOLVED as a registration-ready experiment, not as a claim that the fix has already worked.

## 4. Two lotteries

The v3 evidence establishes sensitivity to training realization, not dependable success, while the start-up lottery is best treated as an alignment-and-credit bootstrap that a curriculum should target directly.

### 4a. What 3/3 versus 0/3 actually says

The full-pass observations are:

• Original v3: 1, 1, 1.
• v3-repro: 0, 0, 0, with partial cell counts 12, 14, 21.

Do not turn either triplet into a reliability claim.

If the six runs were independent draws from a common success probability, the exact 95% interval for 3 successes in 6 runs is approximately 0.118–0.882. That is extremely broad.

For the group difference:

• Conditional on three successes among six independent runs, the probability that all three fall in the specified original group is 1 / C(6,3) = 1/20 = 0.05.
• The two-sided Fisher probability is 0.10.
• If the runs are instead three genuinely matched initialization pairs, all favoring the original stream, the two-sided sign-test probability is 2(1/2)^3 = 0.25.

The often-tempting calculation 0.5^6=1/64 is the probability of one particular ordered outcome under p=0.5, not the appropriate two-sided significance test for this comparison.

Even original v3’s 3/3 has a two-sided exact 95% lower bound of only 0.025^(1/3)=0.2924.

### How many seeds?

| Question | Required prospective result |
|---|---|
| Can six consistently discordant matched pairs establish a stream effect at two-sided 5%? | Yes: 2/2^6=0.03125. Five such pairs are insufficient: 2/2^5=0.0625. |
| Can a small fresh experiment distinguish a roughly 90%-successful recipe from a 50%-successful one? | 12 fresh runs, pass if ≥10 succeed: false-positive probability under p=0.5 is 0.01929; power at p=0.9 is 0.88913. |
| Can all-success runs support success probability above 90% with a one-sided 95% bound? | 29/29, because 0.05^(1/29)>0.9. |
| Above 95% under the same rule? | 59/59. |

These are seed-level success calculations, not averages of accuracy across seeds.

### Cheapest decisive check

Assume the original initial weights and world streams can be reproduced.

First replay one originally successful seed under its exact original data stream, and then under the reproduction stream, with separate random generators for initialization, data and actions. Use the original 6,000-update budget.

If the three existing comparisons are truly paired and reproducible, add just three more matched pairs, initialization seeds 4300, 4301, 4302: six new runs. Six discordant pairs all favoring the original stream produce the sign-test result above.

If the original initialization/data states cannot be recovered, the historical claim is not replayable. Do not manufacture a “reproduction” by choosing a convenient new stream. Start the prospective 12-run reliability experiment instead.

A stream effect can reflect important rare examples, answer collisions, graph-cycle frequencies or optimization ordering. It need not be a code bug. Conversely, bit-identical computation on one batch does not establish identical whole-training randomness.

### 4b. A falsifiable start-up mechanism

My leading account is alignment-limited positive feedback.

Initially, the reader has little reason to attend to the row matching both subject and relation. If attention is roughly uniform over N rows, relevant-row mass is about 1/N, and the local softmax sensitivity is correspondingly small. Moving from 16 to 64 rows reduces that initial mass from 0.0625 to 0.015625.

Small accidental alignment gives some seeds a useful gradient. Better alignment puts more mass on the right row, making the next gradient more informative, producing a rapid transition. Other seeds learn weak output priors or concentrate on unhelpful rows, delaying that transition.

This explains both apparent bimodality and late rescue: the “stuck” state need not be absorbing. The seed reaching 512/512 at 18,000 updates can have crossed the threshold late; the seed reaching only 56/512 has not.

Falsifier: a stalled checkpoint already selects the correct row with probability at least 0.9 on ≥95% of 512 diagnostic queries, while answer accuracy remains near chance, and replacing its read attention with the correct row does not materially improve decoding. That would put the bottleneck downstream of row alignment.

Checkpoint prediction: immediately before successful take-off, correct-row mass should rise substantially before or alongside answer accuracy; failed runs should lack that transition. Probability: 0.75.

### A recipe for a new learner

Use curriculum order as the only experimental variable. Generate the same fixed training batches for both arms; one receives them in the order below, the other in a fixed shuffled order.

| Updates | Worlds/questions |
|---|---|
| 1–500 | Four people, 16 rows, one-step questions. |
| 501–1,000 | Same world size; k=1,2, equally represented. |
| 1,001–1,500 | Same world size; k=1,2,3, equally represented. |
| 1,501–6,000 | Six people, 24 rows; continuing mixture of k=1,2,3. |

Use seeds 4500, 4501, 4502; data seeds 4600–4602; diagnostic panel 47000. Keep the optimizer and reward unchanged. Define dependable onset as ≥487/512 one-step correct by update 2,000 in every seed, plus final short-cell marks ≥61/64.

For a new reader or transformer, small contexts target row-attention alignment. For the dispatcher, whose operator is already reliable, row distractors are not its attention problem: starting with one-step questions instead improves the frequency and clarity of rewarded action trajectories. Do not transplant the reader explanation to the dispatcher without that distinction.

I assign 0.75 probability that this ordered recipe gives all three new-learner seeds the specified onset, and 0.60 probability that it does so more consistently than the shuffled-bank control.

### Rival accounts

“Three original successes prove v3 is robust.” The intervals and matched-pair arithmetic rule that out.

“The failed start-up states are permanently dead.” Late rescue directly contradicts an absorbing-state version of that explanation.

“Just train every seed longer.” One seed remaining at 56/512 after tripling updates makes this an unreliable recipe, not a dependable solution.

Most likely mechanistic error: decoder conditioning or embedding-norm growth, rather than row alignment, is the principal bottleneck. Probability: 0.25.

Self-grade: SOLVED for the statistical numbers, falsifiable mechanism and concrete recipe.

## 5. Attack the roadmap

The roadmap puts too much engineering before the central learning claim: a frozen reader over a hand-maintained notebook is a useful memory system, but it does not establish that teaching changes the model’s reasoning.

### The strongest honest framing

Ben can build an assistant whose components he trained himself, whose factual memory is inspectable, whose corrections propagate immediately, and whose learned controller selects operations.

External memory does not invalidate learned reasoning. Neural systems learning algorithms while using external memory have a substantial research history; the interesting claim here would be the project’s tiny scale, particular transfer behavior and reproducibility, not the invention of that general idea.

Facts also need not all reside in weights for an assistant to improve through teaching. A persistent notebook is a legitimate form of system-level memory.

### The strongest honest objection

In M0, the English interpretation, storage semantics, correction policy and solving loop are all supplied by code. The neural component performs a learned lookup.

That is accurately described as a database-backed symbolic assistant with a neural reader. It is not yet a model that learns how to reason from teaching.

Calling append-only storage “learning” without specifying that the model weights and policy are unchanged would blur exactly the distinction Ben cares about.

### Specific faults in the proposed order

M1 is not a drop-in identity upgrade. Replacing trained entity embeddings changes the reader’s input/output geometry and potentially the dispatcher’s subject binding and recurrent updates. Passing a new-name operator test does not establish that the old dispatcher can use those identities.

A 4,096-name pool is not 4,096 simultaneous names. Nor is it 4,096 facts. With four rows per person, 4,096 facts correspond to 1,024 fully represented people.

M3 is premature. Larger contexts can make the notebook demo more impressive without resolving control or teaching-induced reasoning.

M4 risks overstating language learning. A learned parser for 120 tokens and a controlled grammar is worthwhile, but the claim is controlled-language interpretation, not broad English understanding. Names copied through a symbol table are handles, not learned semantic concepts.

M5 contains the actual research question and comes last. The evidence already shows that additional practice can destroy a held-out short skill. Retention cannot be deferred to a final integration milestone.

The size comparison needs correction. A 79,316-parameter operator plus a roughly 24,000-parameter controller is approximately 103,316 parameters, before the English reader and other learned components. Comparing only the controller with a 94,629-parameter standalone transformer hides the operator.

### Revised milestone order

| Order | Milestone and justification | Permitted claim / forbidden claim |
|---|---|---|
| 0 | Freeze the claim ledger, dictionary baseline and mechanical notebook demo, because they expose how much behavior comes from code. | “The memory plumbing works” / not “the model learned the procedure.” |
| 1 | Diagnose and test autonomous control on the original symbols, because this is the presently failing core capability. | “Learned execution transfers to these unpractised lengths” after passing / not “general reasoning.” |
| 2 | Run the small definition-learning experiment from Problem 7, because X2 should be tested before building a larger assistant around it. | “Answer-based teaching changed a learned procedure” after passing / not “one-shot English understanding.” |
| 3 | Establish new-name binding in the reader, then separately in the controller, because both interfaces depend on identity representations. | “Handles unseen identifiers in these settings” / not “learns arbitrary concepts from names.” |
| 4 | Add UNKNOWN after reliable answerable lookup, because missing information must be handled before real notebook use. | “Recognizes specified missing-fact cases” / not “knows when any belief is uncertain.” |
| 5 | Add the closed-English reader and repeat the teaching test through it, because this is where English teaching must become a learned capability rather than a template trick. | “Learns within this stated grammar” / not unrestricted English competence. |
| 6 | Scale through 64, 256, 1,024 and 4,096 facts with the same claim tests, because scale is valuable only after the underlying behavior is established. | Report the exact passed sizes / not extrapolation from a smaller context. |
| 7 | Add weight consolidation or learned recency only when a measured need justifies them, because both introduce interference or ambiguity that the notebook currently avoids. | A specific retention, latency or context-free-use claim / not unspecified “internalization.” |

The notebook demo can proceed in parallel with early scientific work, but its success must not be counted as evidence for X1 or X2.

### Rival roadmaps

“Build the polished notebook assistant first.” This loses because product progress can conceal that the central learned-control claim remains unresolved.

“Put every taught fact into weights from the beginning.” This loses because it couples factual storage, retrieval, continual learning and control before any one of them is isolated.

“Use a pretrained assistant instead.” It may win as a product choice, but it does not satisfy Ben’s stated goal of owning a genuinely learning model trained by this project.

Forecast: replacing the identity interface without separately retraining or validating the dispatcher will break at least one previously passed control cell. Probability: 0.85.

Most likely way my ordering is wrong: Ben values ownership and inspectable teaching more than weight-level changes to reasoning; under that interpretation the notebook deserves earlier practical emphasis, though its scientific claims remain unchanged.

Self-grade: SOLVED.

## 6. New names before M1 is built

Under ordinary unnormalized tied dot-product logits, I would not make the current M1 design the mainline implementation; I would use a row-copy output, because the principal avoidable risks are decoding and scale control—not an inability to represent 4,096 names in 48 dimensions.

My assumptions are independent isotropic random directions in 48 dimensions, codes fixed within each world, and the same code used for every occurrence of a name in that world. If M1 already normalizes all name and value logits and uses a well-controlled shared temperature, I would change the verdict to GO for a 16-active-name experiment, though not to a 4,096-active-name claim.

### Random-code geometry

For two independent unit vectors, the cosine z has density proportional to:

(1 − z²)^((48−3)/2).

For N codes there are M=N(N−1)/2 pairs. The following expected maxima use a spherical-tail extreme-value approximation; pairwise angles are not jointly independent, so those expectations are approximate. The 95% upper bounds use a union bound and do not require joint independence.

| Active names N | Pairs M | Approximate expected largest pair cosine | 95% upper bound on largest cosine | Sufficient normalized scale for ≥99% name-only probability |
|---:|---:|---:|---:|---:|
| 16 | 120 | 0.363 | 0.462 | 13.6 |
| 64 | 2,016 | 0.473 | 0.546 | 19.3 |
| 4,096 | 8,386,560 | 0.670 | 0.709 | 44.4 |

The calculation is:

P(correct) ≥ 1 / [1 + (N−1)e^(−s(1−c_max))].

So a sufficient scale is:

s ≥ log(99(N−1)) / (1−c_max).

These bounds are conservative: they pretend every competitor is as close as the worst one.

Three conclusions follow.

First, there is no collision impossibility at 16 names. If the output direction exactly equals the target code, its self-cosine is one and it wins argmax against all distinct random codes.

Second, confidence and correctness are different. At many candidates, the sum of many small competing probabilities can make confidence poor even when argmax is correct.

Third, the active vocabulary matters. A pool of 4,096 codes with only 16 active in a world has a 16-name output competition, not a 4,096-name competition. Four thousand ninety-six simultaneous people would require 16,384 complete fact rows, beyond the proposed 4,096-fact milestone.

### The scale problem

If learned value embeddings grow while name vectors stay fixed, ordinary tied logits compare vectors whose norms evolve differently.

An entity-specific learned scale can compensate for average differences. It does not automatically solve every direction- and value-dependent mismatch, and changing it also changes input geometry when the same scaled code is used at input and output.

A shared bias needs precise interpretation:

• Added to every output logit, it cancels exactly and does nothing.
• Added only to name logits, it can adjust name-versus-value preference.
• It cannot improve discrimination between two names.

Per-world code reassignment also removes the possibility of memorizing a stable entity-specific shortcut. That is desirable for binding, but it makes the initial matching problem harder. I predict more variable onset under abrupt full-context random-code training than under the staged recipe. Probability: 0.75.

### The alternative I would register

Use a row pointer, then emit that row’s object token verbatim. Pointer outputs are specifically suited to variable output dictionaries defined by the input itself.

Assume the reader exposes 48-dimensional query and row representations q,H_i. Score rows with:

ℓ_i = β qᵀ W H_i / sqrt(48),

where W is 48 × 48 and β is one learned positive scale. This adds 2,305 parameters. With the original parameter count retained, the total is 81,621. Removing unused learned entity-embedding rows can reduce the active learned count; report that separately rather than silently subtracting stored weights.

At inference, choose the highest-scored row and copy its object identifier. No output embedding reconstruction is required.

Train from final answer tokens using:

L = −log Σ_{i:object(i)=y} p_i.

This avoids adding gold-row supervision. Because duplicate values can receive accidental credit, provenance gets a separate pass mark.

### Keep changes sequential

Stage A: output change only.

• Start from one fixed passing operator checkpoint.
• Retain the original 16 entity embeddings.
• Add the row-copy output.
• Seeds 6100, 6101, 6102.
• 2,000 supervised updates, 64 one-step examples per update.
• AdamW 10^−3, 100-update warm-up, clip 1.0.
• Every relation: ≥63/64 answers and ≥61/64 correct source rows on panel 64000.
• Failure stops M1; it is an output-interface failure, not evidence against new-name binding.

Stage B: identity change only.

Clone each passing Stage-A checkpoint into two arms. The control retains its original identity embeddings. The treatment uses random codes reassigned per world.

• Pool seed 63000: 4,096 codes, training pool 3,072, reserved pool 1,024.
• Use unit directions multiplied by the original checkpoint’s mean entity-embedding norm.
• A world’s map is fixed for all its questions and rollouts.
• 6,000 updates per arm, data seeds 6200–6202.
• First 500 updates: four people/16 rows. Remaining 5,500: sixteen people/64 rows. Both arms receive identical world structures.
• Same optimizer as Stage A.

Primary evaluation, panel 64001: sixteen active names, four relations, three identity conditions—training-pool codes, reserved-pool codes, and newly generated codes outside the entire pool—giving 12 cells × 64 questions.

Every seed must achieve ≥63/64 answers and ≥61/64 source rows in every cell.

Secondary scale evaluation: repeat the 12 cells with 64 active names and 256 rows, marks ≥59/64 for answers and provenance. Failure here does not erase a successful 16-name binding result; it identifies a scale limitation.

Also require 64/64 exact renaming-equivariance pairs when only external identifier strings change while their vector assignments remain consistent. That is principally an interface-bug check.

### Named failure signatures

| Signature | Interpretation |
|---|---|
| Same identifier receives different vectors in query and story | Binding-interface bug; no learning result is interpretable. |
| Correct row receives high attention, but tied decoder emits the wrong name | Decoder/scale failure, not failed retrieval. |
| Name answers fail while value answers remain strong as value norms grow | Output-class scale imbalance. |
| Answer accuracy is high but provenance is poor | Duplicate-object credit or shortcut retrieval. |
| Reserved/new codes fail while familiar codes pass under matched geometry | Learned matching has not generalized; this is the substantive binding failure. |
| Failure appears only with more active names, not merely a larger unused pool | Crowding, attention dilution or context scaling—not “4,096 identifiers are impossible.” |

The fixed 4,096 × 48 float32 codebook is 786,432 bytes, or 0.75 MiB, if stored outright. “Frozen” does not mean “free storage.”

### Rivals, forecasts and risk

A normalized cosine/tied-code decoder is a credible rival. It loses my mainline choice because it still requires reconstructing a sufficiently accurate output direction, whereas copying removes that requirement.

A learned 4,096-entry embedding table loses because it adds 196,608 learned numbers and does not establish unseen-name binding.

My forecast for all three seeds meeting the 16-name primary mark is 0.45 for the unnormalized tied design, 0.65 for a normalized tied design, and 0.70 for the staged copy design. These are engineering priors, not results.

Most likely way the recommendation is wrong: the existing reader already reconstructs codes accurately enough that one learned scale solves the practical problem, making the pointer change unnecessary. Probability: 0.25.

Self-grade: SOLVED for the quantitative go/no-go decision and staged alternative.

## 7. Teaching that changes reasoning, and memory in weights

A small, answer-trained definition can test X2, and bounded consolidation into weights is feasible, but no finite behavioral test can prove that an equivalent hand-written macro could not reproduce the behavior.

That last phrase needs a scientific replacement: demonstrate that this implementation’s new behavior is caused by gradient-trained weights, not by an inserted definition-specific interpreter.

### 7a. The cheapest meaningful definition test

The current world has only one person-to-person operation. Teaching “do LINK twice” is a useful preliminary test, but it cannot distinguish a learned composition rule from assigning a new token a larger step count.

A stronger test needs two noncommuting person-to-person operations.

#### Prerequisite: create that distinction without changing the world size

In a separate experimental fork, let relation 11 mean landlord L, and let relation 8 be a person-valued employer relation E. Relations 9 and 10 remain value-valued endings. There are still four rows per person.

Preserve the old schema in old-skill examples: relation 8 remains value-valued there. The rows themselves determine what the lookup returns. Never ask a new-schema question to terminate at a person-valued operation; this preserves the task’s local value-result stopping convention.

The original operator has not been shown reliable on this altered schema. Audit it first. If necessary, allow a separately labelled 2,000-update one-hop adaptation, half original-schema examples and half new-schema examples, keeping token embeddings fixed. Require ≥63/64 answers in every old and new one-hop cell for every seed, then freeze it again.

Next give the controller a fixed palette of the four primitive operation tokens in addition to its question-position candidates. This is necessary because a question containing only the new word “patron” must still permit primitive operations that are not literally present in that question.

Make this an explicit interface prerequisite, not a hidden macro:

1. 2,000 updates on old questions only after adding the palette.
2. 4,000 updates mixing old questions and new primitive L/E programs equally.
3. All training programs require at most three calls.
4. Relation 10 is still only a one-step training ending.
5. Require the old control marks and ≥59/64 strict on fresh primitive L/E programs at lengths 4, 5, 6, 8.

A prerequisite failure blocks X2; it is not a failed teaching experiment.

#### The actual teaching intervention

Reserve a new token D, displayed as “patron.” Clone each of three passing parents into three arms:

| Arm | One taught definition |
|---|---|
| A | “A patron is the employer of one’s landlord”: D=E∘L, executed L then E. |
| B | The counterfactual definition: D=L∘E, executed E then L. |
| C | No definition teaching; matched old-skill rehearsal only. |

Use experiment seeds 7100, 7101, 7102. The two definitions have identical primitive length, so a step-count interpretation cannot distinguish them.

Freeze the learner/executor implementation before choosing the definition branch. The teacher’s answer oracle knows the definition; the executor must not.

Teaching data: 64 worlds × 4 questions = 256 distinct new-definition examples, seed 72000, using only bare-D questions ending in relation 9. Each requires two person operations and one value lookup.

Training: 2,000 updates, each containing 16 new-definition questions and 48 old questions, with K=16, cap 4, and the existing REINFORCE settings. Freeze the operator; update the controller and the new token embedding. No action traces, intermediate answers, remaining counts or forced continuation are supplied.

This is one taught rule followed by practice, not one-shot language understanding. The English sentence specifies the teacher’s task; the learner acquires the rule through answer feedback. Passing this does not yet prove that the learner interpreted the sentence itself.

#### Held-out compositions

On fresh sixteen-person worlds, test:

DLR, LDR, DER, EDR, DDR, DLDR

for R in {9,10}: 12 cells, 64 questions each, requiring 4, 5 or 6 calls.

For each item, include a twin containing the fully expanded primitive question. Neither new-D compositions nor these longer training trajectories have been practised.

Use panels 73000 immediately after teaching and 73001 after 1,000 additional old-only rehearsal updates. Also cold-restart from weights alone, without the teacher, definition sentence, optimizer or teaching buffer.

Every-seed marks:

• ≥59/64 correct-and-strict pairs in every composition cell, at both evaluation points.
• Taught arms exceed no-teaching arm C by ≥13/64 strict in every composition cell.
• On worlds where the two definitions differ, swapping A’s and B’s taught weights swaps the corresponding primitive-order behavior.
• Every previously correct item on the locked old-skill panel remains correct and strict: zero regressions, not merely an acceptable average.
• Fresh old-skill cells remain ≥61/64.

The old panel must include original held-out endings and previously passed long programs, not just easy training examples.

#### What prevents a macro from being the actual implementation?

Require an execution audit showing:

• no stored D-to-operation-list mapping in the learner or executor;
• no definition-specific expansion branch;
• only gradient updates produce the taught weight difference;
• resetting the taught weights removes the new behavior;
• the same frozen executable produces the opposite operation order when loaded with the opposite-definition weights.

This is strong evidence about how this system acquired and executes the rule. It cannot prove that no other symbolic program could imitate its inputs and outputs. A macro interpreter is, in fact, an essential positive control.

Forecasts, conditional on the prerequisites passing: bare-definition acquisition in all seeds, 0.75; all composition marks plus zero old regressions immediately after teaching, 0.25; the full mark including rehearsal persistence, 0.15.

The likely failure is retention or composition, not recognizing the bare new token.

### 7b. Is bounded weight memory possible near 80,000 parameters?

Yes—but I would first demonstrate a bounded, protected fact cache, not promise unrestricted continual consolidation.

Assume 16 people and 16 value tokens, giving 32 possible output tokens. Allocate a trainable matrix:

A in R^(64×32),

one row for each person/relation key. That is 2,048 parameters, bringing the 79,316-parameter reader plus cache to 81,364. The full system still includes the dispatcher; do not call the whole agent an 81,364-parameter system.

Use an explicit storage-mode interface: story lookup or weight-cache lookup. Do not claim that mode selection is learned.

Teach the 64 facts in eight blocks of eight, with:

• SGD learning rate 1.0;
• momentum 0;
• weight decay 0;
• 100 updates per block;
• only the addressed cache rows receiving gradients.

Then correct eight specified keys with 200 further updates. Because untouched rows and the original reader are frozen, interference with those rows is absent by construction.

Use seeds 7500, 7501, 7502 for fact assignments. Require:

• 64/64 stored facts correct after cold restart with no notebook;
• all eight corrections reflected;
• all 56 uncorrected facts unchanged;
• the original reader’s outputs bit-identical in story mode;
• on fresh composed questions, the dispatcher’s normal strict marks still hold when this cache replaces the lookup backend.

This is genuinely information stored through weight updates. It is also, candidly, a trainable table, not a discovery that dense neural weights are a superior database.

For arbitrary facts it is not efficient storage: the logits occupy 8,192 bytes, while 64 fixed-key, 16-way facts contain only 256 bits of value information, before metadata.

To justify building beyond this demonstration, require either:

• useful answers when the notebook is genuinely unavailable, with no hidden copied rows; or
• at least 2× lower end-to-end p95 latency than the neural notebook-reading path, with no loss of correctness, correction behavior or retention.

A conventional dictionary can also cache facts. The advantage is availability or integration, not a new logical power.

More sophisticated continual-learning methods can reduce interference; they do not eliminate the need for retention testing. For example, EWC protects important weights by penalizing changes, but that is not a guarantee for this architecture or distribution.

### Rival designs

Keeping the definition in a notebook and interpreting it at query time is an excellent baseline, but it does not establish consolidation into weights.

Fine-tuning all approximately 80,000 reader weights on recent facts without replay or protection loses because the project already has concrete forgetting evidence.

Declaring memory in weights impossible at this size loses because bounded protected storage is straightforward; the difficult question is useful, scalable, interference-resistant integration.

Most likely weakness: the bounded cache works but offers no practical advantage over an ordinary array or dictionary. Probability: 0.95. For X2, the most likely substantive failure is that teaching the bare definition does not support its unseen compositions while preserving every old case.

Self-grade: PARTIAL. The experiments and bounded consolidation design are specified, but the literal “a hand-written macro could not fake it” bar cannot be satisfied by behavior alone. The exact additional evidence is the weight-causality and execution audit above; the defensible claim is learned acquisition in this implementation, not symbolic inimitability.

## 8. UNKNOWN, recency and the honest yardstick

Add UNKNOWN only after stable lookup, leave recency in deterministic notebook code for now, and use dictionary and pretrained baselines to separate a worthwhile learning experiment from an unnecessarily complicated database product.

### 8a. UNKNOWN without destroying onset

For the copy reader, add a learned NULL row whose object is UNKNOWN. Its score is learned; do not supply an “answer exists” flag or a precomputed matching-row mask.

First add the output option and verify that answerable behavior remains intact. Then change the training distribution.

Use reader seeds 8100, 8101, 8102, 2,000 supervised updates, 64 examples per update, AdamW 10^−3, 100-update warm-up and clip 1.0. Initialize the NULL logit bias to −6.

| Updates | UNKNOWN examples per batch | Proportion |
|---|---:|---:|
| 1–250 | 0/64 | 0% |
| 251–500 | 4/64 | 6.25% |
| 501–1,000 | 8/64 | 12.5% |
| 1,001–2,000 | 13/64 | 20.3125% |

Within each final-stage set of 13 negatives, use:

• 3 absent-subject queries;
• 4 missing subject/relation pairs where both the subject and relation occur elsewhere;
• 4 matched deletion counterfactuals;
• 2 queries whose subject is UNKNOWN.

Match positive and negative row-count distributions. For deletion pairs, keep row count constant by replacing the deleted target row with a previously omitted irrelevant row. Otherwise, “fewer rows means UNKNOWN” becomes an easy shortcut.

Use ordinary answer/UNKNOWN cross-entropy. Do not balance the headline metric by averaging known and unknown cases; report them separately.

Reader marks, every seed:

• Answerable cells: ≥63/64 correct, hence at most one false UNKNOWN.
• Each missingness type: ≥59/64 correct UNKNOWN.
• Previously correct answerable items: decline ≤1/64 per cell.
• Test at multiple matched context sizes up to 64 rows.
• Fixed argmax decoding; no threshold selected from the final test panel.

A system that always says UNKNOWN gets zero on the answerable cells and fails immediately.

### Propagation through a chain

UNKNOWN should be absorbing at the lookup interface: an UNKNOWN subject has no known row, and the learned reader should therefore return UNKNOWN for every relation. The two UNKNOWN-subject examples per batch teach that behavior; it is not an executor override.

Then freeze the reader and separately fine-tune the dispatcher for 2,000 updates, seeds 8200–8202, with 13/64 unanswerable questions per batch, still using k≤3.

Distribute the first missing lookup across all possible positions. Reward the final answer as before. Do not force STOP after UNKNOWN.

For strict evaluation, an unanswerable execution is correct only when it:

1. follows the correct prefix;
2. encounters UNKNOWN at the first genuinely missing lookup;
3. voluntarily stops immediately.

Extra calls after UNKNOWN are strict failures even if they keep returning UNKNOWN.

Evaluate first-missing positions early, middle and final on k=4,5,8,12. Require ≥59/64 strict in every missingness cell, while retained answerable cells remain ≥61/64, with declines ≤2/64.

I assign 0.70 probability to all three reader seeds satisfying the known/unknown marks, and 0.45 probability, conditional on that, to all three dispatchers meeting the long-chain immediate-abstention marks.

These are claims about missing facts in this closed world. UNKNOWN does not mean the system has learned general epistemic humility.

### 8b. Learning recency

Without age information, two histories can yield the exact same unordered pair of conflicting rows while requiring different answers. A stateless reader receiving identical input cannot distinguish those histories.

The smallest meaningful addition is one scalar timestamp or append-order value per row, passed into the row representation. Do not pass a “this is the newest matching row” flag—that would supply the answer.

A normalized timestamp such as append index divided by the largest append index in the story is sufficient to expose order without choosing the relevant row. The learner must still combine key matching with temporal comparison.

A valid small experiment would use:

• two or three versions of selected keys;
• random row permutations;
• a deliberately newer irrelevant row;
• timestamps with substantially smaller gaps at evaluation;
• 64 queries per conflict condition;
• ≥63/64 correct latest-value selections, with ≥63/64 retention on nonconflicting rows.

However, my decision is SKIP this build now.

The notebook’s “latest value for a key” rule is transparent, deterministic and useful. Teaching a neural model to reimplement it does not address the central control or X2 uncertainty. Keep the append-only diary for provenance and derive the current view in code.

Reconsider learned recency only when the research question concerns temporal interpretation, historical “as of” questions, or learning different update semantics—not merely replacing a reliable maximum operation.

### 8c. The one-time yardstick

Compare three systems on the same notebook and task semantics:

1. Dictionary plus explicit rules.
2. Ben’s frozen reader and learned controller.
3. One fixed pretrained instruction model using the same read interface.

For a concrete, free local comparator, use Qwen2.5-3B-Instruct, whose model card specifies 3.09 billion parameters and a 32,768-token context. This is a fixed comparator, not a claim that it is the best current model.

Use the free PC. Freeze the model version and precision before testing. Use greedy decoding, an 8,192-token context, at most 128 generated tokens per action decision, and the same 16-read-call cap. Malformed actions count as failures; there are no silent retries.

Give the pretrained model the same facts and operation meanings. Its pretraining is an enormous additional resource, so this is a product/reference comparison, not a controlled comparison of learning efficiency.

Use one 32-question format-development panel, seed 88101, then freeze the prompt. Final panel seed: 88100.

### Final panel and measurements

Use 16 cells × 64 test units:

• Eight ordinary cells: k=1,3,5,8, practised versus held-out endings.
• Two unseen-name cells.
• Three UNKNOWN cells: first missing lookup early, middle and final.
• One correction cell.
• One irrelevant-edit cell.
• One taught-definition composition cell.

A test unit can be a paired before/after item where appropriate. Unsupported capabilities are explicitly marked unsupported; they must not disappear from the project’s intended-capability ledger.

For each tiny-model seed, report the complete cell table. Measure:

| Dimension | What must be recorded |
|---|---|
| Correctness | Final-answer accuracy, strict executed traces, edited-pair success, UNKNOWN errors, correction errors. |
| Control | Premature STOP, first wrong call, total calls, voluntary versus cap termination. |
| Learning | Teaching examples, gradient updates, new-definition gain and every old-item regression. |
| Compute | End-to-end latency, per-seed median and p95, total operator/model calls, hardware and precision. |
| Size | All learned and frozen parameters, codebook bytes, notebook bytes, other stored state. |
| Supervision | Operator pretraining, controller training, intermediate supervision if any, pretrained-model resources explicitly unknown rather than zero. |
| Traceability | Actual executed reads and verifiable supporting rows—not a generated explanation presented as an execution trace. |

A dictionary trace is just as traceable as a neural controller’s tool trace. Attention weights alone do not establish faithful internal reasoning.

“Per parameter” must count the whole learned system. “Learned” must identify which weights changed and what code supplied. “Traceable” must refer to recorded execution, not to persuasive prose.

### Explicit stop conditions

There are two different decisions.

Stop expanding the assistant product if the dictionary solves the supported notebook tasks exactly while the neural system adds errors, latency and no demonstrated X1 or X2 capability. More names, English templates and notebook features should not be used to hide that result.

Stop the current control recipe and change the research question after the registered STOP experiment and one separately registered curriculum-order experiment if neither produces the full unpractised-length marks across all three seeds. Do not run an open-ended sequence of favorable-seed searches.

If autonomous control passes but X2 fails its composition or retention marks, retain the narrower control result and stop claiming continual teaching-induced reasoning. If X2 was blocked by an unpassed prerequisite, label it untested, not disproved.

A good changed direction would be a focused study of why tiny controllers learn finite-horizon shortcuts and which addressing or stopping biases alter that outcome. That is a legitimate result, not a failed attempt to make a chatbot.

### Rivals and principal risk

Starting with 50% UNKNOWN from scratch loses because it introduces an easy class prior before reliable positive retrieval exists.

Hard-coding “UNKNOWN ⇒ STOP” loses when the claim is that stopping was learned, though it would be perfectly sensible engineering in a non-learning baseline.

Learning recency without timestamps loses because the relevant information is absent, not merely difficult to optimize.

Omitting the dictionary because it is “not AI” loses because it hides how much of the toy is already solved by the supplied data structure and rules.

I assign 0.99 probability that a correctly implemented dictionary/rules system achieves perfect scores on its fully specified supported cells. I do not assume the small pretrained model will beat Ben’s system on this synthetic execution task.

Most likely failure in the UNKNOWN design: the reader learns context-size or score-scale cues rather than robust evidence of a missing matching key. Probability: 0.30. Matched row counts and separate scale tests are therefore essential.

Self-grade: SOLVED for the UNKNOWN protocol, recency decision and explicit comparison/stop criteria.

## Self-grade summary

| Problem | Grade | Boundary |
|---|---|---|
| 1. Why counting wins | SOLVED | Finite-range representability and falsifiable causal account; mechanism still requires testing. |
| 2. Diagnostics | PARTIAL | Fixed weights cannot reveal whether an identical counter originated from the cap or rewarded depth. |
| 3. The one fix | SOLVED | Complete preregistered experiment, including never-practised length 12. |
| 4. Two lotteries | SOLVED | Statistical sample sizes, cheapest checks, falsifiable mechanism and curriculum recipe. |
| 5. Roadmap | SOLVED | Revised order with explicit claim limits. |
| 6. New names | SOLVED | Quantitative geometry, conditional no-go and staged copy alternative. |
| 7. Teaching and weight memory | PARTIAL | Runnable causal-learning tests; literal immunity to imitation by a macro is not behaviorally identifiable. |
| 8. UNKNOWN and yardstick | SOLVED | Concrete training schedule, recency skip decision and stopping rules. |

## One ordered two-week plan

| Window | Ordered work | Parallel work and dependencies |
|---|---|---|
| Days 1–2 | Freeze registrations, strict-trace semantics, random streams and cap accounting; run Problem 2’s checkpoint probes. | Build and verify the dictionary yardstick; prepare locked panels without inspecting model scores. |
| Days 3–4 | Run 19b unchanged and conduct the exact v3 replay check. | Analyze existing traces while training occupies the six Mac slots; prepare the fixed pretrained comparator on the PC. |
| Days 5–7 | Run the two-arm STOP experiment unless the diagnostic veto applies. | No architecture substitutions. Keep 19b’s length-practised models separate from this length-generalization experiment. |
| Days 8–9 | Run the curriculum-order comparison if onset or optimization is the remaining bottleneck. | Start the row-copy Stage A only in otherwise unused training slots; never exceed six processes. |
| Days 10–11 | If control passes, run the two-person-operation and primitive-palette prerequisites for X2. | Proceed to random-code Stage B only after its own Stage-A gate; it is lower priority than the core control result. |
| Days 12–13 | Run the actual definition-teaching arms only if their prerequisites pass; otherwise finish and characterize the failed prerequisite. | UNKNOWN is next in the queue, not a reason to delay a clean control result. Do not begin 4,096-fact growth or learned recency. |
| Day 14 | Open the locked final panels, run the one-time yardstick, publish every seed and make the registered stop/go decisions. | Unfinished experiments remain unfinished; untested capabilities remain untested. No last-day threshold changes. |

## Five lines for Ben

Your tiny model has already learned a real lookup skill.
The hard part is choosing the next step and stopping for the right reason.
First test that skill on longer problems it has never practised.
Then teach one new rule and check that it uses it in new combinations without forgetting.
A notebook is useful memory, but adding a note is not the same as teaching the model how to reason.
