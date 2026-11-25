### 1. Harness-Only Recipe
The bottleneck is low write SNR (`gate≈0.12`, `out_proj std 0.02` → ~1% delta), compounded by BatchNorm and a short training budget.
- **Reader:** `Linear(48→256)→LN→GELU→Linear(256→256)` + learned 2D pos emb; add a learnable post-RMS gain if allowed.
- **Ticks & Pinning:** Run **3–4 ticks/frame**, **unpinned** (cleanest). If pinning patches into 16 fast rows to raise input SNR, decode strictly from the **48 unpinned rows** (and zero pinned rows for 1 tick before decode). Init board with small norm if controllable.
- **Decoder:** Swap BatchNorm for **per-row LayerNorm** (preserves per-frame contrast). Read all unpinned rows via a **linear + shallow per-patch MLP residual** (normal init, not zero-init) so it immediately matches your ridge probe.
- **Loss:** `MSE + 5× motion-weighted MSE` (`|x_t−x_{t−1}| > 0.02`) so static backgrounds don't mask blurry sprites; add light intermediate-tick loss.
- **Optimizer:** Train reader + decoder (+ trunk, if unfrozen) jointly with AdamW, cosine decay, grad clip 1.0, ≥10k steps. Param-group LRs: `1e-3–3e-3` on reader/trunk (wakes `sigmoid(-2)` gates), `3e-4` on decoder.

### 2. Pass Marks (Held-Out Worlds) & Anti-Cheat Controls
Evaluate mid-rollout (board holds `t−1` before reading `t`):
- **All pixels:** `MSE / MSE(world_mean) ≤ 0.05` (`R² ≥ 0.95`).
- **Moving pixels (`|x_t−x_{t−1}| > τ`):** `MSE / MSE(copy x_{t−1}) ≤ 0.15` (stretch `≤ 0.05`).
- **Linear probe (trained board):** All-pixel NMSE `≤ 0.10`, moving `≤ 0.25` (rules out MLP memorization).
- **Cheat controls:**
  1. *Zero/shuffled context at `t`*: moving-pixel MSE reverts to `copy(x_{t−1})`.
  2. *Zeroed/shuffled board at decode*: error collapses (no side-channel).
  3. *Color-permuted / synthetic-sprite OOD frames*: rules out world-ID lookup.
  4. *Disjoint readout assert* (if pinning): zero read/grad access to pinned rows.

### 3. Proving the Trunk Is the Bottleneck
Test on both a 100-frame overfit set and held-out worlds:
1. **Reader→Decoder bypass** hits NMSE `< 0.01` (clears harness).
2. **Unpinned board** still stalls at moving-pixel NMSE `> 0.30` across 1→4→8 ticks and LR sweeps, plus one smoking gun:
   - *Write starvation:* per-tick delta stays `< 5%` of row norm, gates remain near `0.12`, or MoE routing collapses.
   - *Transfer failure:* pinning into 16 fast rows while decoding the 48 unpinned rows also stalls (`> 0.25`), or a trained trunk barely beats a frozen trunk on a linear probe.
