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

## Amendment 1 (10-14 about 12:10 AM ET, still before any GPU number)
The harness helper found on a CPU stub that E1 rule 3 ("no worse than 1.5 times the old path's own spread") fails on noise when the old spread is tiny or zero (the old path can be nearly batch-invariant). Rule 3 now passes whenever the largest per-row gap (1 - mean cosine) is <= 1e-4, which is far below bf16 rounding and five times tighter than rule 2's 5e-4. Rules 1 and 2 are unchanged, so nothing looser than the registered per-position and per-row limits can pass.

## Result log 1: CPU fp32 check on the Mac, real EmbeddingGemma 2 (10-13 11:18 to 11:36 PM ET; harness 6a870a767c then daee2fd9e9; PTS 3M accum 16, 20,049-row sample of the -L pool, caps_b3s.json)
- **E2 FAILED as registered.** Max abs difference of H over 64 rows = 1.389e-03 against the limit 1e-4.
- Scale diagnostic (added after the first run, not a mark): max |H| 588.1, p99.9 |H| 274.7, mean |H| 34.6. The difference is 2.4e-6 of the largest value, and 5.5e-6 relative at the worst element (251.2). fp32 rounding is 1.2e-7 per operation, so about 40 roundings of error after 24 layers is what reordering the sums would give (suggested). The same vectors give cosine 1 - 4e-12 on all 256 rows (E1 plumbing passes), and one update's loss is identical and the gradient cosine 1.00000000 with relative L2 5e-8 (E3 passes for eg_once, eg_sorted, prefetch, sortpad,oldw and bigmb,oldw). Plain `sortpad` and `bigmb` are NOT EXACT on the plain arms (they change per-token weights; loss rel 2.3e-3, gradient cosine 0.9496) unless `oldw` restores the old weights.
- My absolute 1e-4 limit ignored the size of H (values up to 588). That is my error, but the registered result stays FAIL in the record.

## Amendment 2: E2 relative form (revised after seeing the CPU result; accepted by the big-run thread 10-14 ~12:40 AM ET, still before any GPU number)
For E2-type checks: pass if max abs difference <= 1e-5 x max |H| (about 80 fp32 roundings wide). Big-run's four conditions, all adopted:
1. This text is written before any GPU number exists and is labelled "revised after seeing the CPU result".
2. The CPU result above stays recorded as FAIL on the original wording (abs 1e-4). That it "would pass the relative form" (2.4e-6 against 1e-5) is post hoc and not counted.
3. E2 is re-run under the new rule on fresh pool rows (not the 64 rows that prompted the change) and must pass there. `prof_train.py` at the next commit prints both wordings and the sha256 of the 64 prompts used; use `--seed 401` and `--seed 402` on the Mac sample so the rows differ from the first run (seed 400).
4. Adoption of any variant still needs E1 (bf16 on the GPU), the 300-update loss trace (E4) and the speed on the PC's own card. E1, E3, E4 are unchanged.
eg_once is the only candidate. `sortpad` and `bigmb` change per-token weights on the plain arms (loss rel 2.3e-3, gradient cosine 0.95), so they stay off PTS, PTC, g2c10s and anything compared with them unless the old weights are restored (`oldw`).

## Result log 2: E2 on fresh rows (Mac CPU fp32, real Gemma, PTS 3M accum 16; harness bbaa4a9a16, prof_train.py sha256 91041f40...; 10-13 11:41 to 11:45 PM ET)
Rows: 64 each, from a 20,049-row sample of the -L pool; prompt hashes differ (seed 401: ccb8ba1e22ae..., seed 402: f0fd2653c1b2...); seed 400's hash was not recorded in the first run.
| seed | max abs diff | max abs value | diff / max | registered wording (abs 1e-4) | revised rule (1e-5 x max) | E1 | E3 eg_once |
|---|---|---|---|---|---|---|---|
| 400 (first run, the 64 rows that prompted the change) | 1.389e-03 | 588.1 | 2.4e-6 | FAIL | would pass (post hoc, not counted) | PASS | PASS |
| 401 (fresh) | 0 (identical) | 854.3 | 0 | PASS | PASS | PASS | PASS |
| 402 (fresh) | 2.154e-03 | 564.2 | 3.8e-6 | FAIL | PASS | PASS | PASS |
Condition 3 of big-run (E2 must pass under the revised rule on fresh rows) is met on both fresh seeds. The registered wording fails on one of the two (1 of 3 runs identical, 2 of 3 differ at the 1e-6 relative level), which fits fp32 rounding that depends on how the rows are batched (suggested). E1 rule 3 passes on seeds 401 and 402 through the 1e-4 floor (amendment 1): ratios 6.6 and 3.1 against the old spread (the spread is ~3e-12 and the gap 1e-11 to 2e-11, both far below 1e-4); the harness md now prints the floor beside the ratio. Nothing here is a GPU number; adoption still needs bf16 E1, the 300-update trace E4 and the speed on the PC's own card.

## Result log 3: the rented RTX 4090 (box ran 10-14 1:36 to 3:00 AM ET; harness ca542f77a9; PTC 3M accum 16 and B3G2 3M accum 32; bf16; seed 400; raw outputs in `gpu-run-1/`; full read in `GPU-RUN-1-2026-10-14.md`)
Marks as registered, results unedited:
| mark | result | verdict |
|---|---|---|
| E1 (bf16 GPU, 256 rows): every position cos >= 0.998; every row-mean cos >= 0.9995; gap <= 1.5 x old spread or <= 1e-4 | eg_once vs old accum 16: min position cos 0.5288, 119 positions below 0.998, min row-mean cos 0.996825 (3 rows below 0.9995), largest per-row gap 3.175e-03. Old path's own spread (accum 16 vs accum 8): min position cos 0.7761, 205 positions below 0.998, min row-mean 0.998554 (3 rows), gap 1.446e-03. Ratio 2.20. | **FAIL, all three rules** |
| E2 (fp32 CPU, 64 rows) | max abs diff 5.722e-04 (registered abs 1e-4); 1.07e-06 of max abs H 533.7 (revised rule 1e-5 x max) on rows with prompts hash 40271958166306a8 | registered wording FAIL; revised rule PASS (as agreed in amendment 2) |
| E3 (loss, gradient of one update) | eg_once: loss identical, gradient cosine 0.99999818 (fp32), 0.99999781 (bf16). Run on the GPU in fp32, not on the CPU as registered; the CPU run on the Mac passed (result log 1 and 2) | PASS (setting deviation noted) |
| E4 (300 updates, bf16 GPU, updates 101-300) | mean abs loss difference 0.0162 (limit 0.02); difference of means 0.0088 (limit 0.01; old 1.5322, variant 1.5234) | PASS, at 81 % and 88 % of the limits; one seed |
| Speed, PTC accum 16 (100 timed updates after 20 warm-up, 2 rounds) | baseline 0.619 and 0.911 s/update (round spread 47 %); eg_once 0.414 and 0.425 s/update: 1.83x on the medians, 1.5x to 2.2x against either baseline round | PASS (>= 1.3x) |
| Speed, B3G2 accum 32 (40 timed updates after 10 warm-up, 2 rounds; fewer than the registered 100) | baseline 7.257 and 7.154 s/update; eg_once 6.827 and 6.351: 1.09x | FAIL (< 1.3x) |
| Gemma share of an update (synced wall) | PTC: reader front 686 ms of 870 ms = 79 %. B3G2: 1668 ms of 7600 ms = 22 % | the "Gemma under 40 %" proof-wrong condition holds for B3G2 |
Predictions written in advance: "eg_once alone 2 to 3 times faster for PTS/PTC at accum 16" came in at 1.8x (below the band, above the mark); "for B3G2 at accum 32 more" is **proved wrong** (1.09x; the Mac's passive G2f profile also shows Gemma at 23 %).
**Adoption gate: not met.** E1 is a required step (amendment 2, condition 4) and it failed, so `eg_once` is not adopted anywhere. Nothing already running or queued was touched.
What the E1 numbers say (shown / suggested): the old path already fails rules 1 and 2 against itself when only the micro-batch size changes (205 positions below 0.998), so those two rules were stricter than bf16 allows; that is my error, the same kind as E2. It does not rescue the variant: rule 3, the one tied to the old path's own spread, also fails (2.2x against 1.5x). Why eg_once differs more than an accum change is untested (suggested: sorted chunks pad differently, and bf16 kernels change with shape). The registered text above stays as written. Any new E1 rule would be post hoc and must pass big-run's four conditions (labelled, original FAIL kept, fresh rows, still needs the PC-card timing).
Other variants (same box, same bench; E3 on the GPU in fp32): `sortpad,oldw` 1.27x (below 1.3x), `sortpad,bigmb,oldw` 2.00x (E3 PASS), `eg_once,sortpad,oldw` 1.79x, `eg_once,sortpad,bigmb,oldw,prefetch` 2.12x, `tf32` 1.21x (below 1.3x; E3 PASS). E1 was not run for `sortpad,bigmb`; changing the micro-batch composition moves Gemma's bf16 states by the same kind of amount as an accum change does.
