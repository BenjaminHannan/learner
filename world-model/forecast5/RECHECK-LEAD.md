# PROBLEM-7 Forecast5 Pre-Run Re-Check (`RECHECK-LEAD`)

**Date:** 2026-11-24  
**Scope:** Independent read-only re-check of post-`BUGHUNT-LEAD` fixes on M1 `forecast5/` and M3 `wm5/` (`nice -n 10`, CPU only, zero MPS, zero `/tmp/premonition_m3_mps.lock`, `data/sealed_test.npz` never opened). Verified all 12 non-sealed SHA-256 hashes match between M1, M3, and `PLAN-AMENDMENT.md` §6.5; `test_v5.py` **16/16 PASS** on M3 CPU.

---

## Findings (Ranked)

### 1. `withlock.sh` lock acquisition & stale-lock reap can clobber a live holder
- **Location:** `withlock.sh:28, 53-64` (identical on M1 `forecast5/withlock.sh` and M3 `wm5/withlock.sh`)
- **Severity:** **blocks run** (machine-wide M3 MPS mutex safety)
- **Evidence:** **`shown`**
- **Details:**
  - **Stale-lock TOCTOU clobber (`:58-63`):** Two waiters polling a dead PID can both read `pid`, waiter A runs `rm -f "$L"` and atomically acquires `$L` via `set -C` (`:54`), then waiter B runs `rm -f "$L"` — **deleting waiter A's brand-new live lock** and entering concurrently. Reproduced on M3 (8 concurrent waiters on a stale lock, `PREMONITION_LOCK_POLL=0.02`, isolated temp lock): **`max_concurrent = 3` (`2` overlap events)**.
  - **Zero-byte lock clobber (`:54, 58-62`):** `( set -C; echo "$$ $(date +%s)" > "$L" )` creates `$L` empty (`O_CREAT|O_EXCL`) before `write()` populates the PID. If any waiter polls while `$L` is 0 bytes (including another M3 script writing `$L`), `cut -d' ' -f1 "$L"` yields `pid=""`, `[ -n "$pid" ]` fails, and `else rm -f "$L"` immediately unlinks the live lock (reproduced on M3: empty lock file deleted immediately with zero grace period).
  - **Unconditional unlink in `cleanup()` (`:28`):** `rm -f "$L"` does not verify `$L` still holds `$$`, risking cascading clobber if another process ever holds `$L`.
- **Exact fix:**
  1. Write `"$$ $(date +%s)"` to a unique temp file `"${L}.tmp.$$"` first, then atomically link `ln "$tmp" "$L"` and `rm -f "$tmp"` (POSIX-atomic, zero empty-file window, preserves `"PID TS"` format for other M3 scripts).
  2. Guard stale-lock removal with an atomic `mkdir "${L}.reap"` mutex (released on exit/return), **re-read** `"$L"` inside the mutex, only reap if `pid` is numeric & dead (or file is empty and older than `>= 2s`), and `rmdir "${L}.reap"`.
  3. In `cleanup()` (`:28`), unlink `"$L"` only if `[ "$(cut -d' ' -f1 "$L" 2>/dev/null)" = "$$" ]` (and add `trap 'on_signal 129' HUP` alongside `INT`/`TERM`).
  4. Sync M1 `forecast5/withlock.sh` ↔ M3 `wm5/withlock.sh` (update SHA-256 in `PLAN-AMENDMENT.md` §6.5) and add a stale-lock concurrent-waiter test in `test_v5.py:test_16`.

### 2. Minor documentation/edge nits (non-blocking)
- **Location:** `PLAN-AMENDMENT.md:131, 140`; `withlock.sh:49-51`
- **Severity:** **nit**
- **Evidence:** **`shown`**
- **Details:**
  - `PLAN-AMENDMENT.md:131` lists `r3_wrong = False` for the standalone `shift_or_stay` probe only because `ceiling_abs_pred_k1=None` (`ceiling_provided=False`); a trained model with `ceiling_abs <= 0.25` tying `shift_or_stay` (`0.0879`) correctly triggers `rank3_proved_wrong = True` (`scorer.py:587`).
  - `PLAN-AMENDMENT.md:140` prints `<= 0.0659` (`0.75 * 0.0879`), whereas `scorer.py:504` compares exact float64 `0.75 * 0.087948 = 0.06596`.
  - `withlock.sh:49-51` traps `EXIT`/`INT`/`TERM` but not `HUP` (worth adding in Finding #1's patch for foreground SSH disconnects).

---

## Verified Cleared Checks (`shown`)

1. **`scorer.py:classify_move_displacement` (`scorer.py:28-35, 109-178`):**
   - Verified Crafter `env.render()` geometry (`view=[9,9]`, `size=[64,64]`, `unit=7`, `border=0`, player tile `(4,3)` → `x=28..34, y=21..27`) box-pools **strictly** to global 16×16 `[5:7, 7:9]`.
   - `_build_terrain_masks_by_dir()` masks both destination `[5:7, 7:9]` and every bilinear-shifted source pixel touching `[5:7, 7:9]` (`8` masked / `88` clean terrain pixels per direction; `test_13` PASS).
   - Independent M3 CPU Crafter checks vs. `env._player.pos`: **`99.60%`** on worlds `9990..9999` (`n=1,254`, `FP=1/511`, `FN=4/743`) and **`98.88%`** on disjoint worlds `9980..9989` (`n=1,076`, `FP=2/300`, `FN=10/776`), confirming ~99% multi-world accuracy. Dev `1000..1015` counts match §6.2 exactly (`valid=3,034`, `open=2,222`, `blocked=812`, ambiguous `alpha ∈ [0.25, 0.55] = 40`).

2. **`shift_or_stay` & §6.2 bars (`scorer.py:261-317, 494-589` vs. `PLAN-AMENDMENT.md:121-154`):**
   - Crop is player-centered `[:, 3:9, 5:11, :]` in both `fit_shift_or_stay_baseline` (`:292`) and `rollout_shift_or_stay` (`:309`), covering all 4 adjacent tiles (`move_up` dev `fo` dropped `0.4416 → 0.0363`, `me = 0.0240`), fit strictly on `train` using fixed displacement labels.
   - Independently recomputed all 6 rows of §6.2 on M3 CPU (`train_dn.npz` → `../wm-harness/data/heldout.npz`): every `E/B`, 95% CI, `shuffle_pooled`, worlds count, `block_open` (`fb=0.0207 / fo=0.1552 / me=0.0879`), `legacy`, `rung1`, and `r3_wrong` matches §6.2 to 4 decimals.
   - "Neither rate worse" gate passes `0.7×` damped oracle (`fb=0.0153 <= 0.0207`, `fo=0.0000 <= 0.1552`, `me=0.0077`, `rung1=PASS`) and fails camera-shift-only `0.67`/`1.00` (`fo>=0.9926`, `me~0.500`, `rung1=FAIL`, `r3_wrong=True`).
   - `rung1_verdict` (`scorer.py:554-576`) and `rank3_proved_wrong` (`:579-588`) match §6.2–§6.3 1-to-1 (including `k1 shuffle_pooled >= 1.25`).

3. **Arm fairness, loud incomplete-run failure & 28-min cap (`train_v5.py:240-448`, `model_v5.py:230-253`):**
   - All 4 arms run `--steps 3000 --batch 64 --lr 3e-4 --wd 1e-4 --seed 42 --max-minutes 28.0`, identical batch RNG (`np.random.default_rng(42)`), zero dropout / `noise=False`, and bit-identical shared module init (`test_11` PASS; step-0 `rec/img_res/img_abs/row_rel` identical in M3 `timing_mps_*.log`).
   - `train_v5.py:395-408` raises `RuntimeError("INCOMPLETE RUN...")` before saving/scoring if `done < args.steps` (`test_15` PASS).
   - M3 MPS timing (`timing_mps_*.log`, synchronized via `torch.mps.synchronize()` at `:351-352, 399-400`) is `417.5–425.3 ms/step` → `20.88–21.26 min` for 3,000 steps (`+31.7%` headroom under `28.0 min`); historical 15–29 min M3 MPS logs (`run_forecast2/3/4.log`) show zero thermal slowdown.

4. **Finite `grad_norm` guard, `withlock.sh` non-race checks & §6.4 commands:**
   - `clip_and_check_grad_norm` (`train_v5.py:104-109, 381-382`) checks `torch.isfinite(grad_norm)` and aborts before `opt.step()` (`test_15` PASS).
   - `withlock.sh` exit-code passthrough (`0`/`7`), unbuffered piped streaming (`delta=1.21s` on 1.2s sleep, warnings/stderr preserved), and `SIGTERM`/`SIGINT` cleanup (including preserving live holder's lock when a waiter is terminated) all verified on M3.
   - All 5 §6.4 commands verified runnable as written: M3 paths, executable `./withlock.sh`, venv, all 4 arm names (`ARM_CONFIGS`), fresh `run_r1_*` output dirs, `28 GiB` free disk (`>= 12 GiB` floor), and `guard_sealed_path` (`train_v5.py:70-89, 262-263`) refusing `data/sealed_test.npz` unless both `--eval-only` and `--allow-sealed` are set.

---

## Verdict

**NO-GO** — required fix for GO: make `withlock.sh` acquire the lock without a zero-byte window (`tmp` + atomic `ln`), guard stale-lock reaping with an atomic `mkdir` mutex + re-check (no immediate unlink of empty locks), and verify `$$` ownership before `rm -f "$L"` in `cleanup()` (sync M1↔M3, update §6.5 hash, and cover stale-lock contention in `test_v5.py:test_16`).
