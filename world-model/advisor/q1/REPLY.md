**1) Flaws in the reconcile**

- **k=1 through a head doesn't make `next_rows` a valid input.** The loss only constrains what the head reads, so the fed-back board can drift off the real-board manifold and PARTIAL is nearly built in. Rule-safe fix: add a row-wise loss, `next_rows` vs the detached real next board. It is still k=1 and still uses real transitions only.
- **Train the head on real boards too.** Real-board decode error gives a ceiling that separates "the board lacks the frame" from "the dynamics are bad".
- **Context leak.** For k>1, the sensory context must stay frozen at frame t.
- **The "AND" target check is ambiguous.** Use one precedence rule: pixels 16x16 by default (Crafter moves scroll the whole view), encoder rows only if the encoder passes its sensitivity check. Predict the change, with a zero-init head.
- **B's k=3/5 marks assume unrolled training.** Against the best-of-copy-and-blend baseline they are too strict for k=1-only training.
- **Baseline and reporting.** Fit the blend coefficient on train data, and report moved windows separately, since most of the 17 actions are usually no-ops.

**2) Size**

20k/5k is fine, and data is not the bottleneck. Split by world seed and keep at least 16 held-out worlds. 1,500 steps at batch 64 is about 5 epochs, which is reasonable. I can't verify the wall-clock: time 20 steps first, cap training at about 15 minutes, and cut steps rather than data.

**3) Marks (held-out)**

| Check | Mark |
|---|---|
| (a) Error vs best of (copy, blend) | k=1 ≤ 0.80, k=3 ≤ 0.90, k=5 ≤ 0.95 |
| (a) Real-board ceiling | ≤ 0.70 |
| (b) Shuffled-action error, moved windows | ≥ 1.25x at k=1, ≥ 1.10x at k=5, in ≥ 12/16 worlds; shuffle within world, preserving action marginals |
| (c) Predicted-change std, per action group | 0.25–2x real |
| (c) PCs for 90% variance | ≥ half the real-change count (not an absolute 8) |

Verdicts:
- **PASS:** all marks met.
- **PARTIAL:** the k=1 marks, k=1 shuffle and collapse checks pass, but k=3/5 fail.
- **WRONG:** anything else.

Odds (my judgment, not calibrated): PASS 20%, PARTIAL 45%, WRONG 35%.

On PARTIAL, go to the owner about unrolled training only if the row-alignment loss was already in and it still drifted.

**4) The result that proves the plan wrong**

The k=1 mark is met but shuffled-action error is under 1.05x on moved windows. That means the model beats copy from context and mean-reversion alone, without using the action. The grounding signal then isn't testing action-conditional dynamics, and more k, data or unrolling won't fix it.

The second killer is a pre-gate: if the real-board ceiling is above 0.95, the board doesn't hold the frame and imagine training is moot.