# Two candidate-exact arms, measured on the CPU (2026-10-16)

Code: custom_io at 74d6e92c75 (the code of GPU-RUN-3 and of the PC run 8aB3G2A4), read-only at `/home/user/src-g2f`. Nothing in custom_io or in `prof/` was edited. New files, all in this folder:
`exact_arms.py` (the two arms, `NEW_VARIANTS = [KvCat, FastTeach]`, picked up by `prof_launch.py`), `test_exact_arms.py` (25 tests), `test_exact_arms.log` (their output), `exact_arms_counts.json` (every number below).

Labels: **shown** = I ran it here (CPU, fp32 unless said, torch 2.11.0+cpu, stub Gemma, synthetic rows). **suggested** = reasoning or arithmetic from the GPU-RUN-3 record, not run. **untested** = no CUDA existed here.

## In plain words (for Ben)

Two small speed-ups that should not change a single number the model computes.

1. `kvcat`: every round, each of the two thinker blocks glues two big tables together (the tape's keys/values and the prompt's keys/values). In a teacher-forced micro-batch the two tables are the same every round, so the glued table is the same every round. The arm glues once and reuses it. Shown on the CPU: the same losses and the same gradients, bit for bit. It also saved about a third of the memory the forward pass keeps alive.
2. `fastteach`: before the writer is asked for a line, a helper builds the answer's target tensors with a slow loop (one tiny operation per byte, per row), reads two things back from the GPU, and copies four tensors over with waits. For the G2f writer the result of all that is provably all zeros where it matters, so the arm builds the same four tensors with numpy and copies them without waiting. Shown: the four tensors are identical for thousands of random target lists, and the training result is bit-identical.

Neither arm can make the GPU kernels themselves much faster. The record says the GPU is idle 37 to 60 % of the time because the CPU is slow to launch 70,600 small kernels per update. `kvcat` removes about 1 to 2 % of the launches and some GPU work (small, suggested). `fastteach` removes CPU work in Python (the loop), which is what a launch-bound run actually waits on, but its six waits per call are not the lever (`nosync` already removed those and did nothing). My honest expectation for both together is small: somewhere between nothing and a few percent (suggested, untested on CUDA).

## One correction to the numbers I was given

The task text says CatArrayBatchedCopy is "1,902 launches and 213 ms per update". In `gpu-run-3-box1/b3g2_profile.profiler.md` those two figures are in the "total ms" and "count" columns of the top-kernel table, and that table is summed over the 2 profiled updates (its `ProfilerStep*` row has count 2 and total 6,972 ms = 2 x 3,486 ms, and the top 25 kernels together would otherwise be more than the 1,415 ms real kernel time per update). Per update that is **951 launches and about 107 ms** (4.8 % of the 2.24 s unprofiled wall, 7.6 % of the 1,415 ms kernel time). The CPU count agrees: the model issues 206 `aten::cat` per micro-batch at 16 rounds (143 forward + 63 backward), which is 824 per update, against 951 per update on the GPU at 17.28 rounds (shown for the CPU count; arithmetic for the comparison). Everything below uses the per-update figure.

## kvcat

**What it changes.** `ledger.CBlock.forward` starts with `k, v = torch.cat([kvs[0], kvx[0]], 2), torch.cat([kvs[1], kvx[1]], 2)` every round and in every block. The arm rebuilds `CBlock.forward` from its own source with that one line replaced (prof_train's `patched_fn`; the source hash is checked, another source is a Skip) and keeps one cached (k, v) per block.

- Key: the identity of the two parent tensors `kvs` and `kvx` (`[2, B, heads, keys, dk]`, what `Tool.think` hands each block), their `_version` counters, and (grad enabled, autocast flags). Strong references to the last key only. **Deviation from the brief:** it said to key on `kvs[0], kvs[1], kvx[0], kvx[1]`; indexing a tensor makes a new view object each time (shown: the ids differ on every call), so those can never match. The parents are the stable objects.
- Free run: after a call the tape K/V is rebuilt (new tensors), the key no longer matches, the cat is rebuilt (shown: misses go up in `test_5`, results equal).
- Scope: `loss`, `run`, `talk`, `loop`, `trace_loss` on the model are wrapped; the cache is emptied when each starts and when it returns or raises (shown for all five paths and for an injected exception). `loop` is wrapped too because `call_evals` calls it directly. Teardown empties it.
- Inside backward (`torch._C._current_graph_task_id() != -1`, which is where ToolH1's non-reentrant checkpoint recomputes rounds t >= n_loops) the cache is neither read nor written: the recompute makes its own plain cat, as the original does. Shown: at K = 32 the tiny model has 80 such calls per 4 micro-batches, no cache entry survives the backward, and the gradients are equal.

**Exactness (shown, CPU).** All "equal" below means `torch.equal` (bitwise; nan-aware for floats), arm against the unmodified code, same seed and batches.

| check | result |
|---|---|
| (1) loss tensors and every aux entry, 4 micro-batches | equal |
| (2) all 72 parameter gradients after the 4 backward passes | equal (also a second batch/seed pair) |
| (3) 3 full updates (split, micro-batch loss, backward, clip_grad_norm_, AdamW fused=False), all parameters | equal; the weights really moved (>10 tensors differ from init) |
| (4) K forced to 32 (rounds 12..31 checkpointed) and to 4 | equal, losses, gradients and 3-update parameters |
| (5) free run: `run` (learned stop), `run(loops=6)` (settles), `talk`, `generate`, a direct `loop`, eval mode, no_grad, with a stand-in writer that writes calls so the tape K/V is rebuilt | equal (Z, tape, calls, records, answers) |
| (6) teardown | every attribute of the model, its blocks and the writer is identical (`is`) to before setup; class methods untouched |
| real shape, ONE micro-batch of 64 rows, K = 16, 4,023,302 params | loss equal and all 98 gradients equal |
| bf16 autocast on the CPU (`torch.autocast('cpu', dtype=torch.bfloat16)`), K = model draw and 32 | loss equal and all 72 gradients equal (max abs diff 0.0); 3 full updates also equal. The parameters and gradients are fp32 under CPU autocast; the K/V come out of the Linear in bf16 and are accumulated in bf16 on both sides. |

The backward claim held: the 17 per-round gradient slices are summed into the cached cat's gradient in the same (reverse-round) order and split once; each element gets the same additions in the same order, and select_backward's zero padding adds exactly. No near-miss to explain, so the arm stays `ab_cpu_rule = 'bit_exact'` and is **not** labelled 'near'.

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

**Memory (shown on the CPU, fp32, real 3M shape, 64 rows, prompts of 300 letters, K = 16).** Resident memory held by the forward pass's autograd graph (fresh process, difference of VmRSS before and after `model.loss`): baseline 3,271,980 kB, kvcat 2,231,664 kB, **-1.04 GB (-32 %)**. The baseline keeps one k and one v per saved round and block; the arm keeps one pair per block. On the GPU this is bf16, the real prompt widths and the allocator, so the saving there is untested; it is in the direction of the 8.33 GB peak at accum 4. (Incidental: the same shape with 1,926-letter prompts, the synthetic default, was killed by the box's 16 GB memory limit at 12.3 GB resident for the baseline, so the CPU real-shape tests use 300 letters; op and sync counts do not depend on the width.)

**Honest expected effect on the GPU (suggested).**
- Launches: per update at 17.28 rounds the arm gets about 2 blocks x 16.3 x 4 = 130 cache hits, each removing 2 `cat`, 4 `select_backward` (a zero fill plus a copy each, I believe: 2 kernels) and 2 `add`: about 1,040 ATen ops, up to about 1,560 kernels, i.e. 1.4 to 2.1 % of the 75,966 kernels per update. In a launch-bound run that is the CPU-side gain: at most about 1 to 2 %, near the 2 % noise floor of the record.
- GPU time: of the 951 cat launches per update, about 260 (27 %) are this site's, and they are the large ones (prompt-sized K/V), so most of the 107 ms per update may be theirs; the backward also stops writing and re-adding zero-padded 5-D grads for the same tensors (the kernel table has 142 ms/update of bf16 `add`, 43 ms of bf16 fill, 77 ms of copy that this site feeds into; its share is unknown). This is GPU time, not launches. It shortens the wall only if the GPU is the bottleneck, and the record says it is busy only 40 to 63 % of the time. So: a smaller GPU kernel total (tens of ms per update), a wall gain of perhaps 0 to 3 %, and lower activation memory. Only a GPU profile with the arm on can say more (`--variant kvcat --sections profiler`).

## fastteach

**What it changes.** `B3G2.answer_teacher(Z, ids)` is `ByteWriter.teacher(ids, cids, cmask, WCAP, BOS, EOS)` over `line_context(Z)`: cids zeros `[B, 1]`, cmask all False, made on the device. `teacher` reads both back with `.cpu()` (2 syncs on CUDA), runs a Python loop over rows and target bytes (select, eq, and, any; it can never hit), then copies inp, tgt, fb, over with four blocking `.to(dev)`. With `writer.copy` False (G2f) the writer ignores fb. The arm replaces `answer_teacher` on the model instance, only when `writer.copy` is False (else Skip; source hashes of `answer_teacher`, `line_context` and `ByteWriter.teacher` are checked): `teacher_np` builds inp, tgt, over with numpy (no loop over bytes), the three go to the device through prof_train's `to_device_async` (pinned + non_blocking on CUDA, plain `.to` on the CPU), and fb is `torch.zeros(B, L, 1, device=dev)`, a device fill with no host copy. No device read.

**Exactness (shown).**

| check | result |
|---|---|
| `teacher_np` vs the real `ByteWriter.teacher`, 1,800 random target lists (caps 1, 2, 3, 9, 69, 70; None, [], 1..cap-2 long, len+1 = cap, over-cap len+1 = cap+1, much longer; ids 0..299) plus hand corners (all None, tuples, numpy arrays) | inp, tgt, fb, over: `torch.equal`, same dtype, shape and strides, every case |
| premise: the original's fb is all zero and `[B, L, 1]` for line_context, any target list | true (50 random lists) |
| the installed variant vs the original method, 200 random calls | same four tensors, same dtype, shape, strides, device |
| (1)(2)(3)(4)(5)(6) as for kvcat (losses, aux, 72 gradients, 3 updates, K = 32 and 4, free run, teardown) | all equal; real shape, 64 rows: loss equal and all 98 gradients equal; bf16 CPU autocast equal |
| fastteach + kvcat, and nosync + fastteach + kvcat together | equal |

On CUDA the four tensors have the same values, dtypes and contiguity, so nothing downstream can see a difference by construction; what is untested is only that the pinned, non-blocking copies behave (they are the ones `nosync` already uses).

**Op, sync and host-time counts (shown).** Sync counts are call sites executed per micro-batch (`.cpu`, `.tolist`, `.item`, `.nonzero`, `.to(device)` blocking, `torch.tensor(..., device=)`); on the CPU none waits, each is a place that would on a CUDA tensor. Python's `bool()` of a tensor is counted separately (most are on CPU tensors: 1,082 of the baseline's 1,116 are the loop's `if hit.any()`).

| one micro-batch, K = 16 (16 teacher calls) | tiny, 4 rows | real 3M, 64 rows |
|---|---|---|
| non-view ATen ops, baseline -> fastteach | 7,805 -> 7,101 | 18,798 -> 8,472 (-10,326, -54.9 %) |
| biggest removals (real) | | `copy_` -4,034, `eq` -2,024, `any`/`_local_scalar_dense`/`bitwise_and` -1,082 each, `bitwise_and_` -942, `zeros` -48, `full` -32 |
| `.cpu()` calls (writer.py:121) | 32 -> 0 | 32 -> 0 |
| blocking `.to(dev)` calls (writer.py:138) | 64 -> 0 | 64 -> 0 |
| pinned non_blocking copies | 0 -> 48 (3 per call) | 0 -> 48 |
| host-sync call sites executed, all | 207 -> 111 | 207 -> 111 |
| host seconds inside `answer_teacher` during one forward | 2.6 -> 2.3 ms | 28.5 -> 5.6 ms |
| one call at 64 rows, golds of the real-shape model: answers / first calls / stop lines | | 5.2 / 6.2 / 0.33 ms -> 0.055 / 0.051 / 0.022 ms |

That is exactly the 6 syncs per call the brief predicted (2 `.cpu()` + 4 blocking copies), 96 per micro-batch at 16 rounds. The remaining sites (`tolist` b3g2.py:350/361, `nonzero` :374/:553, `torch.tensor(device=)` :355/:536, `.to` at b3g2.py:224/:567 and tool.py:175/180) are untouched. The host-time numbers are this sandbox's CPU and synthetic gold targets (the loop's cost is proportional to the target bytes); `nosync`, which also moves the context to the CPU, costs the same as the baseline on the CPU (5.3 / 6.8 / 0.34 ms), because on the CPU only the loop is visible.

**Honest expected effect on the GPU (suggested, untested).**
- GPU time: none. The kernels are the same; one fill kernel per call replaces one host-to-device copy.
- Syncs: per update about 4 x 17.28 = 69 calls, so about 138 device-to-host copies (of 745 per update) and 276 blocking host-to-device copies (I believe each is one `cudaStreamSynchronize`) removed, about 414 of 1,305 stream syncs. But `nosync` removed this same set (and more) on three boxes and measured -0.1 % and +1.2 %, inside the noise, so these waits are not the lever.
- Host CPU time: the part `nosync` left in. Measured here, 22.9 ms per micro-batch forward, about 92 ms per update; if the box's CPU were as fast as this one and the real pool's targets as long as the synthetic ones, that is up to about 4 % of the 2.24 s wall in a launch-bound run. Both "if"s are untested. Expect 0 to 4 %.

## Tests

`python test_exact_arms.py` (tiny: 81 s at 1 thread); `EXACT_ARMS_REAL=1 python test_exact_arms.py real` adds the real 3M shape (about 140 s at 1 thread; the cheaper tests skip themselves otherwise). 25 of 25 ran without failure (`test_exact_arms.log` holds both runs: the first skips the 4 real-shape tests, which need `EXACT_ARMS_REAL=1`, and the second runs them). Also checked: the arms register through `prof_launch.register` (names, `ab_cpu_rule = 'bit_exact'`, order after `nosync`, `parse_variants('fastteach,kvcat,nosync')` puts nosync first); a plain arm (PTS) gives a Skip for both; a writer with a copy path gives a Skip for fastteach; a changed `CBlock.forward` source gives a Skip for kvcat; the cache cannot go stale (an in-place write to kvs, another grad mode, a clone with equal values all miss).

On the box (not done here): `python prof_launch.py --arm B3G2 --rung 3M --accum 4 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json --sections abequiv --ab-variants kvcat,fastteach` for the bf16 bar, a baseline-against-baseline repeat first (see above), then `--sections profiler,syncs --variant kvcat` and `--variant fastteach` to read launches, cat/fill/add kernel totals and sync counts.

## Limits

CPU, fp32 (and CPU bf16 autocast for the equality), 1 thread, one machine. Synthetic rows and a stub Gemma, so round counts, call lengths and prompt widths are not the real pool's (K was pinned to 16 for the counts; the real pool averages 17.28 rounds). Op counts are ATen dispatches, not kernels. Nothing here measures CUDA time, launches, memory or kernel selection.
