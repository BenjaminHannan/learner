# Teaching-to-test contract for the first milestone: procedures by instruction, stored in W, meta-trained

## Recommendation in brief

Teach the system an English definition of a new named procedure composed from primitives it already executes ("to zorp a list : flip it , then drop the first item ."). A meta-trained writer stores the definition in the persistent memory W. The workspace z is cleared, the process is optionally restarted, and the frozen reader is then scored on operands that did not exist at write time, on compositions of the new name with known operations and with other newly taught names, and on a reflection query ("what does zorp do ?"). The same machinery is used to teach named constants and one-hop aliases, which supplies the fact-recall, correction, interference, restart and multi-hop tests that the previous review asked for, at no extra architectural cost.

The claim this milestone can support, if it passes, is narrow and worth having: a differentiable write into W can hold a program over known primitives, bound to a novel name, such that a frozen reader applies it to unseen inputs after clearing and restart, and the order of retrieved items can depend on earlier retrievals. It does not support acquisition of new primitives, and I say below why no tiny-scale design can.

Everything below is a design. No experiment in this memo has been run.

---

## 1. Contract choice

### Three candidate contracts

**Contract F, facts first.** Teach "the mark of e5 is 3" style bindings; test recall after paraphrase, correction, interference and restart; later add multi-hop. This is the prior coordinator's recommendation.

**Contract D, demonstration-only induction.** Teach by three to five input-output pairs with no definition; the system must induce the program and store it; test on novel operands. This is the ARC-style format (R9-grokking-arc, extra: 3.3 demonstration examples per task on average, binary success on held-out test inputs) and the induction task in Absolute Zero (R6-self-correction, extra: held-out examples "discourage overfitting through if-else logic").

**Contract I, procedures by instruction.** Teach an English definition composing known primitives; store it in W; test on novel operands and novel compositions with the definition absent from context. This is the SCAN "add primitive" split (R3-compositional, C1) moved from context into weights: MLC and meta seq2seq keep the study examples in the input context and freeze weights (R3-compositional, C4: "On test episodes, the model weights are frozen"; extra: "no weight updates are made after the meta-training phase ceases"), whereas here the only channel from teaching to query is W.

### Scoring

| Criterion | F: facts first | D: demonstration induction | I: procedures by instruction |
|---|---|---|---|
| Meaningful evidence | Establishes memory management (correction, interference, restart). Success is fully explained by "store N numbers," as the brief notes. Nothing about method use. | If it works, strongest evidence. But a failure cannot be attributed: induction (search) and storage (write) fail together, and induction is the hard part on tiny nets. | Isolates storage and execution of a structured object from induction. The definition contains no answer; the query operands do not exist at write time, so nothing answer-shaped can be cached. Failure is attributable through the positive-control ladder in Section 4. |
| Feasibility (16 GB, ten-minute chained runs) | Highest. | Lowest: meta-learning an inducer over compositions is a search problem with no published tiny-scale precedent in the digest that also writes into weights. | Middle. Closest precedent: meta seq2seq trained on 10,000 episodes in under one hour on a Titan X (R3-compositional, C3), but in context, not in weights. My world is much smaller (6 primitives, depth 3). Hypothesis: several chained runs suffice; see Section 4. |
| Shortcut resistance | Low. The natural solution is the cache. | Medium. Novel operands block pair caching, but nearest-demonstration heuristics can pass partially. | High for answer caching (no answer exists at write time). Residual shortcut: storing an index into the set of training compositions. Ruled out by held-out composition classes (Tier 2 below). |
| Relevance to persistent reasoning and method learning | Persistence yes; methods no. | Highest for autonomous practice, since verification from examples is exactly what practice needs. | High for the language interface and for methods; the natural next step is D on the same reader and W, which cleanly isolates induction as the new capability. |

### Choice and assumptions

I choose Contract I, with F's tests folded in as Episodes A and B using the same writer and W. Reasons: (i) it is the only one of the three whose success cannot be explained by an answer cache and whose failure can be localised; (ii) it is feasible enough that a null result after the positive controls is interpretable; (iii) it is the shortest path to D.

Assumptions, labelled: (A1) the reader must be meta-trained on the definition template family; this milestone does not claim learning from unfamiliar instruction formats. (A2) Novel names are novel character strings over familiar characters, not new tokens; tokens never seen in meta-training are outside what meta-learned systems demonstrate (R3-compositional, extra: novel-operand limit). (A3) A primitive is "known" if the reader executes it on the query path at 99 percent or better without any memory.

Conditional recommendation: if positive controls PC1 and PC2 (Section 4) cannot be passed within six chained runs after one reader-width increase, the reader cannot execute programs retrieved from W at this scale, and the milestone should collapse to Contract F (Episode A alone) with the failed control reported.

On the facts-first route as a route: it is necessary machinery but a poor milestone target, because its pass criterion is met by the very shortcut the user wants excluded, and because the same tests cost nothing extra on procedure bindings. That is what the design below does.

---

## 2. Information boundaries

### The world (milestone one)

- Symbols: `a b c d e f g h`. Lists of length 3 to 5, written `[ c a f b ]`.
- Six primitives, each with two surface forms: `rev` ("reverse it" / "flip it"), `tail` ("drop the first item" / "remove the head"), `init` ("drop the last item" / "remove the end"), `rot` ("rotate it left" / "move the first item to the end"), `swap` ("swap the first two" / "exchange the first pair"), `dup` ("repeat the first item" / "double the head"). Primitives applied to the empty list return the empty list.
- Compositions: ordered sequences of 2 or 3 primitives (252 sequences). Each sequence's function table is computed on all 37,376 operands; sequences are grouped into functional equivalence classes; classes are assigned 70/10/20 to train / val-unseen / test-unseen. Constraint: every primitive appears in every slot position within the training classes.
- Names: strings of 4 to 6 lowercase letters in CVCV, CVCC, CVCVC, CVCCV patterns, fed to the encoder one character per token. Training names are sampled fresh per episode and logged. A pre-registered list of 200 test names is checked to be disjoint from, and at edit distance 2 or more from, every logged training name.
- Definition templates. Training: T1 `to NAME a list : P1 , then P2 , then P3 .`; T2 `NAME means P1 then P2 then P3 .`; T3 `define NAME as P1 followed by P2 followed by P3 .`; T4 `you NAME a list when you P1 and next P2 and next P3 .` Held out for paraphrase tests: T5 `NAME is : P1 ; after that P2 ; after that P3 .` (P3 omitted for depth-2 compositions.)
- Constants: `the list called NAME is [ a c f ] .` Aliases: `the twin of NAME1 is NAME2 .` (forward direction only; see Episode B on reversal.)
- Queries: `NAME [ list ]`; `P [ list ]`; `P then NAME [ list ]`; `NAME then P [ list ]`; `NAME1 then NAME2 [ list ]`; `P NAME` for a constant; `P the twin of NAME`; `what does NAME do ?` Outputs are eight slots over a 15-way vocabulary (8 symbols, 6 primitive tokens, PAD); metric is exact match, as in SCAN (R3-compositional, extra: deterministic outputs, exact-match accuracy).
- Operands: test operands never appear in any training query. Length-6 lists are a productivity probe, expected to fail (R3-compositional, C5: MLC "fails to handle longer output sequences"), and are a later extension.

### Components

Encoder `E_theta` (character/word GRU) produces `x`. Reasoner `F_theta` runs `T = 8` steps: `q_t = unit(Q_theta(x, z_t))`, `m_t = W q_t`, `z_{t+1} = F_theta(x, z_t, m_t)`, decoder `D_theta(x, z_T)`. Memory `W` is one 128 by 128 matrix (65,536 bytes in fp32). Writer `G_phi` maps `[x_teach, z_T^teach]` (the final workspace state after reading the teaching string; bounded to one vector, not a trajectory) to a unit key `k`, a content vector `v`, and a strength `beta in (0,1)`; the write is the fixed rule `W' = W + beta (v - W k) k^T`. The writer has no read access to W. Checker `C` is a deterministic syntactic validator at deployment. Replay `R` is an append-only audit log of accepted teaching strings and W snapshots. Evaluator `V` holds expected answers.

### Boundary table

| Component | Initial (meta-)training | Teaching / practice | Persistent write | Clearing temporary state | Scored inference | Evaluation |
|---|---|---|---|---|---|---|
| Encoder `E_theta` | Sees generated episodes (teach string, query, executor answer). `theta` updated by outer loop. | Sees teaching string. No change. | Idle. | Token states discarded. | Sees query string only. Frozen. | Idle. |
| Reasoner `F_theta`, `Q_theta`, `D_theta` | Reads episode-local W; `theta` updated. W is reset per episode (as TTT's `W_0` shared across sequences, R11-ttt-titans-hopfield, C1; MNM tabula rasa per episode, R8-learned-writers, extra). | Reads teaching string to produce `z_T^teach`. Frozen. | Idle. | `z <- z_0` (fixed). | Reads W at every step; frozen; no write. | Idle. |
| Writer `G_phi` | Sees `[x_teach, z_T^teach]`; `phi` updated through post-write query loss and reflection loss (bi-level, as CaMeLS R8-learned-writers, C1, and MNM R8, C3). Never sees the query. | Sees `[x_teach, z_T^teach]` only. Frozen. | Emits `(k, v, beta)`; delta rule applied to W. | Nothing. | Disabled. | Idle. |
| Checker `C` | Not used. | Syntactic validity of the teaching string (pass/fail, no content). In practice (Ep. D): external executor plus log. | Gates whether the write happens. | Nothing. | Absent. | Idle. |
| Replay `R` | Not used. | Appends accepted teaching string; snapshot of W before write. | Snapshot after write. | Survives. | Unavailable to the model. | Supplies snapshots for rollback and swap interventions. |
| Evaluator `V` | Computes training answers with the executor (these are training labels, not evaluation). | Idle. | Idle. | Idle. | Sends query string; receives output. | Exact match against evaluator-only answers. Runs interventions on W copies. |

**Which weights change.** `theta`, `phi` change only in initial training. `W` changes only at the persistent write. Nothing changes in clearing, scored inference or evaluation.

**What survives.** Clearing: `theta`, `phi`, `W`. Restart: the same three, reloaded from disk; `z` is re-initialised; the process is new. "Clear only" and "restart" must give identical outputs; a difference is a hidden-state bug (optimizer state, RNG, caches), not a result.

**Feedback format.** Definitions and constants receive no feedback beyond the validity gate. Corrections are new teaching strings; the natural prefix `correction :` is allowed but not required. Policy: the latest accepted teaching for a name supersedes; the delta rule overwrites the same key (R5-delta-rule, C4: the delta rule "learns to correct the current key to value association"). No feedback ever reveals the answer to a scored query. In Episode D, practice feedback is pass/fail from an external executor, with an explicitly separate answer-revealing variant.

**Availability during a scored query.** No replay, no log, no tools, no executor, no teaching text. Only `theta`, `phi` (disabled), `W`, and the query string.

**Data separation.** Pool 1: meta-training episodes (training composition classes, generated names, templates T1-T4, training operands). Pool 2: writer/reader validation (training classes, fresh names, fresh operands) for early stopping and hyperparameters. Pool 3: val-unseen classes, used once to pick the final checkpoint. Pool 4: test-unseen classes, test names, test operands, template T5, touched once at the end.

### Cache or weight learning?

W is a parameter store; the question is whether what it stores is an answer or a function. Three features make the answer-cache explanation unavailable: the query operands are absent at write time (as in CaMeLS, R8-learned-writers, extra: "we do not have access to Q_test" when updating); the same stored item must produce different correct outputs across hundreds of operands; and the content-swap intervention (Section 4) shows the output is determined by W's content. Persistence is a separate claim, tested by the restart protocol, not inferred from the architecture.

---

## 3. Four worked episodes

Expected answers are evaluator-only unless marked as teaching.

### Episode C (core, milestone one): a new procedure by definition

**Familiar in initial training.** The six primitives and their twelve surface forms; the composition grammar (ordered depth 2-3); the operand alphabet and lengths 3-5; templates T1-T4; the query grammar; the act of binding a fresh name to a composition (names were re-sampled every episode, as MANN shuffles labels per episode so bindings cannot live in weights, R4-mann-babi, C2, and as meta seq2seq re-assigns primitive meanings per episode, R3-compositional, C3).

**Novel at test.** The name string; the binding of that name to this composition; the composition's function class (Tier 2); the operands; the compositions of the new name with known primitives and with other new names; the template (T5 variant).

| Level | Novel | Familiar | Achievement, in the brief's terms |
|---|---|---|---|
| Tier 0 | name, operands | composition class seen in training | binding only; comparable to Kirsch's "task identification" (R13-icl-vs-weights, extra) |
| Tier 1 | name, operands, composition with known primitive at query time | composition class | composing familiar operations at query time |
| Tier 2 | name, operands, composition class never seen as a function | primitives, slot structure, depth | composing familiar operations in an unseen order, stored in W |
| Not tested | a new primitive | | acquiring a new procedure; see Section 5 on why the bridge is weak |

Teaching (test name `zorp`, composition `rev, tail`, assumed in a test-unseen class):

```
to zorp a list : flip it , then drop the first item .
```

Feedback: none (validity gate passes silently). The writer sees the encoded string and `z_T^teach`. W is written. `z` is cleared. Optionally restart.

Held-out queries and expected answers:

- `zorp [ c a f b ]` → `[ f a c ]`
- `zorp [ h h d a g ]` → `[ a d h h ]`
- `zorp then rotate it left [ c a f b ]` → `[ a c f ]` (Tier 1)
- `double the head then zorp [ d b e ]` → `[ b d d ]` (Tier 1)
- `what does zorp do ?` → `rev tail` (reflection; this answer is present in the teaching, which is legitimate)

Second definition written into the same W (interference and composition):

```
to vask a list : rotate it left , then swap the first two .
```

- `zorp then vask [ c a f b ]` → `[ c a f ]`
- `vask then zorp [ c a f b ]` → `[ b a f ]` (order-sensitive; distinguishes execution from set membership)
- `zorp [ c a f b ]` → `[ f a c ]` (re-scored after the second write)

Paraphrase (held-out template T5, fresh name):

```
blim is : reverse it ; after that remove the head .
```

- `blim [ c a f b ]` → `[ f a c ]`

**Simplest shortcut to rule out.** The writer stores an index into the training composition classes and the reader executes the nearest training class. Signature: Tier 0 passes, Tier 2 sits at the nearest-neighbour rate (computed offline by mapping each test class to its most output-similar training class). Second shortcut: the definition leaks through `z`; ruled out by clearing, restart and the no-write control.

### Episode A (milestone one): constant, correction, interference, restart

Teaching 1: `the list called blick is [ a c f ] .`
Queries: `blick` → `[ a c f ]`; `flip it blick` → `[ f c a ]`.

Teaching 2 (correction): `correction : the list called blick is [ a c g ] .` Also run without the prefix.
Queries: `blick` → `[ a c g ]`; `flip it blick` → `[ g c a ]`.

Interference: eight unrelated teachings (four constants, four definitions with other names, e.g. `the list called frap is [ h b ] .`, `to nulm a list : remove the end , then flip it .`).
Queries: `blick` → `[ a c g ]` (must survive); `frap` → `[ h b ]`; `nulm [ a b c ]` → `[ b a ]`.

Restart: serialize W; kill the process; start a new process (optionally on the other machine); load `theta`, `phi`, W; fresh `z`.
Queries: `blick` → `[ a c g ]`; `flip it blick` → `[ g c a ]`; `frap` → `[ h b ]`.

**Shortcut.** This episode is expected to be solvable by a cache; its purpose is memory management, not method evidence. The shortcut to rule out is a hidden channel other than W surviving "restart": verified by the clear-only equals restart check and by zeroing W after restart (must drop to chance). Delta-rule interference is quantifiable: for a write with strength `beta` on key `k`, the change to the read at another key `k'` is `beta (v - W k)(k^T k')` (deduction from the update rule, which is one SGD step on `1/2 ||W k - v||^2`, R5-delta-rule, C1). With random unit keys in 128 dimensions the RMS overlap is `1/sqrt(128) = 0.088` (deduction). The interference test measures whether learned keys do better or worse than that.

### Episode B (milestone one): a retrieval that determines the next retrieval

Teaching, in this order, with the writer blind to W so no write-time precomputation is possible:

1. `the twin of blick is frim .`
2. `the list called frim is [ b d a h ] .`
3. `the list called blick is [ g g e ] .` (distractor: a constant-key lookup on `blick` returns the wrong list)

Queries:

- `flip it the twin of blick` → `[ h a d b ]` (two retrievals: twin of blick, then frim's list)
- `flip it blick` → `[ e g g ]` (control: own list, not the twin's)
- `zorp the twin of blick` → `[ a d b ]` (three retrievals, with `zorp` from Episode C; stretch within milestone one)
- `the twin of frim` is not asked in milestone one. A delta memory is directional by construction, and Berglund et al. found fine-tuned models near 0 percent on reversed facts while in-context reversal was near 100 percent (R7-extraction-reversal, C3a, C4; extra: Meng et al.'s edits "not bidirectional"). A reverse-direction split is a later extension requiring an explicit both-direction write policy.

**Shortcut.** Write-time propagation: at teaching 2, a writer with read access could look up "blick's twin is frim" and also write the list under a `blick+twin` key. Excluded by the writer's no-read boundary and checked by running the teaching in both orders. A second shortcut is a superposed single read (constant key returning a mixture); the constant-key control in Section 4 measures it. The published analogue: parameter-editing methods reach 96 percent single-hop but 7 percent multi-hop on MQuAKE-cf (R1-editing-eval, C3b), while MeLLo succeeds by retrieving iteratively per sub-question (R1, C4). Episode B is the in-weights version of that iteration.

### Episode D (later extension, minimal form specified): background practice

Task origin: the practice loop samples a name from the audit log's name index (an external record, available in practice only), samples a random operand list, and answers from the W path. Verification origin: an external executor runs the logged definition text on the operand and returns pass/fail. The model's own confidence is never a verifier; Huang et al. found intrinsic self-correction without external feedback deteriorates and that reported gains came from oracle labels deciding when to stop (R6-self-correction, C1; extra: keep ground truth out of the stop/accept decision). The executor is the analogue of Absolute Zero's code executor as "an unified source of verifiable feedback" (R6, C3).

Two feedback contracts, run separately: D-pf (pass/fail only; on fail the writer may re-write from the logged teaching string, which is answer-revealing about the definition but not about any scored query) and D-none (no practice; control). Practice cannot create definitions; it can only re-encode accepted ones.

Example: log contains `zorp`, `vask`, `nulm`. Practice draws `nulm`, operand `[ d a c e ]`, answers `[ c a d ]` (wrong; correct is `init` → `[ d a c ]`, `rev` → `[ c a d ]`, so actually correct). The evaluator-only question is not this instance but the before/after comparison: scored accuracy on practiced names versus unpracticed names, and signed damage to unpracticed names.

**Shortcut.** Practice silently becomes retrieval from the log. The boundary makes it explicit: the log is used only inside practice; scored inference has no log; the claim is about W after practice.

---

## 4. The smallest decisive evaluation

### Smoke test versus research result

Engineering smoke test S0: one chained run trains end to end; training loss falls; primitive-only queries (`flip it [ a b c ]` → `[ c b a ]`) reach 99 percent on validation. S0 says the code works and says nothing about memory.

The research result is the battery below, run only after the positive-control ladder passes.

### Positive-control ladder (separating "reader cannot execute" from "writer cannot store")

- **PC1, in-context ceiling.** An architecture-matched reader trained with the definition concatenated to the query (MLC-style, no W). Must reach 95 percent exact match on Tier 2 validation. If it fails, the reader is undertrained or too small; nothing about memory is learned. This is a separate run, not the main system, because jointly training an in-context mode risks the reader ignoring W; Chan et al. report in-context and in-weights learning trade off and that models "were unable to achieve both simultaneously" (R13-icl-vs-weights, C1).
- **PC2, oracle key and oracle content.** One-hot key per name; content = the encoder's pooled representation of the definition, written by hand; reader trained on this. Must reach 95 percent on Tier 0 validation. If PC1 passes and PC2 fails, the read path (retrieval into `z` and execution of retrieved code) is broken, not the writer.
- **PC3, learned key, oracle content.** Tests key discrimination among 64 stored names. Threshold 90 percent.
- **PC4, learned writer, Tier 0.** The full system on training classes with fresh names and operands. Threshold 90 percent. If PC1-PC3 pass and PC4 fails, the writer is undertrained; consider the memorize-first curriculum below before concluding anything.
- **PC-B, chain with oracle keys and values.** Alias and constant written with one-hot keys and oracle content; the reader must chain. Threshold 90 percent. Isolates whether `Q_theta(x, z_t)` can form the second key from a retrieved name code.

The 95 percent figure follows the bAbI convention, which its authors call arbitrary (R4-mann-babi, extra). It is a pre-registration device, not a claim about significance.

### Strong simple baseline and no-write causal control

- **Retrieve-then-execute reference.** Store the verbatim definition string in an external record; at query time, retrieve it by name and feed it to the PC1 in-context reader. This is the ordinary retrieval the user does not want substituted silently, used here explicitly as an upper reference. The system's Tier 2 accuracy relative to this reference measures what the W channel loses.
- **No-write control.** `theta`, `phi` frozen; `z` reset to the same `z_0`; W left at its meta-trained initial value. Expected: chance on all name queries, 99 percent on primitive-only queries. This has zero memory capacity, so it is a baseline, not a capacity-matched control.
- **Nearest-training-class predictor.** For each Tier 2 class, output the most output-similar training class's result. This is the index-shortcut rate that Tier 2 must exceed.

### Interventions on W (all with frozen `theta`, `phi`, fixed `z_0`)

1. Zero W → chance on name queries.
2. Rollback to the pre-write snapshot → chance on the new name; unchanged on earlier names.
3. Content swap: write `vask`'s definition under `zorp`'s key → `zorp [ c a f b ]` must return `vask`'s answer `[ a c f ]`... specifically `rot` then `swap` on `[ c a f b ]` gives `[ f a b c ]`... the expected answer is the swapped program's output, which is the decisive test that W content determines the answer.
4. Random orthogonal rotation of W → chance (key alignment destroyed).
5. Shuffle: permute the stored items' keys among names → answers follow the keys, not the names.

Outcome 3 is the one that discriminates "W carries the program" from "W carries a trigger that the reader completes from `theta`."

### Paraphrase, interference, correction, restart

- Paraphrase: T5 teaching template and the alternate surface forms, scored separately from T1-T4. Larimar loses about 11 points between edit success and paraphrase on CounterFact even with an external memory (R12-baselines, extra), so paraphrase is reported as its own number.
- Interference: after each additional write, re-score all earlier names, building the full accuracy matrix R of GEM (R2-cl-metrics, extra) with writes as "tasks."
- Correction: redefine a name; score new answer, and re-score all other names (Yao et al.'s locality, R1-editing-eval, C1a). Also score the "distract neighbourhood" case where a corrected name appears in the same query as an unrelated one, since editing methods "generally perform poorly in Distract-Neighbor settings" (R1, extra).
- Restart: as in Episode A, including the clear-only equals restart identity check.

### Adaptive retrieval versus extra computation

Minimum comparison, on Episode B two-hop queries, same `theta` size, same training budget, five seeds each:

- (a) `q_t = Q(x, z_t)`, `T = 8`.
- (b) `q_t = Q(x)` (the draft code's constant retrieval), `T = 8`.
- (c) `q_t = Q(x)`, `T = 16`.

Prediction (hypothesis): (a) passes two-hop; (b) and (c) fail equally, because a constant key cannot select the second item and extra steps on a constant `(x, m)` are fixed-point iteration on the same information. If (c) beats (b), extra compute on a constant read is doing work and the brief's caution applies: a constant read prevents re-querying but does not make recurrent computation useless. If (a) equals (b), workspace-conditioned retrieval is not doing what the loop is designed for, and the loop should not be advertised.

### Fair capacity comparison

Bytes: W is 65,536 bytes fp32. The byte-matched alternative is a slot memory with 64 slots of (128-d key, 128-d value) and softmax retrieval (GRACE- and Larimar-like, R12-baselines, C4, C2). Achieved recall capacity `N*`: sweep N in {1, 2, 4, 8, 16, 32, 64, 96, 128} stored definitions; `N*` is the largest N at which Tier 0 accuracy over all N names stays at or above 90 percent. Report both numbers for both memories. Calibration points: a linear memory with 128-d keys cannot hold more than 128 interference-free associations (R5-delta-rule, C5: "storing more than d_dot associations will result in a retrieval error"); Larimar's least-squares memory held near 100 percent up to K = 512 edits and 82 percent at 1,024 (R12-baselines, C3). Also report Chaudhry's pair, forgetting and intransigence, since high negative correlation between them indicates saturated capacity (R2-cl-metrics, extra).

### Thresholds, uncertainty, stopping

| Measurement | Cells | Threshold | Reading |
|---|---|---|---|
| PC1-PC4, PC-B | 500 queries each | as above | gates |
| Tier 2, fresh names, T1-T4 | 500 | at or above 80 percent, and at least 3 times the nearest-class rate | main result |
| Tier 1 compositions with known primitive | 500 | at or above 80 percent | |
| Two-name compositions | 500 | at or above 70 percent | |
| Paraphrase T5 | 500 | within 10 points of T1-T4 | |
| Two-hop (a) vs (b),(c) | 500 each | (a) minus max(b, c) at least 20 points, same sign on 5 of 5 seeds | adaptive-retrieval claim |
| Restart | 500 | identical to clear-only (0 discrepancies) and within 2 points of pre-restart | persistence claim |
| Signed damage per write | all prior names | mean signed change no worse than minus 2 points per write over 32 writes | locality |

Uncertainty: with

n = 500 per cell, the 95 percent binomial half-width is about 2.6 points at p = 0.9 and 4.4 points at p = 0.5 (deduction). Five seeds per condition; report every seed and the mean with standard deviation. Between-seed spread larger than the within-cell interval means the result is seed-dominated and should not be summarised by a mean. For the paired two-hop comparison, all five seeds ordered the same way gives a one-sided sign-test p of 1/32 (deduction), which is the minimum I would accept alongside the 20-point gap.

Training stopping: a chained sequence stops when Pool 2 exact match has not improved by more than 0.5 points across three evaluations spaced 1,000 steps apart, or at 12 chained ten-minute runs per seed, whichever comes first. Kirsch et al. report long meta-optimisation plateaus and that biasing the task distribution toward a fixed subset "enables a smooth path from memorizing to learning" (R13-icl-vs-weights, extra); so the curriculum starts with 16 fixed names for the first two runs and then opens the name generator. Budget, as a hypothesis: five seeds times 12 runs is 10 GPU-hours for the main system, roughly 40 GPU-hours including PC1, the constant-key ablations and the slot-memory comparison. Storage is a few hundred megabytes of checkpoints, far inside the budget.

Project stopping: if PC1 fails after six chained runs, widen the reader once (hidden 256 to 512) and retry; if it fails again, stop and report that the reader cannot execute depth-3 programs at this scale. If PC2 fails with PC1 passing, stop and report the read path as the blocker.

### What counts against the hypothesis, and what indicates a broken component

| Observation | Interpretation |
|---|---|
| PC1 fails | Reader undertrained or too small. No memory claim possible. |
| PC1 passes, PC2 fails | Read-and-execute path broken. Not evidence about writers or W. |
| PC1-PC3 pass, PC4 fails after curriculum | Writer training failed. Component problem, but a real risk for learned writers at this scale. |
| PC4 passes, Tier 2 at the nearest-class rate | Counts against the hypothesis that W holds a compositional code; W holds an index. |
| Tier 2 passes, content swap does not move the answer | Counts against "W carries the program"; the reader completes from `theta`. |
| Tier 2 passes, restart differs from clear-only | Hidden channel; bug. |
| Two-hop: (a) equals (b) | Counts against the adaptive-retrieval design. |
| Two-hop: (c) beats (b) | Extra computation on a constant read helps; report it as such. |
| Signed damage large and negative on unrelated names | Counts against delta-rule locality with learned keys; compare slot memory. |

### New-learning benefit and old-knowledge damage, and the clipping bias

Report separately: benefit = accuracy on the new name's 500 queries after the write minus before (before is chance); damage = signed mean change on all previously stored names' probes, GEM-style backward transfer (R2-cl-metrics, C1, C2: a signed average, and positive backward transfer is allowed), plus Chaudhry's max-based forgetting as a secondary since it captures the process rather than the endpoint (R2, C3).

The draft's damage statistic clips at zero, `D = mean(max(0, before - after))`. Under the null of no true damage with per-probe noise of standard deviation `sigma`, `E[max(0, eps)] = sigma / sqrt(2 pi)` for Gaussian noise (deduction), so a clipped statistic reports damage that is not there. Treatment: use the signed version; if a clipped version is kept for a reward, subtract the sham-write null obtained by writing a definition for an unused name and measuring the same statistic on the same probes. No corruption-detection test is included: a syntactically valid but wrong definition is indistinguishable from a right one at write time, and the brief rightly says not to demand detection without observable evidence.

---

## 5. Architecture consequences

### Required by this contract

- **Memory interface.** An associative read at every reasoner step with the key formed from `(x, z_t)`; a write keyed by the taught name and blind to W; same-key overwrite for supersession. The delta rule provides the last (R5-delta-rule, C4) and its locality is exactly one rank-1 subspace per write (R5, extra), which is what the interference test measures.
- **Workspace-conditioned retrieval.** Required by Episode B, not by Episode C alone; that is why B is in milestone one. The draft's input-only key makes B impossible by construction.
- **Writer and its signal.** A differentiable writer trained by the post-write query loss plus a reflection loss on `what does NAME do ?`. The reflection loss is the in-weights analogue of the support loss without which meta seq2seq dropped from 99.95 to 5.43 percent (R3-compositional, C3). No oracle answer input, no RL heads, no discrete sampling: with the definition contract there is no answer to feed the writer, which removes the "write the label" degeneracy the review found. A learned scalar strength follows Schlag et al. (R5-delta-rule, C6).
- **Stopping.** Fixed `T = 8` in milestone one. Learned halting introduces a confound (ACT's behaviour is "quite sensitive" to its penalty, R10-stopping, C1; expected-time penalties can be gamed, R10, extra) that would contaminate the compute-versus-retrieval comparison.
- **Language interface.** Controlled English of about 60 word types, character-level names, a template family. Chat is not required.
- **Autonomous practice.** Nothing required in milestone one. Episode D requires the audit log and an executor as explicit practice-time tools, absent at scoring.

### Worth comparing experimentally

- Delta bank versus byte-matched slot memory (Section 4).
- Decay gate versus none: gating clears memory but "decay hurts memory retention" in the S-NIAH case study (R5-delta-rule, extra); Titans' gate can clear the whole memory or leave it untouched (R11-ttt-titans-hopfield, extra). Not needed for correction, which the delta rule already handles.
- Learned versus zero `W_0` (TTT reports learning `W_0` "significantly improves training stability," R11, extra).
- One bank versus the draft's four banks with a router; the router is a module without a requirement behind it.
- Random versus zero `z_0` with input injection (R10-stopping, C4).
- Recurrent-depth's successive-step divergence exit rule as a later zero-shot stopping candidate (R10, C3c), after the fixed-`T` results exist.

### The bridge to reusable method learning, stated plainly

What a pass demonstrates: a frozen reader can realise a program it has never executed in that order, on inputs it has never seen, from a description stored in W by a one-shot write, and can chain retrievals. In the brief's taxonomy this is composing familiar operations bound to a novel name, not acquiring a new procedure. The next experiment is Contract D on the same reader and W: replace the definition with three input-output pairs, so the only new capability is induction. If milestone one passes, that experiment is well-posed. If Tier 2 fails, W holds indices and the bridge is not there.

The larger ambition, a genuinely new primitive, is weak at this scale and I say so. Seq2seq gets 1.2 percent on SCAN's held-out primitive (R3-compositional, C1); meta seq2seq and MLC solve it (R3, C3, C4), but their "new" primitive maps a new word to an output action that already exists in the output vocabulary, which is the level of this milestone, not beyond it. Grokking shows new operations being fit by gradient descent over up to a million steps (R9-grokking-arc, C1), which is parameter fitting, not a write. Chollet's benchmark rule, that a task answerable by the same program that fits the teaching set has zero developer-aware generalisation difficulty (R9, extra), is the standard to hold later milestones to.

---

## 6. Decision record

**Recommended first milestone.** Meta-train a writer and reader so that an English definition of a new procedure over six known list primitives, written once into a 128 by 128 delta memory, is executed by the frozen reader on unseen operands, in unseen compositions, after clearing and restart, alongside constant and alias teachings that supply correction, interference and two-hop tests.

**Claim a pass supports.** A one-shot differentiable write into W can persist a program over known primitives, bound to a novel name, that survives clearing and restart and is applied by computation to inputs absent at write time; and retrieval order can depend on prior retrievals.

**Strongest claim it would not support.** That the system acquires new procedures. The primitives, the depth, the slot structure and the definition format were all meta-trained; no new primitive, no unfamiliar format, no longer program, and no learning without prior meta-training on this exact contract.

**Three unresolved risks.** (1) The writer collapses to an index over training classes; Tier 2 is the only detector and it may be noisy at 42 test classes. (2) The reader executes programs only from context and PC2 fails, meaning the in-weights channel is unusable at this scale and the milestone falls back to Contract F. (3) Meta-training does not converge within the chained budget; a null result then says nothing, which the positive-control ladder mitigates but does not remove.

**Smallest observation that would change the recommendation.** PC2 failing while PC1 passes on all five seeds after the width increase. That would show the read-and-execute path, not the writer, is the bottleneck, and the right first milestone would then be Contract F with a reader-side investigation, not a procedure contract.