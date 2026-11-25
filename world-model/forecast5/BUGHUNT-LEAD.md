# PROBLEM-7 Forecast5 Pre-Run Bug Hunt (`BUGHUNT-LEAD`)

**Date:** 2026-11-24  
**Scope:** Independent read-only code, data, scorer, and M3 CPU diagnostic audit (`nice -n 10`, zero MPS, zero lock, `sealed_test.npz` untouched). Checked M1 `forecast5/` and M3 `wm5/` (all 8 pinned SHA-256s match; canonical `board_swarm.py` SHA-256 verified; `test_v5.py` 12/12 PASS on M3 CPU).

---

## Findings

### 1. Shifted player-sprite bleed corrupts 26.6% of dev `block_open` "blocked" labels
- **Location:** `scorer.py:28-32, 149-158`
- **Severity:** **blocks run**
- **Evidence:** **`shown`**
- **Details:** `_TERRAIN_MASK` excludes the `2×2` player sprite (`rows 5..6, cols 7..8` in `16×16`) from `x0c`/`x1c`, **but does not exclude pixels where `_bilinear_terrain_shift(xs, dy, dx)` samples *from* the player sprite into adjacent unmasked terrain.** Because the player stays centered while the world shifts, `sh` injects a phantom shifted player sprite into `s = sh - x0c` that never appears in `df = x1c - x0c`:
  - Against ground-truth Crafter `env._player.pos` (6 throwaway episodes, worlds `9999`, `812` moves), current `classify_move_displacement` gets **`acc = 82.47%` (`FN = 115/555 = 20.7%`, `FP = 0/101`)**. Masking both destination `[5..6, 7..8]` and bilinear source pixels touching `[5..6, 7..8]` immediately raises accuracy to **`99.44%` (`FN = 3/438 = 0.68%`, `FP = 0/98`)**.
  - On dev `heldout.npz` (`1000..1015`), **`296 / 1,111` (26.6%) of current `"true_blocked"` labels are corrupted**: `260` are uniform-grass open moves (median terrain MSE `3e-6`) where phantom sprite energy pushes `sn >= 5e-4` while `df ≈ 0` forces `alpha ≈ 0`, and `36` are textured open moves whose `alpha` is dragged below `0.40` by phantom sprite energy in `<s, s>`. The ambiguous band `alpha ∈ [0.25, 0.55]` drops `4.5×` (`189 → 42`) once fixed.
  - Because phantom energy drags true open moves' `alpha` down, even a `0.7×` damped oracle (`E_1/B_1 = 0.0951`, `79%` error cut) gets `fb = 0.0653` (failing `<= 0.0360`) under current `scorer.py`, vs `fb = 0.0171` once sprite bleed is fixed.

### 2. `shift_or_stay` baseline misses `move_up` (`crop[5:11]` miscentered) AND its noisy `MSE > 1e-4` label creates a skewed `fb` false-fail trap
- **Location:** `scorer.py:256, 271, 288, 482-486` (and pinned refs in `PLAN-AMENDMENT.md:129, 135`)
- **Severity:** **blocks run**
- **Evidence:** **`shown`**
- **Details:** In Crafter (`view=(9,9)`, `unit=7`, `local_view` `63×49 px`, player at tile `(4,3)` → `16×16` **rows `5..6`, cols `7..8`**), the obstacle tile directly **above** the player (`move_up`, action `3`) sits in **rows `3..4`**.
  - `fit_shift_or_stay_baseline` (`:271`) and `rollout_shift_or_stay` (`:288`) crop `X_img[:, 5:11, 5:11, :]`, completely omitting rows `3..4`. On dev `1000..1015`, `shift_or_stay`'s `move_up` false-open rate is **`0.4416`** (`mean_err = 0.2427`), **3.7× worse** than with a player-centered `[3:9, 5:11]` crop (`fo = 0.1204`, `me = 0.1098`, `E_1/B_1 = 0.3167` vs `0.3375`).
  - Additionally, `:256` trains `Wgate`/`Mshift` on `moved = MSE > 1e-4`, which fires on **`45.2%` (`19/42`) of truly blocked moves** (HUD/facing/mob drift). Combined with `BLOCK_OPEN_ALPHA_THRESH = 0.40`, this biases `Wgate` upward into an artificial 8:1 skew (`fb = 0.0360`, `fo = 0.2799` on current `block_open`; `fb = 0.0085`, `fo = 0.3914` on fixed `block_open`).
  - Gating `model.false_block_rate <= base.false_block_rate` (`:484`) against that artificially skewed `fb` rejects a **`0.7×` damped oracle** (`E/B = 0.095/0.103/0.109`, `79%` block/open error cut, `fo = 0.000`) AND rejects a strictly stronger centered `shift_or_stay` (`E/B = 0.2853/0.4068/0.4978`, `fix_bo = 0.0885`, `fb = 0.0211`, `fo = 0.1558` — a `56%` error cut!).
  - Fixing both Findings #1 and #2 gives an honest baseline (`E/B = 0.2853 / 0.4068 / 0.4978`, `fb = 0.0211`, `fo = 0.1558`, `me = 0.0885`) and lets `0.7×–0.9×` oracles pass (`fb = 0.0018–0.0171 <= 0.0211`); consider also setting `BLOCK_OPEN_ALPHA_THRESH = 0.50` or allowing small slack on `fb` (e.g. `<= max(base.fb, 0.05)`) so a balanced model cutting `mean_err` by 50% cannot fail on a 2% `fb` ceiling.

### 3. `--max-minutes 25.0` wall-clock cap risks unequal step counts & truncated cosine LR across arms
- **Location:** `PLAN-AMENDMENT.md:101, 162, 171, 180, 189`; `train_v5.py:213-218, 368-370`
- **Severity:** **blocks run**
- **Evidence:** **`shown`** (M3 MPS logs + CPU arm timing) + **`suggested`** (MPS scaling)
- **Details:** Existing M3 MPS logs for `P7toy` (`batch=64`, 3,000 steps, unfrozen trunk) took **`1,517s` (`25.3 min`)** in `run_forecast3.log` and **`1,732s` (`28.9 min`)** in `run_forecast2.log` — *without* `train_v5.py`'s 3.03M `RowLNDecoder` (2×/step), `ContextRead` (5×/step), or `act_film`. `train_v5.py` has never been timed on M3 MPS.
  - On M3 CPU (`P7toy`, `batch=64`), `no_signal_path` is `4.3%` faster per step than `bundle` (`0.696s` vs `0.726s`, skipping 5 `ContextRead` attention passes/step); MPS small-kernel launch overhead typically widens this gap.
  - If `--max-minutes 25.0` (`1,500s`) triggers early, slower arms (`bundle`, `abs_loss_only`) will execute **fewer steps** and stop higher on the 3,000-step cosine schedule (`lr_factor(s, args.steps)`) than `no_signal_path` / `no_act_film`.
  - `train_v5.py:368-370` silently saves and scores capped runs without recording `cap_hit: True` or failing.

### 4. `withlock.sh` masks non-zero exit codes, block-buffers logs, and strips `Warning` lines
- **Location:** `../wm-harness/withlock.sh:3-6` (invoked by `PLAN-AMENDMENT.md:159, 168, 177, 186, 195`)
- **Severity:** **should fix**
- **Evidence:** **`shown`**
- **Details:** `"$@" 2>&1 | grep -v Warning | tee $LOG` followed by `rm -f $L; echo ...` returns exit code `0` even if `train_v5.py` aborts (NaN `RuntimeError`, disk floor, OOM, sealed-guard refusal). `grep -v Warning` lacks `--line-buffered` (stalling live logs) and hides PyTorch/MPS warnings. There is also no `trap` to release the lock on `SIGINT`/`SIGTERM`. Capture `rc=${pipestatus[1]}`, add a `trap`, drop `grep -v Warning` (or use `python -W ignore::FutureWarning`), and `exit $rc`.

### 5. Non-finite gradient check missing before `opt.step()` + `0.005 * l_row_rel` dominates step-0 loss asymmetrically
- **Location:** `train_v5.py:124-132, 340-358`
- **Severity:** **should fix**
- **Evidence:** **`shown`**
- **Details:**
  - `train_v5.py:340` checks `torch.isfinite(loss)` before `backward()`, but never checks `total_norm = clip_grad_norm_(...)` (`:355`) before `opt.step()`. A `NaN`/`Inf` gradient on the final step silently poisons `model.pt` and later crashes `scorer.py:92` (`eigvalsh`) instead of failing cleanly.
  - At step 0 (`P7toy`, `batch=64`), `signal_path_init_v5`'s `out_proj std=0.1` accumulates over 4 unbounded fast-row ticks (`fast_rms = 5.74`, `static_rms = 4.66`) plus a 5th imagine tick (`diff_rms = 1.066`), making `0.005 * l_row_rel = 0.242` (`42×` larger than `l_img_res = 0.0058`; still `0.084` at step 50 in `smoke_cpu_bundle`). Meanwhile `no_signal_path` has `row_var = 3e-5` clamped `33×` to `1e-3` (`0.005 * l_row_rel = 0.321`). Not a leak, but worth monitoring in logs (`l_row_rel` weight vs pixel losses).

### 6. Minor spec/eval discrepancies (`r1_shuf_pool1`, `abs_loss_only` diagnostic, legacy vs Rung-1 shortcut)
- **Location:** `scorer.py:538-547` vs `PLAN-AMENDMENT.md:127, 138-140`; `train_v5.py:184, 310`
- **Severity:** **should fix** (first item) / **nit** (rest)
- **Evidence:** **`shown`**
- **Details:**
  - `scorer.py:538-547` gates both `rung1_verdict == "PASS"` and `"PARTIAL"` on `k1["shuffle_pooled"] >= 1.25`, which is omitted from `PLAN-AMENDMENT.md` §6.2 (present only in §6.3 `rank3_proved_wrong`). Sync doc and code.
  - **Camera-shift shortcut check (`shown`):** A 100% obstacle-blind shortcut (`0.67 * shift(x0, dir) + 0.33 * x0` on moves + `M_a` on non-moves; `block_open.mean_err = 0.5000`) scores `E/B = 0.6796 / 0.8405 / 0.9342`, `shuf = 2.048 / 1.358`, `worlds_both = 16/16`, `std_ok = True`, `pcs = 114/111` → **`verdict = PASS`** on the legacy ruler, and **`FAIL` / `rank3_proved_wrong = True`** on Rung 1. Thus **only `rung1_verdict == "PASS"` (with Findings #1–#2 fixed) demonstrates action-dependent obstacle physics rather than a camera-shift shortcut.**
  - `train_v5.py:184` scores `abs_loss_only` only on `pred_res` without logging `pred_abs` `E/B` as a diagnostic; adding a non-gating `pred_abs` metric clarifies whether `abs_loss_only` failed to learn or only suffered from `-e_0` residual subtraction.
  - `PLAN-AMENDMENT.md:127`: Copy row (`1.055 / 1.140 / 1.203`) came from legacy `train.npz` `B_k` rather than `train_dn.npz` `B_k` (`1.057 / 1.146 / 1.213`).
  - `train_v5.py:310`: `if ck_arm is not None and ck_arm != args.arm:` lets a checkpoint missing `meta.arm` bypass the arm check (`if ck_arm != args.arm:` is stricter).

---

## Cleared Checks (`shown`)
- **Leakage & open-loop integrity:** Disjoint world IDs (`train_dn` `3000..3079`, dev `1000..1015`, sealed `2000..2015` `chmod 444` untouched); contiguous episodes and exact `t_index`; all baselines (`mean_tr`, `bl`, `Mact`, `sos`) fit strictly on `train`; `rollout` at `k=3, 5` initializes once at `(x_{t-1}, x_t)` with action-only `enc_act` (zero future peeking); `guard_sealed_path` resolves symlinks and verifies pinned SHA-256; `block_open` ground-truth labels never read model outputs.
- **Arm init/data parity:** Shared modules (`cell`, `reader`, `pos`, `action_emb`, `dec`) are bit-identical across all 4 arms at `seed=42` (`test_11` PASS), batch order (`np.random.default_rng(42)`) is identical, `board_swarm.py` untouched, M1↔M3 hashes match on all 8 files.
- **Core scorer math & infra:** `E_k/B_k`, per-step within-world shuffle (`seed=43`), horizon-`k` moved mask, world-ID keyed `worlds_both`, paired world bootstrap CIs, `pcs90`, `std_ratio_active_and_fw_ok`, `proves_wrong`, and `rank3_proved_wrong` are sound; perfect oracle passes both verdicts and copy/zero fail both; M3 venv (`torch 2.14.1`, MPS available), paths, log names, `score_dev`/`score_sealed` split naming, and disk (`28 GiB` free vs `12 GiB` floor) verified.

---

## Verdict

**NO-GO** for the scored runs — required fixes for GO: (1) mask both destination and bilinear-shifted source player-sprite footprints in `scorer.py:classify_move_displacement`, (2) center `shift_or_stay`'s crop on the player (`rows 3:9, cols 5:11`) and fit its gate on fixed displacement labels (re-pinning §6.2 dev baseline numbers and verifying `fb` gate fairness), and (3) calibrate MPS step timing so all 4 arms run an exact fixed `--steps` guaranteed to finish well below `--max-minutes` (and fail/flag if `done < args.steps`).
