# PROBLEM-7 PLAN AMENDMENT (Forecast5 / Rung 0 Ruler Fix & Sealed Test Worlds)

**Date:** 2026-11-24  
**Scope:** Rung 0 ONLY — fixes proven bugs in the `forecast4` scorer and `record.py` train/test lighting split, verifies the fixed ruler on synthetic drift tests and saved Step-5 / Step-6 / perfect-memory-oracle checkpoints (CPU-only, zero training, zero MPS), and seals fresh unseen test worlds (`2000..2015`) BEFORE any model ever sees them. **No Rung 1 training or model build is started here.**

**Unchanged legacy pass-mark numbers (kept verbatim per Lead ruling):**
- Pre-gate: real-board absolute decode ceiling `E_1/B_1 <= 0.70` (if `> 0.95` → `FAIL`).
- Accuracy: `E_1/B_1 <= 0.80`, `E_3/B_3 <= 0.90`, `E_5/B_5 <= 0.95`.
- Action shuffle: `>= 1.25×` at `k = 1` AND `>= 1.10×` at `k = 5` in `>= 12 / 16` worlds (`worlds_both >= 12`).
- Anti-collapse: predicted-change std ratio in `[0.25, 2.0]` and `pcs90_pred >= 0.5 * pcs90_real`.
- `PROVES WRONG`: `E_1/B_1 <= 0.80` AND `k1 shuffle_pooled < 1.05` → `FAIL`.

---

## 1. Proven Bugs Fixed in `forecast5/scorer.py` & `forecast5/record_v5.py` (Each Change & Why)

Every change below fixes a proven bug documented in [AUDIT.md](<project>/PROBLEM-7/neon-audit/AUDIT.md). Legacy files (`forecast4/`, `wm-harness/`, old `score.json`s, old `data/{train,heldout}.npz`) were **never edited**.

| # | Bug Fixed | Old Behavior (`forecast4.py` / `record.py`) | New Behavior (`forecast5/scorer.py` / `record_v5.py`) | Why This Is a Proven Bug Fix |
|---|---|---|---|---|
| **1** | **Bug A2 — Absolute-Frame Blur Trap** | Decoded full frame `P_k = RT(next_rows_k)`, then measured `P_1 - x_0` for `std_ratio`, `pcs90`, and `copy_ness`. | Open-loop residual-change decoding initialized **once** from `x_0`: `P_k = x_0 + (RT(next_rows_k) - RT(start_rows_0))` (zero peeking at intermediate true frames, verified by synthetic drift Check #3). | Static readout error (`RMSE = 0.0419` at `ceiling = 0.410`) is `5.0×` larger than true `noop` change (`0.00834`), making `std_ratio[noop] <= 2.0` **mathematically impossible even for a 100% perfect oracle** — AND gave dead Step-5 refit (`alpha = 0`, zero delta!) a fake `pcs90_pred = 107/111` PASS and fake `copy_ness = 0.605`. Real-board absolute ceiling `ceiling_abs_E_over_B <= 0.70` is STILL gated so a broken readout cannot hide. |
| **2** | **Bug A2b — Noise-Only `noop` `std_ratio` Lower-Bound Trap** | Required `all(0.25 <= ratio <= 2.0)` across all 17 actions including noise-only `noop` / unexecuted craft actions (`std_real = 0.008–0.014`, pure unseeded mob/daylight RNG). | Reports all per-action ratios transparently; gates `[0.25, 2.0]` on **active actions (`std_real >= 0.02`, `n >= 20`)** AND requires the **frequency-weighted mean `std_ratio`** across all `n >= 20` actions to lie in `[0.25, 2.0]`. | On pure RNG `noop` transitions, a perfect deterministic physics predictor predicts `Δx = 0`, giving `ratio < 0.25` and failing the old check despite being physically exact. Active actions cover ~89% of all transitions (all 4 moves, `do`, `sleep`, `place`). |
| **3** | **Bug A10 — `PARTIAL` & `proves_wrong` Verdict Logic** | `PARTIAL` triggered even if `k3`/`k5` accuracy passed while `k5` shuffle failed (`worlds_both < 12`); `proves_wrong` (`E1/B1 <= 0.80` & `shuffle_pooled < 1.05`) from `PLAN.md:38` was never computed. | Computes `proves_wrong = (E1/B1 <= 0.80 and shuffle_pooled < 1.05)` → forces `FAIL`; `PARTIAL` fires ONLY when `k1` marks + `k1` shuffle + anti-collapse + ceiling pass, `not proves_wrong`, AND `k3` or `k5` accuracy fails (matching `PLAN.md:36` & `wm_fit.py:356`). | Prevents an action-blind multi-step rollout from falsely receiving `PARTIAL` or `PASS`. |
| **4** | **Bug A11a — Per-Step Action Shuffle** | Permuted whole `k`-step action tuples across windows within each world (`forecast4.py:98-99`). | Permutes individual per-step actions within each world (`shuffle_actions_per_step`, seed 43), matching `wm_fit.py:199-209`. | Preserves per-step marginal action frequencies without artificially locking `k`-step autocorrelation structure during multi-step shuffles. |
| **5** | **Bug A11b — Horizon-`k` Moved Mask** | Filtered `k = 3, 5` shuffle windows using only 1-step motion `((hfr[xi+1] - x0)**2).mean() > 1e-6`. | Filters horizon-`k` windows using horizon-`k` motion `((hfr[xi+k] - x0)**2).mean() > 1e-6` (and still logs `moved_step1_windows` for comparison). | Prevents dropping `k = 3, 5` windows where step 1 was `noop` and steps 2–5 moved. |
| **6** | **Bug A11c — World-ID Keyed Ratios & Paired World CIs** | Stored `shuffle_world_ratios` as a positional list and zipped `k1` and `k5` positionally (`forecast4.py:118`). | Stores `shuffle_world_ratios` as a `{world_id: ratio}` dict and matches `worlds_both` by identical `world_id`; also logs paired 95% bootstrap CIs across worlds. | Eliminates silent world-index mismatch if any world has 0 moved windows. |
| **7** | **Bug A3 + A13 — Matched 300-Step Day/Night Split & Within-Episode Moved Stat** | `record.py` stopped training episodes at `t = 125` (before Crafter's 300-step day/night cycle reached darkness) while held-out ran to `t = 250`; logged `moved` across episode boundaries. | `record_v5.py` records `350`-step episodes (`MAX_EPISODE = 350`, spanning Crafter's full 300-step light cycle), saves true `env._world.daylight`, computes `moved` strictly within episodes, and seals 16 fresh unseen test worlds (`2000..2015`). Legacy `heldout.npz` (`1000..1015`) remains untouched for side-by-side comparison. | Removes the train=day / test=night OOD shift while preventing reuse of the 16 inspected dev worlds (`1000..1015`) as the final unseen exam. |

**Non-gating diagnostics added in `forecast5/scorer.py` (reported only; do not alter legacy verdict marks):**
- `act_baseline_E_over_B` (`M_a [x_t, 1]` directly) and `shift_or_stay_E_over_B` (destination center-crop shift-or-stay baseline).
- Paired 95% bootstrap CIs across worlds for `E_over_B` and `shuffle_pooled`.
- `ceiling_res_E_over_B` alongside gated `ceiling_abs_E_over_B`.

---

## 2. Sealed Fresh Unseen Test Worlds & New Day+Night Training Data (Sealed Before Any Model Sees Them!)

Recorded on M3 CPU (`nice -n 10`, zero GPU/MPS, disk guard `>= 12.0 GiB`: `12.63 GiB` free before → `12.58 GiB` free after). **Zero models have ever been evaluated on `sealed_test.npz`.** Permissions on M3 `sealed_test.npz` are set read-only (`chmod 444`).

| Split | Path on M3 (`~/learner-ops/seven-problems-m3/PROBLEM-7/...`) | World IDs (Disjoint!) | RNG Seed | Per World / Max Ep | Transitions (Episodes) | Within-Ep Moved | Daylight `<0.4 / 0.4–0.8 / ≥0.8` (mean) | Bytes | SHA-256 |
|---|---|---|---:|---:|---:|---:|---|---:|---|
| **Legacy Train** *(untouched)* | `wm-harness/data/train.npz` | `0..159` (160) | `1234` | `125 / 250` | `20,000` (175) | `0.8210` | Day-only (`t < 125`: `20,000/0/0`; bright min `0.1515`, mean `0.2337`) | `31,634,258` | `d423b5b9eecd68fd21981381781c9821775ecddc4ae3787d85d7c395215e505c` |
| **Legacy Dev Held-Out** *(untouched)* | `wm-harness/data/heldout.npz` | `1000..1015` (16) | `1234` | `313 / 250` | `5,008` (34) | `0.8748` | Day + Night (`t`: `3,842/1,166/0`; bright min `0.1087`, mean `0.2295`) | `7,906,842` | `add00c8bbc5d940ef5af006e983f7f34ef073aca9555430a601a47d9738413f0` |
| **New Day+Night Train** | `wm5/data/train_dn.npz` | `3000..3079` (80) | `5001` | `350 / 350` | `28,000` (199) | `0.8644` | `3,198 / 4,903 / 19,899` (`0.805`) | `44,328,742` | `4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6` |
| **SEALED Fresh Test** *(chmod 444, untouched by any model)* | `wm5/data/sealed_test.npz` | `2000..2015` (16) | `5002` | `350 / 350` | `5,600` (39) | `0.8652` | `634 / 950 / 4,016` (`0.806`) | `8,865,702` | `74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f` |
| **Data Manifest** | `wm5/data/MANIFEST.json` (+ M1 `forecast5/DATA-MANIFEST.json`) | — | — | — | — | — | — | `2,143` | `a363f1e4494a365fed3a8a8fef90d43a8e4108a31263adbb53b871dddd01cbcd` |

---

## 3. Rung-0 Code SHA-256 Hashes (Identical on M1 `forecast5/` & M3 `wm5/`)

- `record_v5.py`: `16f6505fb9d0ccb4c2a6a2252884f76fe5de83fce345f83ff7a7eacf843f083a`
- `scorer.py`: `90d9b0effaba5188b3a654b6ee6308ba40e6d68efc972cc95492a270030a69c9`
- `verify_ruler.py`: `e90808a9922de2d64f5fb66bfa4cb3606f3704d30fd98f21eb35b3d992588418`
- `DATA-MANIFEST.json` / `MANIFEST.json`: `a363f1e4494a365fed3a8a8fef90d43a8e4108a31263adbb53b871dddd01cbcd`

---

## 4. Ruler Proof Results (`scorer.py --selftest` & `verify_ruler.py`)

### 4.1 Synthetic Drift & Verdict Integrity Checks (`scorer.py --selftest`, exit code `0`)
- **Check 1 (Perfect deltas at `k = 1, 3, 5`):** `E = 0.0, 0.0, 0.0`, verdict = **`PASS`**.
- **Check 2 (Zero deltas at `k = 1, 3, 5`):** `|E - copy_SSE| = 0.0, 0.0, 0.0`, `copy_ness = 0.0`, `pcs90_pred = 1`, `std_ok = False`, `pcs_ok = False`, verdict = **`FAIL`**.
- **Check 3 (Constant per-step error `c = 0.01`, single init at `x_0`):** endpoint signed bias = `0.0100, 0.0300, 0.0500` (`k * c` to `1e-15`), RMSE = `0.0100, 0.0300, 0.0500` — **proves zero intermediate true-frame peeking**.
- **Check 4 (Action-blind accurate predictor):** `proves_wrong = True`, verdict = **`FAIL`**.
- **Check 5 (Bug A10 — `k1/k3/k5` accuracy pass & `k1` shuffle pass, `k5` shuffle fails):** verdict = **`FAIL`** (NOT `PARTIAL`).

### 4.2 Saved-Checkpoint Proof on Legacy Dev Held-Out (`1000..1015`, `verify_ruler.py`)
Raw log: [verify_ruler.log](<project>/PROBLEM-7/forecast5/verify_ruler.log) (M3 CPU, `nice -n 10`, zero GPU/MPS; `sealed_test.npz` NEVER touched).

| Evaluated Model / Oracle | Ruler | `E/B` (`k = 1 / 3 / 5`) | `shuffle_pooled` (`k1 / k5`) | Worlds (`k1 / k5 / both`) | `copy_ness` (`k1`) | `pcs90` (`real=111`) | `noop` `std_ratio` | `std_ok` | Verdict |
|---|---|---|---:|---|---:|---:|---:|---|---|
| **Dead Step-5 Refit** (`run_forecast3_refit`) | OLD abs | `1.331 / 1.141 / 1.175` | `1.000 / 1.000` | `0 / 0 / 0` | **`0.6046` (FAKE!)** | **`107` (`True`, FAKE!)** | `6.376` | `False` | FAIL |
| **Dead Step-5 Refit** (`run_forecast3_refit`) | **NEW `forecast5`** | ~copy | `1.000 / 1.000` | `0 / 0 / 0` | **`0.002169`** *(279× drop)* | **`5` (`False`)** *(21× drop)* | — | **`False`** | **FAIL** |
| **Exact Zero-Delta Identity** (`next === st`) | **NEW `forecast5`** | `1.055` (`k1`) | — | — | **`0.000000`** | **`1` (`False`)** | **`0.000`** | **`False`** | **FAIL** |
| **Perfect-Memory Oracle** (`real_board(t+k)` via `RT6`) | OLD abs | `0.4102 / 0.1889 / 0.1451` | — | — | `1.124` | `115` (`True`) | **`4.962` (FAIL!)** | **`False`** | **FAIL** |
| **Perfect-Memory Oracle** (`real_board(t+k)` via `RT6`) | **NEW `forecast5`** | **`0.3152 / 0.2221 / 0.1964`** | — | **`16 / 16 / 16`** | `0.810` | **`88` (`True`)** | **`1.372`** (`fw=0.952`) | **`True`** | **`PASS`** |
| **Linear Per-Action (`M_a [x_t, 1]`)** | **NEW `forecast5`** | **`0.5039 / 0.5805 / 0.6311`** | **`2.858 / 1.813`** | **`16 / 16 / 16`** | — | **`117` (`True`)** | — | **`True`** | **`PASS`** |
| **Saved Step-6** (`run_forecast4`) | OLD abs | `1.1913 / 1.0891 / 1.1169` | `1.038 / 1.078` | `0 / 7 / 0` | `0.396` | **`112` (`True`, FAKE!)** | `4.912` | `False` | FAIL |
| **Saved Step-6** (`run_forecast4`) | **NEW `forecast5`** | **`1.0257 / 1.0944 / 1.1457`** | `1.043 / 1.076` | **`0 / 0 / 0`** | — | **`3` (`False`)** *(37× drop!)* | — | **`False`** | **FAIL** |

*(Execution note: `verify_ruler.py` printed all lines above cleanly before tripping line 199's over-strict `assert s5_new["k1"]["pcs90_pred"] == 1`, because Step-5's final `imagine_alpha` was `~4e-5` rather than literal `0.0`, producing `pcs=5/111` (`pcs_ok=False`) and `copy_ness=0.002169` — while exact zero-delta identity in both `scorer.py --selftest` and `run_xray.py` gave literal `pcs=1/111` and `copy_ness=0.0000`. The assertion in local `forecast5/verify_ruler.py` was relaxed to `pcs_ok is False and pcs <= 10 and copy_ness < 0.01`, and NOT re-run on M3 because M3 disk had fallen to `648 MiB` free.)*

---

## 5. Rung 0 Complete & M3 Disk Cleared

- **Rung 0 deliverables complete:** X-ray ([XRAY.md](<project>/PROBLEM-7/neon-audit/XRAY.md), fork = **skip Rank 4 → go to Rank 3**), fixed ruler ([scorer.py](<project>/PROBLEM-7/forecast5/scorer.py), upgraded to `forecast5-v2-rung1` with visual blocked-vs-open readout; all synthetic drift checks & saved-checkpoint proofs re-verified with `EXIT=0`), matched 300-step day+night train split (`wm5/data/train_dn.npz`), and **sealed fresh unseen test worlds** (`wm5/data/sealed_test.npz`, worlds `2000..2015`, `chmod 444`, sha256 `74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f`, zero models have ever seen it).
- **M3 disk cleared:** Now **`28 GiB` free** (`27.85 GiB` verified after smoke runs; swap `4.0 GiB`).

---

## 6. RUNG 1 / RANK 3 PIN — Un-Choke the Shared Brain *(Pinned 2026-11-24 BEFORE Any Scored Run)*

**Scope & Hard Rules:**
- **Experimental copy ONLY** in `PROBLEM-7/forecast5/` and M3 `~/learner-ops/seven-problems-m3/PROBLEM-7/wm5/`. Canonical `premonition_core_v2/board_swarm.py` (`sha256: 8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d`) is **never edited** and its SHA-256 is verified at runtime before any instance-only method binding.
- **100% learned:** Zero game-specific rules, zero OS/memory cheats. Context-blind imagination (`enc_act`: ONLY the action token in context memory; zero frame-`t` photo leaked into multi-step rollouts).
- **Strict `k = 1` real-transition training ONLY** (`PLAN.md:6`): Trained strictly on `wm5/data/train_dn.npz` (`3000..3079`, 28,000 day+night transitions). Rollouts `k = 3, 5` are scored open-loop (single init at `x_0`, zero intermediate peeking) and never trained.
- **Start board detached on imagination loss** (imagining cannot corrupt seeing), and `wm_grad=False` planning detaches all cell/model parameters and start rows (anti-wishful-thinking, verified by unit tests).
- **Dev vs. Sealed discipline:** All 4 arms are evaluated on legacy dev worlds `1000..1015` (`../wm-harness/data/heldout.npz`). `train_v5.py` **refuses** any path containing `"sealed"` unless BOTH `--eval-only` AND `--allow-sealed` are passed. Only the single winning frozen checkpoint selected on dev is ever evaluated once on `wm5/data/sealed_test.npz` (`2000..2015`).
- **Wall-clock budget & exact fixed-step arm fairness:** Calibrated directly on M3 MPS (`P7toy`, `batch = 64`, 25 steps unscored via `./withlock.sh`, `417.5–425.3 ms/step`; slowest arm `bundle` = **`21.26 min`** for `3,000` steps, all 4 arms within `1.8%`: `20.88–21.26 min`). Every arm runs the exact same **`--steps 3000`** with a safety cap `--max-minutes 28.0` (`+6.7 min` thermal-throttle headroom, still `< 30 min` incl. ~25s MPS eval). `train_v5.py` **FAILS LOUDLY** (`RuntimeError("INCOMPLETE RUN...")`, non-zero exit, refuses to save `model.pt` or `score_dev.json`) if `done < args.steps`, and aborts before `opt.step()` if `grad_norm` is non-finite.

### 6.1 Exact Arms & Execution Order (Bundle-First + Leave-One-Out Ablations)

**Why bundle-first (`Arm 1`) followed by 3 clean leave-one-out ablations (`Arms 2–4`) is justified (same methodology as Problem-1 Family B / `--signal-path`):**  
Our Rung-0 X-ray ([XRAY.md](<project>/PROBLEM-7/neon-audit/XRAY.md)) proved **three coupled failure clogs** block learning simultaneously on the unmodified cell. Shared harness hygiene held constant across all 4 arms: brightness-preserving centered patches `(frames - 0.5)`, context-blind imagination (`enc_act` only), matched `focus = state.focus`, smooth bounded update `3.0 * tanh(raw_delta / 3.0)`, detached start board + stop-grad anchor `x_rec_t.detach()` on `l_img_res`, and `RowLNDecoder` (per-row `LayerNorm(D)` → `Linear(D, 32)` → full-rank `Linear(2048, 768)` + zero-init-last `MLP(2048 → 512 → 768)`). The 3 switchable knobs are:
- **K1 (`use_signal_path`):** Problem-1's 99% signal-path fix (`ContextRead` 1-layer masked self-attention in `encode_context`, `door_floor = 0.15` on slow rows in both `tick` and `imagine`, private-generator `signal_path_init` keeping `row_pos_emb` at `1.0`). Without K1, the board is buried **`3,054 : 1`** (`6,225 : 1` entering `_trunk`).
- **K2 (`use_act_film`):** Zero-init FiLM intercom (`act_film: Linear(D, 2*d)`) broadcasting the action to all 64 rows before `_trunk`. Without K2, in a 2-block `P7toy` trunk the button enters only 1 row out of 65 (`1,437×` weaker step-0 gradient; Step-6 had `3,986×` weaker `screen × action` interaction than screen-blind tint).
- **K3 (`use_res_loss`):** Residual-matched joint loss `1.0 * l_rec + 1.0 * l_img_res + 0.25 * l_img_abs + 0.005 * l_row_rel + 0.01 * aux` vs. total-weight-matched absolute-only `1.0 * l_rec + 1.25 * l_img_abs + 0.005 * l_row_rel + 0.01 * aux` (total imagine pixel weight held fixed at `1.25` across both!).

Shared modules (`cell`, `reader`, `pos`, `action_emb`, `dec`) are created first in fixed order before optional `ctx_read`/`act_film`, so all 4 arms start with **bit-identical** shared initialization at `seed = 42` (verified by `test_11_arm_bit_identical_shared_init`). Testing K2 alone on a `3,054 : 1`-buried board or K1 alone behind a broken frozen ridge would waste MPS compute on already-proven failure modes. Therefore we run **`Arm 1 (bundle)` first**; if and only if Arm 1 does not trigger `rank3_proved_wrong`, we run **Arms 2, 3, and 4** (each removing **exactly ONE knob**):

| Order | Arm CLI (`--arm`) | K1 (`signal_path`) | K2 (`act_film`) | K3 (`l_img_res` loss) | Purpose / Decision Gate |
|---|---|---:|---:|---:|---|
| **1** | `bundle` | **ON** | **ON** | **ON** | Primary Rank-3 test (`P7toy`, 3,000 steps, seed 42, `< 30 min`). **If `rank3_proved_wrong == True` → STOP immediately (skip Arms 2–4).** |
| **2** | `no_signal_path` | **OFF** | ON | ON | Leave-one-out ablation of K1 (vendored `BoardCell` init, no `ContextRead`, `door_floor = 0.0`). Proves whether un-choking earned its keep. |
| **3** | `no_act_film` | ON | **OFF** | ON | Leave-one-out ablation of K2 intercom (`act_film = None`; action enters via canonical 1 action row `ha` + `enc_act` only). Proves whether 64-row broadcast earned its keep. |
| **4** | `abs_loss_only` | ON | ON | **OFF** | Leave-one-out ablation of K3 residual-matched loss (`1.25 * l_img_abs` instead of `1.0 * l_img_res + 0.25 * l_img_abs`, scored identically). Proves whether residual-matched loss earned its keep. |
| **5** *(final only)* | `--eval-only --allow-sealed` | *(winner)* | *(winner)* | *(winner)* | Single read-only locked exam on `wm5/data/sealed_test.npz` (`2000..2015`) using the single dev-selected frozen checkpoint (`guard_sealed_path` resolves symlinks AND checks pinned sealed SHA-256). |

### 6.2 Pinned Rung-1 Pass Bars & Dev Baseline References (`train_dn.npz` → Dev `1000..1015`, Re-Pinned Post-Bug-Hunt)

Measured on `scorer.py` (`forecast5-v3-rung1`, `BLOCK_OPEN_ALPHA_THRESH = 0.40`, `TILE_SHIFT_PX = 1.75`, `BLOCK_OPEN_MIN_SHIFT_ENERGY = 5e-4`, 100% prediction-blind):
- **Destination + bilinear-shifted source player-sprite masking (`classify_move_displacement`):** Masks BOTH the destination `2×2` player sprite (`rows 5..6, cols 7..8`) AND every crop pixel whose bilinear shift samples from `[5:7, 7:9]` with positive weight (`8` masked / `88` clean terrain pixels per direction). Verified against true Crafter `env._player.pos` on disjoint throwaway worlds: **`98.99%`** accuracy on world `9999` (`6 eps × 200`, `FN = 6/526`, **`FP = 0/68`**) and **`99.22%`** on worlds `9990..9999` (`10 worlds × 200`, `FN = 10/1,072`, **`FP = 0/217`**). On dev `1000..1015`, `valid_moves = 3,034` (`true_open = 2,222`, **`true_blocked = 812`**, removing `299` sprite-bleed-corrupted blocked labels and cutting ambiguous `alpha ∈ [0.25, 0.55]` `4.7×` from `189 → 40`).
- **Centered `shift_or_stay` baseline:** Uses a player-centered `6×6` crop (`rows 3:9, cols 5:11`, symmetrically covering 2 rows above/below and 2 cols left/right of `[5:7, 7:9]`, fixing `move_up` visibility in rows `3..4`) and fits its shift model (`Mshift`) and gate (`Wgate`) strictly on `train_dn.npz` using the fixed `classify_move_displacement` labels (valid moves only).

| Baseline / Fairness Probe (fit on `train_dn.npz`, scored on dev `1000..1015`) | `k = 1` `E/B` `[95% CI]` | `k = 3` `E/B` `[95% CI]` | `k = 5` `E/B` `[95% CI]` | `shuf` (`k1/k5`, worlds) | Block/Open (`n=3,034`, open `2,222`, blocked `812`): `fb` / `fo` / `mean_err` | Legacy / `rung1` / `r3_wrong` |
|---|---|---|---|---|---|---|
| **Copy (`x_0`)** | `1.0571` `[1.0505, 1.0627]` | `1.1459` `[1.1264, 1.1608]` | `1.2132` `[1.1849, 1.2351]` | `1.000 / 1.000` (`0/0`) | `1.0000` / `0.0000` / `0.5000` | `FAIL` / `FAIL` / `True` |
| **Linear Per-Action (`M_a [x_t, 1]`)** | `0.4738` `[0.4426, 0.5116]` | `0.5578` `[0.5304, 0.5911]` | `0.6103` `[0.5846, 0.6428]` | `2.995 / 1.856` (`16/16`) | `0.0014` / `0.9926` / `0.4970` | `PASS` / `FAIL` / `True` |
| **Shift-or-Stay (`sos`, strongest baseline)** | **`0.2853`** `[0.2623, 0.3094]` | **`0.4068`** `[0.3781, 0.4348]` | **`0.4977`** `[0.4657, 0.5287]` | `4.716 / 2.328` (`16/16`) | **`0.0207` / `0.1552` / `0.0879`** | `PASS` / `FAIL` / `False` |
| *Fairness probe:* **Damped Oracle (`0.7×`)** | `0.0951` `[0.0945, 0.0956]` | `0.1031` `[0.1014, 0.1045]` | `0.1092` `[0.1066, 0.1112]` | `13.395 / 10.582` (`16/16`) | **`0.0153` / `0.0000` / `0.0077`** (`91.3%` cut) | **`PASS` / `PASS` / `False`** |
| *Fairness probe:* **Camera-Shift-Only (`0.67`)** | `0.4813` `[0.4547, 0.5145]` | `0.6177` `[0.5904, 0.6508]` | `0.6991` `[0.6665, 0.7349]` | `2.697 / 1.599` (`16/16`) | `0.0086` / **`0.9926`** / **`0.5006`** | `PASS` / **`FAIL`** / **`True`** |
| *Fairness probe:* **Camera-Shift-Only (`1.00`)** | `0.5797` `[0.5249, 0.6445]` | `0.7280` `[0.6621, 0.8036]` | `0.8594` `[0.7729, 0.9499]` | `3.235 / 1.575` (`16/16`) | `0.0000` / **`0.9975`** / **`0.4988`** | `PASS` / **`FAIL`** / **`True`** |

**Exact Rung-1 `PASS` Bar (ALL must hold simultaneously; matches `scorer.py:rung1_verdict == "PASS"` 1-to-1):**
1. **Beat BOTH baselines (`linear_Mact` AND `shift_or_stay`) AND legacy accuracy bars at ALL of `k = 1, 3, 5`:**
   `E_k / B_k < min(E_act / B_k, E_sos / B_k)` AND `E_1/B_1 <= 0.80`, `E_3/B_3 <= 0.90`, `E_5/B_5 <= 0.95` (on dev: **`< 0.2853`, `< 0.4068`, `< 0.4977`**; paired 95% world bootstrap CI for `E / E_strongest_baseline` also reported).
2. **Blocked vs. Open Move Physics Cut (`>= 25%`, neither rate worse):**
   `model.mean_err <= 0.75 * base.mean_err` (on dev: **`<= 0.0659`**) **AND** `model.false_block_rate <= base.false_block_rate` (`<= 0.0207`) **AND** `model.false_open_rate <= base.false_open_rate` (`<= 0.1552`). Verified fair above: `0.7×` damped oracle PASSES (`fb = 0.0153 <= 0.0207`, `fo = 0.0000 <= 0.1552`, `mean_err = 0.0077`, `rung1 = PASS`), while obstacle-blind camera-shift-only predictors (`0.67` and `1.00`) FAIL (`fo >= 0.9926`, `mean_err ~ 0.500`, `rung1 = FAIL`, `rank3_proved_wrong = True`).
3. **Fixed-ruler legacy + shuffle + anti-collapse gates:**
   - Real-board absolute ceiling `ceiling_abs_E_over_B <= 0.70` (`> 0.95` → `FAIL`).
   - Action shuffle: **`k1 shuffle_pooled >= 1.25`** (explicitly required so pooled action sensitivity across all moved windows is verified and consistent with §6.3 `rank3_proved_wrong`, preventing any model from passing `rung1_verdict` while triggering `rank3_proved_wrong`), `worlds_k1_shuffle >= 12` (`>= 1.25×` per world at `k = 1`), `worlds_both >= 12` (`>= 1.25×` at `k = 1` AND `>= 1.10×` at `k = 5` in the same world), and `not proves_wrong`.
   - Anti-collapse: `std_ratio_active_and_fw_ok == True` (`[0.25, 2.0]` on active actions `std_real >= 0.02, n >= 20` and frequency-weighted mean) AND `pcs90_pred >= 0.5 * pcs90_real`.
- **`rung1_verdict == "PARTIAL"`:** `k = 1` meets legacy `<= 0.80` + beats baselines + `block_open` cut `>= 25%` (neither worse) + `k1 shuffle_pooled >= 1.25` + `worlds_k1_shuffle >= 12` + `std_ok` + `pcs_ok` + `ceiling <= 0.70` + `not proves_wrong`, while `k = 3` or `k = 5` misses (legacy `verdict` is also reported transparently alongside `rung1_verdict`).

### 6.3 Exact Result That Proves Rank 3 Wrong (`PROVES WRONG` / Stop Trigger)

On **Arm 1 (`bundle`)** after 3,000 steps on `train_dn.npz` (dev `1000..1015`), Rank 3 is **PROVED WRONG** if ANY of:
1. **Ruler/cheat failure:** `ceiling_abs_E_over_B > 0.95` OR `proves_wrong == True` (`E_1/B_1 <= 0.80` with `k1 shuffle_pooled < 1.05`).
2. **Fails to beat stateless linear baseline at `k = 1`:** `k1 E_over_B >= 0.4738` (cannot even match stateless `M_a [x_t, 1]`).
3. **Weak action coupling:** `k1 shuffle_pooled < 1.25` OR `worlds_k1_shuffle < 12`.
4. **No obstacle-physics gain despite clear seeing:** `ceiling_abs_E_over_B <= 0.25` (board holds the screen clearly), yet `block_open.model.mean_err >= block_open.shift_or_stay.mean_err` (`>= 0.0879` on dev — zero improvement over a linear centered `6×6` crop).

If triggered: **STOP immediately** (skip Arms 2–4), inspect `forecasts_dev.npz`, and escalate to the next planned fork (`64×64` patch resolution or Rank 6 dedicated spatial visual module).

### 6.4 Exact Launch Commands (M3 MPS Under Fixed `./withlock.sh`, Exact 3,000 Steps, Calibrated `<= 22 min`)

Run from `~/learner-ops/seven-problems-m3/PROBLEM-7/wm5` on M3 (uses fixed local `./withlock.sh` which passes real exit codes through, streams unbuffered logs preserving warnings, and releases `/tmp/premonition_m3_mps.lock` on `EXIT`/`INT`/`TERM` after stopping the child):

```bash
# Arm 1 (FIRST — bundle: K1 + K2 + K3; stop if PROVES WRONG triggers)
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm5 && \
./withlock.sh run_r1_bundle.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v5.py \
  --arm bundle --size P7toy --device mps --steps 3000 --batch 64 --lr 3e-4 --wd 1e-4 --seed 42 \
  --max-minutes 28.0 --save-forecasts \
  --train-data data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r1_bundle

# Arm 2 (Leave-one-out ablation of K1: no signal_path) — ONLY if Arm 1 does not trigger PROVES WRONG
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm5 && \
./withlock.sh run_r1_no_signal_path.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v5.py \
  --arm no_signal_path --size P7toy --device mps --steps 3000 --batch 64 --lr 3e-4 --wd 1e-4 --seed 42 \
  --max-minutes 28.0 --save-forecasts \
  --train-data data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r1_no_signal_path

# Arm 3 (Leave-one-out ablation of K2: no act_film intercom) — ONLY if Arm 1 does not trigger PROVES WRONG
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm5 && \
./withlock.sh run_r1_no_act_film.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v5.py \
  --arm no_act_film --size P7toy --device mps --steps 3000 --batch 64 --lr 3e-4 --wd 1e-4 --seed 42 \
  --max-minutes 28.0 --save-forecasts \
  --train-data data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r1_no_act_film

# Arm 4 (Leave-one-out ablation of K3 residual-matched loss: abs_loss_only) — ONLY if Arm 1 does not trigger PROVES WRONG
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm5 && \
./withlock.sh run_r1_abs_loss_only.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v5.py \
  --arm abs_loss_only --size P7toy --device mps --steps 3000 --batch 64 --lr 3e-4 --wd 1e-4 --seed 42 \
  --max-minutes 28.0 --save-forecasts \
  --train-data data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r1_abs_loss_only

# FINAL LOCKED SEALED EXAM (ONCE ONLY, on single dev-selected winner <WIN_ARM>, e.g. bundle)
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm5 && \
./withlock.sh run_r1_sealed_eval.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v5.py \
  --arm <WIN_ARM> --size P7toy --device mps --seed 42 --save-forecasts \
  --eval-only run_r1_<WIN_ARM>/model.pt --allow-sealed \
  --train-data data/train_dn.npz --eval-data data/sealed_test.npz \
  --out run_r1_<WIN_ARM>
```

### 6.5 Verification Proof & Pinned File SHA-256 Hashes (Identical on M1 `forecast5/` & M3 `wm5/`)

**Post-bug-hunt fixes & verification completed (zero `sealed_test.npz` touch, zero scored runs, M3 free disk `28 GiB` / `27.81 GiB`, lock cleanly released):**
- **Bug-hunt Requirement 1 (`scorer.py` sprite-bleed fix):** `classify_move_displacement` masks both destination `[5:7, 7:9]` and bilinear-shifted source footprint of `[5:7, 7:9]` (`8` masked / `88` clean terrain pixels/direction). Ground truth vs Crafter `env._player.pos`: **`98.99%`** on world `9999` (`6 eps × 200`, `FN=6/526`, `FP=0/68`) and **`99.22%`** on worlds `9990..9999` (`10 worlds × 200`, `FN=10/1,072`, `FP=0/217`). Dev `true_blocked` dropped `1,111 → 812` (`valid=3,034`, `open=2,222`).
- **Bug-hunt Requirement 2 (`shift_or_stay` & fairness):** Centered `6×6` crop (`rows 3:9, cols 5:11`), fit strictly on `train_dn.npz` fixed displacement labels (`valid_mv` only). Re-pinned `shift_or_stay` dev bar: `E/B = 0.2853 / 0.4068 / 0.4977`, `fb = 0.0207`, `fo = 0.1552`, `mean_err = 0.0879`. Confirmed `0.7×` damped oracle **PASSES** `rung1_verdict` (`fb=0.0153`, `fo=0.0000`, `me=0.0077`) and obstacle-blind camera-shift-only (`0.67` and `1.00`) **FAILS** `rung1_verdict` (`fo>=0.9926`, `me~0.500`, `rank3_proved_wrong=True`).
- **Bug-hunt Requirement 3 (MPS timing calibration & fixed-step arm fairness):** Short unscored M3 MPS timing via `./withlock.sh` (`P7toy`, `batch=64`, `25` steps = `5` warmup + `20` steady-state, `11.0–13.2 s/arm`, dev only, unscored):
  - `bundle`: **`425.3 ms/step`** → `3,000` steps = **`21.26 min`** (slowest arm, `<= 22 min`)
  - `no_signal_path`: `422.1 ms/step` → `3,000` steps = `21.10 min`
  - `abs_loss_only`: `418.9 ms/step` → `3,000` steps = `20.95 min`
  - `no_act_film`: `417.5 ms/step` → `3,000` steps = `20.88 min`
  - All 4 arms keep exact `--steps 3000` with `--max-minutes 28.0`; `train_v5.py` raises `RuntimeError("INCOMPLETE RUN...")` (no save/score) if `done < args.steps`.
- **Bug-hunt Requirement 4 (should-fix items):** Added fixed `withlock.sh` in `forecast5/` & `wm5/` (real exit code, unbuffered `tee`, preserves warnings, `EXIT`/`INT`/`TERM` trap stopping child before releasing lock), finite `grad_norm` abort before `opt.step()`, strict `ck_arm != args.arm` check, non-gating `diag_pred_abs_E_over_B` logging, and synced `k1 shuffle_pooled >= 1.25` in §6.2.
- **`test_v5.py` (16/16 unit tests PASS on BOTH M1 and M3, zero warnings, `EXIT=0`):** Includes new `test_13` (source+dest sprite masking), `test_14` (centered `move_up` crop + HUD-flicker-immune labels + `0.7×` damped oracle PASS / camera-shift FAIL), `test_15` (`done < steps` loud failure + non-finite `grad_norm` guard + missing `meta.arm` refusal), and `test_16` (`withlock.sh` exit code `0`/`7`, warning preservation, `SIGTERM` trap lock release).
- **`verify_ruler.py` on M3 CPU (`136.38s`, `EXIT=0`):** `ALL_PASS`.
- **30-step `P7toy` CPU smoke (`--arm bundle --steps 30 --batch 16`, dev only, `EXIT=0`):** `12.2s` train + `80.1s` CPU eval, verified `w_row`/`gnorm` logs and re-pinned `base=0.2853/0.4068/0.4977`, `bo_base=0.0879`, cleaned temp dir afterwards.

| File | SHA-256 |
|---|---|
| `record_v5.py` | `16f6505fb9d0ccb4c2a6a2252884f76fe5de83fce345f83ff7a7eacf843f083a` |
| `scorer.py` *(upgraded `forecast5-v3-rung1`)* | `6ff1c135c0eeb2085aa4d49479b915cc5630f355b6d4ad3d5fa18ad81a98b83c` |
| `model_v5.py` | `a531eeb9e541c995149e023277aa11be1a6833b1e342561f8c0430200d1f7878` |
| `train_v5.py` | `e20ecfa7a88114ad5e25f1aaa5c172825d7b1a845a95eee616fb0745857001f7` |
| `test_v5.py` | `2c27aff681967cf46820836be4d0e006323d8177c2345867cc6e5848b2c2d965` |
| `verify_ruler.py` | `c9d583e67bac362c89ee1eafb0d75a1d91bd5752df18243593f022153c2490fd` |
| `withlock.sh` *(fixed copy in `forecast5/` & `wm5/`)* | `8ee006a0e1b6ee0591412924a1fb571f2e24a06ef3d04ff8558c17c74b688c69` |
| `DATA-MANIFEST.json` / `data/MANIFEST.json` | `a363f1e4494a365fed3a8a8fef90d43a8e4108a31263adbb53b871dddd01cbcd` |
| `data/train_dn.npz` *(M3)* | `4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6` |
| `data/sealed_test.npz` *(M3, `chmod 444`, untouched)* | `74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f` |
| `../wm-harness/data/heldout.npz` *(M3 dev `1000..1015`, untouched)* | `add00c8bbc5d940ef5af006e983f7f34ef073aca9555430a601a47d9738413f0` |
| `../wm-harness/premonition_core_v2/board_swarm.py` *(canonical, untouched)* | `8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d` |

**Status:** STOPPED — **ready for re-check**.



### 6.6 Lead amendment (2026-11-24 23:10 ET, before any scored run)
RECHECK-LEAD.md found a stale-lock race in withlock.sh (only blocker). The lead fixed it: the lock is written to a tmp file and hard-linked (atomic, never empty); stale reaping goes through an mkdir mutex and re-checks the holder; release only if the lock still holds our pid; HUP is trapped. Contention test on a scratch lock: 8 waiters on a stale lock gave max_concurrent=1, and the exit code passed through (rc=7).
withlock.sh sha256 is now 77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa (identical on M1 and M3). No other file changed. All other §6.5 hashes stand.
Driver: run_rung1.sh runs Arm 1 and stops if score_dev.json shows rank3_proved_wrong == true; otherwise it runs Arms 2-4 in order. The sealed exam is NOT in the driver: the lead launches it once, after picking the dev winner.
