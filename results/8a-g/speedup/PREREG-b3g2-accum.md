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
