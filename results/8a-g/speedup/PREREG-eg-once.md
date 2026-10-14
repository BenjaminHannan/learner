# Pre-registration: same-maths speedups of the training update (written 10-13 ~10:50 PM ET, BEFORE any GPU measurement)

Ben's ask (9:47 PM ET 10-13): "look at speeding up the model. profile where the run time actually goes and find speedups where you can."
Evidence so far (shown, `PC-PASSIVE-2026-10-13.md`): on the live PC job (arm PTS, accum 16) 75.5 % of sampled Python time is the frozen EmbeddingGemma 2 forward, called once per 16-row micro-batch; our model's backward is under 1 %; the trainer keeps about 0.92 of one core busy while the GPU averages 76 %.

Rules, from the big-run thread's conditions (10-13 ~10:47 PM ET) plus mine. Nothing here changes a mark of any queued run.
1. The tolerance below is fixed now and is not changed after seeing numbers.
2. A speedup applies only to queue inserts that have NOT started, only with Ben's say-so, and the same pass must be used on both sides of any compared pair (for example AT 10M and PTC 10M). The commit name goes in each run's log.
3. Timing for the decision to adopt is repeated on the PC's own card when the PC is free; the rented 4090 only guides.
4. Nothing is changed in G2f or any run already started.

## Variants (each keeps the maths of the update; selected by name in `prof_train.py --variant`)
- `eg_once`: EmbeddingGemma runs once per update on all 256 prompts (length-sorted chunks under a token budget), micro-batches take their rows from that result. Same prompts, same weights, no training signal passes through it (it is frozen, no_grad).
- `sortpad`: rows of an update sorted by length before they are cut into micro-batches, each micro-batch trimmed to its own widest row.
- `bigmb`: fewer, larger micro-batches (smaller accum), where memory allows.
- Optional: `tf32` / `compile` / `prefetch` (host-side only).

## Equivalence tolerance (one fixed 256-row batch, seed 400, same weights; bf16 on the GPU, fp32 on CPU)
E1 (vectors, `eg_once` vs the old path, bf16, GPU): for every valid char position the Gemma state H has cosine >= 0.998 with the old path's state, and the row-mean cosine is >= 0.9995 for every row. The old path's own spread is measured first: old path with accum 16 vs old path with accum 8 on the same rows; `eg_once` must differ from the old path by no more than 1.5 times that spread (largest per-row mean-cosine gap), else it fails.
E2 (fp32 on CPU, 64 rows): vectors equal within max abs difference 1e-4 (the repo's own EG check uses 1e-4 in fp32).
E3 (loss and gradient of one update, fp32 on CPU, any variant): loss within relative 1e-5 of the old path (for `sortpad`, after the weighting fix described in prof README if the loss is a token mean per micro-batch; if the weights differ and are not fixed, the variant is marked NOT EXACT and reported as such); gradient cosine >= 0.99999.
E4 (300-update loss trace, seed 400, same rows, bf16 on the GPU): mean over updates 101 to 300 of |loss_variant - loss_old| <= 0.02 and the means of those updates differ by <= 0.01. (Scale: the trained PTS run logs a loss around 0.24 near the end; early losses are larger. This is a smoke check that the trajectory is the same kind of run, not a proof of identical weights; it does not replace the seed spread.)

## Speed marks (rented 4090, then PC)
- The variant counts as a speedup only if the median seconds per update falls by at least 1.3 times against the old path at the same accum on the same box, over >= 100 timed updates after 20 warm-up updates.
- Predictions written now (suggested, not measured): `eg_once` alone 2 to 3 times faster for arm PTS/PTC at accum 16; for B3G2 at accum 32 more. What proves this wrong: `eg_once` below 1.3 times, or the per-section timer showing Gemma under 40 % of an update on the 4090.

## What I will not claim
Any number from the 4090 as the PC's number; any gain on arms I did not time (B3G2 is timed separately); that two runs with different passes are comparable.
