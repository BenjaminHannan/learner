# qwen36_mem: exact packed 4-bit storage of the frozen q4 base

Labels: **shown** = measured here (CPU, tiny model, test_packed.py) or read from a log; **suggested** = arithmetic / reasoning, not run; **untested** = needs the GPU.

## What it is
sleepb `--q4-base --q4-mlx-moe` computes w' = (q*scale + bias).to(bf16) per group of 64 and keeps w' in bf16 (64.6 GiB). `packed.py` keeps (q, scale, bias) instead: uint8 codes (two 4-bit codes per byte),
bf16 scale, bf16 bias = 0.5625 B/param, and rebuilds w' just in time with the same fp32 ops as `sleepb.q4_fake`. Opt-in: nothing imports it; sleepb is untouched. To use it, call
`packed.pack_model(lm)` where `q4_apply` is called (after load, before peft).

* Routed experts (80 fused 3-D tensors, 32.2 B params): `install_experts` deletes the Parameters, adds `gate_up_packed` / `down_packed`, and sets an instance `forward` = a copy of transformers 5.20.2
  `grouped_mm_experts_forward` whose two grouped matmuls are `_PackedGroupedMM`. (It always takes the grouped_mm path; `set_experts_implementation` no longer affects these modules.)
* `_PackedGroupedMM` (autograd.Function): forward dequantizes one layer's tensor (1 GiB gate_up + 0.5 GiB down at real size), runs `_grouped_mm`, frees it; backward dequantizes again and returns only
  grad_x = grouped_mm(g, W). Nothing dense is saved. Under HF gradient checkpointing the dequant happens a third time (recompute).
* Linears with >= 1M elements and no bias (GDN projections, attention, shared expert, lm_head): `PackedLinear` (class swap of the nn.Linear, so peft still targets it and puts LoRA on top) with the same
  trick (`_PackedLinearFn`). Smaller Linears, Embedding, routers, shared_expert_gate: qdq'd in place and left dense, via the same pack/unpack (equal to q4_apply, tested).
* `pack_model(lm, device=cuda)` with lm still on CPU packs layer by layer on the GPU, so a 32 GB card never holds the bf16 model (bench mode `packed_fit`). Loading to CPU needs ~65 GiB host RAM.

Why exact: scale and bias are stored in the weight dtype exactly as q4_fake rounds them; q <= 255 and a bf16 scale have <= 16 significant bits, so q*scale is exact in fp32 and a fused multiply-add
(torch.compile / Triton) gives the same bits as separate mul + add. The one case that is not stored exactly: a group whose bf16 scale underflows to 0 (q4_fake substitutes fp32 1e-8); needs a range < 1e-37, never seen.

## Shown (CPU, `python speed/qwen36_mem/test_packed.py`, torch 2.14.1+cpu, transformers 5.20.2, peft 0.21.2; tiny Qwen3_5Moe from the real config: 4 layers, hidden 256, 8 experts, bf16)
* pack/unpack == `sleepb.q4_fake`, bitwise, 12 cases (bf16/fp32, 4/8 bit, 2-D/3-D, one-piece and sliced, constant group, 1e-30 values).
* All 72 weights (8 packed experts, 32 packed Linears, 32 dense leftovers) bitwise equal to the `q4_apply` copy.
* Logits max abs diff 0.0 (scale 1.46); loss identical (6.333639); 62 LoRA grad tensors (LoRA on attention, GDN, shared expert, including layer 0, so grads cross every packed experts layer) max abs diff 0.0
  (grad scale 0.039). No-grad logits equal. torch.compile'd unpack equal (CPU).
* Autograd-saved tensors in one forward: qdq model saves 6.3 MB of dense expert weights (of 29.5 MB total); packed model saves 0 (20.5 MB total).
* Parameter bytes of the tiny model 9.75 MB -> 2.96 MB (the tiny vocab is a large dense share; real ratio below).
* The CPU grouped_mm of torch 2.14 differs from the GPU kernel, so "0.0" here is shown for CPU only; on GPU grad_x comes from the same grouped_mm call as autograd's own backward, so expect 0 or float-order. Untested.

* `bench_mem.py --tiny` (CPU smoke of the script, fp32 random tiny model with the real 248k vocab, 1 step each): both modes ran, plain and checkpointed; probe logits bitwise equal qdq vs packed; packed 1.06-1.08x slower on CPU (eager dequant, meaningless for GPU). packed_fit and memory fields need CUDA.

## Expected GPU memory (suggested: arithmetic on the bench log numbers; untested)
Real model, GiB: experts 32.2123 B * 0.5625 B = 16.9; packed Linears (GDN 1.0106 B + full attn 0.2726 + shared expert 0.1258 + lm_head 0.5086 = 1.92 B) = 1.0; dense left: embed_tokens 0.95, routers + gates + conv1d 0.05.
Weights ~18.9 GiB vs 64.56 (saves ~45.7). Transient: one layer dequantized, ~1.5 GiB bf16 (+ <1 GiB fp32 temporaries from the 64M-element slices).
From the A11 log (Trainer, peak 83.7 GiB at tok 2048 plain, 67.3 with checkpointing at 4096), non-weight memory is ~19 GiB plain at 2048 and ~2.7 GiB with checkpointing at 4096:
* tok 2048 plain: ~84 - 45.7 + ~2 = ~40 GiB -> fits a 48 GB card. * tok 4096 + checkpointing: ~67 - 45.7 + 2 = ~24 GiB -> fits a 32 GB 5090 (31.4 GiB usable) with ~7 GiB spare.
* On the 95 GB card plain activations grow ~linearly with tokens (~19 GiB per 2048 tokens plain, assumption): 4096 plain ~60 GiB, 8192 plain ~98 GiB (no), 8192 + checkpointing ~ (2.7 GiB per 4096) < 35 GiB, so 8192 and 16384 fit with checkpointing. bench_mem.py measures this.
* Generation (KV, 128 prompts) was 82 GiB peak at gen_bs 128 with bf16 base; packed base would leave ~45 GiB more room, but see the decode cost below.

## Dequant time (suggested: bytes / bandwidth; untested)
One full-model dequant pass (all 80 experts tensors + packed Linears, 34.1 B params): eager `unpack` is ~8 elementwise passes (&15, >>4, stack, float, *, +, .to) ~ 30 B moved per param ~ 1.0 TB -> ~0.65 s at ~1.6 TB/s: too slow.
Fused (`--compile-dequant`, one kernel: read 0.5625 B + write 2 B per param = 2.56 B) = 87 GB -> ~55 ms per pass at 1.6 TB/s (PRO 6000 GDDR7 peak 1.79 TB/s). The grouped_mm then reads the 2 B/param bf16 weights as it does today.
Passes per micro-batch: forward 1, backward 1, +1 with gradient checkpointing; the KL-guard replay forward adds 1 per replay micro-batch. Fixed per micro-batch, not per token, so it is amortized by larger micro-batches:
a step with ~3 forwards + 2 backwards costs ~5 * 55 = ~0.3 s fused (vs 1.7 s/step at tok 2048 today: ~+15%), ~3 s eager. If the memory cut lets tok_budget go 2048 -> 8192 (4x fewer passes per token) the net is expected faster, not slower. Decision rule for the lead: run bench_mem.py and compare `compare[...].slowdown`.
Generation: every decode step dequantizes every layer (+55 ms fused vs 70 ms/step measured at batch 32), so generation should keep the dense qdq base; packed is for the training phase only (the two cannot both live on one 95 GB card:
swap by re-running pack_model / reload between phases, or run training as a separate process). Not implemented.

## Not done / next
* GPU run: `python speed/qwen36_mem/bench_mem.py --out speed/qwen36_mem/bench_mem.json` (add `--compile-dequant` for the fused path; run both). Check `logits_bitwise_equal_to_qdq`, `compare`, `modes.packed_fit.fits_5090`.
* If eager is too slow and torch.compile misbehaves, a Triton unpack kernel (explicit mul.rn/add.rn not needed given the exactness argument above) is the next step.
* Embedding (0.95 GiB) could be packed with a row-gather dequant; not worth the code yet.
* Gradient checkpointing + packed experts is exercised only in bench_mem (the CPU test runs without it).

## Running a real Sleep-B arm packed: run_sleepb_packed.py
Opt-in wrapper, sleepb.py untouched. It wraps `sleepb.load_model` (loads on CPU when CUDA is the target and `--q4-base --q4-mlx-moe` are set; needs ~70 GB host RAM), `sleepb.q4_apply` (first call: `packed.pack_model(device=cuda)` layer by layer
instead of the bf16 qdq, then the rest moves to the GPU), `Trainer.step` (`--grad-ckpt`: HF checkpointing, use_reentrant=False, on only in `pm.train()`, so dreaming/eval generation and use_cache are unchanged), and logs peak CUDA memory per phase (load+pack, dream, train, eval).
Command for a 32 GB 5090 arm (everything after `--` is sleepb's own CLI, so other flags such as `--habit spot` pass through):

    python speed/qwen36_mem/run_sleepb_packed.py --packed-compile --grad-ckpt --kl-cache -- --arm ab_ob_b4_nb --week WEEK.json --out OUT --q4-base --q4-mlx-moe

Flags: `--packed-compile` (fused dequant; measured 2.1-2.5x slower per step than the qdq base, eager is worse), `--grad-ckpt`, `--kl-cache` (fast_step KL-reference cache), `--packed-min-numel` (tests only). Needs `--q4-base --q4-mlx-moe --q4-bits 4`.
* Shown (CPU, `python speed/qwen36_mem/test_run_sleepb_packed.py`, tiny fp32 Qwen3.5-MoE, 8 packed expert tensors + 32 packed Linears): Trainer.step loss/KL abs diff 0.0, 62 LoRA grads max abs diff 5.6e-9 (grad scale 0.06), packed+ckpt vs plain qdq; greedy generation after
  checkpointed steps equals plain; a whole `--arm ab_ob_b4_nb --smoke --q4-base --q4-mlx-moe` run through the runner (2 nights, dreams, eval) completes with scores identical to the plain run.
* Measured on the box earlier (RESULTS-box1.md): packed weights 18.9 GiB; train-step peak 22.1 GiB at tok 2048 with checkpointing, 23.3 at 8192.
* Untested: whole-arm peak on a real 32 GB card (dream generation at gen_bs 128 with packed weights, KV cache + dequant transients, eval), host-RAM load of the 35B on CPU, `--packed-compile` + checkpointing together on GPU, DELTA_ARMS (they edit `base_layer.weight`, which PackedLinear lacks).
  Generation dequantizes every layer per decode step; if dreaming is too slow or tight, lower `--gen-bs`.

## 3-bit base (Oct 27): `--q4-bits 3` (NexVeridian recipe: affine 3-bit g64, 8-bit mlp.gate / shared_expert_gate)
- packed.py packs 3-bit codes for real: 8 codes in 3 bytes (code j at bit 3j of a little-endian 24-bit word). The runner accepts `--q4-bits 3` or 4.
- Shown on CPU: pack/unpack bitwise equal to sleepb.q4_fake at 3 bits (test_packed pack_math), every weight of the tiny model bit-identical to sleepb.q4_apply(bits=3); `--smoke` ab_ob_b4_nb run through the runner at 3 bits matches plain sleepb (floats within 1e-6 rel; two plain CPU runs differ from each other by ~1e-9, so the e2e compare now uses that tolerance).
- Estimate (untested): Qwen3.6-35B-A3B packed weights ~14.7 GiB at 3 bits vs 18.9 GiB at 4 bits (3.5 vs 4.5 bits/weight incl. bf16 scale+bias per 64).
