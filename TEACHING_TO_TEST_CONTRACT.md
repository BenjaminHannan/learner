# Teaching-to-test contract: decision memo

Date: 2026-09-17. Design only. Nothing was implemented, trained, installed, or run. Every list-operation answer in the worked episodes was checked with a throwaway script; no model output is claimed anywhere.

## Recommendation

Adopt the **Declare, Clear, Apply** contract for milestone one.

- **Declare.** Teaching is one English sentence per item, in a controlled grammar, that legitimately contains what is being taught: a constant ("the list called blick is [ a c f ] ."), a relation ("the twin of blick is frim ."), an attribute ("the tag of blick is c ."), or a definition of a new named procedure over primitives the system already executes ("to zorp a list : flip it , then drop the first item ."). Every name is fresh in every episode. No task IDs, family labels, answer indices, or world parameters accompany any sentence.
- **Clear.** After each teaching the writer makes exactly one rank-1 write into W from the encoded sentence alone. The writer cannot read W. The workspace z is reset after every teaching and before every query. All scored numbers are taken after the parameters and W are serialized, the process is killed and restarted, and the audit log is unmounted.
- **Apply.** Scored queries never repeat a teaching's wording and always require something the teaching did not contain: a paraphrased template, a retrieval whose key comes from an earlier retrieval, the corrected value propagated through a chain, or a stored procedure executed on operands and inside compositions that did not exist at write time.

Milestone one has three tiers scored separately, all in the same world with the same encoder, reasoner, writer, and W:

1. **Constants and attributes**: paraphrase, correction, interference, restart, and accumulation across two sessions.
2. **Chains**: a two-hop query where the first retrieved value is the key of the second, and the same query after the intermediate fact is corrected.
3. **Definitions**: a procedure defined once in English, executed on unseen operands, inside unseen compositions with primitives and with other defined procedures, from a composition class never seen in initial training.

Tier 3 is included in milestone one **conditionally**: it is required if a separately trained in-context reader can execute held-out compositions from a definition placed in its input (positive control PC-R in section 4). If PC-R fails within the budget, tier 3 is deferred, milestone one is tiers 1 and 2, and the method bridge becomes the next experiment with a stronger reader. That conditional is the only place where an unresolved choice changes the answer.

Where this departs from the earlier reviews: the adversarial review recommended "facts survive interference, correction, and restart" as the first milestone. I keep those tests but I do not accept them as a milestone on their own, because a memory that passes them can be an answer cache and passing says nothing about the reasoning loop or about methods. Two-hop-with-correction and the definition tier are what make the memory result bear on the stated goals. I also drop the learned write/skip policy, the four-bank router, the checker that reveals answers, and the halting head from milestone one; none is required by this contract and each adds an unexplained variable.

Provenance: I read the draft code and both prior reviews directly. Thirteen source groups were re-verified against primary texts by fetch-and-quote (section 7). Three candidate contracts were drafted by agents I ran with different stances and audited by nine agent auditors under shortcut, feasibility, and evidence lenses. Their objections shaped sections 3 and 4. The recommendation and every judgment in this memo are mine.

---

## 1. Contract choice

### Candidates

| | F. Relational facts by sentence | I. Definitions plus facts by sentence (chosen) | D. Induction from demonstrations |
|---|---|---|---|
| Teaching | Declarative sentences about a random fictional world | Declarative sentences: constants, relations, attributes, and English definitions of new named procedures over known primitives | Three to five input–output pairs for an unnamed function; no rule statement |
| Feedback at teaching | None; accepted sentences are true by declaration | None; a fixed grammar gate accepts well-formed sentences and flags corrections | Pass/fail on the learner's attempts |
| Scored test | Paraphrase, two-hop, correction-then-two-hop, interference, restart | Everything in F plus execution on novel operands, inside novel compositions, from held-out composition classes | Novel operands of the induced function |
| Evidence if passed | Persistent, correctable, composable bindings in W | The same, plus a stored description that a frozen interpreter executes; composition of familiar operations under a novel name | Program induction plus storage; strongest if it worked |
| Feasibility on one 16 GB GPU with chained ten-minute runs | Highest. Closest precedent for episodic teach-then-query meta-training at this scale: meta seq2seq trained on 10,000 episodes in under one hour on one Titan X (Lake 2019, Sec. 4.1), though that model stored support items in an attention memory, not in weights | Middle. Same machinery as F plus an interpreter for compositions; MLC-style in-context interpreters exist at 1.4M parameters, but wall-clock is not stated in that paper (Lake and Baroni 2023, Methods) | Lowest. Induction and storage fail together, so a null is unattributable; pass/fail-only supervision over an open program space has no tiny-scale precedent in the verified sources |
| Shortcut resistance | Good for bindings; success on single-hop recall alone is a cache | Good: the definition contains no answer to any scored query; operands and compositions are absent at write time; the residual shortcut (an index into training compositions) is detectable with held-out classes and discriminating operands | Medium: nearest-demonstration heuristics pass partially |
| Relevance to goals | Persistence and adaptive retrieval; nothing on methods | Persistence, adaptive retrieval, and the first rung of method learning (composing familiar operations from a stored description) | Methods directly; persistence untested unless W also holds the function |

### Why I

Meaningful evidence. The knowledge-editing literature already documents the difference between an answer written into parameters and knowledge that is used. Yao et al. (2023) score edits on reliability, paraphrase generalization, locality, and portability, where portability includes reversed relations and one-hop reasoning from the edited fact (Sec. 2 and Sec. 5.1). On MQuAKE, MEMIT reaches 96.2% edit-wise recall on GPT-J but 7.0% on multi-hop questions that depend on the edited fact (Zhong et al. 2023, Table 3), and the authors read this as facts being hard-coded rather than integrated (Sec. 4.2). "Single-hop passes, chained use fails" is therefore the published signature of a cache. Contract I makes chained use and executed use the primary measurements, at a scale where W can be zeroed, swapped, and rolled back directly.

Shortcut resistance. Two design choices from meta-learning remove the shortcut in the draft world. Names and bindings are re-sampled every episode, which Santoro et al. (2016, Sec. 2) use precisely so the network cannot "slowly learn sample-class bindings in its weights". And the definition tier has no answer in the teaching at all: the sentence names two or three primitives in order, and every scored query supplies an operand the writer never saw. Chan et al. (2022, Sec. 4) note that when bindings are fixed, an in-context strategy and an in-weights strategy give the same answer, so an evaluation on fixed bindings is ambiguous by design; re-randomization removes that ambiguity.

Relevance. Executing a stored two-step definition and answering a two-hop chain use the same machinery: retrieve, act on the workspace, retrieve again with a key that depends on what was retrieved. That is exactly the capability the provisional loop claims and the draft code lacks (its key is computed from the input only, so the retrieved vector is constant across steps). Tier 2 tests the loop on facts; tier 3 tests whether a stored description can drive it.

Feasibility. Facts and chains at this scale are plausible inside chained runs; the interpreter for tier 3 is the open risk, which is why it is gated by a positive control rather than assumed.

### Why not F alone or D

F alone is the earlier reviewers' recommendation. Its pass criterion is satisfied by a store of bindings, and its natural next step is "add chains", which is already tier 2. Making it the whole milestone spends the budget establishing that a delta-rule memory can hold bindings, which Schlag et al. (2021), Larimar, and GRACE have already shown for related stores.

D is where the ambition lives, but at tiny scale a success is ambiguous. Kirsch et al. (2022, Sec. 4) describe meta-learned behavior passing through task memorization and task identification before general learning-to-learn, and needed at least 8,192 tasks to reach the last regime in their setting. With a program family small enough to meta-train in ten-minute runs, success most likely means task identification, which is selecting a known operation. D is the right second experiment once tier 3 shows that a stored description can be executed.

### Labeled assumptions

- A1. Ten-minute runs are chained through checkpoints; the cap is per run, not per project.
- A2. Names are character strings over a fixed alphabet, so novel names get trained embeddings by composition. Tokens never seen in initial training are out of scope; the meta-learning precedents do not demonstrate them either (Lake and Baroni 2023, Discussion: no mechanism for emitting new symbols).
- A3. "Method" at milestone one means a novel ordered composition of familiar primitives bound to a novel name, taught by instruction. Acquiring a new primitive is out of scope and is discussed in section 5.
- A4. Wall-clock convergence inside the chained budget is the binding constraint; VRAM and the 100 GB storage cap are not, for models under a few million parameters.

---

## 2. Information boundaries

### Components

- Encoder E_θ: character-level GRU over one shared vocabulary (about 60 word types, 8 list symbols, brackets, punctuation, letters for names); outputs x.
- Reasoner F_θ with fixed T = 6 steps: q_t = unit(Q_θ(x, z_t)); m_t = M_W(q_t); z_{t+1} = F_θ(x, z_t, m_t). Decoder D_θ(x, z_T) emits up to 8 output slots over {8 symbols, 6 primitive names, name characters, unknown, pad}.
- Memory W: one 128 × 128 float32 matrix, 65,536 bytes. Read M_W(q) = W q. This is the milestone-one substrate; section 4 races it against a byte-matched slot memory.
- Writer G_φ: maps the encoded teaching sentence x_teach (and nothing else) to a unit key k and a content vector v; the write is the fixed rule W' = W + β (v − W k) kᵀ with β = 1 in milestone one. One write per accepted sentence. The writer cannot read W and does not see z.
- Checker: a fixed program. At teaching it accepts well-formed sentences and flags the "correction :" prefix; it reveals nothing. In practice (episode D) it returns pass/fail from the audit log or a primitive executor.
- Replay: a fixed process that re-presents logged sentences through the ordinary teaching channel during practice only.
- Audit log L: append-only plain-text record of accepted sentences with version numbers and superseded marks, plus W snapshots. On disk always; mounted only during teaching, practice, and evaluation.
- Evaluator: holds the world, expected answers, split membership, and the executor; sees outputs only.

### Boundary table

| Component | Initial training (meta-training) | Teaching or practice | Persistent write | Clearing | Scored inference | Evaluation |
|---|---|---|---|---|---|---|
| Encoder | Sees teaching and query strings of training-seed episodes; θ_E changes | Sees the teaching string; no change | Supplies x_teach | Nothing to clear | Sees the query string only; frozen | Idle |
| Reasoner | Reads episode-local W (re-initialized to zero each episode); θ changes by the outer loss on post-clear queries | Idle during teaching; in practice, answers practice queries reading W | Idle | z ← z_0 | Reads W at every step; frozen; no writes | Idle |
| Writer | Sees x_teach only; φ changes by gradient through the functional write to the post-clear query loss | Sees x_teach only; frozen | Emits (k, v); the only channel that changes W | Nothing | Disabled | Idle |
| Checker | Unused | Grammar gate and correction flag; in practice, pass/fail from L or the executor | Gates whether the write happens | Nothing | Absent | Idle |
| Replay | Unused | Reads L; re-presents latest-version sentences as ordinary teachings | Same write rule as any teaching | Nothing | Absent; L unmounted | Idle |
| Evaluator | Supplies expected answers of training-seed episodes to the outer loss | Idle | Records W snapshot | Idle | Sends the query string; receives the output | Scores exact match; runs interventions on W copies |

### The specifics

- **Teaching representation.** One sentence from the teaching grammar (section 3). A correction is the same sentence with the prefix "correction :". Definitions use templates T1–T4 in training; T5 is held out.
- **Feedback format and what it reveals.** At teaching: accept or reject, and the correction flag. Nothing else. At practice: one bit, pass or fail, computed from L or from the executor; on fail the logged sentence is replayed, which is answer-revealing correction routed through the teaching channel, and is labeled as such in episode D. At scored inference and evaluation: nothing.
- **What the writer sees.** The encoded teaching sentence. Not a response, not a workspace trace, not a target embedding, not W. This is stricter than the draft and stricter than two of the three candidate designs, and it is deliberate: a writer that can read W during teaching can pre-compose chains at write time, which would make tier 2 pass without adaptive retrieval. A W-reading writer (consolidation at write time) is a later comparison, not a milestone-one component.
- **Which weights change.** Meta-training: θ and φ. Teaching and practice: W only. Clearing, scored inference, evaluation: nothing.
- **What survives clearing and restart.** θ, φ, W. z does not. L survives on disk but is unmounted at scoring. "Clear only" and "restart" must give bit-identical outputs; a difference is a hidden-state bug, not a result.
- **Replay, tools, external records during a scored query.** None. The scored query is one string; the model has θ, φ (disabled), W, and a fresh z. A log-poisoning check enforces this (section 4).
- **Contradictions and superseded teachings.** Latest accepted teaching wins. Flagged corrections are the milestone-one condition; unflagged restatements are scored as a separate, harder condition. The writer is meta-trained on episodes containing both, so it learns to emit the same key for the same (name, relation) regardless of wording; with β = 1 and a unit key the delta rule then replaces the old value in that key's direction exactly (Schlag et al. 2021, Eq. 23 decomposes the step into a write and a removal of the current value). L marks the old entry superseded; replay uses the latest version only. Decay is not needed for correction and is listed under "worth comparing".
- **Data separation.** Worlds come from a generator with disjoint seed ranges: meta-training, validation (early stopping and hyperparameters), and final test (touched once per condition). Definition templates: T1–T4 train, T5 test. Composition classes (functionally distinct programs of depth 2–3): 70% train, 10% validation, 20% test, with every primitive appearing in every slot position within the training classes. Names: generated fresh per episode from character patterns; a pre-registered test list is checked to be at edit distance two or more from every logged training name. Operands used in test queries never appear in any training query. There is no separate writer-reward pool because the writer is trained by the same outer loss as θ, not by a reward; if a learned write gate is added later, its reward queries must come from a pool disjoint from θ's training queries.

### Persistent weights or a cache in parameters

W is a parameter tensor by construction, and the interventions in section 4 (zero, swap across episodes, rollback, content swap) establish that W and not z, θ, or any record carries the taught information. What separates the result from a cache is use the write could not anticipate: paraphrased wording, a retrieved value serving as the next key, a correction propagating through a chain, and a definition executed on operands and in compositions that did not exist at write time. A cache of query–answer pairs cannot do the last three.

Two honest limits. First, θ and φ are frozen at teaching, so the milestone shows persistent learning in W, not learning in the main network after initial training. Second, W is re-initialized to zero at the start of every meta-training episode, as in the MANN protocol where memory is wiped between episodes (Santoro et al. 2016, Sec. 4.2.1) and in test-time-training layers whose fast weights start from a shared W_0 per sequence (Sun et al. 2024, Sec. 2.7). Persistence at milestone one therefore means: within a session of up to a few dozen teachings, across clearing, across one process restart, and across one additional session taught after the restart with no reset (tier 1 accumulation test). It does not mean lifelong accumulation.

---

## 3. Four worked episodes

### The world

Symbols a–h. Operands are lists of length 3 to 5, written "[ c a f b ]". Six primitives, fixed across all episodes and learned into θ during initial training from direct commands such as "flip [ a b c ]" → "[ c b a ]":

| Primitive | Surface forms (definitions and queries) | Effect on [ e a d b c ] |
|---|---|---|
| flip | "flip it" / "reverse it" | [ c b d a e ] |
| drop-first | "drop the first item" / "remove the head" | [ a d b c ] |
| drop-last | "drop the last item" / "remove the end" | [ e a d b ] |
| rotate | "rotate it left" / "move the first item to the end" | [ a d b c e ] |
| swap | "swap the first two" / "exchange the first pair" | [ a e d b c ] |
| double | "double the head" / "repeat the first item" | [ e e a d b c ] |

Compositions are ordered sequences of two or three primitives (252 sequences). Sequences are grouped by the function they compute on all 37,376 operands; on a 3,000-operand sample I count about 134 distinct functions, seven of which equal the identity or a single primitive and are excluded. The exact count is computed at implementation time. Example of a collision worth knowing: "rotate, then flip, then drop the first item" equals "flip, then drop the last item" on every list. Held-out classes are chosen among the distinct functions, so a held-out definition is never a re-wording of a training program.

Teaching grammar:
- Constant: "the list called NAME is [ ... ] ."
- Relation: "the twin of NAME1 is NAME2 ."
- Attribute: "the tag of NAME is S ." (S a symbol)
- Definition: T1 "to NAME a list : P1 , then P2 [, then P3] ."; T2 "NAME means P1 then P2 [then P3] ."; T3 "define NAME as P1 followed by P2 [followed by P3] ."; T4 "you NAME a list when you P1 and next P2 [and next P3] ."; T5 (held out) "NAME is : P1 ; after that P2 [; after that P3] ."
- Correction: "correction : " prefix on any of the above.

Query grammar: "show NAME" / "what is NAME" / "give me NAME"; "PRIM NAME"; "tag of NAME"; "show the twin of NAME"; "PRIM the twin of NAME"; "tag of the twin of NAME"; "NAME [ list ]"; "NAME then PRIM [ list ]"; "PRIM then NAME [ list ]"; "NAME1 then NAME2 [ list ]"; "what does NAME do ?" (reflection; reported separately, never part of a pass). The answer "unknown" is correct for names never taught and is trained on about 15% of meta-training queries so that confabulation is scorable.

Names are 4–6 lowercase letters (blick, frim, zorp, vask, nulm, ...), fresh per episode. Expected answers below are evaluator-only unless they appear verbatim in a teaching.

Protocol inside every episode: teachings arrive one at a time; z is reset after each write; after the last teaching, (θ, φ, W) is serialized, the process is killed and restarted, L is unmounted, and queries are asked one at a time with z reset before each. Meta-training uses the same clearing schedule, so there is no train–test mismatch in what z may carry.

### Episode A (milestone one): constant, correction, interference, restart, accumulation

Teachings, in order:

1. "the list called blick is [ a c f ] ."
2. "the tag of blick is c ."
3. Four unrelated teachings (two constants, one twin, one definition), including "the list called frap is [ h b a ] ."
4. "correction : the list called blick is [ a c g ] ."
5. Eight further unrelated teachings, including "the list called drell is [ a c f ] ." (shares blick's superseded value) and "to nulm a list : drop the last item , then flip it ."

Restart. Scored queries, z fresh before each:

- "show blick" → [ a c g ]. Old-answer check: [ a c f ] is scored as a specific failure.
- "give me blick" (different query template) → [ a c g ].
- "flip blick" → [ g c a ].
- "tag of blick" → c (same subject, other relation: must be untouched by the correction).
- "show drell" → [ a c f ] (shares the superseded value; must not have been dragged to [ a c g ]).
- "show frap" → [ h b a ].
- "nulm [ a b c ]" → [ b a ].
- "show grok" (never taught) → unknown.

Accumulation: after these queries, a second session teaches six more items with no reset of W, followed by a second restart; all of the above are re-scored together with the new items. Nothing tells the model where the session boundary was.

Feedback available: none at any point. Simplest shortcuts to rule out: the answer rides in z (killed by clearing and restart); the binding was fit into θ (killed by per-episode re-randomization and by scoring "show blick" before teaching 1, which must give unknown); a hidden channel other than W survives restart (killed by the clear-only-equals-restart check and by zeroing W after restart, which must drop every taught item to unknown or chance).

Rollback intervention: restore the W snapshot taken after teaching 3 and re-ask "show blick" → [ a c f ]. This proves the correction lived in W.

### Episode B (milestone one): a retrieval that determines the next retrieval

Teachings, with the writer blind to W so nothing can be pre-composed at write time; run in both orders:

1. "the twin of blick is frim ."
2. "the list called frim is [ b d a h ] ."
3. "the tag of frim is d ."
4. "the list called blick is [ g g e ] ." (distractor: a one-hop lookup on blick gives the wrong list)
5. Six unrelated teachings.

Restart. Scored queries:

- "show the twin of blick" → [ b d a h ]. Two retrievals: blick's twin, then frim's list. "frim" appears nowhere in the query; it exists only in the value retrieved at hop one.
- "flip the twin of blick" → [ h a d b ].
- "tag of the twin of blick" → d.
- "flip blick" → [ e g g ] (control: own list, not the twin's; the rate at which [ h a d b ] appears here is the one-hop confusion rate).
- "show frim" → [ b d a h ] (single hop; must pass for a two-hop failure to be interpretable).

Then: 6. "correction : the list called frim is [ b d a c ] ."

Restart. "flip the twin of blick" → [ c a d b ]. This is the decisive fact-tier test: the corrected intermediate must change the chained answer, the entailed-consequence requirement MQuAKE formalizes (Zhong et al. 2023, Sec. 1), at a scale where we can look inside W.

Why this needs workspace-conditioned retrieval (deduction): the key for hop two is (frim, list). If q_t = Q(x) as in the draft, q_2 = q_1 and m_2 = m_1, so nothing retrieved after step one can depend on frim; extra steps iterate on constant inputs. With q_t = Q(x, z_t), z_2 can carry frim's code and form the second key. This also imposes a representational requirement: the value the writer stores for a twin relation must live in the same code space the encoder uses for name keys, or the reasoner cannot re-key from it.

Simplest shortcut to rule out: write-time composition. A writer that could read W would, at teaching 2, find "blick's twin is frim" and store frim's list under blick's key as well, turning the query into one hop. The W-blind writer makes this impossible by construction; the both-orders run and the correction catch any residual version. A second shortcut, a constant key returning a superposition of both lists, is measured by arm (a) in section 4.

Stretch query, scored but not a milestone criterion: "zorp the twin of blick" with zorp from episode C → [ a d b ]: three retrievals, one of them a definition.

### Episode C (milestone one, conditional on PC-R): a new procedure by definition

What was familiar in initial training: the six primitives and their twelve surface forms; ordered composition of depth two and three as a structure; the training composition classes (70% of distinct functions); templates T1–T4; the query grammar; the act of binding a fresh name to a definition (names re-sampled every episode, as MANN shuffles labels per episode and meta seq2seq re-assigns primitive meanings per episode: Santoro et al. 2016, Sec. 2; Lake 2019, Sec. 4.3).

What is novel at evaluation: the name string; its binding; the composition class (never defined, queried, or executed in initial training); the operands (never in any training query); query-time compositions of the new name with primitives and with other new names; template T5. Not novel: primitives, depth, the definition format.

| Level | Novel | Familiar | Achievement in the brief's terms |
|---|---|---|---|
| Tier 3.0 | name, operands | composition class seen in training | binding only; comparable to task identification |
| Tier 3.1 | name, operands, composition with a known primitive at query time | composition class | composing familiar operations at query time |
| Tier 3.2 | name, operands, composition class never seen as a function | primitives, depth, format | composing familiar operations in an unseen order, from a stored description |
| Not tested | a new primitive | | acquiring a new procedure (section 5) |

Teaching (test name zorp; composition "flip, drop-first", assumed to be in a test-unseen class):

"to zorp a list : flip it , then drop the first item ."

Feedback: none. The writer sees the encoded sentence; W is written; z cleared; restart.

Scored queries and expected answers:

- "zorp [ c a f b ]" → [ f a c ]
- "zorp [ h h d a g ]" → [ a d h h ]
- "zorp then rotate it left [ c a f b ]" → [ a c f ] (tier 3.1)
- "double the head then zorp [ d b e ]" → [ b d d ] (tier 3.1)
- "what does zorp do ?" → "flip drop-first" (reflection; reported separately; this answer is present in the teaching, which is legitimate)

Second definition into the same W: "to vask a list : rotate it left , then swap the first two ."

- "vask [ c a f b ]" → [ f a b c ]
- "zorp then vask [ c a f b ]" → [ c a f ]
- "vask then zorp [ c a f b ]" → [ b a f ] (order-sensitive; distinguishes execution from set membership)
- "zorp [ c a f b ]" → [ f a c ] (re-scored after the second write: interference)

Paraphrase (held-out template T5, fresh name): "blim is : reverse it ; after that remove the head ." then "blim [ c a f b ]" → [ f a c ].

Why this is not fitting a parameter of a known operation: the draft's family was x ↦ x + c mod 8, and W held c; the decoder's arithmetic never changed. Here the stored object selects an ordered composition, and the test requires compositions whose function never appeared in initial training. If θ had learned a lookup from definitions to trained programs, held-out classes would sit at the nearest-training-class rate. If θ learned to decode a description slot by slot and execute each primitive in order, held-out classes pass. The second is "composing familiar operations" under a stored description, which is the brief's middle category, and that is the claim. It is also what a frozen reader interpreting a newly stored program demonstrates: W holds a description; θ holds the interpreter; the description is new, the interpreter is not.

Simplest shortcut to rule out: an index into training composition classes. Detection has two parts. Held-out classes must pass well above the nearest-training-class rate, computed offline by mapping each test class to the training class whose outputs agree with it most often. And every scored operand must be discriminating: the target program's output on that operand must differ from the output of every training-class program and of every program that shares two of three primitives with the target. Without this filter, a program and its neighbors give identical outputs on many short lists and an index passes at well above chance. A second shortcut, the definition leaking through z, is killed by clearing and restart.

### Episode D (milestone one, smoke level; research-grade version is a later extension): background practice

Setup: after the teachings of episodes A–C plus sixteen further interfering writes, the process is left alone with no new messages.

Where the task originates: a fixed scheduler, not the model, draws a name from L's index and either (i) generates a query from the training query grammar for a constant or attribute, or (ii) generates a random operand for a definition. Selection prefers items whose last practice attempt failed or whose output margin is lowest. Confidence is used for selection only, never for acceptance, because intrinsic self-correction without external feedback degrades performance and earlier positive reports depended on oracle labels deciding when to stop (Huang et al. 2023, Sec. 1 and Sec. 3.2).

Where the verification originates: for constants and attributes, the checker compares the exact-match answer with the logged latest-version sentence and returns pass or fail. For definitions, an external executor runs the logged definition text on the operand and compares; this is the role of the code executor in Absolute Zero as the single source of verifiable feedback (Zhao et al. 2025, Abstract and Sec. 3.1). The model never reads L directly; the executor executes logged text, not the model's recollection.

On fail: replay re-presents the logged sentence through the ordinary teaching channel and the writer writes. On pass: no write. Writes are gated by a checked outcome, never by a speculative thought.

Exact strings: L contains "the list called blick is [ a c g ] ." (version 2). Practice query "show blick"; model answers [ a c f ] (interference damage); checker: fail; replay: "the list called blick is [ a c g ] ."; write. Later scored query after restart: [ a c g ].

Negative control (must hold): the scheduler poses "show grok", a name absent from L. Model answers [ b a c ] with high margin. Checker: fail (no entry; expected "unknown"). No write may occur: verified by W being bit-identical before and after, and by the later scored answer remaining unknown.

What this establishes, honestly: that the practice channel can repair interference using only an external record, a one-bit verifier, and answer-revealing replay, and that it cannot introduce facts that were never taught. It is re-teaching gated by a bit. It is not hypothesis testing and not method discovery. The research-grade extension, run after milestone one: derived-entailment practice (two-hop consequences of logged facts written as direct entries, verified against L by fixed rules) scored as a speed-up on chains and as signed damage on forward items; and definition practice with the executor scored as a gain on practiced names against unpracticed ones. Even then, practice converts inference into storage; it does not discover.

Milestone one: A, B, D (smoke level), and C if PC-R passes. Later extensions: reverse-direction queries as a pass criterion (a key-to-value store is directional; fine-tuned models answer reversed facts at chance while in-context reversal works, Berglund et al. 2023, Sec. 2.1.2 and App. B.6), three-hop chains, unflagged contradictions as a pass criterion, depth-four definitions, induction from demonstrations (contract D), and research-grade practice.

---

## 4. The smallest decisive evaluation

### Positive controls, in order

A negative result on any research test is uninterpretable until the controls below pass. Each is a separately trained condition where noted.

- **PC-K (substrate mechanics).** One-hot keys, oracle content vectors placed by the evaluator, no learning. Recall must be 100% for N ≤ 128 writes into the 128 × 128 bank. Failure is a bug. The same rig with random unit keys traces the degradation curve that Schlag et al. (2021, Sec. 4.1 and Sec. 6.1.1) describe: a linear memory in d dimensions cannot hold more than d interference-free associations, and their linear attention with d = 64 began accumulating errors around 60 associations.
- **PC-E (encoder keys).** Learned keys, oracle content, taught wording equals query wording: ≥ 95% at N = 16.
- **PC-W (full writer, tier 3.0 and taught wording).** Learned keys and content: ≥ 90% at N = 16 after clearing and restart.
- **PC-R (reader, in-context).** A separately trained reader of the same width that receives the definition or the teaching sentences in its input, with W disabled. Must reach ≥ 95% exact match on held-out composition classes (validation split) and on two-hop chains. This is trained separately because in-context and in-weights strategies trade off and a jointly trained model may learn to ignore W (Chan et al. 2022, Sec. 3.1). PC-R is also the ceiling reference: it is retrieval-from-context, made explicit.
- **PC-O (read-and-execute from W).** The evaluator writes a canonical program code (three slots, one-hot over primitives plus "none", embedded by a fixed random linear map) under the learned key; the reader is trained to execute from W. Must reach ≥ 95% on held-out classes. If PC-R passes and PC-O fails, the read-and-execute path is the blocker, not the writer.
- **PC-C (chain with teacher forcing).** Oracle-written twin and constant entries; the second-hop key is injected by the evaluator. Must reach ≥ 90%. Separates "cannot re-key from a retrieved value" from "cannot chain at all".

### Baselines

- **No-write causal control.** θ and φ frozen, W at its initial value, z fresh. Expected: unknown or chance on every taught item; ≥ 99% on primitive-only commands. Zero capacity; a causal control, not a capacity match.
- **Sham write.** β = 0 (a skipped write), used as the null for damage statistics. Not v = 0: with v = 0 the delta rule computes W (I − k kᵀ), which erases the stored component along k and is a real intervention, not a sham.
- **Byte-matched slot memory (the strong simple baseline).** 64 slots of (128-d key, 128-d value) float32, the same 65,536 bytes; softmax read; write overwrites the nearest slot above a threshold or the least recently written. This is the GRACE/Larimar-style store and, driven by the same reasoner loop, it is also the honest explicit-retrieval comparator the brief asks to make visible: the same frozen reasoner re-querying an explicit key-value store at every step. If the delta bank does not beat it, the delta bank has no advantage, though both are still parameter memories.
- **Unbounded slot store.** The same, with one slot per teaching, as an upper reference (not byte-matched).
- **Nearest-training-class predictor** for tier 3.2: the index-shortcut rate that held-out classes must exceed by a factor of three.
- **Parameter fitting.** Gradient steps on a designated small MLP memory (biases excluded, byte-matched) with replay from L at teaching time only, L unmounted at scoring. Worth comparing (section 5); not required for the milestone.

### Interventions on W (θ, φ frozen; z fresh)

1. **Zero W** → unknown or chance on taught items; primitives intact.
2. **Cross-episode swap**: score episode i's queries with episode j's W → chance; with its own W → pass. Answers must follow the persistent object.
3. **Rollback**: restore the pre-correction snapshot → the superseded answer returns. For single-item removal, re-run the teaching sequence without item j rather than subtracting its recorded delta, because later writes were computed with item j present and the subtraction is exact only for orthogonal keys.
4. **Content swap**: write vask's content under zorp's key → "zorp [ c a f b ]" must return vask's answer [ f a b c ]. This is the decisive test that W's content, not a trigger completed from θ, determines the output.
5. **Restart identity**: outputs bit-identical before and after kill-and-reload (smoke); accuracy identical (result).
6. **Log poisoning**: overwrite L with wrong sentences after teaching; scored answers must be 100% identical with and without poisoning.

### Paraphrase, interference, correction, restart

- Paraphrase: teaching and query templates are sampled independently in meta-training, so no query ever repeats a teaching's wording. Score training-template queries (threshold ≥ 90%) and T5 definitions (report; within 10 points of T1–T4 is the hypothesis). Larimar loses about eleven points between edit success and paraphrase on CounterFact even with an external memory (Das et al. 2024, Table 2), so this number is reported on its own.
- Interference: after each write, re-score every earlier item, building the accuracy matrix that GEM uses (Lopez-Paz and Ranzato 2017, Sec. 2). Threshold: signed mean change on the first 8 items after 16 further writes ≥ −5 points. The interference term for a write with strength β on key k against another key k′ is β (v − W k)(kᵀ k′) (deduction from the update rule); with random unit keys in 128 dimensions the RMS overlap is 1/√128 ≈ 0.088. Report the measured distribution of kᵀ k′ among stored keys so the damage number can be read against it.
- Correction: new answer ≥ 90%; old-answer rate ≤ 5%; same-subject other-relation items and same-value other-subject items within 5 points of the sham null. Scored only after restart, because before clearing it can be recency in z.
- Restart: all headline numbers are after restart; pre-restart numbers are reported as a leak diagnostic.
- Accumulation: second-session items and first-session items both ≥ 90% after the second restart.

### Adaptive retrieval versus extra computation

Four arms, same parameters, same bytes, same training budget, all with the W-blind writer:

- (a) key from x only, T = 6 (the draft's constant read)
- (b) key from (x, z_t), T = 6
- (c) key from x only, T = 12
- (d) key from x only, four parallel reads, T = 6

On one-hop items all four should match. On two-hop and correction-then-two-hop items the decision rule is: (b) minus the best of (a), (c), (d) ≥ 20 points, same sign on at least four of five seeds, with a paired bootstrap over episodes within each seed excluding zero. If (c) closes the gap, extra computation on a constant read suffices and the retrieval claim fails. If (a) equals (b), the loop is not doing what it is designed for. Diagnostics, not scores: ‖m_{t+1} − m_t‖ per step (identically zero in arms a, c, d) and a linear probe of z_2 for the intermediate name's code in arm (b). The MemN2N finding that more hops help on supporting-fact tasks is the precedent for the expectation (Sukhbaatar et al. 2015, Sec. 4.3), but those hops re-attend over sentences in context, so it does not settle the weight-memory case.

### Fair memory comparison

| Store | Writable object | Bytes | Nominal ceiling (deduction) |
|---|---|---|---|
| Delta bank | W ∈ R^{128×128} | 65,536 | ≤ 128 exactly recoverable associations with linearly independent keys |
| Slot memory | 64 × (128 + 128) | 65,536 | 64 if keys separate; near-duplicate keys blur into an averaged read |
| Unbounded slot store | one slot per teaching | grows | reference only |

Achieved recall capacity N95: write N distinct items once each with no replay, clear, restart, score taught wording; N95 is the largest N in {8, 16, 24, 32, 48, 64, 96, 128} with ≥ 95% recall. Meta-training must sample N up to the sweep ceiling, or N95 confounds substrate capacity with the writer's episode-length generalization; alternatively report N95 for fixed keys (PC-K) as the substrate number. Report bytes per recovered item at N95. Larimar's near-100% up to its memory size of 512 and 82% at 1,024 is the shape one might expect, but that is a least-squares write over slots with a large decoder, not this bank; treat it as a hypothesis, not a calibration.

### Thresholds, uncertainty, stopping

Units. The episode (world) is the unit for absolute thresholds in tiers 1 and 2; the program class is the unit for tier 3.2; the seed is the unit for arm and substrate comparisons. Query-level binomial intervals are anti-conservative because queries within an episode share one W and one teaching set, so intervals are cluster bootstraps over episodes or classes. Five meta-training seeds per condition; a threshold is met when the per-seed mean meets it on at least four of five seeds. Seeds that fail PC-W are reported and excluded from arm comparisons, and their count is a result.

Sample sizes fixed in advance: 200 final-test episodes per condition per seed for tiers 1–2; every test class with at least 40 discriminating operands for tier 3.2.

Thresholds (pre-registered; all after restart):

| Test | Threshold |
|---|---|
| Tier 1 paraphrase, training templates | ≥ 90% |
| Tier 1 correction | new ≥ 90%; old-answer ≤ 5% |
| Tier 1 interference | signed change ≥ −5 points; N95 reported |
| Tier 1 restart and accumulation | outputs identical; ≥ 90% both sessions |
| Tier 2 two-hop | ≥ 80%, conditional on both single hops ≥ 95% |
| Tier 2 correction-then-two-hop | ≥ 75% |
| Tier 2 arm gap (b) − best(a, c, d) | ≥ 20 points |
| Tier 3.2 held-out classes | ≥ 80% and ≥ 3 × nearest-training-class rate |
| Tier 3.1 query-time compositions | ≥ 70% |
| Tier 3 T5 paraphrase | within 10 points of T1–T4 |

Meta-training stopping. Patience is measured in whole runs: stop a condition when validation exact match has not improved by one point over four consecutive ten-minute runs, or at twelve runs. One seed per condition runs to the twelve-run ceiling regardless, so a null stopped on a plateau can be told from a null that persists. This matters because meta-learned in-context learners show long loss plateaus during which unseen-task performance is flat or worse, and a fixed-permutation fraction mixed into every batch removed the plateau in Kirsch et al. (2022, Sec. 4.3); the curriculum here is that per-batch mixture (a fixed fraction of episodes drawn from a small fixed name set, re-bound to random programs each episode), not a phase switch. Grokking on small algorithmic tables can take 10^5–10^6 steps (Power et al. 2022, Fig. 1), which the primitive-learning part of initial training may touch.

Project stopping. If PC-R fails after twelve runs and one width increase, tier 3 is deferred and reported. If PC-O fails with PC-R passing, the read-and-execute path is the blocker; report it. If PC-W fails on all seeds with the fixed-rule writer as well, the substrate or the encoder is the blocker; run the slot memory before concluding anything about W.

### Smoke test versus research result

Smoke: PC-K, PC-E, PC-W pass; gradients reach the writer; W changes on teaching and never on reading; restart is bit-identical; log poisoning agrees 100%; cross-episode swap is at chance. Passing these is engineering.

Research result: PC-R, PC-O, PC-C pass, and then the tier thresholds, the interventions, and the arm comparison, on held-out worlds, templates, classes, and operands, with cluster intervals and per-seed reporting.

| Observation | Reading |
|---|---|
| PC-K or PC-E fails | Bug or undertrained encoder; no memory claim |
| PC-R fails after width increase | Reader cannot interpret at this scale; tier 3 deferred; not evidence about W |
| PC-R passes, PC-O fails | Read-and-execute path broken; not evidence about the writer |
| PC-O passes, PC-W fails on ≥ 2 of 5 seeds | Writer training failed on those seeds; a real risk for learned writers at this scale; count reported |
| PC-W passes, tier 3.2 at the nearest-class rate | Counts against the hypothesis that W holds a compositional description; W holds an index |
| Tier 3.2 passes, content swap does not move the answer | Counts against "W carries the description"; the reader completes from θ |
| Arm (a) equals arm (b) on two-hop | Counts against adaptive retrieval as designed |
| Arm (c) beats arm (a) | Extra computation on a constant read does work; report it as such |
| Restart differs from clear-only | Hidden channel; bug |
| Correction passes before restart, fails after | Recency in z, not memory |
| Signed damage large and negative on unrelated items | Counts against delta-rule locality with learned keys; compare the slot memory |
| Slot memory matches the delta bank everywhere | The bank has no advantage; the contract stands; substrate choice is open |

### Benefit and damage, reported separately

Benefit is accuracy on newly taught items after the write minus a measured (not assumed) pre-write baseline on the same queries. Damage is the signed paired change on every previously taught item and on a frozen validation set, as in GEM's backward transfer, which is a signed average and permits positive values (Lopez-Paz and Ranzato 2017, Eq. 3 and Sec. 3). Also report counts of correct-to-incorrect and incorrect-to-correct flips, following the collateral-change analysis in Huang et al. (2023, Sec. 3.3). If a maximum-over-history forgetting figure is wanted, use Chaudhry et al. (2018, Eq. 3) and label it, since it differs from backward transfer by construction.

Clipping. The draft's D = mean(max(0, before − after)) is biased upward under the null: for zero-mean Gaussian noise with standard deviation σ, E[max(0, ε)] = σ/√(2π) (deduction). Under deterministic inference on identical items the per-item noise is zero and the bias vanishes, which is one more reason to score deterministically. Where scoring is stochastic (sampling, dropout, nondeterministic kernels), use signed paired differences, and if a one-sided figure is still wanted, subtract the same statistic measured under the β = 0 sham. No clipped term enters any training objective in this design.

Not demanded. No test asks the model to detect corrupted teaching: a well-formed wrong sentence is indistinguishable from a right one at write time, and the contract says accepted sentences are true by declaration. Contradiction handling is recency-based and tested by correction, not by the model judging truth.

### What a small budget can establish

Rough costing, labeled hypothesis: throughput for a model under two million parameters with T = 6 and a functional 128 × 128 write is on the order of 10^4 optimizer steps per ten-minute run on this GPU; several such runs can share the card.

| Trained condition | Seeds | Runs each (max) | GPU-hours (max) |
|---|---|---|---|
| Main system, arm (b), delta bank | 5 | 12 | 10 |
| Arms (a), (c), (d) | 5 each | 12 | 30 |
| Slot memory, arm (b) | 5 | 12 | 10 |
| PC-R in-context reader | 3 | 12 | 6 |
| PC-O oracle content | 3 | 12 | 6 |
| PC-K, PC-E, PC-C | 3 each | 6 | 9 |

About 70 GPU-hours at the ceiling, less if conditions converge early, spread over a few days with concurrent runs. Storage is a few hundred megabytes of checkpoints and snapshots. The smallest experiment that establishes something on its own: PC-K, PC-E, PC-W and tier 1 on the delta bank and the slot memory with three seeds, about 15 GPU-hours. That establishes persistence mechanics, correction, interference, and restart. It leaves chains, adaptive retrieval, and definitions untested, and it does not establish convergence in general; it establishes whether these conditions converge under this budget.

---

## 5. Architecture consequences

### Required by this contract

- **Memory interface.** One associative read per reasoner step, keyed from (x, z_t); one rank-1 write per accepted sentence from the encoded sentence alone; same-key overwrite with β = 1 for supersession. The delta rule provides the last (Schlag et al. 2021, Sec. 4.2). Key normalization matters for the write-and-remove balance (same section). One bank; the draft's four-bank router is a module without a requirement behind it.
- **Workspace-conditioned retrieval.** q_t = Q(x, z_t). Required by tier 2 and by the stretch query in episode B; the draft's input-only key makes those impossible by construction.
- **Shared code space.** Values stored for relations must be usable as keys: the writer's value for "the twin of blick is frim" must be in the space the encoder uses for the key of "frim". A support loss that predicts the taught object immediately after each write is the mechanism to enforce this and is included by default, with an ablation scheduled: meta seq2seq dropped from 99.95% to 5.43% without its support loss (Lake 2019, Table 2), though that is an in-context memory and the analogy is a hypothesis.
- **Writer and its signal.** Inputs: x_teach only. Outputs: (k, v). Training: cross-entropy on post-clear queries backpropagated through the functional write, the bi-level structure CaMeLS uses to train a weighting model through post-update question answering (Hu et al. 2023, Sec. 3.2) and Metalearned Neural Memory uses to train its writer through post-write reads (Munkhdalai et al. 2019, Sec. 3.5). No target-answer embedding, no RL heads, no skip head. With no oracle checker and no answer in the definition, the "write the label" degeneracy the earlier review identified has nothing to feed on; what remains is index collapse, which tier 3.2 detects.
- **Stopping.** Fixed T = 6, accuracy reported per step. The halting head is removed from milestone one. A "stuck" output is scored wrong, so the model cannot opt out of hard queries.
- **Language interface.** Controlled English over one shared vocabulary; character-level names; exact-match answers from a closed output space including "unknown"; no free-form generation and no explanation output.
- **Clearing and restart harness.** z reset after every teaching and before every query in meta-training exactly as at scoring; kill-and-reload; unmount L; log-poisoning check; bit-identity check.
- **Practice harness.** A fixed scheduler, the audit log, a one-bit checker, and a primitive executor, available in practice only. No learned gate.
- **Storage guard.** The draft's 100 GB constants and run.py's 10 GB defaults disagree; pick one and log peak bytes per run.

### Worth comparing experimentally

- Delta bank versus byte-matched slot memory; versus parameter fitting with replay.
- Learned β (Schlag et al. 2021, Eq. 21) versus β = 1.
- A decay gate (Gated DeltaNet's α_t; Yang et al. 2024, Eq. 10), expecting a retention cost: in the single-needle case study, decay hurt retention while the pure delta rule held (Sec. 3.2, Table 2). Not needed for correction.
- Learned versus zero W_0 (learning W_0 improved training stability in TTT layers; Sun et al. 2024, Sec. 2.7).
- A W-reading writer (consolidation at write time), scored against the W-blind writer on tier 2, with the understanding that it trades adaptive retrieval for write-time inference.
- Bidirectional writes for reverse queries.
- Deep (MLP) memory versus linear W; a matrix memory is an online linear regressor and two-layer MLPs are strictly more expressive (Behrouz et al. 2024, Sec. 3.1), relevant mainly to tier 3.
- Random versus zero z_0 with input injection at every step (Geiping et al. 2025, Sec. 3.1).
- Learned or zero-shot halting only after fixed-T results exist: ACT is quite sensitive to its time penalty (Graves 2016, Sec. 2.1); PonderNet uses a KL to a geometric prior rather than a step penalty (Banino et al. 2021, Sec. 1); a divergence-between-successive-steps exit needs no training (Geiping et al. 2025, Sec. 6.1).

### The bridge to reusable method learning, stated plainly

If tier 3.2 passes, W holds a description that the frozen interpreter executes on inputs and in compositions that did not exist at write time, including compositions never executed in initial training. That is composing familiar operations from a stored instruction, persisted in weights. The next experiment on the same reader and W is contract D: replace the definition with three or four demonstrations, so induction is the only new capability, with discriminating operands and the nearest-training-class rate as the shortcut baseline.

Beyond that the bridge is weak, and I say so. A genuinely new primitive cannot be represented by a pointer into θ's operation set; it needs W to hold executable structure, and the closest precedent, a feed-forward memory network written by meta-learned local rules (Munkhdalai et al. 2019, Secs. 3.2–3.4), has not been shown to hold procedures rather than key–value maps. Both meta-learning precedents for systematic generalization state that they do not handle unpractised forms (Lake and Baroni 2023, Discussion; Lake 2019, Sec. 5). Grokking shows new operations being fit by gradient descent over up to a million steps (Power et al. 2022), which is parameter fitting, not a write. Chollet's definition of developer-aware generalization difficulty, the fraction of the evaluation-time solution not explained by the shortest training-time solution plus the system's initial state (Chollet 2019, Sec. II.2.1), is the standard later milestones should be held to; tier 3.2 has small but nonzero difficulty under it, and a new-primitive test would have more.

If tier 3 is deferred because PC-R fails, milestone one is tiers 1 and 2, and the bridge to methods is the tier 3 experiment with a stronger reader. Whether a stronger reader means a wider recurrent network or a small pretrained language model is a separate decision under the brief's compute rules.

---

## 6. Decision record

**Recommended first milestone, one sentence.** Meta-train a character-level encoder, a fixed-depth recurrent reasoner with workspace-conditioned retrieval, and a W-blind writer that makes one rank-1 write per English sentence into a 128 × 128 delta memory, then show on held-out worlds, templates, composition classes, operands, and a process restart that constants survive paraphrase, correction, interference, and a second session; that a corrected intermediate fact changes the answer to a two-hop chain only when the key of the second retrieval can depend on the first; and, if the in-context reader control passes, that a procedure defined once in English executes on unseen operands and in unseen compositions.

**Exact claim success would support.** With θ and φ frozen after initial training and z cleared, one-shot writes into a 65,536-byte editable memory store bindings and descriptions that survive clearing, restart, and a further session; are reachable from unseen wording; serve as keys for a second retrieval; are superseded by flagged corrections with the change propagating through chains; and, for definitions, select an ordered composition of meta-trained primitives that a frozen interpreter executes on operands and in compositions absent at write time, including composition classes never seen in initial training; with the information demonstrably carried by W (zero, swap, rollback, content swap) and not by z, θ, or any record available at scoring; at an accuracy above a byte-matched explicit slot store driven by the same reasoner; with a measured recall capacity and a measured, signed cost to earlier items.

**Strongest claim it would NOT support.** That the system acquires new procedures: every primitive, the composition depth, the definition format, and the interpreter were meta-trained, and W holds descriptions and bindings, not executable structure. It would also not support learning in θ after initial training; lifelong accumulation beyond a few sessions with a zero-initialized W; learning from pass/fail feedback alone, since every milestone-one teaching contains what it teaches; open English; or background practice that discovers anything, since practice is log-verified re-teaching.

**Three most important unresolved risks.**
1. Meta-training may not converge inside the chained budget, especially for tier 2 re-keying and the tier 3 interpreter, which sit behind the plateau that meta-learned in-context learners show; the positive-control ladder makes a null interpretable but does not make it positive.
2. Tier 3.2 may pass through a writer that stores an index and a reader that maps indices to trained programs plus a mild interpolation; the held-out classes, discriminating operands, and content swap are the detectors, and with a few dozen test classes they have limited power.
3. The delta bank's capacity and interference with learned, non-orthogonal keys may make tier 1 fail for reasons a slot memory would not share; the contract is substrate-neutral so the store can be swapped, but a failure there would consume budget before the tests that matter.

**Smallest observation that would change the recommendation.** PC-R failing to reach 95% on held-out composition classes on all seeds after twelve chained runs and one width increase. That would show the interpreter, not memory, is the bottleneck at this scale; I would then recommend tiers 1 and 2 alone as milestone one and treat the reader as the next research object. A second, cheaper trigger: if arm (a) matches arm (b) on correction-then-two-hop with the W-blind writer, the retrieval loop is not doing the work it is designed for, and the architecture question would come before any further memory experiment.

---

## 7. Evidence and provenance

Method. The draft code and both prior reviews were read directly. Thirteen source groups were fetched from arXiv abstract and full-text pages (or the open-access Nature page for MLC) by verification agents that quoted the supporting passage and its section; every passage relied on above was read by me from those reports, and the digest is saved under reviews/2026-09-17-contract/evidence_digest.md. Citations in this memo point to sections, not titles. Statements marked deduction are mathematics; statements marked hypothesis are mine and untested.

Verified findings used (author, year, arXiv or venue, and where the passage is):
- Yao et al. 2023, arXiv:2305.13172, Sec. 2 (reliability, generalization, locality), Sec. 5.1 (portability: subject replace, reversed relation, one-hop), Sec. 5.2 (distract-neighbor locality).
- Zhong et al. 2023 (MQuAKE), arXiv:2305.14795, Sec. 1, Sec. 4.2 and Table 3 (MEMIT 96.2 edit-wise vs 7.0 multi-hop on GPT-J), Sec. 5.1 (MeLLo is explicit memory plus decomposition).
- Cohen et al. 2023 (RippleEdits), arXiv:2307.12976, Sec. 3 (six ripple criteria), Sec. 5.2 (editors at 38–66 average).
- Lopez-Paz and Ranzato 2017 (GEM), arXiv:1706.08840, Sec. 2, Eqs. 2–4 (signed BWT), Sec. 3 (positive backward transfer allowed).
- Chaudhry et al. 2018, arXiv:1801.10112, Sec. 3, Eq. 3 (max-based forgetting).
- Lake and Baroni 2018 (SCAN), arXiv:1711.00350, Experiment 3 (add-primitive split; best 1.2% on jump; the isolated primitive was over-sampled).
- Lake 2019 (meta seq2seq), arXiv:1906.05381, Sec. 3, Sec. 4.1, Sec. 4.3, Table 2 (99.95% with support loss, 5.43% without; 10,000 episodes, under one hour on one Titan X; in-context memory, no weight updates after meta-training).
- Lake and Baroni 2023 (MLC), Nature 623:115–121, Modelling results and Methods (study examples in the input; weights frozen at test; 1.4M parameters; 100,000 training episodes; wall-clock not stated), Discussion (no mechanism for new symbols; fails unpractised forms).
- Santoro et al. 2016, arXiv:1605.06065, Sec. 2 (time-offset labels; labels shuffled per episode), Sec. 4.2.1 (memory wiped between episodes).
- Weston et al. 2015 (bAbI), arXiv:1502.05698, Sec. 3 and Table 1; Sukhbaatar et al. 2015, arXiv:1503.08895, Sec. 4 and Table 1 (weak supervision; more hops help; task 3 hardest).
- Yang et al. 2024 (DeltaNet), arXiv:2406.06484, Sec. 2.2 (one SGD step on the online regression loss), Sec. 3.3 (I − β k kᵀ has eigenvalue 1 with multiplicity d − 1).
- Yang, Kautz, Hatamizadeh 2024 (Gated DeltaNet), arXiv:2412.06464, Eq. 10, Sec. 3.2 and Table 2 (decay hurts retention; gating clears).
- Schlag, Irie, Schmidhuber 2021, arXiv:2102.11174, Sec. 4.1 (capacity bounded by key dimension; errors from about 60 associations at d = 64), Sec. 4.2 (delta rule as write plus remove; learned β).
- Huang et al. 2023, arXiv:2310.01798, Sec. 1 and Sec. 3.2 (intrinsic self-correction degrades; oracle labels behind earlier gains), Sec. 3.3 (flip analysis).
- Zelikman et al. 2022 (STaR), arXiv:2203.14465, Secs. 3.1–3.2 (answer hint; retrain from base each iteration).
- Zhao et al. 2025 (Absolute Zero), arXiv:2505.03335, Abstract and Sec. 3.1 (executor as verifier; proposer reward), Sec. 4.1 (pretrained base models).
- Allen-Zhu and Li 2023, arXiv:2309.14316, Secs. 4.1–4.2 (memorized but not extractable without augmentation).
- Berglund et al. 2023, arXiv:2309.12288, Sec. 2.1.2 (reversal at chance after fine-tuning), App. B.6 (in-context reversal works).
- Hu et al. 2023 (CaMeLS), arXiv:2305.15076, Sec. 3.1 (no query access at update time), Sec. 3.2 (bi-level objective with locality term).
- Munkhdalai et al. 2019 (Metalearned Neural Memory), arXiv:1907.09720, Secs. 3.2–3.5 (memory as a network; learned local updates; post-write meta-objective; tabula rasa per episode).
- Miconi et al. 2018 and 2019, arXiv:1804.02464 and arXiv:2002.10585 (plastic components; network-generated gate).
- Power et al. 2022 (grokking), arXiv:2201.02177, Sec. 1 and Fig. 1.
- Chollet 2019, arXiv:1911.01547, Sec. I.3.2 (developer-aware generalization), Sec. II.2.1 (skill-acquisition efficiency; difficulty definition).
- Graves 2016 (ACT), arXiv:1603.08983, Sec. 2.1; Banino et al. 2021 (PonderNet), arXiv:2107.05407, Sec. 1; Geiping et al. 2025, arXiv:2502.05171, Sec. 3.1, Sec. 3.3, Sec. 6.1.
- Sun et al. 2024 (TTT), arXiv:2407.04620, Sec. 2.7; Behrouz et al. 2024 (Titans), arXiv:2501.00663, Sec. 3.1 and Sec. 3.3; Ramsauer et al. 2020, arXiv:2008.02217, Abstract and Theorem 3.
- Lin et al. 2025 (sparse memory finetuning), arXiv:2510.15103, Abstract and Sec. 4; Das et al. 2024 (Larimar), arXiv:2403.11901, Sec. 2.2, Sec. 5.4, Table 2; Hartvigsen et al. 2023 (GRACE), arXiv:2211.11031, Sec. 2.2.
- Chan et al. 2022, arXiv:2205.05055, Sec. 3.1 and Sec. 4; Kirsch et al. 2022, arXiv:2212.04458, Sec. 4 and Sec. 4.3.

Corrections to claims that circulated in earlier drafts: Chan et al. do not show that fixed per-class labels suppress in-context learning; fixed labels are their default and in-context learning still emerges under burstiness with many rare classes. The correct use of that paper here is that fixed bindings make context-based and weight-based strategies indistinguishable, and that models drift toward in-weights learning with repetition. Kirsch et al.'s plateau remedy is a fixed-permutation fraction in every batch, not a two-phase curriculum.

Not verified and not relied on: wall-clock training time for MLC (not stated in the paper); any claim that a delta bank of this size shows Larimar's degradation shape; any throughput figure for this GPU (labeled hypothesis above).

No experiment, code inspection beyond the files named, or independent human review is claimed.
