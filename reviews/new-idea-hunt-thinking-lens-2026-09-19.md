> **Orchestrator note (Claude, 2026-09-19).** How this was produced: 8 idea generators with different source-field lenses (32 raw ideas) + 7 seeds -> triage to 14 -> a prior-art hunt per idea (18-41 searches each, every cited link opened) -> second independent hunt + fit/scale critique for anything not killed -> 3 judges -> write-up -> citation check, mechanism red-team, experiment critique -> this revision. 33 agents.
>
> Caveats. (1) Hunters were told to take the harsher verdict when unsure, so "mostly exists" means: the core mechanism is published and only the port to a tiny from-scratch store-reasoner is not. Their novelty estimates were 12-30%. (2) The WebSearch quota ran out before the final verification pass, which fell back to arXiv/OpenAlex keyword APIs plus direct page fetches. (3) I re-opened five citations myself, including all four 2026 preprints in the table (2604.21632, 2607.23019, 2608.02680, 2604.25166) and Lee et al. 1909.11851; all are real and match their descriptions.
>
> My own reading. The "near-miss" in section 4 got there on a technicality (it was the only idea rated PARTIAL on the first hunt) and is off-target for the open problem. The most *useful* dead idea is #1, residual-question closure: delete the dedicated hop-2 request builder and require the workspace after a fetch to equal the reader's own encoding of the simpler question that remains ("What colour are Oren's shoes?", which the simulator can author). That turns held-out two-step into practised one-step. It is published (Lee et al. 2020; Markov Chain of Thought; TreeHop) and already in the notes as H2, so it is a known thing worth running, not a new idea.

# Final report for Ben: nothing survives

**0. Status line.** Web: WebFetch worked and WebSearch was unavailable (session budget exhausted, 200 of 200), so discovery used keyword queries on the arXiv and OpenAlex APIs and coverage is thin. Verdict: **nothing survives**. All 14 shortlisted ideas already exist or mostly exist, and the best near-miss is a known technique with about a 12% chance of being new. No runner-up takes its place.

Every link below was opened by me in this pass, or by the citation checker or dossier hunters, and its content matched the description.

---

## 1-3. Candidates and how they died

All 14 shortlisted candidates are listed below. "Mostly exists" means published work already covers the core mechanism for the same purpose. What is left in those cases is a port to your setting and does not amount to a new kind of idea.

| # | Candidate | Closest existing work | Verdict |
|---|---|---|---|
| 1 | **Residual-question closure:** after each hop, the thought must equal the reader's own encoding of the simpler question that remains. | Lee et al., "Mathematical Reasoning in Latent Space", ICLR 2020, https://arxiv.org/abs/1909.11851 (the same loss almost word for word). Text version: "Markov Chain of Thought", https://arxiv.org/abs/2410.17635. Architecture skeleton: TreeHop, https://arxiv.org/abs/2504.20114. | **Mostly exists.** It is also already in your own notes as H2, "teach a second lookup to reuse the standalone lookup" (path under Sources). |
| 2 | **E-graph workspace:** the workspace is a term graph with equivalence classes, and a fixed rule generates every follow-up request. | egglog, PLDI 2023, https://arxiv.org/abs/2304.04332 (the whole symbolic core). Talmor & Berant, SplitQA, NAACL 2018, https://aclanthology.org/N18-1059/ (pointer parse plus a fixed substitution rule). | **Mostly exists.** |
| 3 | **Gauge-equivariant anonymous atoms:** words are random codes that the reasoner may only compare by dot product. | Webb et al., ESBN, ICLR 2021, https://arxiv.org/abs/2012.14601. Lazic et al., "To See the Unseen", 2026, https://arxiv.org/abs/2604.21632. | **Mostly exists.** It also sits in the relational-bottleneck family your brief lists as known. |
| 4 | **Lexicon by decipherment:** new words are assigned to old roles by code-breaking, with no weight change. | Cardenas et al., NAACL 2019, https://arxiv.org/abs/1904.05426. ULTRA, ICLR 2024, https://arxiv.org/abs/2310.04562. | **Mostly exists.** |
| 5 | **Thought-invariant mining:** mine the equalities that hold in every correct trace, then enforce them. | "Reason Popper-ly", 2026, https://arxiv.org/abs/2607.23019. TraceCompiler, 2026, https://arxiv.org/abs/2608.02680. | **Mostly exists.** The residual is small: role-position templates that carry over to unseen kinds. |
| 6 | **Syndrome-decoded junction checks:** many tiny local checks locate the wrong field in a trace. | Oarga & Du, NeurIPS 2025, https://arxiv.org/abs/2510.20607. PARC, ICML 2025, https://arxiv.org/abs/2502.02362. | **Mostly exists.** |
| 7 | **Spend-once ledger:** each question word is spent exactly once, and the second request is what is left over. | Zhou et al., IRN, COLING 2018, https://arxiv.org/abs/1801.04726. AIR, ACL 2020, https://arxiv.org/abs/2005.01218. Constrained attention, ACL 2018, https://aclanthology.org/P18-2059.pdf. | **Mostly exists.** |
| 8 | **Procedure cards with a meta-trained interpreter:** skills are stored as data, and the weights only fetch, decode and execute them. | "Training Transformers as a Universal Computer", 2026, https://arxiv.org/abs/2604.25166. CBR-KBQA, EMNLP 2021, https://arxiv.org/abs/2104.08762. | **Mostly exists.** |
| 9 | **Frozen-code plasmids:** a fixed random interface code lets trained modules be copied between models. | LegoNN, https://arxiv.org/abs/2206.03318. Bochkov, "Growing Transformers", 2025, https://arxiv.org/abs/2507.07129v1. | **Mostly exists.** |
| 10 | **Facts are answered questions (lens-law telling):** one path serves both reading and writing, with round-trip laws as a training signal. | Kaplan & Davidson, ACL 1981, https://aclanthology.org/P81-1031/. TPR-RNN, https://arxiv.org/abs/1811.12143. | **Partial** on the first hunt and **mostly exists** on the second. Killed for fit as a bundle of ideas. It was the only candidate to reach the judges, and 3 of 3 voted no. Section 4 covers its one-idea core. |
| 11 | **Suppositional overlay store:** a throw-away what-if layer sits over the card store. | MQuAKE / MeLLo, EMNLP 2023, https://arxiv.org/abs/2305.14795. CLEVRER NS-DR, https://arxiv.org/abs/1910.01442. | **Mostly exists.** |
| 12 | **Sleep-time completion:** a rewrite-rule normaliser is learned from behavioural equivalence. | Wang et al., Voxelurn, ACL 2017, https://arxiv.org/abs/1704.06956. QuickSpec 2, https://smallbone.se/papers/quickspec2.pdf. | **Mostly exists.** |
| 13 | **Store compression as the sleep objective:** count how many cards can be thrown away. | SInC, https://arxiv.org/abs/2107.00729. KGist, WWW 2020, https://arxiv.org/abs/2003.10412. Neural Theorem Provers, https://ar5iv.labs.arxiv.org/html/1705.11040. | **Mostly exists.** |
| 14 | **Transfer-selected wire search:** breed small wires and select them on generalisation after learning. | NAS-OoD, ICCV 2021, https://arxiv.org/abs/2109.02038. Liska et al., 2018, https://arxiv.org/abs/1802.06467. | **Mostly exists.** |

**Dropped or merged at triage, before the prior-art hunt.** The prior-art names in this list come from the triage notes and were not link-checked.

- **The shrinking question** and **Endosymbiotic self-call:** well-known answer-substitution decomposition (DecompRC, Self-Ask, least-to-most).
- **Cards as rewrite rules:** merged into #2.
- **Problem-manifold closure:** merged into #1.
- **Synchrony-tagged thoughts** and the four arbitrary-symbol / anonymous-atom / rotation-gauge variants: merged into #3.
- **Chain-boundary conservation**, **Freivalds checksums** and **linear-logic accounting:** merged into #7.
- **The three skill-card / stored-program variants:** merged into #8.
- **Skill acquisition as list decoding:** Latent Program Network and Latent Programmer already exist, and its author rated it the least novel.
- **Switched-linear thought dynamics:** a weak bet, since closed-form continual learning and DMD exist.
- **Lineage-tracked consolidation:** truth maintenance and provenance, with no gain in reasoning.
- **Path-integrated coordinates:** a recombination of TransE/RotatE and the Tolman-Eichenbaum Machine that does not address the measured failure.
- **Cerebellar dry run:** a small gain, and a type check cannot tell shoes from hat.
- **Corollary-discharge source tags:** a checker with no capability gain.
- **Generational turnover / iterated-learning sleep:** directly prior-arted (Vani et al. 2021, Ren et al. 2020, Li & Bowling 2019).
- **Germinal-centre / Baldwinian wire search:** merged into #14.
- **Hindsight question authoring:** hindsight relabelling is established, and no held-out gain was predicted.
- **Copy is free, compute is taxed:** a tuning pressure that does not change the kind of model.

---

## 4. Best near-miss (did NOT survive): file a told fact at the address the reader would have searched

**The idea already exists in all but one narrow integration.** Programming languages, databases and a 1981 English-language system all evaluate a path up to its last step and then store instead of load. No paper we found does this with a small learned multi-hop reader reused unchanged as the write-addresser.

The idea is also off-target for your lens. It concerns how facts are filed, so it does not change how the model thinks, and it does not touch your open problem.

### 4.1 The idea in three plain sentences
1. When the model is told a roundabout fact such as "Mira's friend's shoes are green", it should file the card under Oren / shoes. That is the address it would have searched if the same words had been a question.
2. To find that address, it runs the question reader it already has and stops just before the last look-up. It then uses that last search request as the filing address.
3. No new weights are trained for writing, so filing can only ever be as good as reading.

### 4.2 Mechanism, tightened
Here "harness" means the ordinary code around the model, and "model" means the frozen reader.

**Stored**
- Cards are unchanged: key = (person, kind of fact), value = word.
- The raw told line goes into the diary first.
- One new ledger row per filing is required. It records which bridge card the filing depended on, the snapped key, and the snap margin.
  - Without it, a card cannot be re-filed when the friend changes or the reader improves.
  - So the ledger gets more complicated. The draft claimed the opposite.

**Computed at telling time**
1. **Recognise and split.**
   - The harness recognises the line as a telling and splits it into subject phrase and value.
   - It hides the value from the reader.
   - This is the mode bit, the switch between "answering" and "filing". It lives in the harness, so the draft's "no mode bit" was wrong.
2. **Rewrite and count hops.**
   - The harness rewrites the subject into the trained question template.
   - This step is the published trick of Levy et al. 2017, https://arxiv.org/abs/1706.04115.
   - The harness then counts hops from the possessives.
   - A one-hop line is filed literally, as it is today.
3. **Run the reader (two hops).**
   - Request 1 fetches normally.
   - Request 2 is intercepted, meaning it is captured before its fetch happens.
   - The model may disagree with the harness hop count by halting early or never emitting a second request. In that case the line is logged as "disagree", stays in the diary and counts as wrong.
4. **Snap the request to a legal address.**
   - The request-2 vector is compared with the key vector of every legal address. That is all P people × K kinds, a closed list supplied by the harness.
   - For an address with no card yet, the key comes from running the card-maker's key encoder on a synthetic line for that address.
   - That is only valid if keys ignore the value. Your 19 Sept evidence note measured 1.6% of pooling weight on the value token in one retrieval-trained seed. If that holds, average the key over all V values.
   - If the request has separate person and kind fields, snap each field separately and report both. Otherwise snap the single vector.
   - Record the margin between the best and second-best address.
5. **Write the card.**
   - The harness decodes the snapped address to symbols and synthesises the standard line "Oren's shoes are green".
   - It passes that line to the normal card-maker, so the value is encoded exactly as in training.
   - Log any write that lands on a card holding a different value.
6. **No bridge card.**
   - The store always returns its nearest card, so "no bridge found" cannot be detected as specified.
   - Detecting it needs a new, uncalibrated no-match threshold or simulator truth, and simulator truth is a leak.
   - The probe below always supplies the bridge, so this case is out of scope. In real use it is an unsolved extra part.

**Trained**
- Nothing new is trained. The reader keeps its existing simulator-checked question-answering signal.
- The write path has zero parameters and zero gradient, so no learning signal flows through it.

**At inference**
- A later direct question such as "What colour are Oren's shoes?" makes one request and fetches Oren/shoes.

**What this spec shows (established)**
- The harness does the parsing, template choice, hop count, interception, address list and card creation.
- The reader contributes exactly one thing, the request-2 vector. It is acting as a neural stand-in for a symbolic resolver.
- The buildable version also carries three extra mechanisms: a closed-grid quantiser, a no-match detector and an overwrite log.
- I dropped three parts of the original candidate because they made it a bundle: placeholder keys, lens laws as a training signal, and clarifying questions.

### 4.3 Change in kind? What should jump?
**It is not a change in kind (established).**
- It is a content-addressed write into a key-value memory, with the address produced by a multi-hop read.
- That is a sub-case of memory networks and pointer dereferencing, which your brief already lists as known.
- The snap grid is a fixed codebook, which is also on that list.

**What moves.** One thing moves: "told compositely, asked directly". It rises from the no-card floor to at most the reader's joint accuracy on request 2. "Joint" means right person and right kind, decoded against all P×K addresses. (plausible; an upper bound; nothing was run)

| Condition | Exact write-key correctness | Status |
|---|---|---|
| Practised kinds, trained seed, no wire, 12k steps | At most that seed's joint request-2 accuracy. This is expected to be high but has never been measured against the full address grid. | plausible |
| Seed that never learned | About 0. | plausible |
| Held-out kinds, no wire | At most your right-kind counts of 72, 84, 8 and 1 of 171. | upper bound from your numbers |
| Held-out kinds, with wire | Unknown. Your 146-171 of 171 counts right kind only, from 4,000-step runs where the first hop collapsed in 3 of 5. Wire at 12k has never been run. | unknown |

**Why I believe this.**
- The same frozen weights on the same input give the same request vector. (established, but only up to the vector)
- The decode then changes from "nearest among a story's few cards" to "nearest among all possible addresses". That change can only lower accuracy. (plausible)

**What does not move.** Samples needed to learn a skill, reliability on unseen combinations, intelligence per parameter, and forgetting all stay where they are.

**Source of the measured numbers.**
- The 72/84/8/1 and 146-171 counts come from your brief, as quoted by the draft and reviewers.
- I could not find them in this worktree, so I did not re-check them.

### 4.4 Five closest prior works and exactly what differs
1. **Kaplan & Davidson, "Interpreting Natural Language Database Updates", ACL 1981.** https://aclanthology.org/P81-1031/ (the checker read the PDF text)
   - What it does: it handles updates phrased through a derived relation, for example "CHANGE BROWN'S MANAGER FROM JONES TO BAKER". It lists candidate base-table updates and ranks them by side effects.
   - Correction to the draft, from the checker's reading of the worked example:
     - Dereference-then-write was one listed candidate, and the system rejected it because it would also have changed Adams' manager.
     - The system instead rewrote the bridge fact, moving Brown to another department.
   - What differs: it uses a hand-written grammar over a relational database, and nothing is learned.
2. **Schlag, Munkhdalai, Schmidhuber, "Learning Associative Inference Using Fast Weight Memory", Nov 2020.** https://arxiv.org/abs/2011.07831, full text https://ar5iv.labs.arxiv.org/html/2011.07831 (both opened by me)
   - What it does:
     - One LSTM hidden state emits both the write keys and the read queries.
     - Reads are chained, with the retrieved value becoming a key in the next query (N_r = 3).
     - Each write first retrieves and removes the old value.
   - What differs:
     - Write keys are a direct linear projection of the hidden state through their own matrix.
     - They are never produced by reading through memory.
     - The write path has trained parameters.
   - Its predecessor TPR-RNN has the same residual: https://arxiv.org/abs/1811.12143 (the dossier lists NeurIPS 2018; not confirmed in-session).
3. **Semantic Machines, "Task-Oriented Dialogue as Dataflow Synthesis", TACL 2020.** https://arxiv.org/abs/2009.11423 (abstract opened by me)
   - What it does: a learned parser emits programs with "metacomputation operators for reference and revision". That is a learned update containing a reference sub-computation.
   - What differs:
     - It has an explicit program and a symbolic executor.
     - Its parser is trained on update utterances.
     - It does not reuse a question reader with zero extra parameters.
4. **Das et al., "Building Dynamic Knowledge Graphs from Text using Machine Reading Comprehension", 2018.** https://arxiv.org/abs/1810.05682 (abstract opened by me; the page says "ICLR 2019 submission")
   - What it does: a question-answering reader is the component that fills the store.
   - What differs:
     - The reader reads the passage and does not read the store.
     - It supplies the value and does not supply the address.
     - It is trained for that job.
5. **Mei, Mao, Wang, Gan, Tenenbaum, "FALCON", 2022.** https://arxiv.org/abs/2203.16639 (the dossier lists ICLR 2022; not confirmed in-session)
   - What it does: teaching sentences and questions share one grammar and one executor. The executor first locates the object a sentence refers to, then writes a concept embedding.
   - What differs:
     - The reference is resolved against a visual scene, with no chained fetches from a fact store.
     - What it writes is an embedding. It does not write a card at a standard key.

**Also close, one line each**
- Neural Turing Machines, https://arxiv.org/abs/1410.5401 (opened by me). The point that its controller's write key can depend on earlier reads is from memory.
- Recurrent Entity Networks, ICLR 2017, https://arxiv.org/abs/1612.03969 (opened by me).
- Learned pointer dereferencing:
  - Neural Random-Access Machines, Nov 2015, https://arxiv.org/abs/1511.06392. It has no language.
  - PANM, 2024, https://arxiv.org/abs/2404.11870. It extends pointer dereferencing to question answering and translation.
- The Referential Reader, ACL 2019, https://arxiv.org/abs/1902.01541.
- Guu et al., EMNLP 2015, https://arxiv.org/abs/1506.01094. Training on path queries improves single-edge answers, which is the same phenomenon reached through gradients.
- Panini, https://arxiv.org/abs/2602.15156. It is a single unrefereed preprint that names reconciliation by a memory-navigating agent as future work.
- Four systems with separate or name-matching writers:
  - MemLLM, https://arxiv.org/abs/2404.11672
  - Zep, https://arxiv.org/abs/2501.13956
  - Mem0, https://arxiv.org/abs/2504.19413
  - Memory-R1, https://arxiv.org/abs/2508.19828
- GMeLLo, https://arxiv.org/abs/2408.15903.

**From memory, unverified, no link given**
- L-value evaluation in compilers. Evaluating `mira.friend.shoes = green` runs the path evaluator to the last step and then stores. This is the mechanism exactly.
- Heim's File Change Semantics.
- Levesque's TELL/ASK interface.
- Entity linking during knowledge-base population.

**Exact residual.** No work we found computes a neural write key by running the model's own multi-hop read chain and using the final read query as the address, with zero write parameters. The checker ran 22 keyword queries with no exact hit. WebSearch was unavailable, so the absence of a hit is weak evidence.

### 4.5 Honest confidence
- **(a) New to the world: 12%.**
  - Roughly 55% that no paper implements the exact narrow integration.
  - A knowledgeable reviewer would still most likely call it l-value evaluation, view update or FWM-style shared-controller memory under a new name.
  - This is below the hunters' 30% and 17% because the checker later found closer neighbours: FWM, dataflow synthesis, Levy-style question rewriting, and write-time retrieval in Zep and Mem0.
  - The judges voted 3 of 3 "does not survive". Their mean score was 13 on a scale not stated in my inputs, so I do not lean on it.
- **(b) Works at your scale: 15%** for the idea as first proposed, where the reader handles statement wording itself.
  - That step has no training signal, because the gradient would have to cross a non-differentiable snap and write.
  - There is no supervision on statement wording.
  - The model would need its own mode bit.
  - For the harness-assisted probe below, my rough guess is 40% (speculative, no derivation). Step 0 replaces that guess in a minute.
  - The chance it produces a large gain in anything you care about is 5% or less.

### 4.6 Cheapest decisive experiment (card task only; says nothing about the village model)

**Check first.**
- Find out how your existing "right person / right kind" counts were decoded.
- If they were already decoded against all P×K addresses, the answer is known and Experiment F adds nothing. In that case skip it.

**Step 0 (minutes, no writing, no new harness)**
- Use the five frozen no-wire 12,000-step checkpoints.
- Take the request-2 vectors for the existing 171 practised and 171 held-out two-step test questions.
- Snap each vector against all P×K address keys.
- Count exact joint matches against simulator truth. This count predicts mark M1.

**Experiment F (filing probe)**
- **Baseline (Arm 0):** the five existing no-wire 12k checkpoints, frozen. The composite line goes to the diary only, and no card is written.
- **The one change (Arm B):** read-address filing, exactly as in 4.2.
- **Eligibility gate, fixed now.**
  - On the existing 171 practised two-step questions, a seed is eligible if it meets both marks:
    - It answers at least 163 (95%).
    - Its first request fetches the friend card at least 163 times.
  - All five seeds are reported either way.
  - At least 4 eligible seeds are needed. If there are fewer, train seed 6 and then seed 7 with the same recipe.
  - If there are still fewer than 4, the verdict is "not testable yet". That is not a fail of the idea.
- **Items.**
  - There are 171 tellings, each built from one existing practised two-step test question.
  - Each telling keeps the same story cards with the target card deleted.
  - The store is dense around the target:
    - Every other kind for the bridge person holds a card with a different value.
    - The same kind for the asker (Mira/shoes) also holds a card with a different value.
    - The likeliest misfiles therefore hit a real card and get counted.
  - The value is random from a fixed seed, identical across model seeds.
  - The direct question runs as a fresh pass.
  - "Unfiled" and "disagree" count as wrong, and the denominator is always 171.
  - Write down P, K and V before running.
- **Primary metric:** exact write key, with person and kind both right, checked against simulator truth.
- **Pass marks**
  - **M1:** exact key at least 154/171 (90%) in every eligible seed.
  - **M2:** tellings that change any existing card at most 9/171 (5%) in every eligible seed. Every misfile is reported, whether or not it hit a card.
  - **M3 (leak check):** the Arm 0 direct-question score is at most 171/V + 9.
  - **M4 (plumbing):** for each item, the write key equals the Step-0 snapped request on the matching question, at least 168/171. 171 is expected.
- **Reference arms and figures, reported with no pass mark and not part of the verdict**
  - Answer accuracy. This is secondary, because nearest-card retrieval forgives misfiles.
  - Arm C, a 20-line symbolic resolver. This is the ceiling, expected at 171/171.
  - Arm D, an oracle-key write followed by a read-back. It separates read-back error from write-key error.
  - Held-out kinds.
  - Any wire checkpoints.
  - P×K and the key margin.
- **Verdicts**
  - **Pass:** M1 to M4 are all met.
  - **The idea is wrong at this scale:** M1 or M2 is missed in two or more eligible seeds. That means a request good enough to pick among a story's few cards is too imprecise to be an address among all possible cards.
  - **Unclear:** exactly one eligible seed misses. Add seeds 6 to 8 and apply the same rule.
  - **No verdict:** M3 or M4 is missed. The harness is invalid, so fix it and rerun.
  - **I am wrong about "writing is just reading":** M4 still fails after the harness has been checked. That means the reader's request depends on store contents in a way I did not expect.
- No outcome of this probe can show a large gain.
- **Cost.**
  - The evaluation takes minutes, plus the new harness code, with no cloud spend.
  - Training is needed only if fewer than 4 seeds are eligible.

### 4.7 What it would replace, and how to introduce it one step at a time
It replaces nothing you have built.
- It would make a future separately trained writer for roundabout statements unnecessary, but only while the hand-written parser exists.
- It does not simplify the told-ledger or de-duplication:
  - Filings now depend on bridge cards.
  - The store depends on the order in which facts were told.

Steps, with marks fixed before each run:
1. **Experiment W first.** This is your own pending run. It is not a new idea and not part of this near-miss.
   - Design: wire on versus the existing no-wire 12k runs, five seeds, all counted, no screening.
   - Marks:
     - Practised two-step at least 154/171 in at least 4 of 5 seeds.
     - First request fetches the friend card at least 154/171 in at least 4 of 5 seeds.
     - Held-out right kind at least 146/171 in at least 4 of 5 seeds.
     - Held-out answers at your existing pass mark in at least 3 of 5 seeds.
   - A seed is dead if practised one-step is below 50% at 12k. A dead seed counts as a fail.
   - Proved wrong if the first-request mark is missed in two or more seeds. That would mean the wire's side effect is not just undertraining.
   - W speaks to the two-hop milestone and F cannot.
2. Step 0.
3. Experiment F. It is optional and should never go ahead of the second-request work.
4. Only if F passes, test the update case: the target card already exists with an old value, and the siblings must not change.
5. Only if step 4 passes, retry unfiled lines once the bridge is told. This needs the no-match detector, which is a new mechanism.
6. Much later, split the removal of the harness into parts and do one at a time:
   - First remove only the template rewrite, so the reader sees statement wording.
   - Then remove the subject/value split.
   - Then remove the hop count.
   - The first part already needs training on statement wording. That contradicts "nothing new is trained", and no training signal has been specified for it.

### 4.8 The two most likely reasons it fails
1. **It inherits the reader's weakest computation and makes the errors persistent.**
   - When reading, a wrong second request costs one wrong answer.
   - When writing, it misfiles a card, and the card stays misfiled until someone rebuilds it from the diary.
   - Nothing detects the misfile, because recomputing the address gives the same wrong key.
   - If the wire collapses the first hop, the value is filed under the wrong person. (established reasoning)
2. **The harness does the real work.**
   - Card-task sentences follow a fixed pattern, so a 20-line resolver files them perfectly.
   - The neural path can at best tie that resolver.
   - Once the rewrite is removed, the reader meets wording it never trained on, with no training signal to fix it. (plausible)

Role versus person is also unsolved. "Mira's friend's shoes" may mean whoever is Mira's friend at the time. A card filed under Oren then goes stale when the friend changes. The 1981 system faced exactly this problem, and in its example it chose to rewrite the bridge instead.

---

## 5. Runner-up
There is no surviving runner-up, and nothing takes the near-miss's place. The dead candidate most relevant to your open problem is residual-question closure. However, its loss is published (Lee et al. 2019, https://arxiv.org/abs/1909.11851), its skeleton is published (TreeHop, https://arxiv.org/abs/2504.20114), and your own notes already hold a version as H2. It is therefore a known diagnostic to run later and gives you no new idea.

---

## 6. Does anything survive?
**No.** Thirteen of the fourteen shortlisted ideas mostly exist in published work. The fourteenth was killed as a bundle of ideas, and its one-idea core is a filing convention with about a 12% chance of being new and no route to a large gain.

This means we found nothing new. It does not mean nothing new exists, because the search ran without WebSearch and covered 14 shortlisted ideas plus the triage list.

The most valuable next step is Experiment W: the wire at 12,000 steps, five seeds, with the first request monitored. It is your own pending run and owes nothing to this report.

---

## 7. Plain-language version for Ben
1. I looked for one new, big idea about how your model thinks, and none passed. Fourteen were checked against published work, thirteen already exist in close form, and all three judges voted no on the last one.
2. The best near-miss is a filing rule. When the model is told something roundabout, like "Mira's friend's shoes are green", it files the card under Oren's shoes. It does not invent a label called "Mira's friend's shoes".
3. Picture a school office where a note arrives saying "the locker of Mira's lab partner is jammed". A good secretary first looks up who the lab partner is, then puts the note in that student's folder.
4. The secretary uses the same look-up skill for filing as for answering, so nothing extra is trained. You run the reader you already have, stop just before its last look-up, and store the new card at the address it was about to search.
5. Filing can therefore only be as good as reading. Your reader's weak spot is exactly that last address, on kinds of fact it never practised in two-step form.
6. A wrong address while reading costs one wrong answer. A wrong address while filing puts a card in the wrong folder and may cover a correct card, and nothing notices until someone rebuilds the card from the diary.
7. The idea is old outside neural nets. Databases and programming languages work this way. A 1981 program already listed it as one way to read such an English sentence, and in its own example it chose a different way.
8. The card task's sentences follow a fixed pattern, so a twenty-line ordinary program would file them perfectly. Passing would not show your model got smarter.
9. The check takes the five 12,000-step models you already trained and keeps only those that read at least 163 of 171 practised two-step questions. It tells each one 171 roundabout facts and counts how often the card lands under exactly the right person and kind.
10. It passes if every model that reads well files at least 154 of 171 correctly and damages at most 9 existing cards. The idea is wrong if two or more such models miss, meaning a request good enough to pick among a story's few cards is too blurry to be an address among all possible cards.
11. Treat it as a plumbing test, one that checks the pipes connect and not that the water is better. It is about the small card task only and says nothing about the village model.
12. What still matters most is what you already found: making the second search request name the right kind of fact on combinations it never practised, in every run. That is why the wire-at-12,000-steps run should go first.

**Terms, one line each**
- **Card:** one stored fact, like an index card.
- **Key / address:** the label a card is filed under (person + kind of fact).
- **Search request:** what the model writes to ask the store for a card.
- **Hop:** one look-up; a two-step question needs two.
- **Bridge card:** the card that links the chain, such as "Mira's friend is Oren".
- **Sibling card:** a nearby card, such as Oren/hat, that must not change.
- **Composite telling:** a fact stated through a chain ("Mira's friend's shoes...").
- **Reader:** the part that turns a question into search requests.
- **Harness:** the ordinary code around the model that prepares inputs and records outputs.
- **Template:** the fixed sentence pattern the questions were trained on.
- **Intercepted:** captured before it is used.
- **Snap:** pick the closest legal address to the model's fuzzy request.
- **Codebook / address grid:** the closed list of all legal addresses.
- **Mode bit:** a switch saying "this is a telling, not a question".
- **Zero gradient:** no learning signal passes through that path.
- **Key-value memory:** a store you search by label to get back contents.
- **L-value:** in programming, the place an assignment writes to, found by following a path.
- **Frozen checkpoint:** a saved trained model whose weights are not changed during the test.
- **Seed:** one training run with its own random start.
- **Dead seed:** a run that never learned even one-step questions.
- **Eligible seed:** a run that reads well enough for a filing failure not to be blamed on training.
- **Pass mark:** the score fixed before looking that decides pass or fail.
- **Floor:** the score when no card is written.
- **Leak:** a way to get the answer without the card, which would make the test invalid.
- **Diary:** the raw log of every told line.
- **Unfiled:** a told line kept in the diary with no card made.
- **Misfile:** a card written at the wrong address.
- **Overwrite:** a new card replacing a different card at the same address.
- **Relation-copy wire:** your 545-parameter shortcut that copies the question's relation word into the request.
- **Practised kind:** a kind of fact seen in two-step form during training.
- **Held-out kind:** a kind of fact never seen in two-step form during training.
- **Plumbing test:** a check that parts connect correctly, which does not show that anything improved.

**Sources**
- Opened by me in this pass:
  - https://arxiv.org/abs/2011.07831
  - https://ar5iv.labs.arxiv.org/html/2011.07831
  - https://arxiv.org/abs/2009.11423
  - https://arxiv.org/abs/1706.04115
  - https://arxiv.org/abs/1810.05682
  - https://arxiv.org/abs/1410.5401
  - https://arxiv.org/abs/1612.03969
- All other links were opened and confirmed by the citation checker or the dossier hunters. Every table link is marked verified in the kill table. The one unverified link there (LARS) has been left out.
- Local file read: `/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/research/design/research/final-sweep-2026-09-19/README.md` (H2 section).
- Local file read: `/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/research/design/research/final-sweep-2026-09-19/00-evidence.md` (the pooling-weight figure).