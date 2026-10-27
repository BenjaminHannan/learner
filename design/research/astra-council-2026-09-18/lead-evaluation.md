# Lead's comparison framework

Research design only. No new experiment is started by this document. Opus's
current answer-path experiment remains the active implementation work.

## What counts as a useful new idea

A proposal earns a place by predicting a measurable change that a simpler
control would not predict. A new name, extra module or biological analogy is
not enough. We distinguish four levels:

1. A known method already in the project plan: useful, but not a new proposal.
2. A known method not yet tested here: a transfer experiment.
3. A specific new combination with an identifiable benefit: a research hypothesis.
4. A demonstrated new general result: requires experiments and a broader prior-art
   review; this council cannot honestly award that label yet.

Preference goes to mechanisms that fit a small reasoner with explicit facts,
permit small causal tests, and offer useful failure information. We do not rank
by adding arbitrary 1–5 scores: a mechanism that cannot be tested fairly does
not become attractive by receiving a high novelty score.

## Four measurements the current data can confuse

**Proof size is not sequential depth.** `oracle.Deriv.steps` adds the steps of
all premises in `join()`. A rule depending on two independently available facts
has a summed proof size, but those two facts might be processed together. Report
rule applications, evidence count and longest dependency chain separately when
available. Do not train a stopping policy to match this sum and then present
the resulting correlation as learned optimal computation. Producing a full
dependency graph requires instrumentation; it is not already present in the
saved evidence set. The existing ordered `rules` tuple is not a full graph.

**Changed answers are only half of causal behavior.** The current
`counterfactual_pair` changes a movement and prefers twins with many changed
answers. `_twin_links` keeps answer-changing, knowable pairs. It does not by
itself supply the equally important test that irrelevant changes leave an
answer alone. Pair metrics must include valid answer-changing and
answer-preserving interventions, with their construction declared. Renaming,
role reversal and event-order changes test different invariances; they cannot
be substituted freely for one another.

**Novel composition is not a novel primitive.** The scheduler's training split
permits at most one rule application; validation allows at most one rule family;
test includes mixtures of families. R8 is absent from train, while names,
wording and proof size also change. An aggregate held-out gain does not tell us
whether a mechanism learned a reusable procedure, adapted to a new instruction,
handled spelling, or simply read longer context. Report these axes independently
before testing their intersections. New diagnostic splits must have separate
identities and must not replace the frozen primary test set.

**Old cards are not necessarily independent facts.** D's card writer pools a
recurrent reader. A later card or the question representation can contain an
earlier fact. Deleting its original card may leave another information path.
Use input-consistent paired worlds, cards-only controls and the full-history
D-noask baseline. A line-local encoder is an already proposed ablation, not a
new discovery of this council.

Code references:
[Deriv and join](/Users/ben-hannan/Desktop/projects/beautiful-model/learnlab/village/oracle.py:98),
[split contract](/Users/ben-hannan/Desktop/projects/beautiful-model/learnlab/village/scheduler.py:1),
[twin construction](/Users/ben-hannan/Desktop/projects/beautiful-model/learnlab/village/scheduler.py:864),
[later spec revisions](/Users/ben-hannan/Desktop/projects/beautiful-model/design/06-premonition-mini-spec.md:252).

## A small shared ladder for proposed mechanisms

Each stage asks a different question. A mechanism should enter at the lowest
stage relevant to its claim, without claiming higher stages automatically.

| Stage | Test | Why it matters |
|---|---|---|
| Information | Can two examples needing different answers become identical at the proposed bottleneck? | Detect irreversible losses before any training. |
| Optimization | Can the mechanism fit a small valid example set and transfer to fresh random bindings? | Distinguish an unusable pathway from a generalization failure. |
| Causal use | Does the answer follow relevant fact changes and ignore irrelevant changes? | Distinguish using facts from a correlated shortcut. |
| Composition | Can familiar operations be applied in unseen combinations? | Test reuse without demanding an unlearned primitive. |
| Extrapolation | Do extra required operations work beyond training lengths? | Test repeated computation and memory capacity independently. |
| Continued learning | Can a new procedure be learned without losing old ones? | Distinguish acquisition from retention and fact recall. |

Fresh names and balanced answer distributions are required throughout.
Do not insert an oracle semantic parser into only one model. If a proposal
requires structured intermediate labels, train the comparison with the same
labels or keep the experiment explicitly privileged. All scored inputs must
remain free of earlier gold answers and feedback.

## Cost comparison

Count training work to reach a predeclared target, including preparation,
recovery, teacher/probe passes and failed development trials. Separately count
inference work and total memory. The existing FLOP counter omits elementwise
work and its fitted cost formula depends on the current architecture. A new
compressor or sparse mechanism needs its own measurement rather than reuse of
the old formula by assumption.

For memory mechanisms, distinguish one-time episode encoding from per-question
work. Report `episode_cost + Q * per_question_cost` at Q=1,10,100 where repeated
queries are valid. A method can be efficient for many questions and inefficient
for one. Include stored token IDs, card values, keys, indices, caches and any
optimizer/replay state appropriate to the claim; weights alone are incomplete.

Compression before a future question cannot use that future question. A method
that reads an episode again after seeing the question may be legitimate, but
its extra pass belongs in the cost and in the comparator's allowed information.

Proposed research screens should have fixed scope and measured runtime before
training. The council opens no additional tuning allowance. A promising screen
must survive fresh seeds and untouched test examples before becoming a primary
claim. An empty confidence interval calculation caused by insufficient data
is not evidence of equivalence or a failed architecture.

## What the synthesis must return

For each surviving idea: one plain-language example, its exact change, what is
already known, what is hypothesized, the cheapest decisive comparison, compute
and supervision costs, a failure criterion, and a dependency on current results.
Record disagreements and ideas rejected after critique. Select a short sequence
of experiments rather than a combined redesign. An interaction study comes
after standalone mechanisms show evidence, not before.

## Lead candidate: move the teaching signal before adding machinery

Plain explanation: if a problem needs several steps, asking for the final
answer after every unfinished step may teach the model to skip the steps.
This is a hypothesis about this trainer, not an established explanation of D's
failure. A single Think pass has two attention layers and may already solve
some multi-fact problems, so loop count is not a proof of required reasoning.

In the current `PremonitionMini.forward`, the decoder is trained against the
final answer after every loop. In gold mode, all evidence is already present,
so the early-answer discount does not reduce this pressure. The answer loss is
the average of these loop losses. Thus a new recurrent-reasoning design must
be compared with a much cheaper training change: final-loop answer supervision
on the existing repaired model. This requires no proof labels or hidden depth
at inference. It can also avoid intermediate decoder training passes; those
savings must be measured and their changed gradient path acknowledged.

Use a preset loop budget independent of each example's oracle depth, and compare
all-loop loss with final-loop loss on the same mixture, initialization, data
and common ordinary evaluation. Fix the number of decoder computations or
report their difference; include equal total time as well as equal examples.
If a proposed trace-trained executor wins, compare it to this control before
attributing the gain to new scratch machinery. Final-only supervision may make
optimization worse by removing useful short gradient paths; keep that negative
outcome. No outcome is predicted as certain and no run is authorized here.

For any reasoning result, train a genuine no-Think control. Disabling a trained
Think branch only at evaluation is a distribution shift, useful as a diagnostic
but insufficient by itself. Separate read count from loop count and keep the
available facts fixed when measuring the benefit of computation.

Two further reasons for cautious evaluation come from primary papers. Ramesh
et al. find that their synthetic function-composition task depends strongly on
training composition order and the availability of intermediate outputs;
their controlled task uses explicit function identifiers. This motivates an
order-held-out diagnostic here, not a claim that their success transfers to
Premonition's latent loops. [Paper, sections 3–4 and appendix A](https://arxiv.org/html/2311.12997v2).
Zhou et al. show that addition length extrapolation can vary greatly with weight
initialization and data order even when ordinary accuracy is excellent. Their
headline curves select best trials. Report every seed and the chosen-checkpoint
rule instead of selecting the best deeper-problem result.
[Paper, sections 4.2–5](https://arxiv.org/html/2402.09371v1).
