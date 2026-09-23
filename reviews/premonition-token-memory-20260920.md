# Token-memory successor: access is a prerequisite, transfer is the target

This is an opt-in Track A candidate responding to Ben's request to solve the
identified information-access/training weaknesses, with intelligence as the main
concern. No old source, checkpoint, default model, or earlier result is replaced.

## Mechanism

Each eligible story line is encoded by a small bidirectional transformer within
that complete line. Every token state survives. No question-blind line pooling is
used for the reasoning memory. Ordinary token positions give order within a line;
no semantic field position, entity/relation index, role label, gold card or answer
is consulted by the model. Line boundaries and question boundaries are visible
format metadata. Only completed lines preceding the question are eligible.

A separately encoded question initializes the reasoning state. Three passes of
the same recurrent transformer block each:

1. Attend over the current question state and the unchanged original question
   encoding, providing a persistent route to its requested attribute.
2. Use four heads to attend softly over every eligible story token.
3. Apply a feed-forward update.

The final visible question position predicts one of all 68 tokens through a tied
embedding classifier. EOS is appended deterministically, as in the preceding
memory-network screen. Training uses only the final answer cross-entropy. There
is no ASK decision, top-k operation, discrete card insertion, entity-slot binder,
teacher card, or evidence/role loss. Training and inference use the same forward.

This removes the identified hard retrieval gradient boundary and mandatory
pre-question compression. It makes relation information accessible at each pass;
it does **not** prove that the network uses it correctly or compositionally.

The model has 79,316 parameters versus 79,748 in plain Premonition. Attention
projections of the story are cached once per visit, shared by questions and read
steps. Padding is compacted without dropping real tokens. A zero NULL row makes
an empty eligible memory well-defined.

## Test and experiment contract

Eleven implementation checks cover parameter size, answer-to-search gradients,
every-token access, future-line exclusion, empty memory, padding invariance,
line-order invariance, world/question isolation, unchanged train/eval policy,
checkpoint reload, immutable question anchors, and exact counted-matmul FLOPs
(some checks cover multiple properties). The existing nine data-adapter and
memory-network checks cover the shared visible-input adapter and consecutive
training-stream parity. Source and data hashes are recorded before training.

Seeds 0, 1, 2 are fixed without replacement. Each gets precisely the archived
plain run's example/update exposure (12,251 / 12,250 / 12,250 updates of 16 visits),
unless a declared time or FLOP ceiling intervenes. All outcomes are reported.
Three independent single-thread CPU jobs may run concurrently, with at most 1,500
training seconds and 1,800 total seconds each. No GPU, remote machine, installation,
paid resource or outside messaging is used. Optimizer is AdamW, learning rate
.001 with 100-update warmup, betas (.9,.99), decay .1, clipping 1.

The original six-cell panel and its answer thresholds remain unchanged. A new
512-unit panel per cell is generated and checked by the exact evaluator before
training, with seeds 202609201001 through 202609201006. The old model is also
scored on these new worlds. Fresh screening thresholds are >=95% for one-hop and
practised two-hop, >=90% for held-out two-hop and joint counterfactual pairs. They
are raw accuracy screens, not confidence-certified admission cutoffs.

Success requires all three seeds to finish exposure, pass all six original answer
thresholds and confirm on the new worlds. Familiar-question accuracy alone does
not count. A memory-wipe lesion measures whether held-out answers actually depend
on story memory. No held-out outcomes select training checkpoints or seed roster.

## Limits and strongest counterexample

The network can still memorize separate behaviours for one-hop and practised
two-hop questions. An immutable question path and differentiable attention do
not enforce reuse of the same attribute operation after a link traversal. It may
therefore reach 100% on familiar questions and still fail changed-link pairs or
the held-out relation. That result rejects this recipe as a solution to the
reasoning blocker, even if all software checks pass.

This is a new architecture combining several changes, not an ablation isolating
their individual effects. Full-token access gives up sparse card-read efficiency.
Line order is deliberately ignored, so temporal updates require further design.
It remains a fixed-vocabulary single-token toy, not an open-domain language model.
The new worlds use the same grammar; passing would demonstrate narrow relational
transfer, not general intelligence, longer-chain reasoning, or a scaling law.

Historical controls have different losses and hardware. Equal example exposure
is not equal spent FLOPs; actual counts and time are reported. Soft token reading
also changes the original hard-card inference contract. No default promotion,
official G_pair admission, or reliability certificate is implied.
