# Profile: B3G2 3M accum 32 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## accumsweep

arm B3G2 | rung 3M | accum 32 | batch 256 | device cuda | torch 2.11.0+cu128

reference accum 32; 2 rounds x 40 timed updates after 10 warm-up (chunks of 5); marks (PREREG-b3g2-accum.md, fixed before any number): speed counts at >= 1.3x, memory fits at <= 10.0 GB peak allocated, a rise of rounds per micro-batch above +25 % is reported with the speed

| accum | rows/micro-batch | median s/update | median of chunks | speed vs ref | speed mark | peak alloc GB | memory mark | rounds/micro-batch | sem | rounds vs ref | rise > 25 % | s/update per round |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 32 | 8 | 11.5680 | 11.3102 | 1.000 | no | 1.64 | yes | 15.92 | 0.21 | 1.000 | no | 11.5797; 11.5564 |
| 16 | 16 | 5.9519 | 5.8991 | 1.944 | yes | 2.66 | yes | 15.99 | 0.29 | 1.005 | no | 5.9587; 5.9450 |
| 8 | 32 | 3.1778 | 3.1751 | 3.640 | yes | 4.68 | yes | 15.76 | 0.40 | 0.990 | no | 3.1824; 3.1733 |
| 4 | 64 | 2.1173 | 2.1319 | 5.464 | yes | 8.77 | yes | 17.09 | 0.56 | 1.074 | no | 2.1258; 2.1087 |

prediction (accum 8 gives 2x to 3x) proved wrong (both accum 16 and accum 8 under 1.3x): no

s_per_update_median = median over the rounds of each round's mean s/update (the bench convention); median_of_chunks = median over every timed chunk of every round. peak_alloc_gb is torch max_memory_allocated in GiB, reset before each timed run. rounds_per_micro_batch = mean of aux["rounds"] (n = max(K, longest call chain + 2), K drawn per micro-batch) over the timed updates. A different accum is a new recipe (b3g2 draws one K per micro-batch), never the registered G2f.

