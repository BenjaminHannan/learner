# Two candidate-exact arms, measured on the CPU (2026-10-16)

Code: custom_io at 74d6e92c75 (the code of GPU-RUN-3 and of the PC run 8aB3G2A4), read-only at `/home/user/src-g2f`. Nothing in custom_io or in `prof/` was edited. New files, all in this folder:
`exact_arms.py` (the two arms, `NEW_VARIANTS = [KvCat, FastTeach]`, picked up by `prof_launch.py`), `test_exact_arms.py` (28 tests), `test_exact_arms.log` (their output), `exact_arms_counts.json` (every number below; the tests write it only when `EXACT_ARMS_WRITE=1`, otherwise to a scratch file). Revised after an independent review (see "What changed after the review" at the end).

Labels: **shown** = I ran it here (CPU, fp32 unless said, torch 2.11.0+cpu, stub Gemma, synthetic rows). **suggested** = reasoning or arithmetic from the GPU-RUN-3 record, not run. **untested** = no CUDA existed here.

## In plain words (for Ben)

Two small speed-ups that should not change a single number the model computes.

1. `kvcat`: every round, each of the two thinker blocks glues two big tables together (the tape's keys/values and the prompt's keys/values). In a teacher-forced micro-batch the two tables are the same every round, so the glued table is the same every round. The arm glues once and reuses it. Shown on the CPU at one thread: the same losses and the same gradients, bit for bit (compared as raw bit patterns). At two or more CPU threads even the unmodified code does not repeat itself bit for bit, so there the claim is only "as close as the original is to itself". It also saved about a third of the memory the forward pass keeps alive (CPU, fp32).
2. `fastteach`: before the writer is asked for a line, a helper builds the answer's target tensors with a slow loop (one tiny operation per byte, per row), reads two things back from the GPU, and copies four tensors over with waits. For the G2f writer the result of all that is provably all zeros where it matters, so the arm builds the same four tensors with numpy and copies them without waiting. Shown: the four tensors are identical for thousands of random target lists, and the training result is bit-identical (at one CPU thread).

Neither arm can make the GPU kernels themselves much faster. The record says the GPU is idle 37 to 60 % of the time because the CPU is slow to launch 70,600 small kernels per update. `kvcat` removes about 1 to 2 % of the launches and some GPU work (small, suggested). `fastteach` removes CPU work in Python (the loop), which is what a launch-bound run actually waits on, but its waits are not the lever (`nosync` already removed those and did nothing). The big "ops removed" count you will see below is mostly that Python loop on CPU tensors, not GPU launches. My honest expectation for both together is small: somewhere between nothing and a few percent (suggested, untested on CUDA).

## One correction to the numbers I was given

The task text says CatArrayBatchedCopy is "1,902 launches and 213 ms per update". In `gpu-run-3-box1/b3g2_profile.profiler.md` those two figures are in the "total ms" and "count" columns of the top-kernel table, and that table is summed over the 2 profiled updates (its `ProfilerStep*` row has count 2 and total 6,972 ms = 2 x 3,486 ms, and the top 25 kernels together would otherwise be more than the 1,415 ms real kernel time per update). Per update that is **951 launches and about 107 ms** (4.8 % of the 2.24 s unprofiled wall, 7.6 % of the 1,415 ms kernel time). The CPU count agrees: the model issues 206 `aten::cat` per micro-batch at 16 rounds (143 forward + 63 backward), which is 824 per update, against 951 per update on the GPU at 17.28 rounds (shown for the CPU count; arithmetic for the comparison). Everything below uses the per-update figure.

## kvcat

**What it changes.** `ledger.CBlock.forward` starts with `k, v = torch.cat([kvs[0], kvx[0]], 2), torch.cat([kvs[1], kvx[1]], 2)` every round and in every block. The arm rebuilds `CBlock.forward` from its own source with that one line replaced (prof_train's `patched_fn`; the source hash is checked, another source is a Skip) and keeps one cached (k, v) per block.

- Key: the identity of the two parent tensors `kvs` and `kvx` (`[2, B, heads, keys, dk]`, what `Tool.think` hands each block), their `_version` counters, and (grad enabled, autocast flags). Strong references to the last key only. **Deviation from the brief:** it said to key on `kvs[0], kvs[1], kvx[0], kvx[1]`; indexing a tensor makes a new view object each time (shown: the ids differ on every call), so those can never match. The parents are the stable objects.
- Free run: after a call the tape K/V is rebuilt (new tensors), the key no longer matches, the cat is rebuilt. What proves it is not served stale is the **equality** of the whole free run (Z, tape, calls, records, answers) with the stand-in writer that writes calls (shown; a mutant whose key is the block only fails that test). The miss count is only a sanity check: the same free run with a writer that writes no call misses strictly fewer times than the run with calls (`test_5`); each entry point clears the cache when it starts, so a miss count on its own proves nothing.
- Scope: `loss`, `run`, `talk`, `loop`, `trace_loss` on the model are wrapped; the cache is emptied when each starts and when it returns or raises (shown for all five paths and for an injected exception). `loop` is wrapped too because `call_evals` calls it directly. Teardown empties it.
- Applicability: the arm installs only on the model class `B3G2` (a Skip, with the reason, on anything else: B3, Tool, ToolH1 and PTS arms have the same `cat` pattern but nothing here shows the arm exact there; shown: a PTS arm gets the Skip).
- Inside backward (`torch._C._current_graph_task_id() != -1`, which is where ToolH1's non-reentrant checkpoint recomputes rounds t >= n_loops) the cache is neither read nor written: the recompute makes its own plain cat, as the original does. Shown: at K = 32 the tiny model has 80 such calls per 4 micro-batches, no cache entry survives the backward, and the gradients are equal.

**Exactness (shown, CPU, 1 thread).** All "equal" below means the **raw bit patterns** are equal (float tensors compared through an integer view, so -0.0 and +0.0 count as different and NaN payloads too; `torch.equal` would call -0.0 and +0.0 equal), arm against the unmodified code, same seed and batches, `torch.set_num_threads(1)`. Re-run with the bitwise comparison after the review: everything below still holds.

| check | result |
|---|---|
| (1) loss tensors and every aux entry, 4 micro-batches | equal |
| (2) all 72 parameter gradients after the 4 backward passes | equal (also a second batch/seed pair) |
| (3) 3 full updates (split, micro-batch loss, backward, clip_grad_norm_, AdamW fused=False), all parameters | equal; the weights really moved (>10 tensors differ from init) |
| (4) K forced to 32 (rounds 12..31 checkpointed) and to 4 | equal, losses, gradients and 3-update parameters |
| (5) free run: `run` (learned stop), `run(loops=6)` (settles), `talk`, `generate`, a direct `loop`, eval mode, no_grad, with a stand-in writer that writes calls so the tape K/V is rebuilt | equal (Z, tape, calls, records, answers) |
| (6) teardown | every attribute of the model, its blocks and the writer is identical (`is`) to before setup; class methods untouched |
| real shape, ONE micro-batch of 64 rows, K = 16, 4,023,302 params | loss equal and all 98 gradients equal |
| **2 CPU threads**, real shape, one 64-row micro-batch, K = 16 (`test_7b`, recorded not asserted) | the unmodified code is **not** repeatable against itself: baseline vs baseline differs in 1 of 98 gradients (max abs 1.2e-7; the reviewer saw this as `reader.tok.weight`, 170 elements); kvcat vs baseline: 1 of 98, max abs 2.4e-7; fastteach vs baseline: 1 of 98, max abs 2.4e-7; losses bit-equal in all. So at 2+ threads no arm can be bit-identical, and with one repeat of the baseline I cannot say whether 2.4e-7 against 1.2e-7 is more than noise |
| bf16 autocast on the CPU (`torch.autocast('cpu', dtype=torch.bfloat16)`), K = model draw and 32 | loss equal and all 72 gradients equal (max abs diff 0.0); 3 full updates also equal. The parameters and gradients are fp32 under CPU autocast; the K/V come out of the Linear in bf16 and are accumulated in bf16 on both sides. |

The backward claim held (at 1 thread): the 17 per-round gradient slices are summed into the cached cat's gradient in the same (reverse-round) order and split once; each element gets the same additions in the same order, and select_backward's zero padding adds exactly. No near-miss to explain, so the arm stays `ab_cpu_rule = 'bit_exact'` and is **not** labelled 'near'.

**The checkpoint path is NOT covered by `abequiv` (important for the box).** `abequiv` pins K to K0 = max(8, longest gold program + 2) (`prof_train.py` `pin_stochastic`, `rounds_needed`). On the real model `n_loops` is 12 and the thinker checkpoints only rounds t >= 12, so unless one of the 256 rows has a program of 11 or more calls, `abequiv` never runs a checkpointed round and never reaches kvcat's bypass branch (`_current_graph_task_id()` read during the recompute, on the autograd engine's thread) -- which is exactly the part that changes on CUDA. (The reviewer ran `abequiv` on the CPU tiny shape: K0 = 8, both arms passed with zero checkpointed rounds; I did not re-run that. The real pool's longest program is not known here.) So the box needs the separate check below (`--box-ckpt`).

**What could differ on CUDA (untested).**
- The forward is a plain copy and every round's SDPA receives a contiguous tensor of the same shape, strides and dtype as before, so the kernel the dispatcher picks (flash / memory-efficient / cuDNN, which depend on shape, mask, alignment and contiguity) should be the same. This is an argument, not a measurement.
- The backward adds grads in the same order but with different tensor shapes and views: the original accumulates narrowed, zero-padded 5-D tensors, the arm accumulates full `[B, heads, keys, dk]` grads in the cat's buffer. Elementwise adds have no atomics, so bit-equality is expected; the memory-efficient attention backward (`fmha_cutlassB`) may itself be non-deterministic run to run, in which case baseline-against-baseline already differs. **On the box, first measure baseline against baseline on the same micro-batch; the pass bar for the arm is "no larger than that".**
- bf16 on CUDA: same accumulation dtype on both sides, equal on the CPU; not tested on CUDA.
- `torch.compile` (the `compile` variants) would graph-break on the Python-side cache: untested, do not combine.

**Op counts (shown, ATen dispatches, forward + backward, one micro-batch, K = 16).**

| | tiny, 4 rows | real 3M, 64 rows |
|---|---|---|
| baseline non-view ATen ops | 7,805 | 18,798 |
| kvcat | 7,685 (-120) | 18,558 (-240, -1.3 %) |
| `aten::cat` fwd + bwd, baseline -> kvcat | 166 -> 136 | 206 -> 146 |
| per cache hit, removed | 2 `cat`, 4 `select_backward`, 2 `add` | same (hits 30, misses 2, bypassed in backward 8) |
| host-sync call sites executed | 207 -> 207 (none touched) | 207 -> 207 |

**Memory (shown on the CPU, fp32, real 3M shape, 64 rows, prompts of 300 letters, K = 16).** Resident memory held by the forward pass's autograd graph (fresh process, difference of VmRSS before and after `model.loss`): baseline 3,275,048 kB, kvcat 2,218,816 kB, **-1.06 GB (-32 %)**. The baseline keeps one k and one v per saved round and block; the arm keeps one pair per block. On the GPU this is bf16, the real prompt widths and the allocator, so the saving there is untested; it is in the direction of the 8.33 GB peak at accum 4. (Incidental: the same shape with 1,926-letter prompts, the synthetic default, was killed by the box's 16 GB memory limit at 12.3 GB resident for the baseline, so the CPU real-shape tests use 300 letters; op and sync counts do not depend on the width.)

**Honest expected effect on the GPU (suggested).**
- Launches: per update at 17.28 rounds the arm gets about 2 blocks x 16.3 x 4 = 130 cache hits (counting a hit per non-checkpointed round), each removing 2 `cat`, 4 `select_backward` (a zero fill plus a copy each, I believe: 2 kernels) and 2 `add`: about 1,040 ATen ops, up to about 1,560 kernels, i.e. 1.4 to 2.1 % of the 75,966 kernels per update. In a launch-bound run that is the CPU-side gain: at most about 1 to 2 %, near the 2 % noise floor of the record.
- GPU time: of the 951 cat launches per update, about 260 (27 %) are this site's, and they are the large ones (prompt-sized K/V), so most of the 107 ms per update may be theirs; the backward also stops writing and re-adding zero-padded 5-D grads for the same tensors (the kernel table has 142 ms/update of bf16 `add`, 43 ms of bf16 fill, 77 ms of copy that this site feeds into; its share is unknown). This is GPU time, not launches. It shortens the wall only if the GPU is the bottleneck, and the record says it is busy only 40 to 63 % of the time. So: a smaller GPU kernel total (tens of ms per update), a wall gain of perhaps 0 to 3 %, and lower activation memory. Only a GPU profile with the arm on can say more (`--variant kvcat --sections profiler`).

## fastteach

**What it changes.** `B3G2.answer_teacher(Z, ids)` is `ByteWriter.teacher(ids, cids, cmask, WCAP, BOS, EOS)` over `line_context(Z)`: cids zeros `[B, 1]`, cmask all False, made on the device. `teacher` reads both back with `.cpu()` (2 syncs on CUDA), runs a Python loop over rows and target bytes (select, eq, and, any; it can never hit), then copies inp, tgt, fb, over with four blocking `.to(dev)`. With `writer.copy` False (G2f) the writer ignores fb. The arm replaces `answer_teacher` on the model instance, only when `writer.copy` is False (else Skip; source hashes of `answer_teacher`, `line_context` and `ByteWriter.teacher` are checked): `teacher_np` builds inp, tgt, over with numpy (no loop over bytes), the three go to the device through prof_train's `to_device_async` (pinned + non_blocking on CUDA, plain `.to` on the CPU), and fb is `torch.zeros(B, L, 1, device=dev)`, a device fill with no host copy. No device read. It also no longer calls `line_context`, so its three device zeros (Xc `[B,1,d]`, cmask, cids) are not made either.

**Exactness (shown).**

| check | result |
|---|---|
| `teacher_np` vs the real `ByteWriter.teacher`, 1,800 random target lists (caps 1, 2, 3, 9, 69, 70; None, [], 1..cap-2 long, len+1 = cap, over-cap len+1 = cap+1, much longer; ids 0..299) plus hand corners (all None, tuples, numpy arrays) | inp, tgt, fb, over: `torch.equal`, same dtype, shape and strides, every case |
| premise: the original's fb is all zero and `[B, L, 1]` for line_context, any target list | true (50 random lists) |
| the installed variant vs the original method, 200 random calls | same four tensors, same dtype, shape, strides, device |
| (1)(2)(3)(4)(5)(6) as for kvcat (losses, aux, 72 gradients, 3 updates, K = 32 and 4, free run, teardown) | all bit-equal at 1 thread; real shape, 64 rows: loss equal and all 98 gradients equal; bf16 CPU autocast equal |
| fastteach + kvcat, and nosync + fastteach + kvcat together | equal |

On CUDA the four tensors have the same values, dtypes and contiguity, so nothing downstream can see a difference by construction; what is untested is only that the pinned, non-blocking copies behave (they are the ones `nosync` already uses).

**Op, sync and host-time counts (shown).** Sync counts are call sites executed per micro-batch (`.cpu`, `.tolist`, `.item`, `.nonzero`, `.to(device)` blocking, `torch.tensor(..., device=)`); on the CPU none waits, each is a place that would on a CUDA tensor. Python's `bool()` of a tensor is counted separately (most are on CPU tensors: 1,082 of the baseline's 1,116 are the loop's `if hit.any()`).

| one micro-batch, K = 16 (16 teacher calls) | tiny, 4 rows | real 3M, 64 rows |
|---|---|---|
| non-view ATen ops, baseline -> fastteach | 7,805 -> 7,101 | 18,798 -> 8,472 (-10,326, -54.9 %) |
| of which dispatched INSIDE `ByteWriter.teacher` (host tensors: the per-byte loop, `torch.full`, `torch.tensor`; counted by wrapping `teacher` during the forward), baseline -> fastteach | 672 -> 0 | 10,294 -> 0 |
| the rest of the removed ops (outside `teacher`: line_context's 3 zeros per call replaced by the 1 fb fill) | -32 (= 2 x 16 calls) | -32 |
| biggest removals (real) | | `copy_` -4,034, `eq` -2,024, `any`/`_local_scalar_dense`/`bitwise_and` -1,082 each, `bitwise_and_` -942, `zeros` -48, `full` -32 |

Read the rows above as **CPU-tensor ops versus would-be CUDA launches**: 10,294 of the 10,326 removed dispatches (99.7 %) are inside `teacher`, which builds and loops over HOST tensors; on CUDA they are Python/CPU time, not kernel launches (code reading plus the count above). The device-visible change per call is only: 3 zero fills -> 1 fill (-2), 4 blocking host-to-device copies -> 3 pinned non-blocking (-1 copy), 2 device-to-host `.cpu()` -> 0 (-2). Per micro-batch at 16 calls: about -32 fill launches, -16 H2D copies, -32 D2H copies; the table does not mix the two kinds any more.

| `.cpu()` calls (writer.py:121) | 32 -> 0 | 32 -> 0 |
| blocking `.to(dev)` calls (writer.py:138) | 64 -> 0 | 64 -> 0 |
| pinned non_blocking copies | 0 -> 48 (3 per call) | 0 -> 48 |
| host-sync call sites executed, all | 207 -> 111 | 207 -> 111 |
| host seconds inside `answer_teacher` during one forward (lower bound for fastteach, see below) | 3.1 -> 2.0 ms | 27.3 -> 5.0 ms |
| one call at 64 rows, golds of the real-shape model: answers / first calls / stop lines (fastteach figures are a lower bound) | | 4.6 / 6.5 / 0.43 ms -> 0.048 / 0.062 / 0.022 ms |

That is exactly the 6 syncs per call the brief predicted (2 `.cpu()` + 4 blocking copies), 96 per micro-batch at 16 rounds. The remaining sites (`tolist` b3g2.py:350/361, `nonzero` :374/:553, `torch.tensor(device=)` :355/:536, `.to` at b3g2.py:224/:567 and tool.py:175/180) are untouched. The host-time numbers are this sandbox's CPU and synthetic gold targets (the loop's cost is proportional to the target bytes); `nosync`, which also moves the context to the CPU, costs the same as the baseline on the CPU (5.0 / 7.8 / 0.43 ms), because on the CPU only the loop is visible. **The fastteach host times are a lower bound for the box:** on the CPU `prof_train.to_device_async` is a plain `.to`, so the pinned staging, the 3 `cudaMemcpyAsync` calls and the 1 fill launch per call that fastteach adds on CUDA are not in them; the savings quoted below are therefore upper bounds (untested on CUDA). (These timings were re-measured in the review re-run, on a busy shared box, best of 5 / best of 3 for the in-forward figures; they differ from the first run's and are noisy.)

**Honest expected effect on the GPU (suggested, untested).**
- GPU time: none to speak of. The model kernels are the same. Per call: 3 line_context zero fills become 1 fb fill (about -2 fill launches, so roughly -138 launches per update at 4 x 17.28 calls, 0.2 % of 75,966), 4 blocking host-to-device copies become 3 pinned non-blocking ones, and 2 device-to-host copies disappear. The 10,000-odd ATen ops it removes on the CPU run are host-tensor ops (see above), not launches.
- Syncs: per update about 4 x 17.28 = 69 calls, so about 138 device-to-host copies (of 745 per update) and 276 blocking host-to-device copies (I believe each is one `cudaStreamSynchronize`) removed, about 414 of 1,305 stream syncs. But `nosync` removed this same set (and more) on three boxes and measured -0.1 % and +1.2 %, inside the noise, so these waits are not the lever.
- Host CPU time: the part `nosync` left in. Measured here, 22.3 ms per micro-batch forward (27.3 -> 5.0 ms, best of 3, fastteach figure a lower bound, see above), about 89 ms per update; if the box's CPU were as fast as this one and the real pool's targets as long as the synthetic ones, that is **up to** about 4 % of the 2.24 s wall in a launch-bound run (an upper bound: the CUDA-side cost fastteach adds is not in the CPU measurement). Both "if"s are untested. Expect 0 to 4 %.

## Tests

`python test_exact_arms.py` runs the 23 tiny-shape tests (about 90 s at 1 thread) and skips the 5 real-shape ones; `EXACT_ARMS_REAL=1 python test_exact_arms.py` runs all 28 (about 220 s at 1 thread on this shared box; the real-shape tests alone are about 2.5 minutes). The runner now prints passed / skipped / failed / selected counts. Last full run (`test_exact_arms.log`): see the last line there; the figures in this report come from the run with `EXACT_ARMS_REAL=1 EXACT_ARMS_WRITE=1`. Also checked: the arms register through `prof_launch.register` (names, `ab_cpu_rule = 'bit_exact'`, order after `nosync`, `parse_variants('fastteach,kvcat,nosync')` puts nosync first); a plain arm (PTS) gives a Skip for both; a writer with a copy path gives a Skip for fastteach; a changed `CBlock.forward` source gives a Skip for kvcat; the cache cannot go stale (an in-place write to kvs, another grad mode, a clone with equal values all miss). Mutants checked by hand in the review re-run (not kept as tests): a cache keyed on the block only is caught by `test_5` (free run differs); a cache that never hits is caught by `test_1_2` (asserts hits > 0 for every kvcat arm).

Added after the review: the comparison is by bit pattern (`test_same_is_bitwise_signed_zero_and_nan_payload`); `test_1_2` and the real-shape test assert cache hits > 0 for every kvcat arm and, at the real shape (2 blocks, K = 16, rounds 12..15 checkpointed), bypass in backward > 0; `test_5` compares misses with and without written calls; `test_7b` records the 2-thread behaviour; `box_ckpt_check` (below) and a tiny-CPU test of it.

## The check for the CUDA box (not done here: no GPU)

`abequiv` does not reach the checkpoint path (see above), so run this in addition. It forces K = 32 (as `test_4` does) so that rounds 12..31 are checkpointed, under bf16 autocast on the arguments' device, on the first 2 micro-batches, with 5 runs: baseline x3, kvcat, fastteach:

```
python test_exact_arms.py --box-ckpt --arm B3G2 --rung 3M --accum 4 --batch 256 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json --device cuda
```

It prints `BOX_CKPT_JSON {...}` and `BOX CKPT CHECK: PASS|FAIL`. Bar (fixed here, before any CUDA number): N = gradient indices that differ in any pair of the three baselines, M = their largest absolute difference; each arm passes if its differing gradients are all in N, its largest difference is <= 4 M, and its loss is bit-equal whenever the baseline's is; and kvcat's `cat_cache_bypassed_in_backward` > 0 and `cat_cache_hits` > 0 (else the checkpoint path did not run and nothing was checked). A baseline that repeats bitwise therefore forces bitwise-equal arms. The factor 4 is a judgement. **Shown here:** the function runs end to end on the CPU tiny shape (bf16 CPU autocast, K = 32): bypass 40, hits 62, baseline repeats bitwise, both arms bitwise equal, PASS. **Untested:** everything on CUDA.

Then, as before: `python prof_launch.py --arm B3G2 --rung 3M --accum 4 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json --sections abequiv --ab-variants kvcat,fastteach` for the bf16 mark-6 bar on the normal K0 (this covers everything except the checkpoint path), then `--sections profiler,syncs --variant kvcat` and `--variant fastteach` to read launches, cat/fill/add kernel totals and sync counts.

## Limits

CPU, fp32 (and CPU bf16 autocast for the equality), 1 thread for every bit-equality claim (2 threads: the original is not self-repeatable, one measurement), one machine. Synthetic rows and a stub Gemma, so round counts, call lengths and prompt widths are not the real pool's (K was pinned to 16 for the counts; the real pool averages 17.28 rounds). Op counts are ATen dispatches, not kernels. Nothing here measures CUDA time, launches, memory or kernel selection.

## What changed after the review (2026-10-16, second pass)

| finding | what I did |
|---|---|
| major: the recommended CUDA check never runs the checkpoint path | agreed. Added the section above and `box_ckpt_check` / `--box-ckpt` (K = 32, bf16, baseline x3 vs kvcat / fastteach, asserts bypass > 0 and hits > 0); said plainly that `abequiv` does not cover the checkpoint path. Shown only on the CPU tiny shape. |
| minor: bit-identical only at 1 thread; `torch.equal` hides signed zero | agreed. `same()` now compares int bit patterns (own test); everything re-run and still equal. The headline now says "at one CPU thread"; `test_7b` records the 2-thread behaviour at the real shape (baseline itself differs in 1 of 98 gradients). |
| minor: the miss-count assertion was vacuous | agreed. The report cites the equality; `test_5` now asserts misses with calls > misses without calls and I checked that a stale-cache mutant and a never-hit mutant are caught. |
| minor: kvcat installs on any ledger model | limited to the model class `B3G2` (Skip otherwise). |
| minor: fastteach launch statement and unlabelled op counts | corrected: about -2 fills per call; the 10,326 removed ops split into 10,294 inside `ByteWriter.teacher` (host tensors) and 32 outside, shown by counting. |
| minor: "composes with defer" | now "no-op under defer (except its fallback); untested". |
| minor: tests overwrote the record file | the record file is written only with `EXACT_ARMS_WRITE=1`. |
| minor: runner summary and timing text | prints passed / skipped / failed / selected; timing text fixed. |
| minor: no assertion that checkpointed rounds ran at the real shape; hits only asserted for the last combination | both asserted now. |
| minor: fastteach host time is a lower bound | labelled so, with the saving as an upper bound. |

Disagreements: none with the substance. One caveat on the major finding: I did not re-run the reviewer's CPU `abequiv` command nor know the real pool's longest program, so "probably never reaches the checkpoint path" stays an inference from the code (n_loops 12, K0 = longest program + 2), which is why the box check forces K instead of relying on the pool. All timings in this report were re-measured in this pass on a busy shared box and differ from the first pass; the op, sync and memory figures hardly moved (ops and syncs are exact counts).
