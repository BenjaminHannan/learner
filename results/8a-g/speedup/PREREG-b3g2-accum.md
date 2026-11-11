# Pre-registration: B3G2 micro-batch size (accum) sweep (written 10-14 about 3:20 AM ET, BEFORE any B3G2 number at accum other than 32)

Why: the passive G2f profile (`G2F-PASSIVE-2026-10-14.md`) and the 4090 run (`GPU-RUN-1-2026-10-14.md`) show B3G2 at accum 32 is not Gemma-bound: the GPU idles about 79 % on the PC (8-row micro-batches, about 505 small sequential passes and about 8,000 host syncs per update), peak memory is 1.5 GB at 8 rows on the 4090. The only lever tested so far (`eg_once`) gives 1.09x on B3G2 and failed E1 on the plain arms.

## What is measured (rented RTX 4090; later the PC's own card)
B3G2 3M (4,023,302 trained params), batch 256, bf16 autocast, seed 400, pool p10-rung30-s400-a64-L, caps_b3g2.json, the harness `prof_train.py` at a named commit. Accum in {32 (the registered G2f setting), 16, 8, 4}; accum 1 and 2 only if memory allows.
- Speed: free-running seconds per update, median over at least 40 timed updates after 10 warm-up, 2 rounds, same box, same rows.
- Memory: peak allocated GB per accum.
- Maths (descriptive, no pass bar): one update on the same 256 rows with the loop length K pinned, accum 32 against each candidate: loss difference and gradient cosine. Also the mean number of thinker rounds per micro-batch at each accum (the code takes n = max(K, longest call chain in the micro-batch + 2), so bigger micro-batches may run more rounds).

## Marks (fixed now, not changed after seeing numbers)
1. **Speed counts** for an accum only if the median seconds per update is at least 1.3 times lower than accum 32 on the same box.
2. **Memory fits** only if peak allocated is at most 10 GB (the PC card has 16 GB and Windows keeps some).
3. Prediction (suggested, untested): accum 8 gives 2x to 3x. It is **proved wrong** if both accum 16 and accum 8 come in under 1.3x.
4. If rounds per micro-batch rise by more than 25 % against accum 32, the speed gain is reported together with that rise (it means more thinker work per row, not only less overhead).

## What this is not
- A same-maths change. `b3g2.py` `_loss` draws one K per micro-batch and averages the stop loss over rounds x rows, so accum changes how many rows share a K and slightly the weights. Any run at another accum is a new recipe with its own name; it is never called the registered G2f.
- Adoption anywhere. That needs Ben's word, a 300-update loss trace on the PC's own card (limits 0.02 and 0.01 as in `PREREG-eg-once.md` E4), timing on the PC card, and the same accum on both sides of any compared pair. G2f and anything running stay untouched.
- A claim about accuracy. One seed everywhere; speed only.

## Result log 1 (rented RTX 4090, Quebec, 10-14 6:13 to 8:33 AM ET; harness 1d728b99ef; B3G2 3M, batch 256, bf16, seed 400; outputs `gpu-run-2/`; read in `GPU-RUN-2-2026-10-14.md`)
Marks as registered above, results unedited. This box ran accum 32 at 11.57 s/update (the 10-14 1:36 AM box ran 7.2 s: different host, so absolute seconds differ; every ratio below is inside this one box).
| accum | rows per micro-batch | median s/update (round 1; round 2) | speed vs accum 32 | mark 1 (>= 1.3x) | peak allocated GB | mark 2 (<= 10 GB) | thinker rounds per micro-batch | mark 4 (> +25 % reported) |
|---|---|---|---|---|---|---|---|---|
| 32 | 8 | 11.568 (11.580; 11.556) | 1.00 | reference | 1.64 | yes | 15.92 | |
| 16 | 16 | 5.952 (5.959; 5.945) | 1.94 | **yes** | 2.66 | yes | 15.99 (+0.5 %) | no |
| 8 | 32 | 3.178 (3.182; 3.173) | 3.64 | **yes** | 4.68 | yes | 15.76 (-1.0 %) | no |
| 4 | 64 | 2.117 (2.126; 2.109) | 5.46 | **yes** | 8.77 | yes | 17.09 (+7.4 %) | no |
Mark 3: the prediction "accum 8 gives 2x to 3x" came in at 3.64x (above the band); it is not proved wrong (it would have been wrong only if both accum 16 and accum 8 were under 1.3x). Rounds per micro-batch do not rise by more than 25 % at any accum, so the gain is less overhead per row and not more thinker work.
Maths, descriptive (one update on the same 256 rows, K pinned, accum 32 against the candidate): fp32 gradient cosine 0.99999987 at accum 16 and 8, 0.99999988 at 4, relative loss difference <= 1.7e-7; bf16 gradient cosine 0.99999949 (16), 0.99999909 (8), 0.99999854 (4), relative loss difference <= 4.3e-5; the rerun noise floors are cosine 1.00000000 (fp32) and 0.99999999 (bf16). With K pinned the partition into micro-batches changes the gradient only at rounding level; what the random K does over training (one K per micro-batch, so fewer independent draws per update at a smaller accum) is untested.
AT-1 (agent-turn model B3AT 3M, same pool and caps as G2f, speed only, train.py log lines, 300 steps asked, 40 min timeout each): accum 32: **26.19 s/update** (only 2 consecutive differences, the timeout stopped it at step 80; first-log average incl. start 25.6 s) = **2.26x** B3G2 at accum 32 on the same box; accum 4: **5.735 s/update** (13 differences, all 300 steps finished in 1,727 s, peak allocated 8.36 GB, reserved 9.4 GB) = 2.71x B3G2 at accum 4, and 4.57x faster than AT at accum 32. Early losses of the two AT runs (descriptive, one seed, K random): step 20: 5.279 / 5.313, step 40: 4.417 / 4.448, step 60: 3.702 / 3.698, step 80: 3.086 / 3.149 (accum 32 / accum 4).
Not shown: any PC-card timing; any 300-update trace (the registered adoption step); G2f's state.
