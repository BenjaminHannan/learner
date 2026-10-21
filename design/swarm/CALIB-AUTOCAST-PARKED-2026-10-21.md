# Calibration under bf16 autocast (no chunking): drafted, review round 2 not clean, PARKED (2026-10-21)

Branch `claude/swarm-calib-autocast`. Draft only: not sealed, no PIN, no dry run, never run on a GPU, no box rented.

**What it does.** `MiniTrainer.calibrate` runs under the same bf16 autocast as `_train_step` (one `_autocast()` helper,
CUDA only). C0 probes every `train_d` arm (`TRAIN_PROBE_ARMS` = D1, S0, S1). A calibration at or above
`TrainConfig().memory_limit_bytes` (allocated or reserved) or a calibration exception stops C0 as "PROVED WRONG",
checked before the generic did-not-complete stop. Tests: FLOP samples, fit and FLOPs per update match within 0.1%
(D1, S0, CPU autocast), and the autocast tests fail when the fix is removed (shown by mutation).

**Round 2 open findings (why it is parked).**
1. Any exception in `calibrate` is called "PROVED WRONG", not only OOM (the brief asked for exception too; reviewer says narrow it).
2. `train_probe` swallows the traceback; only `calibrate` failures carry memory phases (step1/train OOM loses them).
3. One autocast context around all 9 measurements keeps the bf16 weight-cast cache across them, unlike a training step
   (fresh context each step); per-`measure_mini` context would match better. The calibration peak may differ from a
   training-step peak in kind. Untested without a GPU.
4. S1 not in the CPU FLOP-equality test; CUDA FLOP counts under autocast are untested (CPU only).
5. The limit is read from `TrainConfig()`, not from `mini_train_config`; S1 probe is unbudgeted memory-only time.
6. Smaller: arm-coverage test is partly tautological/source-text; `autocast` is a mutable flag; post-OOM current-bytes inflated.
