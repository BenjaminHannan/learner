# Forecast 8 Rel-PER Pilot Plan

Status: PINNED BEFORE ANY PILOT TRAINING. This pilot is UNSCORED. No Rank 8 training is authorized by this file.

## Data and split

- Source: the existing `../wm5/data/train_dn.npz`, SHA-256 `4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6`, worlds `3000..3079`.
- Pilot training worlds: `3000..3071` (72 worlds, 25,200 k=1 windows).
- Pilot evaluation worlds: `3072..3079` (the last 8 source worlds, 2,800 k=1 windows), fixed before results.
- The split is by whole world and preserves whole episodes. The held-out 8 worlds are never present in the training file, sampler, action means, priorities, event-labeller fit, optimizer, or scorer baselines.
- No alternate evaluation split is used. The pilot driver accepts no data-path override and passes only its two generated pilot files to the trainer.

## Runs and budget

- Seeds: `7` and `8` only.
- Arms: `uniform` and `relper` for each seed; 4 serial runs total in balanced order `s7_uniform`, `s7_relper`, `s8_relper`, `s8_uniform`.
- Rank 7 architecture/config: `R7conv`, `n_history=2`, `reencode`, batch `64`, AdamW `lr=3e-4`, `wd=1e-4`, `w_lat=0.05`, grad clip `1.0`, warmup+cosine, unweighted loss, pinned `model_v7.py`, pinned `scorer.py` (`ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912`).
- Pilot budget: `3000` steps per run, `--max-minutes 6.5`. This is the sole budget deviation from Rank 7's 5,000-step scored protocol, required to keep four serial M3 MPS runs under 30 minutes. Both arms receive the identical budget and schedule.
- Expected time from the Rank 7 M3 calibration (`117.1 ms/step`): about `5.85 min` training per run plus lock/eval overhead, or about `24–27 min` total. The 6.5-minute training cap fails loudly rather than saving an under-stepped model.
- Every run uses `withlock.sh`; the driver does not read or manipulate the lock directly.

## Exact Rel-PER change

For each training k=1 transition `j`, with action `a_j`:

- `e_j` initializes to copy MSE `mean((x_{t+1,j} - x_{t,j})^2)`.
- `v_a` is the training-only mean copy MSE for action `a`.
- `r_j = min(e_j / (v_{a_j} + 1e-4), 20)`.
- `p_j = 0.5 * (1/N) + 0.5 * (r_j + 1e-6)^0.7 / sum_k((r_k + 1e-6)^0.7)`.
- A seeded NumPy `Generator` samples with replacement.
- The distribution is refreshed at step 0 and every 25 completed steps.
- `e_j` updates only from detached per-sample residual MSE already computed in the sampled training batch: `e_j = 0.8*e_j + 0.2*residual_mse_j`. Duplicate draws update in draw order. There are no extra forward passes.
- Loss remains unweighted. Uniform remains the default and uses the original `rng.integers(0, N, size=batch)` path.

## Event labeller and sampler log

The labeller is visual and data-derived, using the existing Rank 6/7 sleep-screen rule:

- `asleep = std(x_t[:, :12]) < 0.08`.
- `visual_wake = asleep and std(x_{t+1}[:, :12]) > 0.10 and RMS(x_{t+1}-x_t) > 0.08`.
- `awake_hud_reference` is the training-only median HUD `x_t[:, 12:]` over non-asleep k=1 transitions.
- `post_wake_hud_distance = sum((x_{t+1}[:, 12:]-awake_hud_reference)^2)` over HUD rows, columns, and RGB.
- On the 72 pilot training worlds only, deterministic 1-D two-means splits `post_wake_hud_distance` over `visual_wake` transitions. The lower-distance cluster is the `wake_e89` visual proxy (post-wake HUD closest to the typical awake HUD); the higher-distance cluster is the `wake_hurt` visual proxy. The threshold is the midpoint of the two final centers. This is a visual proxy, not hidden game-state ground truth.
- Mutually exclusive labels, in overriding precedence: `wake_e89`, `wake_hurt`, `sleep_stay` (`asleep` and not `visual_wake`), then `moves` (actions 1..4), `do_awake` (action 5 while awake), `place` (actions 8/9 while awake), else `other`.
- Data-only pin check: threshold `0.7312500589978819`; train visual wakes split into 56 `wake_e89` proxies and 70 `wake_hurt` proxies. The fixed eval split has 9 `wake_e89`, 3 `wake_hurt`, and 369 `sleep_stay` windows, so P2 is non-vacuous but uses only 9 wake proxies.
- Every 250 steps, log cumulative sampled-window share for `moves`, `do_awake`, `place`, `sleep_stay`, `wake_e89`, `wake_hurt`, `other`, plus cumulative mean `r_j` per type. Uniform logs its fixed copy-derived `r_j`; Rel-PER logs the online EMA-derived `r_j` at sample time. Labels never affect sampling.

## Pre-registered pilot marks

P1: relper action-5 std ratio >= 0.30 on BOTH seeds (k1, under the ec44cdca std computation on the pilot eval split).

P2: wake vs stay-asleep separation: relper's mean predicted brightness change on 8→9 wake windows exceeds stay-asleep windows by >= 3x the uniform arm's gap, on both seeds (define it exactly, data-derived).

P3: no regression: relper k1 E/B <= uniform + 0.005, k3 <= uniform + 0.008, wall mean_err <= uniform + 0.005, on both seeds.

All three must hold. Any miss means NO scored Rank 8, and the conv line parks at 2/3 (recorded as unscored).

Exact P2 computation:

- `dBright_i = mean((pred_k1_i - x_t_i)[:, :12])` over terrain rows, columns, and RGB.
- `G_arm = mean(dBright_i | wake_e89) - mean(dBright_i | sleep_stay)` on the fixed 8-world eval split.
- P2 passes for a seed iff both groups are nonempty and `G_relper >= 3 * G_uniform`.

P1 reads `k1.std_ratio_by_action["5"].ratio`. P3 reads `k1.E_over_B`, `k3.E_over_B`, and `k1.block_open.model.mean_err`.

`diag_non_wake_interactions.asleep_all.R2` is reported as `diag_aslR2` for each arm and seed as a pre-registered DIAGNOSTIC only, never as a gate.

## Exact launch

Run on M3 only:

```bash
~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p/pilot_driver.py
```

The driver writes `runs/pilot_summary.json`. `GO_SCORED_RANK8` requires P1, P2, and P3 on both seeds; otherwise it exits nonzero with `NO_SCORED_RANK8`.
