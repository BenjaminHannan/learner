# Launch attribution of one B3G2 3M update (accum 4), counted on the CPU (2026-10-16)

Instrument: `launch/attrib.py` (tests `test_attrib.py`). Trainer code: custom_io at commit 74d6e92c75, built through the profiling harness (`prof/prof_train.py` World, so the model, caps and rows are the real ones). Everything here was counted on a 4-core CPU box with torch 2.11.0+cpu, **no GPU**. Labels: **shown** = I ran it and it is in the tables below; **suggested** = read from code or a documented table, not measured here; **untested** = not run.

## Verdicts on the four claims

| claim | verdict | numbers (this CPU run unless it says GPU) |
|---|---|---|
| C1 | **shown for the model side (a line to within 2.7 %); the Gemma front's fixed part is untested** | device kernel ops per micro-batch: a straight line -556 + 549 n (R2 0.9998, worst point 2.7 % off) over n = 7..32. The honest form is fixed part + sum of per-round costs: the model-side fixed part is 232 ops (2.4 % of a 17.28-round micro-batch, small), and a round costs 481, 523, 557 ops in the successive round classes (t 1..7, 8..11, 12 and later): it steps up when the answer pass, then the thinker, start being recomputed, which is why the line's intercept is negative. The real run also calls the Gemma front about twice per micro-batch whatever n is (stub here, so uncounted); the PTC profile bounds that at 5,929 launches per micro-batch, so "small fixed part" is untested for the whole micro-batch |
| C2 | **unclear: 45 % to 51 % by region, 60 % to 64 % with the writers' share of gradient accumulation** | writer passes (call + answer, forward + backward + recompute) are 45.4 % to 51.1 % of the per-round device kernel ops of the steady rounds; 59.7 % to 64.2 % when the engine's gradient additions are attributed to the region that produced the gradient |
| C3 | **shown** | device kernel ops per steady round: 513.42 at 16 rows, 513.50 at 64 rows (0.016 % apart); 1 of 280 (phase, region, op) cells differ on the device side; the CPU-tensor teacher does depend on the rows: 62 vs 176 CPU ops per round |
| C4 | **shown: 17 per round at the profiled updates' 75.5 rounds, from named lines (the 19 divides by 69.1 rounds)** | 16.8 blocking host-device calls per round at 16 named lines (9.8 device-to-host, 5.2 host-to-device, 1.9 implicit via two-index assignment); scaled to the GPU profile's 75.5 rounds and 4 micro-batches these lines give 1,266 per update against 1,272 at the same lines in the GPU record (the record's total 1,319.5 also has 48 in the real Gemma front). The GPU profile's 1,305 / (4 x 17.28) = 18.9 per round, and 1,319.5 / 75.5 = 17.5 on the profiled updates |

### In plain words

- **Shown (CPU op counts):** the launches of this training are a per-round story. A micro-batch costs a fixed 232 device kernel ops (reader, tape, loss tail, parameter grads: 2.4 % of a 17.28-round micro-batch) plus about 481 per round in rounds 1 to 7, rising to 557 per round once the answer pass and the thinker are being recomputed. In estimated CUDA launches a round is 556 to 607, later 634 to 687.
- **Shown:** the two writer passes (call_pass, ans_pass; forward, backward and recompute) are 45.4 % to 51.1 % of the per-round device kernel ops: about half, not clearly over it. The thinker is 20 % to 23 % of a round. The autograd engine's own gradient additions (one add for every extra use of a shared weight or activation, every round) are 23 % of the per-round ops and sit in neither. Attributed to the pass that produced the gradient they would lift the writers to 59.7 % to 64.2 %.
- **Shown:** the per-round device op count does not depend on the rows (513.4 at 16 rows, 513.5 at 64). The CPU-tensor teacher does (62 vs 176 CPU ops per round): that is host python time, not launches.
- **Shown (the call sites and counts), suggested (that CUDA waits at each):** 16.8 blocking host-device calls per round at 16 named lines (all in `ByteWriter.teacher`, `B3G2.loop` and the answer loop of `B3G2._loss`), 10 of them device-to-host reads. They scale with the rounds. The "about 19" is 1,305 / (4 x 17.28); at the profiled updates' own 75.5 rounds the GPU record gives 17.3 and this census 17.
- **Suggested (an estimate, not a measurement):** the model-side launch estimate is 59 % to 64 % of the 75,966 kernels per update.  The model code itself, with `addmm` and layer norm matching the GPU's counts to 1 %, is not where the missing launches are.

## What was run

| run | what | size |
|---|---|---|
| natural | 5 full update(s) after 1 warm-up update: real 3M shape, batch 256, accum 4, seed 400, synthetic rows, K drawn by torch.randint as in training; rounds per micro-batch [8, 16, 8, 8]; [32, 7, 16, 16]; [32, 16, 16, 8]; [16, 8, 32, 7]; [32, 32, 16, 16] | whole update incl. clip + AdamW |
| pinned | one micro-batch (64 rows) forward + backward per K, K pinned in custom_io.models.b3g2.KS; n = 7, 7, 8, 10, 12, 14, 16, 20, 24, 32 | for C1, per-round table, C2 |
| rows | K = 16, batch 64 vs 256 at accum 4: 16 vs 64 rows per micro-batch | for C3 |
| width | batch 64, K = 16, synthetic prompts up to 2000 letters instead of 300 | shape-independence check |
| autocast | K = 16 one micro-batch under torch.autocast("cpu", bfloat16) | counts the casts CPU autocast makes |
| multi-call rows | K = 16, 32 on rows with 3 to 9 calls (37 % of rows) instead of 0 or 2 | bias of the synthetic rows |

Commands (every number below is regenerated from the raw runs by the last one):

```
cd launch; export OMP_NUM_THREADS=1
python attrib.py natural --threads 1 --synth-letters 300 --n-updates 5 --out natural5b.json         # seed 400, 1 warm-up update, then 5 instrumented updates (final code)
python attrib.py pinned  --threads 1 --synth-letters 300 --ks 4,6,8,10,12,14,16,20,24,32 --out pinned.json      # one micro-batch (64 rows) per K, fwd + backward
python attrib.py rows    --threads 1 --synth-letters 300 --batches 64,256 --k 16 --out rows.json                # 16 vs 64 rows per micro-batch
python attrib.py rows    --threads 1 --synth-letters 2000 --batches 64 --k 16 --out width2000_b64.json         # the width check
python attrib.py pinned  --threads 1 --synth-letters 300 --ks 16 --autocast --out autocast16.json             # CPU autocast bf16 casts
python attrib.py multi   --threads 1 --synth-letters 300 --ks 16,32 --out multi.json                          # rows with 3 to 9 calls
python attrib.py report --natural natural5b.json --natural-check natural5.json --pinned pinned.json --rows-json rows.json --autocast-json autocast16.json --width width2000_b64.json --multi multi.json --md ATTRIB-CPU-2026-10-16.md --json ATTRIB-CPU-2026-10-16.json
```

Common to every run: arm B3G2, rung 3M (4,023,302 trained parameters), caps `caps_b3g2.json`, stub Gemma front, device cpu, torch 2.11.0+cpu, seed 400, rows from `prof_train.synth_rows` (half skills-shaped rows with two worked steps, half cloze rows with none), `n_loops` = 12. One CPU thread per run. **Deviation from the brief:** the synthetic prompts are at most 300 letters, not the caps' 2,000, because the 2,000-letter shape needs 13 GB of RAM on this shared box; every op count is independent of the padded width (shown by the width check below). The update is replicated, not called: `Replica.update` does split_batch, `model.loss(mb)` under the (here empty) autocast, `(l / k).backward()`, `clip_grad_norm_(1.0)`, fused AdamW step and `zero_grad(set_to_none=True)` as train.py does; the optimizer is built `fused=True` even on CPU so that its op sequence is the CUDA one (the harness builds it fused only on CUDA).
## Per-update totals by phase (natural K draws, seed 400, one update after one warm-up update)

**Update 0 (the first instrumented update, right after the warm-up update)**: rounds per micro-batch [8, 16, 8, 8] (K [4, 16, 8, 8]), 40 rounds, device kernel ops 20,132, estimated CUDA launches 23,196 to 24,586 (stub Gemma and CPU-tensor teacher excluded); CPU-tensor teacher ops 29,262.

| phase | all ops | views (no kernel) | host-scalar / alloc | kernel ops | est. CUDA launches |
|---|---|---|---|---|---|
| forward | 15,314 | 7,052 | 432 | 7,830 | 8,446 to 8,834 |
| backward (engine adds included) | 23,291 | 11,594 | 0 | 11,697 | 14,083 to 15,053 |
| recompute (checkpoint re-forward) | 1,740 | 1,180 | 32 | 528 | 576 to 608 |
| host: teacher_host (CPU tensors) | 74,770 | 41,844 | 3,664 | 29,262 | 0 (CPU tensors) |
| train loop (split, loss average) | 134 | 57 | 0 | 77 | 77 |
| clip_grad_norm_ | 8 | 0 | 0 | 8 | 9 |
| AdamW step (fused) | 8 | 0 | 4 | 4 | 5 |
| stub Gemma front (not a real op set; excluded) | 224 | 72 | 0 | 152 | n/a (stub) |
| **device total** | 40,495 | 19,883 | 468 | **20,144** | **23,196 to 24,586** |

All natural updates (the same replica, successive batches; each has its own K draws):

| update | rounds per micro-batch | rounds | device kernel ops | est. CUDA launches | launches per round (all-in) | CPU teacher ops | per-round model predicts kernel ops to |
|---|---|---|---|---|---|---|---|
| 0 | [8, 16, 8, 8] | 40 | 20,132 | 23,196 to 24,586 | 580 to 615 | 29,262 | 0.39 % under |
| 1 | [32, 7, 16, 16] | 71 | 37,194 | 42,591 to 45,062 | 600 to 635 | 36,047 | 0.61 % under |
| 2 | [32, 16, 16, 8] | 72 | 37,683 | 43,163 to 45,673 | 599 to 634 | 33,352 | 0.64 % under |
| 3 | [16, 8, 32, 7] | 63 | 32,878 | 37,688 to 39,890 | 598 to 633 | 32,783 | 0.45 % under |
| 4 | [32, 32, 16, 16] | 96 | 50,916 | 58,220 to 61,578 | 606 to 641 | 40,543 | 0.64 % under |

"Forward" excludes the train-loop ops and the stub Gemma; "backward" includes the autograd engine's own gradient additions (region grad_accumulate); "recompute" is the checkpoint re-forward the engine triggers inside backward (answer pass from round 8, thinker from round 12; the non-reentrant checkpoint stops re-running a function once the saved tensors backward needs are rebuilt, so a recompute is shorter than the forward). The clip and AdamW launch numbers come from the multi-tensor-apply model (`multi_tensor_launches`), not from the CPU op list (which shows the same ops: one `_foreach_norm`, one `_foreach_mul_`, two `_fused_adamw_`).
## Per-round table: region x phase (kernel ops per thinker round)

From the pinned run with n = 32 rounds (64 rows, K = 32); per-round values are means over the rounds of each class. Device kernel ops; in brackets the estimated CUDA launches (low to high). The thinker is checkpointed from round 12 (`t >= n_loops`), the answer pass from round 8 (`CKPT_FROM`), the call pass never.

**t = 0**  (views, which launch nothing: 317.0 per round)

| region | forward | backward | recompute | total kernel ops | est. CUDA launches |
|---|---|---|---|---|---|
| thinker | 36.0 | 60.0 | 0.0 | 96.0 | 120.0 to 134.0 |
| answer_writer | 62.0 | 49.0 | 0.0 | 111.0 | 130.0 to 145.0 |
| loop_bookkeeping | 4.0 | 2.0 | 0.0 | 6.0 | 7.0 to 7.0 |
| loss_tail | 17.0 | 4.0 | 0.0 | 21.0 | 29.0 to 34.0 |
| grad_accumulate | 0.0 | 87.0 | 0.0 | 87.0 | 87.0 to 87.0 |
| **all regions** |  |  |  | **321.0** | **373.0 to 407.0** |

**t = 1..7**  (views, which launch nothing: 447.0 per round)

| region | forward | backward | recompute | total kernel ops | est. CUDA launches |
|---|---|---|---|---|---|
| thinker | 36.0 | 60.0 | 0.0 | 96.0 | 120.0 to 134.0 |
| call_writer | 59.0 | 48.7 | 0.0 | 107.7 | 126.7 to 141.7 |
| answer_writer | 62.0 | 49.0 | 0.0 | 111.0 | 130.0 to 145.0 |
| loop_bookkeeping | 19.1 | 5.1 | 0.0 | 24.3 | 30.1 to 32.9 |
| loss_tail | 15.9 | 3.4 | 0.0 | 19.3 | 25.9 to 30.0 |
| grad_accumulate | 0.0 | 123.0 | 0.0 | 123.0 | 123.0 to 123.0 |
| **all regions** |  |  |  | **481.3** | **555.7 to 606.6** |

**t = 8..11 (answer pass recomputed)**  (views, which launch nothing: 569.0 per round)

| region | forward | backward | recompute | total kernel ops | est. CUDA launches |
|---|---|---|---|---|---|
| thinker | 36.0 | 60.0 | 0.0 | 96.0 | 120.0 to 134.0 |
| call_writer | 59.0 | 48.0 | 0.0 | 107.0 | 126.0 to 141.0 |
| answer_writer | 62.0 | 49.0 | 49.0 | 160.0 | 182.0 to 199.0 |
| loop_bookkeeping | 18.0 | 4.0 | 0.0 | 22.0 | 25.0 to 26.0 |
| loss_tail | 13.0 | 2.0 | 0.0 | 15.0 | 18.0 to 20.0 |
| grad_accumulate | 0.0 | 123.0 | 0.0 | 123.0 | 123.0 to 123.0 |
| **all regions** |  |  |  | **523.0** | **594.0 to 643.0** |

**t = 12..30 (thinker + answer recomputed)**  (views, which launch nothing: 746.0 per round)

| region | forward | backward | recompute | total kernel ops | est. CUDA launches |
|---|---|---|---|---|---|
| thinker | 36.0 | 60.0 | 34.0 | 130.0 | 160.0 to 178.0 |
| call_writer | 59.0 | 48.0 | 0.0 | 107.0 | 126.0 to 141.0 |
| answer_writer | 62.0 | 49.0 | 49.0 | 160.0 | 182.0 to 199.0 |
| loop_bookkeeping | 18.0 | 4.0 | 0.0 | 22.0 | 25.0 to 26.0 |
| loss_tail | 13.0 | 2.0 | 0.0 | 15.0 | 18.0 to 20.0 |
| grad_accumulate | 0.0 | 123.0 | 0.0 | 123.0 | 123.0 to 123.0 |
| **all regions** |  |  |  | **557.0** | **634.0 to 687.0** |

**last round (t = 31)**  (views, which launch nothing: 746.0 per round)

| region | forward | backward | recompute | total kernel ops | est. CUDA launches |
|---|---|---|---|---|---|
| thinker | 36.0 | 60.0 | 34.0 | 130.0 | 160.0 to 178.0 |
| call_writer | 59.0 | 48.0 | 0.0 | 107.0 | 126.0 to 141.0 |
| answer_writer | 62.0 | 49.0 | 49.0 | 160.0 | 182.0 to 199.0 |
| loop_bookkeeping | 18.0 | 4.0 | 0.0 | 22.0 | 25.0 to 26.0 |
| loss_tail | 17.0 | 2.0 | 0.0 | 19.0 | 22.0 to 24.0 |
| grad_accumulate | 0.0 | 50.0 | 0.0 | 50.0 | 50.0 to 50.0 |
| **all regions** |  |  |  | **488.0** | **565.0 to 618.0** |

**Which ATen ops fill a steady round** (rounds 12 to 30 of the n = 32 run; 557 device kernel ops per round; one row per op name, all overloads):

| op | per round | share | where (region/phase: per round) |
|---|---|---|---|
| add | 156.0 | 28.0 % | grad_accumulate/backward 123.0, answer_writer/forward 6.0, call_writer/forward 6.0 |
| mm | 63.0 | 11.3 % | thinker/backward 24.0, answer_writer/backward 18.0, call_writer/backward 18.0 |
| addmm | 47.0 | 8.4 % | thinker/forward 12.0, thinker/recompute 11.0, answer_writer/forward 8.0 |
| sum | 43.0 | 7.7 % | thinker/backward 12.0, answer_writer/backward 11.0, call_writer/backward 10.0 |
| native_layer_norm | 28.0 | 5.0 % | thinker/forward 6.0, thinker/recompute 6.0, answer_writer/forward 5.0 |
| zeros | 18.0 | 3.2 % | call_writer/forward 9.0, answer_writer/forward 4.0, answer_writer/recompute 4.0 |
| cat | 17.0 | 3.1 % | thinker/forward 4.0, thinker/recompute 4.0, answer_writer/forward 2.0 |
| native_layer_norm_backward | 17.0 | 3.1 % | thinker/backward 6.0, answer_writer/backward 5.0, call_writer/backward 5.0 |
| ones | 11.0 | 2.0 % | answer_writer/forward 4.0, answer_writer/recompute 4.0, call_writer/forward 3.0 |
| select_backward | 11.0 | 2.0 % | thinker/backward 8.0, answer_writer/backward 1.0, call_writer/backward 1.0 |
| _scaled_dot_product_flash_attention_for_cpu | 11.0 | 2.0 % | thinker/forward 4.0, thinker/recompute 4.0, answer_writer/forward 1.0 |
| mul | 8.0 | 1.4 % | answer_writer/forward 2.0, answer_writer/backward 1.0, call_writer/backward 1.0 |
| div | 8.0 | 1.4 % | answer_writer/backward 2.0, call_writer/backward 2.0, loop_bookkeeping/backward 1.0 |
| ne | 7.0 | 1.3 % | answer_writer/forward 3.0, call_writer/forward 2.0, answer_writer/recompute 2.0 |
| gelu | 7.0 | 1.3 % | thinker/forward 2.0, thinker/recompute 2.0, answer_writer/forward 1.0 |
| where | 7.0 | 1.3 % | thinker/forward 2.0, thinker/recompute 2.0, answer_writer/forward 1.0 |

The engine's gradient additions (region grad_accumulate) are real kernel launches on CUDA (the GPU profile's most frequent kernel is the bf16 `add`, 5,844 per update): every parameter used in each round and every activation read by more than one op gets one add per use. Per round, by op: add 123.0.

By the region whose backward produced the gradient being added (per steady round): thinker 50.0, call_writer 35.0, answer_writer 34.0, loop_bookkeeping 2.0, loss_tail 2.0.
## The part that does not depend on the number of rounds (once per micro-batch)

Ops with no round tag in the n = 32 run: the reader and tape (the stub Gemma front excluded), the answer teacher's device zeros, the loss tail (`ln_z` / stop head over all rounds at once), the engine's AccumulateGrad of the parameters. The CPU-tensor teacher has its own fixed part, see the fit table.

| region | phase | kernel ops | est. CUDA launches | views |
|---|---|---|---|---|
| grad_accumulate | backward | 35 | 35 to 35 | 98 |
| loop_bookkeeping | backward | 10 | 15 to 15 | 7 |
| loss_tail | backward | 11 | 12 to 12 | 40 |
| reader_gemma_tape | backward | 64 | 93 to 121 | 65 |
| train_loop | backward | 1 | 1 to 1 | 0 |
| answer_writer | forward | 3 | 3 to 3 | 0 |
| loop_bookkeeping | forward | 14 | 14 to 14 | 8 |
| loss_tail | forward | 33 | 32 to 32 | 17 |
| reader_gemma_tape | forward | 60 | 60 to 60 | 56 |
| train_loop | forward | 1 | 1 to 1 | 0 |
| **total** |  | **232** | **266 to 294** | 291 |
## C1: ops per micro-batch against the number of rounds n

| n | K | all ops (dev) | device kernel ops | est. launches (low) | est. launches (high) | writer kernel ops | CPU teacher ops (host) |
|---|---|---|---|---|---|---|---|
| 7 | 4 | 6,716 | 3,379 | 3,918 | 4,289 | 1,427 | 7,553 |
| 7 | 6 | 6,716 | 3,379 | 3,918 | 4,289 | 1,427 | 7,553 |
| 8 | 8 | 7,648 | 3,853 | 4,460 | 4,878 | 1,645 | 7,684 |
| 10 | 10 | 9,862 | 4,899 | 5,648 | 6,164 | 2,179 | 7,946 |
| 12 | 12 | 12,076 | 5,945 | 6,836 | 7,450 | 2,713 | 8,208 |
| 14 | 14 | 14,724 | 7,059 | 8,104 | 8,824 | 3,247 | 8,470 |
| 16 | 16 | 17,372 | 8,173 | 9,372 | 10,198 | 3,781 | 8,732 |
| 20 | 20 | 22,668 | 10,401 | 11,908 | 12,946 | 4,849 | 9,256 |
| 24 | 24 | 27,964 | 12,629 | 14,444 | 15,694 | 5,917 | 9,780 |
| 32 | 32 | 38,556 | 17,085 | 19,516 | 21,190 | 8,053 | 10,828 |

| quantity per micro-batch | a | b (per round) | R2 | worst point | b using n >= 12 only |
|---|---|---|---|---|---|
| all ops incl. views (device) | -2,729.0 | 1,277.3 | 0.9987 | 7.5 % | 1,324.0 |
| kernel ops (device) | -556.5 | 549.1 | 0.9998 | 2.7 % | 557.0 |
| kernel ops incl. CPU teacher | 6,079.5 | 680.1 | 0.9999 | 0.8 % | 688.0 |
| est. launches, low | -560.6 | 624.9 | 0.9998 | 2.7 % | 634.0 |
| est. launches, high | -563.4 | 677.0 | 0.9998 | 2.6 % | 687.0 |
| writer passes: kernel ops | -461.9 | 265.7 | 0.9999 | 2.0 % | 267.0 |
| kernel ops: thinker | -254.6 | 123.4 | 0.9973 | 9.3 % | 130.0 |
| kernel ops: call_writer | -102.0 | 107.0 | 1.0000 | 0.0 % | 107.0 |
| kernel ops: answer_writer | -359.9 | 158.7 | 0.9998 | 3.7 % | 160.0 |
| kernel ops: teacher_host | 6,636.0 | 131.0 | 1.0000 | 0.0 % | 131.0 |
| kernel ops: loop_bookkeeping | 24.0 | 22.0 | 1.0000 | 0.0 % | 22.0 |
| kernel ops: loss_tail | 84.0 | 15.0 | 1.0000 | 0.0 % | 15.0 |
| kernel ops: reader_gemma_tape | 124.0 | 0.0 | 1.0000 | 0.0 % | 0.0 |
| kernel ops: train_loop | 2.0 | 0.0 | 1.0000 | 0.0 % | 0.0 |
| kernel ops: grad_accumulate | -74.0 | 123.0 | 1.0000 | 0.0 % | 123.0 |

Additivity (the structure behind the line): the reference run's fixed part plus its per-round totals reproduce every other pinned run: n = 7: +2.46 %; n = 7: +2.46 %; n = 8: +2.15 %; n = 10: +0.69 %; n = 12: +0.57 %; n = 14: +0.00 %; n = 16: +0.00 %; n = 20: +0.00 %; n = 24: +0.00 %; n = 32: +0.00 %. The error is 0 from n = 14 on and small for n < 14 because the first rounds of a run depend on where its rows' calls fall (the schedule is random per run); the per-round cost of round t does not depend on n.
## C2: the writer passes against everything else

Rows are totals over the rounds of each class (not per round), so only the shares matter.

| round class | kernel ops (sum over the class) | writer share of kernel ops | same, engine adds left out of the denominator | engine adds folded into their producer | writer share of est. launches (low to high) | writer share counting the CPU teacher ops | writer share within forward / backward / recompute |
|---|---|---|---|---|---|---|---|
| t = 0 | 321.0 | 34.6 % | 47.4 % | 45.2 % | 34.9 % to 35.6 % | 34.6 % | 52 % / 24 % / - |
| t = 1..7 | 3,369.0 | 45.4 % | 61.0 % | 59.7 % | 46.2 % to 47.3 % | 79.5 % | 63 % / 34 % / - |
| t = 8..11 (answer pass recomputed) | 2,092.0 | 51.1 % | 66.8 % | 64.2 % | 51.9 % to 52.9 % | 60.9 % | 64 % / 34 % / 100 % |
| t = 12..30 (thinker + answer recomputed) | 10,583.0 | 47.9 % | 61.5 % | 60.3 % | 48.6 % to 49.5 % | 57.8 % | 64 % / 34 % / 59 % |
| last round (t = 31) | 488.0 | 54.7 % | 61.0 % | 62.7 % | 54.5 % to 55.0 % | 64.3 % | 63 % / 46 % / 59 % |

Writer = region call_writer + answer_writer (B3G2.call_pass inside B3G2.loop, B3G2.ans_pass inside B3G2._loss, and `answer_teacher`'s device zeros); the CPU-tensor teacher (ByteWriter.teacher internals) is not a launch and is counted separately.
## C3: do the per-round counts depend on the rows of the micro-batch?

K = 16, rounds 3..14 (all steady), 16 rows (batch 64 / accum 4) against 64 rows (batch 256 / accum 4); n = 16.0, 16.0.

|  | 16 rows | 64 rows |
|---|---|---|
| device kernel ops per steady round | 513.42 | 513.50 |
| CPU-tensor teacher ops per round (not launches) | 61.7 | 175.5 |
| device kernel ops, once per micro-batch | 232 | 232 |
| CPU teacher ops, once per micro-batch | 540 | 2095 |

(phase, region, op) cells with a different per-round count on the device side: 1 of 280. They are:

| phase | region | op | kind | per round at 16 rows | per round at 64 rows |
|---|---|---|---|---|---|
| backward | call_writer | sum.dim_IntList | kernel | 10.167 | 10.250 |

Teacher cells that depend on the rows (CPU tensors; python loops over rows and bytes, no launch): select.int 63 -> 216, copy_|memcpy 39 -> 139, lift_fresh 36 -> 134, slice.Tensor 14 -> 34, eq.Scalar 8 -> 13, _local_scalar_dense 4 -> 7.

Width check: the same 16-row micro-batch with prompts up to 300 letters and up to 2,000 letters: device kernel ops per steady round 513.42 vs 513.42, 0 differing cells, once-per-micro-batch ops 232 vs 232. So running at width 300 (13 GB of RAM at 2,000) changes no op count.
## C4: host syncs by call site

Counted over 5 natural update(s), 342 rounds, 20 micro-batches. Class (read from the source, suggested): **sync** = a device tensor in the real run, so on CUDA the call waits for the stream (a device-to-host read, or a pageable host-to-device copy with non_blocking=False, which ends in a stream synchronise); **host** = a CPU tensor in the real run (counted here only because a CPU run cannot tell); **noop** = `.to(dev)` of a tensor already there; **stub** = this harness's stand-in for the Gemma front; **no-sync** = a tensor-index call the GPU record does not flag; **gpu-only** = lines of the real Gemma front. "Scaled" = per-round count x 75.5 rounds + per-micro-batch count x 4, i.e. what this code would do in the GPU record's two profiled updates; the GPU column is that record (`set_sync_debug_mode('warn')`).

| call site | kind | class | removed by the harness's nosync | per update (this run) | scaled to the GPU rounds | GPU per update | CPU / GPU | what it is |
|---|---|---|---|---|---|---|---|---|
| writer.py:138 | H2D | sync | yes | 273.6 | 300.3 | 302.0 | 0.99 | inp / tgt / fb / over .to(dev) at the end of ByteWriter.teacher: four blocking host-to-device copies per teacher call |
| b3g2.py:350 | D2H | sync | yes | 193.2 | 213.3 | 214.5 | 0.99 | call.tolist(), kk.tolist(), (t > last).tolist(): the schedule sits on the device and is read back (3 per round t >= 1) |
| writer.py:121 | D2H | sync | yes | 136.8 | 150.2 | 151.0 | 0.99 | cids.cpu(), cmask.cpu() in ByteWriter.teacher: two device zeros made by line_context, copied straight back (2 per teacher call) |
| b3g2.py:551 | D2H | sync |  | 68.4 | 75.5 | 75.5 | 1.00 | if not ok.any(): bool of a device tensor (1 per round) |
| b3g2.py:553 | D2H | sync |  | 68.4 | 75.5 | 75.5 | 1.00 | ok.nonzero()[:, 0] (1 per round) |
| b3g2.py:554 | D2H | sync |  | 68.4 | 75.5 | 75.5 | 1.00 | bool(ok.all()) (1 per round) |
| b3g2.py:361 | D2H | sync |  | 64.4 | 71.1 | 71.5 | 0.99 | ok.tolist(): which rows the call_pass got right (1 per round t >= 1) |
| b3g2.py:374 | D2H | sync | yes | 64.4 | 71.1 | 71.5 | 0.99 | call.nonzero(): the rows with a call this round (1 per round t >= 1) |
| b3g2.py:355 | H2D | sync |  | 64.4 | 71.1 | 71.5 | 0.99 | torch.tensor(sel, device=dev): the row list to the device (1 per round t >= 1) |
| b3g2.py:375 (index / index_put_) | implicit | sync |  | 64.4 | 71.1 | 71.5 | 0.99 | cround[rows, kk[rows]] = t: index / index_put_ with two tensor indices; the GPU record flags this line (why CUDA waits there is untested) |
| b3g2.py:376 (index / index_put_) | implicit | sync |  | 64.4 | 71.1 | 71.5 | 0.99 | shown[rows, kk[rows]] = True: same shape as line 375; flagged by the GPU record |
| b3g2.py:535 | D2H | sync |  | 4.0 | 4.0 | 4.0 | 1.00 | int(last.max()): the longest call round, a device tensor read back (1 per micro-batch) |
| b3g2.py:224 | H2D | sync |  | 4.0 | 4.0 | 4.0 | 1.00 | torch.from_numpy(sched).to(dev) in plan (1 per micro-batch) |
| b3g2.py:536 | H2D | sync |  | 4.0 | 4.0 | 4.0 | 1.00 | torch.tensor([bool(L) ...], device=dev) for g["has"] (1 per micro-batch) |
| tool.py:175 | H2D | sync |  | 4.0 | 4.0 | 4.0 | 1.00 | torch.from_numpy(ids).to(dev) in read_texts (1 per read_texts call, 1 per micro-batch here) |
| tool.py:180 | H2D | sync |  | 4.0 | 4.0 | 4.0 | 1.00 | torch.tensor(full, device=dev) in read_texts |
| eg.py:108 | ? | gpu-only |  | 0.0 |  | 16.0 |  | in the GPU record only: the real Gemma front (eg.py / transformers masking_utils); this CPU run has a stub there |
| masking_utils.py:335 | ? | gpu-only |  | 0.0 |  | 16.0 |  | in the GPU record only: the real Gemma front (eg.py / transformers masking_utils); this CPU run has a stub there |
| eg.py:128 | ? | gpu-only |  | 0.0 |  | 16.0 |  | in the GPU record only: the real Gemma front (eg.py / transformers masking_utils); this CPU run has a stub there |
| prof_train.py:331 | H2D | stub |  | 16.0 | 16.0 |  |  | stub front: ids / mask to the device (real: eg.py:108) |
| prof_train.py:341 | H2D | stub |  | 16.0 | 16.0 |  |  | stub front: char-to-token map to the device (real: eg.py:128) |
| torch-internal | H2D | noop |  | 99.0 | 99.0 |  |  | torch.nn.utils.clip_grad_norm_: norm.to(first_device) on tensors already there (no copy) |
| b3g2.py:567 | H2D | noop |  | 4.0 | 4.0 |  |  | right.to(dev): right was made on dev already (torch.zeros(..., device=dev)), a no-op |
| data.py:211 | H2D | noop |  | 4.0 | 4.0 |  |  | to_device of the batch in the replica (once per update; a CPU no-op here) |
| writer.py:135 | D2H | host |  | 3,871.4 | 4,145.0 |  |  | hit.any() in the teacher's python loops over CPU tensors (no device in the real run) |
| b3g2.py:534 | D2H | host |  | 4.0 | 4.0 |  |  | int(torch.randint(...)): the loop-length draw is a CPU tensor, no stream wait |
| writer.py:60 (index / index_put_) | implicit | no-sync |  | 169.6 | 187.2 |  |  | tensor-index call the GPU record does not flag (a gather / scatter, no wait) |
| b3g2.py:555 (index / index_put_) | implicit | no-sync |  | 106.4 | 117.4 |  |  | tensor-index call the GPU record does not flag (a gather / scatter, no wait) |
| b3g2.py:563 (index / index_put_) | implicit | no-sync |  | 68.4 | 75.5 |  |  | tensor-index call the GPU record does not flag (a gather / scatter, no wait) |
| b3g2.py:230 (index / index_put_) | implicit | no-sync |  | 36.8 | 40.6 |  |  | tensor-index call the GPU record does not flag (a gather / scatter, no wait) |
| stub:275 (index / index_put_) | implicit | no-sync |  | 8.0 | 8.0 |  |  | tensor-index call the GPU record does not flag (a gather / scatter, no wait) |
| tool.py:183 (index / index_put_) | implicit | no-sync |  | 8.0 | 8.0 |  |  | tensor-index call the GPU record does not flag (a gather / scatter, no wait) |

The harness's `nosync` variant (GPU-RUN-3: -0.1 % to +1.2 % speed, i.e. nothing) removed the four lines marked: 9.8 of the 16.8 syncs per round; the other 7.1 per round read values computed on the device (`ok`, the answer-loop masks) or are the two index assignments and stay.

**Sum over the 16 sync lines**: 16.82 per round (per update / rounds: device-to-host 9.77, host-to-device 5.18, implicit via two-index assignment 1.88); scaled: 1,266 per update; the same lines in the GPU record: 1,272; GPU lines this run cannot reproduce (real Gemma front): 48.

|  | per update | per round (at 75.5 rounds) | per round (at 69.1 rounds = 4 x 17.28) |
|---|---|---|---|
| GPU cudaStreamSynchronize (profiler) | 1,305 | 17.28 | 18.88 |
| GPU sync-debug warnings summed over lines | 1,319.5 | 17.48 | 19.09 |
| GPU device-to-host copies (profiler) | 745 | 9.87 | 10.78 |
| GPU host-to-device copies (profiler) | 561.5 | 7.44 | 8.12 |
| this CPU census, the sync lines, scaled | 1,266 | 16.76 | 1163 / 69.12 = 16.82 |

The claim "about 19 per round" is the profiler's 1,305 divided by 4 x 17.28 rounds; the profiled updates had 75.5 rounds (b3g2.py:551 runs once per round), which gives 17.3. Either way the syncs scale with rounds, 4 teacher-copy waits + 2 teacher `.cpu()` + 3 schedule `tolist` + 1 `torch.tensor(sel)` + 1 `ok.tolist` + 1 `nonzero` + 3 reads in the answer loop + 2 two-index assignments = 17 per round. Device-to-host copies per round in the GPU profile (9.9) equal the number of D2H lines here (2 + 3 + 1 + 1 + 3 = 10).
## Kernel estimate against the GPU profile (75,966 kernels per update)

How the estimate is built (suggested, not measured): per micro-batch the per-round table gives the estimated launches (CUDA launches per ATen op from `KERNEL_TABLE` in attrib.py: one per kernel op by default, with overrides for SDPA with a bool mask, the layer-norm backward, index_put with accumulate, embedding backward, select / slice backward; a same-dtype contiguous copy is a memcpy, not a launch); per update add clip_grad_norm_ (9 launches by the multi-tensor-apply model), fused AdamW (5) and the train loop's loss and aux averaging (73). `low` and `high` are the two ends of the override brackets. The micro-batch round counts of the real pool are not measured here. Case 1 takes the GPU record's mean of 17.28 with K from (4, 8, 16, 32) and n = max(K, last + 2): last + 2 = 10.56 for the two small K gives the mix (10.56, 10.56, 16, 32). Case 2 is the GPU profile's own two updates, whose rounds are known: b3g2.py:551 runs once per round and the record has 75.5 per update, i.e. 151 over the two. The loop length is K = KS[torch.randint] and the K stream of seed 400 is the same here (the K lists of my natural updates are the stream; counting stream updates from 0, my natural update 0 is stream update 1 because the warm-up update came first: update 1: K 4, 16, 8, 8; update 2: K 32, 4, 16, 16; update 3: K 32, 16, 16, 8; update 4: K 16, 8, 32, 4; update 5: K 32, 32, 16, 16; update 6: K 16, 16, 16, 4; update 7: K 32, 16, 16, 4; update 8: K 16, 16, 16, 32), so the profiled updates were two consecutive updates of that stream with K sums of 148 ((32,32,16,16) and (16,16,16,4) = updates 5 and 6, or (32,16,16,4) and (16,16,16,32) = updates 7 and 8, the profiler's default warm-up), and 151 = 148 + 3 means the one K = 4 draw ran n = 7 (7 is also what the harness rows give for that draw). Either way the micro-batch round counts are {7, 16, 16, 16, 16, 16, 32, 32}, and case 2 is the estimate for exactly that mix, using the measured totals of the pinned runs with those n.

| rounds assumed | rounds per update | est. launches (per-round table) | est. launches (linear fit) | ratio to 75,966 (per-round table) |
|---|---|---|---|---|
| population mean (17.28 rounds per micro-batch, assumed mix n = 10.56, 10.56, 16, 32) | 69.1 | 41,016 to 44,611 | 41,035 to 44,630 | 54.0 % to 58.7 % |
| the two profiled updates (75.5 rounds per update): n = 32, 16, 16, 7 and 16, 16, 16, 32 (inferred, see the text) | 75.5 | 44,992 to 48,916 | 45,022 to 48,950 | 59.2 % to 64.4 % |
| 4 micro-batches of 17.28 rounds (linear fit) | 69.1 | 40,821 to 44,396 | 41,035 to 44,630 | 53.7 % to 58.4 % |

**Ratio.** The model-side estimate (no Gemma front, no bf16 casts) at the profiled updates' rounds is 44,992 to 48,916 launches, **59 % to 64 % of the 75,966 kernels** the GPU profile counted (per round, all-in: 596 to 648 against the profile's 1006). The gap is 27,050 to 30,975 launches per update.

**What the GPU profile itself says about the gap.** The profile lists the 25 CPU ops with the most self time, with call counts. For the ops that are one launch each, the CPU dispatch count at the same rounds (75.5) is compared with the GPU's call count per update:

| aten op | GPU calls per update | CPU dispatch count at the same rounds | CPU / GPU | GPU minus CPU |
|---|---|---|---|---|
| aten::mm | 6,387 | 4,705 | 0.74 | 1,682 |
| aten::addmm | 2,794 | 2,801 | 1.00 | -7 |
| aten::native_layer_norm | 1,694 | 1,716 | 1.01 | -22 |
| aten::add + aten::add_ | 13,840 | 11,135 | 0.80 | 2,704 |
| aten::mul | 5,142 | 673 | 0.13 | 4,468 |
| aten::sum | 3,266 | 3,223 | 0.99 | 42 |
| aten::pow | 3,104 | 0 |  | 3,104 |
| aten::_to_copy | 13,148 | 163 | 0.01 | 12,985 |

`addmm`, layer norm and `sum` agree to within 1 % (ratio 0.99 to 1.01): the CPU run sees the op sequence the GPU ran for the model. The ops that the GPU has and the CPU run does not are aten::mm +1,682, aten::add + aten::add_ +2,704, aten::mul +4,468, aten::pow +3,104, aten::_to_copy +12,985 per update, 24,943 calls in all, each about one launch. That is 81 % to 92 % of the gap (suggested: `_to_copy` is the bf16 autocast casts, which a plain CPU run does not make; `pow` appears nowhere in this model's CPU op stream, and the extra `mul` and `mm` are what a Gemma front looks like: RMSNorm pow / mean / rsqrt / mul, and bias-free q/k/v/o/gate/up/down linears). The profile counts calls at every dispatcher nesting level, so these numbers are indications, not launch counts.

Kernel-name sanity checks of the launch table (the GPU profile's top-25 kernels by time, counts per update, against the CPU op that should launch each one for one):

| GPU kernel | GPU launches per update | CPU op at the same rounds | CPU ops per update | CPU / GPU |
|---|---|---|---|---|
| layer-norm forward kernel | 1,694 | native_layer_norm | 1,716 | 1.01 |
| memory-efficient attention forward (two tile variants listed) | 590 | sdpa_fwd | 616 | 1.04 |
| torch.cat kernel | 951 | cat | 1,034 | 1.09 |
| bf16 fill kernel (zeros / ones / new_zeros) | 2,362 | fill-type | 2,271 | 0.96 |
| indexing_backward_kernel (sort-based index_put_ accumulate) | 190 | index_put_acc | 187 | 0.98 |

The layer-norm, attention-forward, cat and fill kernels are launched about once per CPU op, as the table assumes. What the top 25 cannot confirm is the kernels around them: the bool-mask conversion and padding before the attention kernel (the table says 3 to 5 extra launches per masked SDPA forward) and the sort kernels of the scatter (6 to 9 per accumulating index_put_ in total); those two brackets are untested.

**Casts under CPU autocast** (shown for CPU's cast list; CUDA's list is longer): one micro-batch with n = 16 under `torch.autocast('cpu', bfloat16)` makes 915 dtype-changing `_to_copy` calls (57.2 per round) and changes the device kernel ops from 8,173 to 9,053 (+55.0 per round, 11 %). The GPU profile has 13,148 `aten::_to_copy` per update = 174 per round, so CUDA autocast (casts before every linear, fp32 islands for layer norm / softmax / pow, grad casts in backward, and the Gemma front's own) makes several times as many casts as CPU autocast: the CPU number is a floor.

**The real Gemma front** (untested here: only a stub runs on this box). The GPU PTC profile at accum 16 has 47,878 kernels per update for one Gemma call per micro-batch plus the small PTC transformer, so one Gemma call plus one PTC micro-batch is at most 2,992 launches; B3G2 calls the front 1.98 times per micro-batch (question and tape strings: 63.4 calls per 32 micro-batches in the accum-32 profile), so at most 23,715 launches per update (31 % of the total) can be Gemma (suggested, an upper bound only).

**Other things a CPU run cannot see** (untested): cuBLAS split-K reduce kernels, allocator zero fills, the `cuLaunchKernel` path (5,318 per update) that cutlass / flash kernels use, and any table entry that is wrong: the low-to-high bracket covers the SDPA mask conversion / pad (4 to 6 launches forward) and the sort-based scatter (6 to 9), so a wrong SDPA backend moves the estimate by a few hundred launches, not thousands (suggested).
## What this points at (suggested, untested)

- Launch count is set by rounds, not by rows: about 556 to 687 model-side launches per round (about 9,603 to 11,871 in a 17.28-round micro-batch), the same at 16 or 64 rows (C3). Bigger micro-batches change how many micro-batches (and fixed parts, and K draws) there are, not the ops per round; removing syncs removes waits, not launches.
- The single biggest op is `add` (28 % of a steady round's kernel ops), and most of it is the autograd engine adding gradients of shared weights and activations once per use per round (123 per round: thinker 50, call writer 35, answer writer 34). A change that accumulates those gradients in fewer launches (or shares fewer weights per round) removes more launches than any single forward op can (untested).
- Checkpointing adds to the per-round count: 481 kernel ops in rounds 1 to 7, 523 from round 8 (answer pass recomputed, +9 %), 557 from round 12 (thinker too, +7 %), so the checkpoint start is a launch lever as well as a memory one (untested).
- The two things this CPU run cannot count are the bf16 casts (the GPU profile has 13k `_to_copy` per update) and the Gemma front (at most 24k launches per update by the PTC bound, fixed per micro-batch): together they are about as many launches as the model-side ops. A GPU run with the profiler's per-kernel names grouped by region would settle both (untested).

## How the synthetic rows bias this

The harness's synthetic rows have 0 calls (cloze rows) or 2 calls (skills rows), so `last + 2` is about 4 to 7 and K decides n; the real pool has more calls per row: 37 % of rows have calls (GPU-RUN-1 padding section), and the GPU record's mean of 17.28 rounds per micro-batch with K drawn from (4, 8, 16, 32) needs n = max(K, last + 2) to be about 10 for the two small K, i.e. the longest program in a 64-row micro-batch is several calls long. What that changes and what it does not:

- **Per-round op counts of the writer passes: nothing**, because `call_pass` and `ans_pass` run once per round whatever the call text length (the length L only changes tensor sizes, not the number of ops). Shown by the per-round tables above (they repeat from round to round) and by the multi-call run below.

| K | n (harness rows / multi-call rows) | rounds compared | device kernel ops per round, harness rows | same, multi-call rows | change | writer share, harness rows | writer share, multi-call rows | CPU teacher ops per round, multi-call rows |
|---|---|---|---|---|---|---|---|---|
| 16 | 16 / 24 | 3 to 14 | 513.5 | 521.1 | +1.5 % | 48.1 % | 47.5 % | 622 |
| 32 | 32 / 32 | 3 to 30 | 538.4 | 544.1 | +1.1 % | 48.0 % | 47.6 % | 350 |

- **Subset indexing: about +11 kernel ops per round (2 %) in the rounds where some rows are still "inside" their program.** While round <= the longest call round the loop and `_loss` select rows (`pk(x) = x[si]`: four index ops per round for the answer pass, one `torch.tensor(sel)` and the call-pass rows). Device kernel ops of rounds 0 to 11 on the multi-call rows at K = 16: 321, 485, 485, 485, 485, 481, 485, 485, 530, 534, 534, 534; on the harness rows: 321, 485, 485, 485, 485, 481, 474, 474, 523, 523, 523, 523.
- **Writer share: -0.6, -0.4 points on the multi-call rows** (the extra ops are index ops of the loop and the loss tail, not writer ops), so the harness rows slightly overstate the writer share against a pool with more calls per row; that is a shift of under one point against a 45 to 51 % share and does not change any verdict. The multi-call rows are a stress case (their longest program with gaps needs 24 rounds at K = 16, while the GPU profile's own K = 4 draw ran only 7 rounds, see the estimate section), so this is an upper bound on the effect.
- **The CPU-tensor teacher: a lot more host work**, because `ByteWriter.teacher` loops over rows and bytes in python (about 8 CPU ops per byte of a row with a call text); that is host time (no launch), and it grows with the calls per row and with the rows. Its share of the dispatched ops is large here (the teacher is 49 % to 65 % of all dispatched ops of the natural updates, views included) and it is not part of any launch figure.
- **The tape**: K = the longest call list in the micro-batch sets the tape width (K x le), so the thinker's keys and values per round are longer with the real pool; that is tensor size, not op count.
## Does the instrument itself hold?

- Region coverage (shown): 100.000 % of 514,632 kernel ops over all runs have a region other than 'other' (brief: >= 99 %).
- Backward attribution (shown): 100.000 % of 100,682 backward + recompute kernel ops (the engine's own additions excepted) carry the region of a forward op (brief: >= 95 %); 0 of 126,049 autograd nodes reachable from the losses were not found by the forward tagger. The engine's own additions are 37.2 % of all backward + recompute kernel ops and are filed under grad_accumulate, by design not a forward region; of those, 97.5 % are additions of a gradient that a named forward region's backward produced (tagged with that region), 2.5 % are the parameters' own AccumulateGrad, 0.1 % have no producer.
- Thinker recompute round check (shown): the round the think wrapper saw agrees with the round of the node that asked for the recompute in 29,014 ops, disagrees in 0.
- Counts identical across two runs, the sync wrapper restoring torch exactly, and the instrument leaving loss and weights bit-identical are unit tests (`test_attrib.py`, 17 tests, all pass).
- Determinism at the real shape (shown): 5 of 5 natural updates counted in a second, separate process (an earlier revision of the engine tagging, so op names are compared without the producer suffix) give identical micro-batch tallies, cell for cell (838,749 ops).
- Out-of-sample check of the per-round model (shown): the fixed part plus per-round totals of the n = 32 reference run predict the device kernel ops of 5 complete natural update(s) to within 0.6 % (their row mixes, plan and gap draws are not the reference's).
## Not claimed

- No CUDA time, no CUDA launch, no real profiler: the launch numbers are an ATen-op-to-launch table applied to a CPU op stream. The 75,966 figure is the GPU-RUN-3 profile's, not mine.
- The real Gemma front and the real row pool were not available. The stub front's ops are excluded from every launch figure; the real front is bounded from above only.
- bf16 autocast on CUDA was not reproduced; CPU autocast has a different cast list. The cast counts are a floor.
- One seed (400), one synthetic row set (plus one multi-call set), one 3M shape. The K draws of the natural updates are whatever seed 400 gave after a warm-up update; the 17.28-round population mean is the GPU record's, not recomputed here.
- Why CUDA waits at b3g2.py:375 / :376 (index_put with two tensor indices) is not explained; the call counts are shown, the wait is taken from the GPU record.
- Host python time of the teacher loops was not measured on a device-attached run.
