# Pre-registration: B3G2 speed sweep, round 2 (written 10-14 about 4:55 PM ET, BEFORE any number from this sweep)

Ben, 4:44 PM ET 10-14 (typed in the roadmap thread): "dedicate time to speeding training up. run the untested B3G2 accum 8 and 16 against accum 4 on a 4090, same marks as this morning's sweep. work the cheap wins too - tf32, padding, fused optimizer, sync removal - as paired A/Bs, one change at a time. post measured seconds per update and cost for everything. keep it cheap, inside the $50/week vast cap."

## What is already known (so this sweep does not pretend to be new)
Accum 16 and accum 8 were already timed this morning (`PREREG-b3g2-accum.md` Result log 1, `GPU-RUN-2-2026-10-14.md`): 5.95 s and 3.18 s per update against 2.12 s at accum 4 and 11.57 s at accum 32, one box, one seed. What is untested is (a) how the three compare when run in the SAME box with accum 4 as the reference, and (b) every cheap win on B3G2 at accum 4. (A loss trace of accum 8 or 16 over many updates is also untested; this sweep measures speed only, as the first one did.)

## What is measured (one rented RTX 4090, one session)
B3G2 3M (4,023,302 trained params), batch 256, bf16 autocast, seed 400, pool p10-rung30-s400-a64-L, caps_b3g2.json, custom_io at the PC's src-b3g2 (commit 74d6e92c75), harness `prof_train.py` at a named commit. Free-running seconds per update, median over at least 40 timed updates after 10 warm-up, **3 interleaved rounds (A, B, A, B, A, B)** so box drift cancels; peak allocated GB; mean thinker rounds per micro-batch. Reference **A = accum 4** (the recipe G2f-a4 runs on the PC).

| group | arms (each run against A in the same box) |
|---|---|
| accum rows | accum 8, accum 16; accum 2 as a timing-only extra (128 rows per micro-batch, about 17 GB: fits a 4090, NOT the PC's 16 GB card; reported, never recommended) |
| cheap wins, ONE change on top of accum 4, never combined | `tf32` (matmul + cudnn TF32 on); `pad64` (the padded width of the per-micro-batch inputs rounded up to a multiple of 64 instead of the batch's widest); `unfused` (AdamW with fused=False: the train.py of G2f-a4 already uses fused AdamW on CUDA, so this is a control that measures what the fused optimizer is already worth, not a new win); `nosync` (the biggest host-device syncs per round removed where the same values are already on the CPU: `writer.py:138`, `b3g2.py:350`, `writer.py:121` in the profile of 10-14 AM; the exact sites are re-measured first with the harness's `syncs` section at accum 4) |

All variants live in the harness (monkeypatch or a patched copy of the tree on the box). **Nothing under the PC's `src-b3g2`, `G2f-a4`'s queue or its code is touched.**

## Marks (fixed now, not changed after seeing numbers)
**Accum rows** (this morning's marks, unchanged except that the reference is now accum 4):
1. Speed counts only if the median s/update is at least 1.3 times lower than the reference.
2. Memory fits only if peak allocated is at most 10 GB.
3. Prediction (suggested, untested): **neither accum 8 nor accum 16 passes mark 1 against accum 4** (this morning's ratios: 0.67x and 0.36x). It is proved wrong if either one is at least 1.3x faster than accum 4. Accum 2 is a free extra with the same mark 1; it needs more than 10 GB, so it fails mark 2 by design on the PC's card.
4. If the mean thinker rounds per micro-batch rise by more than 25 % against the reference, the speed is reported together with that rise.

**Cheap wins** (paired against A, same box, interleaved):
5. A win **counts** only if all three rounds have B below A, the median of B is at least 5 % lower than the median of A (speed at least 1.05x), peak allocated is at most 10 GB, and mark 6 holds.
6. **Same maths** (the equivalence check, one update on the same 256 rows with the loop length K and the stochastic parts pinned, as `accumcmp` does): relative loss difference at most 1e-4 and gradient cosine at least 0.9999 in bf16 autocast, beside the harness's own rerun noise floor; for `pad64`, `nosync` and `unfused` also bit-exact on CPU in fp32 where the CPU can run the change (stated if it cannot). A variant that fails mark 6 is reported as NOT EXACT, and its speed is not a recommendation. `tf32` is allowed to differ in the last bits (it changes the fp32 islands only); it has to meet the same 1e-4 / 0.9999 bar.
7. **Noise floor**: A's three round medians are reported with their spread (largest / smallest). A difference smaller than twice that spread is "inside noise" whatever its sign; below 2 % it is "does nothing"; 2 % to 5 % is "small, reported, not recommended".
8. Predictions (suggested, untested): `tf32` changes the speed by under 2 % (bf16 autocast already puts nearly every matmul in bf16): **proved wrong if it counts under mark 5**. `unfused` is at least 2 % slower than A (fused is already on): proved wrong if it is faster or equal within noise. `pad64` under 3 %: proved wrong if it counts under mark 5. `nosync` at least 5 % faster (the GPU idled 79 % of the time at accum 32; its busy share at accum 4 is measured first with the harness's `profiler` section and printed beside the table): proved wrong if it comes in below 2 %.

## Money (computed from the offer's real price, never guessed)
- The harness prints, per arm, the wall minutes it used; arm cost = minutes / 60 x the offer's dph_total (all-in, as in SPEND.md: the account credit is read before and after). The report has, for every arm: median s/update, updates per hour, **dollars per 1,000 updates** and the cost of a full 24,000-update B3G2 run on this card (hours x dph). PC numbers are suggested only (the 5070 Ti is untested at accum 4; the 4090-to-PC factor measured on accum 32 was about 1.05 slower).
- One box only. Stage hard cap $3.00 (MAXH 3 h at an offer of at most $0.60/h incl. setup); week check: $10.7 charged before this sweep, so the $50/week cap leaves room. Box destroyed when collected; the account must list 0 instances of mine.
- Ben's standing words: "keep it cheap, well within the $50/week vast cap" (7:47 PM ET 10-13) and 4:44 PM ET 10-14 above. No 5090 (7:02 AM ET 10-13: only above 90 % confidence).

## What this is not
- Adoption of anything. A cheap win enters a run only with Ben's word, an equivalence proof against the code that run uses, and a new run name; G2f-a4 (already on the PC) is never changed by it.
- A claim about accuracy. Speed only, one seed, one box, one host (the same B3G2 accum 32 took 11.57 s here and 7.2 s on another 4090 box: speed depends on the host CPU).
- A PC-card number.

## Amendment 1 (10-14 about 5:55 PM ET; written BEFORE any run of this sweep; the original marks above stay as written)
The builder's CPU check found that `pad64` is not bit-identical in the gradient in fp32 (relative difference about 1e-8): zero-padding lengthens the reductions, and floating-point sums change in the last bits when terms are added in a different grouping. Mark 6's wording "bit-exact on CPU in fp32" was over-strict for `pad64` (my error in the specification, not a property of the variant). Reading used for `pad64` only: mark 6's bf16 bar (relative loss difference at most 1e-4, gradient cosine at least 0.9999) stays, and the fp32 CPU check becomes "equal to rounding: relative gradient difference at most 1e-6 and a loss difference at most 1e-6 relative". `nosync` and `unfused` keep the bit-exact requirement on CPU fp32 (`nosync` reads the same values from the CPU; `unfused` only changes the optimizer kernel; an optimizer-kernel change is checked on the GPU by the bf16 bar, since fused and unfused AdamW round differently, CPU has no fused kernel). The CPU checks are the builder's tests on a tiny config; the rental cannot repeat them (`bit_exact_cpu_fp32` is None on a GPU box), so on the rental only the bf16 bar is checked.

## Result log
(empty: filled after the run, results unedited, in the order of the tables above)
