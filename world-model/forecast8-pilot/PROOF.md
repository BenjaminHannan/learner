# Forecast 8 Rel-PER Pilot Proof

## Scope and stop point

- Built and pinned only. NO pilot training, MPS run, scored Rank 8 run, or model evaluation was launched.
- No dev or sealed data path is used by the pilot driver. No lock was taken or modified. No secret, SSH-key, Keychain, auth, environment, or private data was read.
- `forecast7/` is unchanged; all local writes are under `forecast8-pilot/`. M3 writes are under `~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p/`.
- M3 transfer used `scp -p` only.

## Diff vs Rank 7

Command:

```bash
diff -u ../forecast7/train_v7.py train_v7.py > train_v7.diff
```

Output: `347 train_v7.diff`, exit `0` from the guarded diff wrapper (`diff` itself returned `1` for differences).

The diff contains only the sampler flag/implementation, per-sample residual extraction from the existing forward pass, event diagnostics/logging, and associated metadata. `model_v7.py`, `scorer.py`, and `withlock.sh` are byte-identical copies of Rank 7.

Rank 7 source hashes remain:

```text
50974a27fa87b147f55afdb838a643ce635234e338f0bc7139523c686a6e4e2b  forecast7/train_v7.py
c87f4110057bddaf4610c423e64c13dbe22f882aa9ea8dd53e4f3b57d7e67006  forecast7/model_v7.py
ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912  forecast7/scorer.py
77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa  forecast7/withlock.sh
b4e86c7dcd7afeba55bcaa56bfd000271219be8c7aad6d5c3720aa2f37318b05  forecast7/run_rank7.sh
b5bf690cc155ed7c04ffdd60b266a3d43851eaa8180cd7323eec993b22978786  forecast7/PLAN-AMENDMENT.md
```

## CPU tests

M1 command:

```bash
~/learner-ops/p2venv/bin/python -B -u test_pilot.py
```

M1 output:

```text
PASS: test_10_scorer_and_architecture_unchanged
PASS: test_1_pins_and_default_sampler
PASS: test_2_uniform_byte_identical_20_steps
PASS: test_3_relper_formula_distribution_and_determinism
PASS: test_4_relper_has_no_extra_forward_passes
PASS: test_5_heldout_worlds_never_enter_training
PASS: test_6_driver_cannot_reach_other_eval_paths
PASS: test_7_event_labeller_and_exact_p2_metric
PASS: test_8_paired_gate_boundaries
PASS: test_9_distribution_refreshes_every_25_steps_in_real_loop
ALL 10 PILOT TESTS PASSED
EXIT=0
```

M3 command:

```bash
ssh m3 'nice -n 10 ~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p/test_pilot.py'
```

M3 output:

```text
PASS: test_10_scorer_and_architecture_unchanged
PASS: test_1_pins_and_default_sampler
PASS: test_2_uniform_byte_identical_20_steps
PASS: test_3_relper_formula_distribution_and_determinism
PASS: test_4_relper_has_no_extra_forward_passes
PASS: test_5_heldout_worlds_never_enter_training
PASS: test_6_driver_cannot_reach_other_eval_paths
PASS: test_7_event_labeller_and_exact_p2_metric
PASS: test_8_paired_gate_boundaries
PASS: test_9_distribution_refreshes_every_25_steps_in_real_loop
ALL 10 PILOT TESTS PASSED
EXIT=0
```

Coverage includes byte-identical uniform batch indices, loss, metrics, and parameters over 20 optimizer steps; exact Rel-PER probabilities; deterministic seeded sampling with replacement; duplicate EMA updates; no extra forward calls; 25-step refresh in the real training loop; held-out world exclusion; driver path isolation; exact P2 computation and gate boundaries; pinned scorer/model/lock hashes; and the full scorer self-test (`ALL_PASS`).

## Real data preparation, no training

Command:

```bash
ssh m3 'nice -n 10 ~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p/pilot_driver.py --prepare-only'
```

Output:

```text
train: worlds 3000..3071, 25,200 actions/k1 windows, 25,382 frames
eval: worlds 3072..3079, 2,800 actions/k1 windows, 2,817 frames
source_sha256: 4d476e750b18fba2f2d6d8bf4f92c6306151f2e31228c749780ff61063503fc6
train_file_sha256: e6b497be18d98d92d32f4cec82e11bd6984902e43b362d8bedd380bdd314c90f
eval_file_sha256: 545870b81493e098fcaefb2b58798c803c45a5fb5c2ac205bcaebda620b7da8c
[PILOT] PREPARE_ONLY_NO_TRAINING
EXIT=0
```

Train/eval world sets are disjoint and exactly the pinned 72/8 split. Data-only event-labeller output:

```text
post_wake_hud_distance_threshold: 0.7312500589978819
train visual wakes: 126 (56 wake_e89 proxies, 70 wake_hurt proxies)
eval counts: moves=1708, do_awake=376, place=56, sleep_stay=369,
             wake_e89=9, wake_hurt=3, other=279
```

## Final hashes

Identical on M1 `forecast8-pilot/` and M3 `wm8p/`:

```text
c87f4110057bddaf4610c423e64c13dbe22f882aa9ea8dd53e4f3b57d7e67006  model_v7.py
ec44cdcaa44ecd528b9540003bfd3a4b7c1d75e737ad5af895630a05e39e9912  scorer.py
77e3ac48eb4df6ce20435bc16b880db6495371911187d39e0868df21b07ea0fa  withlock.sh
3c14e0a7b785ccd73de0f6f1711144562bfcbbcc188fdb552340f091db47da3c  train_v7.py
e44c3ec12d34268e5c24ad9cb35e23bab292c03087f8624cb53d251a77f9ec1d  pilot_driver.py
75a06ef37f7201e8ef47dcd34eb94d3801fef43782cf563a85a4af2480ebf2d3  test_pilot.py
4dd22636c4a8fc9e6d5a76f70e7e65243c234678f1e64203c78009ecb88bc3e9  PILOT-PLAN.md
827b3a7aeb3422fce238ffb09348522b060236b93fb08ba4bc6b87b1c24dcb86  train_v7.diff
```

M3 generated data:

```text
e6b497be18d98d92d32f4cec82e11bd6984902e43b362d8bedd380bdd314c90f  pilot_data/train_worlds_3000_3071.npz
545870b81493e098fcaefb2b58798c803c45a5fb5c2ac205bcaebda620b7da8c  pilot_data/eval_worlds_3072_3079.npz
f03ba429f7148b8fcc79e628588e0297214f4a41ab03ca49f227712267cba16d  pilot_data/manifest.json
```

## Exact pilot launch command

Lead only, on M3:

```bash
~/learner-ops/m3-torch/.venv/bin/python -B -u ~/learner-ops/seven-problems-m3/PROBLEM-7/wm8p/pilot_driver.py
```

The driver runs `s7_uniform`, `s7_relper`, `s8_relper`, `s8_uniform` serially through `withlock.sh`, 3,000 steps each, `--max-minutes 6.5`, expected total `24–27 min`. It writes `runs/pilot_summary.json` and exits nonzero on any P1/P2/P3 miss.
