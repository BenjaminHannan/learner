### 1. Most Likely Cause
**Closed-gate SNR collapse + an Adam-$\epsilon$ dead-gradient trap, reinforced by the predict-zero baseline.**

* **Forward (~1% SNR):** Each tick writes `sigmoid(-2) * out_proj(h)` ($\approx 0.12 \times 0.02\sqrt{D}$). Before that, uniform initial cross-attention averages the 16 patches (washing out localized sprites against static game background), and sparse MoE sees nearly identical rows across frames. That leaves a `0.005–0.03` frame-dependent perturbation sitting on `0.3–1.8` static board magnitude (~1% amplitude SNR, $\sim 10^{-4}$ variance fraction). Running 8 ticks accumulates static drift alongside signal, so SNR stays ~1%.
* **Backward (`~1e-11` grad):** Predicting a sparse, near-zero-mean *next-frame change* from 99%-constant rows lets the decoder immediately cancel the static component and shrink readout weights to hit the predict-zero baseline. Backprop through sparse-target MSE ($\sim 1/768$) $\times$ small/collapsed decoder $\times$ `sigmoid(-2)` $\times$ `out_proj(0.02)` $\times$ cross-attention ($W_O, W_V$, $1/16$ averaging) $\times$ MoE routing drives patch-reader gradients to `~1e-11`—**~3 orders of magnitude below Adam's default `eps = 1e-8`** (and swamped by weight decay). Even at `lr = 3e-3`, Adam is trapped in its $\epsilon$-damped regime and never opens the write gate.

---

### 2. Single Best Harness-Only Fix
**Pin the frame patches directly onto dedicated board rows via `pin_row`.**

* Write the 16 patch embeddings (`Linear(48->D)`, initialized semi-orthogonal/full-rank, scaled to native board RMS `~0.5–1.0`, with zero or small `pos_emb` since row index already encodes patch position) into 16 dedicated board rows (e.g., rows `0..15`), leaving the remaining `R - 16` rows free as recurrent workspace (if `R` is too small, pack into $K \le R/2$ coarser patches).
* **Why it works:** It completely bypasses the closed cross-attention write gate at tick 0—jumping board frame SNR from ~1% to $O(1)$ and giving the patch reader a direct gradient path ($\gg 10^{-8}$) while the trunk reads the full-amplitude frame via self-attention into the workspace rows.
* *Caveat if the decoder is forbidden from reading pinned rows:* Keep `pin_row` on input rows so the trunk reads full-amplitude patches via self-attention, **and** add an auxiliary **current-frame ($x_t$) reconstruction loss** on **batch-standardized** unpinned rows (`(rows - rows.mean(0)) / (rows.std(0) + 1e-5)`) to strip the static offset and break the predict-zero saddle.

---

### 3. Cheap Pre-Run Gate (No Training Required, ~2 Seconds)
Run `N = 512` diverse frames (episode-disjoint **400 train / 112 val** split) through the untrained harness + $T$ ticks, flatten decoder-visible board rows $Z \in \mathbb{R}^{N \times (R \cdot D)}$, center using the train mean, and fit **closed-form dual ridge regression** ($400 \times 400$ solve, sweeping $\lambda \in \{10^{-4}, 10^{-2}, 1\}$) to reconstruct the **current frame $x_t$**. Pair with a 1-step backward check:

1. **Frame-capacity gate (primary):** Held-out pixel reconstruction **$R^2 \ge 0.80$** on decoder-visible board rows (if gating *unpinned* workspace rows specifically, require **$R^2 \ge 0.50$**).
2. **Board SNR sanity check:** `mean(std_across_batch(rows)) / mean(rms(rows)) >= 0.15` (vs. current `~0.01`).
3. **Gradient-flow sanity check (1 backward pass on step 0):** Patch-reader **`RMS(grad) >= 1e-5`** ($\ge 10^3\times$ above Adam `eps = 1e-8`, vs. current `~1e-11`).

If any of these fail at step 0, do not launch a scored run.

---

### 4. Minimal Core Change (If No Harness Fix Is Allowed)
If the frame must enter strictly through cross-attention into unpinned rows, propose a **2-line write-update fix** (zero new parameters):

1. **Open the write gate + standard init + convex overwrite:**
   * Change `gate` bias init from `-2` to **`0.0`** (`sigmoid = 0.5`, $4\times$ gain) and `out_proj` init std from `0.02` to **`1 / sqrt(D)`** ($\sim 3\times$ gain at $D=256$).
   * Replace additive `rows += g * out_proj(h)` with **convex interpolation** `rows = (1 - g) * rows + g * out_proj(h)` so static initial rows decay as $(1 - g)^T$ (`0.25` after 2 ticks) instead of permanently swamping new frame writes.
2. *(Only if the gate in #3 still fails due to internal cross-attention/MoE dilution):* Add one **ungated cross-attention read-in residual** directly onto the board (`rows = rows + cross_attn_in(RMSNorm(rows), ctx)`, standard `1 / sqrt(D)` init) ahead of the gated MoE update.
