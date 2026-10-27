# Wider practice registration

Written 2026-09-27T22:10:26Z (clock recorded with `date -u`).
This recipe is a proposal until CANDIDATE-SEAL.json hashes it. No maze data is used.

## Candidate qualification

The candidate list and generator definitions are in claude_patch_data.py.
Before training, save 300 fresh development puzzles per kind, using seed
92731000 plus the kind's list index. Required panels are four-digit sums and
five-by-five Latin grids with the same symbol legend as xfer-1.
Exclude every development input fingerprint from training. Also keep a distinct
300-puzzle verification panel per kind (seed 92732000 plus index), excluded from
training and unused for qualification selection.

Train an independent ordinary loop (seed 927301) for exactly 18,000 steps,
batch 64, uniform random choice among candidate kinds. Each batch has one kind
and one size. AdamW lr 0.001, betas (0.9,0.95), decay 0.1; 200-step linear
warmup then cosine to zero; gradient clip 1.0. Use 1–16 rounds, with gradient
and deep answer loss through the last uniformly sampled 1–min(6,rounds) rounds.
Stop loss is 0.5 times binary cross entropy against exact answer correctness.
Evaluate using the existing v2 halt rule, capped at 48 rounds: from round three,
halt if p>0.5 and all predicted tokens equal those at the previous two rounds;
otherwise use round 48. Also save forced-depth counts at 4,8,16,32,48.

Drop extras below 270 of 300; require sums and grids at 285 of 300. At least
four extras must qualify. No extensions or easier replacement panels after
seeing results. Failure is a qualification failure, not a negative maze result.
Seal the resulting list and raw qualification counts before arm training.

## Independent arms

Seeds 927401 and 927402. Every arm uses the identical qualified kinds, example
stream, development exclusions, and source optimizer schedule above, for 18,000
supervised steps. Arms: patch, ordinary loop, loop with learning-to-learn, plain.
The ordinary loop is an additional reference; Test A's paired comparator is the
loop with learning-to-learn. Each arm has its own fresh weights; the qualification
pilot is never reused. The plain arm also receives gradient-based episode training.

Following supervised practice, run 2,000 episodes with a fresh outer AdamW using
the same settings and a separate 200-step warmup/cosine schedule. Sample two
different practice kinds A and B uniformly. Four support examples arrive in order:
two of A, then two of B. Each support is different. After those supports, the
objective is mean answer/stop loss on eight different B queries plus the same
loss on eight different A queries (retention coefficient 1). Query/support inputs
are disjoint. Generators may know kinds; nets receive tokens and slot flags only.

For the patch, write after each support correction. Ordinary parameters are
unchanged during all four writes. Detach the patch before the last two writes;
differentiate those two writes through subsequent query and retention losses.
Only query/retention losses train the writer. Carry the detached patch across
episodes and kind changes. Do not reset it at an A/B transition.

For loop-with-learning-to-learn and plain, the same support schedule performs
functional SGD updates (lr 0.01, no inner momentum or decay). Detach the first
two updates' history while retaining the identity derivative to the outer
parameters; differentiate through the last two updates. These temporary inner
weights restart from current outer parameters at each training episode, as in
MAML. This reset is an episode training boundary, not an evaluation kind switch.
For the ordinary loop reference, train on the same support and query examples
with a mean supervised loss; this reference does not replace the required
learning-to-learn control. Disclose its different loss and compute.

Both reasoning-round truncation and stop loss stay as in supervised practice.
Source-trained evaluation uses the patch retained from training; old/new query
ordering never triggers a patch reset. Query targets are used only by the scorer.

## Gates and race boundary

Evaluate each practised arm on the saved verification panels. Required marks are
285 of 300 for sums/grids and 270 of 300 for extras. The patch must be within
nine of 300 of both its paired ordinary loop and learning-to-learn loop on each kind. Save raw per-item
predictions, stop rounds, correctness and forced-depth predictions for recount.
Select fixed comparison depth on the development panels only.
Repeat the construction checks on each final trained patch checkpoint before
declaring readiness. These checks use a throwaway patch branch and apply no
optimizer update to the checkpoint. Report actual batch-one halt latency on
the first 30 verification inputs per kind, without passing answers to inference.

No race execution is authorized by this registration alone: obtain the test
chat's sealed RACE-PASSMARKS from main and commit the required wider-practice
addendum first. The requested default ladder is writer-only at k=1,4,16,64,
ordinary learning plus writer for stream rungs, and fixed replay sleep; those
details must be reconciled with the actual sealed protocol, without changing
its bars. Sleep removal and timing rows remain untested until then.
