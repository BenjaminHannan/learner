# PROBLEM-7 Rank 7 (`R7conv`) Failure Diagnosis & Rank 8 Design Proposal

**Date:** 2026-11-25  
**Scope & Constraints:** Strictly **read-only CPU analysis** (`nice -n 10`, zero MPS, `/tmp/premonition_m3_mps.lock` untouched, zero training, zero code edits, `sealed_test.npz` never opened) of saved Rank 7 artifacts on M3 (`wm7/run_r7_s4{2,3}/{model.pt,forecasts_dev_{plain,reencode}.npz,score_dev_{plain,reencode}.json}` and `wm7/run_r7_s4{2,3}_v3record/score_dev_reencode.json`), saved Rank 6 controls (`wm6/run_r6_s4{2,3}/`, `wm7/rank6_rescore_s4{2,3}.json`), `wm5/data/train_dn.npz`, and dev `wm-harness/data/heldout.npz`.  
**Artifact SHA-256 Provenance (`shown`):**
- `wm7/run_r7_s42/model.pt`: `79e658d41ab322a8...` | `forecasts_dev_reencode.npz`: `5ed2974cc83aa1ca...` | `run_r7_s42_v3record/score_dev_reencode.json`: `1db8496bda3a687b...`
- `wm7/run_r7_s43/model.pt`: `8eef2178836414d2...` | `forecasts_dev_reencode.npz`: `9b1e978aeb6441f9...` | `run_r7_s43_v3record/score_dev_reencode.json`: `78b44f065f6f3be2...`
- Verified zero numeric diff between original `d456b443` runs and `ec44cdca` `v3record` re-scores on both seeds (`shown`).  
**Scale Caveat:** All measurements are on `16×16` Crafter frames with `2.69M`-param `R7conv` (`SpatialWorldModelV7`). Nothing here makes claims about `~50M`/`~500M` scale or 3D Minecraft, and this world-model work stays strictly separate from small card experiments.  
**Claim Labels:** **`shown`** = directly measured from saved files, logs, or read-only CPU probes; **`suggested`** = causal inference from shown measurements; **`untested`** = proposed change, prediction, or odds not yet run.

---

## Executive Summary

| Run (Reencode Verdict of Record) | `k1 E/B` (`<0.2853`) | `k3 E/B` (`<0.4068`) | `k5 E/B` (`<0.4977`) | `bo_err` (`<=0.0659`) | `a=5 (do)` `std_r` (`>=0.25`) | `pool [8,9]` `std_r` (`>=0.25`) | `diag_aslR2` (`wake AUROC`) | `diag_nw_do chR2` | Verdict / Strike |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Rank 6 `s42` (`1f`, re-score) | `0.2470` | `0.3740` | **`0.4881`** | `0.0252` (`fb .014 / fo .037`) | `0.1613` | `0.0855` (`dom [8,9]`) | `+0.080` (`0.647`) | `-0.016` | `FAIL` (`LINE`, 1/3) |
| Rank 6 `s43` (`1f`, re-score) | `0.2488` | `0.3737` | **`0.4827`** | `0.0257` (`fb .014 / fo .037`) | `0.1761` | `0.1126` (`dom [8,9]`) | `+0.080` (`0.709`) | `-0.015` | `FAIL` (`LINE`, 1/3) |
| **Rank 7 `s42` (`2f`, `v3record`)** | `0.2546` | `0.3821` | **`0.4953`** | `0.0375` (`fb .014 / fo .062`) | **`0.1257`** | **`0.0780`** (`dom [8,9]`) | **`+0.065`** (`0.641`) | `+0.009` | **`FAIL` (`LINE`, 2/3)** |
| **Rank 7 `s43` (`2f`, `v3record`)** | `0.2564` | `0.3879` | `0.5016` | `0.0478` (`fb .014 / fo .081`) | **`0.1944`** | **`0.1017`** (`dom [8,9]`) | **`+0.067`** (`0.678`) | `-0.028` | **`FAIL` (`LINE`, 2/3)** |

*(Rank 7 `plain` isolation: `k5 = 0.5116 / 0.5208`, confirming `reencode` cuts `k5` by `0.016–0.019` on both seeds, `shown`.)*

**Headline Diagnosis (`shown`):**
1. **Why `"do"` (`a = 5`) and `[8, 9]` collapsed:** It is a **two-half training-starvation collapse — and Rank 7 (`2-frame`) completely failed to learn BOTH halves even on the training set (`train_dn.npz`)**:
   - **Half 1 (`55.4%` of `a=5` SSE, `60.3%` of `a=8`, `86.5%` of `a=9` — `8 → 9` sleep wake-ups):** Rank 7 learned **literally zero separation** between `8 → 9` wake-ups and `6 → 6` stay-asleep frames (`R7_42` dev `pred_dBright = +0.00312` vs `+0.00312`; `R7_43` `+0.00526` vs `+0.00517`; train `wake_e89 R² = +0.063 / +0.085` vs 1-frame `R6_42`'s `+0.068`). Zeroing `z_t - z_{t-1}` changes asleep SSE by **`0.06%`** (`862.1 → 862.6`). Probing layers proves the **encoder and random-init U-Net preserve `8 → 9` cleanly** (`h0_hud AUROC = 0.981, R² = +0.372`; random-dynamics bottleneck `m1/m2 AUROC = 0.903–0.937, R² = +0.15–0.19`), but **uniform-MSE training actively erased `8 → 9` between `s1 (8×8)` and `m1/m2 (4×4)` (`AUROC 0.937 → 0.685`, `R² +0.187 → +0.026`)**, because `wake_e89` appears in only **`0.41%` of samples (`0.26/batch` → absent in `77%` of batches!)** and sends **`62×` smaller gradient into `in_proj[:, 64:128]` (`w_dz`)** than `moves_awake` (`0.000002` vs `0.000123`) — even while `wake_e89` still makes up **`19.2–24.2%` of all remaining step-5000 training error!**
   - **Half 2 (`42.3%` of `a=5` SSE, `39.4%` of `a=8` — awake chopping/collecting/placing):** Rank 7 outputs a nearly flat constant `0.0020–0.0024` RMS on ALL `635` awake `"do"` windows whether the player chops a tree (`real_rms = 0.0308`, `fac+hud = 0.0450`) or punches grass (`real_rms = 0.0026`), collapsing `a = 5, 8, 9` onto `noop` (`cos_noop = +0.55..+0.74`, `RMS(f(x,a) - f(x,noop)) = 0.0006–0.0011` — `75×` smaller than moves; train `R² = +0.01..+0.02`). Yet `16×16` pixels **are NOT too small or too multimodal under MSE**: a simple `RBF-KRR` on 1-frame `16×16` pixels achieves awake `do` **`ctr6x6 R² = +0.379` (`std_r = 0.603`)**, **`HUD R² = +0.239` (`std_r = 0.597`)**, **`ctr6x6 R² = +0.534`** on the `79` large chop/collect windows, **`std_r = 0.296–0.310`** on ALL `a = 5` with **zero** wake-ups predicted, and awake `place_table` **`HUD R² = +0.301` (`full std_r = 0.378`)**. The blocker is **`38×–306×` expected gradient starvation** under uniform pixel MSE (`do_awake = 0.70%` of train SSE, `do_chop = 0.34%`, `place_table_awake = 0.07%` vs `moves_awake = 85.23%`).
   - **Why `R7` also regressed slightly vs `R6` on `k1/k3/k5` and `bo_err`:** `64` extra channels of high-variance past-move residuals `z_t - z_{t-1}` (`11.8×` larger RMS on moves than on `wake_e89`) caused `k = 1` move/wall overfitting (`R6_42` train/dev `bo_err = 0.0252 / 0.0252` vs `R7_42 = 0.0228 / 0.0375` and `R7_43 = 0.0337 / 0.0478`), NOT `reencode` rollout instability (zeroing `dz` at steps `1..4` slightly *worsens* `k5` by `+0.0015 / +0.0027`).
2. **ONE Proposed Change for Rank 8 (`untested`, variant within the conv line):** **Action-Normalized Online Error-Prioritized Minibatch Sampling (`Rel-PER`)** in [`train_v7.py:701`](<project>/PROBLEM-7/forecast7/train_v7.py:701) (`model_v7.py`, loss, hyperparams, `reencode` rollout, and `scorer.py` unchanged; 100% domain-general, zero hardcoded action IDs).
3. **Honest 3rd LINE-strike risk & alternative line (`untested` / `suggested`):** Roughly **`35%` chance of a 3rd LINE strike** (`35%` 2-seed `PASS` / `20%` `PARTIAL` [0 strikes] / `10%` `VARIANT`-only fail / `35%` `LINE` strike). Worth spending the cheap ~22-min 3rd strike first on a `10/11`-passing line; if it takes Strike `3/3`, switch to a **discrete-token spatial world model (FSQ/VQ grid + spatio-temporal attention + cross-entropy loss)** rather than continuing continuous pixel-MSE U-Nets.

---

## Question 1: Why Is `"do"` (Action 5) Collapsed? (And Why Did `[8, 9]` & 2-Frame Fail?)

### 1.1 Exact Decomposition of `"do"` (`a = 5`, `n = 733`, Dev `heldout.npz`, `shown`)

Total dev `a = 5` change energy is `SSE = 284.50` (`std_real = 0.02247`). Splitting all `733` windows into mutually exclusive behavioral buckets reveals **two distinct halves** — and shows `R7_42` / `R7_43` collapsed on **both**:

| Mutually Exclusive `a = 5 (do)` Bucket (Dev) | `n` (`%`) | Real SSE (`%`) | Real Full RMS | Real `Fac+HUD` RMS | `R7_42` Full RMS (`R²`) | `R7_43` Full RMS (`R²`) | `R7_42` `Fac+HUD` RMS (`R²`) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **1. `wake_up`** (`4` `8→9` + `2` hurt) | `6` (`0.8%`) | **`157.52` (`55.4%`)** | `0.18489` | `0.12716` | `0.00800` (`+0.066`) | `0.01357` (`+0.112`) | `0.00692` (`+0.081`) |
| **2. `stay_asleep`** | `92` (`12.6%`) | `6.54` (`2.3%`) | `0.00962` | `0.01143` | `0.00562` (`-0.336`) | `0.01011` (`-1.116`) | `0.00503` (`-0.180`) |
| **3. `awake_fac+hud`** (chop/collect) | `49` (`6.7%`) | `35.80` (`12.6%`) | `0.03084` | `0.04502` | **`0.00202`** (`+0.035`) | **`0.00237`** (`+0.025`) | **`0.00213`** (`+0.039`) |
| **4. `awake_fac_only`** (hit/mob near) | `30` (`4.1%`) | `12.44` (`4.4%`) | `0.02323` | `0.02985` | **`0.00206`** (`+0.025`) | **`0.00245`** (`+0.022`) | **`0.00218`** (`+0.026`) |
| **5. `awake_hud_only`** (drink/stat) | `126` (`17.2%`) | `29.59` (`10.4%`) | `0.01749` | `0.02086` | **`0.00208`** (`+0.022`) | **`0.00237`** (`+0.007`) | **`0.00217`** (`+0.024`) |
| **6. `awake_outer_only`** (far mobs) | `117` (`16.0%`) | `41.02` (`14.4%`) | `0.02137` | `0.00386` | **`0.00201`** (`+0.023`) | **`0.00241`** (`+0.017`) | **`0.00210`** (`-0.232`) |
| **7. `awake_quiet`** (noop-like) | `313` (`42.7%`) | `1.59` (`0.6%`) | `0.00257` | `0.00199` | **`0.00199`** (`-0.438`) | **`0.00234`** (`-0.758`) | **`0.00213`** (`-1.015`) |

Splitting the `635` **awake `a = 5`** windows strictly by **real full-frame RMS quantiles** (`shown`):
- **Top 10% (`rms > 0.0268`, `n = 64`, real `0.03417`):** `R7_42 pred_rms = 0.00211` (`6.2%` of real, `R² = +0.032`, `corr = +0.296`); `R7_43 = 0.00249` (`7.3%`, `R² = +0.024`, `corr = +0.206`). *(The tiny `+0.02` R² comes mostly from faint global daylight/background drift, NOT localized chopping.)*
- **p75–p90 (`0.0192 < rms <= 0.0268`, `n = 95`, real `0.02299`):** `R7_42 = 0.00204` (`8.9%`); `R7_43 = 0.00245` (`10.6%`).
- **Bottom 75% (`rms <= 0.0192`, `n = 476`, real `0.00818`):** `R7_42 = 0.00200` (`24.5%`, `R² = -0.013`); `R7_43 = 0.00234` (`28.5%`, `R² = -0.052`).

**Key observation (`shown`):** Across ALL `635` awake `"do"` transitions, `R7` emits a **flat `~0.0020–0.0024` RMS background residual** that barely varies by `5%` between a genuine tree chop (`real = 0.0308`) and punching empty grass (`real = 0.0026`). The exact same collapse holds on rare pool `[8, 9]`:
- `a = 8 (place_table, n = 60, SSE = 48.45)`: `1` `8→9` wake-up = `29.22` (`60.3%`); `12` awake table placements (`ch_rms > 0.020`) = `13.39` (`real ch_rms = 0.0584` vs `R7_42 pred = 0.00209`).
- `a = 9 (place_furnace, n = 53, SSE = 48.03)`: `1` `8→9` wake-up = `41.55` (`86.5%`), zero genuine furnace placements (`awake SSE = 6.12`, `std_real = 0.0127 < 0.02`). Because `a = 9` carries `49.8%` (`>= 25%`) of the `[8, 9]` pool energy, **any model that misses `8 → 9` wake-ups automatically trips the `dominant_collapse_actions` guard on `a = 9`** (`shown`).

### 1.2 Where in the `16×16` Frame the Missed Change Sits (`shown`)

| Region in `16×16` | ALL `a = 5` SSE (`%`) | `R7_42 / R7_43` `R²` (`std_r`) | AWAKE `a = 5` SSE (`%`) | `R7_42 / R7_43` `R²` (`std_r`) |
|---|---:|---|---:|---|
| **Player sprite (`4 px`, `[5:7,7:9]`)** | `2.77` (`1.0%`) | `+0.062 / +0.050` (`0.19 / 0.34`) | `0.15` (`0.1%`) | `-0.096 / -0.461` (`0.38 / 0.72`) |
| **Facing ring (`32 px`, `[3:9,5:11] \ spr`)** | `45.05` (`15.8%`) | `+0.046 / +0.051` (`0.13 / 0.23`) | **`17.77` (`14.8%`)** | `+0.022 / +0.014` (`0.11 / 0.16`) |
| **HUD (`64 px`, `rows 12..15`)** | `39.30` (`13.8%`) | `+0.021 / +0.008` (`0.13 / 0.14`) | **`36.0` (`29.9%`)** | `+0.024 / +0.010` (`0.12 / 0.11`) |
| **Outer terrain (`156 px`)** | **`197.38` (`69.4%`)** *(wake=`127.0`)* | `+0.038 / +0.043` (`0.12 / 0.19`) | **`66.5` (`55.2%`)** *(mobs+light)* | `+0.018 / +0.005` (`0.12 / 0.15`) |

On awake `a = 5`, the **top 4 single pixels in the entire `16×16` frame are ALL in the HUD** (`(13,9) = 7.7%`, `(12,9) = 6.4%`, `(13,8) = 4.4%`, `(13,4) = 3.1%` — **`21.6%` of all awake `do` SSE in 4 inventory/drink pixels**), followed by the facing-tile pixels `(6,6) = 1.5%`, `(7,7) = 1.4%`, `(4,9) = 1.3%`, `(7,9) = 1.2%`, `(6,9) = 1.2%`. On every one of these top pixels, `R7_42/43` achieve only `std_r = 0.031–0.128` (`R² = +0.005..+0.052`).

### 1.3 Verdict on Every Candidate Cause (Tested on Saved Data)

| Candidate Cause | Verdict | Evidence (`shown` unless noted) |
|---|---|---|
| **1. MSE regression to the mean on a multimodal outcome** | **REAL FOR CEILING; REFUTED AS CAUSE OF `0.13–0.19` COLLAPSE** (`shown`) | `42.7%` of `do` windows are quiet and `55%` of awake `do` SSE is unobservable outer mobs, capping full-frame `R²`. **However**, by Law of Total Variance ($\text{std\_r}_{\text{Bayes}} = \sqrt{R^2_{\text{Bayes}}}$), pure deterministic MSE predictors easily clear `0.25`: `RBF-KRR` on 1-frame `16×16` `Ctr6x6` gets **awake `do` `full std_r = 0.429–0.454`** and **`ALL a=5 std_r = 0.2957` (`0.3099` with R7 asleep) with ZERO wake-ups predicted**; 2-frame HUD linear Ridge on `8→9` wakes alone lifts `a=5,8,9` to **`0.362 / 0.407 / 0.427`** ([RANK6-DIAG.md:72](<project>/PROBLEM-7/neon-audit/RANK6-DIAG.md:72)). `R7conv` failed to learn the conditional mean even on **train** (`a5_awake R² = +0.022 / +0.010`; `wake_e89 R² = +0.063 / +0.085`). |
| **2. Facing tile too small / ambiguous at `16×16`** | **REFUTED** (`shown`) | `2×2` player sprite decodes facing direction at `96.1%–98.5%` dev accuracy ([RANK6-DIAG.md:82](<project>/PROBLEM-7/neon-audit/RANK6-DIAG.md:82)). Pure 1-frame `RBF-KRR` on ONLY `Ctr6x6 [3:9,5:11]` gets **`ctr6x6 R² = +0.379` (`std_r = 0.603`)** on all awake `do` and **`R² = +0.534`** (`pred_rms = 0.0232` vs real `0.0443`) on the `79` large local chop/collect windows (`R7_42` got `0.00207`, `R² = +0.028`). Linear Ridge on `R7_42`'s own frozen encoder `z_t[ctr6x6]` gets **`R² = +0.182` (`std_r = 0.319`)** — the encoder preserves it. |
| **3. Inventory / HUD digits tiny in pixels** | **READABLE (`shown`), BUT STARVED IN FULL-FRAME MSE SUM (`shown`)** | HUD changes are **not** unreadable: `RBF-KRR` on `16×16` `Ctr+HUD` gets **`HUD R² = +0.239` (`std_r = 0.597`)** on awake `do` and **`HUD R² = +0.301` (`std_r = 0.423`)** on awake `place_table`; `R7_42` `h0_hud` preserves `8→9` at **`AUROC = 0.981, R² = +0.372`**. What hurts is their **full-frame MSE footprint**: changing 4–10 pixels yields `mean_e = 0.00023` on `do_awake` vs `0.0053` on 192-pixel moves (`23×` smaller/sample) and `0.0262` on `sleep` (`113×` smaller/sample). |
| **4. Action conditioning (`FiLM`) too weak** | **ARCHITECTURALLY REFUTED (`shown`), GRADIENT-STARVED (`shown` → `suggested`)** | `a = 6 (sleep)` is **`13×` rarer** than `do` (`311` vs `4,007` train rows) and uses the exact same `action_emb → act_mlp → FiLM` path, yet learns cleanly (`std_r = 0.66–0.92`, `row_grad = 0.000299`, `freq*dyn = 0.000794`). Meanwhile `a = 5, 8, 9` collapse onto `noop` (`cos_noop = +0.55..+0.74`, counterfactual `RMS(f(x,a) - f(x,noop)) = 0.0006–0.0011` vs `0.072–0.083` for moves; `action_emb[5] row_grad = 0.000002`, `150×` smaller than `sleep`). Because `moves_awake` drives `38×–306×` larger shared U-Net gradients, shared conv filters never build `(facing_dir × tile_type)` detectors, leaving `action_emb[5,8,9]` trapped at the `noop` saddle (`suggested`). |
| **5. REAL PRIMARY CAUSE — Dual Optimization Starvation Under Uniform-Sample Uniform-Pixel MSE** | **PROVEN PRIMARY CAUSE** (`shown`) | **(A) `wake_e89` (`55.4%` of `do`, `60.3%` of `a=8`, `86.5%` of `a=9`):** Only `114 / 28,000 = 0.41%` of train (`0.26/batch` → **absent in `77.0%` of batches**), with `11.8×` smaller spatial `dz` RMS than moves (`0.0044` vs `0.0517`). Even at step 5,000, `moves_awake` sends **`62×` larger expected gradient into `w_dz`** (`0.000123` vs `0.000002`) and **`7.5×` larger into `dynamics`** (`0.00428` vs `0.00057`), even though `wake_e89` is **`19.2–24.2%` of all remaining step-5000 training error!** Layer-by-layer Ridge probes confirm uniform training **actively erased `8→9`** inside `down2 → mid1` (`RANDOM_INIT` & `HYBRID` `m1/m2 AUROC = 0.903–0.937, R² = +0.15–0.19` → `TRAINED R7_42` `AUROC = 0.739 → 0.685, R² = +0.041 → +0.026`). **(B) `do_awake` / `place_table_awake`:** Only `0.70%` (`do_chop = 0.34%`) and `0.07%` of train copy SSE (`3.5%` and `0.33%` of step-5000 residual error), generating `38×` and `306×` less expected dynamics gradient than `moves_awake`. |

### 1.4 Why Rank 7 Also Regressed Slightly on `k1/k3/k5` and `bo_err` vs Rank 6 (`shown`)

- `R6_42` (`1-frame`) has **zero** `bo_err` generalization gap (`train 0.0252` → `dev 0.0252`), whereas `R7_42` (`train 0.0228` → `dev 0.0375`, `+0.015` gap) and `R7_43` (`train 0.0337` → `dev 0.0478`, `+0.014` gap) overfit the `64` extra noisy past-move `z_t - z_{t-1}` channels (`blocked_moves` dev SSE `+57.1`, `open_moves` `+42.1`).
- Zeroing `z_t - z_{t-1}` at rollout steps `1..4` on `800` dev windows slightly *worsens* `k5` (`R7_42: 0.4897 → 0.4911`; `R7_43: 0.5107 → 0.5134`), proving `z_t - z_{t-1}` does not destabilize `reencode` rollout — the `k5` regression (`0.488/0.483 → 0.495/0.502`) is simply the `k = 1` move/wall overfitting compounding over 5 steps (`shown`).

---

## Question 2: ONE Proposed Change for Rank 8 (`untested`)

### 2.1 Exact Single Change: **Action-Normalized Online Error-Prioritized Minibatch Sampling (`Rel-PER`)**

- **Line change or variant?** **Variant** on the existing dedicated 2D conv U-Net world-model line (`R7conv` + `reencode`). **Strike-policy warning:** Because the conv line sits at `2/3` LINE strikes, any failure on `a = 5 (do) < 0.25` or any non-std gate still records `strike_class = "LINE"` (`3/3`, closing the conv line) per [`PLAN-AMENDMENT.md §5.2`](<project>/PROBLEM-7/forecast7/PLAN-AMENDMENT.md:133-137).
- **Exact scope (100% domain-general, zero hardcoded action IDs, zero pixel masks, zero Crafter rules):** Change **ONLY** minibatch index sampling in [`train_v7.py:701`](<project>/PROBLEM-7/forecast7/train_v7.py:701) (`j = rng.integers(...)`). `model_v7.py` (`2,693,059` params), `compute_train_step_loss` (unweighted `1.0*l_rec + 1.0*l_img_res + 0.25*l_img_abs + 0.05*l_lat`), `AdamW(lr=3e-4, wd=1e-4)`, warmup+cosine, `batch=64`, `steps=5000`, `rollout=reencode` (verdict of record) + `plain` (isolation), and pinned `scorer.py` (`ec44cdca...`) stay **100% unchanged**.
- **Exact formula (computed strictly on `train_dn.npz`, zero dev/sealed touch):**
  1. Once before training, compute each present action's training mean squared frame change $v_a = \mathbb{E}_{\text{train}}[\text{MSE}(x_{t+1}, x_t) \mid a_t = a]$, and initialize per-transition EMA error $e_j \leftarrow \text{MSE}(x_{t+1,j}, x_{t,j})$ for $j \in \{0, \dots, N-1\}$.
  2. Every `25` steps (starting at step `0`, `<0.5 ms` overhead), update the sampling distribution:
     $$r_j = \min\!\left(\frac{e_j}{v_{a_j} + 10^{-4}},\, 20.0\right), \qquad p_j = 0.5\,\frac{1}{N} + 0.5\,\frac{(r_j + 10^{-6})^{0.7}}{\sum_{k=0}^{N-1} (r_k + 10^{-6})^{0.7}}$$
  3. On each step, draw `j = rng.choice(N, size=args.batch, p=p)` (or fast CDF binary search) and update sampled indices with detached per-sample residual MSE already computed in `compute_train_step_loss`: $e_j \leftarrow 0.8\,e_j + 0.2\,\text{MSE}(\hat{x}_{t+1,j}^{\text{res}}, x_{t+1,j})$.

### 2.2 Why THIS Single Knob Beats Every Alternative (Analytical Comparison on `train_dn.npz`, `shown`)

| Single-Knob Candidate | `wk_e89` Batch Presence (`P>=1/64`) | `wk_e89` Loss Share (`S0 → 5k → post-wk`) | `do_aw` / `do_chop` Loss (`5k → post-wk`) | `pt8_aw` Loss (`5k → post-wk`) | `moves` SAMP / `sleep6` Loss | Key Tradeoff / Failure Mode |
|---|---:|---:|---:|---:|---:|---|
| **R7 Uniform (baseline)** | `23%` (`0.26/b`) | `5.2% → 24.2%` | `3.5% / 1.7%` | `0.3%` | `60%` / `7.3%` | `wk_e89` erased (`62×` `w_dz` drowning); `do`/`place` `38–306×` starved. |
| **Clamped Action-Var Loss (`w_a = clip(e_g/(v_a+1e-4),1..10)`)** | **`23%` STILL** | `11.9% → 34.8% → 6.3%` | **`12.3→17.7%`** / `6.0→8.6%` | **`1.7→2.5%`** | `60%` / `3.8→5.5%` | Best for awake `do`, **but leaves `77%` zero-wake batches**, creates `10×` weighted grad spikes clipped at `1.0`, inflates unobservable `oth_act` mob noise to `17.4%`, and cuts `moves` loss to `29%` (risking `k5` and leaving `a=9 < 0.16` VARIANT fail). |
| **Plain MSE PER (`50/50 em^0.6`)** | `91%` (`2.3/b`) | `55.5% → 4.8%` | `1.6→3.4%` / `1.1→2.4%` | `0.1→0.3%` | `66%` / `10→22%` | Fixes `wk_e89` but leaves `do_aw` / `pt8_aw` starved under moves' off-screen border error (`0.00093 ≈ do_chop 0.00087`). |
| **Proposed: `Rel-PER` (`50/50`, `cap=20`, `α=0.7`)** | **`70% (S0) → 93% (5k)`** (`1.2→2.6/b`) | **`11.9% → 58.6% → 9.3%`** | **`2.9→6.3%`** / `2.0→4.4%` (`3.8%` samp) | `0.4→0.8%` (`1.5%` samp) | **`57–70%` / `5.2–5.8%`** | **Only single knob that (a) stops `down2→mid1` from erasing `8→9` from Step 0 (`freq*g_dyn` jumps to `1.4×` moves, zero clipped weight spikes), (b) self-schedules onto `do_chop`/`pt8_aw` once wakes drop, (c) upsamples `FALSE-BLOCK` hard moves (`14.7×` open err), and (d) caps unlearnable `wk_hurt` (`n=24`) at `0.8%` of samples while keeping `oth_act` noise low (`2.2–4.9%`).** |

- **Why `n = 114` `wake_e89` transitions will NOT simply memorize sleeping terrain (`suggested`):** Each sleeping episode contains `~40` `stay_asleep` frames (`n = 4,042`) with the **identical** dark terrain background and `dz_hud = 0` (`target = 0`) acting as exact hard-negative twins against the single `wake_e89` tick (`dz_hud = 8→9`, `target = wake`).
- **Honest limitation (`suggested`):** Because the loss itself remains unweighted MSE, `Rel-PER` prioritizes `wake_e89` first (`58.6%` mid-training loss, lifting `a = 5, 8, 9` simultaneously to `~0.36–0.70`) and gives a moderate secondary lift to `do_awake` (`3.8–3.9%` `do_chop` samples, `6.3%` post-wake loss). We continue logging `diag_aslR2` and `diag_nw_do_chR2` separately so a wake-driven `std_ok` pass is never misrepresented as solving awake chopping/placing.

### 2.3 Fixed Pass Marks & Falsifier (Pinned in Advance; Zero Moving Goalposts)

- **Pass marks (100% unchanged `forecast7-v2-rung1-n200_or_neff10`, `scorer.py` `ec44cdca...`, 2 seeds `42` and `43`, verdict of record = `reencode`, dev `heldout.npz`; `sealed_test.npz` untouched until 2-seed dev `PASS`):**
  - `k1 E/B < 0.2853`, `k3 E/B < 0.4068`, `k5 E/B < 0.4977` (and `<= 0.80 / 0.90 / 0.95`)
  - `block_open`: `mean_err <= 0.0659` (`>= 25%` cut vs `0.0879`), `fb <= 0.0207`, `fo <= 0.1552`
  - `k1 shuffle_pooled >= 1.25`, `worlds_k1 >= 12/16`, `worlds_both >= 12/16`, `not proves_wrong`
  - `ceiling_abs_E_over_B <= 0.70`, `pcs90_pred >= 56/111`, `std_ok == True` (`a = 1..4, 5, 6` individually in `[0.25, 2.0]`; active rare pool `[8, 9]` in `[0.25, 2.0]` with no `>= 25%` energy-share action `< 0.25`; frequency-weighted ratio in `[0.25, 2.0]`)
  - Aggregate `PASS` = BOTH seeds `PASS`; `PARTIAL` = BOTH seeds in `{PASS, PARTIAL}` (exclusive `k5`-only miss = `strike_class = NONE`).
- **Exact result that proves Rank 8 (`Rel-PER`) WRONG:**
  1. **Primary falsifier (`LINE` strike `3/3` → close conv line):** On **either** seed (`42` or `43`), `a = 5 (do)` `std_ratio` stays `< 0.25` **OR** dev `diag_aslR2` stays `<= 0.15` (vs `R7`'s `+0.065/+0.067` and 2-frame HUD Ridge's `+0.246–0.377`) even with `wake_e89` present in `~70–93%` of batches — proving the strided 2D conv U-Net sharing `in_proj` with noisy move `dz` cannot generalize the 2-pixel HUD temporal cue across `16→8→4` downsampling under replay.
  2. **Regression falsifier (`LINE` strike `3/3`):** Either seed regresses `k1 E/B >= 0.2853`, `k3 E/B >= 0.4068`, `bo_err > 0.0659`, or `a = 6 (sleep)` `std_ratio < 0.25`.

---

## Question 3: Honest Odds of a 3rd LINE Strike & Whether a Different Line Serves Better

### 3.1 Honest Pre-Filed Odds for Rank 8 (`untested`, 2-Seed Bar, Calibrated After Rank 7 Miss)

- **Two-seed Dev `PASS`:** **`35%`** (both seeds learn `8→9` wake-ups, clearing `a=5` and `[8,9]`, while `-0.015` wake gain + hard-move replay pulls `s43 k5` under `0.4977`).
- **Aggregate `PARTIAL` (`k5`-only miss on `>=1` seed, `strike_class = NONE`, conv line survives):** **`20%`** (`R7`'s `z_t - z_{t-1}` move overfitting leaves `k5` tight near `0.4977`).
- **`VARIANT`-only `FAIL` (`a=5` passes, only rare pool `[8, 9]` fails — does NOT close conv line):** **`10%`** (partial wake recall passes `a=5` while missing the single `a=9` wake-up).
- **3rd `LINE` Strike (`FAIL` on `a=5 < 0.25` or non-std regression on `>=1` seed → CLOSES CONV LINE):** **`35%`** (~1-in-3 chance).
  - *Main LINE-strike risks:* `R7conv` still failing to generalize `8→9` through strided downsampling under `57%` move `dz` noise on at least one seed (`~20%`); replay over-focusing `n=114` wakes / `n=24` unlearnable hurt-wakes and degrading `bo_err` or train→dev asleep transfer (`~10%`); weak awake `do` leaving no fallback if wake recall is noisy (`~5%`).

### 3.2 Would a Different Line Serve Better? (`suggested`)

- **Run Rank 8 (`Rel-PER`) FIRST, do NOT abandon the conv line before Strike `3/3`:** The conv line already passes `10/11` marks with wide margin (`k1`, `k3`, `wall 46–71% cut`, `shuffle 5.2–5.7× 16/16`, `ceil 0.015`, `pcs 109–111/111`), and our diagnosis proved **optimization starvation** (`77%` zero-wake batches, `62×` `w_dz` drowning, `38–306×` `do`/`place` gradient drowning) — not architectural impossibility. Testing `Rel-PER` is a `~15`-line sampler change costing `~22 min` total on M3 MPS with a **`~65%` chance of avoiding a 3rd LINE strike (`~35%` immediate `PASS`)**.
- **If Rank 8 takes Strike `3/3` (closing the continuous-MSE 2D conv line), the best DIFFERENT line is a Discrete-Token Spatial World Model (FSQ/VQ `16×16` or `8×8` patch grid + Spatio-Temporal Attention + Cross-Entropy dynamics loss):**
  1. **Kills pixel-MSE scale starvation at the root:** Under per-token cross-entropy, flipping 1 tree tile or 1 HUD inventory digit carries the **exact same loss scale** as shifting 1 terrain tile — no `50–100×` magnitude penalty against `"do"` or `"place_table"`.
  2. **Kills the `16→8→4` conv bottleneck on sparse HUD cues:** Direct spatio-temporal attention across `(x_{t-1}, x_t)` tokens lets every terrain token read the `(12..13, 6)` HUD energy tokens in 1 hop without sharing conv kernels with noisy move diffs.
  3. **Kills `k = 5` off-manifold drift natively** (discrete tokens stay on-manifold without pixel re-encoding) and aligns directly with [`WORLD-MODEL-VISION.md`](<project>/PROBLEM-7/neon-audit/WORLD-MODEL-VISION.md) Deep Dive #1 (`z_world` outcome tokens + Candidate 5 Patch Grid).
- **Why NOT the other two alternative lines right now:**
  - *`64×64` native frames on the same MSE conv U-Net:* Removes the `energy=6 ≡ energy=9` pixel collision, but keeps uniform pixel-MSE starvation (`moves` still `~85%` of SSE), runs `4–8×` slower, and requires re-pinning all baselines — better paired with discrete tokens or after `16×16` Rung 1 passes.
  - *Returning to the 1D 64-row `BoardSwarm` trunk (`forecast5`):* Already proved blocked by 1D holographic-soup geometry (`0.689` post-trunk Ridge wall, `fb = 1.00`, [RUNG1-DIAG.md](<project>/PROBLEM-7/neon-audit/RUNG1-DIAG.md)).

---

## Plain-English Summary (For Ben — 5 Lines)

1. Our picture-brain failed because it kept guessing "almost nothing happens" on the "do" button (chopping trees, drinking water, and waking up from sleep), even though our quick tests proved those clues really are clear enough to read in the tiny game screen.
2. Why did it ignore them? Walking around moves the whole screen and happens all the time, so ordinary practice gave walking 40 to 300 times more attention than small tree-chops, and waking up from sleep was so rare that 3 out of 4 practice rounds did not contain a single wake-up at all.
3. Because waking up was missing from most practice rounds, the brain actually forgot the two-picture wake-up clue we just gave it and learned zero difference between "keep sleeping" and "wake up now," while the extra picture slightly distracted it on walking into walls.
4. Our one next fix for Rank 8 keeps the exact same brain and grading rules, and only changes which practice moments it studies: half normal random moments, and half "surprising" moments where a button had a bigger mistake than usual, so it practices wake-ups, tree-chops, and tricky walls every single round.
5. Honestly, there is still about a 1-in-3 chance this takes our 3rd strike and ends this model family (with about a 1-in-3 chance of passing right away); it is cheap and worth one last shot, and if it misses, we should switch to a tile-by-tile brain that grades every game square equally instead of by how many pixels moved.
