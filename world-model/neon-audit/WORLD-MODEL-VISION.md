# Premonition World Model — Unified Conceptual Blueprint & Toy Proof Ladder

**Date:** 2026-11-24  
**Status:** Complete conceptual blueprint locked with Ben (Parts A, B, C, D) and stress-tested by three independent max-effort reviews: **Astra Max** (Parts A/B, Part C, and Part D Ladder) and **Claude Fable 5.2 Max** (Part C via API, `$3.07`, 5 web searches).  
**Rule:** Everything below is **100% learned** (zero hand-coded game rules, zero OS/memory cheats). Toy results (`P7toy`, Crafter) stay strictly separate from ~50M / ~500M and 3D Minecraft claims.

---

## 1. The Big Picture: One Unified World-Modeling Mind

Premonition does **not** treat its world model as a standalone blurry video generator crammed into its 64-row thought workspace. Instead, **six core design principles** lock together into one coherent Two-Speed Living Mind:

1. **Workspace Separation (The Central Desk):**
   - The Big 4-Wide MoE Brain’s ~64-row persistent workspace holds **separate lanes** for facts/memory, conversation/intent, active plans, and a **compact summary of the most relevant/surprising world objects** (top 8–16 items, reserving slots for `Who` and `Avoid` queries). It never drowns in raw 20 Hz pixels.
2. **Multi-Modal Meaning + Grounded Senses (Never Pixels-Only, Never Meaning-Only):**
   - One shared compact world state predicts **both** high-level **meaning/events** (danger, inventory, goal progress, what just happened) **and** grounded sensory signals:
     - **Visuals:** Weighted on **both changed regions AND critical stationary details** (a stationary void edge, heart icon, or decimal point in a price matters as much as moving objects!).
     - **Audio:** Compressed audio tokens + onset timing (footsteps, creeper hiss behind you, bow draw, fireball whoosh, Ben's voice tone).
     - **Text + Meaning:** Predicts underlying meaning first, plus exact text characters where literal text matters (chat, code, scoreboards, UI labels).
   - **Fast Dreaming Rule:** During branching look-ahead, the model steps purely in **compact state space** (never painting 100,000+ RGB pixels per branch!). Visual decoding runs only during training (anchoring state to reality) and on demand for the live **Tesla Reality View**.
3. **The Brain ↔ Hands Contract ("5W+H Command Frame"):**
   - The Big Brain sends Fast Hands (`≥20 Hz`, target `≤4 ms/tick`) one interruptible learned command packet — **never** a single blurry goal vector and **never** brittle raw keystrokes:
     - **WHO (`Target Query`):** Learned appearance/meaning query (+ optional anchor) so Fast Hands re-finds the target every tick even after a camera turn or page scroll, and cleanly reports *"not visible!"*
     - **WHAT (`Desired Change` + exact text ref):** What outcome to produce — plus, when typing, a **verbatim character-string reference + acknowledged offset** (never asking a continuous embedding to spell a filename!).
     - **WHERE (`Anchor + Avoid Query`):** Optional spatial zone plus what *not* to touch (*"avoid left void edge / fireball / Delete button"*).
     - **WHEN (`Expiry / Tempo`):** Target horizon or trigger condition.
     - **HOW (`Action-Family Bias + Caution`):** Style and safety bias.
   - **Upward Report (Hands → Brain, once per Brain tick, interrupting early only on target loss or imminent danger):** Command ID, elapsed time, order-sensitive summary of **inputs actually sent**, and **observed progress/change with confidence** (*"click sent"* and *"dialog opened"* are strictly separate facts!).
   - **Mandatory Contract Unit Test ("Same-Pixels Test"):** Clone identical screen **and Hands memory**, mirror target positions, flip *only* `Who` / `Avoid` (or `"hover"` vs. `"activate"`), and require both complete routes correct in `≥ 90%` of held-out pairs.
4. **Two-Speed World Model ("Fast Physics ↔ Slow Plot"):**
   - **Fast Physics (`0.1–1s`, paired with Fast Hands):** Predicts near-term physical/UI transitions from observed state, timed motor inputs, and `dt`.
   - **Slow Plot (`2–30s`, inside Big Brain using clock `dt`):** Jumps from event/milestone to event/milestone conditioned on the proposed command — avoiding the 5-tick = 0.25s trap!
   - **Grounded Link:** Link them by running a candidate command through `Hands → sampled controls → Fast Physics`, summarizing via the same real-observation event encoder, and grading **both** against *real observed events* where horizons overlap (agreement between two wrong predictors proves nothing; imagined states never enter the live workspace as facts!).
5. **Parallel Multiverse Engine (`Copy #0 = Live Anchor` + `Copies 1..K-1 = Batched Dream Lanes`):**
   - **Zero Zoning Out:** **Copy #0** stays glued to real life every Brain tick (fresh senses, Ben's voice / instant stop, facts). **Copies `1..K-1`** are **batched branch states sharing one set of weights** (`[B, K, R, D]`), advancing the parallel reality tree right alongside Copy #0 in the same GPU pass!
   - **Learning Intuition Prior + Wild-Card Exploration:** A fast `<1 ms` Intuition Prior prunes obvious blunders (e.g., hanging a queen or walking into the void = 0 realities), **while reserving a small slice for moves Intuition currently dislikes** so creative plays can still be discovered. Smarter search winners are distilled back into the Intuition Prior during Sleep (turning slow calculation into 1ms instinct!).
   - **Effort Slider = Wall-Clock Search Budget:** Sliding `Fast ↔ Deep` (and `AUTO` when uncertainty could change the decision) buys search time/compute — smoothly scaling **both** search depth (waves) and elastic `M × W` branching (`Calm/Solo → all moves W=1`; `Mild → ~3:1–4:1`; `High-Stakes PvP → ~1:1–2:1`; `Chess → many sequential waves`; `Idle → K=1`).
   - **Tournament Funnel + Live Reality Pruning:** Start wide on step 1, drop clear losers, concentrate slots on surviving top moves × enemy reactions; when the next real frame arrives, keep the matching subtree alive and prune misses.
   - **Two-Uncertainty Split (Sharp Futures vs. Dream Bullshit Detector):**
     - *World/Enemy Randomness:* Sampled **within one model** via discrete outcome tokens (`z_world`, top-`W` distinct outcomes weighted by predicted odds `p_w`) → sharp, un-blurred branches!
     - *Model Ignorance:* Measured by **independently bootstrapped prediction heads** after averaging over `z_world` dice inside each head → high disagreement fires the **Dream Bullshit Detector** (cuts off rollout trust and flags learning gaps).
   - **Risk-Aware Scoring (Caution Never Warps Reality):**
     $$\text{Score}(m) = (1 - c)\cdot \text{Avg}(m) + c\cdot \text{WorstCase}(m) - \beta\cdot \text{Disagreement}(m)$$
     Caution `c` sets acceptable downside only — it **never** alters the predicted odds of world outcomes!
6. **Decision-Relevant Surprise Heartbeat + Video & Two-Speed Game-Film Sleep:**
   - **Decision-Relevant Surprise (Noisy-TV Immune):** Prioritize prediction errors that could actually **change a decision or outcome** (not noisy background rain/shimmer!) to drive zoom, `AUTO` effort, and Sleep replay selection.
   - **Video Learning (Ben's Meaning → Sleep Skill Transfer):** Outside YouTube / desktop videos teach **passive physics, causal event meaning, and subgoals** (no compulsory discrete latent-action bottleneck; optional auxiliary only, never the motor vocabulary). Real timed self-play grounds Fast Hands motor execution.
   - **Two-Speed Game-Film Review in Sleep (Hypotheses, Never Blind Labels!):**
     - *Tactical Replay (2–5s back):* Finds the earliest cue/turning point before a failure.
     - *Macro Match Replay (minutes back):* Walks the Slow-Plot event timeline (~15–30 key decisions across the match), pairing failures with comparable real successes to discover minutes-earlier setup mistakes (e.g., skipping defense/armor early).
     - Counterfactual *"what if?"* dream alternatives are treated strictly as **hypotheses**, verified in safe repeatable trials or real matches before being consolidated alongside old skills (`≥ 95%` retention per established skill)!

---

## 2. Part C — Spatial Perception & Memory *(Locked — Unanimous Astra Max + Fable 5.2 Max Verdict)*

Both **Astra Max** and **Claude Fable 5.2 Max** independently reached the **exact same decision**: **do NOT build 3D Gaussian Splats yet.** Instead, build **Candidate 5 (Narrowed Thing-Slots + Patch Grid + Gaze Crop)**, keep plain **Candidate 1 (Patch Grid only)** as the control, and make any 3D upgrade earn its keep on the same ≤4 ms motor clock.

### Winning Base Architecture ("Candidate 5")
1. **Coarse Full-Screen 2D Patch Grid + Recurrent Memory + Cheap Motion Channel:**
   - Holds terrain, empty gaps/void (*"no floor" is not an object*), and page background across all three domains (Crafter, Minecraft, Mac desktop).
   - A lightweight full-frame motion channel catches tiny fast projectiles (arrows, fireballs).
2. **Gaze-Driven Sharp 2D Crop (Independent of the Mouse Cursor!):**
   - Moves via a learned **gaze** output rather than the cursor — so Premonition can read a menu item or button *before* pointing at it without triggering hover popups.
   - Keeps block edges, crosshair aim, HUD numbers, and desktop text razor-sharp; text leaves as exact characters, never through slot vectors or 3D reconstruction.
3. **32–64 Tracked "Thing-Only" Slots with Direction + Learned Range (90% of 3D Splats, 0% of the Renderer Cost!):**
   - Tracks movers, projectiles, interactables, and attended UI widgets (NOT terrain or 500-word pages).
   - Each slot stores: meaning/appearance, **viewing direction (bearing) + learned rough range**, velocity, separate *present* vs. *visible* confidence, and last-seen age (`dt`).
   - **Free Camera Consistency Without Gaussians:** Rotated by `logged mouse delta × learned gain` and shifted by learned movement estimate, with uncertainty widening behind pillars or behind your back (and on Crafter/desktop, the exact same step is a 2D tile shift / page scroll!). Stereo audio raises a *direction hypothesis* rather than inventing an exact fake distance.
   - **Workspace Routing:** Reserves summary capacity for the Big Brain's `Who` and `Avoid` queries (not just raw visual salience).

### Why 3D Gaussian Splats Are Deferred (and What Tests First If 3D Is Needed)
- **Why defer splats:** (1) *Opacity ≠ solidity* — soft blobs can look great visually while putting a bridge's walkable edge in the wrong place; (2) feed-forward encoding is the real bottleneck (`pixelSplat` took ~102 ms to encode vs. 2 ms to render); (3) 256 blobs cannot explain a whole Minecraft frame without smearing terrain or collapsing opacity, and monocular 3DGS without ground-truth depth/pose is unstable at 5M–15M params; (4) the rigid camera rotation win works directly on Candidate 5's Direction+Range slots with **no** Gaussians or renderer!
- **First 3D Challenger (only when needed for Minecraft):** **Candidate 4-lite (Multi-layer Local Height/Terrain Grid + Thing-Slots)** — distinguishing *unobserved* vs. *observed empty* across heights so a bridge deck isn't confused with a tunnel underneath.
- **4-Arm Equal-Clock Gate (≤ 4.00 ms/tick p99 on 5070 Ti with Brain search running; 3–5 seeds; held-out maps/FOV/sensitivity/skins; prettier frames earn zero credit):**
  - Arms: **A** (Patch Grid + Gaze Crop only) vs. **B** (Candidate 5: + Direction/Range Thing-Slots) vs. **C** (B + Coarse Multi-Layer Terrain Grid) vs. **D** (B + Gaussian Splat parameters/render loss).
  - Sub-tests: **Look Away & Look Back** (reappear bearing within 10° ≥ 80% / reacquire ≤ 0.5s), **Pillar Occlusion** (presence ≥ 90%, identity swaps ≤ 5%, ghosts ≤ 10%), **Void Behind & Bridge Crossing** ("floor within 2 blocks behind?" ≥ 90%, cross void without falling), **Off-Screen Sound Centering** (≤ 1s), **Projectile Cover** (≤ 2s), plus **≥ 10% lower 1s fall/hit Brier score** and Crafter/desktop controls not degraded.
  - **Upgrade Rule:** Any heavier arm wins only if it cuts failures by **≥ 25%** on ≥ 2 sub-tests (or **≥ 8 percentage points** higher mean behavioral success, 95% CI excluding zero), no sub-test/control degrades, and ≥ 4/5 seeds train without collapse. If plain Arm A matches Arm B, ship Arm A!

---

## 3. Upgraded, Honest Grading Rulers (Addressing Ben's "Marks Need to Be Greater!")

Our audit proved a brainless 1-line linear camera-shifter (`M_a [x_t, 1]`) already scores **`0.504 / 0.580 / 0.631`** on 16×16 Crafter (`1 / 3 / 5` steps). **Retire the easy `0.80 / 0.90 / 0.95` floor** as a pass bar. Keep the 16 inspected Crafter worlds for dev, **seal fresh unseen test worlds** for final scoring, and report **paired 95% confidence intervals across worlds and training seeds** (never treating 5,000 correlated frames as independent).

### A. Short-Horizon Physics Ruler ("Fast Physics")
1. **Ruler Drift Integrity Check (Synthetic):** At `k = 1, 3, 5`, verify: perfect deltas → 0 absolute error; zero deltas → exact copy baseline; constant per-step bias `c` → endpoint bias `k × c` (initialized once — zero peeking at true intermediate frames!).
2. **Real Physics Bar (Must Beat Both Camera-Shifter & Shift-or-Stay!):**
   - Refit persistence, per-action linear ridge (`0.504 / 0.580 / 0.631` historical refs), AND a cheap **"shift-or-stay"** predictor (peeks at destination patch and picks shift vs. stay). Beat the strongest validation-selected baseline at each horizon `k = 1, 3, 5`.
   - **Blocked vs. Open Move Check:** Label awake movement attempts cleanly from terrain displacement in HUD-masked `64×64` frame pairs (blind to predictions, zero game-memory cheats) and run the exact same displacement readout on every predictor's frames. Require **≥ 25% reduction** in `mean(false-block rate, false-open rate)` with neither rate worse (always guessing "blocked" must lose).
3. **Brain → Hands Contract Test:** Clone **both screen AND Hands memory**, mirror target positions, flip *only* `Who` or `Avoid` (or `"hover"` vs. `"activate"`), and require **both complete routes correct in ≥ 90%** of held-out pairs.

### B. Long-Horizon Conceptual Ruler ("Slow Plot" — All 4 Rulers!)
1. **Event & Milestone Calibration + Timing Error:** On **goal-directed** trajectories (not random wandering!), predict concrete milestones (e.g., *new wood within 25 steps* on Crafter; *purchase confirmed / bed lost / damage* at 2s, 10s, 30s) and beat an **inventory-and-phase baseline** on Brier loss + timing error.
2. **16-Way Future Lineup Picking:** Distractors matched on starting conditions, accepting equivalent futures.
3. **Plan / Goal Scramble:** Randomize feasible plans from cloned starts — plan swaps must **reverse predicted rankings** where real trials reverse outcomes.
4. **Real Play Lift + Latency Budget:** Actual held-out task success / survival / wins within a fixed attempt cap with Slow Plot + Multiverse Search **ON vs. OFF** at equal planning time, reporting p99 motor-tick (`≤ 4 ms`) and p95 sensor-to-action latency (`≤ 50 ms`) *with search running*.

---

## 4. The Revised 4-Rung Toy Proof Ladder *(Astra-Hardened — One Claim at a Time!)*

### Rung 0 *(2 min CPU, Zero Training)* — Verify the Ruler & Open the Hood
- Free space on M3 (currently `5.7 GiB` free, under the `12 GB` safety limit).
- Run the 3 synthetic ruler drift checks at `k = 1, 3, 5`.
- Run the read-only CPU X-ray ([run_xray.py](<project>/PROBLEM-7/neon-audit/run_xray.py)) on saved Step-2/Step-6 weights, comparing individual-row vs. pooled-board probes (if rows predict the change but the decoder cannot, fix the decoder before blaming the 68:1 offset!).
- Match Crafter's actual **300-step** day/night light cycle (counting exposure by actual light level & action), move the 16 inspected worlds to dev, and seal fresh unseen test worlds.

### Rung 1 *(Crafter — Real Physics: "Do You Know When You'll Hit a Wall?")*
- Freeze data and ruler first; change centering, action broadcast, and row-aware decoding **one knob at a time**.
- Compare `16×16` vs. `64×64` inputs on identical trajectories against the same output target.
- **Pass bar:** Beat the strongest baseline (per-action ridge + cheap shift-or-stay) on rollout error at `k = 1, 3, 5` **AND** cut `mean(false-block, false-open)` by **≥ 25%** with neither worse.
- *(Clean Two-Speed test: hold the spatial architecture FIXED and compare 1 clock vs. 2 clocks at equal wall time — never conflate a better spatial encoder with two speeds!)*

### Rung 2 *(Crafter — Honest Branching Odds + True Dream Bullshit Detector + Useful Surprise)*
1. **Honest Branching Odds (NO "best-of-4" cherry-picking!):** Fork identical simulator states, hold actions fixed, vary only future randomness, selecting mob encounters *before* seeing outcomes. Score the `W = 4` branches' **probability-weighted Brier loss** on joint outcomes (mob location + damage) → require **≥ 20% lower Brier loss** than a single-pass probability head, with calibration error `≤ 0.10`.
2. **True Dream Bullshit Detector:** Withhold one specific interaction during training at matched lighting/action/depth, while keeping **familiar-but-random encounters as negatives**. **Average over `z_world` dice inside each head BEFORE measuring disagreement across independently bootstrapped heads!** At 80% coverage, require lower retained error than rejecting by predictive entropy (plus precision-recall at natural prevalence).
3. **Useful Decision-Relevant Surprise:** Replan on the top 10% highest-surprise steps vs. 10% random steps → require **fewer real failures at equal compute**.

### Rung 3 *(Crafter — Split Into 3 Clean Separate Proofs!)*
- **Rung 3a — Command Contract (`Who / Avoid`, can run alongside Rung 1):** Clone screen **and Hands memory**, mirror target positions, flip only `Who` or `Avoid` → **both complete routes correct in ≥ 90%** of held-out pairs.
- **Rung 3b — Slow Plot (Goal-Directed Data, NOT Random Play):** Collect goal-directed episodes with randomized feasible plans from cloned starts. Predict e.g. *new wood within 25 steps* → beat an inventory-and-phase baseline on Brier loss, pass matched-start lineup picking, and prove plan swaps reverse rankings where real trials reverse outcomes.
- **Rung 3c — Two-Speed Game-Film Sleep:** Race ordinary replay vs. tactical replay (2–5s) vs. tactical+macro replay (minutes back, ordered vs. **shuffled** event timelines!) at equal film, updates, and planning time. Require real-play lift on **decisions whose cue predates the tactical window**, trial-verified counterfactuals (never unverified dream labels!), and **≥ 95% retention per established skill**.

### Rung 4 *(3D Minecraft / Bedwars & Mac Desktop — One Claim at a Time!)*
1. **Behind-your-back occlusion:** Identical final views requiring different moves from earlier occlusion (Candidate 5 vs. memoryless Hands / Candidate 1).
2. **Live bridging while dreaming:** Cross void gaps with Big Brain dreaming live, p95 sensor-to-action latency **≤ 50 ms**, validated separately on RTX 5070 Ti and Mac.
3. **4-Arm Part C Shootout:** Arm A (2D Grid) vs. Arm B (Candidate 5 Thing-Slots) vs. Arm C (+ Multi-Layer Terrain Grid) vs. Arm D (+ 3D Gaussian Splats) inside the exact **4.00 ms** motor clock.
4. **YouTube Video × Sleep 2×2 Showdown:** Video ON/OFF × Sleep ON/OFF counting wins within a fixed attempt cap (including worlds never won), keeping old skills `≥ 95%`!

---

## 5. Deep-Dive Module Specs (Astra Max Reviewed, Locked One by One)

### Deep Dive #1 — Parallel Multiverse Engine & Dream Bullshit Detector *(Locked with Astra Max Review #1)*
1. **Exact Discrete World-Dice (`W = 4`, No Gumbel / No Posterior Net):** Enumerate all 4 mixture components directly with exact marginal log-likelihood `−log Σ_z p_z d_z` (equivalently backprop `−Σ_z sg[r_z](log p_z + log d_z)` on stopped real-observation feature changes + reward). Initialize centers from distinct transition residuals, feed the action *before* the component split, never force uniform code usage in deterministic contexts, and calibrate **observable outcomes** (not code IDs).
2. **Anti-Collapse Dream Bullshit Detector (Before Shared Bottleneck + Joint Distribution JS Divergence):** Keep ONE `BoardSwarm`, and give each of `E = 4` episode-bootstrapped heads a tiny **private encoder of recent frames & actions + additive frozen random prior** *before* the shared bottleneck (ablate `heads-only → +private encoder → +random prior`, validating on real roots first). Marginalize `z_world` into a **joint observable distribution** `P_e(y) = Σ_z p_e(z) P_e(y | z)`, then score epistemic disagreement via Jensen-Shannon / Mutual Information `U = H(P̄) − (1/E) Σ_e H(P_e)`. Hold head `e` fixed along a rollout trajectory while redrawing `z` each step.
3. **Reusable Dream Scratchpad (Rebuild From Copy #0 Each Tick for Rung 2):** Keep Copy #0 strictly anchored (test that mutating dream lanes leaves Copy #0 bit-identical); warm-start only action proposals across ticks (drop live board/subtree reuse for Rung 2). Include one full-support wild-card outside top-`M`. **Prune actions, NEVER unlucky world outcomes:** place unresolved probability mass `r` at valid `[lower, upper]` return bounds and spend another wave if completions can flip the ranking (never renormalize `r` away).
4. **Root CVaR Risk + Same-Units Epistemic Penalty + Prospective `AUTO` Effort:**
   - Compute exact lower-tail CVaR over total trajectory return `G` at the root per head `e`: `ρ_e = (1 − c) E_e[G] + c max_t { t − E_e[(t − G)_+] / α }`.
   - Combine in return units: `Score(m) = ρ̄(m) − β · SD_e(ρ_e(m))`.
   - Train a prospective `AUTO` stop-vs-+1-wave gate on dev episodes (randomizing stop vs. +1 wave with subsequent policy fixed) estimating expected return lift `g(x) = ρ(G_extra | x) − ρ(G_stop | x)` from pre-action cues `x`, continuing iff `g(x) > λ · Δt` and deadline fits.
5. **Hardened Rung-2 Proofs:** (2a) Ordinary joint Brier loss `||P̂ − onehot(y)||²` vs. compute-matched direct joint categorical head, checking agent-visible Bayes floor `B_*` first + rare-damage calibration + 3–5 step action ranking; (2b) compare `U` against observable entropy `H(P̄)`, estimate reducible error via two independent fork histograms `(P̂ − F_1)ᵀ(P̂ − F_2)` at 80% coverage, rotate withheld interactions kept strictly out of Sleep/calibration; (2c) compare prospective gate vs. random & action-gap-only on paired held-out worlds at equal **total wall-clock** (including detector cost) reporting failure CIs, deadline misses, and task progress.

---

## 6. External Review Archive (All Reviews Completed)
- **Parts A & B — Astra Max (Codex, `gpt-6.2-astra`, `reasoningEffort=max`):** Completed; adopted all 6 upgrades (`Who/What/Where+Avoid/When/How` target query + exact text ref, `"input sent"` vs. `"world changed"`, Decision-Relevant Surprise, hypothesis-only counterfactuals, caution never warps odds, wild-card exploration slice, effort = wall-clock budget).
- **Part C — Astra Max (Codex, `gpt-6.2-astra`, `reasoningEffort=max`) & Claude Fable 5.2 Max (API, [REPLY.md](<project>/PROBLEM-7/neon-audit/part-c-fable/REPLY.md), `$3.07`):** Unanimous verdict → defer 3D Gaussian Splats, build **Candidate 5** (2D Patch Grid + Motion Channel + Gaze-Driven Sharp Crop + 32–64 Direction/Range Thing-Slots), test Multi-Layer Terrain Grid first if 3D is needed, gate every upgrade on the same ≤4 ms clock.
- **Part D Ladder — Astra Max (Codex, `gpt-6.2-astra`, `reasoningEffort=max`):** Completed; adopted all 7 scientific hardening upgrades (retired 0.80 bar, 300-step Crafter cycle, sealed test worlds, shift-or-stay baseline, forked probability-weighted Brier odds, averaged-dice epistemic alarm, split Rung 3a/3b/3c).
- **Deep Dive #1 (Multiverse Engine & Dream Bullshit Detector) — Astra Max (Codex, `gpt-6.2-astra`, `reasoningEffort=max`):** Completed; adopted exact `W=4` enumeration (dropped Gumbel/posterior net), pre-bottleneck private encoder + frozen random prior + joint-distribution JS disagreement, reusable scratchpad with conservative unresolved-mass bounds (dropped Rung-2 live subtree board reuse), root CVaR + `SD_e(ρ_e)`, prospective `AUTO` VoC gate, and tightened Proofs 2a/2b/2c.
