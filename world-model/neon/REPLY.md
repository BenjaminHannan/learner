### 1. Diagnosis (8 lines)
Yes: the current main-build design carries a severe collapse and shortcut risk once real frames drive the board (`suggested`; `untested` on real transitions).
1. **Unanchored target**: `z_pred` predicts the detached mean of 24 slow rows produced by the *same mutable trunk*, with no external loss forcing those rows to read sensory context (`shown`), so shrinking variance or ignoring frames minimizes MSE (`suggested`).
2. **Dry-run drop proves nothing**: the 50M main-build dry run's 0.022→0.001 drop on `WAIT` (`shown`) can be achieved by slow rows barely changing across thinking ticks (`suggested`).
3. **Untrained imagined board**: `z_pred` uses only the *current* board's slow-row mean plus a linear head on the action row, so the predicted next board (`B_hat = board + residual`) receives zero gradient today (`shown`), making multi-step rollouts ungrounded (`suggested`).
4. **Measurements that tell**: (a) ratio `MSE(z_pred, z_real_{t+1}) / MSE(z_real_t, z_real_{t+1})` (must beat "nothing changes"), (b) `std` and effective rank of `z_real` across distinct real frames (collapse = low variance/rank), and (c) scorer-only linear probe from `B_hat` to real state changes (`suggested`).

---

### 2. Candidate Evaluation

* **Candidate 1 — Latent target as today, real data (`untested`)**
  * *Strongest reason it works*: Zero architectural change; keeps the shared trunk (`shown` rule) and can sometimes avoid full collapse via stop-gradient bootstrapping if another loss keeps representations rich (BYOL-style, `from memory, unchecked`; `suggested`).
  * *Strongest reason it fails*: No external grounding anchors the slow rows, `B_hat` remains completely unsupervised (`shown`), and feeding imagined boards back during training risks drifting into self-generated targets (`suggested`).
  * *Owner rules*: Borderline if multi-step imagined feedback is used during world-model training (`suggested`). **Drop.**

* **Candidate 2 — Observation-grounded target on shared trunk (`untested`)**
  * *Strongest reason it works*: Decoding `B_hat` to the real next 64×64 frame (or frozen spatial features) makes target collapse impossible, trains all 64 rows of `B_hat`, keeps the shared trunk, and directly produces the demo's side-by-side "imagined vs. real" frames (`suggested`).
  * *Strongest reason it fails*: Pixel MSE weights static background tiles equally with tiny HUD/inventory pixels and blurs stochastic mob motion; 1-step training alone may still drift on 3–5 step rollouts (`suggested`).
  * *Owner rules*: Complies with all rules when added as one single change on real transitions (`suggested`). **Keep (Pick).**

* **Candidate 3 — DreamerV3-style separate world model / RSSM (`untested` here)**
  * *Strongest reason it works*: Proven on this exact 2D survival benchmark (Crafter, Hafner et al., DreamerV3, `from memory, unchecked`); small, fast on laptop/16 GB GPU, and includes stochastic latents for unpredictable mobs (`suggested`).
  * *Strongest reason it fails*: Leaves the thinking trunk ungrounded and creates two separate internal state spaces (`suggested`).
  * *Owner rules*: **Breaks** the rule to keep the shared trunk unless shown it cannot work—main-build real-transition evidence does not exist yet (`shown`). **Drop for now** (reserve after 3 shared-trunk misses).

* **Candidate 4 — Frozen-target prediction, no decoder (`untested`)**
  * *Strongest reason it works*: Keeps the shared trunk, target cannot collapse (frozen encoder), and precomputed embeddings are fast on M1 Pro (`suggested`).
  * *Strongest reason it fails*: A pooled natural-image embedding often ignores 64×64 pixel-art HUD icons and 1-tile shifts; also fails to produce visual side-by-side predictions (`suggested`).
  * *Owner rules*: Complies with all rules (`suggested`). **Keep as fallback** (with spatial patch tokens if Candidate 2's pixel decoder fails).

* **Candidate 5 (Added) — Shared trunk + 64×64 decoder + full-board stop-grad alignment `MSE(B_hat, sg(B_real))` (`untested`)**
  * *Strongest reason it works*: Grounds `B_hat` in pixels *and* forces `B_hat` onto the exact manifold of real boards `B_real` for stable 3–5 step rollouts (`suggested`).
  * *Strongest reason it fails*: Combines two changes at once (`suggested`).
  * *Owner rules*: **Breaks** "one change at a time" as Test #1 (`shown` rule). **Keep for Test #2** if Test #1 passes `k=1` but drifts at `k=3, 5`.

---

### 3. Pick & Single First Test

**Pick**: **Candidate 2 (pixel-grounded shared trunk)** on the candidate 2D Minecraft-like survival benchmark (Crafter: 64×64 RGB, 17 discrete actions, 22 achievements, CPU-fast, `from memory, unchecked`). Keep this environment—procedural seeds give clean held-out worlds (`suggested`). Note that past toy-build planning results (`shown`: word-room 94.5–100% and inconclusive bait-grid pilot) used separate small networks and give **no** evidence on this main-build trunk (`shown`).

* **The single change**: Keep the shared trunk (using the existing 64×256 board shape at a laptop-sized ~10–15M active-param trunk, `suggested`), existing frozen image encoder context, action row, and detached `z_pred` loss (`shown`). Add **one** small learned transposed-conv decoder (~0.5M params, mapping 64 board rows reshaped as 8×8×256 → 64×64×3 RGB) attached to `B_hat_{t+1}`, trained with plain `[0, 1]` pixel MSE against real `o_{t+1}` strictly on 1-step real transitions (`untested`). Everything learned end-to-end from pixels and actions; zero game state input, zero hand rules (`suggested`).
* **Data & split**: Record 40,000 real transitions (200 episodes × 200 steps) via a random/scripted-exploration data collector (balanced over the 17 actions so ≥85% are non-noop; used only for dataset collection, never inside the model). Hold out completely unseen world generator seeds: seeds 0–159 train (32,000 transitions), 160–179 val (4,000), 180–199 test (4,000 transitions + 500 contiguous 5-step real sequences). Precomputing frozen encoder rows (~3 min) + 8 epochs on M1 Pro MPS (~18 min) + eval (~2 min) fits under 30 minutes (`suggested`).
* **Fixed pass marks (held-out seeds 180–199, `[0, 1]` pixel MSE, open-loop rollout feeding `B_hat` forward with real `a_{t+k-1}` and no future frames)**:
  * **(a) k-step vs. "nothing changes" (`o_t` copied)**: `k=1 <= 0.65×`, `k=3 <= 0.80×`, `k=5 <= 0.90×` baseline MSE (`untested`).
  * **(b) Action-shuffled control** (permute `a` across the test batch): `MSE_real(k=1) <= 0.80× MSE_shuffled(k=1)` and `MSE_real(k=3) <= 0.88× MSE_shuffled(k=3)` (`untested`).
  * **(c) Anti-collapse**: predicted frame spatial/batch `std(o_hat_{t+1}) >= 0.70× std(o_{t+1})`, ≥50% of `z_real` dims have `std > 0.01`, and `MSE(z_pred, z_real_{t+1}) <= 0.85× MSE(z_real_t, z_real_{t+1})` (`untested`).
* **Outcome odds**: **PASS 30% / PARTIAL 50% / WRONG 20%** (`suggested`—high odds `k=1` passes, high odds `k=3, 5` drifts without full-board alignment).
* **What proves me wrong**: `k=1` fails to beat `"nothing changes"` or `action-shuffled` by even 5% *after* the frozen encoder passes the Free Check—showing the shared trunk's read-only attention cannot route sensory+action dynamics into `B_hat` (`suggested`).
* **Next steps**:
  * *If PASS*: Move to the 16 GB GPU (12-min slot) for the **first dream-trained policy test**: freeze the world model, train a small scalar reward head on real transitions only, then train an actor-critic inside 5-step imagined rollouts from detached real boards (preserving the main build's walled-off planner isolation, `shown`), measuring real held-out Crafter episode return before vs. after offline "sleep" (`untested`).
  * *If PARTIAL (`k=1` passes, `k=3, 5` fails)*: Run Test #2 = Candidate 5 (add `MSE(B_hat_{t+1}, sg(B_{t+1}))` full-board alignment).
  * *If WRONG (`k=1` fails)*: Run Test #2 = Candidate 4 (predict frozen spatial patch tokens) to isolate decoder vs. trunk failure. After **3 misses**, close the shared-trunk world-model branch (`shown` rule) and switch to Candidate 3 (separate RSSM).

---

### 4. One Free Check Before Training (~3 Minutes on CPU)
Collect 500 Crafter frames (3 random episodes), encode them with the main build's frozen image encoder (zero trunk training), and run two checks (`untested`):
1. Compute the exact `"nothing changes"` pixel MSE at `k=1, 3, 5` to verify real visual motion exists.
2. Fit a closed-form ridge probe (scorer-only, using game state strictly as ground-truth labels) from the frozen encoder's output rows to player movement `(dx, dy)` and inventory deltas. **Gate**: if movement probe accuracy is `<85%`, the borrowed encoder is blind to 64×64 pixel-art—switch to its spatial patch outputs before running Test #1 (`suggested`).

---

### 5. Rule Feasibility & Cheapest Rule to Loosen
Candidate 2 meets every rule on a scaled-down shared trunk (`suggested`), with two narrow tensions (`untested`):
1. **Laptop budget vs. full trunk**: Training the full 466M/106M-active production trunk (`shown`) cannot finish in <30 min on an M1 Pro (`suggested`). **Cheapest clarification**: explicitly permit the 64×256 small-trunk slice (~10–15M active) for the 30-min laptop gate before scaling on the 16 GB GPU.
2. **Multi-step drift**: If 1-step real training consistently fails `k=3, 5` even with Candidate 5, the **cheapest rule to loosen** is clarifying "never on its own imagined rollouts" to allow 2–3 step open-loop rollouts supervised *strictly against real observed future frames* (never synthetic targets), which is far cheaper than discarding the shared trunk (`suggested`).

---

### 6. Key Assumptions & Missing Facts
**Assumptions that would flip the pick if false**:
1. The frozen image encoder outputs **spatial patch rows**, not a single global pooled vector (if global-only, pixel decoding fails and the encoder output format must change first, `suggested`).
2. The main build runs a small width-256 shared trunk on M1 Pro MPS in <30 min (`suggested`).
3. Crafter's 1-step frame transitions are mostly deterministic given visible pixels + action (if mob randomness dominates MSE, deterministic prediction blurs and favors Candidate 3's stochastic latent, `suggested`).

**3 facts wanted but missing**:
1. Exact output shape and resolution of the frozen 24 fps image encoder (patch grid vs. single vector).
2. Measured step time (ms/step) and parameter count of the width-256 shared trunk on M1 Pro MPS.
3. Whether `imagine` mode currently attends to live sensory context rows or only the board, and whether any loss touches `B_hat` today.

---

### 7. Summary for the Owner
Right now, the model's "imagination" is graded only against its own internal thoughts, so once we feed it real game frames it could easily cheat by barely changing its thoughts and ignoring the screen. To fix that without abandoning your single shared-brain design, our first laptop test adds one small visual translator that forces the model's imagined next state to actually draw the next 64×64 game frame in a fast 2D Minecraft-like survival world. Before spending 30 minutes training, we will run a 3-minute free check to make sure the borrowed vision encoder can actually see tiny game details like player movement and inventory icons. The training test passes only if the model beats a "nothing changes" guess across 1, 3, and 5 steps in brand-new unseen worlds, gets much worse when we scramble its button presses (proving it truly understands its own actions), and avoids blurry or collapsed outputs. If it passes, our very next step on the GPU is letting the player practise inside 5-step frozen dreams and checking if it plays better after "sleep"; if three shared-brain attempts miss our preset targets, we will cleanly switch to a separate Dreamer-style world model.
