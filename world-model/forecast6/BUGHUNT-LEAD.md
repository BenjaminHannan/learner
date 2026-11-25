# PROBLEM-7 Forecast6 Pre-Run Bug Hunt (`BUGHUNT-LEAD`)

**Date:** 2026-11-25  
**Scope:** Independent read-only code, data, scorer, training-dynamics, and M3 CPU verification (`nice -n 10`, CPU only, `<= 50` steps, zero MPS, `/tmp/premonition_m3_mps.lock` untouched, `sealed_test.npz` never opened). Verified all 7 M1↔M3 code/log SHA-256s + `train_dn.npz`, `heldout.npz`, and canonical `board_swarm.py` match `PLAN-AMENDMENT.md` §6; `scorer.py` (`6ff1c135...`) and `withlock.sh` (`77e3ac48...`) are byte-identical (`cmp -s`) to pinned `forecast5/`; `test_v6.py` **10/10 PASS** on M3 CPU (`EXIT=0`).

---

## Findings (Ranked)

### 1. Power-guard device string check skips indexed MPS syntax (`mps:0`)
- **Location:** `train_v6.py:307` (vs. `train_v6.py:385, 439`)
- **Severity:** **should fix** *(non-blocking for pinned `--device mps` commands)*
- **Evidence:** **`shown`**
- **Details:** `train_v6.py:307` checks `if args.device == "mps" and not args.skip_power_check:` while lines `:385` and `:439` use `dev.type == "mps"`. Passing `--device mps:0` bypasses `check_mps_power()`. Both `run_rank6.sh:25` and `PLAN-AMENDMENT.md:97, 106, 121` pass literal `--device mps`, so pinned runs are protected; normalize to `torch.device(args.device).type == "mps"` when next convenient.

### 2. `--eval-only` loads `eval_data` before validating checkpoint & logs CLI default hyperparams
- **Location:** `train_v6.py:328, 336-369`
- **Severity:** **nit**
- **Evidence:** **`shown`**
- **Details:**
  - In `--eval-only --allow-sealed` mode, `ev = scorer.load_split(args.eval_data)` (`:328`) reads `sealed_test.npz` into RAM before `:356-362` verifies that `args.eval_only` exists and matches `arch`/`size` (though any error aborts before scoring or printing).
  - `:367-368` restores `train_meta["seed"]` from `ck_meta`, but leaves `w_lat`, `lr`, `wd`, and `batch` (`:342-345`) at CLI defaults. Those defaults (`0.05, 3e-4, 1e-4, 64`) match the pinned Rank-6 command, so `score_sealed.json` will be exact for Rank 6; copy them from `ck_meta` if hyperparams ever vary later.

### 3. Minor `run_rank6.sh` shell-hygiene nits
- **Location:** `run_rank6.sh:11, 37-38, 40-58`
- **Severity:** **nit**
- **Evidence:** **`shown`**
- **Details:**
  - `:40-58`: the final `$PY -c "..." >> rank6_driver.log 2>&1` summary has no `|| exit $?`, so a summary error would still append `DONE_ALL` and exit `0`.
  - `:11`: `grep -o "[0-9]*%"` matches bare `%` (0 digits), failing closed to `0`; `grep -Eo "[0-9]+%"` is cleaner. (All 6 tested `pmset` strings — AC@10%, Batt@35%, Batt@34%, Batt@100%, no-`%`, empty — returned expected exit codes `0,0,1,0,1,1`.)
  - `:37-38`: if seed `42` exits `0` with `rank6_verdict == "FAIL"`, `run_rank6.sh` still runs seed `43` (`~6.7 min`) before logging `agg=FAIL sealed_candidate=NONE`. This matches `PLAN-AMENDMENT.md:61, 111`, gives 2-seed confirmation, and never touches sealed.

### 4. Early-training loss tug-of-war (`l_img_res` vs. `0.25 * l_img_abs`) & initial `delta` damping (resolves naturally)
- **Location:** `train_v6.py:154-164`; `model_v6.py:127-130, 236`
- **Severity:** **nit** *(observation / monitor only — no leak or fairness bug)*
- **Evidence:** **`shown`**
- **Details:**
  - Measured on M3 CPU (`R6conv`, `train_dn.npz`, `batch=32`): while `l_rec` is still well above `copy_mse` (`rec = 0.0184` vs `copy = 0.0047`), `0.25 * l_img_abs` pushes `dynamics` to cancel static AE error `e_0 = x_rec_t - x_t`, transiently opposing `l_img_res` (`cos = -0.942` on `dyn`, `-0.514` on `dec`, `cos(l_rec, l_img_res) = -0.777` on `dec`).
  - Once `l_rec` drops near `copy_mse` (`rec = 0.0073`, 50 steps at `lr=1e-3`), every gradient cosine flips strongly positive: `[dec]` `cos(l_rec, l_img_res) = +0.445`, `cos(l_img_res, 0.25_abs) = +0.708`; `[dyn]` `cos(l_img_res, 0.25_abs) = +0.811`, `cos(l_img_res, w_lat) = +0.161` with `l_img_res` dominant (`1.02e-2` vs `0.25_abs` `5.55e-3` vs `w_lat` `1.15e-3`); `[act]` `cos(l_img_res, 0.25_abs) = +0.928`, `cos(l_img_res, w_lat) = +0.839`.
  - Step-0 `out_conv` (`std=0.02`, `fan_in=576`) gives `pred_dz_rms = 0.271` (`34×` `true_dz_rms = 0.008`), so early steps damp `delta` (`img/copy 1.468 → 1.032` by step 59 in `timing_mps_r6.log`), while `action_emb` grad starts small (`1.9e-4 → 1.9e-6`, still `190× > AdamW eps=1e-8`). Worth watching in `run_r6_s42.log` (`img/copy` and `rec` by step 250–500).

---

## Cleared Checks (`shown`)

1. **Leakage, dev split & sealed guard (`train_v6.py:94-123, 177-263, 304-305`; `model_v6.py:326-366`):**
   - `rollout(x0, acts_k)` encodes `x0` once and steps purely on its own `z`; no BatchNorm/dropout or cross-sample state. Independent 16-world real `heldout.npz` `k=5` NaN-poisoning test (`t=1..4 = NaN`) produced `finite=True, bit_equal=True` outputs; `test_4` PASS.
   - `train_dn.npz` (`3000..3079`, `28,000` k1 wins) and dev `heldout.npz` (`1000..1015`, `5,008` k1 wins) have `overlap=set()`. `scorer.py` fits `mean_tr`, `bl`, `Mact`, and `sos` strictly on `train`.
   - `guard_sealed_path` blocks lexical paths, symlinks (`realpath`), and renamed copies (pinned SHA-256) unless both `--eval-only` and `--allow-sealed` are passed, and rejects `--allow-sealed` on non-sealed files (`test_7` PASS). `sealed_test.npz` on M3 is `-r--r--r--` (`chmod 444`), untouched (`Nov 24 16:02`).
2. **Eval ↔ `scorer.py` contract, ceiling & anti-shortcut (`train_v6.py:222-263`; `model_v6.py:75-261`; `scorer.py:500-576`):**
   - `preds_by_k`/`shuf_preds_by_k` match `[N_k, 16, 16, 3]` float64 residual convention `x0 + (dec(z_k) - dec(z_0))`; `ceiling_abs_pred_k1 = decode(encode(x_{t+1}))` and `ceiling_res_pred_k1` match §3.1 verbatim (`test_4` PASS).
   - Adversarial probes on real `heldout.npz` through `evaluate_model` + `scorer.py`: `PerfectAE+ZeroDyn` (`ceil=0.0000`, `E/B=1.0571`) → `FAIL`; `PerfectAE+1.75px CameraShift` (`ceil=0.0000`, `E/B=0.861/0.976/1.083`, `bo fb=0.000/fo=1.000/me=0.500`) → `FAIL`; `BrokenAE+PerfectPred` (`ceil=28.595`, `E/B=0.0000`) → `FAIL`.
   - `4×4` bottleneck self-attention (`SpatialSelfAttention2d`) and `[-1, 1]` `CoordConv` are 100% domain-general learned components (zero hardcoded player/HUD/shift coordinates).
   - Active actions in `heldout.npz` (`std_real >= 0.02, n >= 20`) cover all 4 moves (`1..4`), `do` (`5`), `sleep` (`6`), and actions `8, 9`; a PASS requires beating `shift_or_stay` at `k=1, 3, 5` + `>= 25%` `block_open` cut with neither `fb` nor `fo` worse + shuffle/anti-collapse/ceiling gates, genuinely requiring action-dependent physics.
3. **Training isolation, seeds & fixed-step enforcement (`train_v6.py:126-174, 316-448`):**
   - `z_t.detach()`, `x_rec_t.detach()`, and `no_grad` on `z_next_tgt` give exact `0.0` imagination grad on `encoder` and exact `0.0` `l_rec` grad on `dynamics`/`action_emb` (`test_3` + M3 `R6conv` grad probe).
   - Seeds `42` and `43` differ genuinely in weights (`max_wdiff=0.08279`), batches (`0/64` overlap), 5-step losses, and `k=5` dev rollouts (`max_abs_diff=1.32016`), while sharing eval shuffle seed `43`.
   - Fixed `--steps 5000` (`6.37 min` calibrated MPS vs `--max-minutes 14.0`, `2.2×` headroom), fail-loud `INCOMPLETE RUN` if `done < steps`, and finite loss/grad guards before `opt.step()` (`test_9` PASS).
4. **Driver, lock, disk, power & plan-vs-code verdicts (`run_rank6.sh:1-58`; `withlock.sh:1-99`; `scorer.py:554-588`):**
   - `run_rank6.sh` (`chmod +x`, `zsh -n` clean) checks M3 disk (`26G >= 12G`), waits for AC/`>= 35%` battery (M3 currently `AC Power`, `43%`), runs seed `42` then `43` under bit-identical `withlock.sh` (`test_10` PASS), exits on non-zero `rc`, and never references `sealed_test.npz` (only prints `sealed_candidate`).
   - `PLAN-AMENDMENT.md` §4.1–§4.4 (`PASS`, `PARTIAL` incl. Bug A10, `FAIL`, two-seed tie-break `(k1, k5, seed)`) matches `scorer.py:554-576`, `train_v6.py:261-262`, and `run_rank6.sh:40-57` 1-to-1 across all 9 tested verdict/tie-break cases. *(Note: `score_dev.json` still emits legacy `rank3_proved_wrong` from unchanged `scorer.py:581-588`; `train_v6.py` and `run_rank6.sh` correctly gate on `rank6_verdict`.)*

---

## Verdict

**GO** — zero blocking bugs found; launch the pinned two-seed dev run (`run_rank6.sh`) as written (optional non-blocking cleanup later: use `torch.device(args.device).type == "mps"` at `train_v6.py:307`, validate `--eval-only` ckpt before loading `eval_data` at `train_v6.py:328`, and add `|| exit $?` on `run_rank6.sh:57`).
