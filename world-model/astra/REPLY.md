### Diagnosis

**Shown — main build:** The weighted WAIT loss fell from 0.022 to 0.001 on internal ticks. There is no real-transition result.  
**Shown — toys only:** The word-room planning successes and the bait-grid pilot’s failed model-learning gate were on separate networks.  
**Untested risk:** If the slow-row mean ignores the frame and stays constant, a zero predicted change is perfect. Stop-gradient blocks a gradient on this update; it does not keep the target informative across updates. Sharing is not itself the defect.  
**Suggested measurement:** Track the slow-mean covariance spectrum on fixed held-out histories, its response to different real next images at matched history and clock, and latent error versus copying the current mean.

### Candidates

| Candidate | Strongest case for / against — **untested** | Rule call and decision — **suggested** |
|---|---|---|
| 1. Real next latent | Could predict relevant state without reconstructing nuisance pixels. But the target can discard the action’s effect; even an accurate action-row summary need not constrain the board fed back. | Legal for one-step real-pair training; feeding predictions back is for evaluation or frozen-policy practice, not model training. **Drop as sole anchor.** |
| 2. Observation decoder | A real next picture gives the *returned board* an external standard. Pixel MSE can still reward blurry, action-independent averages. | Legal. **Keep; test first**, without an auxiliary latent loss. |
| 3. Separate recurrent model | Stochastic memory could represent hidden state and alternative futures. A second representation costs training and must remain usable by the thinking board. | **Drop:** separation breaks the keep-sharing rule today. Reconsider only with repeated matched-data, matched-budget evidence that tying the trunks loses grounded prediction while untying them preserves it. |
| 4. Frozen embedding | Stable targets, cheap if cached. A global embedding may recognize the same scene equally well before and after a consequential move. | Legal. **Keep in reserve** if features demonstrably preserve local action effects better than pooled pixels. |

### One laptop test — one fit, with the protocol locked before collection

**Suggested free CPU check:** In the proposed survival environment, replay 24 short prefixes on throwaway seeds. From identical pre-action pictures, actually execute move versus noop; repeat noop to measure replay noise. Use RGB area-pooled to \(16\times16\), scaled to \([0,1]\). Require move–noop next-picture MSE to exceed noop–noop MSE by \(10^{-4}\) on at least 8 prefixes. Otherwise stop before training: the capture path has not demonstrated a visible, correctly timed action effect.

**Suggested single change:** In the real-transition harness, replace summary matching with **one affine decoder from the mean slow rows of the predicted residual board to the real next pooled picture**. Do not decode the disposable action row. Use the same observe/imagine trunk implementation and \(64\times256\) board, 24 slow rows; laptop fixture: two width-64 blocks, four width-128 feedforward experts, top-2. This tests the shared design, not production-scale performance.

**Suggested wiring:** From the initial board, read two consecutive real pictures ending at \(t\), one observation tick each, as positioned, read-only pixel patches. Run imagine once with recorded \(a_t\), unit clock and empty sensory context. Backpropagate next-picture MSE through decoder, imagine and observation ticks; discard the imagined board afterward. What is learned is how to retain visual information and update it given an action. No other loss, policy or privileged input.

**Suggested data and fit:** Record 128 transitions per world: train seeds 0–31 (4,096 transitions), held-out seeds 1000–1015 (2,048). Sample actions independently: 80% uniform over moves, 20% uniform over remaining public actions. Restart on termination without splicing episodes. Cache pooled pictures; run 512 Adam updates, learning rate \(3\times10^{-4}\), batch 16 uniform valid training windows, initialization seed 42. Score only the final checkpoint.

**Untested time budget:** Five minutes install/preflight, five record, fifteen train, four batched scoring: 29 minutes inclusive. This requires about 21 recorded steps/s and at most 1.76 s/update during fitting. Enforce the wall cutoff; timeout is a budget miss, not evidence against sharing.

**Suggested locked score:** At every held-out origin with the two-frame history and five remaining real steps, initialize as in training. Roll the board forward using logged actions only: **no subsequent real picture, context or board refresh**. Include blocked moves and unchanged frames.

- **Prediction:** At \(k=1,3,5\), divide forecast pixel MSE by the MSE of displaying picture \(t\) unchanged until \(t+k\). Average errors within world, then across worlds, *before* division. Require ratios \(R_k\le(0.80,0.90,0.95)\), respectively; baseline MSE below \(10^{-5}\) makes that horizon uninformative.
- **Action use:** Permute whole five-action strings among origins within each world (fixed shuffle seed 43); change nothing else. Require \(R^{\rm shuffled}-R\ge0.10\) at one step and \(\ge0.05\) at five, with positive paired gaps in at least 12/16 worlds at each. An action-blind forecast cannot earn that gap.
- **Collapse:** Within each first-action group, sum pixelwise variances across origins; average groups by frequency. Require predicted one-step variance to be 0.25–2 times its real counterpart. A constant picture per action fails even though the targets themselves cannot drift.

**Untested odds, conditional on a valid completed run:** **PASS 20%** (all gates), **PARTIAL 40%** (all one-step gates, but not all rollout gates), **WRONG 40%** (otherwise). In particular, harmless one-step shuffling despite visible action effects would refute this loss as *sufficient at this budget*.

**Suggested next decision:** On PASS, freeze trunk, decoder and action codebook. Give an actor a real goal photo from five steps later in a recorded trajectory. From real training boards, practise five discrete moves in the frozen model to minimize terminal goal-photo error. Compare against an identically initialized goal-imitation actor spending the same update budget on real replay only. Require at least 10% lower **real** terminal goal-photo MSE on paired fresh-world starts; imagined improvement does not count.

**Suggested on a grounding miss:** No policy training. If only rollouts fail, next change just one thing: add returned-board consistency against the detached board reading the **real** next frame, retaining the pixel anchor. If one-step grounding fails, inspect saved forecasts and action-stratified errors before spending another run. Three locked misses close the idea.

**Untested dependencies / three missing facts:** Actual pixel versus encoder action-to-noise contrast (prefer 4 if only the encoder preserves the signal); necessary real history length (extend burn-in if two frames alias states); measured end-to-end M1 throughput. No candidate is shown to meet every mark. **Suggested:** If compute alone binds, loosen laptop-first by using the available GPU slot, not the grounding rules or score thresholds.

### For the owner

**Shown — main build:** So far your model has been graded on what its own thinking did next, not what a game did next. **Untested risk:** It could get a good grade by keeping its notes almost unchanged. **Suggested:** Keep one thinking system and teach it to draw a small picture of what follows a real move. In new worlds it should beat leaving the old picture on screen, even five moves ahead, and mixing up the moves should hurt. Only then let it practise in its frozen predictions, and judge that practice by what it actually does in the game.