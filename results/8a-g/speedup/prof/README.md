# prof_train.py: where does the training time go, and which speedups keep the maths?

One file, `prof_train.py`, replays `custom_io/train.py`'s update loop (bf16 autocast, fused AdamW, `split_batch` -> `loss/len(parts)` -> backward per micro-batch, `clip_grad_norm_(1.0)`, step) at the real rung shape on the real pool, and measures it. Nothing under `custom_io` is edited; every variant is a wrapper or monkeypatch made inside `prof_train.py`. `test_prof.py` is the CPU test (about 14 s). It was written with no GPU: **no CUDA number in this folder has been produced yet.** The fixed pass marks for the same-maths speedups are in `../PREREG-eg-once.md` (written before any GPU number; this file implements them as E1-E4 and never changes them).

## Run it (RTX 4090, nothing else on the GPU)

```
export CUSTOM_IO_EG2=/path/to/eg2            # the EmbeddingGemma-2 folder; else the hub revision in models/eg.py (EG_REV) is downloaded
export PYTHONPATH=/path/to/eg_site:$PYTHONPATH   # transformers >= 5.19, as in the PC queue files (# ENV PYTHONPATH= ... # ENV CUSTOM_IO_EG2= ...)
POOL=$WORK/pools/<key>                       # the real pool dir: must contain train.jsonl (and charvocab.json if the job has one)
C="--arm PTC --rung 3M --accum 16 --data $POOL --pkg-root $J/src-ptc"      # PTC / PTS at 3M, accum 16 (PTC needs the PTC overlay tree)
# B3G2 at 3M, accum 32:  C="--arm B3G2 --rung 3M --accum 32 --data $POOL --pkg-root $J/src-b3g2"   (add --caps <the job's caps_b3g2.json> if it is not the package's)

python prof_train.py $C --out out/profile.json          # breakdown, throughput, profiler, padding, sweep, syncs
```

`--pkg-root` is the folder that CONTAINS `custom_io/`. Each run writes `out/X.json`, `out/X.md` and (after the profiler section) `out/X.profiler.json` / `.profiler.md`, updated after every section; a failed section is recorded, never fatal; every table says arm, rung, accum, batch, device, torch. B3G2 updates launch 10^5+ kernels, so its profiler section (`--prof-active`, default 2) takes minutes to post-process.

Speed (free-running s/update, variants interleaved A B A B; the number to quote; the pre-registered mark is median >= 1.3x over >= 100 timed updates after 20 warm-up):

```
python prof_train.py $C --sections bench --updates 100 --warmup 20 --bench-rounds 2 --out out/bench.json \
  --bench-list "baseline;eg_once;sortpad,oldw;sortpad,bigmb,oldw;eg_once,sortpad,oldw;eg_once,sortpad,bigmb,oldw,prefetch;tf32;eg_once,sortpad,oldw,compile"
```

Same maths (PREREG-eg-once.md E1-E4). E1 and E4 are registered for bf16 on the GPU, E2 and E3 for fp32 on the CPU:

```
# GPU: E1 (Gemma vectors, 256 rows), E3 numbers in fp32+bf16 on the GPU (extra), E4 (300-update loss trace per variant, ~2 x 300 updates each; --curve-updates 0 skips)
python prof_train.py $C --sections equiv --equiv-check --equiv-list "eg_once;sortpad,oldw;sortpad,bigmb,oldw;eg_once,sortpad,oldw;sortpad;bigmb;tf32;prefetch" --out out/equiv_gpu.json
# CPU: E2 (64 rows) and E3 (fp32, one update) with the real Gemma on the host CPU; slow (minutes per gradient); set OMP_NUM_THREADS to the core count
python prof_train.py $C --device cpu --eg real --sections equiv --equiv-check --curve-updates 0 --equiv-list "eg_once;eg_sorted;tf32;prefetch;sortpad;sortpad,oldw;bigmb,oldw" --out out/equiv_cpu.json
```

The GPU command also runs E2 (it loads a second, fp32, CPU copy of Gemma for it). `--seed 400` (default) and the first 256 rows of that seed's shuffled iterator are the "one fixed batch".

## What the equiv section reports

- **E1** (runs when an equiv spec contains `eg_once`, or `--equiv-vectors yes`): Gemma state H at every valid char position, eg_once vs the old path at the job's accum; the old path's own spread (accum vs accum/2); rules as registered: every position cos >= 0.998; every row's mean cos >= 0.9995; eg_once's largest per-row mean-cosine gap <= 1.5 x the old path's own largest gap. "registered setting met" says whether it ran as bf16 + GPU + real Gemma; anything else is only a plumbing check.
- **E2**: 64 rows, fp32 on the CPU, max abs diff of H, limit 1e-4.
- **E3**: loss relative diff <= 1e-5 and gradient cosine >= 0.99999 for each variant, plus the per-token weighting report. The plain arms (PTS/PTC/PT) use one token-mean `cross_entropy` per micro-batch, so a token weighs 1/(K n_k): any variant that changes the partition (`sortpad`, `bigmb`) changes the weights and is printed **NOT EXACT**. `oldw` restores the old weights inside the new partition, and then the numbers decide. B3G2's loss averages per row (b3.py:91 call loss, b3g2.py:566 answer loss) and its stop loss over rounds x rows (b3g2.py:569); rounds n and the K / gap / drill draws depend on the micro-batch mix, so `--equiv-pin 1` (default) pins them for the check; the weighting report says "not analysed" for it.
- **E4**: per variant, the loss of every update of a `--curve-updates` (default 300) run with the job's real lr schedule, same seed and rows as the old path (whose trace is computed once); mean over updates 101..300 of |loss_variant - loss_old| <= 0.02 and the two means within 0.01. Fewer than 300 updates prints the numbers but is not the check.

## Sections (`--sections`)

| section | what it gives |
|---|---|
| breakdown | ms per update, mean / median / p90 over `--updates` after `--warmup`: fetch, prep+split, h2d, forward (per top-level module via forward hooks and per python method: tokenize, tape_of, Gemma front, ...; `--methods none` for hooks only), backward, clip, opt, other. Each region is bracketed by `cuda.synchronize`: true region time, but the syncs slow the update, so the shares are of the SYNCED wall (the md prints the free-running number beside it and the per-section overhead). Forward-hook calls seen during backward count gradient-checkpoint recomputation. |
| throughput | free-running s/update (one sync per chunk) and peak memory. |
| profiler | `torch.profiler` wait/warmup/active: top-25 CUDA kernels, top-25 CPU ops, kernels per update, mean kernel us, GPU-busy fraction and idle gap (union of kernel intervals / wall), launch calls, stream syncs, DtoH copies per update, CPU-op time over kernel time, a launch-bound verdict (a heuristic; profiler overhead inflates wall). |
| padding | real batches (`--pad-updates`): row lengths, padded width W, real fraction of padded positions per micro-batch and per accum, and the same if each micro-batch were sorted and trimmed to its own widest row; b3g2: expected thinker rounds per row, random vs sorted partition. |
| sweep | accum 1,2,4,8,16,32 on the same rows: s/update and peak memory; OOM caught. Each point starts from a cold tokenizer cache. |
| syncs | CUDA only: every host-device sync in an update by python file:line (`torch.cuda.set_sync_debug_mode('warn')`). |
| bench / equiv | above. |

## Variants (`--variant a,b`; `--list-variants`)

| variant | what | same maths? |
|---|---|---|
| eg_once | Gemma runs ONCE per update on all rows (distinct prompts sorted by token length, chunks of <= `--eg-once-budget` padded tokens, default 16384); `FrozenEG.encode` serves each micro-batch's `[B,T,768]` (same dtype and zero padding) from the cache; an uncached prompt takes the old path (counted in `variant_stats_total`); `encode_texts` untouched | frozen, no_grad: only kernel rounding changes (E1/E2). Not run with `eg.pre` (the 30M/100M no-plug front). Alternative to `eg_sorted`. |
| sortpad | sort rows by prompt length, cut micro-batches in that order, trim `prompt_ids`/`prompt_mask` to each micro-batch's widest row | plain arms: **NOT EXACT** (weights, see E3); use `sortpad,oldw`. B3G2: row-averaged, exact only with K / gap / drill pinned. |
| oldw | per-token weights of the OLD partition inside any new partition (counts every row's supervised tokens first without running the network, then weighs each token 1/(K n_old(row))) | plain arms only; loss and gradient equal the old ones up to rounding. One extra host-side `_targets` pass per update. |
| sortpad_tokw | sortpad, weighted by token share = the FULL-batch token mean (what accum=1 computes) | differs from the old weights (not exact vs the old path), plain arms |
| bigmb | accum = `--bigmb-accum` (default accum//2) | NOT EXACT on the plain arms for the same reason; `bigmb,oldw` is |
| tf32 | tf32 matmul flags | under bf16 autocast only fp32 islands change |
| sdpa | the models already call `F.scaled_dot_product_attention` (ledger.py:136/138 CBlock, plain_lm.py:38 FlexBlock, writer.py:71; only the small copy-pointer scores at ledger.py:287 are an explicit einsum + softmax): nothing to switch; `--sdpa-backend flash/efficient/math/cudnn` restricts the dispatch | rounding only |
| compile / compile_ro | `torch.compile(dynamic=True)` on each controller block (default / reduce-overhead); skipped cleanly on CPU and on failure; `compile_stats` counts graphs/recompiles; sortpad rounds widths to 16 when a compile variant is on (`--pad-multiple`) | rounding only |
| eg_sorted | the frozen Gemma runs on length-sorted chunks of each micro-batch, scattered back to row order | rounding only |
| prefetch | thread + queue, pinned memory, side stream; same order and content | exact; limited by the GIL (collate is Python-bound) |

## Caveats

- Variants patch the one EG object that every Trainer of a run shares; the harness builds one Trainer at a time (the tests do too).
- Quote `throughput`/`bench` numbers, not `breakdown` ones; `breakdown` is for shares.
- `--eg auto` is the real Gemma on CUDA and a stub on CPU (`--eg real` on CPU for E2/E3 with the real front). The stub is a tiny deterministic copy of `FrozenEG` (same surface), good for plumbing and maths, not a cost model.
- PTC needs `--pkg-root` of the PTC overlay (`C.add_ptc`).
- The sweep's accum 1 (and the equiv accum=1 reference, CUDA only by default) may OOM at 256 rows x 2,000 letters; that is a result, not a failure.
- CPU-only so far: plumbing, the maths of the variants, padding arithmetic, accounting. Not yet seen: any CUDA time, the real profiler kernels, `set_sync_debug_mode`, inductor compile, the real Gemma through `eg_once`.

## Test

`python test_prof.py` (or `pytest test_prof.py`). The package is found from `$PROF_PKG_ROOT`, else an importable `custom_io`, else `git archive 74d6e92c75 custom_io`.
