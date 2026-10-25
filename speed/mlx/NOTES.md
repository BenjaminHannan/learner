# speed/mlx: Mac sleep-training speed (chunked Gated DeltaNet, loss-position-only logits)
Labels: SHOWN = measured here (CPU, tiny); SUGGESTED = reasoned from shapes/earlier bonsai numbers; UNTESTED = needs the Mac GPU.
Everything is opt-in; nothing here is imported by running jobs. Container: mlx 0.32.4 + mlx-lm 0.32.2 CPU wheels (`pip install "mlx[cpu]" mlx-lm`).

## Files
- chunked_gated_delta.py   copy of bonsai's chunked rule (origin/claude/project-thread-e51zyw) + `compile=` (mx.compile of the chunk-prep and scan step) + `patch_mlx_lm(chunk, compile)` (patches mlx_lm's module-global `gated_delta_ops`, so qwen3_5 / qwen3_next training, `use_kernel=not self.training`, takes the chunked path; inference keeps the Metal kernel). bonsai's mlx_vlm patch is still in the file.
- bench_gdn.py             per-layer fwd+bwd, per-token vs chunk 32/64/128 vs chunk64/128+compile. Shapes from HF configs: 35B-A3B Hk16 Hv32 Dk128 Dv128 (30 GDN layers of 40); 2B Hk16 Hv16 Dk128 Dv128 (18 of 24). Prints JSON rows: ms (median), peak_gb (mx.get_peak_memory), rel_y/rel_grad_max vs per-token, speedup_vs_ref; plus an fp32 T=200 match check (padding path).
- loss_logits.py           `make_loss(chunk_rows=None)` for `mlx_lm.tuner.trainer.train(loss=...)`; body -> gather hidden at mask positions -> lm_head only there. `chunk_rows=N` also checkpoints the head+CE per N rows so [rows,V] is never kept. Custom body/head/head_owner for softcap or non-llama models.
- bench_loss.py            stock vs gather vs gather+chunk, K2-3.7B shapes (36L, 2560, mlp 10240, 32/8 heads, V=250,624, LoRA r8 all layers, bf16).
- test_loss_logits.py, test_patch.py   CPU correctness.

## Measured here (CPU, so not representative of Mac GPU timing)
- test_loss_logits.py: SHOWN loss and all grads identical to stock default_loss (rel err 0 to 1.5e-7; tied and untied head; padded `lengths`; chunk_rows=4). 
- test_patch.py: SHOWN y and dq/dk/dv through gated_delta_update(use_kernel=False) match unpatched within 6e-6 (fp32).
- bench_gdn.py --quick (2B shape, T=256, B=1, fp32 match): SHOWN chunk 32/64/128 and compile variants match per-token to <=2.6e-6 (y and all 5 grads). bf16 timing run: rel diff vs per-token 1e-3 y / 5e-3 grad, identical for every chunk size, i.e. bf16 rounding of the reference, not chunk error.
  CPU timing T=256: per-token 2122 ms, 0.55 GB; chunk32 1190 ms, 0.088 GB; chunk64 1898 ms, 0.082 GB; chunk128 5876 ms; compile no help on CPU. Peak memory 6-7x lower SHOWN; CPU speed order is meaningless for the GPU (chunk128 is slow because the (I+A)^-1 matmul chain grows with C).
- bench_loss.py --quick (tiny llama, V=5000, 25% target positions): SHOWN stock 292 ms / 13 MB vs gather 175 ms / 5.6 MB, loss and grads identical. K2-size CPU run is not feasible: MLX Linux CPU matmul against a 250k x 512 head took 92 s.

## Needs the Mac (UNTESTED)
Check first: `ls ~/learner-ops/PAUSE_OTHERS ~/learner-ops/ASSISTANT_RUNNING` (both scripts exit by themselves if present). Run one at a time; they use up to ~7.4 GB (loss bench) and up to ~14 GB (GDN ref path; per-token rows over REF_MEM_CAP_GB=14 are skipped, override with env).
```
cd ~/learner && pip install -U mlx mlx-lm      # mlx >=0.32
python speed/mlx/test_loss_logits.py && python speed/mlx/test_patch.py                       # seconds
python speed/mlx/bench_gdn.py --quick                                                        # smoke, <1 min on GPU
python speed/mlx/bench_gdn.py --out speed/mlx/results-gdn.json                               # full grid, 35b+2b, T 512/1024/2048, B 1/2/4 (long: per-token T=2048 rows are the slow ones; add --seq 512,1024 --batch 1,2 to cut)
python speed/mlx/bench_loss.py --out speed/mlx/results-loss.json
```
Wire in (training script, before building the model/trainer): `from chunked_gated_delta import patch_mlx_lm; patch_mlx_lm(chunk=<best>)` and `train(..., loss=make_loss(chunk_rows=4096))`. Pass marks to fix before trusting: GDN rel_y <= 1e-2 and rel_grad_max <= 3e-2 in bf16 (fp32 check <= 1e-4/1e-3, already met on CPU); loss rel diff <= 1e-5 and grad rel <= 1e-3 in bf16; then a 5-step Qwen3.5-2B LoRA run (bonsai/lora_smoke.py) must show s/step below the 46 s baseline and loss curves overlapping stock for the same seed. Disproved if chunked is not faster than per-token at T=1024, B=1 on the GPU, or peak memory not lower.

## Expected wins
- GDN memory: SHOWN 6-7x lower on CPU at T=256; bonsai measured 12.6x lower at longer T (saved states scale with T/chunk). Per-token saved state at 35B shapes is Hv*Dv*Dk*4 B = 2 MiB per token per layer per batch row, so T=2048, B=1 is ~4 GiB per layer before checkpointing: SUGGESTED this is why batches >1 are impossible today.
- GDN speed on GPU: SUGGESTED 2-5x per GDN layer (bonsai 2.3x on CPU; GPU gains from far fewer sequential kernel launches, 2048 steps -> T/chunk steps). UNTESTED. The 46 s/step -> target is 10-20 s/step, UNTESTED. Best chunk is probably 32 or 64 (larger chunks lengthen the inverse chain); the grid decides.
- Logits: stock fp32 CE temp for B=4, T=2048, V=250,624 is 8192 x 250,624 x 4 B = 8.2 GB per copy (logits + softmax/grad temps ~2-3 copies). SUGGESTED gather removes it in proportion to the prompt share (frac 0.25 -> 4x less). Head is ~1.3 GFLOP/token fwd vs ~4.8 for the 36-layer body (body non-embedding params ~2.4B, estimate), so ~21% of forward FLOPs; with 25% target tokens SUGGESTED ~15% of step FLOPs saved (frozen head: bwd only dX), more if memory pressure currently forces smaller batches. UNTESTED on GPU.
- mx.compile on chunk body: UNTESTED; no gain on CPU, may help GPU by fusing the many small elementwise ops.

## Caveats
- make_loss does one tiny host sync (mask -> indices); shapes are dynamic so mx.compile of the whole loss will not work (stock default_loss neither is compiled by mlx-lm).
- K2-Horizon is a remote-code HF class; make_loss assumes `.model(inputs)` returns final-normed hidden and `.lm_head` exists (true for mlx-lm llama; K2's MLX loading path is not checked here). If K2 has a logit softcap, pass `head=`/`head_owner=`.
- Chunked rule falls back to the per-token loop for vector g (GDN with per-dim gate, e.g. Kimi-style); Qwen3.5/3.6 use scalar g.
- Not verified here: whether sleepb.py uses MLX or torch for the Mac path; I did not edit it.

## MEASURED on Ben's M1 Pro GPU (2026-10-25 ~17:50Z, mlx 0.32.4, mlx-lm 0.32.2, ~/learner-ops/swap1/venv; raw JSON on the Mac in ~/learner-ops/speed/results/)
Tests: test_loss_logits 4/4 pass (grad rel <= 2e-7); test_patch rel <= 8.4e-6; fp32 chunked vs per-token <= 2.6e-6; bf16 rel_y <= 3.8e-3, rel_grad <= 1.0e-2 (pass marks 1e-2 / 3e-2 met).
GDN fwd+bwd per layer, per-token ms (GB) -> best chunked ms (GB):
- 35B shapes: T512 B1 590 (2.44) -> c64+compile 30.6 (0.92) 19x; T1024 B1 1542 (4.78) -> 76.2 (1.56) 20x; T1024 B2 2916 (9.66) -> 150 (1.70) 19x; T2048 B1 4546 (9.69) -> c128+compile 194 (1.82) 23x; T2048 B2 per-token too big (yellow pressure) -> c128+compile 335 (3.30).
- 2B shapes: T512 B1 333 -> 16.5 20x; T1024 B1 854 -> 40.5 21x; T2048 B1 2081 -> c128+compile 84.9 25x; T2048 B2 4253 (9.76) -> c128 168 (2.07) 25x.
Best chunk: 64 for T<=1024, 128 at T=2048; chunk 32 always slowest; mx.compile 0-5%.
Loss bench (K2 shapes V=250,624, LoRA r8, bf16, B=1, body cut to 12 layers): stock vs gather T1024 2590 ms (4.13 GB) -> 2039 (3.72) 21%; T2048 5453 (7.49) -> 4222 (6.15) 23%; loss/grad rel diff 0.0. Full 36-layer body: suggested ~15%.
