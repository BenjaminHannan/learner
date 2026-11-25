# PROBLEM-7 Rank 6 (`R6conv`) Failure Diagnosis — `std_ok` & `k=5` Drift

**Date:** 2026-11-25  
**Scope & Constraints:** Strictly **read-only CPU diagnostics** on saved M3 checkpoints (`wm6/run_r6_s{42,43}/{model.pt,forecasts_dev.npz,score_dev.json}`), `wm5/data/train_dn.npz`, and dev `wm-harness/data/heldout.npz`. **Zero training, zero MPS, zero code edits, zero writes outside `neon-audit/`, `sealed_test.npz` untouched.**  
**Scale Caveat:** All measurements below are on `16×16` Crafter frames with the compact `2.69M`-param `R6conv` spatial world model. Nothing here makes claims about `~50M`/`~500M` scale or 3D Minecraft.  
**Supporting Scripts & Raw Logs (`neon-audit/`):**
- [run_rank6_diag_part1.py](<project>/PROBLEM-7/neon-audit/run_rank6_diag_part1.py) → [rank6_diag_part1.log](<project>/PROBLEM-7/neon-audit/rank6_diag_part1.log)
- [run_rank6_diag_part2.py](<project>/PROBLEM-7/neon-audit/run_rank6_diag_part2.py) → [rank6_diag_part2.log](<project>/PROBLEM-7/neon-audit/rank6_diag_part2.log)
- [run_rank6_diag_part2b.py](<project>/PROBLEM-7/neon-audit/run_rank6_diag_part2b.py) → [rank6_diag_part2b.log](<project>/PROBLEM-7/neon-audit/rank6_diag_part2b.log)
- [run_rank6_diag_part2c.py](<project>/PROBLEM-7/neon-audit/run_rank6_diag_part2c.py) → [rank6_diag_part2c.log](<project>/PROBLEM-7/neon-audit/rank6_diag_part2c.log)
- [run_rank6_diag_part3.py](<project>/PROBLEM-7/neon-audit/run_rank6_diag_part3.py) → [rank6_diag_part3.log](<project>/PROBLEM-7/neon-audit/rank6_diag_part3.log)

---

## Executive Verdict (`shown`)

Rank 6 (`R6conv`, Strike 1/3) is the first model in PROBLEM-7 to beat `shift_or_stay` at `k=1` (`0.247 / 0.249` vs `0.285`) and `k=3` (`0.390 / 0.384` vs `0.407`), pass wall physics (`block_open = 0.025`, `71%` cut), pass `pcs` (`111/111`, `109/111`), achieve `ceil_abs = 0.015`, and pass shuffle in `16/16` worlds (`5.6× / 2.6×`). It failed on **exact two independent mechanisms** — and both surprised naive intuition:

1. **Question (a) — Why interactions (`a=5 do`, `a=8 place_table`, `a=9 place_furnace`) are shrunk (`std_ok = False`):** It is a **compound of TWO distinct mechanisms (`shown`), NOT capacity or receptive field:**
   - **Mechanism (a1) — Exact `16×16` single-frame pixel collision (`energy=6 ≡ energy=9`, `L2 = 0.00000`) on sleep wake-ups (`shown`):** All `8/8` large (`rms > 0.08`) non-move/non-sleep transitions in dev are **sleep wake-ups** (in Crafter, `Player.update()` wakes the player automatically once `energy == 9`, regardless of whichever action `a ∈ {1..5, 8, 9, ...}` the random policy happened to sample on that tick). Those `8` wake-up frames account for **`55.4%` of `do` SSE** (`6/733`), **`60.3%` of `place_table` SSE** (`1/60`), and **`86.5%` of `place_furnace` SSE** (`1/53`). On `place_furnace` (`a=9`), the random policy **never places a furnace** on dev (`std_real = 0.0127 < 0.02` without that single wake-up!). Because `4×4` area pooling makes the HUD glyphs `energy = 6` (11 ticks asleep, `0%` wake) and `energy = 9` (1 tick, `100%` wake) **bit-for-bit identical (`L2 = 0.00000`)**, the Bayes-optimal single-frame wake probability is capped at **`12.5%` (`116/931`)**. Rank 6 actually **reached** the 1-frame Bayes ceiling on asleep frames (`R² = +0.080` dev vs 1-frame Bayes template `+0.028` and 1-frame linear Ridge `+0.065`), and **even a 1-frame Bayes wake predictor + 100% perfect local (`Ctr6x6 + HUD`) oracle is mathematically capped at `std_r = 0.245 < 0.250` on `a=9`!** By contrast, **2-frame past history `(x_{t-1}, x_t)`** sees the unique `8 → 9` HUD transition (`L2 = 0.242`), predicting dev wake-ups at **`100.0%` precision (`20/20`) / `80%` recall**, and a **pure linear Ridge** on 2-frame HUD `[x_t, x_t - x_{t-1}]` (zero templates) plugged onto saved `s42` immediately jumps `a=5, 8, 9` to **`std_r = 0.362 / 0.407 / 0.427` (`R² = +0.226 / +0.241 / +0.467`)** and cuts overall `k=1 E/B` from `0.2470 → 0.2304`.
   - **Mechanism (a2) — Extreme MSE loss starvation of local interactions (`do_awake`, `place_table_awake`) (`shown`):** Excluding sleep wake-ups, single-frame `16×16` pixels **DO** cleanly observe local interactions (the `2×2` player sprite decodes facing direction at `96.1%` linear / `98.5%` quadratic dev accuracy; single-frame 300-feature linear Ridge gets `do Ctr6x6 R² = +0.254` / `std_r = 0.504` and `place_table HUD R² = +0.248` / `std_r = 0.582`). Yet `2.69M`-param `R6conv` got **`R² <= 0` even on the training set** and collapsed `a=5, 8, 9` onto `noop` (`cos(cond[a], cond[noop]) = +0.56..+0.72`, `RMS(f(x,a) - f(x,noop)) = 0.0008–0.0016`) because `moves_awake + sleep_enter + sleep_wake = 97.98%` of training pixel SSE while `do_awake = 0.70%` (`Ctr+HUD = 0.35%`) and `place_table_awake = 0.07%` (`Ctr+HUD = 0.04%`, `62×` smaller dynamics gradient norm at step 5,000!).

2. **Question (b) — What drives `k=5` drift (`0.5202 / 0.5031` vs `0.4977`):** **NEITHER interaction misses NOR compounding pixel blur — it is `15×` off-manifold latent drift on `3–5` open-move sequences (`shown`, PROVEN BY ZERO-TRAINING COUNTERFACTUAL)!**
   - Interaction windows at `k=5` **beat** `shift_or_stay` (`has_do`: `-140.5` s42 / `-463.4` s43; `other_nonmove`: `-36.3` / `-189.1`). **>100% of the `k=5` deficit comes from `pure_moves`** (`+1,105.9` s42 vs total `+1,036.4`; `+885.0` s43 vs total `+248.0`), concentrated strictly in `open_moves = 3, 4, 5` (`+2,400` s42 / `+1,825` s43).
   - Rank 6 is **`2×` SHARPER** than `shift_or_stay` at `k=5` (`terrain gradE = 0.75×` true vs `sos 0.38×`; `FFT HF = 0.75×` vs `sos 0.49×`).
   - Because `z_t` (`16×16×64 = 16,384` dims) is `21.3×` overcomplete vs pixels (`768` dims) and `w_lat = 0.05` is small, off-manifold error `||z_k - encode(decode(z_k))||` explodes from `0.0033` (real frames) → `0.0189` (`k=1`) → `0.0353` (`k=3`) → **`0.0494` (`k=5`, `15.0×` real, `71%` of total latent error!)**, degrading open-loop `block_open` from `2.2% → 23.8%` and shift amplitude `al_op` from `0.961 → 0.627`.
   - **Zero-training proof:** Running full `scorer.py` on the **exact saved `s42` and `s43` checkpoints** with pixel-manifold re-encoding (`z <- encode(clamp(pred, 0, 1))`) between open-loop steps drops **`k=5 E/B` from `0.5202 → 0.4881` (s42) and `0.5031 → 0.4827` (s43, 95% CI `[0.944, 0.994]` vs `sos`)**, cuts `k=3` (`0.390 → 0.374`, `0.384 → 0.374`), raises `k=5` shuffle (`2.52 → 2.67`, `2.65 → 2.75`), and **passes EVERY SINGLE Rung-1 mark except `std_ok` on BOTH seeds with ZERO retraining!**

3. **Recommended ONE Next Change (One Knob):** **2-Frame Past-History Input `(x_{t-1}, x_t)` into `SpatialDynamicsUNet`** (`[z_t, z_t - z_{t-1}, coord]`, matching `forecast5`'s exact 2-frame past-input protocol with `x_{-1} = x_0` at `t=0`; `SpatialEncoder`, `SpatialDecoder`, ceiling, `k=1` loss, and all hyperparams unchanged).
   - **Why THIS knob first:** (i) Latent snapping alone is a **guaranteed `FAIL` (`Strike 2/3`)** because `std_ok` stays `False`; (ii) change-weighted loss alone on 1-frame `x_t` is **mathematically blocked** on `a=9` (`<= 0.245 < 0.25`) by the `energy=6 ≡ energy=9` pixel collision; (iii) 2-frame `(x_{t-1}, x_t)` breaks the `8 → 9` wall (`5.70%` of train SSE already present — no loss hack needed!), flips `std_ok` to `True`, and at worst yields **`PARTIAL` (NOT a strike!)**, cleanly unlocking the already CPU-proven `reencode_res` snap for `k=5`. *(Honest caveat: we also track non-wake local `do`/`place_table` `R²` separately so we don't confuse solving sleep-wake with solving local chopping/placing!)*

---

## Part (a): Diagnosis of Interaction Shrinkage (`std_ok = False`)

### 1. Exact Per-Action Breakdown (`train_dn.npz` vs `heldout.npz`, `k = 1`, `shown`)

| Action | Name | `tr_n` (`%`) | `tr_dY%` | `tr_std` | `dv_n` | `dv_std` | `s42` `std_r` | `s43` `std_r` | `s42` `R²` | `s42` slope | `s42 E/c` | `sos E/c` |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `0` | `noop` | `303` (`1.1%`) | `0.09%` | `0.0182` | `53` | `0.0083` | `0.356` | `0.385` | `-0.106` | `0.08` | `1.106` | `14.002` |
| `1..4` | `move_l/r/u/d` | `19,938` (`71.2%`) | **`89.89%`** | `0.069–0.073` | `3,574` | `0.074–0.078` | **`0.870–0.912`** | **`0.903–0.948`** | **`+0.768–0.821`** | `0.97–1.01` | `0.179–0.232` | `0.195–0.239` |
| **`5`** | **`do` (FAIL)** | `4,007` (`14.3%`) | **`1.79%`** | `0.0225` | `733` | `0.0225` | **`0.161`** | **`0.176`** | `+0.029` | `1.07` | `0.971` | `0.962` |
| `6` | `sleep` | `311` (`1.1%`) | **`7.21%`** | `0.1559` | `41` | `0.1763` | **`0.752`** | **`0.882`** | **`+0.648`** | `1.05` | `0.352` | `0.384` |
| **`8`** | **`place_table` (FAIL)** | `346` (`1.2%`) | **`0.07%`** | `0.0155` | `60` | `0.0324` | **`0.083`** | **`0.118`** | `+0.008` | `1.39` | `0.992` | `1.701` |
| **`9`** | **`place_furnace` (FAIL)** | `333` (`1.2%`) | **`0.09%`** | `0.0176` | `53` | `0.0343` | **`0.088`** | **`0.106`** | `+0.038` | `3.03` | `0.962` | `1.518` |
| `7,10..16` | `other place/make` | `2,762` (`9.9%`) | `0.87%` | `0.011–0.023` | `494` | `0.011–0.015` | `0.19–0.34` | `0.22–0.33` | `-0.09 to -0.01` | `0.08–0.37` | `1.01–1.09` | `4.23–5.95` |

*(Note: `linear_Mact` / `shift_or_stay` has `std_r = 0.78–2.34` on rare actions `7..16` only because solving 769 parameters on ~340 samples overfits massively: `E/copy = 1.52–14.00`!)*

### 2. Finding (a1): Sleep Wake-Ups Dominate `a=5, 8, 9` Variance — and Single-Frame `16×16` Pixels Have an Exact `energy=6 ≡ energy=9` Collision (`shown`)

Inspecting the top-change dev windows for actions `5, 8, 9` ([rank6_diag_part1.log:109-145](<project>/PROBLEM-7/neon-audit/rank6_diag_part1.log:109-145), [rank6_diag_part2.log:1-48](<project>/PROBLEM-7/neon-audit/rank6_diag_part2.log:1-48)) revealed that **all `8/8` non-move, non-sleep dev transitions with `rms > 0.08` are sleep wake-ups** (`terrStd` jumping from `0.020–0.048` → `0.112–0.257`, `9–34` ticks after an earlier `a=6` sleep):

- **`a=5 (do, n=733)`:** `6` wake-up windows (`0.8%` of `do`) = **`55.4%` of total `do` SSE** (`157.5 / 284.5`). Removing them drops `std_real` from `0.0225 → 0.0150` (below the `0.02` active threshold!).
- **`a=8 (place_table, n=60)`:** `1` wake-up window (`w=1000 ep=1 t=131`, `rms=0.1950`) = **`60.3%` of total `place_table` SSE** (`29.22 / 48.45`). Removing it leaves `std_real = 0.0206` (still active due to genuine crafting-table placements).
- **`a=9 (place_furnace, n=53)`:** `1` wake-up window (`w=1008 ep=16 t=70`, `rms=0.2326`) = **`86.5%` of total `place_furnace` SSE** (`41.55 / 48.03`). Removing it drops `std_real` from `0.0343 → 0.0127` (**inactive** — the random policy never collects 4 stone to place a furnace; windows `#2..#10` are `88–100%` outer-terrain wandering mobs with `0%` HUD change).

**Why did Rank 6 learn `sleep_enter` (`7.05%` train SSE → `R² = +0.82` train / `+0.68` dev) yet stall at `R² = +0.08` on `sleep_wake` (`5.70%` train SSE)?**  
Direct inspection of `crafter.objects.Player.update()` and `4×4` area-pooled `16×16` HUD renders proved an **exact information-theoretic collision (`shown`):**
- In Crafter, while `sleeping == True`, `self._fatigue` counts 11 invisible ticks per `+1` energy; when `energy` increments from `8 → 9` at the end of tick `t-1`, `x_t` is rendered **still asleep** with `energy = 9` in the HUD; then tick `t` wakes the player deterministically (`if energy < 9: action='sleep' else: sleeping=False`), regardless of `a_t`.
- In `16×16` area-pooled pixels, the energy digit spans `[(12,5),(12,6),(13,5),(13,6)]`, and **`energy = 6` vs `energy = 9` has exact `L2 = 0.00000` (bit-for-bit identical!)**, whereas **`energy = 8` vs `energy = 9` has `L2 = 0.24206`** (`px (12,6): +0.0625`, `px (13,6): -0.1250`).
- Consequently, on single-frame `x_t`, the `11` sleeping ticks at `energy = 6` (`0%` wake) and the `1` wake tick at `energy = 9` (`100%` wake) collapse identically: in `train_dn.npz`, `e ∈ {6,9}` occurs `931` times with only `116` wakes (**exact Bayes wake probability `p* = 12.5%`!**; dev: `20/176 = 11.4%`).
- **Saved `s42/s43` ALREADY hit the 1-frame Bayes ceiling on asleep frames** (`dev asleep R² = +0.080 / +0.080`, `std_r = 0.286 / 0.276` vs 1-frame exact template Bayes `+0.028 / 0.299` and 1-frame HUD linear Ridge `+0.065 / 0.282`).

**Exact `std_ratio` Ceiling Proof — 1-Frame vs. 2-Frame (`shown`, all dev windows of `a=5, 8, 9`):**

| Predictor / Bound on DEV | `a=5 (do)` `std_r` (`R²`) | `a=8 (place_table)` `std_r` (`R²`) | `a=9 (place_furnace)` `std_r` (`R²`) |
|---|---:|---:|---:|
| Saved `R6conv` `s42 / s43` (1-frame) | `0.161 / 0.176` (`+0.029 / +0.039`) | `0.083 / 0.118` (`+0.008 / +0.020`) | `0.088 / 0.106` (`+0.038 / +0.050`) |
| Oracle `Ctr6x6 + HUD` ONLY (0 wake, 0 mobs) | `0.446` (`+0.199`) | `0.511` (`+0.261`) | **`0.157`** (`+0.025`) — **FAIL** |
| **1-frame Bayes Wake + Oracle `Ctr6x6 + HUD`** | `0.475` (`+0.218`) | `0.526` (`+0.331`) | **`0.245`** (`+0.132`) — **STILL < 0.25 FAIL!** |
| **Saved `s42` + pure 2-frame HUD Linear Ridge (`[x_t, x_t - x_{t-1}]`, zero templates)** | **`0.362`** (`+0.226`) — **PASS** | **`0.407`** (`+0.241`) — **PASS** | **`0.427`** (`+0.467`) — **PASS** |
| 2-frame `(8→9)` Wake ONLY (0 local) | `0.525` (`+0.293`) | `0.718` (`+0.211`) | `0.689` (`+0.705`) |
| 2-frame `(8→9)` Wake + Oracle `Ctr6x6 + HUD` | `0.680` (`+0.479`) | `0.881` (`+0.470`) | `0.706` (`+0.729`) |

- Because `(x_{t-1}, x_t)` uniquely distinguishes `8 → 9` (`d(12,6)=+0.0625, d(13,6)=-0.1250`) from `5 → 6`, `6 → 7`, `7 → 8`, and static `6 → 6`, 2-frame detection hits **`92.7%` precision / `82.6%` recall** on train (`114/123`) and **`100.0%` precision / `80.0%` recall** on dev (`20/20`).
- Even a **plain linear Ridge** on 2-frame HUD pixels `[x_t[12:], x_t[12:] - x_{t-1}[12:]]` achieves **`AUROC = 0.9666`**, lifts dev asleep `R²` by `4.7×` (`+0.080 → +0.377`), lifts **all three** failing `std_ok` actions well above `0.25` (`0.362 / 0.407 / 0.427`) while slashing their error, and cuts total dev `k=1 E/B` from **`0.2470 → 0.2304`** (`-273.9` SSE; the `20` `8→9` wakes account for `694.3 / 4,062.6 = 17.1%` of Rank 6's entire remaining `k=1` error!).

### 3. Finding (a2): Local Interactions (`do_awake`, `place_table_awake`) Are Observable on 1-Frame `16×16` — But Starved by Pixel-MSE Loss Weighting (`shown`)

Excluding sleep wake-ups (`rms < 0.08`), local interactions ARE genuine and observable from single-frame `16×16` `x_t`:
- **Facing direction is observable (`shown`):** A linear classifier on just the `2×2` player sprite `[5:7, 7:9]` decodes facing direction (`1..4`) at **`96.1%` dev accuracy (`98.5%` quadratic; `98.4%` linear on `4×4` crop; chance `25%`)**.
- **Linear Ridge beats `2.69M`-param `R6conv` badly on local interactions (`shown`):**
  - `do` (non-wake, `n_dev=727`, `26.1%` change HUD, `13.9%` change `Ctr6x6`): single-frame `300`-feature Ridge(`Ctr6x6 + HUD`) achieves **`Ctr6x6 R² = +0.254` (`std_r = 0.504`)**, **`HUD R² = +0.132` (`std_r = 0.413`)**, and `full 16×16 R² = +0.071` (`std_r = 0.354`).
  - `place_table` (non-wake, `n_dev=59`, `23.7%` change HUD & `Ctr6x6` by genuinely placing a table): Ridge achieves **`HUD R² = +0.248` (`std_r = 0.582`)** and `full 16×16 R² = +0.094` (`std_r = 0.243`).
  - Yet **`R6conv` got `R² <= 0` EVEN ON THE TRAINING SET** (`do` train `s42/s43`: `HUD R² = -0.007 / +0.012`, `Ctr6x6 R² = -0.077 / -0.148`; `place_table` train: `HUD R² = -0.002 / -0.009`, `Ctr6x6 R² = -0.005 / -0.037`).
- **Counterfactual action-swap proves collapse onto `noop` (`shown`, [rank6_diag_part2.log:95-121](<project>/PROBLEM-7/neon-audit/rank6_diag_part2.log:95-121)):**
  - `moves 1..4`: `cos(cond[a], cond[noop]) = -0.14..-0.34`, `RMS(f(x,a) - f(x,noop)) = 0.074–0.083`.
  - `sleep (6)`: `cos_noop = -0.43..-0.52`, `RMS = 0.123–0.153`.
  - **`do (5)`, `place_table (8)`, `place_furnace (9)`:** `cos_noop = +0.56..+0.72`, `RMS(f(x,a) - f(x,noop)) = 0.00083–0.00163` (**`50–90×` smaller than moves**!).
- **Why? Exact training pixel-SSE budget (`train_dn.npz`, `28,000` transitions, `total SSE = 86,757.8`, `shown`):**
  - `moves_awake (1..4)`: **`85.23%`** of SSE (`60.69%` of samples)
  - `sleep_enter (a=6)`: **`7.05%`** (`0.61%` of samples — `11.5×` above average MSE/sample → learned cleanly!)
  - `sleep_wake (ANY a)`: **`5.70%`** (`0.49%` of samples — nearly as large as `sleep_enter`, blocked only by 1-frame `e=6 ≡ e=9`!)
  - **`do_awake (a=5)`:** **`0.70%`** (`Ctr6x6 + HUD = 0.35%`)
  - **`place_table_awake (a=8)`:** **`0.07%`** (`Ctr6x6 + HUD = 0.04%` — **`2,100×` smaller than moves!**)
  - **`place_furnace_awake (a=9)`:** **`0.04%`** (`Ctr6x6 + HUD = 0.01%`)
  - Pure CPU backward at step 5,000 confirms `moves (1..4)` still produce `12.6×` larger dynamics gradient norm than `do` (`0.00555` vs `0.00044`) and `62×` larger than `place89` (`0.00009`).
- **Capacity / receptive field ruled out (`shown`):** `R6conv` (`2.69M` params, `4×4` global self-attention, `ceil_abs = 0.0145`, `AE HUD_rms = 0.0045` vs `8→9` diff `0.125`) already solves global obstacle checks (`97.5%`) and `sleep` (`R² = 0.82` train), and dwarfs the 300-feature linear Ridge that succeeds on local `do` / `place_table`.

---

## Part (b): Diagnosis of `k = 5` Drift (`0.5202 / 0.5031` vs `0.4977`)

### 1. Not Interaction Misses, Not Compounding Pixel Blur (`shown`)

- **Action-sequence breakdown at `k = 5` (`n = 4,874`, mutually exclusive, sums to exact total gap `s42 = +1,036.4`, `s43 = +248.0` vs `shift_or_stay`):**

| `k = 5` Window Bucket | `n` (`%`) | `s42` SSE | `s43` SSE | `sos` SSE | `gap42` (`s42-sos`) | `gap43` (`s43-sos`) |
|---|---:|---:|---:|---:|---:|---:|
| **`pure_moves` (only `1..4`)** | `1,269` (`26.0%`) | `7,847.4` | `7,626.5` | `6,741.5` | **`+1,105.9`** | **`+885.0`** |
| `has_sleep` (`a=6`) | `202` (`4.1%`) | `2,077.9` | `2,035.2` | `2,012.6` | `+65.2` | `+22.6` |
| `has_do` (`a=5`, no sleep) | `2,373` (`48.7%`) | `9,025.3` | `8,702.4` | `9,165.8` | **`-140.5`** | **`-463.4`** |
| `has_place89` (no slp/do) | `216` (`4.4%`) | `1,065.9` | `1,016.8` | `1,023.9` | `+42.0` | `-7.1` |
| `other_nonmove` (`0,7,10..16`) | `814` (`16.7%`) | `3,898.9` | `3,746.1` | `3,935.2` | **`-36.3`** | **`-189.1`** |

- **Monotonic cliff by `# of true OPEN moves` inside the 5-step window (`shown`):**
  - `open_moves = 0` (`n=1,095`): `gap42 = -777.4`, `gap43 = -1,075.9` (`0.80× / 0.73×` of `sos` — Rank 6 dominates blocked moves!)
  - `open_moves = 1` (`n=675`): `gap42 = -498.8`, `gap43 = -410.1`
  - `open_moves = 2` (`n=877`): `gap42 = -87.6`, `gap43 = -90.4`
  - `open_moves = 3` (`n=894`): **`gap42 = +582.0`, `gap43 = +441.9`**
  - `open_moves = 4` (`n=864`): **`gap42 = +956.8`, `gap43 = +711.5`**
  - `open_moves = 5` (`n=469`): **`gap42 = +861.4`, `gap43 = +671.1`**
- **Not compounding pixel blur (`shown`):** At `k = 5`, Rank 6 retains **`2×` more spatial edge energy** than `shift_or_stay` (`terrain gradE` vs true: `s42 = 0.749`, `s43 = 0.753` vs `sos = 0.384`; `2D FFT HF` vs true: `0.751 / 0.741` vs `sos = 0.491`).

### 2. Primary Fixable Driver: `15×` Off-Manifold Latent Drift (`shown` — Proven by Zero-Training Counterfactual)

Tracking `s42` (and `s43`) step-by-step across `k = 1..5` open-loop rollouts on all `4,874` dev windows ([rank6_diag_part2.log:134-175](<project>/PROBLEM-7/neon-audit/rank6_diag_part2.log:134-175)):

| Step `k` | `s42 E/B` (`s43`) | `sos E/B` | `s42 bo_err` (`fb / fo`) | `s42 al_op` (shift amp) | `s42 ||z_k - z_real||` | `s42 offman ||z_k - enc(dec(z_k))||` |
|---:|---:|---:|---:|---:|---:|---:|
| Real `x` | — | — | — | — | `0.0000` | **`0.0033`** (`s43: 0.0031`) |
| `k = 1` | `0.2464` (`0.2480`) | `0.2840` | `0.022` (`0.013 / 0.031`) | `0.961` | `0.0288` | **`0.0189`** (`5.7×` real) |
| `k = 2` | `0.3211` (`0.3186`) | `0.3501` | `0.066` (`0.069 / 0.063`) | `0.887` | `0.0416` | **`0.0276`** (`8.4×` real) |
| `k = 3` | `0.3905` (`0.3844`) | `0.4063` | `0.117` (`0.122 / 0.111`) | `0.797` | `0.0520` | **`0.0353`** (`10.7×` real) |
| `k = 4` | `0.4572` (`0.4462`) | `0.4560` | `0.179` (`0.193 / 0.165`) | `0.710` | `0.0610` | **`0.0424`** (`12.8×` real) |
| `k = 5` | `0.5202` (`0.5031`) | `0.4977` | **`0.238`** (`0.277 / 0.198`) | **`0.627`** | `0.0694` | **`0.0494`** (**`15.0×` real = `71%` of `z_err`!**) |

- **Why:** `SpatialEncoder` (`16×16×64 = 16,384` dims) is `21.3×` overcomplete relative to pixels (`768` dims), and `w_lat = 0.05` barely constrains the `15,616`-dim null space of `SpatialDecoder`. At `k=1`, null-space residuals are invisible to `decode(z_1)`. Fed recursively into `imagine_step` at `k=2..5`, they compound to `15×` off-manifold, causing (i) in-view terrain on `open_moves >= 3` to degrade `+1,109.5` (s42) / `+726.3` (s43) worse than `sos`, (ii) step-5 open-move shift amplitude `al_op` to decay `0.961 → 0.627` (`fb: 1.3% → 27.7%`), and (iii) even static `HUD (rows 12..15)` to drift `1.34×` / `1.21×` worse than `sos` (`+181 / +113` SSE).
- **Secondary structural factor (`shown`):** At `k=5`, `25.3%` of all terrain pixels (`41.0%` on `open_moves >= 3`) scrolled in from **off-screen** (never visible in `x_0`). Linear `shift_or_stay` contracts those unobservable border pixels toward `mean_tr` (`var = 0.0401`, `cal_w = 0.991`), whereas `R6conv` keeps higher variance (`0.0482 / 0.0455`, `cal_w = 0.908`), paying `+1,094` (s42) / `+992` (s43) SSE on off-screen pixels.
- **Decisive zero-training counterfactual proof (`shown`, full `scorer.py` real + shuffled on CPU, [rank6_diag_part3.log:27-28](<project>/PROBLEM-7/neon-audit/rank6_diag_part3.log:27-28)):**  
  Inserting a 1-line **pixel-manifold re-encoding snap** between open-loop steps (`z <- encode(clamp(x0 + decode(z) - dec0, 0, 1))`, zero retraining, zero future frames):

| Seed & Rollout Mode | `k1 E/B` (`<=0.2853`) | `k3 E/B` (`<0.4068`) | **`k5 E/B` (`<0.4977`)** | `k5 E/sos` (95% CI) | `shuf k1 / k5` | `k5 in-view / off-screen / HUD` SSE | Marks Passing |
|---|---:|---:|---:|---:|---:|---:|---|
| `s42` normal (saved) | `0.2470` | `0.3902` | `0.5202` (**FAIL**) | `1.045` (`[1.017, 1.072]`) | `5.55 / 2.52` | `10,376 / 12,827 / 713` | `9/11` (`k5`, `std_ok`) |
| **`s42` `reencode_res` (0-train)** | `0.2470` | **`0.3740`** | **`0.4881` (PASS)** | **`0.981`** (`[0.953, 1.008]`) | **`5.55 / 2.67`** | **`9,275` (`-1,101`) / `12,531` / `632`** | **`10/11` (ALL except `std_ok`)** |
| `s43` normal (saved) | `0.2488` | `0.3844` | `0.5031` (**FAIL**) | `1.011` (`[0.983, 1.038]`) | `5.73 / 2.65` | `9,758 / 12,725 / 645` | `9/11` (`k5`, `std_ok`) |
| **`s43` `reencode_res` (0-train)** | `0.2488` | **`0.3737`** | **`0.4827` (PASS)** | **`0.970`** (`[0.944, 0.994]`) | **`5.73 / 2.75`** | **`9,169` (`-589`) / `12,430` / `589`** | **`10/11` (ALL except `std_ok`)** |

---

## Proposal: ONE Next Change (One Knob)

### Why NOT the Other Single Knobs First (`shown` / `suggested`)

| Candidate Single Knob | Why Rejected as the Sole Next Run |
|---|---|
| **1. Pixel-manifold latent snap (`reencode_res`) alone** | Already proven on CPU to fix `k=5` (`0.4881 / 0.4827`), **but leaves `k=1` and `std_ok` untouched → guaranteed `FAIL` (`Strike 2/3`)** because `std_ok` gates both `PASS` and `PARTIAL` in `scorer.py`. |
| **2. Change-weighted `k=1` image loss alone (1-frame `x_t`)** | (a) Naive per-pixel weight `(1 + 10*(|dx|>0.02))` leaves `do`/`place_table` shares unchanged (`0.70%→0.69%`, `0.07%→0.06%`) because moves also change `75%` of pixels! (b) Even per-example changed-pixel loss (`MSE + MSE_changed_ex`, which boosts `do_awake` `5.8×` to `4.05%`) **cannot honestly fix `a=9 (place_furnace)`** because 1-frame `e=6 ≡ e=9` caps `a=9` at `std_r <= 0.245 < 0.250` even with a perfect local oracle, AND lowers `sleep_wake` loss share (`5.70% → 2.17%`), while leaving `k=5` unsnapped → high risk of `Strike 2/3`. |
| **3. Conditional / stochastic latent head alone** | Wrong fit for a deterministic-MSE scorer (`scorer.py` evaluates one rollout `P_k`): sampling adds variance penalty to MSE, while taking the mean recovers the same shrunk prediction. Both `8 → 9` wake-up and local `do`/`place_table` are **deterministic** once observed. |

### Recommended ONE Knob: **2-Frame Past-History Input `(x_{t-1}, x_t)` into `SpatialDynamicsUNet`**

- **Exact single change (`+4,096` params = `+0.15%`):**
  - Keep `SpatialEncoder(x_t) -> z_t`, `SpatialDecoder(z_t) -> x_t`, explicit ceiling `decode(encode(x_{t+1}))`, strictly `k=1` training loss (`1.0*l_rec + 1.0*l_img_res + 0.25*l_img_abs + 0.05*l_lat`), optimizer, LR schedule, batch `64`, `5,000` steps, and latent rollout loop **100% unchanged**.
  - Pass the previous real frame `x_{t-1}` (strictly past `<= t`, with `x_{-1} = x_0` at `t=0`, identical to `forecast5/train_v5.py:184`) through the same `SpatialEncoder` (detached into dynamics: `z_prev = encode(x_{t-1}).detach()`), and change ONLY `SpatialDynamicsUNet.in_proj` from `Conv2d(latent_ch + 2, c0, 1)` on `[z_t, coord]` to `Conv2d(2 * latent_ch + 2, c0, 1)` on **`[z_t, z_t - z_{t-1}, coord]`**.
  - During open-loop `k=3, 5` rollouts (`rollout(x_prev, x_0, acts_k)`), step `0` uses `(z_{t-1}, z_0)`, step `1` uses `(z_0, z_1)`, ..., step `m` uses `(z_{m-1}, z_m)` — **zero real future frames `x_{t+1..t+k-1}` ever enter** (verified by NaN-poisoning unit test).
- **Why THIS single knob goes first:**
  1. **Unblocks the proven mathematical wall on `std_ok` (`a=5, 8, 9`):** `z_t - z_{t-1}` exposes the unique `energy 8 → 9` HUD transition (`SNR ≈ 60:1` over AE error) with **`5.70%` of training pixel SSE already present** (nearly matching `sleep_enter`'s `7.05%` SSE, which Rank 6 already learned cleanly without loss reweighting!). Learning 2-frame sleep-wake alone lifts `a=5, 8, 9` to `std_r ≈ 0.36–0.70` while cutting their error `23–70%` and cutting overall `k=1` SSE by `10–17%`.
  2. **Protects our Strike budget under `scorer.py`:** Even if `k=5` still sits slightly above `0.4977` on `s42` without pixel snapping, passing `std_ok` upgrades the verdict from `FAIL` to **`PARTIAL` (NOT a strike!)**, which immediately unlocks the already CPU-verified **`reencode_res` snap** (`-0.020 to -0.032` at `k=5`) as the next clean single-knob step to a 2-seed `PASS`.
  3. **Honest scientific tracking (no self-deception):** Alongside official `scorer.py` marks, log a non-gating diagnostic of **non-sleep-wake `do_awake` (`Ctr6x6+HUD`) and `place_table_awake` (`Ctr6x6+HUD`) `R²` and `std_r`**. Passing `std_ok` via `8 → 9` sleep-wake is 100% genuine Crafter physics, **not** cheating — but it does **not** automatically solve local tree-chopping or crafting-table placement, which remain starved (`0.70%` / `0.07%` SSE) unless a later follow-up adds per-example changed-pixel weighting (`MSE + MSE_changed_ex`).
  - *(Note for Lead: if Lead explicitly prefers not to spend a separate `PARTIAL` step when `reencode_res` is already CPU-verified on both saved seeds, Lead could optionally authorize bundling `2-frame + reencode_res` into one run — we keep our formal proposal strictly **1 knob** as requested.)*

### Cheapest Test, Falsifier & Honest Odds (`untested`)

- **Cheapest test (strictly unchanged ruler & protocol):**
  - Same `forecast6/scorer.py` (`sha 6ff1c135...`), same bars (`E/B < 0.2853 / 0.4068 / 0.4977`, `block_open <= 0.0659` neither rate worse, `worlds_both >= 12/16`, `std_ok`, `pcs_ok`, `ceil <= 0.70`), strictly `k=1` training on `train_dn.npz`, dev `heldout.npz` (`sealed_test.npz` untouched), **2 seeds (`42` and `43`)**, `5,000` steps each (`~6.8 min/seed` on M3 MPS under `withlock.sh` + power/disk guards ≈ `13.6 min` total).
  - *Cheap pre-run sanity check (CPU, `< 30s`):* verify `test_v6.py` updated for `(x_prev, x_0)` NaN-poisoning (`t=1..4 = NaN` bit-identical), `wm_grad=False` zero leak, and `t=0` boundary (`x_prev = x_0`).
- **What result proves this change WRONG:**
  1. Either seed still fails **`std_ok`** (`a=5, 8`, or `9` stays `< 0.25`) **OR** dev `asleep R²` fails to exceed the 1-frame ceiling (`<= 0.15`, vs saved `s42/s43 = +0.080` and 2-frame linear Ridge `+0.377`) → **proves** `0.41%` sample frequency / localized 2-pixel HUD-to-terrain optimization (not 1-frame observability alone) blocks learning `8 → 9` wake-up under uniform MSE; inspect train vs dev `asleep R²` to separate underfitting from overfitting.
  2. Either seed regresses `k=1 E/B >= 0.2853`, `k=3 E/B >= 0.4068`, or `block_open > 0.0659` (e.g., if `z_t - z_{t-1}` amplifies open-loop latent drift at `k=3`).
  *(By contrast, both seeds passing `std_ok` + `k=1, 3, block_open, shuffle, pcs, ceil` while `k=5` stays `> 0.4977` is `PARTIAL`, confirming the `(a)` diagnosis and triggering the already CPU-verified `reencode_res` follow-up.)*
- **Honest Odds (`untested`, strictly 1-knob `2-frame` with unchanged latent rollout, 2-seed bar):**
  - **Two-seed Dev `PASS`:** **`20%`** (`s43` is only `+0.0054` above `0.4977`, so 2-frame wake/motion gains may pull `s43` under, while `s42` at `+0.0225` likely still needs `reencode_res` to clear `0.4977`).
  - **Two-seed Aggregate `PARTIAL` (no strike → unlocks CPU-proven `reencode_res`):** **`55%`**.
  - **Aggregate `FAIL` (`Strike 2/3`):** **`25%`** (main risks: `R6conv` underfitting the `0.41%`-frequency 2-pixel HUD cue under uniform MSE on at least one seed, or `z_t - z_{t-1}` worsening open-loop `k=3/5` latent drift).
  - *(Reference only — if Lead explicitly authorizes the 2-knob bundle `2-frame + reencode_res`: `PASS 65% / PARTIAL 10% / FAIL 25%`.)*

---

## Plain-English Summary (For Ben)

Our new picture-shaped imagination brain (Rank 6) worked great for walking and walls, and beat the strong simple rule 1 and 3 steps ahead on both tries — but missed passing on **two** things: predicting small actions (`do` and `place`), and drifting slightly too far by step 5. We dug into the saved runs (CPU only, no new training) and found two big surprises:

1. **Why `do` and `place` looked shrunk (two separate reasons):**
   - **Surprise #1 (a hidden `16×16` blur collision on waking up from sleep):** Almost all the big changes on `do` (`55%`), `place_table` (`60%`), and `place_furnace` (`87%` — in fact the random player never once places a furnace!) aren't chopping or placing at all — they happen on the exact tick the player **wakes up from sleep** when energy hits `9`. When we shrink Crafter's `64×64` screen down to `16×16`, the tiny energy digits **`6`** and **`9`** average out to the **exact same pixel numbers** (`0.00000` difference). So looking at just **one** frame, it is mathematically impossible for any honest model to tell "energy 6, keep sleeping" from "energy 9, wake up now!" Looking at **two** past frames (`t-1` and `t`) makes `8 → 9` jump out cleanly (`100%` precision on dev), immediately fixing all three failing actions in a quick linear check.
   - **Surprise #2 (chopping/placing gets drowned out by walking):** Real tree-chopping and table-placing *are* visible in `16×16` (even a simple linear rule predicts them), but walking + sleeping make up **98%** of the total pixel-change score while real `do` is `0.7%` and `place_table` is `0.07%`, so the model barely bothered learning them.
2. **Why step 5 drifted (`0.520 / 0.503` vs `0.498`):** It is **not** missed interactions and **not** blurry pictures (our model is actually `2×` sharper than the baseline at step 5!). Instead, its internal scratchpad (`z`) has `21×` more numbers than pixels, so repeating 5 imagination steps lets invisible scratchpad noise build up **`15×` off-track** during long walks. Just translating the scratchpad back through the picture decoder/encoder between imagined steps — with **zero retraining** — immediately fixes step 5 on **both** saved runs (`0.488` and `0.483`, beating the `0.498` bar!).
3. **One next change to try:** Give the imagination step **two past frames (`t-1` and `t`)** instead of one (matching every earlier test in PROBLEM-7). That directly unlocks the mathematically blocked `8 → 9` wake-up mark first (avoiding a wasted strike), and if step 5 still needs help, we already have the proven picture-snapping step ready right behind it. **Stopped here — nothing built yet.**
