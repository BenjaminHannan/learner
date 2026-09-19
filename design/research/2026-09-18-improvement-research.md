# Premonition improvement research: make learning easier, then make it cheaper

> Later review, 2026-09-18: the immediate priority ranking below is superseded
> by [the deeper review](/Users/ben-hannan/Desktop/projects/beautiful-model/design/research/2026-09-18-deep-research.md).
> The trainer handoff reports failure even with correct cards supplied. First
> reproduce and repair the answer path; do not start with a new retrieval method.
> TST remains conditional on a working baseline.

Research completed for Ben on 2026-09-18. This is a source review and code
inspection, not a training result. Astra designs and reviews; Opus implements
and runs. New rental spending for this research: **$0**. No rental authorized.

**My recommendation:** first make sure answer mistakes can teach the memory
selector, then check whether the model stops too early. Test Token Superposition
Training (TST) as a separate, small pretraining experiment after the correctness
milestone. It may save training work, but does not repair a disconnected learning
signal. Preserve the existing model and compare separately named variants.

The important distinction is between **learning better** (solving new examples)
and **training faster** (doing fewer calculations to reach the same ability).
We need evidence of the first before claiming the second.

## What the current code tells us

These are observations of the inspected source, not explanations proven by a
training run. The files may change while Opus works; hashes appear below.

| Observation | Plain-language meaning | Evidence |
|---|---|---|
| Own retrieval uses `store.top(scores.detach(), ...)`; insertion gathers values without a differentiable use of selection scores. | The answer's error cannot directly adjust the query/key parameters through the choice of cards. Separate evidence teaching can train those parameters. Shared reader parameters still receive other gradients. | [model.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:608), [store.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/store.py:119) |
| The model computes gold evidence, uses it to scale answer losses, and sometimes supplies gold cards. | Setting the evidence-loss weight to zero alone does not make an experiment free of evidence supervision. | [model.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:547), [model.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:582) |
| HALT is checked before retrieval; finished questions receive no new cards. | A model can stop before looking anything up. One think loop in this implementation allows zero retrievals; K loops allow at most K−1 retrieval rounds. | [model.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:712) |
| Training's stopping target uses predictions supplied with correct preceding answer tokens. Evaluation generates its own preceding tokens. | The stop signal is trained under easier conditions than normal answering. This is a mismatch to investigate, not proof that it caused the toy failure. | [model.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:557), [model.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:731) |
| The toy draws random filler tokens, while next-token and answer losses each have default weight 1. | Some language-prediction work concerns unpredictable noise. It might compete with fact learning. Both losses are averaged, so more filler tokens do NOT by themselves prove language loss dominates. | [toy.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/toy.py:87), [config.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/config.py:48) |
| Cards pool the recurrent reader's outputs, and question states also come from that reader. | Facts have more than one route to the answer. Removing one card need not remove all information about its fact. | [model.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:183), [model.py](/Users/ben-hannan/Desktop/projects/beautiful-model/premonition/model.py:410) |

New `preprocess.py`, `identity.py`, and Opus probe artifacts now exist. The
saved probe reports removal of C's candidate gap and changed near/far counts
under label-free inputs. I have not independently rerun those probes or accepted
the completed correctness milestone in this research pass. Their results concern
input correctness, not learned reasoning accuracy. Source:
[Opus probe](/Users/ben-hannan/Desktop/projects/beautiful-model/artifacts/opus-m01-20260918-202731/probe.json).

An Opus completion entry appeared in the decisions log during this research.
It also reports concurrent changes to the village renderer and pattern bank.
Freeze the generator, pattern bank and data identities across compared runs;
otherwise changed examples could be mistaken for a training improvement. This
memo does not constitute acceptance of that milestone's final verification.

## Ranked improvements

**1. Give the memory selector a direct learning signal.** A gradient is the
signal telling a parameter which change would reduce an error. In soft retrieval,
each eligible card receives a weight and contributes to a weighted read. That
lets answer errors teach the weights used to find memories. End-to-End Memory
Networks established this approach for multi-step question answering; Key-Value
Memory Networks separated what is searched from what is read. Neither paper
proves this will fix Premonition. [Memory Networks](https://arxiv.org/abs/1503.08895),
[Key-Value Memory Networks](https://aclanthology.org/D16-1147/).

Our test: verify the gradient path, then compare existing D with the already
specified D-soft baseline. D-soft should attend only to earlier non-question
cards plus NULL. Start without evidence labels; use fixed reasoning steps.
Check answer-only gradients reach both query and key projections on several
nondegenerate batches. There must be no gold-dependent card selection, loss
weighting, loop count or stopping rule. Shuffling gold metadata must leave its
training loss and gradients unchanged with identical random state. Evidence
labels may be used afterward to measure retrieval, outside the loss path.

A soft read may mix incompatible facts. More than one read row can help, but
is a separate design choice: record it and count parameters/compute. It is also
possible that D with evidence labels wins. That would support supervised memory,
not prove answer-only learning is impossible.

**2. Separate finding facts, using facts, and deciding when to stop.** First
give the correct cards and use a fixed loop count. Next let D choose its cards
while keeping the fixed loop count. Finally enable its learned stopping rule.
This measures where accuracy is lost. Disable early HALT explicitly: merely
passing `max_loops=4` still permits an earlier stop. Measure ASK separately;
forcing retrieval changes that decision too and must have its own named row.

Tiny Recursive Models supports investigating repeated refinement and supervision
at intermediate steps. It does not establish that extra loops improve every
task. A 2026 controlled autoregressive study found no reliable gain from the full
autoregressive TRM in its tested setting. This supports measuring useful work
per loop instead of assuming more loops mean more reasoning.
[TRM](https://arxiv.org/abs/2510.04871),
[Tiny Autoregressive Recursive Models](https://arxiv.org/abs/2603.08082).

**3. Give reasoning priority over predicting filler.** Compare the current toy
objective with answer-focused training while keeping data, initialization and
retrieval settings fixed. Measure each loss's gradient size and direction on
the shared reader. Multi-task learning research documents conflicting gradient
signals; it motivates this measurement, not an automatic new optimizer.
[Gradient Surgery](https://arxiv.org/abs/2001.06782).

Start with one ablation: language-loss weight 1 versus 0 on the toy. A lower
combined loss is not success; held-out answers must improve. If the zero-weight
branch still computes language logits, count that cost. Real village text may
benefit from language learning even if random toy filler does not.

**4. Test word-order and role binding directly.** Binding means connecting an
entity to its role: who gave an object, who received it, and where it went. Use
paired cases with identical words but swapped giver/receiver roles, random
entity IDs, corrected facts, and several relations for the same entity. Count
both members correct and also test changes that should leave the answer alone.

ESBN supports separating reusable relations from particular identities;
Abstractors provides evidence for explicitly emphasizing relations in other
tasks. Neither validates a new module in this code. Only if gold-evidence
reasoning fails these probes should we propose role-aware encoding or a
line-local card encoder. Any long-term store change goes to Ben first.
[ESBN](https://arxiv.org/abs/2012.14601),
[Abstractors](https://arxiv.org/abs/2304.00195).

**5. For later continual learning, measure learning capacity as well as memory.**
A model can remember old tasks yet become worse at learning new ones. Research
on plasticity documents this distinction; replay research supplies a practical
baseline. Test ordinary bounded replay before adding several sleep mechanisms.
New-task acquisition and old-task retention must be measured separately with
fresh episode facts. Neither source establishes that our proposed sleep design
works. [Plasticity](https://arxiv.org/abs/2306.13812),
[Replay](https://arxiv.org/abs/1811.11682).

## Ben's TST idea

**Verdict: worth a free pilot, after the correctness gate.** TST teaches a model
using groups of tokens first, then restores ordinary next-token training. The
paper reports roughly 2.5× lower training time at similar loss for its large
mixture-of-experts experiment. The authors' table compares 4,768 versus 12,311
B200 GPU-hours, with 2T versus 1.05T raw tokens consumed. Its smallest tested
model has 270M parameters. Those measurements are far outside Premonition's
roughly 2M setting. [Authors' results](https://nousresearch.com/token-superposition).

The paper explicitly identifies greater data consumption as a tradeoff and
suggests **output-only superposition** for data-limited settings. That keeps
ordered inputs but predicts a bag of upcoming tokens. It tests the target's
learning benefit without shortening the input. The authors did not run repeated
identical large experiments to establish statistical significance.
[Paper, §7](https://arxiv.org/pdf/2605.06546).

**My application to this project:**

- Averaging is unchanged by a permutation inside a bag. If giver and receiver
  IDs swap positions within the same bag, the input average is identical. This
  does not mean every whole sentence loses its order: order between bags stays.
  Recovery training might restore the needed distinctions; our role-swap probes
  must check whether it actually does.
- We can generate fresh simulator visits, so we are not necessarily limited to
  the existing file's token count. More visits still do not add new kinds of
  reasoning automatically. Measure generation speed, independent visit count,
  repeated exposure and new compositions before claiming abundant useful data.
- D has a reader, card writer, thinking steps and an answer decoder. Compressing
  only the reader does not reduce all of those costs. Profile them before
  predicting a whole-system speedup. Its line/question offsets also make TST
  more invasive than changing a plain language-model input.
- Test first on the existing pointerized Core baseline E. This is a cheap
  measuring instrument; adopting a plain transformer as Premonition's final
  design is a separate decision that remains Ben's.
- Keep ordinary ordered answer training. TST belongs in a separate preparatory
  phase, followed by normal-token recovery and the same answer-only training in
  every arm. Comparing TST+extra pretraining to an unpretrained baseline would
  mix two changes.
- Ordered multi-token prediction is another research option: predicting several
  future positions separately preserves target order but adds its own cost.
  Leave it out of this small pilot to avoid a wide search.
  [Multi-token prediction](https://arxiv.org/abs/2404.19737).

Proposed three-arm pilot (our settings, not a claim they are optimal):

| Arm | First 20% of preparatory training compute | Remaining preparatory training | Then |
|---|---|---|---|
| E-AR-pretrain | Ordinary next-token prediction | Ordinary next-token prediction | Identical label-free question-centred answer training |
| E-TST2 | Average neighboring pairs; predict the next non-overlapping pair | Ordinary next-token prediction | Same answer training |
| E-BAG2-output | Ordered input; one head predicts the next two tokens as a bag | Ordinary next-token prediction | Same answer training |

Start with pairs rather than four-token groups because the model is small and
the task depends on order. This is an engineering hypothesis, not a result from
the paper. The output-only arm offers no input-compression speedup. If it helps,
the evidence is about the learning objective, not reading fewer positions.

Use equal measured total training FLOPs for the main comparison and report
actual elapsed time, raw tokens, supervised targets, independent visits, and
data-reuse counts. Also compare at equal raw-token consumption. TST can expose
a longer raw history at the same latent length: record effective context and
include a context-matched diagnostic before attributing gains to the objective.
All conclusions concern ordinary-token evaluation **after recovery**, never a
direct comparison of the bag loss with ordinary next-token loss.

Keep averaging within permitted input spans. Do not mix visits, question/answer
boundaries, feedback or padding into a valid bag. Any boundary-aware adaptation
must be named and measured rather than called an exact reproduction. Repeated
tokens contribute repeatedly to the target average. Apply positional encodings
to the latent positions after averaging, consistently with the chosen method.

The local screen has a 30-minute training ceiling across the three arms. Profile
first, then freeze an equal compute budget that all three can finish. A short
screen may show nothing; call that inconclusive. Promote a candidate only if
ordinary validation loss and reasoning results justify it, then use seeds
0/1/2. A later efficiency success requires at least 20% less measured total
training time to a predeclared common reasoning target, without losing more
than three percentage points on role swaps or fresh-name reasoning. Use a
one-sided 99% visit-clustered bound for that non-inferiority claim and enough
visits; otherwise report uncertainty. This pilot does not authorize GPU spending.

## Decision order and costs

1. Finish and review Opus's correctness milestone.
2. Run the gradient/stop diagnostics and bounded toy repairs, prioritizing soft
   retrieval if the gradient test confirms the suspected limitation.
3. Establish a solvable village diagnostic. Run the TST pilot as a separate
   local comparison once the shared input and training paths are trusted.
4. Spend only from the existing $5 solvability envelope if a prepared GPU job
   is justified and Ben approves its exact quote. TST has **no extra rental
   allocation**; its local pilot does not authorize taking money from reserve.
5. Keep the existing research success gates. A token-prediction speedup alone
   does not establish better reasoning, useful memory, or continual learning.

The broader roadmap remains staged. This memo recommends experiments; it makes
no permanent architecture change. Opus prompts accompany it:
[learning diagnostics](/Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-research-learning-diagnostics.md)
and [TST pilot](/Users/ben-hannan/Desktop/projects/beautiful-model/reviews/opus-research-tst-pilot.md).

## Source snapshot

Inspected locally; no engineering files changed and no training run by Astra.
The existing 74-test result belongs to the earlier handoff, not a fresh test of
Opus's current edits. Literature statements above are from primary papers or
the authors' official page; transfer to Premonition is explicitly a hypothesis.

```
f6d8c36093f8d392a7a680db3ab46b5dc6b28bee3475d6cb9e3e58be6404fda5  premonition/model.py
62c75d70b369daf61cf862b28f87aa64bf6037314dd1a39a7df994b81d2b9531  premonition/store.py
b4ebde7cfccc2156617d89ee3f9a27a5fe58ea0e58d638a8bebe11176673f6c2  premonition/config.py
f7b945f080807c5dc4a5d91325d7ae3c760ea2de75c7bdf13c6da4c254f4deb9  premonition/train.py
c3a218c51d48f3e193ee0c4cde6fb73769ebf9da7787d5fd26c9d5d5acd84c0b  premonition/toy.py
af75a3acfd2e2a0a39ab9321bf8767e28c39db08b227784ee4eace3b08f3dafe  premonition/preprocess.py
769e9036514b14b046898c7867115c15f82d07bc9792621340afa1288cc59aca  premonition/identity.py
```
