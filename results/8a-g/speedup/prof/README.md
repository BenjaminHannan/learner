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

B3G2 accum sweep (PREREG-b3g2-accum.md; speed, memory and rounds per micro-batch, then the pinned-K comparison):

```
python prof_train.py --arm B3G2 --rung 3M --accum 32 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json \
  --sections accumsweep,accumcmp --accum-list 32,16,8,4 --accum-updates 40 --accum-warmup 10 --accum-rounds 2 --out out/accum.json
```

B3G2 speed A/B (PREREG-b3g2-speed-ab.md; accum 4 is the reference; the cheap wins ONE at a time on top of it; mark 6 first, then the paired timing with the money lines; abbench runs the variant arms first, in the order nosync, pad64p, pad64, tf32, unfused, THEN the accum rows 8, 16, 2: `AB_ARM_ORDER` is the default of both `--ab-variants` and `--ab-accums`, and giving either option overrides its part, in the order given):

```
python prof_train.py --arm B3G2 --rung 3M --accum 4 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json \
  --sections profiler,syncs --out out/ab_profile.json     # the log has one line 'profiler: GPU busy NN.N % of wall, idle gap ... (accum 4 ...): verdict'; the table is in ab_profile.profiler.md
python prof_train.py $B3 --sections abequiv --ab-variants nosync,pad64p,pad64,tf32,unfused --out out/ab_equiv.json
python prof_train.py $B3 --sections abbench --ab-variants nosync,pad64p,pad64,tf32,unfused --ab-accums 8,16,2 --ab-rounds 3 --ab-warmup 10 --ab-updates 40 \
  --dph 0.46 --ab-equiv-json out/ab_equiv.json --ab-partial out/ab_bench.partial.json --out out/ab_bench.json
```

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
| accumsweep | B3G2 micro-batch size sweep for `../PREREG-b3g2-accum.md`: `--accum-list` (default 32,16,8,4), `--accum-rounds` rounds (default 2), a fresh Trainer per (round, accum), `--accum-warmup` (default 10) then `--accum-updates` (default 40) free-running timed updates on the same rows; median s/update, peak allocated GB, mean thinker rounds per micro-batch (read from the model's own `rounds` aux), speed against the reference accum (first of the list, 32), the marks (speed >= 1.3x, memory <= 10 GB, rounds rise > 25 %), and whether prediction 3 is proved wrong. OOM is caught per accum and not retried. Not in the default section list. |
| accumcmp | descriptive, no pass bar: one update on the same first 256 rows with the loop length K pinned (`--equiv-pin`, default 1), the reference accum against each candidate in `--accum-list`: loss difference, gradient cosine and relative L2, fp32 (and bf16 on CUDA, `--equiv-precisions`), plus the reference run twice as the noise floor. Not in the default section list. |
| abequiv | mark 6 of `../PREREG-b3g2-speed-ab.md`: one update on the same first 256 rows, K and the stochastic parts pinned, the reference (`--accum`) against each of `--ab-variants` alone: relative loss difference, gradient cosine and relative L2, the parameters' change after one optimizer step, bit-exactness, the reference run twice as the noise floor, and the booleans of the 1e-4 / 0.9999 bar (read in bf16 autocast where run, else fp32). Amendment 1's CPU fp32 clause: nosync bit-exact, pad64 and pad64p equal to rounding (relative gradient and loss difference <= 1e-6), tf32 and unfused the bar only; only a CPU run can say (`bit_exact_cpu_fp32` is None on a GPU run). Without that CPU comparison mark 6 is the bf16 bar alone and is printed and stored as `bf16_bar_only`, with the sentence "CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run" (the tiny-config CPU tests of `test_prof.py` are that evidence). An exception in one variant is recorded for it (`error`: type, message, traceback tail) and the other variants still run. Not in the default section list. |
| abbench | the paired speed A/B of `../PREREG-b3g2-speed-ab.md`: A = `--accum` (4); B arms, in this order: one variant alone at the reference accum, `--ab-variants` (nosync, pad64p, pad64, tf32, unfused), THEN `--ab-accums` (8,16,2) (so an `--ab-max-min` cutoff skips accum rows, not the cheap wins); per arm `--ab-rounds` (3) interleaved rounds A,B,A,B,A,B of `--ab-warmup` (10) + `--ab-updates` (40) updates (a fresh Trainer per run, same rows): median s/update and per-round values, A's spread, peak allocated GB, thinker rounds per micro-batch, wall minutes; the flags of marks 1, 2, 4, 5, 7, the predictions of marks 3 and 8 as fields, and (`--dph`) per arm cost, dollars per 1,000 updates and the cost of a 24,000-update run. Mark 5 reads mark 6 (and its label) from this process's abequiv or `--ab-equiv-json`; as coded it needs B below A in every one of the `--ab-rounds` rounds (an arm with fewer completed rounds is "incomplete, cannot count"), the median of B at least 5 % lower than A's (B <= 0.95 A, slightly stricter than speed >= 1.05x), peak <= 10 GB and mark 6; the md prints that reading. An arm whose run raises (not OOM / Skip) is recorded (`error`, and `errors` of the section: arm, run, round, type, message, traceback tail) and the remaining arms still run. `--ab-partial` keeps the arms done if a timeout ends the run; `--ab-max-min` skips arms not started in time. Not in the default section list. |

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
| unfused | AdamW with fused=False (a CONTROL: train.py already uses fused AdamW on CUDA) | loss and gradient cannot change; the optimizer step differs at rounding (abequiv reports it) |
| pad64 | widths that vary per micro-batch rounded up to a multiple of 64: the prompt columns (own widest row, never past the batch width), the Gemma token width of the question's call, the teacher-forced tape entry width (`--pad64-parts`; `--list-variants` has the full list of what is and is not padded). Not with sortpad or eg_once / eg_sorted | masks unchanged; on the tiny CPU b3g2 the loss is identical and the gradient equal to about 1e-8 relative but NOT bit for bit (summation order over more columns): mark 6's CPU clause for it is "equal to rounding" (Amendment 1: relative gradient and loss difference <= 1e-6), not bit-exact |
| pad64p | pad64's PROMPT part alone (the per-micro-batch prompt inputs of the PREREG text): `prompt_ids` / `prompt_mask` cut to the micro-batch's own widest row rounded up to a multiple of 64, never past the batch width (so never past the cap) and never below the real widest; the Gemma and tape widths stay exact. Not with pad64 or sortpad | same reading of mark 6 as pad64 (equal to rounding on the CPU); its own row in abequiv and abbench, no pre-registered prediction |
| nosync | B3G2 only: the per-round syncs whose values are on the CPU already (writer.py:121 and :138 through `answer_teacher`, b3g2.py:350 and the `nonzero` after it) read from the CPU schedule / are copied async; rebuilt from the model's own source with exact text edits (refused with Skip if the text is not found once) | exact: same lists, same tensors, bit for bit on the CPU; the syncs on GPU values stay (see `--list-variants`) |

## Caveats

- Variants patch the one EG object that every Trainer of a run shares; the harness builds one Trainer at a time (the tests do too).
- Quote `throughput`/`bench` numbers, not `breakdown` ones; `breakdown` is for shares.
- `--eg auto` is the real Gemma on CUDA and a stub on CPU (`--eg real` on CPU for E2/E3 with the real front). The stub is a tiny deterministic copy of `FrozenEG` (same surface), good for plumbing and maths, not a cost model.
- PTC needs `--pkg-root` of the PTC overlay (`C.add_ptc`).
- The sweep's accum 1 (and the equiv accum=1 reference, CUDA only by default) may OOM at 256 rows x 2,000 letters; that is a result, not a failure.
- CPU-only so far: plumbing, the maths of the variants, padding arithmetic, accounting. Not yet seen: any CUDA time, the real profiler kernels, `set_sync_debug_mode`, inductor compile, the real Gemma through `eg_once`.

## Test

`python test_prof.py` (or `pytest test_prof.py`). The package is found from `$PROF_PKG_ROOT`, else an importable `custom_io`, else `git archive 74d6e92c75 custom_io`.
