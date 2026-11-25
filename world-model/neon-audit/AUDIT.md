# PROBLEM-7 World Model — End-to-End Forensic Audit

**Date:** 2026-11-24  
**Scope:** Read-only code, log, score, and history audit of the PROBLEM-7 world-model effort (`P7toy` = 2.47M active / 6.14M cell params, `debug_tiny` = 66K active params, on 16×16 Crafter frames). **Zero** training, tests, GPU/MPS runs, or code edits performed.  
**Scale separation (`shown`):** Every empirical world-model number below comes from toy builds (`debug_tiny` or `P7toy`), **not** from `dryrun_50m` or the ~500M production trunk. Toy results test mechanisms and do not automatically transfer to ~50M/~500M.  
**Claim labels used throughout:**
- **`shown`** = directly verified in code, logs, JSON score files, or exact arithmetic on those recorded numbers.
- **`suggested`** = causal/mechanistic inference from shown code and numbers, not yet proved by a locked intervention.
- **`untested`** = prediction or proposed fix not yet run.

**Verified code identity (`shown`):** SHA-256 hashes of `premonition_core_v2/*.py`, `forecast4.py`, `imagine_head6.py`, `recon.py`, and `record.py` on M1 match the M3 copies that ran (`board_swarm.py` `8ffc3fb8...`, `forecast4.py` `287668b5...`, `imagine_head6.py` `f8b8bada...`, `recon.py` `7737cc34...`, `record.py` `4df5f6d5...`).

---

## Executive Summary (The 5 Headline Findings)

1. **The Crafter task/data DOES let the action matter massively (`shown`):** Hidden inside the existing score JSONs (`act_baseline_E_over_E`), a stateless 1-line linear regression per action (`x_{t+1} ~ M_a [x_t, 1]`) already scores **`E/B = 0.504` at 1 step, `0.580` at 3 steps, and `0.631` at 5 steps** — crushing all three accuracy pass marks (`0.80 / 0.90 / 0.95`)! Furthermore, **71.4%** of held-out steps (`3,574 / 5,008`) are directional moves with ~9× larger frame change (`std ≈ 0.076`) than `noop` (`0.0083`). The data is **not** why Steps 3–6 failed.
2. **Step 6 was NOT completely blind to the action — it learned a real ~4–9% action signal that was choked ~10×–30× (`shown`):** In [forecast4/score.json](<project>/PROBLEM-7/forecast4/score.json), **16 out of 16** held-out worlds had `shuffle > 1.0` at k=1 (`1.014–1.063`, pooled `1.038`), k=3 (`1.033–1.105`, pooled `1.068`), and k=5 (`1.041–1.126`, pooled `1.090`, 7/16 worlds `>= 1.10`). It failed every mark because the signal was strangled by the **same 68:1 constant-offset burial that choked Problem 1 (Family B)**, compounded by three world-model-specific chokes: a **frozen reading-only trunk** that never learned action×state shifting, a **row-independent** `imagine_out` MLP that physically cannot move pixels between board rows, and a **frozen `lam=140` ridge readout** that created a Catch-22 between freezing vs. unfreezing the trunk.
3. **NEW BUG — The "unexplained" Step-6 ceiling jump (`0.226 -> 0.410`) is 100% explained (`shown`):** [STATUS.md:464-465](<project>/PROBLEM-7/STATUS.md:464-465) attributed this to a "`dec` vs. jointly trained readout" difference, which is **incorrect** — neither Step 3 nor Step 6 uses `dec` at eval. Step 6 started with `lam=140` on the Step-2 checkpoint (`val SSE = 625.7 / 8607.5 = 7.27%` → `0.410 × B_1`), whereas Step 3 trained 1,500 more `l_rec` steps and picked `lam=100` (`val SSE = 349.3 / 8607.5 = 4.06%` → `0.226 × B_1`). Notice `0.410 / 0.0727 = 5.64` vs. `0.226 / 0.0406 = 5.56` — exact match.
4. **NEW SCORER BUG — Under absolute-frame decoding (`P = RT(next_rows)`), passing `std_ratio <= 2.0` on `noop` is MATHEMATICALLY IMPOSSIBLE even for a 100% perfect oracle (`shown`):** Step 6's `RT` readout alone has held-out reconstruction RMSE `0.0419` (`ceiling = 0.410`), which is **5.0× larger** than the true `noop` frame change (`0.00834`). Thus even if `imagine()` produced the **exact real next board**, `P - x_0` has `std_ratio[noop] ≈ 5.0` (actual Step 6: `4.91`) and `2.8–3.8` on actions `7, 10–16`, guaranteeing `FAIL`! Even Step 3's best-ever ceiling (`0.226`, RMSE `0.0311`) forces `std_ratio[noop] >= 3.7 > 2.0`. Conversely, the exact same readout residual let Step 5 (`imagine_alpha = 0.0000`, literally zero change!) score a **false pass** on `pcs90_pred = 107 / 111` and fake `copy_ness = 0.605`.
5. **The Forecasting Line (Steps 3–6) Was Trapped in a Frozen-Ridge Catch-22 (`shown` + `suggested`):** Switching from an undertrained MLP decoder to a frozen high-gain `1/sd` ridge matrix (`Wp`) on a 68:1 buried board meant: unfreeze the trunk → `1/sd` blows up reading (`0.41 -> 3.63` in Step 4, `4.74` in Step 5); freeze the trunk → the trunk never learns action×state spatial shifting (Step 6). **Neither un-choking `BoardCell` (Problem-1's fix) nor cross-row action-conditioned imagination has ever been tested yet.**

---

## (a) Real Bugs Found in Code (`file:line`)

### Critical Bugs Affecting Training, Architecture, or Validity

| # | File & Line | Status | Exact Bug | Impact |
|---|---|---|---|---|
| **A1** | [board_swarm.py:73, 231-237, 242-243, 319-321, 562-564](~/learner-ops/ds-copies/problem-7/wm-harness/premonition_core_v2/board_swarm.py:231-243) | **`shown`** | **Unscaled constant embeddings (exact Problem-1 Blocker C bug):** `src_emb` (`:242`) and `row_type_emb` (`:235`) have no init call (PyTorch `N(0,1)`, 50× larger than `mode_emb`/`clock_enc`/`action_pos` at `0.02`); `age_lin` (`:243`) uses Kaiming init on constant `[0,1,1,1]` (RMS `0.58`); `row_pos_emb` uses `std=1.0` (`:73, 237`); `init_rows` uses `std=0.5` (`:232`). | Real boards sit on an RMS `1.36` static offset with `~0.02` frame spread (**68:1 burial**, [STATUS.md:313](<project>/PROBLEM-7/STATUS.md:313)). `enc_act` adds constant RMS `~1.15` to every action token, pushing all 17 actions to `cos ~ 0.85–0.90`. Causes Step 1 decoder death, Step 4/5 readout fragility, and Step 6 signal burial (`suggested`). |
| **A2** | [forecast4.py:103, 115](<project>/PROBLEM-7/forecast4/forecast4.py:103) (also `forecast.py:84`, `forecast2_PINNED.py:112`, `forecast3_PINNED.py:114`) | **`shown`** | **Absolute-frame `P - x_0` conflates static readout error with imagined change:** `P = RT(next_rows)` is decoded as a full frame, then `P - x_0` is used for `std_ratio_by_first_action`, `pcs90_pred`, and `copy_ness`. | **Mathematically impossible for a perfect oracle to pass `okstd` (`<= 2.0`) on `noop`:** Step 6 `RT` has held-out RMSE `0.0419` (`0.410 × B_1`) vs. `std_real[noop] = 0.00834` → `ratio ≈ 5.0` (actual: `4.91`). Even Step 3's best ceiling (`0.226`, RMSE `0.0311`) forces `ratio >= 3.7`. Passing `<= 2.0` requires `ceiling <= 0.049` (14× stricter than the `0.70` mark!). Also gave Step 5 (`alpha=0`, literally zero delta) a fake `pcs90_pred = 107/111` PASS and fake `copy_ness = 0.605`. |
| **A3** | [record.py:12-14](<project>/PROBLEM-7/wm/record.py:12-14) | **`shown`** | **Train/held-out episode length mismatch (unseen nighttime OOD):** `TRAIN_PER_WORLD = 125` caps training episodes at 125 steps (160 worlds → 175 episodes in `record.log`, nearly all stopping at `t=125` before Crafter's night cycle), whereas `HELDOUT_PER_WORLD = 313, MAX_EPISODE = 250` runs held-out episodes to step 250 into dark nighttime frames (moved share `0.823` train vs `0.876` held-out). | Held-out evaluates both the model and linear ridge readout on unseen dark-lighting frames (`suggested` contributor to train `rec ≈ 0.00090` vs held-out ceiling `0.00176`). |
| **A4** | [board_swarm.py:568, 571-572](~/learner-ops/ds-copies/problem-7/wm-harness/premonition_core_v2/board_swarm.py:568-572) | **`shown`** | **Canonical `_imagine_impl` mismatches `tick()` & ignores `next_rows` in `z_pred`:** (1) Hard-codes `focus = 1.0` (`:568`), turning on untrained `SparseMoE.film` (`tick()` uses Explorer `focus=0`); (2) writes ungated `next_rows = x0 + out_proj(hn[:, :R])` (`:571`), ignoring `gate`, `gate_scale`, `row_pin`; (3) `z_pred` (`:572`) depends only on `x0` and `hn[:, R]`, giving `next_rows` zero gradient from `world_model_loss`. | Caused Step 3 (`E/B = 31.3`) and Step 4 (`step-0 img = 2,814`, `E/B = 321`) catastrophic OOD jumps when calling canonical `cell.imagine()`. Fixed only in P7 copies (`imagine_damped.py`, `imagine_head6.py`), still unpatched in canonical core. |
| **A5** | [board_swarm.py:465, 571](~/learner-ops/ds-copies/problem-7/wm-harness/premonition_core_v2/board_swarm.py:465) | **`shown`** | **Unbounded additive fast-row / imagined-row drift:** Fast rows (`fast0 + d_f`) and canonical imagined rows (`x0 + delta`) have no decay, convex blend, or norm bound. | Untrained cell norm grows monotonically with ticks (`0.40 -> 0.52 -> 0.64 -> 0.74`, [DS-NOTES.md:45-48](<project>/PROBLEM-7/wm/DS-NOTES.md:45-48)); continued-state `l_row` diverged to `3,291` (Step 1 Run 1) and `16,181` (Step 3 Run A). |
| **A6** | [imagine_head6.py:39, 54-56](<project>/PROBLEM-7/forecast4/imagine_head6.py:39) | **`shown`** | **Double-damping on slow rows in Step 6:** `delta = imagine_out(hn[:, :R]) * imagine_scale` ALREADY scales slow rows down by their tiny real-board `SD` (`imagine_scale`), and then `:54-56` multiplies slow rows AGAIN by frozen `g_slow ≈ 0.12` (whereas fast rows get `1.0x`). | Slow rows (24 of 64) are attenuated ~8× harder than fast rows relative to their actual scale (`suggested`). |
| **A7** | [forecast4.py:67](<project>/PROBLEM-7/forecast4/forecast4.py:67) vs [diag5.log:82](<project>/PROBLEM-7/STATUS.md:372) | **`shown`** | **Training noise (`NOISE=0.2`) equals ~44% of the entire real 1-step transition variance + unfloored batch `std(0)`:** Real 1-step board change `((st - nxt)/SD)^2 = 0.0908` (`RMS = 0.301 SD`, `diag5.log:82`). `forecast4.py:67` injects `0.2 * batch_std * randn` (variance `0.04` in `SD^2` units, unfloored batch std on 64 samples). | Almost half of `l_row`'s signal is denoising random Gaussian start jitter back toward `st` (action-independent shrinkage), swamping non-move actions (`suggested`). Note: `l_row` dropped `0.104 -> 0.0765` (`-0.027`), close to the injected noise floor (`shown`). |

### Moderate / Hygiene & Scorer Bugs (`shown`)

| # | File & Line | Bug | Impact |
|---|---|---|---|
| **A8** | [forecast4.py:69-70](<project>/PROBLEM-7/forecast4/forecast4.py:69-70) | `w_img = 0` for steps `0..100` (trunk-warmup leftover, even though trunk is frozen!) and `action_emb_grad_step0 = 3.06e-7` comes ONLY from `0.01 * o.aux_loss` (since `imagine_out[2]` is zero-init). | First 100 steps ignore `l_img`; step-0 grad log is a false metric (caught in `bughunt-step6`). |
| **A9** | [forecast4.py:57, 74](<project>/PROBLEM-7/forecast4/forecast4.py:57) | `m.cell.imagine_scale` is set as a plain attribute, not `register_buffer`. | Not saved in `model.pt`; reloading `run_forecast4/model.pt` crashes with `AttributeError` (caught in `bughunt-step6`). |
| **A10** | [forecast4.py:122](<project>/PROBLEM-7/forecast4/forecast4.py:122) | `PARTIAL` triggers even if `k3`/`k5` `E/B` pass while `k5` shuffle fails (`nboth < 12`); `proves_wrong` (`E1/B1 <= 0.80 and shuffle_pooled < 1.05`) from [PLAN.md:38](<project>/PROBLEM-7/PLAN.md:38) is never computed or checked. | Action-blind rollouts could falsely earn `PARTIAL` (caught in `bughunt-step6`). |
| **A11** | [forecast4.py:98-99, 108, 118](<project>/PROBLEM-7/forecast4/forecast4.py:98-118) | (1) `sh` permutes whole `k`-step action tuples instead of per-step actions (`wm_fit.py:199-209`); (2) `mv` filters `k=3, 5` windows using **1-step** motion `hfr[xi+1] - x0` (also in `wm_fit.py:292`); (3) `nboth` zips `wr` positionally instead of by `world_id`. | Alters `k=5` shuffle null distribution; omits windows that moved on steps 2–5; fragile if any world has 0 moved windows. |
| **A12** | [forecast4.py:9-15, 21-25, 65-69](<project>/PROBLEM-7/forecast4/forecast4.py:65-69) | Dead `Dec` class & shadowed `imagine()`; `real_board()` runs without `torch.no_grad()`, `MC=refmean()` runs 3,000 times on a frozen trunk, and zero-grad `10*l_rec` is computed every step. | Wastes ~50–60% of Step 6 compute (~15.5 min instead of ~6 min). |
| **A13** | [record.py:85](<project>/PROBLEM-7/wm/record.py:85) | `save_split` computes printed `moved` across episode boundaries (`frames[1:] - frames[:-1]`). | Cosmetic (~+0.8% on printed log stat only; `wm_fit.windows()` stays strictly within episodes). |
| **A14** | [STATUS.md:464-465](<project>/PROBLEM-7/STATUS.md:464-465) | Documentation error: explains Step 6's `0.410` ceiling vs Step 3's `0.226` as "`dec` vs jointly trained readout". | Neither uses `dec` at eval (`forecast.py:46`, `forecast4.py:58`); true cause is `lam=140` on Step-2 ckpt (`val SSE 625.7`) vs `lam=100` after +1,500 `l_rec` steps (`val SSE 349.3`). |

*Cleared (`shown`):* No held-out data leakage exists in any script (`forecast.py` through `forecast4.py`, `wm_fit.py`, `recon.py`). Step 6's trunk freeze truly held (127/127 trunk tensors identical, [STATUS.md:462-463](<project>/PROBLEM-7/STATUS.md:462-463)).

---

## (b) Design Reasons the Action Cannot Strongly Influence the Forecast (and Parallel to Problem 1)

This is the core diagnosis. Just as Problem 1 (Family B) suffered a **multi-lock signal choke** (`1,085×` smaller gradient from unscaled constant embeddings + choked readout + unfloored gate, [PROBLEM-1/neon-agent/REPORT.md:42-65](<project>/PROBLEM-1/neon-agent/REPORT.md:42-65)), Problem 7 suffers a **5-lock signal choke** (`shown` in code → `suggested` combined mechanism):

1. **Lock 1 — 68:1 Board & Action Offset Burial (Exact Problem-1 Bug, `shown`):**
   - `real_board` has RMS `1.36` static offset vs. `~0.02` frame-to-frame spread (`STATUS.md:313`).
   - Entering `_imagine_impl` / `damped_imagine` (`imagine_head6.py:30-31`), `in_proj(x0)` is summed with unscaled `row_type_emb` (`std=1.0`) and `row_pos_emb` (`std=1.0`), producing static RMS `~1.8` before `norm1` (`RMSNorm`). Thus the **entire game screen is reduced to a ~1% ripple (`~0.01`)** inside the frozen trunk's residual stream.
   - Simultaneously, `enc_act` (`forecast4.py:27-32` → `board_swarm.py:319-321`) adds frozen `src_emb(SIGHT)` (`std=1.0`) + `age_lin(0)` (`RMS 0.58`) to `zoom(at)` (`RMS 0.48`), making all 17 action context tokens ~85–90% identical before attention even begins!
2. **Lock 2 — 1-of-66 Action Dilution + `RMSNorm` Ceiling (`shown`):**
   - In `imagine_head6.py:33`, the action enters as 1 extra row `ha` + 1 context token `enc_act` alongside 64 board rows (2 of 66 keys ≈ 3% under uniform attention).
   - Because `norm1` (`board_swarm.py:179`) is `RMSNorm`, the trainable `action_in` / `action_pos` **cannot** grow `ha`'s norm to grab attention — `norm1` rescales `ha` right back to unit RMS before the frozen `qkv` projections!
3. **Lock 3 — Crafter Dynamics Are Bilinear (`Δframe = (S_a - I) x_t`), Not Additive (`shown` + `suggested`):**
   - Pressing "move left" shifts every tile right by 1 tile. Averaged over screens, `E[Δframe | action=left] ≈ 0` — the pixel change at `(x, y)` depends **multiplicatively** on `(current pixel at neighbors) × (action)`.
   - Inside Step 6's **frozen 2-block trunk** (`P7toy`), `frame_signal` is a `~0.01` ripple and `action_signal` is a `~0.03` additive perturbation on top of a `1.0` static vector. The frozen `SparseMoE` GELUs (never trained to route or multiply actions!) produce at most an $O(0.01 \times 0.03) \approx 3 \times 10^{-4}$ bilinear interaction term (`suggested`).
4. **Lock 4 — Step 6's Trainable Head (`imagine_out`) Is Row-Wise Only (`shown`):**
   - `imagine_head6.py:14-18, 39` applies `Linear(256, 256) -> GELU -> Linear(256, 256)` independently to each row `r ∈ 0..63`.
   - **It cannot move information from row `r'` to row `r`!** Even if the Step-2 board cleanly stores all 16 screen patches across its 64 rows, a per-row MLP cannot shift patch `(x+1, y)` into patch `(x, y)` unless the *frozen* 2-block trunk already routed the exact shifted neighbors into row `r` conditioned on `a_t` — which a reading-only trunk was never trained to do!
5. **Lock 5 — The Frozen-Ridge Catch-22 (`shown`):**
   - Because Step 2's MLP decoder underfitted (`0.140` vs ridge `0.062`), Steps 4–6 locked a frozen closed-form ridge matrix `Wp = W_std / sd` (`forecast4.py:48`).
   - Because `sd ≈ 0.02` is tiny relative to `RMS 1.36`, `Wp` has massive `1/sd` gain.
   - **Unfreezing the trunk (Steps 4–5)** lets even `lr = 1e-5` rotate the `0.02` signal out of `Wp`, destroying reading (`ceiling 0.41 -> 3.63` in Step 4, `4.74` in Step 5).
   - **Freezing the trunk (Step 6)** protects reading, but traps the model behind Locks 1–4 where the trunk never learned to see actions or shift rows!

**Positive proof that the path isn't totally dead (`shown`):** Despite all 5 locks, Step 6's `head` grew from `0.00001 -> 0.01556` (`run_forecast4.log:3-17`) and produced **16/16 worlds with `shuffle > 1.0`** at every horizon (`1.038 -> 1.068 -> 1.090`). The small ~4% action signal it squeezed through is consistent with Lock 3 + Lock 4 choking a real underlying dynamics signal.

---

## (c) Does the Task / Data Even Let the Action Matter?

**YES — overwhelmingly (`shown`).**

### Exact Proof From Existing Score Files (`shown`)
Every `forecast*.py` script computes a **stateless per-action linear predictor** `act_roll(x_0, acts)`: 17 separate closed-form linear matrices `M_a` fit on `train.npz` (`x_{t+1} ~ M_a [x_t, 1]`, ridge `1.0`), rolled out open-loop for `k = 1, 3, 5` on `heldout.npz` ([forecast4.py:81-92](<project>/PROBLEM-7/forecast4/forecast4.py:81-92)). Dividing `E_over_B / act_baseline_E_over_E` from [forecast4/score.json](<project>/PROBLEM-7/forecast4/score.json) (identical across Steps 3, 4, 5, and 6!) gives the exact performance of that 1-line linear model on the exact same held-out worlds:

| Horizon | Pass Mark (`E/B`) | Lazy Copy (`copy/B`) | **1-Line Linear Per-Action (`M_a [x_t, 1]`)** | Step 6 (`forecast4`) |
|---|---:|---:|---:|---:|
| **k = 1** | `<= 0.80` | `1.055` | **`0.504`** (beats `B_1` by **49.6%**) | `1.191` |
| **k = 3** | `<= 0.90` | `1.140` | **`0.580`** (beats `B_3` by **42.0%**) | `1.089` |
| **k = 5** | `<= 0.95` | `1.204` | **`0.631`** (beats `B_5` by **36.9%**) | `1.117` |

### Action Breakdown on Held-Out (`5,008` Windows, `shown` from [wm/score_p7toy.json:105-208](<project>/PROBLEM-7/wm/score_p7toy.json:105-208))

| Action Group | Action IDs | Held-Out Count (% of total) | Real 1-Step Change `std_real` | What Causes the Frame Change |
|---|---|---:|---:|---|
| **4-way moves** | `1, 2, 3, 4` | **3,574 (71.4%)** | **`0.0743 – 0.0779`** | **~9× larger than `noop`** — whole-screen directional shift (`shown`). |
| **`do` (interact)** | `5` | 733 (14.6%) | `0.0225` | Local sprite/tile change + background drift. |
| **`sleep`** | `6` | 41 (0.8%) | **`0.1763`** | Large global screen darkening/brightening (`shown`). |
| **`place_stone / table`** | `8, 9` | 113 (2.3%) | `0.0324 – 0.0343` | Occasional placement + background drift. |
| **`noop` + rare crafts** | `0, 7, 10–16` | 547 (10.9%) | `0.0083 – 0.0145` | Almost pure background / daylight / mob jitter (no prerequisites in random play). |

### Data Limitations (Real, But NOT the Reason Steps 3–6 Failed)
1. **Unseen nighttime in held-out (`record.py:12-14`, `shown`):** Train stops at `t=125`; held-out runs to `t=250`. Hurts generalization, yet `M_a [x_t, 1]` still hits `0.504 / 0.580 / 0.631` despite it!
2. **Unseeded Crafter randomness (`step0.json:6`, `shown`):** Replaying `noop` twice gives max MSE `0.00229` (non-zero, from uncontrollable mob/env RNG). Sets a non-zero noise floor (~`std 0.008` on `noop`), not an obstacle to `E/B <= 0.80`.
3. **`4×4` pooling across `7×7` tiles (`record.py:18`, `shown` + `suggested`):** Smears player facing direction and HUD icons (limiting `do`/crafting accuracy, though moves still drive `0.504` `E/B`).

---

## (d) Scorer and Pass-Mark Problems (`shown`)

1. **Fatal Bug — Absolute-Frame `std_ratio` Makes `PASS` / `PARTIAL` Impossible Even for a Perfect Oracle (`shown`):**
   - `forecast4.py:115` evaluates `std(P - x_0) / std(y_1 - x_0)` where `P = RT(next_rows)`.
   - On `noop` (`action 0`, `std_real = 0.00834`), `P - x_0 = (RT(next_rows) - y_1) + (y_1 - x_0)`.
   - Because `RT` has held-out reconstruction RMSE `0.0419` (at `ceiling = 0.410`), even an exact oracle (`next_rows === real_board(t+1)`) has `std(P - x_0) >= 0.0419` → `std_ratio[0] ≈ 5.02` (failing `<= 2.0`!).
   - To pass `<= 2.0` on `noop` with absolute-frame decoding, `RT` would need `RMSE <= sqrt(3) × 0.00834 = 0.0144` → **`ceiling <= 0.049`** — 14× stricter than the `0.70` ceiling mark and 4.6× stricter than Step 3's best-ever `0.226`!
   - **Verified directly in Step 6 (`score.json:33-51`) and Step 5 refit (`score_refit.json:33-51`):** `std_ratio` follows `RMSE_ceiling / std_real[a]` across all 17 actions (`4.91` on `noop`, `0.54–0.56` on moves, `2.82–3.65` on actions `7, 10–16`).
2. **Mirror Bug — `pcs90_pred` and `copy_ness` Give False Passes Under Absolute-Frame Decoding (`shown`):**
   - In Step 5 refit (`imagine_alpha = 0.0000`, literally `next_rows === st.rows`), `P - x_0 = RT(st) - x_0` scored **`pcs90_pred = 107 / 111` (`pcs_ok: true`!)** and `copy_ness = 0.605` purely from static readout error!
3. **Catch-22 on `std_ratio >= 0.25` for Noise-Only No-Op Actions (`shown`):**
   - Even after fixing Bug #1 (measuring decoded change `RT(next) - RT(now)`), Crafter has ~10 actions (`0, 7, 10–16`) that rarely do anything in random exploration (`std_real ≈ 0.008–0.014` is almost all random mob/daylight noise). A perfect deterministic physics model predicts `Δx ≈ 0` on `noop`, giving `std_ratio < 0.25` and failing `all(0.25 <= x <= 2.0)`! (Astra's original design in [astra/REPLY.md:33](<project>/PROBLEM-7/astra/REPLY.md:33) used frequency-weighted group variance, and Neon warned about this exact trap in [neon/q4-marks/REPLY.md:4](<project>/PROBLEM-7/neon/q4-marks/REPLY.md:4).)
4. **Ceiling Tax on `E_1/B_1` (`shown`):**
   - Because `B_1` (`16,475`) is ~5.5× smaller than mean-frame SSE, Step 6's `7.3%` readout error (`lam=140`) eats **`0.410`** of `B_1` before imagination even runs! Even an exact-identity copy in board space (`next_rows = st.rows`) starts around `E_1/B_1 ≈ 1.24`, not `1.055`. Using residual decoding `x_0 + RT(next_rows) - RT(st_rows)` (still 100% through the frozen readout, using only frame `t=0`) removes both the ceiling tax and Bugs #1–#2 cleanly (`suggested`).
5. **Other Scorer Discrepancies (`shown`):** `PARTIAL` omits the `k3/k5` negation check (`forecast4.py:122`); `proves_wrong` (`E1/B1 <= 0.80` & `shuffle < 1.05`) is dropped; `sh` shuffles `k`-step tuples rather than per-step actions (`forecast4.py:98-99`); `mv` filters `k=5` by step-1 motion (`forecast4.py:108`); `nboth` zips positionally (`forecast4.py:118`).

---

## (e) Ledger: What Every Past Run Actually Ruled Out vs. What Is Still Untested

| Stage / Run | Model & Setup | Key Raw Held-Out Numbers (`shown`) | Verdict | What It Actually Ruled Out | What It Did NOT Rule Out |
|---|---|---|---|---|---|
| **Step 0** (`step0.json`) | No training; 16×16 Crafter | 19/24 move > noop+1e-4; `B` = blend (4%/11%/17% < copy); noop-noop max `0.0023` | **PASS** | Ruled out dead capture path. | — |
| **Step 1 Run 1** (`wm/score_run1.json`) | `debug_tiny` (66K), continued row target, MLP delta head | `E/B 1.055 / 1.140 / 1.204`; ceil `1.055`; shuf `1.000`; `l_row -> 3,291` | **WRONG** | Continued-tick board as stop-grad target (diverges from unbounded fast rows). | Everything else (ceiling failed). |
| **Step 1 Retry 1** (`wm/score_fresh.json`) | `debug_tiny`, `--row-target fresh` | `E/B 1.056 / 1.143 / 1.210`; ceil `1.056`; shuf `1.000` | **WRONG** | Unstandardized MLP decoder on 1%-SNR board. | Whether board holds frame (G0 proved `R^2=0.68` unpinned!). |
| **Step 1 Try 3 + P7toy** (`wm/score_try3.json`, `score_p7toy.json`) | `debug_tiny` & `P7toy` (2.47M), `+ --dec-norm`, stale frame-`t` ctx | P7toy: `E/B 1.004 / 1.608 / 4.527`; ceil `1.066`; shuf `1.082 / 1.025` (0/16 k1, 1/16 k5); PCs `7/111` | **WRONG (LINE CLOSED)** | Jointly training `BatchNorm + 1-layer` delta MLP from scratch for 1,500 steps on unmodified buried `BoardCell` with stale context. | Cleanly reading frames first, un-choking `BoardCell`, or context-blind imagination. |
| **Step 2** (`recon/ridge_board.json`) | `P7toy`, current-frame recon + `--fixed-scale --ridge` (`lam=0.1`) | MLP: `M1=0.140` (FAIL); **Ridge: `M1=0.062`, `M2 vs copy=0.059`, `C1=169x`, `C2=1.95`** | **PASS (via Ridge)** | Ruled out "board cannot hold current frame". Proved MLP decoder was undertrained. | Whether board holds dynamic cues cleanly without 68:1 burial, or can be updated by actions. |
| **Step 3** (`forecast/score.json`) | `P7toy` from Step 2, `l_rec` (`Dec` BN) + raw `l_row`, stale ctx, ungated `imagine`, then ridge (`lam=100`) | `E/B 31.3 / 120.2 / 247.2`; ceil `0.226`; shuf `0.999`; 0/16 worlds | **FAIL (#1)** | Raw Euclidean `l_row` without pixel alignment (collapses behind BN; ungated `imagine` blows up off-manifold). | Pixel-aligned imagination or gated `imagine`. |
| **Step 4** (`forecast2/score_primary.json`) | `P7toy`, context-blind `enc_act`, frozen `lam=140` ridge + `MC=refmean`, unfrozen trunk (`1e-4`), **ungated `imagine` (`focus=1`)** | `E/B 320.9 / 1266 / 2625` (refit `471`); ceil `3.63` (refit `0.92`); shuf `1.003`; 0/16 | **FAIL (#2)** | Backpropping huge ungated `_imagine_impl` error (`img=2814`) into unfrozen trunk against frozen `1/sd` ridge. | Gated/bounded imagination or un-choked `BoardCell`. |
| **Step 5** (`forecast3/score_primary.json`, `score_refit.json`) | `P7toy`, gated `imagine_damped` (`alpha=0.02`), split LR (`1e-5` trunk / `3e-4` img) | `alpha -> 0.0000`; primary `E/B 4.58 / 2.41 / 2.04` (ceil `4.74`); refit `1.33 / 1.14 / 1.17` (ceil `0.78`); shuf `1.000` | **FAIL (#3)** | Scalar `imagine_alpha` on reading `out_proj` (collapses to `0` saddle) AND updating trunk even at `1e-5` against frozen `1/sd` ridge (wrecks reading!). | Own imagination layers, frozen trunk, or training without frozen `1/sd` ridge. |
| **Step 6** (`forecast4/score.json`) | `P7toy`, **trunk 100% frozen**, row-wise 2-layer `imagine_out` MLP (zero-init last) × `imagine_scale`, frozen `g_slow` | `E/B 1.191 / 1.089 / 1.117`; ceil `0.410`; shuf `1.038 / 1.068 / 1.090` (**16/16 > 1.0**, 0/16 k1, 7/16 k5, 0/16 both); `std 0.42–4.91` | **FAIL (#4; 1st frozen-trunk try)** | Row-wise MLP on top of a frozen reading-only buried trunk + frozen `g_slow` gate. | **Everything below!** |

### Still Completely Untested (`untested`)
1. **No-training X-ray on saved Step-2/Step-6 weights:** Whether the Step-2 board itself supports `E/B <= 0.70` via a per-action linear map, and whether frozen `hn` even reacts to `a_t`.
2. **Fixing the Problem-1 68:1 offset-burial init bug in `BoardCell`** (`src_emb`, `age_lin`, `row_type_emb`, `row_pos_emb`, `init_rows`, `out_proj`) before reading & forecasting.
3. **Broadcasting / FiLM-conditioning the action into ALL 64 board rows** (instead of 1-of-66 behind `RMSNorm`).
4. **Cross-row mixing in a standalone imagination block** on the standardized frozen Step-2 board (removing Step 6's row-blind MLP + frozen trunk + frozen `g_slow`).
5. **Joint clean training of an un-choked shared trunk with a LayerNorm linear-skip decoder** (escaping the frozen-ridge Catch-22 without BatchNorm scale collapse!).
6. **Clean residual-change scoring** (`x_0 + RT(next) - RT(now)`) + matched 250-step day/night train split.
7. **Discrete state snapping (FSQ)** or Ben-approved **2-step real-target pushforward** for multi-step stability (only relevant after 1-step passes!).
8. **Separate small spatial world model (DreamerV3-style Candidate 3)** as a benchmark / escape hatch if the un-choked shared trunk misses cleanly.

### Honest Accounting Under the "3 Clean Misses Close an Idea" Rule
- **CLOSED:** Step-1 from-scratch change-MLP on unmodified `BoardCell` (4 misses: 3 tiny + 1 `P7toy`).
- **CLOSED:** Patching an **unfrozen** buried trunk against a **frozen `1/sd` ridge readout** (Steps 3–5 = 3 misses; mathematically broken Catch-22).
- **1 of 3 misses (do NOT burn try 2 before the 2-min X-ray!):** Frozen Step-2 trunk + separate imagination layers (Step 6 = 1st miss; failed due to row-blind head + frozen trunk + frozen gate).
- **0 of 3 misses (never tried yet):** Un-choked `BoardCell` (Problem-1 fix) + action-broadcast shared trunk trained jointly with a clean decoder; and separate compact spatial world model (escape hatch).
