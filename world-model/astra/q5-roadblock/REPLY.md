**Suggested — decision.** Keep the last scored conv strike unspent. First check whether a *fixed checkpoint* gets a fixed wall score. If that check is clean, use the third and last sampler pilot for **one change: keep pilot 1’s prioritised draws, but importance-correct the loss**. That tests whether seeing rare events more often helps without making those events count for more than they should.

### 1. What is actually stuck?

**Shown — shared board only.** The board could *store* a frame: ridge got 0.062 where the trained decoder got 0.140. That did not translate into forecasting. Rank 3 got k1 E/B 0.953 against its 0.4738 stop threshold, pooled shuffle 1.152 against 1.25, and called every open move blocked. It hit its own stop rule. The board forecasting line is closed; these are not conv strikes.

**Shown — conv only.** Rank 7 beat shift-or-stay at k1 and k3, passed the dev wall mark, and had pooled k1 shuffle ratios above 5. Its record re-encode k5 scores straddled the 0.4977 bar: 0.4953 and 0.5016. Rank 6’s successful *k5 re-score* used a rollout choice examined after seeing dev; it was not a new overall PASS.

**Suggested.** The conv model has learned useful action-conditioned movement. The shuffle result is not evidence that it predicts what chopping or placing will do. Nor is k5 solved: a change that fixes the rare actions still has to preserve rollout accuracy on **both** seeds.

**Shown — real rare-event gap.** Rank 7 predicts very little change for “do” and the place pool. Wake windows are absent from about 77% of uniform batches; awake interactions also have much weaker measured gradients than moves. Chop/place fit was poor even on train, while a pixel ridge probe found predictive signal for awake “do.” Prioritisation raised “do” std and the wake gap, but non-wake “do” R² **fell**, from −0.031 to −0.493 and from −0.035 to −0.165 in the reported comparison.

**Shown — measurement limitation.** Write \(p_i=e_i/\sum_j e_j\), so Kish \(n_{\rm eff}=1/\sum_i p_i^2\). One window with 86.5% of action 9’s energy implies \(n_{\rm eff}\le 1/0.865^2=1.34\). Six windows sharing 55% of “do” energy imply \(n_{\rm eff}\le 6/0.55^2=19.8\), despite 733 windows. There were **zero real furnace placements** in the dev action-9 sample.

**Suggested.** Missing a wake is a real, expensive *frame prediction error*. It is not evidence about predicting a furnace placement that never occurred. Likewise, std measures how much the prediction moves, not whether it moves on the right occasion. With ambiguous inputs, a squared-error predictor can reasonably predict less variation than it observes. The awake R² result is the reason not to declare victory merely by getting std above 0.25.

**Shown — wall.** The paired pilot-1 wall deltas were +0.0083 and +0.0118; pilot 2’s contemporaneous deltas were +0.0134 and −0.0136. Move share **rose** in the logged sampling comparison. On the pilot wall set, five extra errors among the 500 blocked moves alone add 0.005 to mean_err. Pilot 2 missed under either reading of its gate, though on different seeds.

**Suggested.** There is a credible wall regression, but neither “it took examples away from moves” nor “it’s just noise” is established. Prioritisation could change *which* move examples dominate learning. The 0.050–0.071 range of uniform scores is **not** an uncertainty interval for a *paired difference*, and a cross-build rerun discrepancy is not a measurement of random noise. The dev 0.0659 absolute bar is not calibrated on the eight pilot worlds. No past verdict changes: **conv 2/3; Rel-PER pilots 2/3**.

### 2. Five-minute interlock, before another try

**Untested — do this on pilot artifacts only, in this order.**

1. **Replay the score without the model.** Freeze the ordered window IDs, preprocessed inputs, true wall labels, classifier version, and saved predictions from one uniform checkpoint. Score those predictions twice in fresh processes. Compare the **per-window open/blocked calls and integer confusion counts**, not rounded mean_err. A difference localises a problem downstream of prediction.
2. **Replay the model without training.** Reload the *same checkpoint including buffers*, in evaluation mode, twice on the same device/build. Hash the predictions and compare wall calls by ID. If available, cross-score the two historical checkpoints on one frozen evaluator, and the same checkpoint on both evaluator builds. A tiny tensor difference with identical wall calls is not an explanation for the historical wall gap.
3. **Only then replay training briefly.** Twice run the first **20 real uniform pilot minibatches** from the same initial state on the actual training backend. Compare initial weights, sampled IDs, batch tensors, losses, gradients and updated-weight hashes at each step. Different IDs point to data/RNG handling; identical batches and weights followed by different updates point to the training computation. Compare *within* a build before calling a difference *between* builds nondeterminism.

**Suggested — decision rule.** Require identical fixed-checkpoint wall decisions and counts, and a matching same-build short training trace, before trusting a new paired pilot. If they differ, stop and localise the first difference. If they agree, that clears a short reproducibility check; it does **not** prove step 3,000 reproducible. If the old gap cannot be reconstructed, do not borrow controls from an unmatched build. Pin one scorer function that both **prints and enforces** the paired limits.

### 3. The one training change

**Untested — importance-corrected Rel-PER, not a sweep.** Use the Rank 7 model and record re-encode rollout unchanged. Use pilot 1’s priority implementation unchanged: \(u=0.5\), exponent 0.7, cap 20, denominator offset \(10^{-4}\), same EMA and initialisation. For each draw with replacement record its actual probability \(p_j\) **at draw time**. The sole change from pilot 1 is the minibatch loss:
\[
L_{\rm batch}=\frac{1}{64}\sum_{j\ {\rm drawn}}
      \underbrace{\frac{1}{N p_j}}_{\text{detached weight}}\,L_j ,
\]
where \(L_j\) is the **whole existing k1 per-pair loss**. No weight clipping, batch renormalisation, action exceptions, new inputs or rollout gradients.

**Shown — algebra, conditional on that sampling law.** Since \(p_j\ge 0.5/N\), the multiplier is at most 2. For additive per-pair losses, at fixed weights and priority table,
\[
\sum_j p_j\,\frac{\nabla L_j}{Np_j}=\frac1N\sum_j\nabla L_j .
\]
Thus the expected raw gradient targets the uniform training loss, while the draws are still prioritised.

**Suggested — why this bet.** This separates **frequency of practice** from **bias in the objective**. It might give a steadier learning signal for wakes without teaching the model that surprising outcomes are more common than they are. It does *not* guarantee lower gradient variance, an unchanged AdamW trajectory, or better walls. Its main weakness is testable: if the rare actions need more **mean gradient**, not merely more frequent informative draws, full correction may lose the pilot’s “do” gain.

### 4. Prospective gate card

**Untested — scope.** Pin this card before training. Use seeds **7 and 8**, 72 pilot training worlds and the same eight pilot evaluation worlds. Pair each candidate with the **same seed’s uniform arm on the locked build and device**, not a choice between historical arms. Keep batch 64, AdamW settings and **3,000 steps per arm**. Both seeds must clear the pilot. This card is a screen for a *new* candidate, not a way to promote pilot 1 or 2.

| Prospective pilot mark | Pinned decision |
|---|---|
| **Untested — frame accuracy** | For each seed, candidate minus matched uniform E/B must be **≤+0.005 at k1** and **≤+0.008 at k3**. Publish open-loop k5 too; no intermediate real frames. |
| **Untested — wall non-inferiority** | Let \(D_s=\tfrac12(\Delta FB_s+\Delta FO_s)\), candidate minus uniform on identical windows. Require both observed \(D_s\le+0.005\). Also resample **whole worlds** with replacement 10,000 times, RNG seed 7001, using the same resample for both arms and both seeds. Recompute FB and FO from summed counts each time. Require the **90th percentile of \(\max(D_7^*,D_8^*)\le+0.005\)**. Publish both component rates. An interval crossing the allowance is **not clearance**; a one-sided lower bound above it is affirmative evidence of harm. |
| **Untested — “do” and waking** | All-window “do” std ratio **[0.30, 2]** on both seeds, with the support test below. Keep the normal-HUD wake contrast separate, pooled across actions: require at least **6 distinct eligible wakes in ≥3 worlds**, positive real gap, and candidate gap **≥ max(3 × matched uniform gap, 0.25 × real gap)**. Publish leave-one-wake-out gaps. The real-gap floor prevents “three times almost zero” from sufficing. |
| **Untested — awake rare-action amplitude** | Score awake-at-both-ends pairs by first action, using state **only in the scorer**. Keep the activity floor \(n\ge20,\ \sigma_{\rm real}\ge0.02\). For an individual std ruling require **both** \(n_{\rm eff}\ge10\) and **≥3 effective worlds**, the latter computed by the same Kish formula on world energy totals. No \(n\ge200\) bypass. Require **[0.25, 2]** individually where supported; pool the remaining active groups and apply the same support and ratio bounds to an active pool. Retain the **25% energy-dominance veto** and the all-window frequency-weighted **[0.25, 2]** gate. An active required pool lacking support is **insufficient evidence: no promotion**, not a demonstrated collapse. An inactive or zero-positive placement group is *not certified*. |
| **Untested — guard against fake variation** | On identical awake non-wake “do” windows require \(R^2_{\rm candidate}\ge R^2_{\rm uniform}-0.02\) on each seed, using next-frame **change** as the target. This is a non-regression screen; do not claim useful awake interaction prediction from a still-negative R². |

**Suggested.** Check all truth-only support conditions **before** spending the training budget. Nine wake windows evaluated on two seeds are still nine wake windows. The world bootstrap is a small-sample precision check conditional on these training seeds, not a precise population confidence statement. If the split cannot resolve a material tail or a +0.005 wall difference, the honest outcome is “not enough evidence,” not a wider tolerance chosen after seeing the result.

**Untested — budget.** Reserve at most 5 minutes for the audit and 3 for scoring/aggregation, leaving 22 for updates on one device. With two verified, exactly matched archived uniform controls, the two candidate runs need measured throughput above **4.55 updates/s**; with four fresh runs, above **9.1 updates/s**. Time the real path first. If it cannot fit, do not start a shortened or one-seed substitute and call it the pinned test.

**Suggested — falsifier and odds.** A clean return to “do” std **<0.30**, loss of the wake mark, or another wall miss disproves the *operational bet* that this estimator delivers both gains together at this budget. Any pilot non-pass blocks Rank 8; a third clean sampler miss retires Rel-PER, without spending a conv strike. Conditional on a clean audit and adequate support, my odds are **25% for a two-seed pilot green**, then **25% for a two-seed dev PASS conditional on green**: roughly **6% for both**. The unresolved place pool and marginal k5 are why the second number is low.

**Untested — only if earned.** On dev I would keep the last scored strike under **Ruler C as filed**, not replace its rare bucket with the easier interpretation of a pilot result. Require both seeds to beat **0.2853 / 0.4068 / 0.4977** strictly, wall **mean ≤0.0659, FB ≤0.0207, FO ≤0.1552**, the original moved-window shuffle marks (**1.25 at k1, 1.10 at k5 in ≥12/16 worlds**, pooled k1 ≥1.25), ceiling ≤0.70, and the original pcs and full C std gates. Keep PARTIAL/VARIANT/LINE accounting unchanged. Only a two-seed dev PASS licenses the single sealed opening.

### 5. Substrate decision

**Suggested.** Keep 16×16 conv as a candidate **short-horizon subsystem**, not yet as an imagination a policy can trust. A board failure does not condemn it; a conv frame-score PASS would not validate policy practice. Discrete tokens have no demonstrated advantage here, and changing the output representation alone does not supply missing observations or placement examples.

**Untested — what would settle usefulness.** After dev and sealed success, test real-game transfer at fixed real-data and policy-update budgets: policy practice with the model versus a compute-matched real-data-only control. A concrete later bar would be **≥0.5 additional distinct achievements per 350-step real episode**, over 16 fresh paired worlds and three policy seeds, with a paired one-sided 90% lower bound above zero. That would be evidence to keep the substrate for this use. An upper bound below +0.5 would rule out that size of benefit in this setup, even with good pixel scores. This is a downstream criterion, not a second change in the current wave.

### Five-line summary
**Shown** — The old shared model could remember a picture but could not forecast the next one well.  
**Shown** — The newer model handles many moves, but a few wake-ups swing its rare-action grade.  
**Suggested** — Check that the same saved model gets the same wall score before trusting a tiny difference.  
**Untested** — Show the model hard moments more often, but count each one less when updating it.  
**Suggested** — Save the last official try for a clear win; the real prize is a player that does better in the actual game.