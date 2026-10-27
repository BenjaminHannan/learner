# Ben's targeted sleep-training idea

Research synthesis, 2026-09-27. **Untested proposal.** This does not change AR1's
registered experiment, running code, marks or data. AR1 tests replay timing;
the controller described here would require a separate preregistration.

## What the proposed controller would do

The reasoner would continue to answer each puzzle using only the puzzle. During
training, a small controller would output a number between zero and one for each
declared group of weights. Zero permits no weight movement; one permits the
ordinary proposed movement; intermediate numbers scale it. It would learn which
permissions help from the consequences of training, rather than receiving a
hand-written assignment such as “these weights are the grid skill.” The groups
and measured training signals are implementation choices, not learned anatomy.

Ben's suggested feedback is the key objective: after learning something new,
measure how much of the old skill remains. The reward also needs new learning,
otherwise refusing all changes is an easy but useless solution. The controller
must be judged by actual exact old/new puzzle performance after several learning
steps, not by pleasing-looking gates or merely reducing a training loss.

The controller belongs to the training process. It would not be the reader/talker
and would not supply answers. Every controller parameter must still count against
the project's fixed total of 1,646,750. Its inputs, rewards and optimizer state
must never expose hidden task labels or targets to the served inference API.

## Evidence and limits

[ANML](https://arxiv.org/abs/2002.09571) provides a primary research precedent for
learning a modulatory gate that affects activation and plasticity. It does not
validate this small reasoner, a sleep-only controller, or our limited number of
updates. [Meta-Experience Replay](https://arxiv.org/abs/1810.11910) studies learning
with attention to transfer and interference; it likewise supplies motivation,
not a predicted pass on this benchmark. The two detailed research notes record
the alternatives and their costs: [protection](RESEARCH-PROTECTION.md) and
[context/MoE](RESEARCH-CONTEXT.md).

The strict replay budget matters. Checking an old example again to reward the
controller is still another old-example exposure and must be counted. Reusing
losses from scheduled replay avoids extra passes, but comparing different batches
introduces noise from puzzle difficulty, sizes, and recurrent training depths.
Those factors can mislead a controller about whether its choices caused harm.
The suggested small policy has fewer than 400 delayed reward opportunities, so
there is no basis yet to claim that it will learn a useful policy in this budget.

A retention-aware controller versus a new-learning-only controller would isolate
the reward objective, but **does not satisfy the requested dense-baseline
comparison by itself**. Any capability claim for a future controller needs a
same-size, same-Mac, freshly run dense-plus-replay comparator. An objective
ablation would be an additional declared arm or a separate experiment. We will
not redefine the main comparison around an easier control.

An implementation must scale the actual proposed AdamW displacement, including
momentum and weight decay. Scaling the raw gradient alone can be cancelled by
adaptive normalization and may not stop a supposedly protected weight moving.
Before training, forced zero gates must preserve reasoner weights bitwise;
forced one gates must reproduce the ordinary optimizer trajectory. These are
software checks, not retention results.

## Status of claims

- **Shown:** AR1's registered input-only model passed its bounded software
  checks. It is one same-size dense reasoner; the full capability runs are in
  progress. This does not demonstrate permanent retention.
- **Suggested:** reward-trained regional control is a concrete way to investigate
  Ben's idea, and the Mac can host this small model and controller prototype.
  Large-scale meta-training could take much more time than the current run.
- **Untested:** whether such a controller meets the numerical marks, whether it
  beats dense plus replay, how many training histories it needs, and whether it
  generalizes beyond the three native puzzle formats. No claim concerns the
  1B chat model, reader/talker, joined build, or skills lasting indefinitely.
