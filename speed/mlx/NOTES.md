# speed/mlx: Mac sleep-training speed (chunked Gated DeltaNet, loss-position-only logits)
Labels: SHOWN = measured here (CPU, tiny); SUGGESTED = reasoned from shapes/earlier bonsai numbers; UNTESTED = needs the Mac GPU.
Everything is opt-in; nothing here is imported by running jobs. Container: mlx 0.32.4 + mlx-lm 0.32.2 CPU wheels (`pip install "mlx[cpu]" mlx-lm`).

## Files
- chunked_gated_delta.py   copy of bonsai's chunked rule (origin/claude/project-thread-e51zyw) + `compile=` (mx.compile of the chunk-prep and scan step) + `patch_mlx_lm(chunk, compile)` (patches mlx_lm's module-global `gated_delta_ops`, so qwen3_5 / qwen3_next training, `use_kernel=not self.training`, takes the chunked path; inference keeps the Metal kernel). bonsai's mlx_vlm patch is still in the file.
- bench_gdn.py             per-layer fwd+bwd, per-token vs chunk 32/64/128 vs chunk64/128+compile. Shapes from HF configs: 35B-A3B Hk16 Hv32 Dk128 Dv128 (30 GDN layers of 40); 2B Hk16 Hv16 Dk128 Dv128 (18 of 24). Prints JSON rows: ms (median), peak_gb (mx.get_peak_memory), rel_y/rel_grad_max vs per-token, speedup_vs_ref; plus an fp32 T=200 match check (padding path).
- loss_logits.py           `make_loss(chunk_rows=None)` for `mlx_lm.tuner.trainer.train(loss=...)`; body -> gather hidden at mask positions -> lm_head only there. `chunk_rows=N` also checkpoints the head+CE per N rows so [rows,V] is never kept. Custom body/head/head_owner for softcap or non-llama models.
- bench_loss.py            stock vs gather vs gather+chunk, K2-3.7B shapes (36L, 2560, mlp 10240, 32/8 heads, V=250,624, LoRA r8 all layers, bf16).
- test_loss_logits.py, test_patch.py   CPU correctness. test_patch.py also runs the REAL-input and STRESS regression guard (see Bug and fix).
- gdn_cases.py, capture_real_gdn.py, realgdn_inputs.npz, check_e2e.py   real-layer inputs (Qwen3.5-2B layers 6 and 17, T=256, 11.8 MB), the capture script that regenerates all 18 layers, synthetic stress cases, and the Mac end-to-end check.

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

## CORRECTION (Mac, 17:58Z, real Qwen3.5-2B 4-bit weights): the per-layer numbers above used random inputs and HIDE a bug.
Step-1 loss, T=256: stock 4.22342; chunked c8 4.22330, c16 4.21994, c32 4.24422, c64 4.30290; c64 training NaN from step 2. Only chunk 8 is safe today.
End-to-end 5-step LoRA (r8 all linears, B1, T256): stock 3.01 s/step, 11.97 GB peak; chunk 8 + make_loss 1.13 s/step, 3.45 GB (2.65x faster, 3.5x less memory, losses overlap); stock cannot run T>=512 on this Mac (memory critical); chunk 8 at T=1024 5.65 s/step, 10.3 GB, losses finite and falling.

## Bug and fix: chunk >= 32 gave wrong loss, chunk 64 went NaN (found and fixed 2026-10-25, CPU, mlx 0.32.4)
Labels: SHOWN = measured here on CPU with real Qwen3.5-2B layer inputs; SUGGESTED = reasoning; UNTESTED = needs the Mac.

**Root cause (SHOWN): hypothesis 2, the triangular inverse.** `_unit_lower_inv` computed (I+A)^-1 as (I-A)(I+A^2)(I+A^4)... This is exact on paper, but the powers A^(2^m) of the intra-chunk key-overlap matrix (A = beta * decay * k_i.k_j, strictly lower) grow like binomial(C, 2^m) when keys are correlated (cos ~ 0.9-1, beta ~ 1; entries 1e18 at C=64) and the terms cancel to O(1). fp32 has 7 digits, so the result is garbage that grows with chunk size: fine at C=8, wrong at 32, NaN/1e36 at 64. Real keys are correlated enough (several layers, e.g. 6 and 17); random-normal keys are near-orthogonal, so A^k stays small and the old tests passed at 2.6e-6. The block-recursive inverse Ben tried still builds the result from products of big blocks, so it only reduced the error.
Ruled out (SHOWN, exact fp32 match at every chunk once the inverse is fixed): (1) gate handling (only exp(b_i - b_j), j<=i, is exponentiated; exp(b) and exp(b_C-b_i) are <= 1; g=0 handled by the 1e-30 clamp), (3) bf16 (everything is cast to fp32 inside the op; with the fix chunked-on-bf16-inputs error equals the per-token path's own bf16-vs-fp32 error, to every printed digit), (4) l2norm/scale/beta/g preprocessing (done by mlx_lm before the op; the captured inputs are what gated_delta_ops receives), (5) padding masks (the T=200 padded case still matches).

**Fix:** `_unit_lower_inv` is now blocked forward substitution in fp32 (what FLA's solve_tril does): row-by-row inside 16x16 diagonal blocks (16 steps, batched over C/16 blocks), then C/16 block rows T_I = D_I (E_I - A[I,:I] T_<I). Substitution only combines earlier rows of T, and for beta in [0,2] those stay O(1). Matmul/slice ops only (no CPU-stream solve), analytic VJP (dA = -T^T dT T^T, tril) via mx.custom_function, `INV_BLOCK=16` tunable, works with compile=True and any chunk (non-multiples of 16 use the largest divisor). `patch_mlx_lm(chunk, compile)` API unchanged.

**Errors vs per-token mlx_lm reference, same inputs, T=256 (SHOWN).** rel = max|diff|/max|ref|; "grad" = worst of dq,dk,dv,dg*g,dbeta (dg is compared as g*dg, which is what reaches A_log/dt_bias; raw dg at g~1e-20 is noise).
Real layer 6 (fp32 inputs), y / grad:
| chunk | old | new |
|---|---|---|
| 8 | 7e-7 / 5e-6 | 8e-7 / 5e-6 |
| 16 | 1e-5 / 7e-5 | 6e-7 / 7e-6 |
| 32 | 4e+2 / 7e+3 | 7e-7 / 7e-6 |
| 64 | 2e+36 / 7e+34 NaN | 7e-7 / 4e-6 |
| 128 | NaN | 6e-7 / 6e-6 |
Real layer 17: old 64 = 1.8e36 (NaN in bf16 grads), new 64 = 6e-7 / 3e-6. Layer 11: old 64 = 8e-3 / 2e-3, new 8e-7 / 4e-6. Layer 0 (benign): old 64 = 4e-7, old 128 = 7e-5 / 7e-4, new all <= 5e-7 / 7e-6.
bf16 inputs (real layers 0/6/11/17): per-token's own bf16-vs-fp32 floor is y 4e-3/2.8e-2/5e-2/7e-3 (grad 1.4e-2/6.4e-2/4.6e-2/2.6e-2); new chunk 8..128 equals the floor exactly (ratio 1.0, mark was <= 2x); old chunk 32 (L6, L17) and 64 are 1e3..1e37 off.
Stress (cos 0.9/0.99 keys, beta 1 and 2, alternating-sign keys, g ~ 0 with exact zeros, g ~ 1): old at chunk 64 = 5e3, 5e8, NaN, 3e6, 1e-6 (g-strong, ok), NaN; new at chunk 8..128 all y <= 2.6e-6, grads <= 1e-5 (g-strong dg*g 4e-5, independent of chunk).
Regression guard: `python speed/mlx/test_patch.py` runs 8 cases (6 stress + real L6, L17) x chunk 16/32/64/128 x fp32/bf16 = 32 checks; fp32 marks y <= 1e-4, grads <= 3e-4; bf16 <= 2x the per-token floor. New code 32/32 pass; old code 10/32 (SHOWN, same test against the old file). `bench_gdn.py` runs the same cases (`hard_cases` in its JSON) before timing. `REALGDN_NPZ=/path/realgdn_all.npz` tests all 18 layers (`python speed/mlx/capture_real_gdn.py` regenerates it from the unquantized Qwen/Qwen3.5-2B in ~9 min on CPU; the 4-bit CPU path is unusably slow here).

**CPU timing, fwd+bwd, 2B shapes (Hk16 Hv16 D128), fp32, relative only (SHOWN; Mac GPU timing UNTESTED):**
| T / chunk | old ms | new ms |
|---|---|---|
| 256 / 16 | 1170 | 1148 |
| 256 / 32 | 1220 | 1127 |
| 256 / 64 | 1866 | 1393 |
| 256 / 128 | 6011 | 2043 |
| 1024 / 32 | 5502 | 4923 |
| 1024 / 64 | 8300 | 6014 |
| 1024 / 128 | 25238 | 8858 |
The fix is not slower: at C=64 it is ~25% faster on CPU, at 128 about 3x (the old chain of C-sized matrix squarings is gone). SUGGESTED on GPU: ~20 extra tiny sequential steps per layer, not per chunk (they are batched over all chunks and heads), so little change; the Mac grid must re-pick the best chunk. The earlier Mac table above measured the broken code, so its speedups need a re-run (the per-token side is unchanged).

**End-to-end CPU (SHOWN):** full Qwen3.5-2B (unquantized weights cast to fp32; CPU cannot run the 4-bit path in useful time), real text, T=256, training mode, step-1 forward loss: stock per-token 3.512183, old chunk 64 3.637056 (+3.6%, the same bug Ben saw: +1.9% on his text), new chunk 64 3.512183 (rel diff 1.4e-7). Each full forward takes ~11 min on this CPU, so new chunk 32/128 and the 5-step run were not repeated end to end; `check_e2e.py --tiny` (random 4-layer model, T=128, 3 steps) gives step-1 and per-step loss rel diff <= 2.3e-7.

**Mac re-check for the lead (UNTESTED; ~5 min, run alone, check PAUSE_OTHERS / ASSISTANT_RUNNING first):**
```
cd ~/learner && python speed/mlx/test_patch.py        # expect: hard cases: 32 / 32 pass
python speed/mlx/check_e2e.py --model mlx-community/Qwen3.5-2B-4bit --T 256 --chunks 8,16,32,64,128 --train-chunk 64 --steps 5
```
Pass marks fixed in advance: step-1 forward loss of chunk 64 within 1e-4 relative of stock (Ben's stock value 4.22342 at his text; chunk 64 must print 4.2234 +/- 0.0004, not 4.30290), no NaN, and the 5 per-step losses of chunk 64 within 1e-3 relative of stock at every step (printed as `step_rel_diff`; exit code 0 and `pass` all true). Disproved if chunk 64 still differs by more than 1e-4 at step 1 or goes NaN at step 2 or at T=1024 (also run with `--T 1024`). `check_e2e.py --tiny` is the CPU smoke test of the script itself.

## Mac re-check of the fix (19:37-19:41Z, M1 Pro GPU, local Qwen3.5-2B 4-bit, LoRA r8, B1)
test_patch.py 32/32 pass on GPU. Step-1 loss T=256: stock 4.82224; c8 4.82576 (7.3e-4), c16 4.82438, c32 4.82192 (6.6e-5), c64 4.82195 (6.0e-5, PASS <=1e-4), c128 4.82323 (2.1e-4).
5 steps T=256: stock 4.8255 2.8348 1.0347 0.2347 0.1336 | 3.0 s/step | 13.23 GB; c64 4.8277 2.8406 1.0315 0.2360 0.0956 | 1.03 s/step | 3.91 GB (2.9x faster, 3.4x less memory).
The preregistered <=1e-3 per-step mark FAILED (steps 2-4 off up to 3e-3, step 5 by 0.28 abs... of a collapsing loss). But stock vs stock with the same init and batch also differs (4.8255 2.8332 1.0314 0.2353 0.1192; step 5 0.119-0.141 over 3 runs): the Mac GPU path is nondeterministic, and the mark was below the noise floor. Suggested: chunk 64 is within stock's own run-to-run spread; a deterministic check needs fp32/CPU or many seeds.
T=1024 (stock can't fit): c8 6.4 s/step 13.45 GB; c64 4.25 s/step 11.79 GB; c128 4.15 s/step 12.17 GB; all finite, step 1 agrees to ~2e-4.
Recommendation: patch_mlx_lm(chunk=64) + make_loss().
