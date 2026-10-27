# 0\. Header

**Reviewer 4/5 — Autonomous Practice**  
**Effort: high**  
**BROWSING: no**

Prior judgment before reading the review, code, and evidence pack:

1. Curiosity-driven practice is likely useful, but only if the system measures *improvability* rather than novelty or surprise; naive curiosity rewards noise.
2. Checked self-practice can create real learning signals, but a checker that always reveals answers risks turning the system into a disguised supervised learner rather than an autonomous learner.
3. Persistent unfinished state is potentially valuable, but its value must be separated from ordinary persistent weights and reproducible checkpoints.

After reading the materials, my judgment is mostly unchanged. The design correctly identifies many risks, especially noisy curiosity, replay contamination, and checkpoint requirements. The main weakness is that autonomous practice is still underspecified: the system does not yet have a reliable definition of “this task is worth practicing,” and the current synthetic environment makes the checker signal much cleaner than real autonomous learning would be.

* * *

# 1\. Strongest objections ranked by likely impact

## 1\. Learning progress is much harder than curiosity, and may be too noisy for ten-minute experiments

**Impact: very high**

The architecture correctly distinguishes curiosity from learning progress, but learning progress itself is not automatically reliable.

Prediction-error curiosity:

rt​\=∣∣y^​t​−yt​∣∣

measures surprise.

Learning progress instead attempts to estimate:

LPt​\=E\[future error reduction\]

A simple version:

LP\=Lold​−Lnew​

where L is loss on the same task distribution before and after practice.

The problem is that with tiny task pools and short runs, the estimate has high variance. A task can appear to have large progress because:

- the first measurement was unlucky,
- the second measurement sampled easier examples,
- the model temporarily memorized examples,
- the evaluation noise dominates the true improvement.

The reward shape also matters. If selection uses:

max(0,LP)

then noise becomes a positive bias. Even if true progress is zero:

E\[max(0,ϵ)\]\>0

for measurement noise ϵ.

### Failure scenario

The selector repeatedly chooses tasks where evaluation variance is highest. The system believes it is learning because noisy improvements appear after practice. It ignores stable skills because their measured progress is small.

### Smallest resolving observation

Run the selector against three task classes:

1. learnable tasks,
2. impossible/noisy tasks,
3. already mastered tasks.

Measure whether it prefers category 1 over category 2.

**Evidence:** VERIFIED-PACK. The review cites curiosity failure modes from Burda et al.; the evidence pack confirms prediction-error curiosity suffers in stochastic environments.

* * *

## 2\. The checker currently makes practice equivalent to supervised learning

**Impact: very high**

In `tasks.py`:

Python

```
def feedback(self, question, response, teaching=False, hint_level=0):
    return Feedback(True, self.answer(question), ...)
```

The system receives the correct answer after every attempt.

This is a valid training setup, but it is not autonomous learning in the strongest sense.

The important distinction:

### Supervised learning

Input:

(x,y)

Update:

θ←θ+∇L(fθ​(x),y)

### Autonomous practice

Input:

x

Output:

a

Receive limited feedback:

r(a)

Discover useful improvement.

The current setup tests whether the writer can store externally supplied truths. It does not test whether the system can decide what it needs to know.

This does not make the experiment useless. It tests memory writing. However, the claim should be limited.

### What changes with weaker checkers?

A progression would be:

| Checker | Learning signal |
| --- | --- |
| exact answer revealed | supervised distillation |
| pass/fail only | reinforcement signal |
| delayed score | credit assignment |
| noisy score | robustness |
| no checker | self-consistency/world modeling |

### Absolute Zero comparison

Absolute Zero demonstrates that a pretrained model can generate and solve executable tasks with verification.

It does **not** show:

- an untrained tiny model can discover useful tasks,
- a model without existing language ability can bootstrap itself,
- checker feedback alone creates intelligence.

**Evidence:** VERIFIED-PACK. Absolute Zero uses pretrained Qwen/Llama models and a code executor.

* * *

## 3\. Replay can silently become retrieval instead of learning

**Impact: high**

Replay is useful, but checked experiences contain answers.

A replay item:

(x,y,trace)

contains the information the system is supposed to learn.

This creates a contamination risk.

A model could pass evaluation by:

- storing examples,
- retrieving similar experiences,
- copying answers.

That is different from:

- learning a fact representation,
- learning a method,
- transferring to unseen cases.

### Required separation

The system needs:

1. Practice pool  
   Experiences allowed for replay.
2. Development pool  
   Used for tuning.
3. Final test pool  
   Never stored or replayed.

Additionally every memory item needs provenance:

```
source = generated_practice
source = human_teaching
source = checker_correction
source = replay
timestamp
generator_version
```

### Decisive test

Train on:

- exact examples,
- paraphrases,
- unseen entities,
- unseen rule compositions.

If performance collapses only when examples change, the system learned retrieval.

**Evidence:** VERIFIED-PACK. Experience replay helps continual learning but does not establish broad method transfer.

* * *

## 4\. Self-generated practice has strong degeneration risks

**Impact: high**

A learned generator creates a second learning problem.

The generator can optimize:

maxE\[reward\]

and discover shortcuts.

Examples:

### Trivial task attractor

Generate only:

```
What is 1+1?
```

because it maximizes success.

### Self-confirming error

Generator proposes tasks based on its current beliefs. The checker accepts those beliefs. The system reinforces mistakes.

### Always-write policy

If writes are rewarded immediately, the easiest strategy may be:

always write

rather than selective learning.

A deterministic generator is safer initially because it removes this failure mode.

However, deterministic generation does not demonstrate creativity. It only tests learning.

### Positive control

Compare:

- random generator,
- hand-designed curriculum,
- learned generator.

The learned generator should outperform random selection without collapsing into easier tasks.

* * *

## 5\. Persistent unfinished workspace may matter, but only under strict controls

**Impact: medium-high**

The architecture distinguishes:

- persistent weights,
- saved workspace,
- continuous computation.

This distinction is correct.

The question:

What can a saved workspace preserve that restarting from weights cannot?

Potential examples:

- intermediate reasoning state,
- unfinished plans,
- exploration branches,
- uncertainty estimates.

But it may simply be equivalent to saving activations.

The decisive experiment:

Start from identical state:

S0​\=(W,z,x,RNG)

Branch A:

```
pause
resume
continue
```

Branch B:

```
continue immediately
```

Compare outputs.

If they differ, identify why:

- asynchronous data,
- randomness,
- cache state,
- numerical differences.

### Required checkpoint contents

A meaningful checkpoint requires:

- model weights,
- memory weights,
- optimizer state,
- workspace state,
- RNG states,
- software version,
- tokenizer version,
- generator state,
- replay position,
- cache state.

A random seed alone is insufficient.

* * *

# 2\. Strongest defensible case FOR the architecture

The strongest case is that autonomous practice does not need to solve intelligence from scratch. It only needs to create a controlled mechanism where experience improves future behavior.

The architecture has several good properties:

## 1\. It separates temporary reasoning from permanent learning

The distinction:

zt+1​\=Fθ​(x,zt​,mt​)

versus:

W′\=W+ΔW

is important.

Many systems confuse:

- thinking longer,
- remembering later.

This design explicitly separates them.

## 2\. A checker can provide a clean learning signal

Even if the checker is not autonomy, it is valuable for early experiments.

A tiny system cannot learn useful memory writing without some signal.

The first milestone should not be “self-directed intelligence.”

It should be:

> Can a system store checked experiences and generalize beyond them?

## 3\. Learning-progress selection is a reasonable long-term direction

Humans do not simply seek novelty. They often practice things where improvement is possible.

A task selector based on estimated improvement is more aligned with useful learning than raw uncertainty.

## 4\. Persistent unfinished state is experimentally testable

Unlike many claims about autonomous systems, this one has a clear experiment.

The system either benefits from preserved workspace or it does not.

* * *

# 3\. Classification of issues

| Issue | Classification |
| --- | --- |
| Learning-progress estimation noise | Training problem + unknown |
| Checker revealing answers | Engineering choice |
| Replay contamination | Engineering choice |
| Learned generator collapse | Training problem |
| Persistent workspace value | Unknown |
| Writer/selectors reinforcing mistakes | System interaction problem |
| Curiosity noisy-TV failure | Fundamental limitation of naive curiosity |

None of these are fundamental limitations of the overall architecture. They are mostly failures of objective design and evaluation.

* * *

# 4\. Simpler competing designs

## A. External episodic memory baseline

Instead of modifying weights:

M\={(k,v)}

Use retrieval.

Advantages:

- easy auditing,
- low forgetting,
- clear provenance.

Disadvantage:

- does not satisfy strong weight-learning goals.

Useful as a baseline.

* * *

## B. Fixed curriculum + learned writer

Remove autonomous selection.

Pipeline:

```
task generator
      |
      v
checker
      |
      v
writer
```

This isolates whether writing works.

* * *

## C. Learned selector + no learned generator

The selector chooses from a known task distribution.

This tests:

which tasks should I practice?

without adding:

what tasks should exist?

* * *

## D. Replay with explicit consolidation

Maintain:

- fast memory,
- slow memory.

Fast memory handles recent experiences.

Slow memory consolidates useful information.

This is closer to continual-learning approaches.

* * *

# 5\. One bounded experiment (<10 minutes)

## Experiment: Does learning-progress selection avoid noise?

### Setup

Three task pools:

1. Learnable arithmetic transformation tasks.
2. Random noisy tasks.
3. Mastered tasks.

Use the same learner and writer.

Compare:

- random selection,
- prediction-error curiosity,
- learning-progress selector.

### Positive control

A fixed curriculum selecting only learnable tasks.

Expected:

Fixed curriculum should improve.

### Outcome counting AGAINST proposal

The proposal fails this experiment if:

- learning-progress performs no better than random,
- it selects noisy tasks frequently,
- it cannot distinguish mastered from improvable tasks.

This experiment does not prove autonomous intelligence. It only tests whether the selector provides useful training allocation.

* * *

# 6\. Component interactions isolated ablations may miss

## Selector ↔ Writer

A selector chooses what gets practiced.

A writer decides what becomes permanent.

These can create feedback loops:

1. Selector chooses easy tasks.
2. Writer becomes optimized for easy tasks.
3. Selector observes improvement.
4. System reinforces the bias.

A good selector can make a bad writer look good.

* * *

## Replay ↔ Memory

Replay can hide memory failures.

Without replay:

write→retain

With replay:

write+retrieve

may look like learning.

* * *

## Checker ↔ Generator

A weak checker allows generator exploitation.

A strong checker may make the task too supervised.

* * *

## Workspace ↔ Practice

Saved reasoning states could become a shortcut.

The system may store unfinished answers instead of learning reusable methods.

* * *

# 7\. Corrections to RESEARCH\_REVIEW.md

## Correction 1

Passage:

> “Begin conceptually with a bounded external synthetic generator, a task-selection rule, and a checked replay buffer.”

Issue:

This is correct but should explicitly separate “learning from feedback” from “autonomous learning.”

Corrected statement:

> Begin with checked practice as a controlled learning mechanism. Treat autonomy as a separate hypothesis requiring tests where the system chooses useful activities without answer-revealing feedback.

* * *

## Correction 2

Passage:

> “Compare random selection, uncertainty selection, and estimated learning progress.”

Issue:

The review does not emphasize enough that learning-progress estimates require repeated measurements.

Corrected statement:

> Learning-progress selection requires variance estimation, repeated evaluation, and protection against positive noise bias from max-based rewards.

* * *

## Correction 3

Passage:

> “A learned generator is a later distinct question.”

Issue:

Correct, but the dependency should be stronger.

Corrected statement:

> A learned generator should only be introduced after learner and selector behavior are validated, because generator failures can hide learner failures.

* * *

No other major corrections found.

* * *

# 8\. Retain, revise, defer

## Retain

### Checked synthetic practice

Confidence: **high**

Useful for validating memory writes.

### Replay with provenance

Confidence: **high**

Necessary for continual learning experiments.

### Persistent workspace checkpoint tests

Confidence: **high**

Clear and falsifiable.

* * *

## Revise

### Learning-progress reward

Confidence: **high**

Needs uncertainty estimates and repeated measurements.

### Checker design

Confidence: **high**

Need staged progression from answer reveal → weaker feedback.

### Autonomous task selection

Confidence: **medium**

Useful, but too early as a core dependency.

* * *

## Defer

### Learned task generator

Confidence: **high**

Too many interacting failure modes.

### Large-scale autonomous practice

Confidence: **high**

The current system lacks enough validated mechanisms.

* * *

# 9\. Single most consequential design decision

The most important decision is:

**Define exactly what feedback the writer receives during practice.**

Everything else depends on this.

If feedback is:

(x,y)

the system is learning supervised memory.

If feedback is:

(x,r)

the system must discover useful behavior.

If feedback is absent:

the system requires stronger internal objectives.

The writer, selector, and memory system cannot be evaluated until this contract is fixed.

* * *

# 10\. Citation ledger

## VERIFIED-PACK

- Burda et al. (2018), “Large-Scale Study of Curiosity-Driven Learning.”  
  Supports noisy-TV and prediction-error curiosity limitations.
- Rolnick et al. (2019), “Experience Replay for Continual Learning.”  
  Supports replay benefits and limitations.
- Zhao et al. (2025), “Absolute Zero: Reinforced Self-play Reasoning with Zero Data.”  
  Supports the distinction between pretrained models with verifiers and untrained systems.
- Graves (2016), “Adaptive Computation Time.”  
  Supports compute allocation concepts.
- Banino et al. (2021), “PonderNet.”  
  Supports learned halting mechanisms.
- Geiping et al. (2025), “Scaling up Test-Time Compute with Latent Reasoning.”  
  Supports recurrent computation as a separate mechanism from permanent learning.

## UNVERIFIED

None used for substantive claims.

## VERIFIED-LIVE

None. Browsing was not performed.
