### 1. Score validity & optimism bugs

**No data leak or readout cheat:**
- **No held-out / next-frame leak into imagination:** `real_board(he, i, ti)` (`forecast2.py:17-19, 95`) only reads frames `i-1` (when `ti > 0`, guaranteed same-episode by `wm_fit.py:133-147`) and `i`. The active `imagine` (`forecast2.py:32-36`) shadows the dead photo-context version (`forecast2.py:20-24`), ignores `x0`, and passes only `enc_act(acts[:, j])` (`forecast2.py:26-31`) into `m.cell.imagine`. `st` is not mutated across `P` and `Ps` (`dataclasses.replace` on `forecast2.py:35`).
- **Readout fit strictly on real train boards with final weights:** `fit_readout()` (`forecast2.py:38-51`) uses only `real_board(tr, ...)` on `w1 < 140`, runs under `m.eval()`, is called again on final weights at `forecast2.py:67`, and updates globals `Wp, bp` read dynamically by `RT` (`forecast2.py:54`).
- **No eval/train mode mismatch in `m`:** `m.head` is deleted (`forecast2.py:7`) and `dec` (which owns the only `BatchNorm1d`, `forecast2.py:8-14`) is never called; `BoardCell` has no dropout/BN, `m.read` passes `noise=False` (`wm_fit.py:61-62`), and `SparseMoE` routing is deterministic (`board_swarm.py:506-508`).
- **Shuffle control is valid (not optimistic):** `forecast2.py:91-92` permutes intact `k`-step action chunks across windows within each held-out world `w` (slightly different from `wm_fit.py:201-212`, which permutes individual actions before windowing, and no easier).

**Bugs that DO make the `PASS` / `PARTIAL` verdict optimistic (compared to `wm_fit.py`):**
1. **Per-world shuffle conjunction broken (`forecast2.py:111, 113` vs `wm_fit.py:313-316, 343`):** `forecast2.py` checks `n1 >= 12 and n5 >= 12` independently instead of requiring `>= 12` worlds to pass **both** `k=1 >= 1.25` and `k=5 >= 1.10`. Disjoint sets of 12 worlds would wrongly `PASS`.
2. **Missing PCA anti-collapse mark (`forecast2.py:112-114` vs `wm_fit.py:328, 345, 349`):** `pcs90(pred_change) >= 0.5 * pcs90(real_change)` is neither computed nor checked. A low-rank collapse that matches scalar per-action std still passes.
3. **Ceiling gate logged but never enforced (`forecast2.py:107, 112-114` vs `wm_fit.py:338-339, 351-353`):** `ceiling_real_board_E_over_B` is computed and stored, but `verdict` ignores both `<= 0.70` (PASS pre-gate) and `> 0.95` (hard FAIL).
4. **Minor discrepancies / hazards:**
   - `std_ratio_by_first_action` (`forecast2.py:108`) drops actions with `< 20` samples (`wm_fit.py:322` uses `< 2`).
   - `fit_readout()`'s logged `val SSE` (`w1 >= 140`, `forecast2.py:42, 48`) is only unseen at step 0; the training loop (`forecast2.py:57`) samples all of `xi1`, including `w1 >= 140`. (Does not affect held-out `he`.)
   - `mv` (`forecast2.py:101`) checks `hfr[xi+1] - x0` even for `k = 5` (matches `wm_fit.py:296`, just note it filters by step-1 movement, not `k`-step movement).
   - Dead code: shadowed `imagine` (`forecast2.py:20-24`), unused `Dec`/`dec` (`forecast2.py:8-14`, which also breaks reloading a `forecast2.py` checkpoint since `forecast2.py:67` omits `"dec"`), and `ga` unbound if `--steps 0` (`forecast2.py:62, 69`).

---

### 2. Why one Adam step at `lr = 1e-6` moves `rec` 80× (`0.0008 -> 0.066`, then `681` by step 19)

First, rule out the `0.2` input noise as the cause of `img = 2813`:
- In `fit_readout()` (`forecast2.py:47`), writing $W_{\text{std}} = A^\top (AA^\top + \lambda I)^{-1}(Y - \bar y)$ with $\lambda = 3500 \cdot 0.2^2 = 140$ and $\|Y_{\text{train}} - \bar y\|_F^2 \approx 7 \times 8607 \approx 6.0\times 10^4$, the SVD bound $s/(s^2+\lambda) \le 1/(2\sqrt{\lambda})$ gives:
  $$\|W_{\text{std}}\|_F^2 \le \frac{\|Y_{\text{train}}-\bar y\|_F^2}{4\lambda} \approx 108 \implies \mathbb{E}\big[\mathrm{MSE}(0.2\,\varepsilon W_{\text{std}})\big] \le \frac{0.04 \cdot 108}{768} = 0.0056.$$
- So **`img = 2813` ($\mathrm{RMSE} \approx 53$ on `[0,1]` pixels!) at step 0 is NOT from `NOISE=0.2`** — it is from `BoardCell._imagine_impl`'s OOD `out_proj(hn[:, :R])` hitting `Wp = W_std / sd`.

The exact chain of mechanisms in the code:

1. **Step 0 `img = 2813`: `_imagine_impl` is wildly OOD relative to `real_board`, and drops the slow-row doorman gate on `Wp`'s highest-gain coordinates (`board_swarm.py:470-473` vs `561-571`, `forecast2.py:44, 47`):**
   - `real_board` runs 4 ticks of `tick()` with `focus=0`, `ThinkMode.THINK`, 16 image tokens, and **gates the 24 slow rows by `g_slow = sigmoid(gate(...) - 2.0) ≈ 0.12`** (`board_swarm.py:470-473`). Because step 3 trained with per-feature standardization (`Dec`'s `BatchNorm1d`, `forecast2.py:10`), slow rows and weakly-varying coordinates can have small cross-frame `sd` while sitting on a large constant offset `mu` (from `init_rows` std `0.5` and `row_pos_emb` std `1.0`, `board_swarm.py:232, 237`), which `bp = ym - mu @ Wnp` cancels.
   - `fit_readout()` divides `Wnp = (A.T @ al) / sd[:, None]` (`forecast2.py:47`), amplifying low-`sd` coordinates (especially slow rows, down to `1e-3 + 0.1*median(sd)`). And `lam = 140` is tiny relative to `Tr(A A^T) = 3500 * 16384 = 5.7e7`, so `Wnp` has high gain on small-singular-value collinear directions (`s ~ sqrt(140) ≈ 12`) that cancel on real boards.
   - `_imagine_impl` (`board_swarm.py:561-571`) runs a **5th** step with untrained `mode_emb[IMAGINE_NEXT_STATE]`, untrained `focus = 1.0` (`board_swarm.py:568` — activating the untrained `moe.film`!), untrained `action_emb`/`action_in`/`action_pos`, 1-token `enc_act` context, and **no doorman gate on slow rows** (`next_rows = x0 + self.out_proj(hn[:, :R])`, `board_swarm.py:571`). Adding full `1.0x` ungated `out_proj(hn)` shifts `o.next_rows` many `sd` off `mu` along `out_proj`'s column space, exploding `RT(o.next_rows)` to $\mathrm{RMSE} \approx 53$ ($\mathrm{MSE} = 2813$).

2. **Why `rec` jumps `0.0008 -> 0.066` in ONE `lr = 1e-6` step, then peaks at `681` by step 19 (`forecast2.py:59-63`):**
   - **`st.rows` is NOT detached into `imagine` (`forecast2.py:59`) AND `l_img` (`2813`) swamps `l_rec` (`0.0008`) by `3.5e6`×:**
     Because `o.next_rows = st_n.rows + delta_img` (`board_swarm.py:571`) has a direct residual skip from `st.rows`, `l_img` backprops straight into `real_board` (all 4 ticks + `init_rows` + `reader` + `pos` + `zoom` + `gate`) as well as the shared trunk. Nearly 100% of step 0's gradient on `real_board` points along $-W_p (RT(o.\text{next\_rows}) - x_n)$ — **actively pushing `RT(st)` away from `xt`** to cancel `imagine`'s $\mathrm{RMSE}=53$ bias!
     - **Smoking gun in the probe numbers:** minimizing $l_{\text{img}} + l_{\text{rec}} = (u + c)^2 + u^2$ with $c^2 \approx 2813$ puts the encoder at $u = -c/2$, giving $l_{\text{rec}} = c^2 / 4 = 2813/4 = \mathbf{703}$ — matching step 19's **`681`**, after which `rec` (`~10`) and `img` (`~11`) track each other symmetrically down as $c$ shrinks.
   - **Adam defeats `clip_grad_norm_(params, 1.0)` (`forecast2.py:55, 63`):**
     Global norm clipping multiplies all gradients by a single scalar $s = 1/\|g\|_2$. On step 0, Adam computes $m_1 / (\sqrt{v_1} + \epsilon) = s g / (|s g| + 10^{-8}) \approx \mathrm{sign}(g)$ (typical $|s g_i| \sim 1/\sqrt{2.6\times 10^6} \approx 6\times 10^{-4} \gg 10^{-8}$), so every active parameter takes a **full $\pm 10^{-6}$ $L_\infty$ step** constructively aligned with $d l_{\text{img}}/d\theta$.
   - **Coherent $L_1$ fan-in × 4 weight-tied ticks × $1/\text{sd}$ readout gain:**
     For a linear layer $y = W x$ ($d=256$, $\|x\|_1 \approx 200$), a coherent $-\eta\,\mathrm{sign}(g_y x^\top)$ update shifts each output channel by $\sim d\eta \approx 2\times 10^{-4}$ (and `zoom` has fan-in `768`, `board_swarm.py:241`). `real_board` applies the **same tied cell 4 times** (8 blocks deep), accumulating a coherent $\sim 10^{-3}$ shift per board coordinate ($\|\Delta z\|_2 \sim 0.1\text{–}0.4$ over 16,384 dims) aligned *precisely* with $W_p$'s top-gain ($1/\text{sd}$) direction — enough to move $\mathrm{RMSE}(RT(st))$ by $\sim 0.26$ ($\mathrm{MSE} = 0.066$) at $\eta = 10^{-6}$, and by $190\times$ cumulative lr over steps 0–18 straight into the `681` trough.
   - **Secondary amplifiers in the code:**
     - **Hard top-2 MoE routing flips (`board_swarm.py:191`):** `real_board` makes $64 \text{ rows} \times 2 \text{ blocks} \times 4 \text{ ticks} = 512$ top-2-of-16 decisions per frame. Even a $\sim 10^{-3}$ logit shift flips tokens near a 2nd/3rd expert tie discontinuously by $O(w_2 (E_{\text{new}} - E_{\text{old}}))$, cascading across subsequent ticks and getting amplified by $W_p$. (This adds step-1 fragility, though the smooth climb to $2813/4 \approx 681$ and symmetric decay to $10 \approx 11$ shows the continuous attached-`st` / `l_img`-dominated drift is the dominant driver.)
     - **`W.rms_level = lambda t: t / SCALE` (`forecast2.py:6`, `wm_fit.py:39`):** multiplies `reader`/`pos` perturbations by $1/0.20386 \approx 4.9\times$ right before `tanh(16 * x)` in `zoom` (`board_swarm.py:319`, up to $\sim 78\times$ slope near zero) and removes scale invariance during training. However, `ctx_norm` (`RMSNorm`, `board_swarm.py:168`) immediately follows `zoom`, so this is a ~5× amplifier on the input path (and a later saturation-drift risk), not the root cause of the `681` blowup.
     - **Broken `l_row` scaling (`forecast2.py:51, 60`):** `ROWSD = float(Z[:3500].std())` is the *global* std across both samples and features — dominated by constant `init_rows` (`std=0.5`), not per-coordinate `sd`! So `0.1 * ((o.next_rows - nxt)**2).mean() / ROWSD**2` is ~100–1000× too weak on low-`sd` slow rows and cannot hold `o.next_rows` near `nxt`.

---

### 3. Smallest fix before the scored run (all in `forecast2.py`; trunk stays shared, `board_swarm.py` untouched)

1. **Detach the start board going into `imagine` (`forecast2.py:59`):**
   ```python
   st_n = dataclasses.replace(st, rows=st.rows.detach() + NOISE * st.rows.detach().std(0, keepdim=True) * torch.randn_like(st.rows))
   ```
   Stops `l_img` from backpropagating through the `o.next_rows = st_n.rows + delta` skip connection to wreck `real_board`.

2. **Standardize `l_row` per coordinate with `sd` (not global `ROWSD`) and ramp `l_img` in only after `imagine` lands on the real-board manifold (`forecast2.py:50-51, 55-64`):**
   - In `fit_readout()`, save per-coordinate `SD = torch.tensor(sd, dtype=torch.float32, device=dev).view(1, 1, m.R, m.D)` alongside `Wp, bp`.
   - Replace `l_row` with `l_row = (((o.next_rows - nxt) / SD) ** 2).mean()`.
   - **Prevent step-0 OOD shock on the shared trunk:**
     - **First ~100 steps (board-space alignment + strong `l_rec` anchor):** train with `l_img` weight `0` (or ramp `w_img` from `0 -> 1` over steps `100..250`, or use Huber `F.smooth_l1_loss(RT(o.next_rows[:,0]), xn, beta=0.1)`), using `loss = w_img * l_img + 10.0 * l_rec + 1.0 * l_row + 0.01 * o.aux_loss` — and optionally freeze everything except imagination-only params (`m.action_emb`, `m.cell.action_in`, `m.cell.action_pos`) for the first ~50 steps so `imagine`'s initial OOD shock is absorbed before touching shared trunk weights.
     - Keep `l_rec` weighted up (e.g. `10.0 * l_rec`, or dynamically balance against `l_img`) so `l_img` never outvotes `l_rec` by orders of magnitude on the shared trunk.
   - **Reset Adam moments when `fit_readout()` refits (`forecast2.py:64`):** after refitting `Wp, bp` at steps 250, 500, ..., clear `opt.state.clear()` (and briefly re-warmup lr for ~20 steps) so stale Adam momentum from the previous `Wp` doesn't kick the trunk at full `lr=1e-4`. (Keep `W.rms_level = lambda t: t / SCALE` since `run_recon_ridge/model.pt` was trained with it, or use a lower LR on `m.reader`/`m.pos` so they don't drift out of `SCALE`.)

3. **Fix the verdict marks (`forecast2.py:107-114`) to match `wm_fit.py`:**
   - Compute `worlds_both = sum(a >= 1.25 and b >= 1.10 for a, b in zip(k1["shuffle_world_ratios"], k5["shuffle_world_ratios"]))` (keyed by world id) and gate `PASS` on `worlds_both >= 12`.
   - Compute and gate on `W.pcs90(pred_change) >= 0.5 * W.pcs90(real_change)`.
   - Gate `PASS` on `k1["ceiling_real_board_E_over_B"] <= 0.70` and force `FAIL` if `> 0.95`.
   - Delete dead `imagine` (`forecast2.py:20-24`) and unused `Dec`/`dec` (`forecast2.py:8-14`).

*(Quick diagnostic to log on step 0 before launching: print `||Wp||_F`, `sd.min()/median()`, and step-0 `l_img` with `NOISE=0` vs `NOISE=0.2` — you should see `l_img` is already `~2800` at `NOISE=0`, confirming the OOD `_imagine_impl` step is the sole driver.)*
