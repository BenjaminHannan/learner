# defer port pack (B3G2 deferred batched writer)

**DRAFT. All code in this folder is a draft until the coordinator has code-reviewed it. Not for use before that.**

> **PARKED FOR GOOD 2026-10-21 (Ben's ruling via the coordinator: one last round, then park if not clean).**
> - Round 3's review (after 9dabf411f) found **no numeric bug**. `deferred_loss` matches `launch/defer.py` op for op, the 14 SRC_HASH values match, and the README's sha values match the files.
> - It is **not clean**. Nine findings, in order:
>   1. The source guard hashes methods on `type(m)` / `type(m.writer)`, so a method replaced on the model *instance* passes. prof_train's pad64 `m.tape_of`, exact_arms' `m.answer_teacher` and some tests do this.
>   2. A flag-on resume from a sidecar without `defer_counts` silently keeps 0.
>   3. The counter test's pair and width checks are true by construction.
>   4. `defer_stats` is copied once, before the final evals.
>   5. A dead `train_golds` call sits in that test.
>   6. `deferred` is counted before the sums, so they are wrong if the call raises.
>   7. The sidecar counts are not integrity-checked.
>   8. One dict mixes the headline counters and the sums.
>   9. A small inefficiency in the folder guard.
> - None affects flag-off (bitwise the original) or the flag-on numerics (bit-equal to the GPU-tested harness). Nothing here is changed further without a new ruling.

> **UNPARKED for round 3 (the last) by Ben's ruling via the coordinator, 2026-10-21.** The pack was parked 2026-10-20 under the 2-round review cap after round 2 (10 findings, no numeric finding);
> round 3 fixes the real findings below and nothing else (see "Round 3 (10-21)"). The round-2 triage, kept for the record:
> - Round 1 (10 findings) was fixed in 089b8c7bd.
> - Round 2 (10 findings) was **not clean**, so the pack was parked.
> - No round-2 finding is a numeric bug. Fixing them would not change the numbers: the port stays bit-equal to the GPU-tested `launch/defer.py`.
>
> The parent session's triage of round 2:
> - **Real (guard holes):**
>   - `B3G2.plan` is not in the source guard. The harness guarded it, and `_loss` still calls it.
>   - `think` and `tape_of` are hashed on `ToolH1` / `Tool`, not resolved on `type(m)`.
>   - The tests' g2fa4 reference `train.py` is not checked against its pin (e75e45fa…). A mistyped `G2FA4_TRAIN` silently falls back to the repo copy.
>   - The forbidden-folder check is case-sensitive, but the PC's NTFS is not.
> - **Real (reporting):**
>   - `defer_stats` in RESULT.json resets on every `--resume`. It could be kept in the flag-on sidecar without touching the flag-off checkpoint format.
>   - The harness's per-micro-batch pair and width statistics were dropped, though they describe the GPU memory caveat.
> - **Wording:**
>   - The comment "trace_loss / ST1 never come here" is wrong for ST1's ordinary half-batches, which call `model.loss`.
>   - "before anything is drawn" is wrong: `train_golds` draws first.
> - **Cleanup:**
>   - The applies-check is written twice (`train.py` and `B3G2.loss`).
>   - The pins and runner are copied into three files.
> - **Test gap:** the existing custom_io suite had not been run on the port tree. The parent ran it on 10-20; see "Existing custom_io tests on the port tree" below.

## What it is
An overlay pack that ports the speed change "defer" (`launch/defer.py`, the GPU-RUN-4 / GPU-RUN-5 variant) into the production trainer of the B3G2 arm as an opt-in flag. With
`--speed-arms defer`, `B3G2.loss` (the training entry point train.py and the harness Trainer call; teacher forcing, training, autograd on, `talk_rounds == 'last'`, no copy writer) runs `models/b3g2_defer.py`: one thinker-only loop, then one batched call pass
and one batched answer pass over all (round, row) pairs, with every host-side list taken from the numpy schedule (`B3G2.plan_np`). Anything else (eval, `no_grad`) runs `_loss` and is counted in `model.defer_counts['fallback']`. `_loss` itself is the BASE text (zero diff), so `trace_loss` and every other direct `_loss` caller run the original and count nothing. (ST1's ordinary half-batches call `model.loss`, so with the flag on they take the deferred path too.) train.py refuses `--speed-arms defer` at startup for a model that can never take the path (`talk_rounds != 'last'` or a copy writer). The first deferred call on a model checks a source guard (`SRC_HASH`: sha1[:12] of the sources of `loop`, `call_pass`, `ans_pass`, `answer_teacher`, `line_context`, `plan`, `plan_np`, `_loss`, `loss`, `ByteWriter.teacher/nll/right`, and `think` / `tape_of` as resolved on `type(m)`) and raises RuntimeError naming the method on a mismatch. The ops, their order and the dtypes are those of `defer.py` (checked by `test_port_vs_harness.py`, bit for bit).

## Base it applies to (pins, the g2fa4 list)
- `git archive 74d6e92c75 custom_io` (commit 74d6e92c75f3a0ed6b3f1e49e13fefc5ed5d29d6)
- `custom_io/models/b3g2.py` sha256 `a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce`
- `custom_io/train.py` sha256 `e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d`, replaced by `results/8a-g/pc-job-cards/g2fa4/overlay/train.py`
  (sha256 `e75e45fa43c6a6422c0a0e4222e05d8afc27580ec6551100680ed8f9ecdc5015`, checkpoint / resume) = the tree "src-b3g2ck"
- This pack then replaces `train.py` (adds `--speed-arms`) and `models/b3g2.py` (adds `plan_np`, `speed_defer`, `defer_counts`, the switch in `loss`; `_loss` untouched), and adds `models/b3g2_defer.py` and
  `tests/test_b3g2_defer.py`. Overlay file sha256 (as printed by `make_port_tree.py`):
  `train.py` a96328f2...c4102, `b3g2.py` 90e57766...b4c11, `b3g2_defer.py` f9b5167b...c53cd, `tests/test_b3g2_defer.py` c74588a8...867e2 (full values: printed on every build). `make_port_tree.py` also pins the g2fa4 train.py sha256 above and dies on a mismatch.

## Rules
- **Numerics-changing ('near').** Per-row maths is the same but floating-point rounding is not (batched GEMMs, longer padded call width, one-shot gradient reductions). The thinker is bit-identical.
- **Only fresh runs from update 0, under NEW run names.** Never resume a run into or out of a run with the arm. This is enforced: `--speed-arms` is in the config hash only when non-empty, so
  `--resume` refuses a change in either direction (T4c), and a flag-off hash is byte-identical to the g2fa4 train.py's, so old checkpoints still resume (T4b, T4f).
- **No change to 8aB3G2A4 / A8 or their tree.** `make_port_tree.py` never writes into an existing folder (it refuses a non-empty OUT_DIR, and any OUT_DIR whose resolved path has an ancestor, or itself, named `src-b3g2` / `src-b3g2ck`, compared case-insensitively).
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
BASE_TREE=<base> G2FA4_TRAIN=<g2fa4 overlay/train.py> PYTHONPATH=OUT_DIR python OUT_DIR/custom_io/tests/test_b3g2_defer.py     # about 100 s; first checks the trees (base pins, overlay sha256; PORT_OVERLAY=<port/overlay> when run from a built tree outside the repo) and stops on a mismatch.  A SKIP makes the run exit 1 unless ALLOW_SKIP=1 (DEFER_T4=0 skips the train.py subprocess tests)
BASE_TREE=<base> PORT_TREE=OUT_DIR python test_port_vs_harness.py                                                                  # port == harness, bitwise, about 30 s
PROF_PKG_ROOT=<base> python ../test_defer.py                                                                                       # the harness's own tests, unchanged, on the base tree
```
Rollback: drop `--speed-arms` within the port tree (flag off is bitwise the original).
**Checkpoint format:** the counters are `model.defer_counts`, not a `*_stats` dict, so train.py's `model_streams` (which stores every `*_stats` dict) does not capture them: a flag-off port-tree checkpoint has the g2fa4
format and resumes in the g2fa4 tree (src-b3g2ck code) bitwise as the uninterrupted g2fa4 run (T4g); a flag-on port checkpoint resumed there is refused by the config hash, no AttributeError (T4h). Old g2fa4
checkpoints resume in the port tree (T4f). A flag-ON run keeps its counts exact across `--resume`: they are saved in the flag-on checkpoint SIDECAR (`defer_counts`, never in the flag-off sidecar or in the `.pt`) and restored
on resume (T4d: 12 deferred losses after kill + resume, and every count and mean in `RESULT.json["defer_stats"]` equals the uninterrupted run's). A flag-on checkpoint still must only be resumed in the port tree with `--speed-arms defer`.

## Spec correction (10-20, parent session)
The per-tensor fp32 bar "every gradient tensor rel L2 <= 1e-6" was the parent's over-tight spec and is replaced by `test_t2_float64_same_maths`. The registered fp32 bar (solve report 4.1) is the flat one:
loss rel <= 1e-6 and gradient cosine >= 0.999999. Evidence: in fp32 two tensors, `writer.ln_z.weight` / `.bias`, differ by 1.48e-6 / 2.12e-6 at K 32 (1.20e-6 / 1.64e-6 at gap_p 1 + ans_drill 1,
K 32; every other tensor <= 5.1e-7; flat 9.3e-8), because one LayerNorm backward sums them over all n*B pairs where the original sums per round (the original is within 1.4e-7 of the float64
truth on them, the deferred path within 1.5e-6 / 2.2e-6). In float64 the original and the deferred path agree to 1.2e-15 (K 4) / 3.5e-15 (K 32) in the first measurement, and to 1.4e-15 / 2.6e-15
in the committed test, on EVERY tensor, with loss rel 0.0: the same maths, so the fp32 difference is summation order only. The fp32 tests keep ln_z at 1e-5 and every other tensor at 1e-6
(comment in the test points to the float64 test). The deferred path is unchanged: the port stays bit-equal to the GPU-tested harness `defer.py` (`test_port_vs_harness.py`, below).

## Round 3 (10-21): the last round, fixes only
Ben's ruling via the coordinator. Nothing in `deferred_loss`'s tensor ops changed; the port is still bit-equal to the harness (`test_port_vs_harness.py`).
- **(a) `plan` is in the source guard** (`SRC_HASH['plan']`, the port's `plan` text; `_loss` still calls it).
- **(b) `think` and `tape_of` are hashed as resolved on `type(m)`**, not on `ToolH1` / `Tool`; all `B3G2.*` methods and the writer's are labelled by the real class name. Tests: patching a method still raises (now naming `B3G2.think` / `B3G2.tape_of`), and a subclass that overrides `think` or `tape_of` raises naming `SubB3G2.<method>`.
- **(c) `test_000` checks the g2fa4 reference `train.py` against its pin** (e75e45fa...) and FAILs on a mismatch. `G2FA4_TRAIN` set to a path that does not exist FAILs loudly instead of walking up to another copy (checked by hand with a missing file and with an edited copy).
- **(d) `make_port_tree.py` compares the forbidden names case-insensitively** (`part.lower()`); `test_make_port_tree_refuses_src_b3g2_folders_in_any_case` (in `test_port_vs_harness.py`) tries `SRC-B3G2CK/x`, `src-b3g2ck/x`, `Src-B3g2/x`, `src-b3g2` and the folders themselves: refused, nothing created.
- **(e) `defer_counts` stay exact across `--resume`**: saved in the flag-ON sidecar only (`defer_counts` key), restored on resume. The flag-off sidecar and the `.pt` are unchanged (T4g still passes bitwise in the g2fa4 tree; it now also asserts the flag-off sidecar has no `defer_counts`). T4d: 12 deferred after kill + resume, and the whole `defer_stats` dict equals the uninterrupted run's.
- **(f) The harness's per-micro-batch counters are back** in `defer_counts` (call / EOS-only / answer pairs, sum and max call width, rounds, rows): Python ints from numpy sizes, no device read. `RESULT.json["defer_stats"]` is `b3g2_defer.stats(model)`, the same keys and means as `defer.py`'s `Defer.stats()` (`deferred_losses`, `fallback_losses`, `call_pairs_per_micro_batch`, `eos_only_pairs_per_micro_batch`, `answer_pairs_per_micro_batch`, `mean_call_width`, `max_call_width`, `mean_rounds`, `mean_rows_per_micro_batch`, `numerics`). `test_port_vs_harness.py` compares them to the harness's, scenario by scenario and after 3 updates.
- **(g) Two wrong comments fixed**: ST1's ordinary half-batches DO call `model.loss`, so with the flag on they take the deferred path (only `trace_loss` calls `_loss` directly); `train_golds` draws (drill rng) BEFORE the source guard runs.
- **(h) `b3g2_defer.applies_statically(m)`** (`talk_rounds == 'last'` and no copy writer) is used by both `train.py` (startup refusal) and `B3G2.loss`. The duplicated pins and runners are left as they are.

## Test results actually obtained (CPU, torch 2.11, one thread, 2026-10-21, round 3, fresh tree)
`test_b3g2_defer.py` (BASE_TREE, G2FA4_TRAIN, PORT_OVERLAY set): **25 passed, 0 skipped, 0 failed (of 25)**, 111 s.
```
PASS test_000 the trees under test are the pinned ones (base b3g2.py / train.py == 74d6e92c75 pins; the g2fa4 reference train.py == its pin; the port tree's overlay files == port/overlay sha256)
PASS T1 flag-off bitwise: loss, aux, 68 gradient tensors, RNG states (torch, gap, drill) and final state_dict BITWISE equal to the unmodified b3g2.py over 3 AdamW updates (gap_p .5, ans_drill .5)
PASS T2 deferred vs original (fp32), real ByteWriter.right   (12 scenarios: K 4 / 8..32 / drawn, 4 rows, gap_p 1, ans_drill 1, only call rows, only no-call rows, writer cap 7, label right)
PASS T2 deferred vs original (fp32), NON-TRIVIAL right       (the same 12; call_acc, eos_acc, right_last, stop_y, stop_acc all strictly between 0 and 1 somewhere; nll*10 edge margin >= 5e-5)
PASS T2 float64 same maths (loss rel <= 1e-12, EVERY tensor rel L2 <= 1e-12): worst 1.4e-15 (K 4), 2.6e-15 (K 32), 2.6e-15 (gap+drill K 32); loss rel 0.0
PASS T2 mutation check (4 wrong deferred losses are caught by the marks)
PASS T3 fallbacks (eval, no_grad, talk_rounds 'all') bitwise the original, counted: deferred 0 / fallback 3; training path deferred 1 / fallback 3
PASS source guard: shipped hashes match the port tree (14 methods, resolved on type(m)); a changed B3G2.call_pass / _loss / plan / plan_np / think / tape_of or ByteWriter.nll -> RuntimeError naming it
PASS source guard: a SubB3G2 override of think or tape_of -> RuntimeError naming SubB3G2.<method>
PASS defer counters are Python ints and consistent with the batch (rounds, rows, pairs, widths); stats() gives the means
PASS trace_loss with speed_defer True: bitwise the original, defer_counts untouched
PASS attributes plain / state_dict unchanged; plan_np == plan; teacher_np == ByteWriter.teacher; schedule lists / answer pairs == the loop's host reads
PASS T4a speed arm on plain_tf exits with the message; T4b flag-off config hash == g2fa4's (1a1058f4d313cccf; with defer 88b98660c3c734af)
PASS T4c a change of speed arms refused at --resume both ways (rc 1); same flags resume
PASS T4d speed run killed after the step-4 checkpoint resumes from 4, trace == uninterrupted speed run, RESULT.json config.speed_arms 'defer', defer_stats == the uninterrupted run's (12 deferred, counts and means); flag-off RESULT.json has no speed_arms / defer_stats
PASS T4e flag-off port train.py == g2fa4 train.py (train lines, start event, RESULT.json keys/config, config hash, final weights)
PASS T4f a g2fa4 checkpoint resumes in the port tree and finishes as the uninterrupted g2fa4 run
PASS T4g a flag-off port-tree checkpoint (sidecar without defer_counts) resumes in the g2fa4 tree and finishes bitwise as the uninterrupted g2fa4 run
PASS T4h a flag-on port-tree checkpoint resumed in the g2fa4 tree is refused by the config hash (rc 1), no AttributeError, no training line
PASS T4i --speed-arms defer with cfg talk_rounds 'all' exits at startup (rc 1) saying why; the same model without the flag trains
```
Negative checks of the runners (by hand): an edited port file or base train.py, a missing or edited g2fa4 reference file makes test_000 FAIL and nothing else runs; `DEFER_T4=0` or a missing reference overlay makes the run exit 1 and print the skip reasons.
fp32 T2 numbers (all scenarios, both rights): loss relative diff 0.0 (bitwise on this CPU); flat gradient rel L2 6.6e-08 .. 9.3e-08; gradient cosine (per tensor and overall) 1.0000000000; aux keys equal,
counts and `plan_*` exact; RNG states equal; per-tensor rel L2 <= 1e-6 for every tensor except `writer.ln_z.weight` / `.bias` (K 4: 7.8e-07; K 32: 2.1e-06, held to 1e-5; see the spec correction).

`test_port_vs_harness.py`: **3 passed, 0 skipped, 0 failed (of 3)**, 28 s (test_000 trees; make_port_tree case-insensitive refusal; the comparison). 24 scenarios (12 real right, 12 non-trivial right): loss, every aux value, every gradient
tensor and the RNG states BIT-EQUAL between the harness `Defer` variant on the base tree and `speed_defer=True` on the port tree, and the per-micro-batch counters equal the harness `Defer.stats`; 3 AdamW updates through
`Trainer.update()` (losses 36.7156906, 99.8713531, 55.9968453), the final 72 state_dict tensors and the counters after the 3 updates BIT-EQUAL; 12 / 12 deferred losses.

`../test_defer.py` unchanged on the base tree (`PROF_PKG_ROOT=<base>`): **24 passed, 2 skipped (the DEFER_REAL_SHAPE ones, which are not run here by design), 0 failed (of 26)**, 69 s.

Existing custom_io suites re-run on the round-3 port tree (my run, `python tests/<file>.py`, CPU): test_b3g2, test_b3g2_run, test_talk_rounds, test_st1: ALL OK.

## Possible later change (numerics-changing; would need its own run)
The per-round `lcall = lcall + ...` and `acc.index_add` loops in `deferred_loss` stay as they are: they keep the original's summation order and the bit-equality with the GPU-tested code. Replacing them by
single reductions would change the numerics again and would need its own run and its own tests.

## Deviations from the spec, and open points
- fp32 per-tensor bar: the two `writer.ln_z` tensors are held to 1e-5, every other tensor to 1e-6 (see the spec correction); the float64 test carries the same-maths claim. Aux counts and ratios of counts are held exact, stricter than asked.
- The dispatch is in `B3G2.loss` (not `_loss`), reviewed 10-20: the golds are drawn first (same drill draws), `_loss` is the base text.
- `deferred_loss` reads the module constants (`KS`, `CKPT_FROM`, `settled`, `BOS`, `EOS`, `F`, `N_REG`) from the `custom_io.models.b3g2` module at call time, which are the same objects `defer.py` read from
  `__globals__` (and lets `caps.apply` / the tests' `KS` pinning take effect).
- The `writer.copy` fallback is tested for its counter only (B3G2 never has a copy writer; the original body is not run on one).
- T4 helper data and a "g2fa4 tree" are built by the test itself from the base tree plus the g2fa4 train.py (`G2FA4_TRAIN`, or found by walking up from the test file in the repo).
- Not tested: any CUDA run, bf16, GPU memory, a real-shape run, `--accum` other than 2 in T4, the free-run paths beyond T1's flag-off identity.

## Existing custom_io tests on the port tree (parent session, 10-20)

Run directly (`python tests/<file>.py`) on the base tree (`git archive 74d6e92c75 custom_io`) and on the port tree built by `make_port_tree.py`, CPU:

| suite | base | port |
|---|---|---|
| test_b3g2 | ALL OK | ALL OK |
| test_b3g2_run | ALL OK | ALL OK |
| test_talk_rounds | ALL OK | ALL OK |
| test_reader_rule | ALL OK | ALL OK |
| test_no_plug | ALL OK | ALL OK |
| test_st1 | ALL OK | ALL OK |
| test_writer | stopped at the 30-min limit during its base-tree training run (step 4000, dev exact 0.970) | not run |

Not run: the rest of the custom_io suite (`writer.py` and the files the port does not touch are byte-identical to the base).
