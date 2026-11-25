I'm working out the reconcile step: the head reads next_rows and is trained with only the k=1 loss. Since gradients pass through out_proj and the trunk, that should still train next_rows, though how the decoder reads the slow rows versus the attention head is the part I still need to settle.

I'm checking whether k=1 training alone keeps next_rows usable as input: the decoder only constrains the mean of the slow rows, so the remaining row dimensions can drift, which makes PARTIAL at k=3 or 5 the likely result. A row-wise consistency loss against the detached real next board would train on real transitions only and pull the fed-back rows back toward the real-board manifold.

I'm looking at whether next_rows should be the object the consistency loss constrains: matching its rows against the detached real next board would train on real transitions only and keep the fed-back rows in-distribution for the k>1 rollouts. I also need to note that sensory context stays frozen at frame t during open-loop rollouts, and that the copy baseline could let the trunk simply pass context through, which is why I'd want delta targets and shuffle checks.

I'm now checking the pixel-based free check: the player is centered and the view scrolls, so an unblocked move should shift the whole view and pass easily, while a noop only moves other creatures. I'm leaning toward pixels as the primary check, predicting deltas, with one precedence rule so the free check makes a single decision instead of two gates.

I'm checking how the stochastic and no-op-heavy action mix affects the copy baseline, since it dominates on steps where nothing moves. I'm also fixing the blend coefficient on training data rather than held-out, and shuffling actions within matched world and time buckets to keep the action marginals intact.

I'm weighing how the decoder's structure affects the collapse check: a mean-pooled affine readout from the 256-dim slow rows could carry the full 16x16 pixel delta, so the bottleneck itself is not the constraint I need to worry about.

I'm weighing whether the decoder should be trained on real boards so the imagined ones stay decodable, and how the real-board decode error sets a ceiling for the rollout checks.

I'm checking the size budget now: at 3M parameters on a laptop CPU, a batch of 64 over roughly 65 tokens plus context rows should come out to tens of milliseconds per step, so 1,500 steps looks comfortable.

I'm estimating the per-step cost from the model size and batch, which comes out to a few seconds per step on a laptop CPU, so 1,500 steps could take close to an hour. The recurrent rollout over episodes is likely the dominant cost, so I'd time about 20 steps first and then pick the step count that fits the budget.

I'm checking whether 1,500 steps is enough for the zero-init delta head to beat the copy baseline at k=1, since it starts at exactly 1.0 and has to learn view shifts from frozen features. I'll time about 20 steps first to confirm the budget.

I'm working through the pass/fail marks for the rollout check: the first one sets the ratio against the stronger of copy and train-fit blend on held-out data, at 0.80 for k=1, 0.90 for k=3, and 0.95 for k=5, looser at the longer horizons since the model was only trained on k=1. I'm also weighing whether the shuffle check should need the error to rise to at least 1.25x.

I'm weighing the odds for the three checks: the alignment loss might help k=3 and k=5, but without it drift is likely, so I'd put PASS around 25%, PARTIAL around 45%, and WRONG around 30%. WRONG covers k=1 failing to beat copy by 20% in 1,500 steps, or the model ignoring the action, and I'm keeping in mind that random-action Crafter has many no-op and blocked moves.

I'm estimating the odds for each outcome: PASS around 20%, PARTIAL around 45%, and WRONG around 35%, which are rough judgment calls rather than measured numbers. I'm also checking what single result would show the plan is off: if k=1 clears its mark but the shuffled-action gap stays at or below about 1.05x, the model would be beating copy without really using the action.

I'm now weighing which result would actually sink the plan: if k=1 clears its mark but the shuffled-action gap stays near 1.0x, the model is beating copy without really using the action, so the gain comes from context alone. I'm also considering a failed real-board decode ceiling, which would show the board itself doesn't carry the frame, but the decisive check in the plan as drafted is whether k=3 still holds when k=1 passes.

I'm settling on a single decisive check: the k=1 ratio has to clear its mark, but the shuffled-action error should still be at least 1.05x copy on moved windows. If shuffling the actions barely changes the error, the model is beating copy on context alone rather than using the action. Training on real targets with imagined inputs would be the escalation step, and whether that breaks the rules is the owner's call; the alignment loss is the safer intermediate step.

I'm noting that the context at k>1 has to stay frame-t only, or the rollout would leak future information. I also need the baseline blend fit on training data, and the "AND" condition in the check still needs tightening before I write it up within the word budget.

