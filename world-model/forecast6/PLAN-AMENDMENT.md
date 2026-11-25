# PROBLEM-7 PLAN AMENDMENT — Rank 6 (`forecast6` / `wm6`): Dedicated 2D Conv Spatial World Model

**Date:** 2026-11-24  
**Status:** **STOPPED — ready for independent bug hunt.** Zero scored runs launched. `sealed_test.npz` untouched (`chmod 444`).  
**Motivation:** Rung-1 / Rank-3 Arm 1 (`bundle`) failed and triggered §6.3 `PROVES WRONG` (`E/B = 0.953 / 0.945 / 0.958` vs `shift_or_stay 0.285 / 0.407 / 0.498`; `block_open fb = 1.00`). Our read-only CPU diagnosis ([RUNG1-DIAG.md](<project>/PROBLEM-7/neon-audit/RUNG1-DIAG.md)) proved `K1` fixed seeing (`burial 3,054:1 → 3.49:1`, fresh Ridge on `real_board(t+1)` gets `99.6%` block/open) and `K2` fixed action delivery (`2,000×` stronger bilinear ratio, `E/copy = 0.363` on `sleep`), while the 64-row 1D attention whiteboard lacked a 2D spatial-shift path (global soup localization `1.14`, trunk attention entropy `93.5%` of uniform max, post-trunk per-action Ridge stalled at `0.689`). Lead approved **Rank 6**: a dedicated compact 2D Conv Spatial World Model (`forecast6/` mirrored to M3 `wm6/`).

---

## 1. Scope, Learning Rules & Hard Invariants

- **100% learned parts only:** Zero game-specific rules, zero hand-coded shifts, zero OS/memory cheats.
- **Canonical core untouched:** `premonition_core_v2/board_swarm.py` (`sha256: 8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d`) is completely untouched.
- **Bit-identical ruler (`scorer.py`):** `forecast6/scorer.py` (and M3 `wm6/scorer.py`) is a **bit-identical** copy of pinned `forecast5/scorer.py` (`sha256: 6ff1c135c0eeb2085aa4d49479b915cc5630f355b6d4ad3d5fa18ad81a98b83c`), verified at runtime by `verify_pinned_scorer()`. **All pass bars are unchanged.**
- **Bit-identical lock wrapper (`withlock.sh`):** `forecast6/withlock.sh` (and M3 `wm6/withlock.sh`) is a **bit-identical** copy of Lead's lock-safe `forecast5/withlock.sh` (`sha256: 77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa`).
- **Write scope:** Strictly `PROBLEM-7/neon-audit/`, `PROBLEM-7/forecast6/`, and M3 `~/learner-ops/seven-problems-m3/PROBLEM-7/wm6/`.
- **M3 power & disk guards:**
  - Every MPS execution enforces **`pmset -g batt` shows `AC Power` OR battery `>= 35%`** inside BOTH `train_v6.py:check_mps_power()` and `run_rank6.sh:power_ok`.
  - Free disk guard `>= 12.0 GiB` enforced before training and before saving checkpoints (`26.36+ GiB` free verified).
- **Anti-leakage & sealed guard:** `train_v6.py:guard_sealed_path` blocks any path resolving to `sealed_test.npz` (via lexical path, symlink realpath, OR pinned SHA-256 `74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f`) unless BOTH `--eval-only` AND `--allow-sealed` are passed, AND verifies the exact pinned SHA-256 when `--allow-sealed` is used.

---

## 2. Model Architecture (`SpatialWorldModelV6`, Preset `R6conv`)

- **Scale note:** Compact `2,688,963`-parameter (`enc = 39,872`, `dec = 38,659`, `act = 2,176`, `dyn = 2,608,256`) 2D spatial world model for `16×16` Crafter frames (`3.6×` smaller than `P7toy`'s `9.58M` total params; comparable to `P7toy`'s `2.47M` active cell params). Once proven, `BoardSwarm` reads its compact visual latent grid as a sense.
- **SpatialEncoder (`16×16×3 → 16×16×64`):** Strictly Markov single-frame encoding `z_t = encode(x_t)`. Centers `(x_t - 0.5)`, appends fixed normalized 2D `CoordConv` channels `(y, x) ∈ [-1, 1]`, applies two `3×3` conv layers (`5 → 64 → 64`, `SiLU`). Keeps full `16×16` grid resolution so Crafter's `1.75`-pixel tile shift and `2×2` player sprite are never downsampled away; no output normalization stripping global brightness (`sleep`/night).
- **SpatialDynamicsUNet (`z_t, a_t → z_{t+1}`):** Multi-scale Action-FiLM 2D `ConvResNet` U-Net (`16×16 [64] → 8×8 [96] → 4×4 [128] → 8×8 [96] → 16×16 [64]`, `GroupNorm(8)`, `SiLU`, nearest 2× upsampling + `3×3` skip fusion, fixed 2D `CoordConv` re-injected at input) with one `4×4` global spatial self-attention block (16 tokens, 4 heads) at the bottleneck so obstacle checks at the center tile broadcast globally to all `16×16` terrain pixels in 1 hop while `3×3` convs provide native 2D translation equivariance. Bounded residual update `z_{t+1} = z_t + 3.0 * tanh(raw_delta / 3.0)` with small near-identity init (`std = 0.02`) on `out_conv` and FiLM projections.
- **SpatialDecoder (`16×16×64 → 16×16×3`):** Two `3×3` conv layers (`64 → 64 → 3`, `SiLU`) + `0.5` offset.
- **Anti-wishful-thinking (`wm_grad=False`):** Both `imagine_step` and multi-step `rollout` detach encoder, decoder, action lookup, and dynamics parameters/buffers via `torch.func.functional_call`, leaking zero gradient into any world-model weight while preserving planning gradients into continuous float action embeddings (verified by `test_5`).

---

## 3. Ceiling Definition, Strict `k=1` Training & Open-Loop Rollout

### 3.1 Explicit Ceiling Definition (No Board)
Because `SpatialWorldModelV6` has no `BoardCell`, the real-frame reconstruction ceiling at `k = 1` is pinned **before any run** as:
- **`ceiling_abs_pred_k1 = decode(encode(x_{t+1}))`** — exact reconstruction of the real next frame `x_{t+1}` through the model's same `SpatialEncoder` and `SpatialDecoder` (zero actions, zero dynamics). Passed to `scorer.py` as `ceiling_abs_pred_k1`, yielding the gated `ceiling_abs_E_over_B` (`<= 0.70` required; `> 0.95` → `FAIL`, unchanged from `scorer.py`).
- **`ceiling_res_pred_k1 = x_t + (decode(encode(x_{t+1})) - decode(encode(x_t)))`** — matching residual reconstruction ceiling, passed as `ceiling_res_pred_k1`.
- Non-gating 2D AE health diagnostic: `diag_ae_ceiling_le_0.20 = (ceiling_abs_E_over_B <= 0.20)`.

### 3.2 Strict `k=1` Real-Pair Training & Open-Loop `k=3, 5` Rollouts
- **Training (`compute_train_step_loss`):** Strictly `k = 1` real transition pairs `(x_t, a_t, x_{t+1})` from `../wm5/data/train_dn.npz` (`worlds 3000..3079`, `28,000` day+night transitions, `sha256: 4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6`).
  - Loss: `1.0 * l_rec + 1.0 * l_img_res + 0.25 * l_img_abs + 0.05 * l_lat`, where `z_t` is detached entering `imagine_step` (`l_rec` trains `encoder` exclusively; `dynamics` receives `100%` dynamics gradients from step 0 with zero `l_rec` starvation), `x_rec_t` is detached in `x_img_res = x_t + (x_img_abs - x_rec_t.detach())`, and `l_lat = MSE(z_{t+1}^{pred}, encode(x_{t+1}).detach())` anchors imagined latents onto the encoder manifold.
- **Open-loop evaluation (`rollout(x0, acts_k)`):** For `k = 1, 3, 5`, `rollout` encodes `x_0` **ONCE** (`z_0 = encode(x_0)`, `dec_0 = decode(z_0)`), steps `z_{m+1} = imagine_step(z_m, a_m)` recursively on its own outputs for `m = 0..k-1`, and outputs `P_k = x_0 + (decode(z_k) - dec_0)`. **No real intermediate frame `x_{t+1..t+k-1}` ever enters `rollout`.** Verified mathematically by `test_3` and `test_4` (including poisoning all intermediate frames `t = 1..4` with `NaN`s and verifying bit-identical `k = 5` outputs and bit-identical `evaluate_model` `k = 1, 3, 5` predictions).

---

## 4. Pinned Pass Bars, Exact `PARTIAL` Definition, Falsifier & Two-Seed Rule

### 4.1 Unchanged `forecast5/scorer.py` (`forecast5-v3-rung1`) Per-Seed Bars (Dev `1000..1015`)
Dev baseline reference (`train_dn.npz` → `heldout.npz`, unchanged from `forecast5/PLAN-AMENDMENT.md §6.2`):
- `linear_Mact`: `E/B = 0.4738 / 0.5578 / 0.6103`, `block_open mean_err = 0.4970` (`fb = 0.0014`, `fo = 0.9926`).
- `shift_or_stay` *(strongest baseline)*: **`E/B = 0.2853 / 0.4068 / 0.4977`**, **`block_open mean_err = 0.0879` (`fb = 0.0207`, `fo = 0.1552`)**.

**Per-seed `PASS` (`scorer.py:rung1_verdict == "PASS"`, ALL must hold simultaneously):**
1. **Beat both baselines & legacy accuracy at ALL of `k = 1, 3, 5`:** `E_k/B_k < min(E_act/B_k, E_sos/B_k)` AND `E_1/B_1 <= 0.80`, `E_3/B_3 <= 0.90`, `E_5/B_5 <= 0.95` (dev: **`< 0.2853 / < 0.4068 / < 0.4977`**).
2. **Blocked vs. Open Move Physics Cut (`>= 25%`, neither rate worse):** `mean_err <= 0.75 * base.mean_err` (dev: **`<= 0.0659`**) AND `false_block_rate <= base.false_block_rate` (`<= 0.0207`) AND `false_open_rate <= base.false_open_rate` (`<= 0.1552`).
3. **Action shuffle, ceiling & anti-collapse:** `ceiling_abs_E_over_B <= 0.70`, `k1 shuffle_pooled >= 1.25`, `worlds_k1_shuffle >= 12/16`, `worlds_both >= 12/16` (`>= 1.25×` at `k = 1` AND `>= 1.10×` at `k = 5`), `not proves_wrong`, `std_ratio_active_and_fw_ok == True`, `pcs90_pred >= 0.5 * pcs90_real` (`>= 56/111` on dev).

### 4.2 Exact Two-Seed Rule (Seeds `42` and `43`)
Because MPS timing calibration confirmed each `5,000`-step run completes in **`~6.7 min`** (`< 10 min`), we run **TWO independent seeds (`42` and `43`)** sequentially with identical hyperparameters:
- **Aggregate Rank-6 Dev `PASS`:** Requires **`rung1_verdict == "PASS"` on BOTH seed `42` AND seed `43`**.
- **Pre-pinned single sealed-exam candidate (zero cherry-picking):** If and only if aggregate Dev verdict is `PASS`, select ONE frozen checkpoint for the single locked sealed exam: the seed with lower dev `k1 E_over_B` (tie-break: lower dev `k5 E_over_B`, then seed `42`).

### 4.3 Exact `PARTIAL` Definition & What Follows It
- **Per-seed `PARTIAL`** (exact match to `scorer.py:rung1_verdict == "PARTIAL"`): ALL `k = 1` + `block_open` + `k1` shuffle + anti-collapse + ceiling gates pass (`ok1`, `r1_b1`, `r1_bo`, `okS1`, `r1_shuf_pool1`, `okstd`, `okpc`, `okceil`, `not proves_wrong`), **WHILE** at least one `k = 3` or `k = 5` accuracy gate fails (`not ok3`, `not ok5`, `not r1_b3`, or `not r1_b5`). *(Per Bug A10, if `k = 1, 3, 5` accuracy all pass while `worlds_both < 12`, that is `FAIL`, NOT `PARTIAL`.)*
- **Two-seed aggregate `PARTIAL`:** BOTH seeds `42` and `43` score in `{"PASS", "PARTIAL"}` (every seed passes all `k = 1` + wall-physics + shuffle + anti-collapse + ceiling gates), and at least one seed is `PARTIAL`.
- **What follows `PARTIAL`:**
  1. **STOP — do NOT open or evaluate `sealed_test.npz`.**
  2. Run a read-only CPU drift diagnosis on `forecasts_dev.npz` (checking open-loop `k = 2..5` latent off-manifold drift, decoder blur, and action-shift compounding).
  3. Pin ONE clean strict-`k=1` multi-step stability follow-up in a new plan amendment before any re-run (Rank 5A: FSQ discrete snapping on the `16×16` latent grid, or small start-latent noise regularization during `k = 1` training — still strictly `k = 1` real pairs).

### 4.4 Fixed Falsifier (Rank 6 `FAIL` — NO Auto-Escalation to `64×64`)
- **Aggregate Rank-6 Dev `FAIL`:** Triggered if **either** seed (`42` or `43`) scores `rung1_verdict == "FAIL"` (or fails to finish all `5,000` steps / trips non-finite loss or grad).
- **What a Rank-6 `FAIL` means:**
  1. Counts as **Strike 1/3 for Rank 6** (dedicated 2D spatial visual module) and **STOPS** before touching `sealed_test.npz`.
  2. Triggers a **read-only CPU diagnostic & training-bug hunt** on the saved `model.pt`, `forecasts_dev.npz`, and training logs (checking `ceiling_abs` / `l_rec`, train vs. dev underfitting, receptive-field/bottleneck global gating, `w_lat` balance, LR/step schedule, and blocked-vs-open alpha distributions).
  3. **Explicit non-claim:** A Rank-6 `FAIL` does **NOT** prove `16×16` is the wall — linear `shift_or_stay` already achieves `0.2853 / 0.4068 / 0.4977` and `91.2%` block/open on `16×16`, and fresh Ridge on `real_board(t+1)` achieves `99.6%`. **No automatic escalation to `64×64` is pinned.**

---

## 5. Timing Calibration & Exact Launch Commands (NOT Launched Yet)

### 5.1 M3 MPS Timing Calibration (Unscored, Under `./withlock.sh`)
Ran on M3 (`AC Power`, battery `34%`, `26.36 GiB` free, `timing_mps_r6.log`, `--size R6conv --device mps --steps 60 --batch 64 --timing-only`, 10 warmup + 50 steady-state steps):
- **Steady-state speed:** **`76.4 ms/step`** (`5.6×` faster than `BoardCell`'s `425.3 ms/step`).
- **Projections:** `3,000` steps = `3.82 min` | `4,000` steps = `5.09 min` | **`5,000` steps = `6.37 min`** | `6,000` steps = `7.64 min`.
- **Step-0 gradient & latent check:** `action_emb = 0.00019`, `encoder = 0.10561`, `dynamics = 0.36179`, `decoder = 0.52031`, `lat_burial = 4.88`; by step 59 `rec` dropped `0.12845 → 0.01571`, `lat` dropped `0.07366 → 0.00262`.
- **Pinned fixed step budget:** **`--steps 5000`** (`~6.7 min/seed` incl. MPS eval, well under `10 min/seed` so both seeds fit in `~13.5 min`), with safety cap **`--max-minutes 14.0`** (`>2×` thermal headroom) and fail-loud `RuntimeError("INCOMPLETE RUN...")` if `done < 5000` (refuses to save or score) plus `clip_and_check_grad_norm` abort before `opt.step()`.

### 5.2 Exact Dev Launch Commands (Run on M3 `wm6/` ONLY After Independent Bug Hunt GO)
```bash
# Seed 42 (dev 1000..1015, ~6.7 min on M3 MPS under lock; AC power or >= 35% battery enforced)
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm6 && \
./withlock.sh run_r6_s42.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v6.py \
  --size R6conv --device mps --steps 5000 --batch 64 --lr 3e-4 --wd 1e-4 --w-lat 0.05 \
  --seed 42 --max-minutes 14.0 --save-forecasts \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r6_s42

# Seed 43 (dev 1000..1015, ~6.7 min on M3 MPS under lock; PASS requires BOTH seeds 42 and 43)
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm6 && \
./withlock.sh run_r6_s43.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v6.py \
  --size R6conv --device mps --steps 5000 --batch 64 --lr 3e-4 --wd 1e-4 --w-lat 0.05 \
  --seed 43 --max-minutes 14.0 --save-forecasts \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm-harness/data/heldout.npz \
  --out run_r6_s43

# Or via driver (checks disk >= 12 GiB and power AC/>=35%, runs seed 42 then seed 43; sealed exam NOT included):
~/learner-ops/seven-problems-m3/PROBLEM-7/wm6/run_rank6.sh
```

### 5.3 Exact Locked Sealed-Exam Command *(ONCE ONLY, ONLY After Two-Seed Dev `PASS`)*
Evaluates the single pre-pinned dev-winning frozen checkpoint (`<WIN_SEED>` ∈ `{s42, s43}`, lower dev `k1 E_over_B`, tie-break lower dev `k5 E_over_B`, then `s42`) ONCE on **`../wm5/data/sealed_test.npz`** (`worlds 2000..2015`, `chmod 444`, pinned `sha256: 74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f`, verified at runtime inside `train_v6.py`):
```bash
cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm6 && \
./withlock.sh run_r6_sealed_eval.log \
  ~/learner-ops/m3-torch/.venv/bin/python -B -u train_v6.py \
  --size R6conv --device mps --save-forecasts \
  --eval-only run_r6_<WIN_SEED>/model.pt --allow-sealed \
  --train-data ../wm5/data/train_dn.npz --eval-data ../wm5/data/sealed_test.npz \
  --out run_r6_<WIN_SEED>
```

---

## 6. Verification Proof & Pinned File SHA-256 Hashes (Identical on M1 `forecast6/` & M3 `wm6/`)

**Pre-bug-hunt verification completed (zero scored runs, zero `sealed_test.npz` touch, M3 `AC Power` / `36%` battery charging, `26.37 GiB` free disk, `/tmp/premonition_m3_mps.lock` cleanly released):**
- **`test_v6.py` (10/10 unit tests PASS on BOTH M1 and M3 CPU, `EXIT=0`):** Verifies bit-identical pinned `scorer.py` (`6ff1c135...`), canonical `board_swarm.py` (`8ffc3fb8...`) untouched, `R6conv` (`2,688,963` params) and `tiny` (`171,315` params) shapes & action sensitivity, strictly `k=1` training loss with encoder protected (`z_t.detach()`), open-loop `k=1/3/5` rollouts matching manual loop + bit-identical `k=5` outputs when intermediate real frames `t=1..4` are poisoned with `NaN`s + exact `decode(encode(x_{t+1}))` ceiling definition, `wm_grad=False` anti-wishful-thinking across both `Long` IDs and continuous `Float` single-step & multi-step action plans (zero grad leak to encoder/decoder/action_emb/dynamics), `B=1` finite grads/stats + bit-identical checkpoint round-trip, sealed-split guard (path, symlink, pinned SHA-256, and refusal of `--allow-sealed` on non-sealed files), `pmset` MPS power guard (`AC Power` or `>= 35%`), loud `INCOMPLETE RUN` abort when `done < steps` + non-finite grad abort before `opt.step()` + checkpoint size mismatch refusal, `scorer.py --selftest` (`ALL_PASS`), and lock-safe `withlock.sh` (`77e3ac48...`) exit-code passthrough + `SIGTERM` trap + 6-waiter stale-lock contention (`max_concurrent = 1`).
- **M3 MPS Timing Calibration (`timing_mps_r6.log`, unscored, via `./withlock.sh`, `AC Power`, `60` steps, `batch=64`, `EXIT=0`):** `76.4 ms/step` steady-state → `5,000` steps = **`6.37 min`** (`~6.7 min` incl. MPS eval, well under `10 min/seed`), lock cleanly released.
- **50-Step CPU Smoke Runs (M3 CPU, `nice -n 10`, dev `heldout.npz` only, zero MPS, `EXIT=0`, temp dirs cleaned):**
  - `tiny` (`50` steps, `batch=16`, `2.8s` train + `39.3s` eval) + `--eval-only` reload (`42.1s` eval): **`TINY_EVAL_ONLY_EXACT_MATCH`** (`k1 E/B = 1.3626`, `k5 E/B = 3.9692`, `ceil_abs = 15.1725`, `seed = 42` bit-identical across live and `--eval-only` reload).
  - Full `R6conv` (`50` steps, `batch=16`, `7.1s` train + `135.1s` CPU eval): `rec` dropped `0.12383 → 0.01588`, `lat` dropped `0.07364 → 0.00378`, `img/copy = 1.029`, `lat_burial = 4.62`, dev `E/B = 1.0985 / 1.3190 / 1.5813`, `ceil_abs = 4.3566`, `ceil_res = 0.8085`, baseline refs verified (`0.2853 / 0.4068 / 0.4977`, `bo_base = 0.0879`).
- **Architectural Sanity Checks (M1 CPU, synthetic data only):**
  - Full `R6conv` `B=1` train step + 5-step `wm_grad=False` rollout grad check: `PASS`.
  - Global receptive-field broadcast check (`R6conv`): perturbing only obstacle pixel `(4, 7)` above player reaches far corners `(0, 0)` (`1.87e-3`) and `(11, 15)` (`3.04e-3`) in a single `k=1` step.
  - Synthetic bidirectional 2D shift sanity check (`tiny`, 60 steps): `img/copy` dropped `1.002 → 0.128`.

| File | SHA-256 (Identical on M1 `forecast6/` & M3 `wm6/`) |
|---|---|
| `scorer.py` *(bit-identical copy of pinned `forecast5/scorer.py`)* | `6ff1c135c0eeb2085aa4d49479b915cc5630f355b6d4ad3d5fa18ad81a98b83c` |
| `withlock.sh` *(bit-identical copy of lock-safe `forecast5/withlock.sh`)* | `77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa` |
| `model_v6.py` | `7a76f1b5d88a7d9f52b3b39f9d1d7d686cfc5a7c4f6f2424d2433fa44f7e24ec` |
| `train_v6.py` | `f4b7e74af70c9b55620d74e19bf98a32b474622f50a87786ba878f11fc357989` |
| `test_v6.py` | `65ecd7463fc9df194806d7cd087fcfae880352dfab3dd30f5a335da49c80c0f0` |
| `run_rank6.sh` | `50f4825a7cbbb1cf6f1b3d7db2c3042759b5adc0f7cb75d9326496ac267975bc` |
| `timing_mps_r6.log` *(unscored M3 MPS calibration log)* | `6d3fd88c737adcba1b509ee46758288ad7beed9095dfe74cdde9a00d53c10128` |
| `../wm5/data/train_dn.npz` *(M3, untouched)* | `4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6` |
| `../wm-harness/data/heldout.npz` *(M3 dev `1000..1015`, untouched)* | `add00c8bbc5d940ef5af006e983f7f34ef073aca9555430a601a47d9738413f0` |
| `../wm5/data/sealed_test.npz` *(M3 `2000..2015`, `chmod 444`, untouched)* | `74c421c42c113067e6f065f2343dfefec5372055dbbe54fc34d641f666a85e3f` |
| `../wm-harness/premonition_core_v2/board_swarm.py` *(canonical, untouched)* | `8ffc3fb860547551f10e10a135bcd088176fe0f7b569125c123e0e797e0b6b1d` |

**Honest Pre-Filed Odds (`untested`, two-seed bar):**
- **Two-seed Dev `PASS` (both 42 & 43 pass `k=1, 3, 5` + `block_open <= 0.0659` under strict `k=1` training):** `50%`
- **Aggregate `PARTIAL` (both pass `k=1` + `block_open <= 0.0659`, at least one drifts on `k=3/5` → Rank 5A FSQ follow-up):** `35%`
- **Aggregate `FAIL` (Strike 1/3 + CPU diagnostic/bug hunt):** `15%`

---

## 7. Plain-English Summary (For Ben)

We built the new **picture-shaped imagination module (Rank 6)** in a clean separate folder (`forecast6/` and M3 `wm6/`), leaving the main thinking brain completely untouched. Instead of forcing the 64-row bullet-point notepad to slide 2D pictures around, this compact `2.69M`-weight 2D visual module looks directly at the `16×16` screen grid, uses 2D grid convolutions to slide terrain cleanly when you press a move button, and uses a tiny global `4×4` center-to-edges link so checking an obstacle right next to the player tells the entire screen whether to slide or stay put.

- **Same strict rules, same exact ruler:** It is 100% learned (zero game rules), trains strictly 1 step ahead on real frames, dreams 3 and 5 steps ahead purely from its own guesses (proven in a unit test where hiding/corrupting the real middle frames changes nothing), and uses the **exact byte-for-byte unchanged grading ruler** from Rung 1 (`shift_or_stay` `0.285 / 0.407 / 0.498`, plus cutting blocked-vs-open wall errors by at least 25%).
- **Fast enough to run TWO seeds for extra honesty:** Our quick 7-second speed test on the M3 showed this 2D model runs **5.6× faster** than the notepad brain (`6.4 minutes` for `5,000` training steps). Because each seed finishes well under 10 minutes, we pinned **two seeds (`42` and `43`)** — BOTH must pass on dev before we ever unlock the single final exam on the sealed unseen worlds.
- **Safety checks built in:** Both the trainer and driver refuse to run MPS unless the M3 is plugged into AC power or at `>= 35%` battery, refuse to touch the sealed test worlds without explicit locked-exam flags + exact file checksum, and fail loudly if a run stops early or hits bad math.

**Status: STOPPED — ready for bug hunt. No scored runs launched.**
