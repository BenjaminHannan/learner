# Opus research handoff: a small, controlled TST pilot

> Still conditional: milestone 2 does not activate this pilot. Read the
> [deeper research](/Users/ben-hannan/Desktop/projects/beautiful-model/design/research/2026-09-18-deep-research.md)
> for the revised order, context/data controls and limits on interpreting gains.

Ben proposed Token Superposition Training (TST). This is a separate local
research comparison, after completion/review of the correctness milestone and
availability of a working ordinary question-centred training baseline. It does
not interrupt or overwrite that milestone. If prerequisites are missing, return
a readiness assessment and exact missing work before training.

Astra's recommendation and source links:
design/research/2026-09-18-improvement-research.md.
Primary method: https://arxiv.org/abs/2605.06546 and
https://nousresearch.com/token-superposition.

Work in /Users/ben-hannan/Desktop/projects/beautiful-model using the registered
Python 3.12 runtime and runtime.local.json import roots. System python has no
torch. Read the current decisions log and spec overrides. Use additive
premonition modules; preserve all old code, caches, checkpoints and artifacts.
Do not modify learnlab/ or interfere with an agent editing shared files.

Mac CPU/MPS only. **No paid compute is authorized.** Training across all arms
and any reruns is capped at 30 minutes for this pilot. Profile first and freeze
a small equal-FLOP budget before training. Use seed 0 for the screen; a result
from this seed is exploratory. Do not automatically launch a larger sweep.

## Question

Does a brief preparatory stage with coarse token prediction improve subsequent
ordinary question answering per unit of total training work?

Start on pointerized Core E, a comparator already in the project. This is not
an adoption of a plain transformer as Premonition's final architecture. The
eventual test on D depends on a positive result and a profile of D's costs.

Use the v2 tokenizer, identical model shape/initial weights, compatible pointer
permutations, and an identical label-free data policy in three named arms:

- E-AR-pretrain: standard next-token prediction for the entire preparatory budget.
- E-TST2: for the first 20% of preparatory compute, average each non-overlapping
  pair of embeddings and predict the next non-overlapping pair with the mean
  of its token cross-entropies. Then restore ordinary next-token prediction.
- E-BAG2-output: for that same initial compute allowance, preserve ordered input
  positions and predict the next two tokens as a bag from one output head.
  Then restore ordinary next-token prediction. This has no input compression.

Our 20%-of-compute schedule and pair size are proposed small-model settings, not
an exact reproduction of the authors' large-model schedules. Name and record
adaptations. All arms then receive the SAME question-centred answer-only
training budget with label-free prefixes. Include preparatory training,
recovery and answer training in the total cost. Carry weights/optimizer state
through each phase and record the learning-rate schedule; do not reset an arm
unless the same reset is explicitly applied to its control.

## Correctness requirements

Test next-bag alignment with a hand-checkable sequence; target bags cannot be
part of their input context. Duplicate target tokens count more than once:
for [E,E,F,G], masses are 1/2, 1/4, 1/4. Do not deduplicate targets. At s=1 the
wrapper must match ordinary training, including gradients within tolerance.

Bag boundaries must respect visits and question/answer/feedback regions. Earlier
labels never enter inputs, including through pooled vectors. Padding contributes
neither embedding weight nor loss; define how partial bags are handled. Mask
invalid positions and forbid future leakage. Use a memory-efficient loss
implementation; do not create a dense target cube unnecessarily. Add positional
encoding at latent positions after input averaging. Verify normal-token checkpoint
loading and ordinary inference after recovery.

Freeze and hash the generator, pattern bank and data for every compared run;
the correctness log reports concurrent edits to those files. Do not mix data
versions across arms or reuse a cache whose generator identity has changed.

Preserve and report raw-token span as well as latent context length. TST can
see more raw history at a fixed latent length, which may itself help. Include
a context-matched diagnostic before attributing a gain solely to learning.
Keep question-centred evaluation context identical across arms.

Record raw tokens, processed positions, supervised targets, unique visits,
data reuse, data-generation time, forward/backward FLOPs, train/eval seconds and
peak memory. Compare equal total compute, then an equal-raw-token checkpoint
where feasible without adding a sweep. More fresh examples are permissible
only from the training generator. Keep validation and test seeds separated and
do not access the test split. Repeatedly reading the same file is not new data.

## Judge the recovered model

Use ordinary next-token validation loss and held-out question accuracy after
normal-token recovery and the common answer-training phase. Never compare raw
bag loss numerically with ordinary next-token loss as a success criterion.

Report familiar shallow reasoning, fresh names, paired role-swaps (both members
correct), corrected facts and invariance cases. Construct swaps from valid
simulator events, not arbitrary text edits that leave wrong answer labels.
If the ordinary baseline has not learned, report that limitation; a flat tiny
pilot does not refute the method at a larger scale.

Do not claim the paper's 2.5× speedup transferred. A promising screen earns a
later three-seed test. That later test would preregister a common reasoning
target, require ≥20% less total measured training time to reach it, and establish
no >3-point loss on the critical binding slices with enough independent visits.
No new rental budget is allocated to TST.

Return reviews/opus-research-tst-<unique-id>.md with a plain-language result first,
then changed files, exact commands, source/data identities, tests, all three
learning curves and resource measurements, failed checks, and a keep/drop/
inconclusive recommendation. Preserve every run and append decisions honestly.
