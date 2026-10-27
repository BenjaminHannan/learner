# 358t v3 addendum 7: which card the rental uses (sleep research thread, written 2026-09-27 14:10:55 UTC, before any v3 run)

Additive to addenda v3-4 to v3-6. Marks, seal, seeds and arms are unchanged.
**Why:** Ben's standing order (14:05 UTC, relayed by the Director): "just use vast until I tell you not to" and "use cheap gpus, whatever gives most tflops/$/hr". Each job is capped at $4.
1. **Card:** the single-GPU offer with the best TFLOPS per $/h (vast's listed TFLOPS), not only an RTX 5090. It must have at least 24 GB of GPU RAM, compute capability 8.0 or higher (bf16 autocast), a CUDA 12.8 driver, reliability >= 0.98, >= 16 CPU cores, inet_down >= 200 and a price of at most $0.65/h.
   - Why 24 GB: 358i2's loop runs fit 4 at once in 16 GB on BensPC, so they are about 3-4 GB each. drive.sh starts a run only while 5 GB is free, so a 24 GB card runs about 5 at a time and a 32 GB card all 8.
2. **Time cap:** 3 h 30 min on a 5090, multiplied by (5090's 104.8 TFLOPS / the chosen card's TFLOPS) when the chosen card is slower, never shortened. The $1.45 money stop is unchanged and still applies.
3. **Logged:** the card's name, its TFLOPS, its GPU RAM, its $/h and its TFLOPS per $/h (Mac log), and the card as nvidia-smi names it (rental progress file).
4. **What it can move:** 358i's plain nets (the graded comparison) were trained on a 5090. A different card adds a GPU-type difference on top of the torch difference that was already there (2.11 vs 2.8). RESULTS-v3 names both.
