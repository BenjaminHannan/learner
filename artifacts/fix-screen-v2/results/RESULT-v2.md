# Fix screen v2: result (run on BensPC by the Mac session; see PC-RUN-NOTE.md)

## Shown
- **X (exit StatePrefix 32 -> 256):** fit gain +0.6 / +1.3 / +0.3 (mean +0.7) -> **NO EFFECT**. Held-out gain +1.9 / +1.9 / +1.2 (mean +1.7).
- **Z (8 pooled core vectors zeroed):** 0 / 1,360 in_dist (main2 intact 68.5%) -> "core matters" by the registered mark.

## Caveat on Z (suggested)
Zero vectors are an input the LM never saw in training, so 0% may mean "the LM breaks on an odd prefix", not "every answer needs the core". A shuffled-core lesion (another question's 8 vectors) separates the two; it is in screen v3.

## Running tally (fit gain over paired baseline, 3 seeds, 6,000 updates)
reader x8 +0.2, rounds x2 -0.2, lr x0.3 -1.2, pointer exit -2.5, exit pipe x8 +0.7. Five changes on the core side and the exit width all leave fit at ~50%.
