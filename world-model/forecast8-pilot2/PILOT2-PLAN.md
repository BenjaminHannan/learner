# Forecast 8 Rel-PER Second-Pilot Plan

Status: PINNED BEFORE ANY PILOT-2 TRAINING. This pilot is UNSCORED. No Rank 8 training is authorized by this file.

## Fixed second-pilot protocol

- Outcome: decide whether one domain-general sampler adjustment can keep Rel-PER's rare-event gains while restoring the wall gate.
- Single adjustment: change Rel-PER from 50% uniform / 50% prioritised to 75% uniform / 25% prioritised. Everything else remains exactly as pilot 1.
- Reuse pilot 1's `pilot_data/` by path. The driver accepts no data-path override and verifies both NPZ SHA-256 values before every launch.
- Train file: `train_worlds_3000_3071.npz`, worlds `3000..3071`, SHA-256 `e6b497be18d98d92d32f4cec82e11bd6984902e43b362d8bedd380bdd314c90f`.
- Eval file: `eval_worlds_3072_3079.npz`, worlds `3072..3079`, SHA-256 `545870b81493e098fcaefb2b58798c803c45a5fb5c2ac205bcaebda620b7da8c`.
- No dev or sealed data is used. The held-out 8 pilot worlds never enter training, sampler priorities, action means, event-labeller fitting, optimizer, or scorer baselines.
- Seeds `7` and `8` only. Four serial runs in balanced order: `s7_uniform`, `s7_relper_u75`, `s8_relper_u75`, `s8_uniform`, under a fresh `runs/` root.
- Arms are `uniform` and `relper_u75`. The driver maps `relper_u75` to trainer `--sampler relper --uniform-mix 0.75`. Uniform runs omit `--uniform-mix`, retaining pilot 1's default `0.5` behaviour and command path.
- Trainer default `--uniform-mix 0.5` reproduces pilot-1 Rel-PER probabilities exactly. Pilot 2 uses `p_j = 0.75/N + 0.25 * (r_j + 1e-6)^0.7 / sum_k((r_k + 1e-6)^0.7)`.
- Keep the existing action-normalised priority, cap, exponent, epsilon, EMA, refresh cadence, replacement sampling, unweighted loss, architecture, optimizer, schedule, data, scorer, rollout, and event labeller unchanged. The event labeller remains diagnostic/logging-only and never affects `p_j`.
- Rank 7 architecture/config: `R7conv`, `n_history=2`, two-frame input, `reencode`, batch `64`, AdamW `lr=3e-4`, `wd=1e-4`, `w_lat=0.05`, grad clip `1.0`, warmup+cosine, unweighted loss.
- Budget: `3000` steps per run and `--max-minutes 6.5`. An incomplete run fails loudly and is not saved or scored.
- Pinned `model_v7.py`, `scorer.py`, and `withlock.sh` hashes remain unchanged. Every M3 MPS run goes through the existing `withlock.sh`; the driver never reads or manipulates the lock directly.
- The P1/P2/P3 gate and summary logic are unchanged from pilot 1. In the verbatim block below, pilot 1's label `relper` means this pilot's `relper_u75` arm.

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

## Numerical second-pilot limits

| Seed | P1 action-5 std | P2 wake gap | P3 k1 E/B max | P3 k3 E/B max | P3 wall max |
|---|---:|---:|---:|---:|---:|
| 7 | `>= 0.30` | `>= 0.003285568` | `<= 0.302498862` | `<= 0.416700799` | `<= 0.065448336` |
| 8 | `>= 0.30` | `>= 0.002440902` | `<= 0.295619094` | `<= 0.407272043` | `<= 0.054507881` |

## Second-pilot falsifier

**Any** of the following on **either** seed proves the adjustment wrong:

1. P1 is below `0.30`.
2. P2 is below `3 * G_uniform`, or either P2 group is empty.
3. P3 k1, k3, or wall exceeds its same-seed allowance.
4. A run is incomplete, invalid, leaks held-out worlds into training, or touches dev/sealed data.

Decision rule:

- Any miss → **NO scored Rank 8**.
- A second pilot miss records **Rel-PER 2 of 3** and parks this sampler line; it does not spend the scored last strike.
- All three marks on both seeds → eligible for the lead's separate scored-Rank-8 decision, not an automatic scored run.

a miss = Rel-PER 2 of 3

## Exact launch

Lead only, on M3:

```bash
~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p2/pilot_driver.py
```

The driver writes `runs/pilot_summary.json`. `GO_SCORED_RANK8` requires P1, P2, and P3 on both seeds; otherwise it exits nonzero with `NO_SCORED_RANK8`. A pass only establishes eligibility for the lead's separate scored-Rank-8 decision.
