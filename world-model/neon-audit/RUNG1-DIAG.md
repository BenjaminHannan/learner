# PROBLEM-7 Rung-1 / Rank-3 Failure Diagnosis (`run_r1_bundle`)

**Date:** 2026-11-24  
**Scope:** Read-only CPU X-ray of M3 saved Rung-1 Arm 1 (`bundle`) checkpoint [`model.pt`](file://<m3-project>/PROBLEM-7/wm5/run_r1_bundle/model.pt) (`sha256: 404642fb8d315da1...`), [`forecasts_dev.npz`](file://<m3-project>/PROBLEM-7/wm5/run_r1_bundle/forecasts_dev.npz), [`score_dev.json`](file://<project>/PROBLEM-7/forecast5/run_r1_bundle/score_dev.json) (`sha256: 4338767ce8d22320...`), and M3 `run_r1_bundle.log`.  
**Constraints respected:** CPU only, zero training, zero MPS, lock never touched, `sealed_test.npz` never opened, zero edits outside `neon-audit/`.  
**Raw probe script & logs:** [run_rung1_diag.py](file://<project>/PROBLEM-7/neon-audit/run_rung1_diag.py), [rung1_diag_stdout.log](file://<project>/PROBLEM-7/neon-audit/rung1_diag_stdout.log), [rung1_diag_part2.log](file://<project>/PROBLEM-7/neon-audit/rung1_diag_part2.log), [rung1_diag_part2b.log](file://<project>/PROBLEM-7/neon-audit/rung1_diag_part2b.log).  
**Scale note (`shown`):** Everything below is `P7toy` (`R = 64` rows: 24 slow + 40 fast, board width `D = 256`, trunk width `d = 192`, 2 MoE blocks × 16 experts, `2.47M` active cell / `9.58M` total params) on `16×16` Crafter frames — **not** `~50M`/`~500M` and **not** 3D Minecraft. *(Note: a print-format typo in `rung1_diag_stdout.log` and `rung1_diag_part2.log` labeled `real_board` as `64x192`; the actual tensor width probed in all scripts is `D = 256` (`64×256`) and `hn_img` is `d = 192` (`64×192`), confirmed by `dec_total = 3,025,440`.)*

---

## 1. Executive Verdict — Answers to All 4 Diagnostic Questions

| Question | Verdict | Root-Cause Status | Decisive Evidence (`shown` unless noted) |
|---|---|---|---|
| **Q1. Is it underfitting (even on train, `img/copy 0.82`)?** | **YES — selective *spatial* underfitting, NOT overfitting or general capacity failure** | **Symptom (`shown`)** | `TRAIN ≈ DEV` across every metric (`img_res/copy`: `0.893` train vs `0.909` dev; board delta `R² = -0.032` train / `-0.036` dev; open-move `alpha` med `0.037` train / `0.042` dev, max `0.27 < 0.40`). **Smoking gun:** on non-spatial global dimming (`act=6 sleep`), the exact same model gets **`E/copy = 0.360` train / `0.363` dev** (`std_ratio = 0.617`), whereas on 2D moves (`act=1..4`) it stalls at **`0.919–0.941`** with `4–6×` over-globalized brightness drift. |
| **Q2. Does the decoder or 64-row board lack a spatial-shift path?** | **YES — the 64-row board + 2-block trunk lack a 2D spatial-shift path** *(plus secondary decoder under-convergence)* | **PRIMARY WALL (`shown`)** | Un-choking (`K1`) fixed seeing (`burial 3,054:1 → 3.49:1`; fresh Ridge on `real_board(t+1)` gets `res/copy = 0.161` and **`block_open mean_err = 0.0042` (`99.6%`)**). **BUT** the 64 rows store pixels as a **1D global holographic soup** (every row predicts all 16 `4×4` patches nearly equally: localization ratio `max/mean = 1.14`, max `1.23` vs `1.0` soup / `16.0` specialist), and Block-0 imagine self-attention is near-uniform (`entropy = 3.902 / 4.174 = 93.5%` of max). Apples-to-apples per-action Ridge (`N=6,000` train, moves `1..4`) degrades monotonically: **raw pixels `0.473` → `real_board(t)` `0.584` → post-trunk `hn_img` `0.689` → full model `0.931`**. Trained `RowLNDecoder` adds secondary blur (`2.5×` worse MSE than Ridge on `real_board`), but is NOT primary (`ceil_res` still separates open/blocked `0.528 vs 0.001`; `imagine` outputs `0.042`). |
| **Q3. Is the residual loss pulling toward zero change?** | **NO math bug in `l_img_res`; YES severe early gradient starvation + MSE uncertainty shrinkage** | **CONTRIBUTING (`shown`)** | `l_img_res` has exact minimum at `x_{t+1} - x_t`, aligns with `l_img_abs` (`cos = +0.844` cell / `+0.855` dec), and let `sleep` hit `E/copy = 0.363`. **However**, at step 0 `l_rec` (`65×`) and `0.005*l_row_rel` (`35×`) drowned `l_img_res` on `cell` (`|g|: 0.414` and `0.225` vs `0.0064`), keeping `img/copy` flat at `0.97–1.01` for 1,750/3,000 steps; even at step 3,000 `l_rec` is `3.0×` larger and slightly opposes `l_img_res` on `dec` (`cos = -0.215`). Under spatial uncertainty on moves, MSE then shrinks predictions toward zero (`pred_rms/true_rms ≈ 0.20`, `fb = 1.00`). Training longer alone cannot fix the `0.689` post-trunk wall. |
| **Q4. Is the action still not reaching the cells (`shuffle 1.15`)?** | **NO — action reached all 64 cells LOUDLY (`K2` worked!)** | **RULED OUT (`shown`)** | `act_film` is strong (`|W| = 3.69`, `tanh(γ)` rms `0.573`, `β` rms `0.591`); `action_emb` cos `0.030`, `enc_act` cos `0.153` (vs Step-6 `0.809`); `g_slow_imagine` mean `0.617` (vs Step-6 `0.094`); all `32/32` MoE block-expert slots active with `L1(L vs R) = 0.798`. Inside the cell, `eff_delta` bilinear ratio is **`0.497` (`2,000×` stronger than Step-6's `0.00025`!)**. `shuf k1 = 1.152` (`0/16`) vs `k5 = 1.240` (`16/16`) happens because the trunk emits a low-rank (`13`-PC) directional tint/drift (`MODEL` `act_add = 0.0073` matches `SOS` `0.0077`, while `bilinear = 0.0115` is `4.1×` weaker than `SOS` `0.0473`), which compounds over 5 steps without shifting terrain. |

**One-line diagnosis (`shown`):** Un-choking (`K1`) and the FiLM action intercom (`K2`) **both worked as designed** — the board sees clearly (`burial 3.49:1`, `99.6%` linear Ridge block/open ceiling) and hears the button loudly (`2,000×` stronger bilinear action×screen interaction, `E/copy = 0.363` on `sleep`). The remaining wall is **geometric**: a 1D unstructured 64-row holographic attention whiteboard has no 2D spatial-shift path, so its 2-block trunk smears spatial terrain (`0.473 → 0.584 → 0.689`) and collapses 2D moves into a small 13-PC global/low-rank blur (`alpha = 0.042`, `fb = 1.00`).

---

## 2. Detailed Evidence From Saved Artifacts

### 2.1 Q1 — Train vs. Dev Parity & The `sleep` vs. `moves` Smoking Gun (`shown`)

From [rung1_diag_stdout.log](file://<project>/PROBLEM-7/neon-audit/rung1_diag_stdout.log) (2,048 sampled train windows from `train_dn.npz` vs. 2,048 dev windows from `heldout.npz`, plus full dev [`score_dev.json`](file://<project>/PROBLEM-7/forecast5/run_r1_bundle/score_dev.json)):

| Metric | `TRAIN_2048` | `DEV_2048` | Full Dev (`5,008`) | Interpretation |
|---|---:|---:|---:|---|
| `rec_mse` (`rmse`) | `0.001540` (`0.0392`) | `0.002029` (`0.0450`) | — | Mild gen gap on decoder; seeing works |
| `img_res / copy` (`E/B`) | `0.8928` | `0.9087` | `0.9013` (`E/B = 0.9528`) | **Train ≈ Dev** → pure underfitting |
| `img_abs / copy` (`E/B`) | `0.9263` | `1.0002` | (`diag E/B = 1.0426`) | Absolute decode no better than copy |
| `ceil_abs / copy` | `0.3894` | `0.4642` | (`E/B = 0.4782`) | Passes `<= 0.70`, still blurrier than Ridge |
| `ceil_res / copy` | `0.3784` | `0.4145` | (`E/B = 0.4352`) | Same; `open_al_med = 0.528` vs `blkd = 0.001` |
| Board burial (`all / slow / fast`) | `3.60 / 2.19 / 4.02` | `3.48 / 2.11 / 3.89` | `3.49` | `K1` fixed `3,054:1` burial cleanly (`875×` drop) |
| **Board delta `R²` (`all / slow / fast`)** | **`-0.0317` (`-0.031 / -0.032`)** | **`-0.0364` (`-0.029 / -0.040`)** | — | Imagined board deltas barely align with real (`cos = +0.027 / +0.022`) |
| Pred `alpha` on `TRUE_OPEN` (med / p90 / max) | `0.0371 / 0.1237 / 0.2639` | `0.0421 / 0.1334 / 0.2717` | `fb = 1.0000` | **Never crosses `0.40` even on training set** |
| Pred `alpha` on `TRUE_BLKD` (med / p90 / max) | `0.0237 / 0.0910 / 0.1706` | `0.0265 / 0.0960 / 0.1673` | `fo = 0.0000` | Faint gap (`0.054` vs `0.036` mean), 10× too small |

**Per-action split (`TRAIN_2048` / `DEV_2048`, `rung1_diag_stdout.log:19-50`) — the decisive smoking gun:**

| Action | `TRAIN` `E/copy` | `DEV` `E/copy` | `DEV` `std_ratio` (full dev) | `global_brightness_frac` (`pred` vs `true`, dev) | `screen_blind_const_frac` (`pred`, dev) |
|---|---:|---:|---:|---:|---:|
| **`6` (`sleep` — global dimming, non-spatial)** | **`0.3602`** | **`0.3633`** | **`0.577`** (**`0.617`**) | **`0.68` vs `0.66`** | `0.76` |
| `1` (`move_left` — 2D spatial shift) | `0.9332` | `0.9283` | `0.205` (`0.207`) | `0.22` vs `0.06` (`3.7×` too global) | `0.33` |
| `2` (`move_right` — 2D spatial shift) | `0.9188` | `0.9241` | `0.215` (`0.215`) | `0.19` vs `0.05` (`3.8×` too global) | `0.27` |
| `3` (`move_up` — 2D spatial shift) | `0.9365` | `0.9411` | `0.198` (`0.197`) | `0.30` vs `0.07` (`4.3×` too global) | `0.27` |
| `4` (`move_down` — 2D spatial shift) | `0.9250` | `0.9333` | `0.192` (`0.191`) | `0.32` vs `0.07` (`4.6×` too global) | `0.20` |
| `5` (`do` — local interaction) | `1.0178` | `1.0198` | `0.203` (`0.191`) | `0.15` vs `0.35` | `0.38` |
| `0` (`noop`) | `1.3593` | `2.8334` | `1.354` (`0.790`) | `0.15` vs `0.09` | `0.25` |

- Across `k = 1 / 3 / 5` in saved `forecasts_dev.npz` ([rung1_diag_part2b.log](file://<project>/PROBLEM-7/neon-audit/rung1_diag_part2b.log)): `E/copy = 0.9013 / 0.8248 / 0.7895` (`E/B = 0.9528 / 0.9451 / 0.9577`), `pred_rms/true_rms = 0.254 / 0.373 / 0.456`, and `global_brightness_frac(pred) = 0.40 / 0.34 / 0.33` vs. `true = 0.10 / 0.15 / 0.19`.
- Spatial regions on moves `1..4` (`DEV_2048`): interior terrain `0.9153`, top border `0.9392`, bottom terrain `0.9494`, player sprite `0.8724`, HUD `1.0829` — **zero localized tile shifting anywhere on the frame**.

---

### 2.2 Q2 — Board Capacity, 1D Holographic Soup & Trunk Spatial Erosion (`shown`)

**A. Seeing works — the screen IS in `real_board(t)` (Probe 2A, `rung1_diag_stdout.log:52-57`):**

| Representation → `x_t` (or `x_{t+1}` ceiling) | `DEV` `MSE` | `RMSE` | `/ copy` | `block_open` (`fb / fo / mean_err`) |
|---|---:|---:|---:|---|
| `patch0` (`16×256` before `BoardCell`, Ridge) | `0.000000` | `0.0002` | `0.0000` | — (lossless input!) |
| `real_board(t)` (`64×256`, fresh Ridge `λ=100`) | `0.000802` | `0.0283` | `0.1820` | — |
| `real_board(t+1)` via fresh Ridge (`λ=10`, ceiling) | — | — | `abs 0.1861` / **`res 0.1607`** | **`0.0055 / 0.0030 / 0.0042` (`99.6%`!)** |
| `RowLN-32` bottleneck (`64×32`, fresh Ridge `λ=10`) | `0.001016` | `0.0319` | `0.2306` | — |
| **Trained `RowLNDecoder` (`model.dec`)** | **`0.002029`** | **`0.0450`** | **`0.4603`** | `ceil_res: 0.3110 / 0.0000 / 0.1555` (`open_al=0.528`) |

- **Takeaway on `RowLNDecoder`:** The trained decoder is `2.5×` blurrier than linear Ridge on the exact same `real_board` (still under-converged at step 3,000), degrading `ceil_res` `fb` from `0.0055` to `0.3110`. **However, this is strictly secondary:** `ceil_res` still produces `open_al_med = 0.5281` vs. `blkd_al_med = 0.0009` (a clean separation), whereas `imagine` fails inside the board (`board delta R² = -0.0364`) and produces `open_al_med = 0.0421` (`12.5×` smaller).

**B. Why the 64-row board cannot shift 2D images (`rung1_diag_part2.log` & `rung1_diag_part2b.log`):**

1. **Row Spatial Locality Probe (64 board rows × 16 `4×4` patches, `rung1_diag_part2b.log:1-5`):**
   - Per-row `max_patch R²`: `mean = 0.967` (`min = 0.943, max = 0.986`).
   - Per-row `mean_all_16 R²`: `mean = 0.849` (`min = 0.783, max = 0.884`).
   - **Localization ratio (`max / mean`): `mean = 1.14`, `max = 1.23`** (`1.0` = pure global soup; `16.0` = 1-patch specialist; slow rows `1.17`, fast rows `1.12`).
   - Every one of the 64 board rows is a **global holographic mixture of all 16 patches** — there is zero 2D spatial layout across rows.
2. **Block-0 Imagine Self-Attention is Near-Uniform Soup (`rung1_diag_stdout.log:77-79`):**
   - Average attention over 64 board rows (`65` keys: `64` board + `1` action): **`entropy = 3.902` vs. uniform max `ln(65) = 4.174` (`93.5%` of uniform!)**, `self_diag = 0.0136` (`≈ 1/65 = 0.0154`), `to_action_row = 0.1473`, `cross_board_rows = 0.8391`, `mean L1 attn shift (L vs R) = 0.3168 / 2.0`.
   - Inside `_trunk`, `screen` RMS collapses **`9.3×`** (`0.306 → 0.0328`) and `screen × action` bilinear RMS collapses **`5.2×`** (`0.131 → 0.0252`).
3. **Apples-to-Apples Trunk Spatial Erosion Waterfall (Per-Action Ridge, `N = 6,000` train → `N = 2,048` dev, moves `1..4`, `rung1_diag_part2.log:1-6`):**

| Stage in Pipeline | Moves `1..4` `E/copy` (optimal per-action Ridge) | `block_open` (`fb / fo / mean_err`) | What Changed |
|---|---:|---|---|
| **Raw pixels `x_t` (`768d`)** | **`0.4734`** (`λ=1`) | `0.012 / 0.951 / 0.482` | Clean 2D pixel coordinates (linear shift baseline) |
| **`real_board(t)` (`64×256`)** | **`0.5837`** (`λ=500`) | `0.177 / 0.518 / 0.347` | **`+0.110` erosion** encoding 2D screen into 1D global soup |
| **`hn_img` AFTER 1-tick `_trunk` (`64×192`)** | **`0.6894`** (`λ=10`) *(std: `0.7081`)* | `0.708 / 0.087 / 0.398` | **`+0.106` FURTHER erosion** inside 2-block uniform-attn trunk! |
| **Trained `imagine_step` + `RowLNDecoder`** | **`0.931`** (mean moves `1..4`) | `1.000 / 0.000 / 0.500` | Full trained readout (`board_dR² = -0.036`) |

Even an **oracle closed-form per-action linear matrix** fitted directly on the trunk's own post-FiLM hidden state `hn_img` cannot beat **`0.6894`** on moves (worse than raw pixels `0.4734` by `+0.216` and `2.4×` worse than `shift_or_stay` `0.2853`!).

---

### 2.3 Q3 — Residual Loss, Early Gradient Starvation & MSE Shrinkage (`shown`)

From [rung1_diag_stdout.log](file://<project>/PROBLEM-7/neon-audit/rung1_diag_stdout.log) lines 85–101 (single batch, zero optimizer updates) and M3 `run_r1_bundle.log`:

| Loss Term (Weighted) | Step 0 Value | Step 0 `\|grad_cell\|` | Step 0 `\|grad_dec\|` | Step 3,000 Value | Step 3,000 `\|grad_cell\|` | Step 3,000 `\|grad_dec\|` |
|---|---:|---:|---:|---:|---:|---:|
| **`1.0 * l_rec`** | `0.331436` | **`0.41360`** (`65×` > img_res) | **`1.37521`** (`18×`) | `0.003124` | **`0.01197`** (`3.0×` > img_res) | `0.01950` |
| **`1.0 * l_img_res`** | `0.005763` | **`0.00640`** | `0.07454` | `0.004106` | **`0.00396`** | `0.01906` |
| `0.25 * l_img_abs` | `0.052244` | `0.01551` | `0.21954` | `0.001096` | `0.00110` | `0.00574` |
| **`0.005 * l_row_rel`** | `0.242030` | **`0.22497`** (`35×` > img_res) | `0.00000` | `0.001696` | `0.00131` | `0.00000` |

- **Gradient cosines (`shown`):**
  - `cos(l_img_res, l_img_abs)` = `+0.1157` (step 0) → **`+0.8443` (cell) / `+0.8550` (dec)** at step 3,000 → `l_img_res` does **not** pull toward zero; it points in the exact same direction as `l_img_abs`.
  - `cos(l_rec, l_img_res)` at step 3,000 = `-0.0335` (cell) and **`-0.2149` (dec)** → mild decoder tug-of-war.
- **Training trajectory (`run_r1_bundle.log`, `shown`):** Because `l_rec` and `0.005*l_row_rel` (`row_rel = 48.4` at step 0, exactly as HungerG Red-Team #3 predicted!) dominated trunk gradients by `35–65×`, `img/copy` stayed completely flat at **`0.97–1.01`** through **step 1,749** (`rec`: `0.331 → 0.0054`) and only started dropping (`0.88 → 0.80–0.82`) in the last 1,000 steps as cosine LR decayed.
- **Why training longer or fixing loss weights is NOT enough (`shown`):** Even after 3,000 steps, `sleep` reached `0.363` under this exact loss, while post-trunk `hn_img` optimal Ridge on moves is stuck at **`0.6894`** — confirming loss starvation delayed learning, while the 1D spatial architecture set the hard ceiling.

---

### 2.4 Q4 — Action Delivery & 256×5 Bilinear ANOVA (`shown`)

From [rung1_diag_stdout.log](file://<project>/PROBLEM-7/neon-audit/rung1_diag_stdout.log) lines 67–83 (256 dev screens × 5 actions `0..4`, exact ANOVA decomposition `T = static + screen + act_add + bilinear`):

| Tensor / Output | `static` | `screen` | `act_add` (screen-blind) | `bilinear` (`screen × action`) | `bilinear / act_add` |
|---|---:|---:|---:|---:|---:|
| `h_pre` (before `act_film`) | `2.3797` | `0.60795` | `0.00000` | `0.00000` | `0.000` |
| **`h_after_film`** | `1.7339` | `0.30608` | **`0.49431`** | **`0.13136`** | `0.266` |
| `hn_board` (after `_trunk`) | `0.9865` | `0.03278` *(9.3× drop!)* | `0.06191` | `0.02517` *(5.2× drop!)* | `0.406` |
| **`eff_delta` (all rows)** | `0.0958` | `0.04565` | `0.08091` | **`0.04024`** | **`0.497`** *(Step-6: `0.00025`!)* |
| `eff_delta_SLOW` / `FAST` | `0.0785 / 0.1048` | `0.03947 / 0.04899` | `0.06038 / 0.09104` | `0.03546 / 0.04286` | `0.587 / 0.471` |
| **`MODEL px_delta`** | `0.0016` | **`0.00652`** | **`0.00731`** | **`0.01151`** | **`1.573`** |
| **`SOS_BASELINE px_delta`** | `0.0036` | **`0.04053`** | **`0.00771`** | **`0.04729`** | **`6.134`** |

- **Action delivery health (`shown`):** `act_film` `|W| = 3.6852`, `tanh(γ)` rms `0.5729` (`act_std = 0.1891`), `β` rms `0.5909` (`act_std = 0.3760`); `action_emb` mean cos `0.0299`; `enc_act` mean cos `0.1532` (vs. Step-6 `0.809`); `g_slow_imagine` mean `0.6165` (`std = 0.1878`, min `0.1897`, max `0.9809`, vs. Step-6 `0.0942`); MoE experts `32/32` block-expert slots active (`1.9%–4.7%`), `L1(left vs right) = 0.7982`.
- **Exact explanation of `shuf k1 = 1.152` (`0/16`) & `shuf k5 = 1.240` (`16/16`):** The model matched `SOS`'s screen-blind action tint (`0.00731` vs `0.00771`), learned `sleep` (`0.363`), and learned a `13`-PC low-rank bilinear drift (`0.01151`, **`4.1×` weaker** than `SOS`'s `0.04729`). At `k=1` every world falls in `1.098–1.212` (just under `1.25`), while over 5 steps that tint/drift compounds (`pred_rms/true_rms: 0.254 → 0.373 → 0.456`), pushing all `16/16` worlds over `1.10` (`1.133–1.374`) without shifting tiles (`pcs = 13/111`, `fb = 1.00`).

---

## 3. Fork Decision & ONE Recommended Next Step

### Why We REJECT `64×64` Patches on `BoardCell` Right Now (`shown`)
1. **`16×16` resolution is NOT the current wall:** On the exact same `16×16` frames (`train_dn.npz` → dev `1000..1015`), linear `shift_or_stay` ALREADY gets `E/B = 0.2853 / 0.4068 / 0.4977` and `block_open mean_err = 0.0879` (`91.2%`); a zero-training quadratic `6×6` crop cuts further to **`0.2804`** and **`0.0843`** (`rung1_diag_part2b.log:8`); and linear Ridge on `real_board(t+1)` gets **`res/copy = 0.1607`** and **`block_open mean_err = 0.0042` (`99.6%`)**.
2. **More patches will NOT give `BoardCell` a 2D spatial-shift path:** `BoardCell` already received 16 lossless `4×4` spatial patches (`patch0` MSE `0.000000`) and still melted them into a `1.14`-localization 1D soup with `93.5%`-max-entropy self-attention. Quadrupling tokens (`16 → 64` for `64×64`) slows M3 MPS ~2× while leaving the exact same lack of 2D translation equivariance intact. `64×64` belongs **after** `16×16` passes (Rank 7 in [IDEAS.md](file://<project>/PROBLEM-7/neon-audit/IDEAS.md)).

### RECOMMENDED NEXT STEP: **Rank 6 — Dedicated Compact 2D Spatial Visual World Model (on `16×16` First)**

- **What it is (`100%` learned, zero game rules, strict `k = 1` real transitions, canonical `premonition_core_v2` untouched):**
  - Replace the 1D 64-row whiteboard's pixel-shifting duty with a **compact `~1.5–2.0M`-parameter 2D Spatial Visual World Model** (`forecast6/`, operating at full **`16×16` spatial resolution** — no aggressive spatial downsampling that would blur Crafter's `1.75`-pixel tile shift or `2×2` player sprite):
    1. **Shallow 2D Spatial Encoder:** `Conv3×3` stack (`16×16×3` + 2 fixed normalized `(y, x) ∈ [-1, 1]` `CoordConv` channels → `16×16×64` spatial latent grid `z_t`).
    2. **2D Action-Conditioned Spatial Dynamics (`16×16×64` → `Δz`):** 6 pre-norm `3×3` `ConvResNet` blocks with **Action-FiLM** (`(1 + tanh(γ(a))) * norm(h) + β(a)`) at every block + smooth bounded residual update (`z_{t+1} = z_t + max_delta * tanh(Δz / max_delta)`).
       - **Why this directly defeats the proven wall:** Weight-tied `3×3` convolutions are **natively 2D translation-equivariant** (a single kernel shifts every tile across the entire map simultaneously), and 6 stacked `3×3` blocks give a `13×13` (`±6` px) receptive field around every pixel — plenty to inspect terrain adjacent to the player sprite `[5:7, 7:9]` and decide shift vs. stay while keeping the HUD rows `12..15` stationary via `CoordConv`.
    3. **Shallow 2D Spatial Decoder:** `Conv3×3` stack (`16×16×64` → `16×16×3`), scored open-loop via the exact same `forecast5/scorer.py` residual rule `P_k = x_0 + dec(z_k) - dec(z_0)` (`z_0 = enc(x_0)`, single init at `x_0`, zero peeking at intermediate frames, `wm_grad=False` during planning).
    4. **Clean loss & zero starvation:** `l_rec` on a 2-layer `16×16×64` conv AE drops `< 1e-4` within ~200 steps (no `65×` trunk starvation!), `start z_t.detach()` protects seeing from imagining, and `1.0 * l_img_res + 0.25 * l_img_abs + 0.01 * l_lat_res` trains dynamics cleanly from step 0.
    5. **How it fits the shared brain (`suggested` / `untested`):** Once the visual module passes Rung 1, `BoardSwarm` reads its compact `16×16×64` visual state (pooled to 16 or 64 visual sense tokens) without forcing the 1D reasoning whiteboard to act as a 2D pixel video engine — matching [IDEAS.md](file://<project>/PROBLEM-7/neon-audit/IDEAS.md) Rank 6 and the multi-sense architecture in [WORLD-MODEL-VISION.md](file://<project>/PROBLEM-7/neon-audit/WORLD-MODEL-VISION.md).

- **Cheapest Test *(NOT started — awaiting Lead/Ben approval)*:**
  - **1 single run on M3 MPS** (`forecast6/`, `~1.5M` params, `batch = 64`, `3,000` steps on the exact existing `wm5/data/train_dn.npz`, estimated **`~4–8 min`** wall-clock on M3 MPS under `./withlock.sh`), evaluated on legacy dev `1000..1015` with the **EXACT unchanged [`forecast5/scorer.py`](file://<project>/PROBLEM-7/forecast5/scorer.py)** (`forecast5-v3-rung1`). `sealed_test.npz` stays untouched until a dev winner is selected.
  - *(If Arm 1 scores `PARTIAL` — i.e., `k=1` and `block_open` smash `shift_or_stay` while `k=3/5` drifts under strict `k=1` training — the single clean follow-up knob is Rank 5A: FSQ discrete snapping on `z_t`, still 100% strict `k=1`.)*

- **Fixed Pass Marks (unchanged `forecast5-v3-rung1` dev bars, zero moving goalposts):**
  1. **Beat both baselines (`linear_Mact` & `shift_or_stay`) at ALL of `k = 1, 3, 5`:** dev `E/B < 0.2853 / 0.4068 / 0.4977` (and legacy `<= 0.80 / 0.90 / 0.95`).
  2. **Blocked vs. Open Move Physics Cut (`>= 25%`, neither rate worse):** dev `mean_err <= 0.0659` (`fb <= 0.0207`, `fo <= 0.1552`).
  3. **Action shuffle & anti-collapse:** `k1 shuffle_pooled >= 1.25`, `worlds_k1 >= 12/16`, `worlds_both >= 12/16`, `not proves_wrong`, `ceiling_abs_E_over_B <= 0.70` (expected `< 0.10`), `std_ok == True`, `pcs_ok == True` (`>= 56/111`).

- **Exact Result That Proves Rank 6 Wrong (Stop Trigger):**
  - On `train_dn.npz` → dev `1000..1015` after 3,000 steps, Rank 6 is **PROVED WRONG** on `16×16` if ANY of:
    1. `ceiling_abs_E_over_B > 0.20` (a 2D conv AE failed even to represent `16×16` frames cleanly), OR
    2. `k1 E/B >= 0.2853` (a 2D ConvResNet cannot beat linear `shift_or_stay` at 1 step), OR
    3. `block_open.model.mean_err >= 0.0879` (zero obstacle-physics improvement over a linear `6×6` crop), OR
    4. `k1 shuffle_pooled < 1.25` OR `worlds_k1_shuffle < 12`.
  - **What that failure would prove:** If even a translation-equivariant 2D ConvResNet with `ceiling <= 0.10` cannot beat linear `shift_or_stay` on `16×16`, then **`16×16` downsampling blur / sub-pixel aliasing really IS the bottleneck**, and we immediately escalate to `64×64` frames (still using the 2D spatial module!).

- **Honest Pre-Filed Odds (`untested`):**
  - **Full Rung-1 `PASS`** (`k=1, 3, 5` `< 0.285 / 0.407 / 0.498` + `block_open <= 0.0659` under strict `k=1` training): **`55%`**
  - **`PARTIAL`** (`k=1` + `block_open` PASS cleanly, `k=3` or `k=5` open-loop drifts above `0.407 / 0.498` → clean FSQ follow-up): **`30%`**
  - **`FAIL`** (misses `k=1 < 0.2853` or `block_open <= 0.0659` → triggers `64×64` upgrade): **`15%`**

---

## 4. Plain-English Summary (For Ben)

We opened up the saved Rung-1 brain on the CPU (no training) to find out *why* it still predicted "nothing moves" even after we unplugged its buried signal (`3,054:1 → 3.5:1`).

- **The fixes DID work on seeing and hearing:** The brain can now clearly see the game screen (a quick linear math reader on its memory tells blocked vs. open moves apart with **99.6% accuracy**!), and it **loudly hears which button you pressed** (`2,000×` stronger button signal than Step 6). Even better, on **"sleep"** (where the whole screen just dims at once, no sliding), the brain **nailed it** (`0.36` error vs. copy)!
- **Why walking still failed:** The shared 64-row brain is built like a **1D list of bullet points**, not a **2D map**. Every single one of its 64 notepad rows blends all 16 screen pieces together into one global soup (localization `1.14` vs. `16.0` for a real grid). Asking a bullet-point notepad to slide a 2D picture sideways by 1.75 pixels while checking if a tree is right next to the player is like trying to play Tetris by reading a shuffled paragraph — it can dim the whole room ("sleep"), but when you press "walk left" it just smears a faint tint across the screen (`E/B = 0.95`, predicts "blocked" every time). Also, the "redraw the current picture" loss drowned out the "predict the next picture" loss `65×` at the start, starving dynamics for the first half of training.
- **Our one clear next step (Rank 6 — NOT `64×64` patches yet):** Don't feed `64×64` patches into the same bullet-point brain (`16×16` pictures ALREADY have enough detail for 91%–99.6% obstacle physics, so blurry pictures aren't what blocked us). Instead, give imagination its own tiny **2D picture-shaped visual module** (~1.5M weights, ~5 minutes to test on M3 MPS, 100% learned, same strict 1-step rules and exact same grading ruler) that naturally slides 2D grids and checks neighboring tiles, then hands its clean picture state to the main thinking brain. **Honest odds:** **55% full 5-step PASS**, **30% 1-step + wall-physics PASS (needing a 5-step stabilizer)**, **15% FAIL** (which would prove we really do need sharper `64×64` frames).

**Status:** STOPPED — awaiting Lead / Ben decision. No build started.
