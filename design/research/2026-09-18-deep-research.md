# Premonition: deeper research and the next decisive experiments

Prepared for Ben, 2026-09-18. Astra researches and reviews; Opus implements and
runs. This report combines primary literature, source inspection, the trainer
handoff and Opus's correctness report. **It is not a new training result.**
New GPU rental spending remains **$0 / $30**. No rental is authorized.

## Read this part first

**Our next improvement should help the model use a fact it already found.**
The earlier trainer reports that D sometimes finds the correct memory every
time yet answers about as well as guessing. Even handing it the right memory
does not fix that. That changes my earlier recommendation: better searching is
not the first thing to try. First we must reproduce that result and locate where
useful information stops affecting the answer.

Imagine a student who finds the correct textbook paragraph, copies it onto a
scratchpad, then mixes it with other notes until the answer is hard to read.
That is a useful picture of our leading hypothesis. It is not yet a proven
description of what D does.

Two small tests are justified. One starts the thinking block with very gentle
changes and lets training increase them. The other lets the answer writer see
the retrieved facts before thinking transforms them. If either works, we learn
something specific about the failure. Neither by itself proves deep reasoning.

**TST remains worth testing later.** It is a way to reduce the work spent reading
training text. It cannot yet be credited with fixing this model's failure to
answer a simple question. Our version must check that cheaper reading does not
damage understanding of who did what to whom.

This changes the order of tests, not Ben's long-term vision. A growing codebook,
sleep, drives and the final memory design remain separate decisions for Ben.

## 1. Evidence: what we know, and how strongly

| Evidence | Status | What it supports | What it does not establish |
|---|---|---|---|
| Own retrieval selects detached scores and gathers card values. | Direct code inspection. | Answer loss has no direct differentiable route through that discrete choice into query/key scoring. Evidence supervision supplies another route. | That this caused the current failure; gold-card failure bypasses the choice. |
| All valid thinking rows receive the same learned step vector; residual attention and MLP updates follow. Decoder normalizes each memory row before cross-attention. | Direct code inspection. | There is a plausible route for a shared component to obscure differences among rows. | That collapse actually occurs, or that normalization is inherently wrong. |
| Retrieval reportedly reaches 100%, while own and gold-card answers remain around chance. | Historical trainer report, not independently reproduced here. | Using supplied facts is the first problem to reproduce. | A trustworthy final accuracy estimate or a proved cause. Original probe scripts were not archived. |
| The trainer reports that Decoder learns with real rows and a clean oracle card, but struggles when one Think pass is inserted. | Historical controlled probe, pending reproduction. | The Think-to-Decoder interface deserves investigation. | That every writer-produced card is usable or that this is the only failure. |
| Opus's stored probe removes prior-answer leakage and C's candidate gap. | Submitted report/artifacts and code review; tests not rerun by Astra. | Milestone 1's scoped input-correctness acceptance. | Learned reasoning, useful memory, or the full statistical verdict. |
| Published architectures solve related tasks. | External primary evidence. | Candidate mechanisms and better experimental controls. | Guaranteed transfer to our roughly 2M-parameter model. |

Local evidence: [trainer handoff](/Users/ben-hannan/Desktop/projects/beautiful-model/design/research/2026-09-18-trainer-handoff.md),
[Opus milestone 1](/Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-milestone-01-m01-20260918-202731.md),
[Think block](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:201),
[decoder](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:278),
[hard selection](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:609).

The historical probes also report failed gold-card training with one loop and
answer loss only. Therefore simply adding more loops, reducing the filler loss,
or teaching retrieval harder is poorly motivated as the first repair. These
are deprioritized hypotheses, not universally disproved mechanisms.

## 2. The answer-path hypothesis, made testable

The current route is:

    text → reader → stored cards → retrieved row copies → Think → Decoder → answer

The persistent store already retains card values. The concern is the copies
that reach the decoder after Think transforms them. We must preserve access to
evidence, rather than assume the underlying store itself is being overwritten.

The handoff reports 91% held-out value-probe accuracy on cards, 84% before
Think, 67% after Think and 5.6% after decoder cross-attention in one probe.
Those numbers suggest a location to investigate. A probe is a separate small
model trained to read information from a representation. Its success means
information is accessible to that probe; it does not mean D uses it.

### A precise explanation to check

Our hypothesis can be written as `row_i = common_vector + fact_specific_i`.
If the feature-varying common vector grows much larger than the differences,
normalizing each row can leave rows pointing in nearly the same direction.
The decoder may then have trouble distinguishing their contents.

This is an analytical possibility, not a finding. LayerNorm removes each row's
mean **over features**. A constant scalar added to every feature is removed;
a shared vector whose coordinates differ is not generally removed. Also, large
norms alone prove nothing: the fact-specific part could grow just as quickly.

For valid rows `x_i`, log their mean `m`, centered spread
`sqrt(mean_i ||x_i-m||²)`, and the spread-to-mean ratio. Also measure pairwise
similarity after the decoder's exact normalization. Measure all of these before
and after Think. Exclude padding. Compare the same examples and row types.

The rank-collapse literature gives a caution, not a diagnosis: Dong et al.'s
strong collapse result concerns pure attention, and their analysis explicitly
shows counteracting roles for skip connections and MLPs. Premonition already
has both. We cannot cite that theorem as proof our block collapses.
[Primary paper, especially §3](https://proceedings.mlr.press/v139/dong21a/dong21a.pdf).

Uniform attention is likewise insufficient. One literature line demonstrates
attention distributions can be misleading explanations; a response shows
their usefulness depends on the question and controlled tests. We should use
attention as a measurement alongside interventions, not as a causal verdict.
[Jain and Wallace](https://aclanthology.org/N19-1357/),
[Wiegreffe and Pinter](https://aclanthology.org/D19-1002/).

### The two interventions

**Gated Think:** `x_next = x + alpha * (Think_original(x, step) - x)`, with
learnable `alpha` initially zero. The entire update includes the step embedding.
This makes the initial transformation exactly preserve the input. ReZero
established zero-initialized residual gates as a way to ease optimization.
Our proposal retains the current pre-normalized block and gates its complete
update, so it is an adaptation rather than a reproduction of ReZero's
Transformer. Its theoretical and empirical guarantees do not automatically
transfer. [ReZero, §3–4](https://proceedings.mlr.press/v161/bachlechner21a/bachlechner21a.pdf).

At zero, branch-weight gradients initially vanish while the gate can receive a
gradient. That is expected, not automatically a broken learning path. Check that
the gate actually opens. A gate that stays closed but solves one-fact copying
would not demonstrate learning a multi-step procedure.

**Pre-think card access:** replace only the decoder's post-think card rows with
their pre-think versions. Keep the number of rows, other row types and masks
fixed. This isolates access to the facts more cleanly than concatenating extra
rows, adding type embeddings, changing normalization and introducing a new loss
all at once. It may still change gradient routes, which must be reported.

Run these separately. A successful bypass localizes a useful intervention; it
does not establish the common-vector mechanism uniquely. A successful gate
could improve optimization for several reasons. Mean subtraction, per-type
normalization and register-only step embeddings remain follow-up hypotheses,
not extra adjustments in this milestone.

### What would change our mind

| Result | Interpretation and next action |
|---|---|
| Clean-card Decoder alone fails. | Audit labels, shifts, masks, optimization and probe construction before blaming Think. |
| Baseline now succeeds with normal gold cards. | Identify the changed conditions; do not impose an unnecessary repair. |
| Clean oracle cards work; writer-produced gold cards fail. | Inspect the writer/readout interface and contextual contamination. |
| A bypass works, while normalized row diversity does not collapse. | Keep the result; reject the specific collapse explanation as insufficient. |
| Gold works, own retrieval fails. | Now study card choice, insertion, ASK, early stopping and D-soft. |
| Own retrieval works; D-noask matches it. | The toy has not demonstrated that the store adds value. Design a stronger comparison. |
| More loops worsen correct answers. | Study stability and the stopping rule, rather than assuming more compute helps. |

Use a consistent counterfactual too: change the relevant fact's value, keep its
entity and relation fixed, regenerate the valid episode and target, and check
whether the answer follows the changed fact. An internal vector swap is useful
as an extra diagnostic, but it can create an input distribution never seen in
training. Report that limitation.

## 3. Memory and reasoning: the useful lessons from earlier work

**Separate the evidence from the state doing the reasoning.** End-to-End Memory
Networks updates a query state through weighted reads of encoded memories.
It also tested positional and temporal encoding, and a simpler initial training
phase. Its small QA setting used a limited vocabulary, encoded multiword answer
combinations as classes, and sometimes selected among ten initializations.
Those details limit comparisons with our generative decoder and budget.
[Memory Networks, §2 and §4](https://papers.neurips.cc/paper/5846-end-to-end-memory-networks.pdf).

Key-Value Memory Networks makes a second useful distinction: the representation
used to find a fact need not be the representation used to answer from it.
Its structured triples and document features also supplied task-specific
structure. We should not give only D an oracle subject/relation/object parser
and call the resulting gain architectural superiority.
[Key-Value Memory Networks, §3](https://aclanthology.org/D16-1147.pdf).

**Application to Premonition:** a later candidate could let a small writable
scratchpad repeatedly read unchanged fact representations. That is a design
hypothesis, not a new permanent store decision. The immediate card bypass is a
cheap test of whether such separation deserves attention. Before building a
new architecture, compare the already specified D-soft and matched iterative
retrieval baseline C*.

Soft retrieval has a cost: averaging several incompatible facts can produce a
representation that corresponds to none of them. Multiple read slots, sharper
weights or sparse selection may help, but each introduces a new choice. First
establish the failure being solved. Hard retrieval trained with evidence labels
can be a useful system even though it lacks answer-only selection gradients.

**Protect relationships from superficial identity.** Abstractors explicitly
construct representations of relations using symbols independent of object
contents. Its evidence concerns particular relational tasks; the paper does
not systematically establish length generalization. That supports testing role
and identity invariance, not assuming a new module will extrapolate.
[Abstractors, §2.2–2.3 and experiments](https://arxiv.org/html/2304.00195v3).

Our tests should cover distinct problems:

- **Renaming:** replace every name consistently. The answer should change only
  by the same renaming. Check both raw-name and entity-ID pipelines.
- **Role reversal:** swap who gave and who received an object. The answer should
  change appropriately even though the word inventory is the same.
- **Updated facts:** state a location, then change it. The answer must use the
  relevant time, not whichever card has the strongest keyword overlap.
- **Distractors:** add irrelevant facts without changing the target answer.
- **Longer reasoning:** require more dependent steps while keeping prose length
  controlled. Separately lengthen prose without adding reasoning steps.

The CLRS benchmark is a useful precedent for generating exact algorithmic
inputs, outputs and intermediate hints, including tests beyond training sizes.
Our simulator can supply similar diagnostic structure, but privileged traces
must be labeled and supervision must be matched across competitors.
[CLRS, §3–4](https://proceedings.mlr.press/v162/velickovic22a/velickovic22a.pdf).

## 4. Repeated thinking: promising, but not a free reasoning upgrade

The looped-transformer work of Fan et al. uses training information about how
many iterations an example requires, even without intermediate-answer labels.
It also reinjects the original input each iteration; its ablations support that
choice on several tasks. This is stronger structure than merely repeating a
block. Its full-answer setting differs from ordinary left-to-right generation.
[Methods §4 and ablations §6.3](https://arxiv.org/html/2409.15647v2).

TRM provides encouraging evidence for small recurrent systems on structured
puzzles. Transferring its schedule to a language decoder is a different claim.
A 2026 autoregressive study found its full AR-TRM variant performed poorly in
tested character tasks, while some simpler variants worked. Its compute control
counts block evaluations; that is not a complete equivalence of wall time,
memory or parameter count. These are narrow, useful counterexamples rather
than a refutation of all recursion.
[TRM](https://arxiv.org/html/2510.04871v1),
[autoregressive study, §5 and Appendix B](https://arxiv.org/html/2603.08082v1).

A June 2026 preprint adds another caution: randomizing training loop counts
reduced variability, and learned stopping helped several tasks but made Copy
worse despite more stable results. Consistency and correctness are separate.
This is recent preprint evidence, not an established universal recipe.
[Stochastic stopping, §4 and Table 1](https://arxiv.org/html/2606.29983v1).

**Our next reasoning experiment, after one-fact learning works:** make a grid
of reasoning depth versus allowed loops, and report accuracy in each cell.
Use the same held-out episodes for every loop setting. Separate extra thinking
with fixed available facts from extra retrieval opportunities: current D allows
at most K−1 reads in K loops. Simply changing `max_loops` also does not override
early HALT. A benchmark that leaks its true depth into inference cannot count
as autonomous stopping.

Measure whether extra loops preserve already correct answers, change incorrect
answers to correct ones, or make correct answers wrong. If longer problems
remain unsolved despite more loops, inspect which intermediate relation fails.
Do not hide this behind one average score.

## 5. TST: where the headline transfers, and where it does not

TST averages groups of input embeddings and predicts the next non-overlapping
token bag, then returns to standard next-token training. The authors' large
MoE comparison reports 4,768 versus 12,311 B200-hours at comparable loss,
while consuming 2T versus 1.05T raw tokens. The smallest reported model has
270M parameters. [Authors' overview](https://nousresearch.com/token-superposition).

The paper identifies more data consumption and longer effective context as
important considerations. Output-only superposition keeps ordered inputs and
changes the target. Large repeated-run significance was not established.
The small dense configurations untie input/output embeddings; our Core ties
them. An embedding/head reset between phases destroys the reported advantage,
but does not isolate which component explains it.
[Paper §4, §5.2–5.3 and §7](https://arxiv.org/pdf/2605.06546).

The rest of this section is our own analysis and proposed experiment design.

### Why order matters mathematically

For a group of s token vectors, averaging computes `mean(e_1,...,e_s)`.
Reordering those same vectors leaves that mean unchanged. If two examples
require different answers but differ only by such a permutation, a model given
only the pooled representation cannot distinguish them without another cue.
For a balanced two-answer collision, the best deterministic classification
accuracy on that isolated pair is 50%. This limit applies to the information
available during the compressed phase, not to the recovered ordinary-token
model, which sees order again.

Simply adding position vectors and then averaging does not solve the problem:
`mean(e_i + p_i) = mean(e_i) + mean(p_i)`. The sum does not retain which token
occupied which position. Position-dependent transformations, contextualization
before pooling, or keeping role markers separate could preserve more order,
but change the method and its compute cost. Treat them as separate future
variants, not invisible fixes to a TST reproduction.

Do not claim D's present card pooling has the same exact limitation. It pools
**contextual reader outputs**, which can already encode order. Raw token
averaging before a reader and pooling contextual states are different.

### Three quantities people accidentally confuse

1. **Raw tokens:** how much original text is read.
2. **Transformer positions:** how many vectors the expensive block processes.
3. **Useful new examples:** how many independent situations teach something new.

TST can improve raw tokens per position without improving useful examples per
second. Our simulator can generate fresh visits, so a small saved corpus does
not necessarily make us data-limited. But new names and another rendering of
the same trivial rule do not automatically add harder reasoning. Measure fresh
compositions, episode count, repeats and generation/tokenization time.

Under an idealized fixed-position, equal-step-cost schedule, if fraction r of
steps pools groups of size s, the raw-token multiplier is `1+r(s−1)`. Our proposed
`s=2, r=0.2` screen would give 1.2× exposure under those assumptions, not a
promised 2.5× end-to-end saving. A FLOP-based phase schedule needs its measured
step costs rather than silently substituting this approximation.

There is a separate fixed-raw-text question. If only fraction f of total work
is compressible reader work and that part becomes s times cheaper, idealized
speedup is `1 / ((1−f)+f/s)`. For illustrative `f=0.3, s=4`, that is about 1.29×,
before overhead. D also writes cards, thinks and decodes answers. These terms
do not all shrink with reader positions. Profile them instead of quoting the
group size as whole-system speedup.

### The inexpensive experiment

Use the existing pointerized Core E as a measuring instrument once ordinary
question-centred training works. This does not change the final architecture.
Keep three arms: ordinary preparatory next-token training, TST with pairs,
and ordered-input/output-bag training. Then give all three ordinary recovery
and identical question-centred answer training. Keep embeddings across phases.

The first 20% of preparatory compute is the proposed coarse phase; the rest is
ordinary training. This is a conservative experimental setting, not a known
optimum. The output-only arm changes the learning objective without shortening
the input. If it wins, that is not evidence of a compression speedup.

For targets `[A,A,B,C]`, target probabilities are `{A:0.5,B:0.25,C:0.25}`.
One log-softmax with gathered repeated targets can express the average loss;
do not unnecessarily repeat the vocabulary projection for each target. Keep
padding, visit boundaries and answer/feedback spans out of valid bags.
Record any boundary-aware adaptation explicitly. Bag loss has a different
target entropy from ordinary next-token loss, so compare ordinary evaluation
after recovery, never the raw losses from different objectives.

Predeclare the primary comparison at equal total measured training compute,
including preparation and recovery. Record wall time, actual tensor shapes,
effective raw context, unique episodes and data reuse. Use intermediate
checkpoints for an equal-raw-token comparison where feasible. A context-matched
control is needed before attributing a gain to compression itself rather than
access to longer histories; the small initial screen may leave that attribution
unresolved. Do not expand it into a large sweep.

Keep the existing separate 30-minute local TST ceiling. It is **conditional**
and not activated by milestone 2. A promising screen earns a replicated study;
it does not prove efficiency. Final success requires less time to a common
reasoning target and preserved role/fresh-name performance under the project's
uncertainty rules. Lower language loss alone is insufficient.

## 6. Continual learning: three different abilities

Forgetting means losing an old skill. Loss of plasticity means becoming worse
at learning new skills. Dohare et al. demonstrate the latter over long task
sequences, including supervised image tasks. Selective unit replacement helps
in those settings, but is not established here; with Adam, its state also needs
care when weights are reset. Four successful lessons would not establish
lifelong plasticity.
[Plasticity paper, §2–6 and Appendix E](https://arxiv.org/html/2306.13812v3).

Replay—revisiting earlier training examples—is a useful basic competitor.
Rolnick et al. show strong replay results in their continual reinforcement
learning setting, with bounded buffers. That is a reason to include a practical
baseline, not proof of the best method for our supervised model.
[Experience Replay for Continual Learning](https://arxiv.org/abs/1811.11682).

Our future pilot should distinguish:

| Ability | Example | Test |
|---|---|---|
| Remember a new fact | A particular person's current location. | New fact, fixed skill; isolate cards, reader state and names. |
| Learn a new procedure | A newly taught rule for combining two relations. | Evaluate on fresh people/facts after clearing episode memory. |
| Keep learning | Learn a fourth procedure as readily as earlier ones. | Learning curves under matched lesson difficulty and order controls. |

For a sleep claim, compare the proposed scheduled update with an online replay
baseline using the same examples, replay capacity, optimizer updates and total
compute. If sleep simply gets more training, improved accuracy does not isolate
the schedule. Count optimizer state, raw replay, stored cards and any persistent
adapters in the memory budget. A compressed latent card may become stale when
its encoder changes; fresh re-encoding costs must be counted if used.

Use fresh episode facts to test procedures. If a claimed new skill disappears
after clearing cards, it may have been carried by episode memory instead of
learned in weights. That result is interesting but is a different claim.
Do not add unit resets, a learned sleep clock or private-language reinforcement
learning before a basic controlled pilot identifies a need.

## 7. Decision order and acceptance rules

| Stage | Question | Advance only when | Current status |
|---|---|---|---|
| Correctness | Are inputs and comparisons trustworthy? | Shared label-free path and identity safeguards work. | Milestone 1 accepted within its reported scope; full statistics unfinished. |
| Answer path | Can D answer from a supplied ordinary card? | ≥95% held-out toy accuracy, fresh bindings, reproducible evidence. | New bounded Opus handoff prepared; historical failure remains. |
| Autonomous memory | Can D find and use cards, and do they help? | Own retrieval plus fair D-noask/cards-only controls. | Not established. |
| Village solvability | Can a model solve simple real rendered reasoning? | Existing shallow gold-evidence gate, matched baselines and clean splits. | Not established. |
| Efficiency | Can TST reach the same useful ability more cheaply? | Matched total compute/time, recovery, role tests and replication. | Conditional local pilot only. |
| Continual learning | Can it learn new procedures and retain earlier ones? | Fresh-episode transfer, replay control and matched budgets. | Later proposal for Ben. |

For milestone 2, at most two focused adjustments and 30 minutes total training,
including all diagnostic fits and reruns. Do not move goalposts when a run fails.
Start with one development seed; a promising repair should use remaining time
for a fresh seed and untouched test set. Save exact success counts, not just
rounded percentages. Final scientific comparisons still require the existing
three-seed and visit-clustered statistical rules.

Questions from the same visit share facts and are not independent coin flips.
Resample whole visits for uncertainty. Keep paired model results together.
Repeated questions remain excluded from the primary score; report them
separately if useful. An inconclusive bound is not a pass or a kill result.
Small cell counts do not justify overriding the required coverage floors.

Concurrent generator work makes reproducibility especially important: freeze
source and generated data for comparisons. Record tokenizer and preprocessing
identities, seeds, source hashes, actual training time and every failed run.
The unfinished item-level verdict must continue to say `full_verdict: false`.

## 8. Deliverables and revision history

The actionable next handoff is
[Opus milestone 2: answer path](/Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-execution-02-answer-path.md).
It supersedes the immediate prioritization in the earlier learning prompts.
The TST prompt remains conditional and gains the constraints in this report.

This report corrects my earlier priority ranking. The detached retrieval path
is a real code property, but the trainer's gold-card failure makes it a poor
first explanation. The proper next step is reproduction and causal isolation.
No engineering source was changed and no experiment was run by Astra in this
research pass. Acceptance of milestone 1 relies on submitted evidence and source
review, not a claimed independent test run. Its reported suite is 108 tests
total, with one intentionally skipped learning gate.

Relevant source hashes at inspection:

```
f6d8c36093f8d392a7a680db3ab46b5dc6b28bee3475d6cb9e3e58be6404fda5 premonition/model.py
62c75d70b369daf61cf862b28f87aa64bf6037314dd1a39a7df994b81d2b9531 premonition/store.py
f7b945f080807c5dc4a5d91325d7ae3c760ea2de75c7bdf13c6da4c254f4deb9 premonition/train.py
af75a3acfd2e2a0a39ab9321bf8767e28c39db08b227784ee4eace3b08f3dafe premonition/preprocess.py
769e9036514b14b046898c7867115c15f82d07bc9792621340afa1288cc59aca premonition/identity.py
097c4ab5d3b81ec51562f52b9b307ba5647341ae7a725edf8b27d155d10070d6 learnlab/core.py
```
