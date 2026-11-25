# PROBLEM-7 Rank 1 X-Ray — Read-Only CPU Diagnostic on Saved Weights

**Date:** 2026-11-24  
**Scope:** Rung 0 / Step A — strictly **no training**, **no GPU/MPS**, **no `/tmp/premonition_m3_mps.lock`**, **zero writes on M3** (`PYTHONDONTWRITEBYTECODE=1 nice -n 10 python -B -` on M3 CPU).  
**Scale note (`shown`):** All weights and numbers below come from `P7toy` (`2.47M` active / `6.14M` cell total, `16×16` Crafter frames), strictly separate from ~50M / ~500M production builds.  
**M3 Disk Stop Note:** After `verify_ruler.py` finished, M3 disk dropped to **`648 MiB` free (`100%` capacity, `/System/Volumes/VM` rose `14Gi → 19Gi`, total `wm5/` size only `51 MiB`)**. Per the `< 12 GB` hard stop rule, all further M3 CPU runs were halted immediately. Every fork-deciding X-ray metric (Parts 1, 2, 3A–3D, and `g_slow_imagine`) already completed and is recorded verbatim below.

---

## 1. Pre-Filed Fork Decision Marks (Verbatim From `IDEAS.md:50-54`, Unchanged) & Final Fork Decision

1. **Step-2 notepad per-action ridge `<= 0.70` AND row-independent frozen-trunk formula `> 0.90`:** Proves notepad already holds the world and Step 6 only failed from frozen trunk + row-blind head.
2. **Step-2 notepad per-action ridge `> 0.85`** (even though raw pixels get `0.504`): Proves the Step-2 notepad lost dynamic details → **skip Rank 4** and go straight to **Rank 3** (un-choke and retrain the shared brain).
3. **Perfect-memory oracle fails `std_ratio <= 2.0` on `noop` under whole-picture decoding while passing under residual-change decoding:** Confirms Rank 2's ruler fix is mandatory before any scored run.
4. **Falsifier:** Frozen trunk's `hn` reacts strongly to the button AND a single shared linear readout on `hn` already scores `<= 0.80`.

### Exact Pre-Filed Fork Decision (`shown`)
- **DECISION: SKIP RANK 4 → GO TO RANK 3 (un-choke shared brain + clean decoder) WITH MANDATORY RANK 2 RULER FIX!**
  - **Why (`shown`):**
    1. Under the exact legacy whole-picture target (`board_t → x_{t+1}`, `2A-abs`), Step-2 notepad per-action ridge scored **`E_1/B_1 = 0.8687 > 0.85`** (triggering pre-filed rule #2: **skip Rank 4**!). Even predicting board-to-board (`board_t → board_{t+1} → RT`, `2B`) scored **`0.7992` abs / `0.7081` res** (both `> 0.70`, board-delta `R² = 0.3764`). Even giving the Step-2 notepad a direct pixel skip `x_t + ridge(board_t)` (`2A-del`) only reached **`0.6925`** — still **`0.189` (`37%`) worse** than raw pixels (`0.5039`), because the Step-2 board is buried **`3,054 : 1`**!
    2. **Row-independent frozen-trunk formula (`hn[:, r] → dboard[:, r]`)** scored **`1.1904` abs / `1.0243` res** (`> 0.90`) with board-space **`R² = 0.0075` (`0.75%`)** BEFORE `RT` — even adding the action row `[hn[:, r], hn[:, R]]` only reached **`R² = 0.0078`**.
    3. **Falsifier NOT triggered:** Shared linear ridge on Step-6 `hn` scored **`1.2797` abs / `0.9723` res** (far above `0.80`). Worse, passing `real_board(t)` through the frozen trunk **destroyed** screen fidelity (`per-action` `dx` ridge degraded from `0.6925` on `Z_t` → `0.8123` on Step-2 init `hn` → `0.9242` on Step-6 trained `hn`!).
    4. **Ruler trap 100% confirmed:** Perfect-memory real-board oracle FAILED whole-picture `std_ratio <= 2.0` (`noop = 4.962`, `do = 2.048`, `all_n20_ok = False`, `active_ok = False`) and cleanly **PASSED** under residual-change decoding (`E/B = 0.3152 / 0.2221 / 0.1964`, `noop = 1.372`, moves `0.880–0.894`, `fw_std = 0.952`, `all_n20_ok = True`, `active_ok = True`, `pcs = 88/111`, `verdict = PASS`).

---

## 2. Exact Commands, Exit Codes & Reproduction Checks

- **Command executed (M3 CPU, read-only, zero M3 writes):**
  ```zsh
  ssh m3 'df -h ~ && cd ~/learner-ops/seven-problems-m3/PROBLEM-7/wm-harness && PYTHONDONTWRITEBYTECODE=1 nice -n 10 ~/learner-ops/m3-torch/.venv/bin/python -B -' < .../PROBLEM-7/neon-audit/run_xray.py > .../PROBLEM-7/neon-audit/xray_stdout.log 2>&1
  ```
- **Script:** [run_xray.py](<project>/PROBLEM-7/neon-audit/run_xray.py)
- **Raw log:** [xray_stdout.log](<project>/PROBLEM-7/neon-audit/xray_stdout.log)
- **Exit code & scope note:** `XRAY_EXIT=1` at line 771 (after completing ALL of Part 1, Part 2, and Part 3A–3B) due to a missing `.reshape(4000, -1)` on `Z5_ro` in the Step-5 refit block. Step-5 refit & Step-6 residual metrics were then completed in [verify_ruler.log](<project>/PROBLEM-7/forecast5/verify_ruler.log); we did NOT re-run `run_xray.py` for the 2 remaining secondary diagnostics (per-day/night `E/B` split and `g_slow_read`) because M3 disk dropped to `648 MiB` free immediately afterwards.
- **Data hashes verified (`shown`; `sealed_test.npz` NEVER touched):**
  - Legacy `train.npz`: `d423b5b9eecd68fd21981381781c9821775ecddc4ae3787d85d7c395215e505c`
  - Legacy `heldout.npz`: `add00c8bbc5d940ef5af006e983f7f34ef073aca9555430a601a47d9738413f0`
- **Reproduction checks (`shown`):**
  - Step-2 vs. Step-6 shared trunk max weight diff = **`0.000e+00`** (100% frozen confirmed).
  - `trunk_hn_and_gate()` vs. `imagine_head6.damped_imagine()` max diff `< 1e-6`.
  - Exact Step-6 frozen readout reproduced: `lam = 140.0`, `val_SSE = 625.73`, `val_base = 8607.45` (exact match to `run_forecast4.log`: `625.7 / 8607.5`).
  - Exact baselines reproduced: `B_1 = 16,475.33` (`copy = 17,384.61`, `blend = 16,475.33`, `bl1 = 0.886119`), pixel linear `M_a [x_t, 1]` `E_1/B_1 = 0.503872`.

---

## 3. Finding 1 — Board Burial (`3,054 : 1`) & Action-vs-Screen ANOVA (`shown`)

### 3.1 Real-Board Burial Is **3,054 : 1** (45× Worse Than the Earlier `68 : 1` Estimate!)
- Step-2 real boards (`train`, 3,500 frames):
  - **Static mean offset RMS:** **`1.36065`**
  - **Per-coordinate cross-screen spread RMS:** **`0.0004455`** (slow rows: `0.0001749`, fast rows: `0.0005469`; median coord std: `0.000319`, p95: `0.000819`, max: `0.002188`)
  - **Burial ratio:** **`3,054 : 1`** on train (`2,931 : 1` on held-out)!
- Entering `_trunk` (`h_in_board`): static RMS = **`1.8889`** vs. screen RMS = **`0.0003035`** → **the entire game screen enters the frozen trunk as a `6,225 : 1` whisper (`0.016%`)!**

### 3.2 Action Context & Bilinear ANOVA (`256` Held-Out Screens × `17` Actions)
- `enc_act` mean pairwise cosine across 17 actions: **`0.8087`** (Step-2 init, min `0.734`, max `0.866`; block-0 `V` cosine `0.769`) / **`0.8046`** (Step-6 trained; `V` cosine `0.764`), despite `action_emb` itself having cosine `0.0035` / `0.0386`. Confirms `src_emb + age_lin` collapsed 17 nearly orthogonal action vectors to `cos ~0.81`.
- Exact ANOVA decomposition `X[screen, action] = static_mean + u_screen[s] + v_action_additive[a] + w_bilinear[s, a]` on moves + `noop` (`0..4`):

| Model & Tensor (`0..4`) | `static_rms` | `screen_rms` | `act_additive_rms` | `act_screen_bilinear_rms` | `bilinear / act_additive` |
|---|---:|---:|---:|---:|---:|
| Step-2 init `h_in_board` | `1.8889` | `0.000303` | `0.0` | `0.0` | — |
| Step-2 init `hn_board` | `0.9918` | `0.000130` | `0.01555` | `0.0000424` | `0.00273` (`367×` smaller) |
| Step-6 trained `hn_board` | `0.9912` | `0.000129` | **`0.04020`** | **`0.00000395`** | **`0.000098` (`10,185×` smaller!)** |
| Step-6 trained `delta` (in `SD` units) | `0.02047` | `0.0000226` | **`0.02842`** | **`0.00000713`** | **`0.000251` (`3,986×` smaller!)** |

**What this proves (`shown`):**
- Step 6 was **NOT** deaf to the button — training pushed `h_in_action` RMS from `0.562` → `2.321` and `hn_board` additive action RMS from `0.0156` → `0.0402` (**311× louder** than the buried `0.000129` screen!).
- **Step 6 was blind to the `screen × action` interaction:** Because the screen was buried `6,225 : 1` entering `_trunk`, the multiplicative `screen × action` interaction in Step 6's `delta` was **`7.13e-6 SD`** — **3,986× smaller** than its screen-blind constant button tint (`0.02842 SD`)!
- Confirmed independently by `verify_ruler.py`: under residual-change decoding, Step 6's predicted frame changes collapsed to just **`pcs90_pred = 3 / 111`** (down from fake `112 / 111`!) — literally a 3-dimensional screen-blind button-tint subspace!

---

## 4. Finding 2 — Notepad Capacity & Frozen-Trunk Ridge Probes (`shown`, Held-Out `1000..1015`)

| Probe (Fit strictly on train `w < 140`, `lam` selected on train `w >= 140`, scored on held-out `1000..1015`) | Absolute `E_1/B_1` | Residual `E_1/B_1` | Board-Space `R²` | Notes |
|---|---:|---:|---:|---|
| Pixel 1-line linear per-action (`M_a [x_t, 1]`) | **`0.5039`** | — | — | Benchmark ceiling for stateless linear shifts |
| **Step-2 `real_board(t)` per-action → `x_{t+1}` (`2A-abs`)** | **`0.8687`** | — | — | **`> 0.85` → triggers pre-filed SKIP RANK 4!** |
| **Step-2 `real_board(t)` per-action → `dx` (`2A-del`, from `x_t`)** | — | **`0.6925`** | — | Still `+0.189` worse than raw pixels (`0.5039`) |
| **Step-2 `real_board(t)` per-action → `board_{t+1}` → `RT` (`2B`)** | **`0.7992`** | **`0.7081`** | **`0.3764`** | Even linear board dynamics stay `> 0.70` |
| Step-6 `hn[:, :R]` shared linear → `x_{t+1}` / `dx` | `1.2797` | `0.9723` | — | Falsifier (`<= 0.80`) **NOT** triggered |
| Step-6 `hn[:, :R+1]` (+ action row) shared linear → `x_{t+1}` / `dx` | `1.2796` | `0.9723` | — | Adding action row adds zero linear pixel power |
| **Step-6 `hn[:, r]` row-independent → `dboard[:, r]` → `RT`** | **`1.1904`** | **`1.0243`** | **`0.0075`** | **`> 0.90` confirmed; `0.75%` board `R²` BEFORE `RT`!** |
| Step-6 `[hn[:, r], hn[:, R]]` row + action → `dboard[:, r]` → `RT` | `1.1890` | `1.0229` | `0.0078` | Still dead even giving every row the action row |
| **Step-6 single row `hn[:, r]` → `dx` (best / median of 64 rows)** | — | `1.0256` / `1.0283` | — | Astra Rung-0 check: individual rows carry ~0% |
| Step-6 `hn[:, :R]` per-action FULL board → `x_{t+1}` / `dx` | `2.1810` | `0.9242` | — | Frozen trunk **degraded** `0.6925 → 0.9242`! |
| Step-2 init `hn[:, :R]` shared linear → `x_{t+1}` / `dx` | `1.0983` | `0.9443` | — | — |
| Step-2 init `hn[:, :R]` per-action FULL board → `x_{t+1}` / `dx` | `1.2759` | `0.8123` | — | Step-6 action training made `hn` screen info *worse* |

**Key takeaway (`shown`):** Passing the `3,054 : 1`-buried board through the frozen trunk **erodes** screen dynamics (`0.6925 → 0.8123 → 0.9242`), and row-wise `hn[:, r]` captures `< 0.8%` of the true board delta BEFORE `RT` is even applied (answering Astra's Rung-0 check: the bottleneck is NOT just the decoder — the buried board + frozen trunk genuinely destroyed the screen×action signal!).

---

## 5. Finding 3 — Ruler Trap & Frozen Gate (`shown`)

| Model / Oracle (Held-Out `1000..1015`, `k = 1`) | Ruler Mode | `E_1/B_1` | `copy_ness` | `pcs90` (`real=111`) | `noop` `std_ratio` | Moves `std_ratio` | `okstd` (old all / fixed active+fw) | Verdict |
|---|---|---:|---:|---:|---:|---|---|---|
| **Perfect-Memory Oracle (`real_board(t+1)`)** | OLD whole-picture | `0.4102` | `1.124` | `115` (`True`) | **`4.962` (FAIL!)** | `1.00–1.02` (`do=2.048` FAIL!) | `False` / `False` | **FAIL** |
| **Perfect-Memory Oracle (`real_board(t+1)`)** | **NEW `forecast5` residual** | **`0.3152`** | `0.810` | **`88` (`True`)** | **`1.372`** | **`0.88–0.89`** (`fw=0.952`) | **`True` / `True`** | **`PASS`** |
| **Exact Zero-Delta Identity (`next === st`)** | OLD whole-picture | `1.2217` | **`0.382` (FAKE!)** | **`113` (FAKE!)** | `4.918` | `0.53–0.56` | `False` / `False` | FAIL |
| **Exact Zero-Delta Identity (`next === st`)** | **NEW `forecast5` residual** | `1.0552` | **`0.0000`** | **`1` (`False`)** | **`0.000`** | **`0.000`** | **`False` / `False`** | **FAIL** |
| **Dead Step-5 Refit (`alpha ≈ 4e-5`)** | OLD whole-picture | `1.3314` | **`0.6046` (FAKE!)** | **`107` (FAKE!)** | `6.376` | `0.67–0.70` | `False` / `False` | FAIL |
| **Dead Step-5 Refit (`alpha ≈ 4e-5`)** | **NEW `forecast5` residual** | `1.054` | **`0.0022`** | **`5` (`False`)** | `0.15` | `0.04` | **`False` / `False`** | **FAIL** |
| **Saved Step-6 (`run_forecast4`)** | OLD whole-picture | `1.1913` | `0.396` | **`112` (FAKE!)** | `4.912` | `0.54–0.56` | `False` / `False` | FAIL |
| **Saved Step-6 (`run_forecast4`)** | **NEW `forecast5` residual** | `1.0257` | — | **`3` (`False`)** | — | — | **`False` / `False`** | **FAIL** |

- **Frozen slow-memory door (`g_slow_imagine`, Step-6 trained & Step-2 init):** `mean = 0.0942`, `std = 0.0203`, `min = 0.0662`, `median = 0.0881`, `p90 = 0.1225`, `max = 0.1390` — slow rows (24/64) are attenuated **~10.6×** on top of `imagine_scale`.
- **Legacy train vs. held-out lighting mismatch (`shown`):** Legacy `train.npz` has `t < 125 = 20,000`, `t >= 125 = 0` (`bright_min = 0.1515`, mean `0.2337`); legacy `heldout.npz` has `t < 125 = 3,842`, `t >= 125 = 1,166` (`23.3%`, `bright_min = 0.1087`, mean `0.2295`).
- **Two secondary diagnostics deferred due to M3 `648 MiB` disk stop:** per-day/night `E_1/B_1` split and `g_slow_read` tick comparison (neither can change the fork decision or ruler proof above).
