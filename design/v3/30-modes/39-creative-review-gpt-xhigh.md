**Recommendation:** keep the core design—one model dreams and judges, a backlog preserves good unchecked ideas, and only an external check may declare `FOUND`—but move the experiment onto **notebook-native rule discovery**. That gives you a real trained generator/verifier while preserving an exact checker for one narrow but useful class of creativity. The literature strongly supports separating *generation* from *ground-truth checking* even when generation and verification share weights. Evidence at your intended tiny scale is still thin: most 2024–2026 work below is 1B+ parameters, so the next experiment matters more than extrapolating from those papers.

## 1\. The three biggest gaps

| Gap | Why it matters | Cheapest useful experiment |
| --- | --- | --- |
| **The toy has an oracle; real creativity usually doesn't.** | Your 0 false-`FOUND` result is largely a consequence of the exact checker. For an open-ended hypothesis, "good" is not usually decidable. | Move to **proposed relation rules over the notebook**. Let the model invent rules like `R1(x,y) ∧ R2(y,z) → R3(x,z)` and test them against held-out known facts. You still have a real executable checker, but the task now resembles the actual agent. |
| **The dreamer/filter is scripted rather than learned.** | A learned generator and verifier can share blind spots. More dangerously, a generator can learn what its verifier likes rather than what the checker accepts. Learned reward models can be overoptimized, and same-family evaluators can exhibit self-preference. [ICLR Proceedings+1](https://proceedings.iclr.cc/paper_files/paper/2024/hash/dda7f9378a210c25e470e19304cce85d-Abstract-Conference.html?utm_source=chatgpt.com) | Train a tiny generator plus verifier from actual checker outcomes. Mine **hard negatives**: high-scoring ideas that fail the checker. Compare tied/shared versus independent weights. |
| **The toy is a stationary short episode.** | Your real agent accumulates facts, corrections, aliases and unresolved ideas for weeks. A backlog may become stale, and your known length-generalization problem can reappear. | Evaluate an episodic stream: new facts → corrections → aliases → rule proposals. Keep backlog items across episodes. Train on short rules/chains; separately report longer unseen chains. |

There is another important difference hidden inside the second row: **verification is not automatically easier for a small model**. T1 found that even distilled 1B-scale models struggled to verify arithmetic/factual material from their own parameters, while giving them executable tools greatly improved verification. That is almost exactly the argument for making your notebook/reasoner/checkers part of the verifier rather than expecting the neural network to "know" correctness internally. [arXiv+1](https://arxiv.org/abs/2504.04718)

* * *

## 2\. Training "the filter should know a good idea when it sees one"

I would make the final architecture **one trunk, two roles**:

```
                 shared small model
                /                 \
        DREAM / generator      VERIFY head
              |                    |
        candidate idea       P(checker accepts)
              |                    |
              +------> exact/tool checker
                           |
                    ACCEPT / REJECT
```

Use a role token such as `<DREAM>` versus `<VERIFY>`, with the same underlying model. A small scalar verifier head is enough initially; later you can test a generative verifier that explains its verdict.

### Training signal

For every proposed idea i:

yi​\={10​checker acceptschecker rejects​

Train the verifier with binary cross-entropy:

LV​\=−ylogp−(1−y)log(1−p).

Train the generator separately toward checker-successful candidates. **Do not initially train the generator to maximize the learned verifier score.** Let the real checker provide the generator's reward. Otherwise generator and verifier can collude accidentally: the generator discovers artifacts that fool its own head.

Most importantly, refresh training examples **on-policy**: periodically sample ideas from the *current* generator and run the checker on those. SCoRe found that training self-correction on static/off-policy correction traces can fail because the model's own error distribution moves during training; their online RL procedure avoided that distribution mismatch. [arXiv+1](https://arxiv.org/abs/2409.12917?utm_source=chatgpt.com)

I would deliberately oversample four kinds of examples during training: ordinary positives, ordinary negatives, **near-miss sibling negatives**, and **high-verifier-score checker failures**. That fourth bucket is adversarial training against your own filter.

### Outcome reward first; process reward later

Start with **outcome supervision**: did the proposed idea actually pass?

Do not invent subjective process labels such as "this thought seems promising." Process supervision becomes attractive only when you can define progress objectively. The useful definition is approximately:

progresst​\=P(eventual success∣st+1​)−P(eventual success∣st​).

That is close to the result in *Rewarding Progress*: process rewards were most effective when they measured change in future success probability rather than generic intermediate correctness. Their process-advantage verifiers beat outcome reward models in their reasoning setting, but crucially their progress signal was grounded in another prover policy. [ML Anthology+1](https://mlanthology.org/iclr/2025/setlur2025iclr-rewarding/?utm_source=chatgpt.com)

For your system, estimate that later with repeated checker-backed rollouts.

### Calibration: make 0.85 actually mean something

Your toy's `0.85` threshold has no reason to equal an 85% probability in a neural model.

Use a held-out calibration set sampled from the **real deployment distribution**, not the balanced training set. Fit one scalar temperature T:

p\=σ(z/T),

where z is the verifier logit.

Then report:

- Brier score;
- ECE/reliability diagram;
- AUROC or ranking accuracy;
- and most importantly, actual checker acceptance among predictions scored `0.80–0.90`, `0.90–0.95`, etc.

A useful operational requirement would be:

> Among ideas with calibrated score ≥0.85, at least 85% should actually pass the checker pooled across held-out data, with each seed reported separately.

Calibration can differ badly between slices even if global calibration looks good; 2024 multicalibration work showed why slice-specific checking matters. For you, track at least rule type, chain length and familiar-vs-unseen relation family. [Proceedings of Machine Learning Research+1](https://proceedings.mlr.press/v235/detommaso24a.html?utm_source=chatgpt.com)

### What is known about generator–verifier gaps?

The recent evidence points in the same direction:

**There really is a generation-verification gap.** *Mind the Gap* formalized the situation where a model can sometimes generate a correct answer yet cannot reliably recognize it, and found that the useful generation-verification gap changes systematically with pretraining compute. This is a warning against assuming a tiny generator can automatically be its own good judge. [ICLR Proceedings+1](https://proceedings.iclr.cc/paper_files/paper/2025/hash/63943ee9fe347f3d95892cf87d9a42e6-Abstract-Conference.html?utm_source=chatgpt.com)

**Joint/shared training can work.** *Generative Verifiers* trained verification through next-token prediction jointly with solution generation and substantially improved Best-of-N selection over discriminative and judge baselines on their algorithmic/math tasks. So "one model has both skills" is not a bad premise. [ICLR Proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/214308a2d5e3f83ef9ad2739e1cbc46d-Abstract-Conference.html)

**But a shared judge is not independent evidence.** NeurIPS 2024 found self-preference when LLMs evaluated their own generations. That study does **not** establish that a sub-million-parameter model will show the same effect, but it gives you a concrete reason to include the separate-verifier control. [NeurIPS Proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html?utm_source=chatgpt.com)

**Small self-verifiers especially benefit from tools.** T1 reports that small models struggled on verification requiring memorized facts/calculations even after verifier distillation, while tool integration substantially narrowed the gap. [arXiv](https://arxiv.org/abs/2504.04718)

**Intrinsic "think again" is unreliable unless trained or externally grounded.** Earlier work found that asking an LM to self-correct reasoning without external evidence can degrade answers; SCoRe later showed that self-correction can be specifically trained with on-policy RL. [arXiv+1](https://arxiv.org/abs/2310.01798?utm_source=chatgpt.com)

So my rule would be:

> **The neural verifier may prioritize ideas. It never creates truth.**

That rule from your toy should survive unchanged.

* * *

## 3\. What replaces the exact checker?

You already have more machine-checkable creativity than it may seem.

| Creative proposal | Real checker |
| --- | --- |
| **New relational rule** | Apply it to notebook triples. Measure support, counterexamples, precision and held-out prediction. |
| **New inferred fact** | Execute its claimed reasoning path through the notebook/reasoner; verify every premise and provenance edge. |
| **Entity merge** | Check alias evidence plus hard contradictions: incompatible unique attributes, explicit distinction, conflicting identity facts. Usually gives a reliable **veto**, not proof of identity. |
| **Contradiction repair** | Simulate the edit and check whether it resolves the conflict without overwriting higher-priority taught facts. |
| **Structural analogy** | Compare relation/path structure between source and target; check whether the same relational transformation actually holds. |
| **Question for Ben** | In experiments, use a known hidden world and calculate how many possibilities each possible answer eliminates. In deployment, estimate entropy reduction over the current ambiguity set. |
| **Proposed query plan** | Execute it against the notebook; measure whether it retrieves the needed evidence. |
| **Sleep-derived lesson/rule** | Hold out notebook queries before learning the lesson; learn it; rerun them plus regression tests. Accept only if transfer improves without damaging old cases. |
| **Web-derived hypothesis** | Check provenance/retrieval agreement automatically, but keep truth quarantined exactly as you currently do until Ben approves. |

Recent KG work supports this general pattern: reason over explicit structured facts and executable graph operations rather than asking an LM to pronounce a claim true from its internal knowledge. Programmatic Graph Reasoning explicitly executes graph programs for verification, while RulE scores rules based on consistency with observed triples. [ACL Anthology+1](https://aclanthology.org/2025.findings-emnlp.293/?utm_source=chatgpt.com)

**Build relation-rule discovery first.**

It is unusually valuable because it provides all four things you need simultaneously:

1. an actual form of creative induction;
2. essentially unlimited automatically generated training labels;
3. a strong checker;
4. direct usefulness to your existing notebook/reasoner.

For example, the dreamer might propose:

```
IF parent(A,B) AND sibling(B,C)
THEN aunt_or_uncle(C,A)
```

Software can search the notebook for supporting and contradicting cases. The neural filter must learn which proposals are worth spending checker calls on.

That is a much stronger next step than making the synthetic puzzle prettier.

* * *

## 4\. Stopping and ASK BEN

Because **GPU thinking is cheap to you but Ben's attention is expensive**, I would deliberately make stopping asymmetric:

**Do not ask merely because confidence is low. Ask when the remaining uncertainty is both important and not machine-resolvable.**

There are three states:

```
Machine can still test useful ideas  -> KEEP THINKING
Only unchecked useful backlog remains -> CHECK BACKLOG
Key uncertainty requires Ben          -> ASK BEN
```

Examples:

- "I have not found a rule yet" → keep searching.
- "Two entity IDs may be the same person, and existing facts cannot distinguish them" → potentially ask.
- "Two taught statements directly conflict and provenance gives equal authority" → ask.
- "The verifier merely feels uncertain" → not sufficient.

### Rank human questions by information gain

For candidate question q, approximate:

VOI(q)≈H(current possibilities)−E\[H(possibilities after answer)\].

Then also multiply by how consequential the ambiguity is—whether resolving it affects one forgotten fact or hundreds of future inferences.

There is direct recent evidence that LMs can be trained to ask better questions using **expected information gain** as supervision: EMNLP 2024 generated candidate questions, ranked them by EIG and preference-trained the model toward the more informative ones. [ACL Anthology](https://aclanthology.org/2024.findings-emnlp.291/?utm_source=chatgpt.com)

When asking, batch related ambiguities into at most a few high-value questions and show the evidence:

> I have two possibilities for Alex: entity 17 and entity 42.  
> Entity 17 matches the school fact; entity 42 matches the tennis fact. Nothing in the notebook links them.  
> **Are these the same Alex?**  
> Your answer would resolve 6 currently blocked inferences.

That is better than "I'm unsure; can you clarify?"

### Can we beat the fixed cap?

There are principled adaptive schemes, but **you do not yet have evidence that one beats your fixed cap**.

Test-time-compute research shows that adaptive allocation can outperform uniform Best-of-N because different problems benefit from different amounts of search. [arXiv](https://arxiv.org/abs/2408.03314?utm_source=chatgpt.com) But those methods optimize **compute**, whereas you explicitly do not care much about compute. Your objective is different: minimize premature failure and Ben interruptions.

I would therefore keep:

> **fixed high safety cap + backlog**

as the production baseline.

The adaptive challenger I would test is a conservative **success-hazard estimator**. From previous rounds estimate:

pr​\=P(checker success on another novel idea∣current state).

Continue unless:

1. backlog is empty,
2. novelty generation has essentially collapsed,
3. and an **upper confidence bound**, not merely the point estimate, says the chance of success over another K attempts is below a tiny threshold.

Because thinking is cheap, err heavily toward continuing.

Your Good-Turing result already tells you not to replace the fixed cap with an elegant-looking statistic before it proves itself.

* * *

# 5\. The next preregistered experiment

### Question

**Can a tiny genuinely trained model generate creative relational rules and recognize its own useful ideas well enough for verifier-guided search, and do sharing/backlogs help?**

### Task

Generate synthetic notebook worlds containing entities and relations plus hidden Horn-style rules.

Example hidden world rule:

Ra​(x,y)∧Rb​(y,z)→Rc​(x,z).

Give the model a subset of facts. It proposes candidate rules from a small compositional grammar.

The checker tests each proposed rule on **held-out facts** from that world.

Include:

- solvable worlds;
- unsolvable worlds;
- near-miss sibling relation families;
- unseen entity names;
- held-out rule combinations;
- a separate longer-chain OOD split.

This is still controlled, but it now tests the real mechanism you want.

### Tiny models

Hard cap:

> **≤1 million total trainable parameters per arm**, widths adjusted so shared/separate conditions are within ±3% total parameters.

Use a 2-layer tiny Transformer or GRU; whichever is already easiest in your experiment harness.

For separate models, divide capacity between generator and verifier. For shared, one trunk gets `<DREAM>` and `<VERIFY>` role tokens plus separate output heads.

Because capacity allocation can affect generation, always report **oracle@N**—whether the candidate pool contained a valid answer—separately from verifier selection.

### Factorial arms

|  | No backlog | Backlog |
| --- | --- | --- |
| **Shared generator/verifier** | S−B | S+B |
| **Separate generator/verifier** | D−B | D+B |

Everything else identical.

Three seeds.

### Training

Use exact checker labels.

Generator objective:

LG​\=−logc∈Cvalid​∑​P(c∣x)

so it is rewarded for assigning probability to **any** valid rule rather than memorizing one canonical answer.

Verifier:

LV​\=BCE(V(x,c),checker(x,c)).

Every few hundred updates, refresh part of the verifier dataset with **current-generator candidates**. Keep high-scoring false positives as hard negatives.

For the shared model:

L\=LG​+λLV​.

Freeze λ before running seeds.

Calibrate the verifier afterward on a natural-prevalence validation split; do not calibrate on the test set.

### Search evaluation

Freeze all weights.

For each puzzle:

- high-temperature generator;
- verifier threshold frozen before test;
- same candidate samples/round;
- same checker-call budget;
- **11-round hard cap**, matching your successful existing control;
- only exact checker may emit `FOUND`;
- backlog arm saves unchecked survivors;
- no-backlog arm discards them;
- after round 11, unresolved → `ASK`.

Do not introduce adaptive stopping yet. That would be a fifth changed variable.

### Metrics

Report every seed:

1. solvable `FOUND` rate;
2. false-`FOUND` count;
3. correct `ASK` on unsolvable worlds;
4. oracle@N;
5. verifier-selection accuracy conditional on oracle@N;
6. AUROC;
7. Brier score / ECE;
8. checker acceptance for scores ≥0.85;
9. checks per solved case;
10. longer-chain OOD results.

### Pre-register these pass marks

I would use:

**Safety**

- `0` false `FOUND`, every seed. This should be structural.

**Useful learned creativity**

- ≥85% solvable `FOUND` in every seed.
- oracle@N ≥90% in every seed.

**Verifier actually knows something**

- AUROC ≥0.80 every seed.
- pooled checker acceptance among calibrated `score ≥ .85` ≥85%.
- no seed below 75% in that high-confidence bucket.

**Backlog hypothesis**

- backlog improves `FOUND` by **≥5 percentage points averaged over seeds**, and does not reduce any seed by >2 points.

**One-model viability**

- shared condition's verifier-selection success is **within 3 percentage points of separate**, averaged over seeds.
- If shared wins, do not conclude sharing is inherently superior; only that independence was unnecessary on this task.

The OOD long-chain split should initially be **diagnostic, not a pass/fail gate**, because length generalization is already a known failure mode and otherwise it could obscure what this experiment is meant to isolate.

### How to interpret the outcomes

- **Shared + backlog passes:** your "dreamer/filter/worker = one model" premise survives its first genuinely learned test. Move next to persistence and ASK-BEN.
- **Separate beats shared substantially:** likely correlated representation/error matters. Before abandoning one-model design, try one trunk with stronger role separation—independent verifier adapter/head, stop-gradient boundaries, or verifier-specific recurrent steps.
- **Oracle@N high, verifier selection low:** you have a **generation-verification problem**. Work on the verifier, not creativity.
- **Oracle@N low:** the filter is not the bottleneck; improve generation/diversity.
- **Verifier good in-distribution but bad on longer chains:** this is your length-generalization wall reappearing in verification.
- **Backlog still helps:** promote backlog from toy trick to a core architectural primitive.
- **Backlog stops helping:** its previous gain was likely specific to the scripted candidate distribution.
- **Score ≥0.85 is badly calibrated:** do not use verifier confidence for stopping or ASK-BEN yet.
- **All four arms fail despite learning the checker labels:** shrink the problem before adding architecture. That would mean the neural generation/verification problem itself is not yet solved.

The key result I would want from this experiment is not "98% solved." It is the decomposition:

Can generate it?→Can recognize it?→Can verify it externally?​

Your existing toy mostly proved the third box and showed that backlog helps search. This next experiment cleanly tests the first two.

### Sources

[Mind the Gap — ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/63943ee9fe347f3d95892cf87d9a42e6-Abstract-Conference.html?utm_source=chatgpt.com)  
[Generative Verifiers — ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/214308a2d5e3f83ef9ad2739e1cbc46d-Abstract-Conference.html?utm_source=chatgpt.com)  
[T1: Tool-integrated Verification for Small Language Models](https://arxiv.org/abs/2504.04718?utm_source=chatgpt.com)  
[Rewarding Progress — ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/98711dea460bdefe0e651ca23ec98ba2-Abstract-Conference.html?utm_source=chatgpt.com)  
[Training Language Models to Self-Correct via RL — ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/871ac99fdc5282d0301934d23945ebaa-Abstract-Conference.html?utm_source=chatgpt.com)  
[LLM Evaluators Recognize and Favor Their Own Generations — NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7f1f0218e45f5414c79c0679633e47bc-Abstract-Conference.html?utm_source=chatgpt.com)  
[Scaling LLM Test-Time Compute Optimally](https://arxiv.org/abs/2408.03314?utm_source=chatgpt.com)  
[Learning to Ask Informative Questions — EMNLP 2024](https://aclanthology.org/2024.findings-emnlp.291/?utm_source=chatgpt.com)  
[Multicalibration for Confidence Scoring — ICML 2024](https://proceedings.mlr.press/v235/detommaso24a.html?utm_source=chatgpt.com)  
[RulE: Knowledge Graph Reasoning with Rule Embedding — ACL 2024](https://aclanthology.org/2024.findings-acl.256/?utm_source=chatgpt.com)  
[Programmatic Graph Reasoning for KG Fact Verification — EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.293/?utm_source=chatgpt.com)
