1. Pick A: harden before gating.

It is the cleanest test of the failure you actually observed. The exhaustive 729-chain control says the correct discrete chain is strongly identifiable; the question is whether the soft optimizer has already put the correct option at the top of each stage but leaves probability mass spread enough that the resulting mixture falls below the 0.9 answer threshold.

Do not change the gate yet. C weakens the safety mechanism before establishing that the gate is the problem. B spends much more compute without diagnosing why. D addresses genuinely wrong optimization basins, which should come next if A fails.

If A is right, the signature is very specific:

- At 2 wrong, hardened OOF scores should cluster at 0.90, and installs should rise from 10/15 to at least the old 12/15 target, plausibly 15/15.
- At 4 wrong, correct hardened chains give exactly 0.80, so installs should rise substantially above 2/15.
- The cells currently scoring 0.65 should often jump directly to 0.90, rather than gradually improving.

If hardening still gives ~0.65/0.15 in the failed cells, the argmax chains themselves are wrong. Then A has falsified the “right discrete chain hidden inside a soft mixture” explanation, and D would be my next experiment.

2. The main safety failure is equivalence on the 20 teaching episodes.

A wrong hard chain could happen to produce exactly the same outputs as the true chain on those starts, pass 0.80, agree with the refit, and then differ elsewhere in the village. Hardening makes this slightly more important because you are committing directly to one discrete program.

For this synthetic experiment, the cheapest safety audit is extremely strong: for every would-install candidate, evaluate it on all 60 possible start people and compare its outputs with the true word. This is only 60 executions, not 729-chain enumeration.

Pre-register:

“Any candidate that passes the install gate but differs from the true word on even 1/60 starts counts as a wrong install and fails the experiment.”

Keep this as an evaluation-only audit, not part of selection, so A remains the only experimental change. In a real setting without known ground truth, the analogue would be a sealed clean probe set.

3. Keep 0.80 and 0.90 unchanged for Experiment 46.

With two corrupted labels, a correct hard chain gets 18/20 = 0.90 OOF match, so there is comfortable margin over 0.80. Its refit-versus-OOF prediction agreement should normally be 20/20, because that comparison is between predictions, not against noisy labels.

There are two traps.

First, apply 0.80 to the pooled 20 OOF predictions, not separately to each five-example fold. If both wrong labels land in one fold, even a perfect chain scores only 3/5 = 0.60 in that fold. That happens for 4\*C(5,2)/C(20,2) = 40/190 ≈ 21% of placements.

Second, four wrong labels are exactly on the boundary: 16/20 = 0.80. One additional clean-example mistake makes it 15/20 = 0.75. Therefore 4-wrong performance will be deliberately brittle under the existing gate. That is useful information; don't move the threshold during Experiment 46.

4. I would pre-register two independent batches: the current five seeds × three words, then five new fixed seeds × the same three words. Judge each 15-cell batch separately rather than pooling them.

Use these marks:

- 0 wrong: 15/15 installs.
- 2 wrong: at least 12/15 installs. Keep the previously registered target instead of moving the goalposts.
- 4 wrong: at least 8/15 installs.
- 20 wrong: 0/15 installs.

Require those same four marks again on the fresh-seed confirmation batch.

Over both batches, require zero semantically wrong installs out of all 120 cells under the 60-start audit. One wrong install fails Experiment 46 regardless of the aggregate install rate.

I would also record, without making it another pass criterion, how often each fold's hardened argmax chain equals the true chain. That tells you immediately whether the remaining failures are optimization failures or gate failures.

5. A still makes sense with 100+ skills and four stages. Hardening does not enumerate K^4 programs. You simply take one argmax at each stage: roughly O(4K) to choose the four skills, then execute four matrices.

The first thing likely to break is the soft relaxation that comes before hardening. With 100+ choices at each of four stages, the optimizer can distribute mass among many skills, and a useful discrete skill may never become the top-1 option. Worse, the best soft mixture need not have a good stagewise-argmax discrete counterpart. Credit assignment through four large categorical mixtures also becomes much harder.

So A scales computationally; the soft router may not. If Experiment 46 shows that hardened argmaxes themselves are often wrong, that is the evidence to investigate sparse/top-k or explicitly discrete routing next—not to relax the safety gate.
