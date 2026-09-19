# Teaching-to-test contract for a tiny persistent-memory reasoner

Proposal from the "architecture-agnostic skeptic" seat. Everything cited is from the verified evidence digest (source id, item, location). Statements marked (deduction) are mathematics; statements marked (hypothesis) are mine and untested.

## Recommendation up front

Adopt the **Cleared-Context Binding Contract (CCB)** for milestone one. Each episode samples a fresh world; teaching is English declarative sentences (facts) or a short demonstration block (procedures) that legitimately contain the taught answer; the only feedback is a fixed, non-learned grammar gate that accepts or rejects a teaching and flags it as a correction; after teaching, the workspace z is hard-reset, (θ, W) is serialised, the process is restarted with the audit log unmounted, and the system is scored on queries that use different wording from the teaching, that need a taught binding as the key for a second retrieval, that need the later of two conflicting teachings, and, for procedures, that need a demonstration-induced composition of familiar primitives executed on operands never demonstrated.

The contract is deliberately substrate-neutral so that three memories can be raced under identical encoder, reasoner, key/value/query projections and outer loss, differing only in the storage object and its write rule: (i) a linear delta-rule bank, (ii) a slot memory whose slots are parameters with softmax reads, (iii) plain gradient steps on a designated small MLP with replay from the audit log (log available at teaching, never at scoring). They are matched at 9,216 writable float32 values (36,864 bytes) and additionally compared on achieved recall capacity N95.

I reject two things in the draft: the RL writer heads with an oracle checker, and "facts on a fixed world" as the first milestone. With fixed bindings a weight-fitting strategy and a memory strategy give identical answers, so the test is ambiguous by design (R13-icl-vs-weights, extra 2). I also assess the prior coordinator's facts-first route: facts-first is a useful route only if the same contract forces the stored binding to be *used* (as a key, in reverse, in a composition, as a program pointer). Verbatim recall alone is an answer cache, whatever substrate holds it.

---

## 1. Contract choice

Three contracts were compared.

| | A. Fixed-world facts, oracle checker (draft) | B. Cleared-Context Binding Contract (recommended) | C. Novel-primitive induction, pass/fail feedback only |
|---|---|---|---|
| Teaching | Question family + answer revealed by checker | Declarative sentence or 4-demo block containing the answer; per-episode random bindings | Demo block for an operation outside any known program space |
| Feedback | Oracle always reveals correct answer | Grammar accept/reject + correction flag; no answers from the checker | Pass/fail on the model's own attempts |
| Test | Same 24 entities, two templates | Disjoint query wording, 2-hop, reversal, correction after restart, held-out compositions on novel operands | Novel operands of the new operation |
| Meaningful evidence | Low: 24 stored numbers + decoder arithmetic (project context) | High: maps onto Reliability/Generalization/Locality (R1-editing-eval, C1a, Sec 2), Portability incl. reversed relation and one-hop (R1, C1b, Sec 5.1), multi-hop-after-edit (R1, C3a) | Highest, if it worked |
| Feasibility (10-min runs) | High | Medium: episodic meta-training; MLC-scale runs used 100,000 episodes on a 1.4M-parameter model, wall-clock not stated (R3-compositional, C4, Methods) | Low: pass/fail-only supervision on an open program space; both Lake papers fail on unpractised forms (R3, C5) |
| Shortcut resistance | Poor: bindings constant across episodes, so θ can hold them (R13, extra 2) | Good: per-episode re-randomisation prevents sample-class bindings in weights (R4-mann-babi, C2, Sec 2; R3, extra 2) | Good but unmeasurable if nothing passes |
| Relevance to method learning | None | Partial: procedures as program selection + persistent storage + execution | Full |

Choice: **B**. It is the only one of the three that yields interpretable evidence inside the budget while keeping a non-trivial method component. The composition level has published precedent for separating memorisation from systematic recombination: basic seq2seq has 51.13% error on SCAN "around right" while MLC has 0.04% (R3, C4, Table 2), and standard seq2seq scores near zero on "add jump" (R3, C1). I use that split shape, not those systems, because both Lake papers are in-context precedents that make no weight updates after meta-training (R3, extra 1).

Why A cannot be salvaged by swapping an index for a sentence: the world's bindings are constant, so they can be fit into θ during any training that touches them (R13-icl-vs-weights, C1, Sec 3.1: greater burstiness trades off against weight-based learning, and models drift toward in-weights learning with repetition, extra 2). The oracle checker makes "write the revealed label" the optimal writer policy (deduction: if every accepted teaching should be stored and the label is supplied, the skip head has no information to act on).

Why C is premature: with a frozen reader, a genuinely new primitive can only be represented if W holds executable structure rather than a pointer into θ's program space. Nothing in the evidence shows a one-shot writer doing that; the closest precedent, Metalearned Neural Memory, meta-trains a feed-forward memory with learned local update rules (R8-learned-writers, C3, Secs 3.2-3.4), which is a larger project than milestone one.

Labelled assumptions. A1: ten-minute runs are chained through checkpoints (coordinator's operational note). A2: the token vocabulary is shared between meta-training and test; only bindings, compositions and template phrasings are held out, because novel tokens are outside what the meta-learning precedents demonstrate (R3, extra 4). A3: milestone one's "method" is a novel composition of familiar primitives, not a new primitive. Conditional recommendation: if A3 is rejected, the contract must change to one where W is itself executed (MNM-style feed-forward memory, R8, C3), and CCB should still be run first as the positive control for the reader and writer.

---

## 2. Information boundaries

Shared skeleton for all three substrates: encoder E_θ (token GRU or 2-layer transformer, x ∈ R^48); reasoner F_θ with T = 6 fixed steps, z_{t+1} = F_θ(x, z_t, m_t), q_t = unit(Q_θ(x, z_t)), m_t = M_W(q_t); key/value projections K_θ, V_θ shared across substrates; decoder D_θ(x, z_T) emitting one answer token (facts) or four symbols (procedures). Substrates: (i) M_W(q) = Wq, W ∈ R^{96×96}, write W' = W + β(v − Wk)kᵀ with k = unit(K_θ(x_teach, z_T)), v = V_θ(x_teach, z_T), β = 1 in milestone one; (ii) 96 slots (k_i, v_i) ∈ R^{48+48}, read m = Σ_i softmax_i(γ k_i·q) v_i, write overwrites argmax_i cos(k, k_i) if above τ else the least-recently-written slot; (iii) M_W = MLP_mem (48→96→48, no biases), write = 5 SGD steps on ‖MLP_mem(k) − v‖² over the new (k, v) plus the R = 8 most recent non-superseded log entries' (k, v). The three writable objects each contain exactly 9,216 float32 values (deduction: 96² = 96·96 = 48·96 + 96·48).

| Component | Initial (meta-)training | Teaching / practice | Persistent write | Clearing | Scored inference | Evaluation |
|---|---|---|---|---|---|---|
| Encoder E_θ | Sees teaching and query strings of training-seed episodes; θ_E changes | Sees teaching string; no change | Supplies x_teach; no change | — | Sees query string only; no change | — |
| Reasoner F_θ, Q/K/V, decoder | Sees x, z, m; θ_F changes via outer loss on post-write, post-clear queries | Runs T steps on teaching, reads W; only z changes | Supplies bounded trace z_T; no change | z ← 0 | Reads W (frozen); only z changes | — |
| Writer (K_θ, V_θ, β or slot/step rule) | Its parameters change; W re-initialised per episode (as TTT W_0, R11-ttt-titans-hopfield, C1; MNM tabula rasa, R8, extra 4) | Sees x_teach, z_T, checker flags; never the query, never an answer embedding | Changes W only ((iii): MLP_mem only) | — | Disabled | — |
| Checker (fixed program) | — | Sees teaching string; emits accept/reject, is-correction; no answers | — | — | Disabled | — |
| Replay | Not used | Reads audit log of accepted teachings with superseded marks; may issue practice teachings through the writer | (iii) replay items enter the same write rule | Log stays on disk | Log unmounted (verified by log-poisoning check, Sec 4) | Unmounted |
| Evaluator | Supplies expected answers of training-seed episodes to the outer loss (declared writer training signal) | Nothing | Nothing | Nothing | Nothing | Holds world seed, expected answers, task/family IDs; sees outputs only |

Specifics the brief asks for:

- **Teaching representation.** Plain-text sentences from a teaching grammar (Sec 3). A correction is the same sentence prefixed "Correction:". A procedure is four lines "NAME of STRING gives STRING". No task ID, family label, or world parameter accompanies any string.
- **Feedback format and what it reveals.** The checker returns {accepted, rejected} and {correction, not-correction}. It reveals nothing beyond the teaching text. Nobody detects corrupted teaching, because no observable evidence makes corruption identifiable; every well-formed teaching is accepted. Pass/fail on the model's own attempts exists only inside background practice (Episode D), where it is computed from the audit log, never from the evaluator.
- **What the writer sees.** x_teach and the bounded trace z_T after T steps of the teaching pass (which may include reads of W, so the writer can see what is currently stored under that key). It does not see a response, a query, or a target embedding. This removes the draft's nn.Embedding(target) input.
- **Which weights change.** Meta-training: all θ. Teaching/write: W only ((iii): MLP_mem only). Clearing: none. Scored inference: none, and writes are disabled so nothing can be cached at test time. Evaluation: none.
- **What survives clearing and restart.** θ and W, reloaded from disk into a fresh process. z does not survive. The audit log survives on disk but is not mounted.
- **Replay, tools, records during a scored query.** None. The scored query is one string.
- **Contradictions.** Latest accepted teaching wins. Flagged corrections are the milestone-one case; unflagged contradictions are scored as a separate, harder condition. For (i) same-key delta overwrite (R5-delta-rule, C4, Sec 4.2, Eq. 24); for (ii) slot overwrite; for (iii) the superseded log entry is excluded from replay.
- **Data separation.** Worlds come from a generator with seed ranges: meta-training seeds 0-79,999 (the outer loss on these episodes is the writer's training signal, so there is no separate writer-reward set); validation 80,000-80,499 for early stopping and hyperparameters; final test 90,000-90,199, touched once per arm. Held-out compositions (10 of ~30) and one held-out query template never appear in seeds below 90,000.

Does this support "persistent weight learning" rather than an answer cache in parameters? Only partly, and I want to be exact. The stored object at milestone one *is* a binding. What distinguishes the result from a cache is what the binding can do after restart: be reached from wording it was never stored under, act as the key for a second retrieval, be reversed, be superseded, and (Episode C) select a program the reasoner executes on new operands. The comparison against an explicit nearest-key cache (Sec 4) makes this operational: a substrate that only matches the cache on these tests is a cache. What the evidence will not show is that W holds anything executable; the procedures that exploit the bindings live in θ.

---

## 3. Four worked episodes

World generator (per episode, seed s): 32 entity names sampled from a fixed vocabulary of 96 pseudo-words (e.g. boka, rimu, selt, gral, vune, pell, tosk, dorn); 12 colours {red, blue, green, teal, amber, violet, gray, pink, olive, navy, coral, ivory}, colour(e) uniform; keeper: a derangement of the 32 entities, so every entity has exactly one keeper and is the keeper of exactly one entity (deduction: bijection with no fixed points).

Teaching grammar T_teach (used in meta-training and test):
- colour: "{E} is painted {C}." | "The paint on {E} is {C}." | "They painted {E} {C}."
- keeper: "{E1} is kept by {E2}." | "The keeper of {E1} is {E2}." | "{E2} keeps {E1}."

Query grammar T_query (used in meta-training and test):
- colour: "What color is {E}?" | "Which color does {E} have?"
- keeper: "Who keeps {E1}?" | "Which one is {E1}'s keeper?"
- reverse: "Which one does {E2} keep?"
- 2-hop: "What color is the keeper of {E1}?" | "Which color does {E1}'s keeper have?"

Held-out query template (final test only): "Say what color {E} is."

The lexical overlap between teaching and query wording is minimal by construction ("paint" never appears in a query, "color" never in a teaching), which kills string-template lookup; the encoder must be meta-trained on both grammars to map them to a common key space.

Protocol within an episode: teachings arrive one at a time; z is reset to zero after each write, so no fact can ride between teachings in z; after the last teaching, (θ, W) is serialised, the process is killed, restarted, the log unmounted, and queries are asked one at a time with z reset before each. Twelve teachings per episode at test.

### Episode A (milestone one): fact, correction, interference, restart

Teachings, in this order, interleaved with six unrelated fillers:
1. "boka is painted teal."
2. "rimu is painted amber."
3. "The keeper of selt is boka."
4. "Correction: boka is painted navy."
5. "gral is painted teal."
6. "They painted vune coral."

Scored queries after restart (expected answers evaluator-only):
- Q1 "What color is boka?" → navy (correction wins after restart)
- Q2 "Which color does rimu have?" → amber (unrelated neighbour, Locality)
- Q3 "What color is gral?" → teal (interference item sharing boka's superseded value)
- Q4 "Who keeps selt?" → boka
- Q5 "Which color does selt's keeper have?" → navy (2-hop through the corrected fact; answer must change as an entailed consequence, R1, C3a)
- Q6 "Say what color boka is." → navy (held-out template)
- Q7 "What color is dorn?" where dorn was never taught → scored against chance 1/12; above-chance accuracy here indicates the answer came from θ, not W (the "no support in context" in-weights test, R13, extra 1)

Intervention: rollback W to its snapshot after teaching 3 → Q1 must return teal.

Simplest shortcut to rule out: recency in z (killed by clearing and restart); string-template lookup (killed by disjoint grammars); "return the most recent entity associated with teal" (fails Q1 and Q3 jointly).

### Episode B (milestone one): multi-hop where one retrieval determines the next

Teachings (order randomised across episodes, eight fillers):
- "The keeper of pell is tosk."
- "tosk is painted olive."
- "pell is painted gray."
- "The keeper of tosk is vune."
- "vune is painted pink."

Queries after restart:
- "What color is the keeper of pell?" → olive (the 1-hop shortcut "colour of the mentioned entity" gives gray; report the rate at which gray is emitted as the 1-hop confusion rate)
- "Which color does tosk's keeper have?" → pink
- "Who keeps pell?" → tosk (single hop, must pass for the 2-hop failure to be interpretable)

Order conditions: the colour fact taught before vs after the keeper fact. A writer that pre-composes "colour of keeper of pell" at write time can only do so when the second-arriving fact triggers it, so accuracy that depends on order is diagnostic of pre-composition (hypothesis), and pre-composition is additionally bounded by the byte budget (32 entities × 2 relations already fill a 96-association bank, deduction). The writer cannot know which queries will be asked (write-time query blindness, as in CaMeLS, R8, extra 1, Sec 3.1).

Later extension: 3-hop "What color is the keeper of the keeper of pell?" is scored but not a milestone criterion; longer chains than meta-trained are where the meta-learning precedents fail (R3, C5).

Simplest shortcut: the 1-hop answer; or a memory that stores entity-valued facts in a form that cannot be re-keyed. The draft's x-only key makes m_t constant across steps (‖m_{t+1} − m_t‖ = 0 by construction, deduction from the project context), so the 2-hop query is impossible for it by design; this episode is the behavioural test of that.

### Episode C (milestone one): method learning as composition of familiar primitives

Domain: strings of length 4 over {a,b,c,d,e,f}. Six primitives, fixed and named across all episodes, learned in θ during meta-training from many examples: rev (abcd→dcba), rot (abcd→bcda), swp (abcd→bacd), mir (abcd→abba), dup (abcd→aabc), xlast (abcd→dbca). A composition is an ordered pair "p then q". Pairs that equal identity or a single primitive on all strings are removed (rev·rev, swp·swp, xlast·xlast; deduction), leaving about 30 distinct pairs; 20 are used in meta-training episodes, 10 are held out for final test, chosen so every primitive appears in held-out pairs in both positions.

Each procedure episode assigns a fresh pseudo-name (e.g. "frob") to one pair. Teaching is one block of four demonstrations; for the held-out pair (rot then rev):
- "frob of bdfa gives bafd."
- "frob of ecca gives eacc."
- "frob of fabd gives fdba."
- "frob of ddeb gives dbed."

(Each line is rot then rev: bdfa→dfab→bafd.) The evaluator checks that the four demonstrations identify the pair uniquely among all ~30 (identifiability, deduction), and that every query string is discriminating: the correct pair's output differs from every other pair's output on that string.

Query after restart, novel operand: "frob of cafe?" → cefa (evaluator-only; rot: afec, rev: cefa). Exact match on all four symbols.

What was familiar during initial training: the alphabet, the six primitives and their behaviour, depth-2 composition as a structure, 20 specific pairs, the demonstration format, per-episode pseudo-naming. What is novel at evaluation: the 10 specific ordered pairs, the operand strings, the name binding. Not novel: primitives, depth, format.

Why this is not fitting a parameter of a known operation: no scalar attached to a fixed operation yields the held-out pair; the system must induce from four demonstrations which two primitives in which order, store that program identity in W across clearing, and execute it on unseen strings. It is also not new-primitive acquisition. What a pass demonstrates, precisely: program selection over a structured space containing never-seen elements, persistent storage of the selection, and execution by pre-existing machinery. Two easier levels are reported separately: single-primitive relabelling ("frob" = rev), which is exactly parameter-of-a-known-operation; and seen-pair naming, which tests storage only.

Baselines for this episode: the "nearest meta-training pair" shortcut (predict with the training pair most consistent with the demonstrations); the parameter-fitting baseline (gradient steps on the four demonstrations into all of θ, the analogue of the basic seq2seq control that stores everything in weights, R3, extra 5, at least seven times MLC's error on the compositional splits, R3, C4); and the in-context positive control (demonstrations left in the input). If the in-context control fails, the inducer in θ is undertrained and the memory result is uninterpretable.

Later extension: a new primitive not expressible as any depth-2 composition (abcd→cadb). With a frozen reader I expect failure (hypothesis); a pass would demonstrate that W holds executable structure, which is the claim milestone one cannot make.

### Episode D (milestone one, lite): background practice

After the teaching phase of Episodes A/B and before scoring, the process enters practice mode with no new messages. Available: θ, W, the audit log of accepted teachings with superseded marks, and a fixed, non-learned entailment generator. Unavailable: the evaluator, the world, the test queries.

Where the task originates: the generator derives practice items from log entries by three rules: reverse ("The keeper of selt is boka" ⇒ practice query "Which one does boka keep?", derived answer selt); two-hop (keeper fact + colour fact ⇒ "What color is the keeper of selt?", derived answer navy, using only non-superseded entries); re-check of corrected items. Where the verification originates: the derived answer is computed from the log by the fixed rules, so it can only contain consequences of accepted teachings, never new external facts. The system attempts each practice query from W with the log hidden during the attempt; the verifier returns pass/fail; on fail, the generator issues a practice teaching in the teaching grammar ("boka keeps selt.") which passes through the ordinary checker and writer.

Held-out queries after clearing and restart, with and without practice:
- "Which one does boka keep?" → selt
- "What color is the keeper of selt?" → navy
- Forward items (Q1-Q4 of Episode A), scored for signed change (damage).

Honest labelling: this converts inference at query time into storage at practice time. The supportable claim is "log-verified self-practice improves reverse and two-hop recall after restart without external input, at a measured cost to forward recall". It is not "the system reasons in the background". Reverse recall is worth practising because fine-tuned models trained on "A is B" answer "B is A" at chance (R7-extraction-reversal, C3a, Table 1), key-value memories are directional (R7, extra 6), and in-context presentation reverses fine (R7, C4), so a writer that only stores the forward direction leaves reversal to practice. Ground truth never enters the stop or accept decision, which is the confound behind oracle-guided self-correction results (R6-self-correction, C1, Sec 3.2; extra 1).

Later extension: proposer/solver self-play with a learnability reward, as in Absolute Zero's r_propose = 1 − mean solve rate (R6, C3, Eq. 4), which needs an executor-grade verifier; here the log-plus-rules is that verifier for entailments only.

---

## 4. The smallest decisive evaluation

### Gated positive controls (must pass before any negative is interpretable)

- PC0, in-context: the same model with all teachings concatenated before the query and no clearing. Threshold ≥ 95% on T_query. Failure means the reader or encoder is undertrained; stop.
- PC1, one-hot keys + oracle content: keys are fixed one-hot codes per (ent

ity, relation), content is the evaluator's answer embedding, written by the fixed rule; only the reader trains. Threshold ≥ 99% recall at N ≤ 32 writes for (i) and (ii); measured for (iii). This is the prior review's lead 6 and I keep it because it isolates the substrate from representation learning.
- PC2, learned key + oracle content: threshold ≥ 95% at N = 12.
- PC3, learned key + learned content (the full writer) on the taught phrasing after clearing and restart: threshold ≥ 90% at N = 12. Only after PC3 passes do paraphrase, correction, 2-hop and method numbers mean anything.

### Strong simple baseline and no-write causal control

- Baseline (explicit cache): a nearest-key lookup over stored (K_θ(x_teach), answer) pairs using the same encoder, answering with the stored answer. It has the same bytes if capped at 96 entries. Any substrate must beat it on held-out template, reverse, 2-hop and method queries; matching it on taught-phrasing recall is expected and proves nothing.
- Baseline (parameter fitting): substrate (iii) with all of θ unfrozen and no replay, the classic fine-tune.
- No-write causal control: θ frozen, z cleared, writer disabled → must be at chance (≤ chance + 5 points). Sham write: writer enabled but v replaced by zero → chance. With θ frozen and z cleared, any above-chance recall can come only from W (deduction).

### Interventions on W

- Removal: reset W to its per-episode initial value after teaching → chance.
- Cross-episode swap: teach episode 1 (save W1) and episode 2 (save W2); score episode-1 queries with W2 → chance; with W1 → passes. Answers must follow W, not the process.
- Rollback: restore the pre-correction snapshot → the superseded answer returns.
- Targeted ablation: for (i) project W onto the complement of the written key's rank-1 subspace, for (ii) zero the written slot, for (iii) not available; only the targeted item should fail. A delta write with β = 1 and unit key is a projection that erases one subspace and preserves d − 1 others (R5, extra 1, Sec 3.3), so locality holds only to the extent other keys are orthogonal to it.
- Log-poisoning: after teaching, overwrite the audit log with wrong answers, then score. Scored answers must be identical with and without poisoning (100% agreement); any change means the log is being read at inference.

### Paraphrase, interference, correction, restart

- Paraphrase: T_query templates seen in meta-training (threshold ≥ 90%) and the held-out template (report; hypothesis ≥ 75%). Score separately; even an external-memory editor loses about eleven points on paraphrases versus edit success (R12-baselines, C3, Table 2).
- Interference: the accuracy matrix R over teachings, re-scoring every earlier item after each new write (R2-cl-metrics, extra 1), with signed BWT (R2, C1, Eq. 3; C2), plus the max-based forgetting measure if items are re-scored more than once (R2, C3, Eq. 3). Unrelated items must stay within ±3 points of the sham-write control.
- Correction: post-correction accuracy ≥ 90% on the corrected item; locality on neighbours as above; rollback as above. Correction is scored only after clearing and restart, because before clearing it can be recency in z.
- Restart: all scored numbers are after process restart; the same numbers before restart are reported as a diagnostic, and a gap between them is a finding (state leaking through z or the log).

### Adaptive retrieval versus extra computation

Four arms, same parameters and bytes: (a) key from x only, T = 6; (b) key from (x, z_t), T = 6; (c) key from x only, T = 12; (d) key from x only, four parallel reads, T = 6. On 1-hop queries all four should match. On 2-hop queries the decisive comparison is (b) versus the best of (a), (c), (d): a difference ≥ 15 points with a paired per-episode bootstrap interval excluding zero, replicated in every seed, supports workspace-conditioned retrieval. If (c) closes the gap, extra computation alone suffices and the retrieval claim fails. Arm (a) is the draft's constant-read design.

### Fair capacity comparison

| Substrate | Writable object | Float32 count | Bytes | Independent-key ceiling (deduction) |
|---|---|---|---|---|
| (i) delta bank | W ∈ R^{96×96} | 9,216 | 36,864 | ≤ 96 exactly recoverable associations with linearly independent keys; storing more than d_dot associations gives retrieval error (R5, C5, Sec 4.1) |
| (ii) slot memory | 96 × (48 + 48) | 9,216 | 36,864 | 96 if keys separate; near-duplicate keys blur into an averaged retrieval (R11, extra 6) |
| (iii) MLP_mem | 48·96 + 96·48 | 9,216 | 36,864 | unknown; measured |
| Cache baseline | 96 × (48 + 1) | 4,704 | 18,816 | 96 |

Achieved recall capacity N95: write N distinct facts once each with no replay, clear, restart, score the taught phrasing; N95 is the largest N ∈ {8, 16, 24, 32, 48, 64, 96, 128} with ≥ 95% recall. Larimar's near-100% up to 512 edits at memory size K = 512 then 82% at 1024 is the calibration shape to expect (R12, C3, Sec 5.4). Report N95 per substrate at equal bytes, and report bytes per recovered fact at N95. "No persistent writes" has zero capacity and is a baseline, not a capacity-matched control.

### Damage measurement and the clipping bias

Report new-learning benefit (accuracy on newly taught items) and old-knowledge damage (change on previously taught items, and on a frozen meta-training validation set) as separate numbers, never a difference or a weighted sum. Damage is signed, as GEM's BWT is (R2, C2). The draft's D = mean(max(0, before − after)) is biased upward: for zero-mean Gaussian noise with standard deviation σ, E[max(0, ε)] = σ/√(2π) (deduction), so a harmless write registers as damage proportional to evaluation noise. Treatment: paired per-item outcomes with counts of correct→incorrect and incorrect→correct flips (the collateral-flip framing in R6, extra 2), the signed mean, and if a one-sided figure is wanted, D_signed minus the same statistic under sham writes.

### Thresholds, uncertainty, stopping

- Sample sizes fixed in advance: 200 final-test episodes per condition per seed, roughly 2,000 queries per query type; a Wilson 95% interval at p = 0.9 has half-width about 1.3 points at n = 2,000 (deduction). Three meta-training seeds minimum, five preferred; report per-seed means and ranges, and treat the seed as the unit for arm comparisons.
- Chance levels stated with every number: 1/12 colours, 1/32 entities, 1/1296 strings (report the nearest-training-pair shortcut instead of chance for Episode C).
- Method threshold: ≥ 70% exact match on discriminating held-out-pair queries (hypothesis), with the nearest-training-pair shortcut and the parameter-fitting baseline both reported.
- Meta-training stopping: halt an arm when validation query accuracy improves by less than one point over three consecutive ten-minute runs, or after twelve runs. Expect plateaus: general-purpose in-context learners show long loss plateaus and a memorisation-first curriculum removes them (R13, extra 6), and grokking-style delayed generalisation on small algorithmic tables can take 10^5-10^6 steps (R9-grokking-arc, C1), which the primitive-learning part of Episode C may touch.
- Budget: 3 substrates × 4 retrieval arms is too many; run the retrieval arms on substrate (i) only, and the substrate race on arm (b). That is 6 configurations × 3 seeds × ≤ 12 runs ≈ 36 GPU-hours plus evaluation, over a few days on the single card. Storage is trivial (models under 1M parameters).

### What counts against the hypothesis versus a broken component

Smoke test: PC0-PC3, no-write control at chance, log-poisoning agreement, W-swap at chance. Passing these is engineering, not a result.

Research result, per substrate, requires PC3 ≥ 90% and then: held-out template, reverse, 2-hop and method above the explicit cache; correction surviving restart; N95 reported. Outcomes that count against "W carries persistent, compositionally usable bindings": PC0-PC3 pass but W-removal does not drop accuracy (information is elsewhere); 2-hop and reverse at chance across all arms while PC0 passes (the substrate is a verbatim cache); correction passes before clearing and fails after (recency, not memory). Outcomes that indicate an undertrained or broken component rather than a falsification: any PC failure; PC0 failing on Episode C (inducer not trained); accuracy that differs before and after restart with everything else equal (serialisation or leakage bug). Ten-minute null results without PC0-PC3 are uninterpretable and are not reported as negatives.

---

## 5. Architecture consequences

Required by this contract:

- Memory interface: a read M_W(q) callable with a key formed from (x, z_t), and a value space that the reasoner can re-key from (entity-valued retrievals must be usable as the next key). Without this, Episode B is impossible by construction, whatever the substrate.
- Writer: input (x_teach, z_T); output a write to W only; trained by the outer loss on post-clearing queries (bi-level, as CaMeLS trains its weighting model through post-update QA loss, R8, C1, Sec 3.2, and MNM trains its writer through post-write reads, R8, C3). No target-answer embedding, no RL heads, no skip head, bank choice by softmax, write strength a sigmoid if learned (R5, C6, Eq. 21). An auxiliary loss on the taught items themselves is worth keeping: meta seq2seq drops from 99.95% to 5.43% without its support loss (R3, C3, Table 2).
- Clearing and restart: z reset after every teaching and before every query; serialise (θ, W); kill and restart; unmount the log; log-poisoning check in the harness.
- Language interface: encoder over one shared vocabulary handling both grammars; decoder for one answer token and for four-symbol strings. No explanation output is required.
- Stopping: fixed T = 6 in milestone one; no 'stuck' output, which would let the model opt out of hard queries; a 'stuck' is scored wrong.
- Practice: a fixed entailment generator and log verifier, as in Episode D.
- Storage guard: the draft's 100 GB constants and run.py's 10 GB defaults disagree (project context); pick one and log peak bytes per run.

Worth comparing experimentally:

- The substrate race (i)/(ii)/(iii) itself.
- (i) with learned β versus β = 1; (i) with a decay gate, expecting a retention cost: gating clears memory but decay hurts retention on long needle tasks (R5, C3; extra 2, Table 2).
- (i) with expanded key dimension at equal bytes (fewer, larger banks), following the d_dot capacity argument (R5, C5).
- (ii) with a deferral radius trading paraphrase generalisation against locality, the knob GRACE exposes (R12, C4, Sec 3.2.2).
- (iii) with replay size R ∈ {0, 8, all} and with a learned per-token loss weighting (R8, C2).
- Deeper memory for (iii): a matrix memory is an online linear regressor and two-layer MLPs are strictly more expressive (R11, extra 4).
- Halting: ACT's time penalty is sensitive to its hyperparameter (R10-stopping, C1), PonderNet uses a KL to a geometric prior rather than a step penalty (R10, C2), and a zero-shot exit on the KL between successive steps below 5×10⁻⁴ needs no training (R10, C3c). Any expected-time penalty is gameable (R10, extra 1). Compare only after the fixed-T results exist.
- Input injection at every recurrent step and a random z_0, which stabilises recurrence (R10, C4).

Bridge from milestone one to reusable method learning: Episode C shows that W can hold a program identity the reasoner executes, induced from demonstrations over a program space with never-seen elements. The next experiment is a memory that is executed rather than pointed to: a feed-forward memory function with meta-learned local update rules (R8, C3), tested on the new-primitive extension. The bridge is weak, and I will say so plainly: nothing in milestone one shows W holding executable structure, and the composition result may be entirely explained by θ having learned a 30-way program classifier plus six executors. That is still a real step beyond storing 24 numbers, but it is not procedure acquisition.

---

## 6. Decision record

**Recommended first milestone, one sentence.** Under the Cleared-Context Binding Contract, race three byte-matched memory substrates behind one shared encoder, reasoner and writer, and require taught bindings to survive clearing and process restart while being reachable from unseen wording, usable as keys for a second retrieval, superseded by flagged corrections, and, for demonstration-taught compositions of familiar primitives, executed on operands never demonstrated.

**Exact claim success would support.** With θ frozen after meta-training and z cleared, a one-shot write into a 36,864-byte editable memory stores a binding that survives restart and is used compositionally at scored inference (paraphrase, reverse, 2-hop, correction, held-out composition), at an accuracy above an explicit nearest-key cache of equal bytes, with a measured recall capacity N95 and a measured, signed cost to earlier bindings.

**Strongest claim it would NOT support.** That the system acquires new procedures: every operation executed at test time was learned into θ during meta-training, and W holds bindings and program pointers, not executable structure. It would also not support any claim about learning from pass/fail feedback, since milestone one's teachings all contain their answers, nor any claim about autonomous reasoning, since practice is log-verified entailment.

**Three most important unresolved risks.**
1. Meta-training may not converge inside the chained ten-minute budget, especially through the plateau before general in-context learning (R13, extra 6); a result of "nothing passed PC3" would be uninterpretable, not negative.
2. The 2-hop test may be solved by pre-composition or by θ-side heuristics on the 1-hop answer rather than by re-keyed retrieval; the order conditions and byte accounting are indirect controls, not proofs.
3. Episode C may pass through a 30-way program classifier in θ with W storing only the class, which is the weakest reading of "method"; the new-primitive extension is the only test that separates the readings, and it is outside milestone one.

**Smallest observation that would change the recommendation.** If PC0 (teachings in context, no clearing) fails to reach 95% on 2-hop or held-out-composition queries after twelve chained runs on any substrate, the reader itself cannot use the information when it is freely available, and no memory experiment is worth running; I would then recommend a smaller milestone that meta-trains only the encoder and reader on in-context episodes, and revisit the memory contract afterwards.