# defer port pack (B3G2 deferred batched writer)

**DRAFT. All code in this folder is a draft until the coordinator has code-reviewed it. Not for use before that.**

## What it is
An overlay pack that ports the speed change "defer" (`launch/defer.py`, the GPU-RUN-4 / GPU-RUN-5 variant) into the production trainer of the B3G2 arm as an opt-in flag. With
`--speed-arms defer`, `B3G2._loss` (teacher forcing, training, autograd on, `talk_rounds == 'last'`, no copy writer) runs `models/b3g2_defer.py`: one thinker-only loop, then one batched call pass
and one batched answer pass over all (round, row) pairs, with every host-side list taken from the numpy schedule (`B3G2.plan_np`). Anything else (eval, `no_grad`, `talk_rounds 'all'`) runs the
original body and is counted in `model.defer_stats['fallback']`. The ops, their order and the dtypes are those of `defer.py` (checked by `test_port_vs_harness.py`, bit for bit).

## Base it applies to (pins, the g2fa4 list)
- `git archive 74d6e92c75 custom_io` (commit 74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6)
- `custom_io/models/b3g2.py` sha256 `a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce`
- `custom_io/train.py` sha256 `e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d`, replaced by `results/8a-g/pc-job-cards/g2fa4/overlay/train.py`
  (sha256 `e75e45fa43c6a6422c0a0e4222e05d8afc27580ec6551100680ed8f9ecdc5015`, checkpoint / resume) = the tree "src-b3g2ck"
- This pack then replaces `train.py` (adds `--speed-arms`) and `models/b3g2.py` (adds `plan_np`, `speed_defer`, `defer_stats`, the `_loss` switch), and adds `models/b3g2_defer.py` and
  `tests/test_b3g2_defer.py`. Overlay file sha256 (as printed by `make_port_tree.py`):
  `train.py` 7d382b15...a65585, `b3g2.py` 155d6dbb...a24444, `b3g2_defer.py` 363e5e16...480e92, `tests/test_b3g2_defer.py` 69947c88...b2b07 (the full values are printed on every build).

## Rules
- **Numerics-changing ('near').** Per-row maths is the same but floating-point rounding is not (batched GEMMs, longer padded call width, one-shot gradient reductions). The thinker is bit-identical.
- **Only fresh runs from update 0, under NEW run names.** Never resume a run into or out of a run with the arm. This is enforced: `--speed-arms` is in the config hash only when non-empty, so
  `--resume` refuses a change in either direction (T4c), and a flag-off hash is byte-identical to the g2fa4 train.py's, so old checkpoints still resume (T4b, T4f).
- **No change to 8aB3G2A4 / A8 or their tree.** `make_port_tree.py` never writes into an existing folder (it refuses a non-empty OUT_DIR and the names `src-b3g2` / `src-b3g2ck`).
- Flag off (`--speed-arms ''`, the default) is bitwise the original model code (T1) and the original train.py behaviour (T4e).

## Build and run
```
python make_port_tree.py OUT_DIR          # OUT_DIR must not exist or be empty; prints the sha256 of every overlay file and of the base files it replaced
export PYTHONPATH=OUT_DIR; cd OUT_DIR
python -m custom_io.train --model b3g2 ... --speed-arms defer --out RUN_NEW_NAME [--ckpt-every N --resume]
```
Tests (CPU, one thread; the first needs the base tree from `git archive 74d6e92c75 custom_io`, built by the test itself if BASE_TREE is unset; run from a git checkout that has the commit):
```
export OMP_NUM_THREADS=1
BASE_TREE=<base> G2FA4_TRAIN=<g2fa4 overlay/train.py> PYTHONPATH=OUT_DIR python OUT_DIR/custom_io/tests/test_b3g2_defer.py     # T1-T4, about 80 s  (DEFER_T4=0 skips the train.py subprocess tests)
BASE_TREE=<base> PORT_TREE=OUT_DIR python test_port_vs_harness.py                                                                  # port == harness, bitwise, about 30 s
PROF_PKG_ROOT=<base> python ../test_defer.py                                                                                       # the harness's own tests, unchanged, on the base tree
```
Rollback: drop `--speed-arms` **within the port tree** (flag off is bitwise the original). **Checkpoint caveat:** a checkpoint written by the port tree (flag on or off) carries `defer_stats`,
because train.py's `model_streams` stores every `*_stats` dict of the model. Restoring it into a tree whose `b3g2.py` lacks the port's changes (src-b3g2ck, the g2fa4 tree) dies loudly:
`AttributeError: 'B3G2' object has no attribute 'defer_stats'`, rc 1, before any training line and before the `resumed` event (test T4g). **Never move port-tree checkpoints to src-b3g2ck.**
Old g2fa4 checkpoints resume in the port tree fine (T4f).

## Spec correction (10-20, parent session)
The per-tensor fp32 bar "every gradient tensor rel L2 <= 1e-6" was the parent's over-tight spec and is replaced by `test_t2_float64_same_maths`. The registered fp32 bar (solve report 4.1) is the flat one:
loss rel <= 1e-6 and gradient cosine >= 0.999999. Evidence: in fp32 two tensors, `writer.ln_z.weight` / `.bias`, differ by 1.48e-6 / 2.12e-6 at K 32 (1.20e-6 / 1.64e-6 at gap_p 1 + ans_drill 1,
K 32; every other tensor <= 5.1e-7; flat 9.3e-8), because one LayerNorm backward sums them over all n*B pairs where the original sums per round (the original is within 1.4e-7 of the float64
truth on them, the deferred path within 1.5e-6 / 2.2e-6). In float64 the original and the deferred path agree to 1.2e-15 (K 4) / 3.5e-15 (K 32) in the first measurement, and to 1.4e-15 / 2.6e-15
in the committed test, on EVERY tensor, with loss rel 0.0: the same maths, so the fp32 difference is summation order only. The fp32 tests keep ln_z at 1e-5 and every other tensor at 1e-6
(comment in the test points to the float64 test). The deferred path is unchanged: the port stays bit-equal to the GPU-tested harness `defer.py` (`test_port_vs_harness.py`, below).

## Test results actually obtained (CPU, torch 2.11, one thread, 2026-10-20, final run)
`test_b3g2_defer.py`: **17 passed, 0 skipped, 0 failed (of 17)**, 86 s.
```
PASS T1 flag-off bitwise: loss, aux, 68 gradient tensors, RNG states (torch, gap, drill) and final state_dict BITWISE equal to the unmodified b3g2.py over 3 AdamW updates (gap_p .5, ans_drill .5)
PASS T2 deferred vs original (fp32), real ByteWriter.right   (12 scenarios: K 4 / 8..32 / drawn, 4 rows, gap_p 1, ans_drill 1, only call rows, only no-call rows, writer cap 7, label right)
PASS T2 deferred vs original (fp32), NON-TRIVIAL right       (the same 12; call_acc, eos_acc, right_last, stop_y, stop_acc all strictly between 0 and 1 somewhere; nll*10 edge margin 1.75e-04 >= 5e-5)
PASS T2 float64 same maths (loss rel <= 1e-12, EVERY tensor rel L2 <= 1e-12): K 4 worst 1.4e-15, K 32 2.6e-15, gap+drill K 32 2.6e-15, 4 rows K 16 7.0e-16, cap 7 1.3e-15, label right 1.5e-15; loss rel 0.0
PASS T2 mutation check (4 wrong deferred losses are caught by the marks)
PASS T3 fallbacks (eval, no_grad, talk_rounds 'all') bitwise the original, counted: defer_stats {'deferred': 0, 'fallback': 3}; training path {'deferred': 1, 'fallback': 3}
PASS attributes plain / state_dict unchanged; plan_np == plan; teacher_np == ByteWriter.teacher; schedule lists / answer pairs == the loop's host reads
PASS T4a speed arm on plain_tf exits with the message; T4b flag-off config hash == g2fa4's (1a1058f4d313cccf; with defer 88b98660c3c734af)
PASS T4c a change of speed arms refused at --resume both ways (rc 1); same flags resume
PASS T4d speed run killed after the step-4 checkpoint resumes from 4, trace == uninterrupted speed run, RESULT.json config.speed_arms 'defer', defer_stats {'deferred': 12, 'fallback': 0}; flag-off RESULT.json has no speed_arms / defer_stats
PASS T4e flag-off port train.py == g2fa4 train.py (train lines, start event, RESULT.json keys/config, config hash, final weights)
PASS T4f a g2fa4 checkpoint resumes in the port tree and finishes as the uninterrupted g2fa4 run
PASS T4g a port-tree checkpoint resumed in the g2fa4 tree fails loudly: rc 1, AttributeError: 'B3G2' object has no attribute 'defer_stats', no train line, no `resumed` event
```
fp32 T2 numbers (all scenarios, both rights): loss relative diff 0.0 (bitwise on this CPU); flat gradient rel L2 6.6e-08 .. 9.3e-08; gradient cosine (per tensor and overall) 1.0000000000; aux keys equal,
counts and `plan_*` exact; RNG states equal; per-tensor rel L2 <= 1e-6 for every tensor except `writer.ln_z.weight` / `.bias` (K 4: 7.8e-07; K 32: 2.1e-06, held to 1e-5).

`test_port_vs_harness.py`: **1 passed, 0 skipped, 0 failed (of 1)**, 27 s. 24 scenarios (12 real right, 12 non-trivial right): loss, every aux value, every gradient tensor and the RNG states BIT-EQUAL between the
harness `Defer` variant on the base tree and `speed_defer=True` on the port tree; 3 AdamW updates through `Trainer.update()` (losses 36.7156906, 99.8713531, 55.9968453) and the final 72 state_dict
tensors BIT-EQUAL; 12 / 12 deferred losses. (Mutation check: a 1e-7 scale in the port's answer accumulation makes it FAIL at `aux.ans`.)

`../test_defer.py` unchanged on the base tree (`PROF_PKG_ROOT=<base>`): **24 passed, 2 skipped (the DEFER_REAL_SHAPE ones), 0 failed (of 26)**, 74 s.

## Deviations from the spec, and open points
- fp32 per-tensor bar: the two `writer.ln_z` tensors are held to 1e-5, every other tensor to 1e-6 (see the spec correction); the float64 test carries the same-maths claim. Aux counts and ratios of counts are held exact, stricter than asked.
- `deferred_loss` reads the module constants (`KS`, `CKPT_FROM`, `settled`, `BOS`, `EOS`, `F`, `N_REG`) from the `custom_io.models.b3g2` module at call time, which are the same objects `defer.py` read from
  `__globals__` (and lets `caps.apply` / the tests' `KS` pinning take effect).
- The `writer.copy` fallback is tested for its counter only (B3G2 never has a copy writer; the original body is not run on one).
- T4 helper data and a "g2fa4 tree" are built by the test itself from the base tree plus the g2fa4 train.py (`G2FA4_TRAIN`, or found by walking up from the test file in the repo).
- Not tested: any CUDA run, bf16, GPU memory, a real-shape run, `--accum` other than 2 in T4, the free-run paths beyond T1's flag-off identity.
