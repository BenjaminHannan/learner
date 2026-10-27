# Teaching-to-Test Contract for the First Milestone: Facts-First With an Explicit Bridge

## Recommendation in brief

Adopt **Contract A: a randomized fictional relational world taught by single English sentences and tested, with teaching text removed, by paraphrased single-hop queries, two-hop chains, corrections that must propagate through chains, unrelated interference, and a process restart.** All persistent learning goes into W through a writer that is meta-trained by the loss on later queries; theta is frozen after initial training; z is cleared before every scored query. The decisive test is not "recall the taught fact" but "answer a two-hop question correctly after an intermediate fact is corrected," which an answer cache in W cannot pass and workspace-conditioned retrieval can. The next experiment (Contract C, taught relation definitions) reuses the same machinery to test whether W can hold a small program that the frozen reasoner interprets. I assess that bridge as real but narrow: it reaches composition of familiar operations, not acquisition of new primitives.

Everything below is design. No experiment has been run; no result is claimed.

---

## 1. Contract choice

### 1.1 Three candidate contracts

| | **A. Randomized relational facts (recommended)** | **B. Method-first: novel functions from demonstrations** | **C. Taught rules over stored facts (bridge)** |
|---|---|---|---|
| Taught | English declaratives about a per-episode random world: "Tarvo works for Kelvane." | Input-output demonstrations of an unseen symbol-mapping function; test on novel operands (as in R3 C3, Lake 2019 Sec 3-4.3; R9 extras, Chollet III.1.1) | A defined relation: "A patron of a person is the employer of that person's landlord," plus facts |
| Feedback | None at teaching (accepted); pass/fail only in practice | Pass/fail on queries | Same as A |
| Test | Paraphrase, 2-hop, correction-then-2-hop, interference, restart, W removed | Novel operands under the taught function; W removed | Held-out relation compositions applied to facts; correction of an underlying fact |
| Meaningful evidence | High for persistent, composable memory; nil for procedure acquisition | Highest for method learning if it works | Medium: composition of familiar primitives from a stored definition |
| Feasibility (16 GB, 10-min chained runs) | High: ~1-2M parameters, episodes of ≤16 sentences [hypothesis] | Low-medium: meta-training over a program distribution; Lake 2019 needed 10,000 episodes and under one hour on a Titan X for a memory-based (not weight-writing) model (R3 C3 note); Kirsch et al. needed ≥8,192 tasks to leave the task-identification regime (R13 C3) | High: same machinery as A plus one extra relation type |
| Shortcut resistance | Strong: bindings re-randomized per episode; test templates and compositions held out; correction after composition defeats write-time caching | Weak at tiny scale: "task identification" among meta-trained programs is indistinguishable from learning without a very large program family (R13 C3) | Medium: held-out compositions; write-time expansion defeated by ordering and correction |
| Relevance to persistent reasoning and method learning | Direct for persistence and workspace-conditioned retrieval; indirect for methods | Direct for methods; persistence untested unless W also holds the function | The bridge |

### 1.2 Why A first

**Meaningful evidence.** The published knowledge-editing literature already provides the discriminator between a fact in memory and an answer hard-coded to a query. Yao et al. distinguish Reliability, Generalization to rephrasings, and Locality (R1-editing-eval, Yao Sec 2, Eqs. 2-4), and add Portability, including One-hop reasoning where the edited fact must feed a downstream inference (R1, Yao Sec 5.1). MQuAKE shows that MEMIT reaches 96.2% edit-wise recall yet 7.0% multi-hop accuracy on GPT-J (R1, MQuAKE Sec 4.2, Table 3), and the authors interpret this as "hard coding them into the model by updating weights locally" rather than integrating knowledge (R1 extras, MQuAKE Sec 4.2). Cohen et al. report ripple-effect accuracy of only 38-66 for parametric editors (R1, Cohen Sec 5.2). So "single-hop recall passes, chained use fails" is the documented signature of an answer cache. Contract A is built so that this signature is the primary measurement, at a scale where we can also intervene on W directly.

**Feasibility.** A meta-trained memory system of this size has precedent within an hour of single-GPU time for the non-weight-writing case (R3 C3 note, Lake 2019 Sec 4.1). Whether the additional writer converges in six chained ten-minute runs is my hypothesis, not a fact; Section 4 gives stopping rules for the case where it does not.

**Shortcut resistance.** Two design choices from the meta-learning literature remove the main shortcut in the previous draft. First, all entity bindings are re-sampled every episode, so no binding can be stored in theta: Santoro et al. shuffle labels per episode precisely to prevent "slowly learning sample-class bindings in its weights" (R4-mann-babi, Santoro Sec 2), and Lake 2019 re-assigns primitive meanings every episode with the true permutation held out (R3 extras, Lake 2019 Sec 4.3). Second, Chan et al. show that when labels are fixed, an in-context strategy and an in-weights strategy give the same answer, so the evaluation is "ambiguous (by design)" (R13-icl-vs-weights, Chan Sec 4); randomized bindings remove that ambiguity.

**Relevance.** Two-hop chains force the retrieval key at step 2 to depend on what was retrieved at step 1, which is the single capability the provisional loop `q_t = Q(x, z_t)` claims and the draft code lacks. Contract A is the smallest test of that claim. Contract C then reuses the identical world and model to ask whether W can hold a program.

### 1.3 Why not B or C first

B is where the ambition lives, but at this scale a positive result would be ambiguous. Kirsch et al. describe three regimes as task count grows: task memorization, task identification, and general learning-to-learn, with the transition at roughly 2^13 tasks in their setting (R13, Kirsch Sec 4, Insights 1 and 3). With a program family small enough to meta-train in ten-minute runs, success most likely means task identification: the reasoner recognizes which of the meta-trained programs it is seeing. That is "selecting a parameter of a known operation," the exact confound the brief warns against. C is a better bridge than B because its shortcut (task identification among 2-chains) is enumerable and can be held out exactly.

### 1.4 Labeled assumptions and the conditional recommendation

- Assumption 1 (labeled): a learned writer trained through post-write query loss converges within six chained runs. If it does not while the fixed-rule writer (encoder-derived key and value, beta=1) does, use the fixed-rule writer for milestone one; the contract is unchanged. This is the one unresolved choice that changes the implementation but not the claim.
- Assumption 2 (labeled): the answer set is small enough for exact-match scoring. All answers are names or attribute values from a closed vocabulary; SCAN-style exact match is the metric throughout (R3 extras, Lake & Baroni 2018 'The SCAN tasks').
- Assumption 3 (labeled): the 100 GB storage cap is non-binding; checkpoints for a 2M-parameter model are megabytes.

---

## 2. Information boundaries

### 2.1 Component-by-stage table

"Sees" lists inputs; "changes" lists what the component may modify. theta = all slow parameters (encoder, reasoner, writer, decoder, key/value projections). W = persistent memory. z = workspace. L = audit log of accepted teaching strings (external, plain text). G = evaluator's ground-truth world graph.

| Component | Initial training (meta-training) | Teaching / practice | Persistent write | Clearing temporary state | Scored inference | Evaluation |
|---|---|---|---|---|---|---|
| **Encoder** | Sees: teaching and query strings from train templates and train name pool. Changes: theta (outer loop) | Sees: teaching string. Changes: nothing | Not involved | Not involved | Sees: query string only. Changes: nothing | Not involved |
| **Recurrent reasoner** | Sees: x, z_t, m_t from W (W is inner-loop state, reset per episode). Changes: theta | Sees: x_teach, z_t, m_t (reads W to expose what is already stored). Changes: z only | Not involved | z reset to fixed init; W untouched | Sees: x_query, z_t, m_t for fixed K steps. Changes: z only; no writes | Not involved |
| **Writer** | Sees: x_teach, bounded trace z_K, current read m. Changes: theta via gradient through the delta write to later query loss; W (inner loop) | Sees: same. Changes: proposes (k, v, beta) | Applies W' = W + beta (v - W k) k^T; the only channel that changes W | Not involved | Disabled | Not involved |
| **Checker** | Not involved (teaching is accepted by declaration) | Sees: model answer and the logged object for the practiced item; emits pass/fail only. Never sees G | Gates a re-write on fail only | Not involved | Absent | Not involved |
| **Replay process** | Not involved | Sees: L (strings only). Re-presents a logged teaching string through the ordinary teaching channel | Same as any teaching write | Not involved | Absent: L is not readable during a scored query | Not involved |
| **Evaluator** | Holds G, held-out templates, held-out compositions, held-out names; never touches theta | Not involved | Not involved | Not involved | Not involved | Sees: model outputs, W snapshots, L. Scores exact match against G; runs interventions on W |

### 2.2 The specifics the brief asks for

**Teaching representation.** One English sentence per fact, tokenized at the syllable level (names are two syllables from a 40-syllable inventory; ~70 function words; total vocabulary ~120). Example: "Tarvo works for Kelvane." Corrections are also sentences: "Kelvane has relocated. Kelvane is now based in Vell." There are no task IDs, family labels, or answer indices anywhere in the input.

**Feedback format.** At teaching: none; an accepted sentence is ground truth by declaration, which the brief permits. At practice (Episode D): a single bit, pass/fail, produced by comparing the model's answer to the logged object; the correct answer is never revealed by the checker. At scored inference and evaluation: nothing.

**What the writer sees.** x_teach (encoder output), the bounded trace z_K after K=6 reasoner steps over the teaching sentence (so it can see what W already contains under the same key), and the current read m. It never sees a decoded response, a target embedding, or a query. This matches the CaMeLS constraint that the update must be "broad rather than query specific" because Q_test is unavailable at write time (R8-learned-writers, extras, Hu et al. Sec 3.1).

**Which weights change.** Meta-training: theta by the outer loop; W as inner-loop state, initialized tabula rasa each episode (MNM initializes memory "tabula rasa at each task episode," R8 extras, Munkhdalai Sec 3.5; TTT shares W_0 across sequences, R11-ttt-titans-hopfield, Sun Sec 2.7). Teaching and practice: W only. Scored inference: nothing. The writer's training signal is the exact-match loss on queries posed after the write, backpropagated through the differentiable delta update, following CaMeLS's bilevel structure (R8 C1, Hu Sec 3.2, Eqs. 1-2) and MNM's post-update meta-objective (R8 C3 note, Eq. 5). No reinforcement heads.

**What survives clearing and restart.** Clearing: z is reset to its fixed initialization; W and theta persist. Restart: theta checkpoint and W tensor are written to disk, the process is killed, and both are reloaded; z is fresh. The evaluator records W's SHA-256 before and after the reload as an engineering check.

**Replay, tools, external records during a scored query.** None. L exists, is plain text, and is readable by the replay process during practice and by the evaluator, never by the model during scoring. This is the explicit answer to the concern about retrieval from logs being substituted for weight learning: the log is a teaching source and an audit trail, not a query-time resource.

**Contradictions and superseded teachings.** Recency wins. A later accepted sentence about the same (subject, relation) supersedes the earlier one; the writer is meta-trained on episodes containing corrections so that it uses the same key, and the delta rule then overwrites the old value in that key's rank-1 subspace (Schlag et al. decompose the step into a "write" and a "remove" of the value currently bound to that key, R5-delta-rule, C4 note, Eq. 23; DeltaNet: the update leaves d-1 subspaces intact, R5 extras, DeltaNet Sec 3.3). Queries about the old value are scored as errors ("old-answer rate"). The brief is right that the delta rule already supports same-key correction; decay is not required and is listed under "worth comparing."

**Data separation.** Four disjoint pools: (i) meta-training episodes: name pool P_train (1,200 of 1,600 syllable pairs), teaching/query templates T_train (8 of 12 per relation), relation compositions C_train (40 of 64 ordered pairs, used only in Contract C); (ii) writer/hyperparameter validation: fresh worlds, P_train names, T_val (2 templates); (iii) final test: fresh worlds, T_test (2 templates never used in training or validation), C_test (16 compositions); (iv) a held-out-name subset of the final test using P_test (200 names). The writer's reward is the query loss inside pool (i) only. The evaluator alone holds G.

### 2.3 Does this support "persistent weight learning" rather than an answer cache?

Partly, and the partition must be stated exactly.

- W is a parameter tensor by construction, and every intervention in Section 4 (removal, shuffle, swap, rollback) tests that W, not z or theta, carries the taught information. That establishes persistence in editable weights.
- What distinguishes a relational store from an answer cache is use under conditions the write could not anticipate: paraphrased queries on held-out templates, two-hop chains whose composition was never taught, and chains re-evaluated after an intermediate correction. These are Yao's Generalization and Portability (R1, Yao Sec 2 and 5.1) and Cohen's Compositionality I/II (R1, Cohen Sec 3). A cache of (query -> answer) pairs cannot pass the correction-then-chain test unless the writer recomputes every dependent at write time, which the ordering controls in Episode B defeat.
- What the evidence would not show: that theta learns anything after initial training. theta is frozen at teaching. So the supported claim is "persistent, composable, correctable memory in W," not "the network learns methods in its weights." I state this plainly in Section 6.

---

## 3. Four worked episodes

### 3.1 The world (shared by all episodes)

Per episode the generator samples 12 persons, 6 towns, 4 guilds, with names drawn without replacement from the pool. Relations: `lives_in` (person -> town), `works_for` (person -> guild), `based_in` (guild -> town), `mentor_of` (person -> person), `landlord_of` (person -> person), `rival_of` (guild -> guild). Attributes: `trade` (8 values), `badge` (6 colors). Every binding is fresh each episode. The answer vocabulary is {unknown} ∪ attribute values ∪ names; the decoder has a type head and two syllable heads; scoring is exact match on the full answer. "unknown" is the correct answer for queries about untaught facts and is trained during meta-training (15% of queries), so that confabulation is scorable and background practice cannot "discover" facts.

Meta-training episodes: N ∈ {4, ..., 16} teachings, a correction in 25% of episodes, queries posed only after the teaching prefix (24 per episode: 10 paraphrased single-hop, 6 two-hop, 4 post-correction, 4 untaught). Teaching and query templates are sampled independently, so the encoder must map "Tarvo works for Kelvane" and "Which guild employs Tarvo?" to the same (subject, relation) key. This is how paraphrase robustness is trained in without leaking test templates: T_test is never instantiated before the final test. Allen-Zhu and Li's finding that extraction requires diverse phrasings at storage time (R7-extraction-reversal, C1b, Sec 4.2) motivates the diversity; the held-out split is what makes the test honest.

Expected answers below are **evaluator-only** unless they appear in a teaching sentence.

### 3.2 Episode A: new fact, correction, interference, restart (milestone one)

Teaching (in order), z cleared before each query, no feedback:

1. T1: "Tarvo lives in Ostine."
2. Q1 (held-out template): "Which town is home to Tarvo?" Expected: **Ostine** (evaluator-only).
3. T2: "Tarvo has moved. Tarvo now lives in Rhode."
4. Q2: "Which town is home to Tarvo?" Expected: **Rhode**. Old-answer check: "Ostine" scored as a specific failure.
5. T3-T10, eight unrelated sentences, including two chosen to share tokens: "Melk lives in Ostine." (shares the object) and "Tarvo works for Kelvane." (shares the subject, different relation), plus six about other entities.
6. Q3: "Which town is home to Tarvo?" Expected: **Rhode**. Q4: "Which town is home to Melk?" Expected: **Ostine**. Q5: "Which guild employs Tarvo?" Expected: **Kelvane**. Q6 (untaught): "Who is Tarvo's mentor?" Expected: **unknown**.
7. Restart: save W, kill the process, reload theta and W, fresh z. Q7: "In what town does Tarvo reside?" (second held-out template) Expected: **Rhode**. Q8: "Which town is home to Melk?" Expected: **Ostine**.
8. Reported but not a pass criterion: reverse query "Who lives in Rhode?" Expected: **Tarvo**. A key -> value memory is directional by construction, and Berglund et al. find reversal fails under fine-tuning but works in context (R7, C3a Sec 2.1.2; C4 Appendix B.6); whether the writer should write both directions is a Section 5 comparison.

Feedback available: none. Simplest shortcut to rule out: the answer lives in z, not W. Ruled out by clearing z before every query and by the restart; also by the W-removal intervention (Section 4.3). Second shortcut: the binding was learned into theta. Ruled out by per-episode randomization; a model must be at "unknown"/chance on Q1 posed before T1 (the analogue of Santoro's chance-level first presentation, R4 extras, Santoro Sec 4.1).

### 3.3 Episode B: two-hop chain where the first retrieval determines the second (milestone one)

1. T1: "Tarvo works for Kelvane."
2. T2: "Kelvane is based in Ostine."
3. T3-T8: six unrelated sentences, including "Melk works for Sorrin." and "Sorrin is based in Rhode."
4. Q1: "In which town is Tarvo's employer based?" Expected: **Ostine**. Q2: "In which town is Melk's employer based?" Expected: **Rhode**.
5. T9 (correction to the intermediate fact): "Kelvane has relocated. Kelvane is now based in Vell."
6. Q3: "In which town is Tarvo's employer based?" Expected: **Vell**. Q4: "Where is Sorrin based?" Expected: **Rhode** (locality).
7. The same episode is also run with T1 and T2 in swapped order.

Why this requires workspace-conditioned retrieval [deduction]: the key for hop 2 is (Kelvane, based_in). "Kelvane" does not appear in the query; it exists only in the value retrieved at hop 1, which lands in z. If q_t = Q(x) as in the draft code, q_2 = q_1 and m_2 = m_1, so nothing retrieved after step 1 can depend on Kelvane; extra steps iterate on constant (x, m). With q_t = Q(x, z_t), z_2 carries Kelvane's code and can form the second key. This also imposes a representational requirement: the value written for T1 must be in the same code space the encoder uses for key-subjects, or the reasoner cannot reuse it as a key (Section 5).

Simplest shortcut to rule out: **write-time composition**. When T2 arrives, a writer that reads W could find "Tarvo -> Kelvane," compose, and store "Tarvo's employer's town = Ostine" under a direct key, making the query single-hop. Q3 defeats this: after T9 the cached composite is stale, and a correct "Vell" requires either query-time chaining or write-time recomputation of every dependent, which needs a reverse lookup (who works for Kelvane?) that a directional store cannot supply without extra writes. The swapped-order run defeats the symmetric variant. This is the MQuAKE logic that edits must propagate to "entailed consequences of the edited facts" (R1, MQuAKE Sec 1), scaled down to a setting where we can inspect W. Scoring: two-hop accuracy is reported both unconditionally and conditional on both single-hop facts being individually retrievable, so a chain failure is not confused with a storage failure.

### 3.4 Episode C: the strongest feasible method-learning example (bridge; not in milestone one)

Teaching:

1. T1 (a definition using a nonce relation word sampled per episode): "A patron of a person is the employer of that person's landlord."
2. T2: "Dara is Tarvo's landlord."
3. T3: "Dara works for Sorrin."
4. T4-T9: six unrelated sentences, including "Melk's landlord is Ilsa." and "Ilsa works for Kelvane."
5. Q1: "Who is Tarvo's patron?" Expected: **Sorrin**. Q2: "Who is Melk's patron?" Expected: **Kelvane**.
6. T10: "Dara has changed jobs. Dara now works for Kelvane."
7. Q3: "Who is Tarvo's patron?" Expected: **Kelvane**.
8. The definition is also taught after the facts (T1 moved to position 9) in a second run.

What is familiar at initial training and what is novel at evaluation, stated by split:

- Primitive operations: the six relations. **Familiar.**
- Program structure: a 2-chain "r2 of r1 of X." **Familiar** (meta-training contains definitions of this form).
- Composition: which ordered pair (r1, r2). **Novel**: C_train has 40 of the 64 ordered pairs; the 16 test pairs, including (landlord_of, works_for), never appear in any meta-training or validation episode.
- Nonce relation word ("patron"): drawn per episode from a pool of nonce words; the word-to-definition binding is **novel** every episode.
- Operands (names): from P_train (primary) or P_test (secondary split).
- Program length 3 ("the mentor of the employer of the landlord"): **not attempted** in the bridge; expected to fail, by analogy with the productivity failures reported for meta-learned systems on longer forms (R3-compositional, C5, Lake & Baroni 2023 Methods and Discussion). Report it as a diagnostic, not a target.

What this is and is not: it is composition of familiar operations under a stored definition. It is not acquisition of a new primitive, and it is not "fitting a parameter of a known operation" either, because the operation to run (which two relations, in which order) is read from W, not selected from x. In the brief's terms, it is the case where "a frozen reader interprets a newly stored program using existing computational machinery." Success demonstrates exactly that: W can hold a program token that sequences the reasoner's existing retrieval primitives. In Chollet's terms, the evaluation-time solution for a held-out pair is not the same program that fits the training pairs, so developer-aware generalization difficulty is non-zero, though small (R9-grokking-arc, extras, Chollet II.2.1).

Simplest shortcut to rule out: **task identification**, where the reasoner recognizes one of the 40 trained compositions instead of reading the definition. Ruled out by the held-out pairs, and by a control where the definition sentence is omitted (expected: "unknown"). Second shortcut: write-time expansion of the definition over all entities. Ruled out by teaching the definition first (nothing to expand yet) and by the correction Q3.

### 3.5 Episode D: background practice, with the origin of task and verification made explicit (milestone one, minimal form)

Setup: after Episode A-style teaching of 16 facts plus 16 further interfering writes, the model is left alone for a practice phase. No new messages arrive.

- Task origin: the practice scheduler (a fixed program, not the model) selects an entry from L, the audit log of accepted teaching strings, and generates a query with a train-template query generator. Selection prefers items whose last practice attempt failed or whose answer-confidence margin is lowest; confidence is used for selection only, never for acceptance, following Huang et al.'s finding that self-judged correctness is unreliable and that earlier positive results depended on oracle labels to stop the loop (R6-self-correction, C1, Sec 3.2).
- Verification origin: the checker compares the model's exact-match answer to the logged object for that entry and emits pass/fail. For self-posed two-hop queries, a fixed symbolic chain-checker resolves the chain over L. The signal is external to the model, in the spirit of Absolute Zero's code executor as "an unified source of verifiable feedback" (R6, C3, Abstract and Sec 3.1); the model never reads L directly.
- On fail: the replay process re-presents the logged teaching string through the ordinary teaching channel, and the writer performs a write. On pass: no write. Writes are gated by a checked outcome, never by a speculative thought.
- Exact strings: L contains "Tarvo lives in Rhode." Practice query: "Which town is home to Tarvo?" Model answers "Ostine" (interference damage). Checker: fail. Replay: "Tarvo lives in Rhode." Writer writes. Later scored query, z cleared: Expected **Rhode**.
- Negative control (must hold): the model is prompted with a self-generated claim not in L, e.g. it answers "Vell" to "Where does Ilsa live?" when Ilsa's residence was never taught. Checker: fail (no log entry; the expected answer is "unknown"). No write may occur; verified by W diff = 0 and by the later scored answer remaining **unknown**.

What this establishes: practice can repair interference damage using only an external record and a one-bit verifier, and cannot introduce facts that were never taught. What it does not establish: hypothesis testing or method discovery. That is a later extension (Section 5.3).

**Included in milestone one:** A, B, D. **Later extensions:** C, three-hop chains, reverse-direction writes as a default, held-out-name split as a pass criterion, practice over rules.

---

## 4. The smallest decisive evaluation

### 4.1 Positive controls, in the order they must pass

Adopted from the prior review's ladder (a lead, now specified):

- PC0, memory mechanics: one-hot keys and oracle values, no learning. Single-hop recall must be 100% for N ≤ d per bank and degrade beyond; this reproduces the d_dot bound of Schlag et al. (R5, C5, Sec 4.1) for this implementation. Failure = bug.
- PC1, learned encoder, template-matched teach and query (same template), oracle values: ≥ 95% at N = 16. Failure = encoder/key learning broken, not a memory result.
- PC2, learned encoder and writer, template-matched: ≥ 95% at N = 16.
- PC3, reasoner capability without W: the 16 teaching sentences are concatenated into the context (the in-context reference, analogous to Cohen's ICE and Yao's IKE, which were the best performers in their evaluations, R1 extras Cohen Sec 5.1-5.2; R1 C2 note), W disabled. Two-hop accuracy ≥ 80%. If PC3 fails, the reasoner cannot chain and a memory-based multi-hop failure is uninterpretable.

Only after PC0-PC3 pass does a negative result on the research tests count against the hypothesis.

### 4.2 Baselines

- **No-write causal control**: theta frozen, W fixed at its meta-trained initialization, z cleared. Expected ≤ 2% on taught facts and "unknown" on most queries. This has zero memory capacity; it is a causal control, not a capacity-matched comparison.
- **Byte-matched slot memory**: with the draft's 4 banks of 48x48 fp32, W is 36,864 bytes [deduction from the draft dimensions]; a slot store of (key, value) pairs in R^48 at 4 bytes per float holds 96 slots for the same bytes. Softmax retrieval over slots, same encoder, same reasoner, writer replaced by "append or overwrite nearest slot." This is the GRACE/Larimar-style comparator (R12-baselines, C2, C4).
- **kNN over stored teaching encodings**: the encoder's teaching vectors are stored verbatim (same byte cap) and the reasoner attends over them. This is the explicit "ordinary retrieval" baseline the brief wants made visible rather than hidden.
- **In-context reference (PC3)** as the ceiling.

Achieved recall capacity for each memory is measured, not assumed: the largest N at which paraphrased single-hop accuracy stays ≥ 95%, swept N ∈ {4, 8, 16, 32, 64}. Larimar's near-100% up to K = 512 slots then 82% at 1,024 is the shape to expect (R12, C3, Sec 5.4); Schlag et al. observed errors accumulating from about 60 associations at d = 64 (R5, C5 note, Sec 6.1.1).

### 4.3 Interventions on W

Each run on the same episodes, theta frozen, z cleared:

1. **Remove**: W set to its pre-teaching value. Expected: no-write levels.
2. **Shuffle**: rows of W permuted. Expected: no-write levels.
3. **Swap**: W from episode j used to answer episode i. Expected: no-write levels; any residual accuracy exposes a binding leak into theta.
4. **Rollback of one write**: subtract the recorded delta of one teaching. Expected: only that fact is lost; others unchanged within noise. This tests the rank-1 locality claim (R5 extras, DeltaNet Sec 3.3).
5. **Restart**: as in Episode A; outputs must be bit-identical with deterministic kernels (smoke test) and accuracy identical (result).

### 4.4 Paraphrase, interference, correction, restart tests

- Paraphrase: accuracy on T_test templates versus T_train templates, same facts. Threshold: T_test ≥ 90% at N = 16 and within 5 points of T_train. Larimar's gap between edit success (99.6) and paraphrase (88.4) on CounterFact (R12, C3 note, Table 2) is a reminder that this gap is where memories fail.
- Interference: GEM's accuracy-matrix protocol, re-scoring every earlier fact after each new write (R2-cl-metrics, extras, Lopez-Paz & Ranzato Sec 2). Threshold: mean signed change on the first 8 facts after 16 further writes ≥ -5 points.
- Correction: post-correction new-answer accuracy ≥ 90%; old-answer rate ≤ 5%; locality on same-subject other-relation facts and same-object other-subject facts within 5 points.
- Restart: as above.
- Two-hop: ≥ 80% conditional on both hops retrievable; correction-then-two-hop (Episode B, Q3) ≥ 75%. This is the decisive number.

### 4.5 Adaptive retrieval versus extra computation

A 2x2 with everything else held fixed (same theta size, same W, same training budget): key from x only versus key from (x, z_t); K = 1 versus K = 6 steps. Prediction [hypothesis]: single-hop is insensitive to the key source; two-hop and correction-then-two-hop pass only in the (x, z_t) cell, and adding steps to the x-only cell does not help. Diagnostic (not a score): ||m_{t+1} - m_t|| per step, which is identically zero in the x-only cell [deduction], and whether the argmax bank or slot changes between steps 1 and 2 in the (x, z_t) cell. The MemN2N finding that "more computational hops give improved performance" on supporting-fact tasks (R4, C5 note, Sukhbaatar Sec 4.3) is a precedent for the expectation, but there the hops re-attend over sentences in context, so it does not settle the weight-memory case.

### 4.6 Thresholds, uncertainty, stopping

- Units: 5 seeds x 200 final-test episodes per condition; per-episode accuracy averaged; Wilson 95% intervals on pooled queries and per-seed means reported side by side. A threshold is "met" only when the lower interval bound exceeds it.
- Meta-training stopping: stop when validation paraphrased single-hop accuracy improves by < 1 point across three consecutive checkpoints, or after six chained ten-minute runs, whichever first. Kirsch et al. report long loss plateaus in meta-training, which a memorize-first curriculum shortened (R13, extras, Kirsch Sec 4.3); the curriculum is permitted as long as the memorized bindings come from meta-training worlds only.
- Milestone stopping: declare success when all thresholds in 4.4 are met; declare a negative research result when PC0-PC3 pass and the correction-then-two-hop threshold is missed in the (x, z_t) / K = 6 cell across seeds; declare "undertrained or broken" when any positive control fails at budget exhaustion.

### 4.7 Damage measurement and clipping bias

Report new-learning benefit and old-knowledge damage separately, never as one net score. Damage is the signed paired difference on the same items, as in GEM's BWT, which is signed and can be positive (R2, C2, Lopez-Paz & Ranzato Sec 2, Eq. 3; Sec 3). A clipped statistic D = mean(max(0, before - after)) is positively biased under the null: for zero-mean Gaussian noise with standard deviation sigma, E[max(0, eps)] = sigma/sqrt(2 pi) [deduction]. Because the writer's training signal in this design is the differentiable query loss, no clipped damage term enters any reward; if a locality penalty is added later, use a signed KL or signed accuracy term as CaMeLS does (R8, extras, Hu Sec 3.2, Eq. 3). Also report the correct-to-incorrect and incorrect-to-correct flip counts, following Huang et al.'s analysis (R6, extras, Sec 3.3). If a maximum-over-history forgetting measure is wanted, use Chaudhry et al.'s Eq. 3 and say so (R2, C3), since it differs from BWT.

### 4.8 What is not demanded

Randomly corrupted teaching that carries no observable marker is not required to be detected; the contract states that accepted sentences are ground truth. Contradiction handling is recency-based and is tested by correction, not by the model judging truth.

### 4.9 Smoke test versus research result

Smoke: PC0-PC2 pass, gradients reach the writer, W changes on teaching and not on reading, restart reproduces outputs bit-for-bit. Research: PC3 plus the 4.4 thresholds plus the interventions in 4.3 plus the 2x2 in 4.5, on held-out templates and worlds, with intervals.

---

## 5. Architecture consequences

### 5.1 Required by this contract

- **Memory interface**: a key-value write and a differentiable read; the delta update as baseline; writes only through the writer; no write on read. Key normalization matters for the remove/write balance (R5, extras, Schlag Sec 4.2).
- **Workspace-conditioned retrieval**: q_t = Q(x, z_t). Required by Episodes B and C, not optional [deduction in 3.3].
- **Shared entity code space**: values written for person/guild objects must be the same codes the encoder produces for key-subjects, so a retrieved value can become the next key. Required by B.
- **Writer and its training signal**: writer inputs are x_teach, z_K, and m; output is (k, v, beta) with beta a learned sigmoid scalar (R5, C6, Schlag Sec 4.2, Eq. 21); trained by exact-match loss on post-write queries through the write. No oracle-answer embedding, no RL discrete heads. Corrections and untaught queries must appear in meta-training. A support loss (predict the taught object immediately after each write) is included by default given the ablation in Lake 2019 where removing it dropped accuracy from 99.95% to 5.43% (R3, C3 note, Table 2), with an ablation scheduled.
- **Stopping**: not required. Fixed K = 6 with accuracy reported per step. The draft's halting head is removed from milestone one.
- **Language interface**: syllable-level English with template families; exact-match answers from a closed vocabulary including "unknown."
- **Audit log L**: plain-text record of accepted teaching strings, available to replay and evaluator only.
- **Autonomous practice**: a scheduler and a checker over L, as in Episode D.

### 5.2 Worth comparing experimentally

- Gated decay alpha_t (R5, C3, Gated DeltaNet Eq. 10), noting the measured retention cost of decay (R5, extras, Gated DeltaNet Table 2).
- Bank count and routing from (x, z) versus a single bank.
- Slot memory versus matrix at equal bytes (Section 4.2).
- Bidirectional writes (subject-keyed and object-keyed) to address reverse queries (R7, extras, Berglund Sec 3).
- Deep (MLP) memory versus linear W, since a linear W is limited to linear key-to-value maps (R11, extras, Behrouz Sec 3.1); relevant mainly to Contract C.
- Learned halting (ACT with its tau sensitivity, R10-stopping, C1; PonderNet's KL prior, R10, C2; or a zero-shot convergence exit, R10, C3c) only after fixed-K results exist.
- Writer variants: fixed-rule, learned content only, learned key and content.

### 5.3 The bridge to reusable method learning, assessed honestly

Next experiment: Episode C at scale, with C_train/C_test held out and the nonce-word binding randomized. If it passes, W holds a program token and the frozen reasoner interprets it. The bridge beyond that is where I must be plain: what the reasoner can do with a stored program is bounded by the interpreter it was meta-trained to be. Kirsch et al.'s taxonomy separates task identification from general learning-to-learn (R13, C3), and Lake and Baroni state that MLC "does not automatically handle unpractised forms of generalization" (R3, C5, Discussion). A pass on Episode C therefore supports "composition of familiar primitives from a stored definition," and the next rung, primitives the interpreter was never trained on, has no route in this design that I can specify without inventing one. The bridge from A to C is strong; the bridge from C to primitive acquisition is weak, and I would not describe milestone one as being on a path to it.

---

## 6. Decision record

**Recommended first milestone, one sentence.** Meta-train a syllable-level encoder, a K = 6 recurrent reasoner with workspace-conditioned retrieval, and a delta-rule writer trained through post-write query loss on randomized fictional relational worlds, then show on held-out worlds, templates, and a process restart that facts written once into W survive paraphrase, unrelated interference, and correction, and that a corrected intermediate fact changes the answer to a two-hop chain, with theta frozen and z cleared.

**Exact claim success supports.** At N ≤ 16 facts per episode, a linear delta-rule memory written once per English sentence by a meta-trained writer stores relational facts that a frozen reasoner can retrieve under paraphrase, compose across two hops using retrieval keys formed from prior retrievals, correct in place, and recover after restart, with the information demonstrably carried by W (removal, shuffle, swap, rollback controls) and not by z, theta, or any external record available at query time.

**Strongest claim it would NOT support.** That the system learns procedures or methods; that theta learns anything after initial training; that the mechanism scales past the measured recall capacity; that it handles names never seen in meta-training; or that background practice discovers knowledge rather than repairing it. Persistence across restarts, useful background activity, and procedure learning remain three separate claims, and only the first, plus a narrow form of the second, would be established.

**Three most important unresolved risks.**
1. Meta-training may not leave the plateau within six chained runs, leaving positive controls unmet; the fallback is the fixed-rule writer, which weakens the writer-learning claim.
2. Two templates per relation in the final test may be too few to distinguish paraphrase robustness from template memorization; the interval widths in 4.6 are the guard, but a wider template pool costs authoring time.
3. The bridge to method learning is narrow: Episode C tests composition, and nothing in this design tests acquisition of a new primitive.

**Smallest observation that would change the recommendation.** If, in the first pilot, the held-out-composition test of Episode C passes at the same training budget as Episode B, facts-first was too conservative and Contract C should be milestone one. Conversely, if the byte-matched kNN-over-teaching-encodings baseline matches the W system on the correction-then-two-hop test, W is not doing anything that explicit retrieval does not, and I would move to Contract C immediately, where the content of memory must change the computation rather than supply an operand.