**Verdict:** Defer the Gaussian splats. Build Candidate 5, a narrowed Candidate 2 on Candidate 1's patch grid, and make every 3D upgrade pass the gate in section 3. [untested]

Labels: [shown] = stated in your brief; [suggested] = my reasoning or an outside lead; [untested] = nobody has measured it.

## 1. Critique

- The hardest bottleneck is behind-the-back persistence of moving things while the agent turns and moves; it is the only one where the needed information is off-screen. Only Bedwars stresses it. [suggested]
- Text, block edges and most projectiles are on screen when acted on, so a sharp crop solves them. [suggested]
- Unseen opponents keep moving, so after 1–3 s the honest state is a widening guess. Precise 3D there is false confidence. [suggested]
- No single store is clean: grids lose identity, slots cannot hold void ("no floor" is not an object) or 500 words, and blobs cannot hold hard edges or text. [suggested]

## 2. Candidates

**Candidate 1 (patch grid + recurrent memory): keep, as control and scene backbone.** One code path for all three domains and nothing to calibrate [suggested]. Its memory has no built-in notion of turning and gives Who/Avoid queries no persistent handle [suggested]. Candidate 1's forgetting risk has outside backing in WorldMem, where a bank of past frames stored with poses and timestamps was the fix for consistency failures of a short context window (checked online: https://arxiv.org/abs/2504.12369). Its test conditions supplied ground-truth poses, and the model is far larger than ours (from memory), so this may not carry over. Budget: fits easily [untested].

**Candidate 2 (universal slots): keep, narrowed.** Slots are what the Command Frame's queries match [shown], and dreaming on them is cheap [suggested]. Learning objects from scratch is the weak point: one object-centric world-model win on a visually busy game, Hollow Knight, borrowed its objects from a frozen pretrained segmenter seeded with a few human-marked frames (OC-STORM, checked online: https://arxiv.org/abs/2501.16443). "Universal" also overreaches, because terrain and dense text do not fit 64–128 slots [suggested]. Budget: fits [untested].

**Candidate 3 (Gaussian blobs): defer.** Rendering a predicted view is the only mechanism here that can tell "hidden behind a pillar" from "gone" [suggested]. But its headline benefit, the rigid camera transform, needs no Gaussians and works on Candidate 2's slots [suggested]. The new part is the render loss, and 256 blobs cannot explain a Minecraft frame. The loss either smears blobs over terrain or lets a background decoder explain everything while blob opacity collapses [suggested]. Budget: fits at runtime; training stability is the risk [untested].

**Candidate 4 (coarse grid + entity slots): defer, first upgrade to test.** It has the right split of terrain and movers, is the only candidate that stores void, and Crafter is already a bird's-eye grid [suggested]. Lifting one uncalibrated camera into a grid without depth labels is unproven (driving models use calibrated rigs and 3D labels: Lift-Splat, BEVFormer; from memory, unchecked). Drift also blurs the grid at each resample, and it does nothing for desktop [suggested]. Budget: a coarse height map fits; a full 3D grid is tight [untested].

**Candidate 5 (my pick): fits the budget as a smaller Candidate 2.** [untested]
- **Things only:** 32–64 slots for movers, projectiles, interactables and attended widgets. Terrain and page background stay in the patch grid and recurrent memory.
- **Direction plus range:** each slot stores a viewing direction and a learned range, and takes Candidate 3's step (a). It is rotated by logged mouse delta times a learned gain and shifted by a learned movement estimate, with uncertainty widening as last-seen age grows.
- **No Gaussians, no renderer:** range is learned as whatever makes look-back predictions come out right. On Crafter and desktop the same step is a 2D shift (tile move, scroll).
- **Gaze-driven crop:** the sharp crop follows a learned gaze output rather than the cursor, so reading does not trigger hovers. Text leaves it as exact characters, never through slot vectors.
- **Motion channel:** a cheap full-frame motion channel catches small fast projectiles.

## 3. Pick and gating test

**Pick: Candidate 5.** The gate has four arms on held-out maps and skins:
- A = Candidate 1
- B = Candidate 5
- C = B + coarse height-map memory (Candidate 4-lite)
- D = B + Gaussian parameters and splat render loss (Candidate 3)

All arms get equal data and parameters. Each is resized to the same p99 tick (≤4 ms) on the 5070 Ti with Big Brain search running, over 5 seeds. Arm A has no slots, so every arm is read through the same small probe (a tiny read-out network) trained on separate labelled clips. Scoring truth comes from the test script or hand labels and never reaches the agent.

| Sub-test | Setup | Pass mark |
|---|---|---|
| Look away and back | Opponent seen 0.5 s, stationary or at constant velocity. Turn 120–180° away for 0.5–2 s, strafing in half the trials. | Predicted bearing within 10° of where it reappears in ≥80% of trials |
| Pillar occlusion | Opponent hidden ≤1.5 s; two look-alikes cross; some leave for good. | Presence held ≥90%; identity swaps ≤5%; ghosts after a true exit ≤10% |
| Void behind | On a 1-wide bridge facing an opponent, floor unseen for 2 s including one knockback. | "Floor within 2 blocks behind?" correct ≥90%; in-view 16-block bridging no worse than A |

Free-moving opponents are scored on honesty: the predicted 90% region must hold the truth in 85–95% of trials.

**Upgrade rule** (C or D over B, and B over A):
- at least 25% fewer failures on two sub-tests, with a 95% interval excluding zero;
- no sub-test more than 5% worse;
- Crafter score and character-exact desktop reading not worse;
- 4 of 5 seeds training without collapse.

All thresholds are my proposals [untested].

**What proves me wrong:**
- A lands within the margin of B: ship Candidate 1.
- D passes the rule while B misses the absolute marks: build the splats.
- B collapses in two or more seeds: slots from scratch are not viable here.

## 4. Candidate 3 traps

- **Camera calibration: cheap.** It is one gain per axis plus field of view, learnable by spinning in place. Minecraft's sprint and bow field-of-view changes, view bobbing and damage tilt (from memory, unchecked) need a learned residual or the game's own options menu. [suggested]
- **Movement: medium.** WASD does not give position under collisions and knockback, so movement must be estimated visually and its error enters every blob. [suggested]
- **Training from one camera without depth or pose: serious, open rather than fatal.**
  - A 5–15M from-scratch network is far from the MoVieS setting, which presupposes a large pretrained backbone plus big static, dynamic and point-tracking training sets (checked online: https://arxiv.org/pdf/2507.10065).
  - Candidate 3's compact-blob premise did gain support from C4G, whose pose-free, low-Gaussian-count query design is the first evidence I found that blob budgets can shrink without losing to per-pixel predictors (checked online, abstract only: https://arxiv.org/abs/2605.31595).
  - C4G is offline reconstruction of unverified size, so it may not carry over to a streaming model. It moved me from "drop" to "defer".
- **Soft blobs versus block edges: fatal only if blobs carry terrain.** If they do not, blobs have no occluders, and the hidden-versus-gone advantage needs Candidate 4's grid as well. [suggested]
- **Identity collapse: cheap.** Use predict-then-match updates and watch the swap metric. [suggested]
- **Internal inconsistency: cheap.** Step (b) compares against a predicted view every tick, yet step (c) renders only in training and on demand [shown]. Compare against projected blob centres and features instead [untested].

## 5. Assumptions that would change the pick [untested]

1. Thing-slots can be learned from scratch at 5–15M parameters, using motion the camera-movement estimate fails to explain as the objectness signal. If false: Candidate 1, or permit a frozen pretrained teacher offline.
2. Off-screen terrain needs only ±1-block awareness, because exact edges are in view when acted on. If blind retreats dominate deaths, Candidate 4 becomes the base.
3. Logged mouse deltas map stably to camera angle. If not, Candidates 3, 4 and 5 lose their free consistency and Candidate 1 wins by default.

## 6. Owner summary

Don't build the 3D blob system yet; this is a design recommendation, and nothing here has been run. Start simpler: the agent keeps a short list of tracked things (enemies, projectiles, buttons), each remembered as a direction and rough distance that updates whenever the agent turns or moves. Alongside that it keeps a coarse view of the whole screen and a small sharp window for text, the crosshair and block edges, and text never passes through any 3D step, so it stays crisp. This gives most of what the blobs promised, such as remembering an enemy behind your back, without their riskiest part: learning true 3D shape from one flat screen with nothing to check it against. Every design then takes the same fixed test at identical speed (look away and back, enemy behind a pillar, void behind you on a bridge), and a terrain map or the blobs get added only if they cut failures by at least a quarter. If the plain version with no tracking does just as well, the tracking goes too.