# Established memory-network baseline: scope and interpretation

User request: compare a small established memory network with Premonition on the
same held-out-relation task and budget. The later request authorizes local coding,
tests, checkpoint evaluation and bounded CPU training for this comparison. The
earlier prohibition on GPU/SSH/paid resources is retained. No remote service,
credential directory, installation or download is used.

## What is implemented

An additive reimplementation of the **layer-wise tied End-to-End Memory Network**
from Sukhbaatar et al. (2015), with published sentence position encoding and three
soft memory reads. Independent A, C, B and W matrices encode keys, returned values,
questions and answer logits; a shared H transforms the controller between reads.
The memory inputs are complete visible non-question lines, including filler lines.
No parsed subject, object, relation, gold card, supplied card subset or token-role
mask enters the neural forward. Ordinary sentence boundaries and question spans
are shared with Premonition. Position encoding distinguishes directed link order.

This is the older architecture, not the older authors' exact training recipe.
The optimizer uses the repository's AdamW settings (1e-3 learning rate, .9/.99
betas, .1 matrix decay, gradient clipping at 1, 100-update warmup). H starts as the
identity; embeddings and output weights use standard deviation .1. Only final
answer-token cross-entropy trains the baseline. There is no language-model loss,
evidence loss, teacher-card schedule, ASK gate or learned stopping rule. A fixed
EOS is appended to its one-token prediction; this is a toy answer classifier.

At width 177, parameter count is `4*68*177 + 177^2 = 79,473`, versus the control's
79,748 (0.345% fewer). The archived plain controls preserve their own full decoder,
training losses and inference policy. This comparison cannot identify the causal
effect of hard versus soft retrieval independently of these other differences.

References: [End-to-End Memory Networks](https://arxiv.org/abs/1503.08895),
[Key-Value Memory Networks](https://aclanthology.org/D16-1147/).

## The resource distinction is material

A 40-update CPU rehearsal at width 177 took 0.531 seconds and counted 2,455,140,096
training FLOPs, about 4.62e9 counted FLOPs/second. This projects approximately 163
seconds for 12,251 updates, but approximately **4.10 hours per seed** to spend the
historical 6.81e13-FLOP budget. These are rehearsal estimates, not completed-run
times. The rehearsal's generator lacked the subsequently corrected serial draw;
its timing estimate is approximate, and it was not a roster training run.

The authorized local execution therefore first performs an explicitly named
**exposure-matched historical-reference screen**: each baseline sees the same
frozen training stream, 16 visits/four questions per visit, for the corresponding
historical control's exact actual update count. The historical per-seed FLOP
budget is a ceiling, not a claim of equal compute spent. The runner records actual
FLOPs, exposure completion and full-budget completion separately. A time stop is
incomplete. Full-budget execution is implemented as a separate command and must
not be described as completed by these screen results.

This substitution was disclosed in chat before roster training. It can answer
whether an older architecture already solves the task within a smaller allowance.
A failure cannot answer whether the older architecture would solve it after
spending the entire allowance. An exact-spent-FLOP study remains separate.

## Frozen screen

The plan selects seed IDs **0,1,2**, the first three numeric historical IDs,
before observing baseline outcomes. No replacements, extension, tuning against
the test cells or selecting the best checkpoint. These happen to be learned plain
runs, so the three controls do not represent the full 40-run stuck distribution.
Identical numeric IDs across different architectures do not imply matched initial
tensors or identical optimization trajectories. The screen is descriptive.

The stream uses the frozen generator, seed 1101 and its additional per-batch serial
draw. No held-out relation-2 two-hop question occurs in training. Label-free source
question inputs were checked against the original batch assembler on successive
batches. Full store causality and no use of evidence/answer labels in inference
are checked separately.

All six existing development panels are byte-verified and reused unchanged.
Both the new models and saved plain checkpoints are scored anew on local CPU.
All single-cell and paired-world counts retain the original sizes and integer
thresholds. Both members must be correct for pair credit; the irrelevant-edit
cell also requires identical outputs. Every model's weights are fingerprinted
before and after evaluation. Plain inference must match its original fixed-K4
routine and pass world-isolation checks. Soft reads are the baseline's primary
policy; hard-argmax reads are a secondary diagnostic and cannot rescue it.

Meeting the six answer thresholds with soft reads is **not official G_pair
advancement under the existing hard-retrieval policy**, nor G_cert. The common
panel is already a development panel, not fresh certification data. Historical
control training used different hardware/software. READS, new-seed reliability,
and noninferiority admission are outside this first screen. No recipe is promoted.

## Execution and records

Files added:

- `scripts/premonition_memnn.py`: model, visible-input conversion and counted FLOPs.
- `scripts/premonition_memnn_compare.py`: frozen plan, bounded training, evaluation
  of both models, native-policy integrity and generated report.
- `tests/test_premonition_memnn.py`: nine CPU checks, including gradient routing,
  exact counter agreement, label independence, stream parity, causal masking,
  padding/order, world isolation and joint pair counting.

The initial plan directory is retained as **not run**: a subsequent two-batch
integrity check found the missing RNG serial draw before any roster learning.
Its source hash is obsolete, and its runner refuses it. The corrected frozen
plan and all outcomes are in `artifacts/codex-memnn-comparison-20260919-v2/`.
Existing model files, scripts, tests, designs, datasets and checkpoints were not
edited. CPU execution is bounded to 1,800 seconds per wave and 1,200 seconds of
training per job. Actual times and zero paid-compute cost are recorded separately
from this design note.

Results and conclusions belong in that directory's generated `REPORT.md` and
`completion.json`; this pre-result note makes no performance claim.
