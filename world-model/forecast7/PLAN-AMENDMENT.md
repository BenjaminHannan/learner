# PROBLEM-7 PLAN AMENDMENT — Rank 7 (`forecast7` / `wm7`): 2-Frame Input (`R7conv`) & Pinned `reencode_res` Rollout

**Date:** 2026-11-25  
**Status:** **STOPPED — final v2 scorer fixes complete after bug hunt #2; ready for re-check.** `n200_or_neff10` was adopted 2026-11-25 before any Rank 7 training. Zero scored Rank 7 training runs launched. `sealed_test.npz` untouched (`chmod 444`).  
**Motivation:** Rank 6 (`R6conv`, Strike 1/3 on the conv world-model line) beat `shift_or_stay` at `k = 1` (`0.2470 / 0.2488` vs `0.2853`) and `k = 3` (`0.3902 / 0.3844` vs `0.4068`), passed wall physics (`block_open = 0.0252 / 0.0257`, `71%` cut), passed `pcs` (`111/111`, `109/111`), hit `ceil_abs = 0.0146 / 0.0145`, and passed shuffle in `16/16` worlds (`5.55–5.73× / 2.52–2.65×`), failing only `std_ok` (`a = 5, 8, 9`) and `k = 5` (`0.5202 / 0.5031` vs `0.4977`). Our read-only CPU diagnosis ([RANK6-DIAG.md](<project>/PROBLEM-7/neon-audit/RANK6-DIAG.md)) proved:
1. **`std_ok` wall (`shown`):** On single-frame `16×16` pixels, Crafter's HUD `energy = 6` (`0%` wake) and `energy = 9` (`100%` wake) are **bit-for-bit identical (`L2 = 0.00000`)**, mathematically capping even an oracle local predictor on `a = 9` below `0.25`. Two-frame past history `(x_{t-1}, x_t)` breaks the collision (`energy 8 → 9` HUD delta `L2 = 0.242`), lifting a pure linear 2-frame HUD Ridge on saved `s42` to `a = 5/8/9 std_r = 0.362 / 0.407 / 0.427` (`asleep R²: +0.080 → +0.377`). *(Local awake chopping/placing `do_awake`/`place_table_awake` remains MSE-starved at `0.70%` / `0.07%` of train SSE and is tracked separately as a non-gating honesty diagnostic.)*
2. **`k = 5` drift (`shown`):** `> 100%` of the `k = 5` gap is `15×` off-manifold latent drift on `3–5` open-move sequences (`||z_5 - enc(dec(z_5))|| = 0.0494` vs `0.0033` real). Projecting intermediate open-loop latents back onto the encoder manifold (`reencode_res`) cuts `k = 5` on saved Rank 6 `s42 / s43` to `0.4881 / 0.4827` (`< 0.4977`) with zero retraining.

Lead approved **Rank 7 (`forecast7/` ↔ M3 `wm7/`)**: **ONE training change** (2-frame past-history input into `SpatialDynamicsUNet`), with the exact same trained weights scored under two pinned rollout modes (`reencode` = verdict of record, `plain` = one-knob isolation), plus full 2×2 re-scoring of saved Rank 6 `s42 / s43` through the exact same pinned evaluation path.

---

## 1. Scope, Learning Rules & Hard Invariants

- **100% learned parts only:** Zero game-specific rules, zero hand-coded shifts, zero OS/memory cheats.
- **Canonical core untouched:** `premonition_core_v2/board_swarm.py` (`sha256: 8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d`) untouched.
- **Dated ruler (`scorer.py`):** `forecast7/scorer.py` (and M3 `wm7/scorer.py`) is the adopted `forecast7-v2-rung1-n200_or_neff10` scorer (`sha256: 720adce8a1881c26510bf32850e4686f91cc7e03e5419ecef5e3819abfe62a93`), verified at runtime by `verify_pinned_scorer()`. Relative to pinned `forecast5/scorer.py` (`6ff1c135...`, untouched), only the version, std gate, PARTIAL exclusivity, and strike-class fields changed (`test_13`).
- **Bit-identical lock wrapper (`withlock.sh`):** `forecast7/withlock.sh` (and M3 `wm7/withlock.sh`) is **bit-identical** to pinned `forecast5/withlock.sh` (`sha256: 77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa`).
- **Write scope:** Strictly `PROBLEM-7/neon-audit/`, `PROBLEM-7/forecast7/`, and M3 `~/learner-ops/seven-problems-m3/PROBLEM-7/wm7/`.
- **M3 power, disk, sealed & bug-hunt hygiene guards (`BUGHUNT-LEAD.md` nits folded in):**
  - Power check uses `torch.device(args.device).type == "mps"` (covers `mps:0` too) enforcing `AC Power` OR battery `>= 35%` in BOTH `train_v7.py` and `run_rank7.sh` (`grep -Eo "[0-9]+%"`).
   - `--eval-only` validates checkpoint `arch`, `size`, and `state_dict` **before** opening or hashing `eval_data`, and restores trained `seed, w_lat, lr, wd, batch` into logged metadata. `test_9` asserts the eval-data guard is not invoked before checkpoint validation.
  - `guard_sealed_path` blocks `sealed_test.npz` (lexical path, symlink `realpath`, or pinned SHA-256 `74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f`) unless BOTH `--eval-only` AND `--allow-sealed` are passed.
  - Disk floor `>= 12.0 GiB`, fail-loud `INCOMPLETE RUN` if `done < steps`, finite loss & grad norm check before `opt.step()`, and `|| exit $?` on the final driver summary.

---

## 2. Exact ONE Training Change (`SpatialWorldModelV7`, `R7conv`) & Two Pinned Rollout Modes

### 2.1 Single Training Change (`+4,096` params = `+0.152%`)
- `SpatialEncoder(x_t) -> z_t`, `SpatialDecoder(z_t) -> x_t`, `action_emb`, ceiling definition (`decode(encode(x_{t+1}))` [abs] and `x_t + (decode(encode(x_{t+1})) - decode(encode(x_t)))` [res]), strictly `k = 1` training loss (`1.0 * l_rec + 1.0 * l_img_res + 0.25 * l_img_abs + 0.05 * l_lat`), optimizer (`AdamW`, `lr = 3e-4`, `wd = 1e-4`), warmup+cosine schedule, `batch = 64`, `steps = 5000`, and `train_dn.npz` are **100% identical to Rank 6**.
- **ONLY training change:** `SpatialDynamicsUNet.in_proj` expands from `Conv2d(latent_ch + 2, c0, 1)` on `[z_t, coord]` (`R6conv`, `2,688,963` params) to `Conv2d(2 * latent_ch + 2, c0, 1)` on **`[z_t, z_t - z_{t-1}, coord]`** (`R7conv`, **`2,693,059` params** = `+4,096` params). `z_{t-1} = encode(x_{t-1}).detach()` passes under `torch.no_grad()` so `encoder` still receives **100% `l_rec` gradients only** (`test_3`).
- `SpatialWorldModelV7(size, n_history)` supports `n_history in {1, 2}` (`n_history = 1` has byte-for-byte identical keys/shapes to `SpatialWorldModelV6`, letting the exact same pinned `evaluate_model` path score both saved Rank 6 and Rank 7 checkpoints).

### 2.2 Pinned History Rules (Every Rule Enforced & Unit-Tested)
1. **Only `x_{t-1}` and `x_t` may be real (`test_4a`):** At rollout start, only `x_{t-1}` (`prev_frame_indices`) and `x_t` (`xi`) are read. NaN-poisoning both `x_{t-2}` AND all intermediate future frames `x_{t+1..t+k-1}` yields finite, **bit-identical** `k = 5` real and shuffled predictions in **BOTH `plain` AND `reencode` modes**.
2. **From rollout step 2 onward, history is strictly the model's own outputs (`test_4b`):**
   - Step `0` (`t -> t+1`): `(enc(x_{t-1}), enc(x_t)) -> z_1`
   - Step `1` (`t+1 -> t+2`): `(enc(x_t), z_hat_1) -> z_2`
   - Step `2` (`t+2 -> t+3`): `(z_hat_1, z_hat_2) -> z_3` *(BOTH inputs are strictly the model's own outputs!)*
   - Steps `3, 4`: `(z_hat_2, z_hat_3)`, `(z_hat_3, z_hat_4)` *(verified via direct spy on `dynamics.forward` + `a_0` counterfactual perturbation in BOTH `plain` and `reencode` modes).*
3. **Never crosses an episode or world boundary; `x_{-1} = x_0` at episode start (`test_4c`):** `prev_frame_indices` clamps `h_idx = np.where(ti > 0, xi - 1, xi)` and runtime-asserts identical `episode_id` and `world_id`. Poisoning the final frame of the prior episode (same world AND different world) with `NaN` leaves `t = 0` predictions finite, bit-identical, and equal to explicit `x_prev = x0` in **BOTH `plain` and `reencode` modes**.

### 2.3 Two Pinned Rollout Modes (`--rollout {plain,reencode}`)
- **`reencode` (`reencode_res`) — VERDICT OF RECORD:** Between open-loop steps (`step < k - 1`), projects the imagined latent back onto the encoder manifold via `z_next_feed = encode(clamp(x0 + decode(z_next) - dec0, 0, 1))`, and updates `z_prev, z = z, z_next_feed` (so both inputs to `dynamics` stay on the encoder manifold). At `k = 1`, `step < 0` never fires → **bit-identical to `plain`**.
- **`plain` — ONE-KNOB ISOLATION:** Feeds raw imagined latents `z_prev, z = z, z_next` without re-encoding; scored on the exact same frozen `model.pt` weights and reported alongside `reencode`.

---

## 3. Pinned 2×2 Matrix — Saved Rank 6 Re-Scores Completed FIRST (`shown`)

Before any Rank 7 training, we re-scored both saved Rank 6 (`1-frame`) checkpoints (`../wm6/run_r6_s{42,43}/model.pt`) on M3 MPS under `./withlock.sh` through the exact pinned `wm7/train_v7.py --eval-only --size R6conv --n-history 1 --rollout {plain,reencode}` path:

- **Exact `plain` reproduction vs saved `wm6/run_r6_s{42,43}/score_dev.json`:** `max |E/B diff| = 0.000e+00` on BOTH seeds!
- **Exact `reencode` reproduction vs diagnostic CPU probe (`0.4881 / 0.4827`):** **`s42 = 0.488105`** (probe `0.4881`, `E/sos = 0.9807`, CI `[0.9529, 1.0080]`), **`s43 = 0.482662`** (probe `0.4827`, `E/sos = 0.9698`, CI `[0.9442, 0.9939]`) — **reproduces to all 4+ decimal places across both CPU and M3 MPS!**

| Model (History) | Rollout Mode | Seed | `k1 E/B` (`<0.2853`) | `k3 E/B` (`<0.4068`) | `k5 E/B` (`<0.4977`) | `k5 E/sos` (95% CI) | `shuf k1 / k5` | `worlds` | `bo_err` (`<=0.0659`) | `std_ok` | `diag_aslR2` | `diag_nw_do / pt` `chR2` | Verdict |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|:---:|---:|---:|---|
| **Rank 6 (`1-frame`)** | `plain` (saved) | `42` | `0.2470` | `0.3902` | `0.5202` | `1.0453 [1.0166, 1.0723]` | `5.551 / 2.517` | `16/16/16` | `0.0252` | `False` | `+0.080` | `-0.015 / +0.004` | `FAIL` |
| **Rank 6 (`1-frame`)** | `plain` (saved) | `43` | `0.2488` | `0.3844` | `0.5031` | `1.0108 [0.9830, 1.0378]` | `5.727 / 2.646` | `16/16/16` | `0.0257` | `False` | `+0.080` | `-0.015 / -0.000` | `FAIL` |
| **Rank 6 (`1-frame`)** | **`reencode` (re-score)** | `42` | `0.2470` | **`0.3740`** | **`0.4881`** | `0.9807 [0.9529, 1.0080]` | `5.551 / 2.675` | `16/16/16` | `0.0252` | `False` | `+0.080` | `-0.015 / +0.004` | `FAIL` *(10/11)* |
| **Rank 6 (`1-frame`)** | **`reencode` (re-score)** | `43` | `0.2488` | **`0.3737`** | **`0.4827`** | **`0.9698 [0.9442, 0.9939]`** | `5.727 / 2.750` | `16/16/16` | `0.0257` | `False` | `+0.080` | `-0.015 / -0.000` | `FAIL` *(10/11)* |
| **Rank 7 (`2-frame`)** | `plain` (isolation) | `42, 43` | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* |
| **Rank 7 (`2-frame`)** | **`reencode` (OF RECORD)** | `42, 43` | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* | *TBD* |

*The Rank 6 rows above are the pinned historical verdicts under the old ruler. The final v2 end-to-end re-score is FAIL/FAIL with `strike_class=LINE` (`std_high_count_or_concentrated: [5]`) as well (§4.2); Rank 6's recorded strike and verdict are not retroactively changed.*

### Non-Gating 2-Frame Baseline Context (Dev `1000..1015`, `shown`; Pinned Pass Bars Stay 1-Frame!)
Implemented in `train_v7.py:compute_2f_baselines_context` using the exact 2-frame analog of `scorer.py` (`[x_t, x_t - x_{t-1}, 1]`, `ridge = 1.0`, `gate_ridge = 10.0`, strict Point 2 history rules):

| Baseline | `k1 E/B` | `k3 E/B` | `k5 E/B` | `block_open mean_err` (`fb / fo`) | Role |
|---|---:|---:|---:|---:|---|
| `1f linear_Mact` | `0.4738` | `0.5578` | `0.6103` | `0.4970` (`0.0014 / 0.9926`) | Pinned bar (in `scorer.py`) |
| **`1f shift_or_stay`** | **`0.2853`** | **`0.4068`** | **`0.4977`** | **`0.0879` (`0.0207 / 0.1552`)** | **Pinned strongest bar** |
| `2f linear_Mact` (`ridge=1.0`) | `0.4875` | `0.5907` | `0.6377` | `0.4882` (`0.0023 / 0.9741`) | Reported context only |
| `2f shift_or_stay` (`ridge=1.0`) | `0.3093` | `0.4349` | `0.5225` | `0.0814` (`0.0212 / 0.1416`) | Reported context only |

*(Unconstrained 1,537-dim per-action linear ridge slightly overfits on `~330–5,000` samples, raising `E/B`, while 2-frame crop gating trims `shift_or_stay` `block_open` from `0.0879 → 0.0814`. Pinned pass bars remain the tighter 1-frame `0.2853 / 0.4068 / 0.4977` and `0.0879`.)*

---

## 4. Point 3 — Fragility of `std_ok` on Rare Actions (THROWAWAY Worlds Only, `shown`) & Proposed Dated Gate Amendment

**Strictly throwaway worlds only (zero dev, zero sealed):** We generated **10 independent 16-world throwaway splits** (`worlds 9000..9159`, `160` worlds = `56,000` transitions, `350`/world, exact `record_v5.py` policy & `16×16` pooling, disjoint from `0..159`, `1000..1015`, `2000..2015`, `3000..3079`; script [run_std_fragility_throwaway.py](<project>/PROBLEM-7/neon-audit/run_std_fragility_throwaway.py), raw log [std_fragility_throwaway.log](<project>/PROBLEM-7/neon-audit/std_fragility_throwaway.log)).

### 4.1 Throwaway Fragility Evidence (`shown`)
- **Genuine placements across all 160 throwaway worlds (`56,000` transitions):**
  - `place_table (a = 8)`: `76` total (`[4, 8, 10, 10, 8, 8, 5, 3, 9, 11]` per 16-world split), yet **without wake-ups `sr_noWk = 0.0165 < 0.02` (inactive in `7/10` splits)**.
  - **`place_furnace (a = 9)`: `0` total across ALL 160 throwaway worlds (`[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`)!**
- **Single-event wake-up lottery drives `a = 8`, `a = 9`, and EVERY rare action (`0, 7..16`):**
  - **`a = 8 (place_table)`:** Active in `3/10` splits — in **all `3/3` active splits**, literally **`1` single sleep wake-up** carries **`73.5–80.3%`** of total SSE (Kish effective event count `n_eff = 1.5–1.8`), jumping `sr` from `~0.016` to `0.0299–0.0355`. Missing that **1 wake-up** collapses `std_ratio` from **`0.620 ± 0.010` → `0.092 ± 0.007`** (**`3/3` FAIL**).
  - **`a = 9 (place_furnace)`:** Active in `1/10` splits — literally **`1` single sleep wake-up** carries **`91.0%`** of total SSE (`n_eff = 1.2`, `sr = 0.0291`). Missing that **1 wake-up** collapses `std_ratio` from **`0.675` → `0.103`** (**`1/1` FAIL**).
  - **Same lottery across ALL 11 rare actions (`0, 7..16`):** An average of **`3.2` rare actions per 16-world split** randomly catch 1–2 wake-ups (`n_eff = 1.2–2.3`) and become active! Worse, `~17–25%` of wake-ups are **monster-hurt wake-ups** (unobservable even from 2-frame HUD `8 → 9`):
    - Under the **old ruler (`forecast5/scorer.py`)** across 10 throwaway splits:
      - Even a **perfect 2-frame oracle (`2f_oracle_e9`: `100%` of `8→9` wakes at `0.70` amp)** **FAILS `2/10` (`20%`)** of throwaway splits (killed by hurt wakes on rare `a = 13`)!
      - A **realistic 2-frame model (`2f_realistic_85`: `85%` recall on `8→9` wakes, 200 Monte Carlo draws)** **FAILS `44.5%` (`89/200`)** of throwaway splits! At `80%` recall / `0.60` amp, it **FAILS `50.5%` (`101/200`)** — a coin flip!
    - By contrast, high-frequency `a = 5 (do, n ≈ 810, n_eff = 11.7–30.9)` is stable: across active splits (`5–8` wakes each), missing 1 wake shifts `std_ratio` only from `0.565 ± 0.032 → 0.502 ± 0.040` (`0/3` FAIL).

### 4.2 Adopted Dated Gate Amendment (`2026-11-25`, Before Any Rank 7 Training)
- **Exact adopted rule (`n200_or_neff10`, 100% domain-general, zero hardcoded action IDs):**
  - For each action `q` with `n >= 20`, compute Kish's effective event count on per-window mean squared change `e_i = mean((y_i - x_i)^2)`:
    $$n_{\text{eff}}(q) = \frac{(\sum_i e_i)^2}{\sum_i e_i^2}$$
  - **Individual gate (`0.25 <= ratio <= 2.0`):** Applied to every action with `n >= 20`, `std_real >= 0.02`, AND **`(n >= 200 OR n_eff >= 10.0)`** *(naturally covers moves `1..4` with `n ≈ 900, n_eff ≈ 330`, `do 5` with `n ≈ 733–810, n_eff ≈ 12–31`, and `sleep 6` with `n ≈ 41–75, n_eff ≈ 26–32`)*.
   - **Pooled rare/concentrated gate (`0.25 <= pool_ratio <= 2.0` when `pool_sr >= 0.02`):** Pool only **ACTIVE** remaining `n >= 20` actions with `n < 200` AND `n_eff < 10.0` into ONE combined rare bucket. Inactive actions never dilute the pool. **Energy-dominance guard:** any pooled active action with `ratio < 0.25` carrying `>= 25%` of the pool's real change energy fails the gate even if the aggregate pool ratio passes.
  - **Frequency-weighted gate (`0.25 <= fw_ratio <= 2.0`):** Unchanged.
- **Final v2 throwaway re-check (`10` fresh splits, worlds `9000..9159`, `shown`):** Active-only pooling plus the energy-dominance guard is stricter than v1; Crafter's unseeded randomness means counts can vary slightly across regenerations.

| Predictor Regime (Throwaway `9000..9159`) | Old Ruler | Final v2 `n200_or_neff10` |
|---|---:|---:|
| `2f_oracle_e9` (`100%` of `8→9` wakes, misses hurt wakes) | `7/10` (`70.0%`) | **`9/10` (`90.0%`)** |
| `2f_realistic_85` (`85%` `8→9` recall @ `0.70` amp) | `111/200` (`55.5%`) | **`153/200` (`76.5%`)** |
| `2f_realistic_80_amp60` (`80%` recall @ `0.60` amp) | `95/200` (`47.5%`) | **`137/200` (`68.5%`)** |
| `1f_bayes_like` (`12.5%` wake amp — saved Rank 6 regime) | `0/10` | **`0/10`** |
| `collapsed_nowk` (`0` wakes, shrunk non-moves) | `0/10` | **`0/10`** |

- **Saved Rank 6 (`s42` & `s43`) Final v2 End-to-End Re-Score (NO FLIP, `shown`):**
  - **`s42`:** Old ruler → `std_ok = False` (`fail = [5, 8, 9]`, verdict `FAIL`). Final v2 → **`std_ok = False`**, `strike_class = LINE`, reason `std_high_count_or_concentrated`; action 5 fails individually at `0.1613`, and the active-only rare pool `[8, 9]` fails at `0.0855`. Verdict **`FAIL`**.
  - **`s43`:** Old ruler → `std_ok = False` (`fail = [5, 8, 9]`, verdict `FAIL`). Final v2 → **`std_ok = False`**, `strike_class = LINE`, reason `std_high_count_or_concentrated`; action 5 fails individually at `0.1761`, and the active-only rare pool `[8, 9]` fails at `0.1126`. Verdict **`FAIL`**.
- **Adoption and bug-hunt record (Lead, 2026-11-25, BEFORE any Rank 7 training):** The gate was adopted because action 8/9 activity is decided by a single wake-up on throwaway worlds, it does not flip saved Rank 6, and collapsed controls still fail. Bug hunt #2 then required active-only pooling plus the `>=25%` energy-dominance guard, exclusive k5-only `PARTIAL`, and explicit strike classification. `forecast7/scorer.py` is now version `forecast7-v2-rung1-n200_or_neff10` (`sha256: 720adce8a1881c26510bf32850e4686f91cc7e03e5419ecef5e3819abfe62a93`); `forecast5/scorer.py` remains untouched at `6ff1c135...`. `test_11` loads real M3 eval-only Rank 6 re-scores, `test_12` covers oracle/collapsed controls, `test_13` restricts the scorer diff to the approved changes, and `test_14` covers both PARTIAL counterexamples, selective collapse, Kish-zero, and strike classes. **Rank 6's pinned historical verdict remains under the old ruler.**

---

## 5. Pinned Verdict Rules, Strike Policy, Sealed `PARTIAL` Rule & Honest Pre-Filed Odds

### 5.1 Verdict of Record & Two-Seed Rule (Seeds `42` and `43`)
- **Verdict of record:** **`2-frame + reencode`** (`score_dev.json` / `score_dev_reencode.json`). `2-frame + plain` (`score_dev_plain.json`) is scored on the exact same `model.pt` weights and reported as the 1-knob isolation.
- **Aggregate Dev `PASS`:** BOTH seeds `42` and `43` must score `rank7_verdict == "PASS"` under `reencode` using the adopted §4.2 scorer bars.
- **Pre-pinned single sealed candidate:** If and only if aggregate Dev is `PASS`, select the single seed with lower dev `reencode` `k1 E/B` (tie-break: lower dev `reencode` `k5 E/B`, then seed `42`).
- **Point 6 — Exclusive `PARTIAL` rule (pinned 2026-11-25):** `PARTIAL` is allowed **only** when k5 alone misses. All of `ok1`, `ok3`, `r1_b1`, `r1_b3`, `block_open`, `k1` shuffle, `worlds_k1`, `worlds_both`, `std_ok`, `pcs`, and `ceiling` must pass; the only permitted failure is `not ok5` / `not r1_b5`. A k3-only miss or a k5 miss with `worlds_both < 12` is `FAIL`.
- **Inherited bug note (2026-11-25):** The same non-exclusive `PARTIAL` bug exists in untouched `forecast5/scorer.py`. It did **not** affect Rank 6's recorded `FAIL`, because `std_ok` already failed.
- **Point 5 — Non-gating honesty diagnostics:** Log `diag_non_wake_interactions` (`asleep_all R2/AUROC`, plus non-wake `do`, `place_table`, `place_furnace` `full/ctr6x6/hud/ctr_hud R2 & std_ratio`) and `diag_baselines_2f` (`linear_Mact_2f`, `shift_or_stay_2f`) on every run. **Explicit honesty claim:** A Rank 7 `PASS` proves 2-frame sleep-wake + wall physics + open-loop rollout stability — it does **NOT** claim awake local chopping/placing is solved unless `diag_non_wake_interactions` shows `ctr_hud_R2 > 0`.

### 5.2 Point 4 — Pinned Strike Rule (Line Strike vs. Variant Strike)
- **Score JSON:** Every score emits `strike_class` and `strike_reasons`. `NONE` for `PASS`/`PARTIAL`; `LINE` for any non-std gate failure or high-count/concentrated/frequency-weighted std failure; `VARIANT` only when the sole failure is the pooled rare/low-`n_eff` std gate.
- **Counts as a LINE strike** against the dedicated 2D conv world-model line (currently at `1/3` from Rank 6): if under `reencode` (verdict of record) either seed fails on **`k1` accuracy**, **`k3` accuracy**, **`block_open` wall physics**, **`shuffle`** (`k1_pooled < 1.25`, `worlds_k1 < 12`, `worlds_both < 12`, or `proves_wrong`), **`ceiling > 0.70`**, **`pcs`**, **high-count/concentrated or frequency-weighted std**, or an incomplete/non-finite run.
- **Counts as a VARIANT strike ONLY** (does NOT count against the conv world-model line): all non-std gates and individual std gates pass, and the sole failure is the adopted pooled rare/low-`n_eff` bucket or its energy-dominance guard.
- **`PARTIAL`** (exclusive k5-only miss, on dev or sealed): **NOT a strike.** `run_rank7.sh` prints strike class and reasons for both rollout modes.

### 5.3 Honest Pre-Filed Odds (`untested`, 2-Seed Bar, Verdict of Record = `2-frame + reencode`, Adopted `n200_or_neff10`)
- **Two-seed Dev `PASS`: 65% | Aggregate `PARTIAL` (`k5` miss alone): 15% | Aggregate `FAIL`: 20%** (main risk: 2-frame `R7conv` underfitting the `0.41%`-freq 2-pixel HUD `8 → 9` cue under uniform MSE on at least one seed).

---

## 6. Timing Calibration & Exact Launch / Sealed Commands (NOT Launched Yet)

### 6.1 Unscored M3 MPS Timing Check (`timing_mps_r7.log`, Under `./withlock.sh`)
Ran on M3 (`AC Power`, battery `82%`, `23.01 GiB` free, `--size R7conv --n-history 2 --device mps --steps 60 --batch 64 --timing-only`, 10 warmup + 50 steady steps, `EXIT=0`, lock cleanly released):
- **Steady-state speed:** **`117.1 ms/step`** (`5.85s` for 50 steady steps) → **`5,000` steps = `9.76 min`** (`~10.8 min/seed` incl. both `reencode` and `plain` MPS evals @ `~33s` each).
- **Step-0 check:** `grad = {'action_emb': 0.00017, 'encoder': 0.10561, 'dynamics': 0.38076, 'decoder': 0.54965}`, `lat_burial = 4.88`; by step 59 `rec: 0.12845 → 0.01639`, `lat: 0.08694 → 0.00349`.
- **Pinned budget:** `--steps 5000`, **`--max-minutes 18.0`** (`1.84×` thermal headroom over `9.76 min`), fail-loud if `done < 5000`.

### 6.2 Exact Dev Launch Commands (Run on M3 `wm7/` ONLY After Lead Bug Hunt GO)
```bash
# Seed 42: train 5,000 steps + score verdict of record (reencode), then score same weights under plain
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm7 && \
./withlock.sh run_r7_s42_reencode.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v7.py \
  --size R7conv --n-history 2 --rollout reencode --device mps --steps 5000 --batch 64 \
  --lr 3e-4 --wd 1e-4 --w-lat 0.05 --seed 42 --max-minutes 18.0 --save-forecasts \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r7_s42 && \
./withlock.sh run_r7_s42_plain.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v7.py \
  --size R7conv --n-history 2 --rollout plain --device mps \
  --eval-only run_r7_s42/model.pt --save-forecasts \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r7_s42

# Seed 43: identical protocol
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm7 && \
./withlock.sh run_r7_s43_reencode.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v7.py \
  --size R7conv --n-history 2 --rollout reencode --device mps --steps 5000 --batch 64 \
  --lr 3e-4 --wd 1e-4 --w-lat 0.05 --seed 43 --max-minutes 18.0 --save-forecasts \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r7_s43 && \
./withlock.sh run_r7_s43_plain.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v7.py \
  --size R7conv --n-history 2 --rollout plain --device mps \
  --eval-only run_r7_s43/model.pt --save-forecasts \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r7_s43

# Or via driver (checks disk >= 12 GiB & power AC/>=35%, runs s42 then s43, both rollout modes; sealed NOT included):
~/learner-ops/seven-problems-m3/PROBLEM-7/wm7/run_rank7.sh
```

### 6.3 Exact Locked Sealed-Exam Command *(ONCE ONLY, ONLY After Two-Seed Dev `PASS`)*
Evaluates the single pre-pinned dev-winning frozen checkpoint (`<WIN_SEED>` ∈ `{s42, s43}`) ONCE on **`../wm5/data/sealed_test.npz`** (`worlds 2000..2015`, `chmod 444`, pinned `sha256: 74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f`):
```bash
# Verdict of record (reencode) — single locked sealed exam
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm7 && \
./withlock.sh run_r7_sealed_reencode.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v7.py \
  --size R7conv --n-history 2 --rollout reencode --device mps --save-forecasts \
  --eval-only run_r7_<WIN_SEED>/model.pt --allow-sealed \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm5/data/sealed_test.npz \
  --out run_r7_<WIN_SEED>

# Optional one-knob isolation readout on the exact same frozen sealed checkpoint (non-gating):
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm7 && \
./withlock.sh run_r7_sealed_plain.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v7.py \
  --size R7conv --n-history 2 --rollout plain --device mps --save-forecasts \
  --eval-only run_r7_<WIN_SEED>/model.pt --allow-sealed \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm5/data/sealed_test.npz \
  --out run_r7_<WIN_SEED>
```

---

## 7. Verification Proof & Pinned File SHA-256 Hashes (Identical on M1 `forecast7/` & M3 `wm7/`)

- **`test_v7.py` (`16/16` unit tests PASS on BOTH M1 and M3 CPU, `EXIT=0`):** Covers the final scorer pin (`720adce8...`) plus untouched `forecast5/scorer.py` (`6ff1c135...`), canonical `board_swarm.py` untouched (`8ffc3fb8...`), exact `+4,096` param delta (`2,693,059` vs `2,688,963`) + `x_prev` sensitivity, strictly `k=1` loss with zero imagination grad on `encoder` (including via `x_prev`), **all 3 Point 2 history rules**, `wm_grad=False` zero leak in both rollout modes, `B=1` finite grads + V6/V7 checkpoint round-trip, sealed/power/incomplete-run guards, scorer selftest, lock safety, real stored Rank 6 re-scores, oracle/collapsed controls, strict amended-logic diff, both PARTIAL counterexamples, selective rare collapse, Kish-zero, and LINE/VARIANT/NONE strike classification.
- **M1 Architectural Sanity Checks (synthetic, CPU, `EXIT=0`):**
  - `x_prev` HUD pixel `(12, 6)` perturbation broadcasts to far terrain corners `(0, 0)` (`1.47e-4`), `(5, 7)` (`1.15e-3`), and `(11, 15)` (`5.90e-5`) in 1 step via `4×4` global self-attention.
  - Synthetic 2-frame HUD collision (`0.5→0.5` stay vs `0.2→0.5` wake with identical `x_t`, `tiny`, 250 steps): `img/copy` dropped **`0.9984 → 0.0084`** (`SYNTHETIC 2-FRAME COLLISION SOLVED CLEANLY`).
- **M3 MPS Re-Scores (`rescore_r6_s{42,43}`) & Timing Calibration (`timing_mps_r7.log`, `EXIT=0`, lock cleanly released):** Reproduces `wm6` `plain` to `0.000e+00` and diagnostic CPU `reencode` `0.4881 / 0.4827` to all 4+ decimal places; `R7conv` steady speed `117.1 ms/step` → `9.76 min` for `5,000` steps.
- **Final v2 Rank 6 end-to-end proof (`rescore_r6_s{42,43}_amended`, M3 MPS via `./withlock.sh`, `EXIT=0`):** Both real eval-only re-scores are `FAIL`, `strike_class=LINE`, reason `std_high_count_or_concentrated`; active-only rare pools are `[8,9]` at `0.085546` / `0.112601`. Full score JSONs are stored as `rank6_rescore_s{42,43}.json` and loaded by `test_11`.
- **M3 50-Step CPU Smoke Runs (`nice -n 10`, dev `heldout.npz`, zero MPS, `EXIT=0`, temp dirs cleaned):**
  - `tiny` (`50` steps, `batch=16`, `3.5s` train + `53.0s` eval, `reencode`) + `--eval-only` reload (`47.1s` `reencode`: exact match `E/B = 1.3815 / 1.3466 / 1.3705`, `ceil_abs = 15.4790`, `ceil_res = 0.9911`; `48.7s` `plain`: `E/B = 1.3815 / 2.5125 / 4.1716`, `k1` exact match).
  - Full `R7conv` (`50` steps, `batch=16`, `7.0s` train + `147.7s` CPU eval, `reencode`): `rec: 0.12383 → 0.01683`, `lat: 0.08730 → 0.00356`, `img/copy = 1.030`, `lat_burial = 4.68`, dev `E/B = 1.1045 / 1.1897 / 1.2561`, `ceil_abs = 4.5518`, `ceil_res = 0.8159`, `R7CONV_SMOKE_JSON_OK` (`diag_non_wake_interactions` + `diag_baselines_2f` verified).

| File | SHA-256 (Identical on M1 `forecast7/` & M3 `wm7/`) |
|---|---|
| `scorer.py` *(final v2 std gate + PARTIAL exclusivity + strike fields)* | `720adce8a1881c26510bf32850e4686f91cc7e03e5419ecef5e3819abfe62a93` |
| `withlock.sh` *(bit-identical to pinned `forecast5/withlock.sh`)* | `77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa` |
| `model_v7.py` | `5f3d7bdeb5dc3da58a5a9813123b2b4644d32504d992febe87dc469afbc2fb8d` |
| `train_v7.py` | `50974a27fa87b147f55afdb838a643ce635234e338f0bc7139523c686a6e4e2b` |
| `test_v7.py` | `9ad9ebaa9bd1be51ce14ac85b830cceb4b8e228a17fb950edee37d7a004860a5` |
| `rank6_rescore_s42.json` *(real final-v2 eval-only re-score)* | `63ee59fdc56f47a82df5471dc64a1ee2814f668bf3aa7d020f1adbdc9df904be` |
| `rank6_rescore_s43.json` *(real final-v2 eval-only re-score)* | `ce81fe4f2f6f324b1454455691129c1b5b72455e03b59aab0dfad5bdf814da9d` |
| `run_rank7.sh` | `b4e86c7dcd7afeba55bcaa56bfd000271219be8c7aad6d5c3720aa2f37318b05` |
| `timing_mps_r7.log` *(pre-amendment training-only timing; logged scorer hash is historical)* | `3d46ed9611872332394f77e01566b4392d27a527ec94e4671c86ac761424b5c8` |
| `rescore_r6_s42/score_dev_plain.json` *(M3 `wm7/`)* | `b12e24420fade1700f481b5b832df869361abfa49b70360c3f9607e8d2d69fd8` |
| `rescore_r6_s42/score_dev_reencode.json` *(M3 `wm7/`)* | `9b498e1064de33f9e1defbe4710ece049efb2664ce34246147f30fe0ca713483` |
| `rescore_r6_s43/score_dev_plain.json` *(M3 `wm7/`)* | `6ebbb6761b70e55100371cf50e94529724f9314e5a2722bd6b73715fe8660cb2` |
| `rescore_r6_s43/score_dev_reencode.json` *(M3 `wm7/`)* | `efa996baff990771ca4cd348263dd6f1d0693652f275390e67afb30135795efe` |
| `../wm5/data/train_dn.npz` *(M3, untouched)* | `4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6` |
| `../wm-harness/data/heldout.npz` *(M3 dev `1000..1015`, untouched)* | `add00c8bbc5d940ef5af006e983f7f34ef073aca9555430a601a47d9738413f0` |
| `../wm5/data/sealed_test.npz` *(M3 `2000..2015`, `chmod 444`, untouched)* | `74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f` |
| `../wm-harness/premonition_core_v2/board_swarm.py` *(canonical, untouched)* | `8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d` |

---

## 8. Plain-English Summary (For Ben)

We built **Rank 7 (`forecast7/` and M3 `wm7/`)** with exactly **one training upgrade** over Rank 6: letting the 2D picture-imagination module see **two past frames (`t-1` and `t`)** instead of one (`+4,096` weights = `+0.15%`) so it can tell `energy 8 → 9` wake-ups apart from `energy 6` sleeping ticks, while scoring the exact same weights both **with** picture-snapping between imagined steps (`reencode` — our official verdict) and **without** (`plain` — clean isolation).

- **Verified our Rank 6 re-score first:** Running the already-saved Rank 6 models through this exact official grader reproduced our earlier numbers to every decimal (`0.4881` and `0.4827` at step 5, beating the `0.4977` bar!).
- **Checked the rare-action lottery on 160 brand-new throwaway worlds (zero dev/sealed touched):** We proved the random player places **zero furnaces in 160 worlds**, so whenever `place_furnace`, `place_table`, or another rare button gets graded, it's usually decided by **1 single random sleep wake-up**. Lead adopted `n200_or_neff10` before training; bug hunt #2 then required active-only pooling plus a `>=25%` energy-dominance guard to stop selective collapse. The final v2 throwaway re-check cuts the realistic-85 false-fail rate from **44.5% → 23.5%**, keeps collapsed controls at **0% pass**, and keeps saved Rank 6 FAIL/FAIL with `strike_class=LINE`. `forecast5/scorer.py` is untouched; Rank 6's pinned historical verdict stays under the old ruler.
- **All 16 unit tests pass on both M1 and M3**, including real Rank 6 re-scores, exclusive k5-only PARTIAL, selective-collapse rejection, and strike classification. **Stopped here — ready for re-check.**

### Dated amendment (Lead, 2026-11-25, BEFORE any Rank 7 training): all-rare non-vacuous rule
- The HungerG re-check (NO-GO) found that `decide_std_gate` required a nonempty individual bucket, which §4.2 does not state. A perfect oracle on all-rare data (only pooled actions) therefore failed as `VARIANT/std_no_individual_active`.
- Fix (the reviewer's recommended option): the non-vacuous requirement is now "at least one gate active": an individually gated active action, OR an active rare pool. This is inherited from the old ruler's `active and ...`. The strike reason is renamed `std_no_active_gate` and fires only when nothing is active anywhere.
- Real dev data always has moves 1..4 individually gated, so Rank 6 re-scores are unchanged (test_11 PASS).
- New regression `test_12b`: all-rare oracle PASS, collapsed FAIL, all-quiet FAIL.
- `test_v7.py`: 17/17 PASS on M3 CPU, EXIT=0.
- New pins: scorer.py `d456b443ff6abdb86ff1861667e72e85bc4f83b73e4073ff4b7583708910195c` (pinned in model_v7.py), model_v7.py `8a0c22e530ef8498e99f92b2f23055f2cdcd9aa7892d18017a47fb5a54c491a8`, test_v7.py `d489c4a0f8f2c04176050b8f35e1f20bcb15ff0ee3cdac96770dfe89f4e63431`. These supersede `720adce8…` for the scorer.
- Nit left as-is: the legacy `verdict` field may say PARTIAL when the wall check fails; run_rank7.sh reads only the official `rank7_verdict`.
- Pin-record note: the `train_v7.py` docstring (line 6) and `rank6_rescore_s4{2,3}.json` still cite `720adce8…`. The docstring is left unchanged on purpose, because train_v7.py was running on the M3 at the time and must stay identical on both Macs; the pinned value that is enforced lives in model_v7.py. The Rank 6 fixtures are historical outputs of the 720adce8 scorer. The two changed hunks do not touch any path those fixtures exercise (test_11 PASS under d456b443).

### Dated amendment (Lead, 2026-11-25, during the Rank 7 dev run, before any verdict of record): no-active strike = LINE
- The second HungerG re-check (NO-GO) found that §5.2 reserves VARIANT for failures of the pooled rare bucket or its energy guard. "Nothing active anywhere" is not a pool failure.
- Fix: `std_no_active_gate` moves into the LINE reasons in `classify_strike`. The verdict logic is unchanged. A new assertion in test_12b checks that all-quiet gives `("LINE", ["std_no_active_gate"])`, and that all-rare collapsed gives VARIANT when the frequency-weighted gate passes and LINE/`std_frequency_weighted` when it fails.
- Pins (M1, test_v7.py 17/17 EXIT=0): scorer.py `ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912`, model_v7.py `c87f4110057bddaf4610c423e64c13dbe22f882aa9ea8dd53e4f3b57d7e67006`, test_v7.py `ba4e339547c6c150f30bf674bfd41765532d38850942a124486611d9f0f32c1f`. These supersede d456b443.
- The Rank 7 dev run that is in flight trains under d456b443. The two scorers differ only in the strike label for the all-quiet case, which real dev data cannot reach because moves 1..4 are always individually gated. The VERDICT OF RECORD is still an eval-only re-score of the saved Rank 7 checkpoints under ec44cdca, after an independent GO. M3 files sync after the run ends.
