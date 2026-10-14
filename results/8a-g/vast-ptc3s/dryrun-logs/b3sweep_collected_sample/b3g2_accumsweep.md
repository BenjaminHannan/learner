# Profile: B3G2 3M accum 32 batch 32 on x86_64 (cpu), torch 2.14.1+cpu

model b3g2, 205,014 trained params, data /dev/shm/ptcdry/J/work/g8a/pools/p10-rung30-s400-a64-L (400 rows), EG front stub, bf16 autocast False, seed 400, caps caps_b3g2.json

## accumsweep

arm B3G2 | rung 3M | accum 32 | batch 32 | device cpu | torch 2.14.1+cpu

reference accum 32; 1 rounds x 2 timed updates after 1 warm-up (chunks of 2); marks (PREREG-b3g2-accum.md, fixed before any number): speed counts at >= 1.3x, memory fits at <= 10.0 GB peak allocated, a rise of rounds per micro-batch above +25 % is reported with the speed

| accum | rows/micro-batch | median s/update | median of chunks | speed vs ref | speed mark | peak alloc GB | memory mark | rounds/micro-batch | sem | rounds vs ref | rise > 25 % | s/update per round |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 32 | 1 | 4.8031 | 4.8031 | 1.000 | no | - | - | 14.69 | 1.29 | 1.000 | no | 4.8031 |
| 16 | 2 | 3.2026 | 3.2026 | 1.500 | yes | - | - | 17.19 | 1.91 | 1.170 | no | 3.2026 |
| 8 | 4 | 2.0442 | 2.0442 | 2.350 | yes | - | - | 17.81 | 2.99 | 1.213 | no | 2.0442 |
| 4 | 8 | 0.9815 | 0.9815 | 4.894 | yes | - | - | 12.62 | 3.38 | 0.860 | no | 0.9815 |

prediction (accum 8 gives 2x to 3x) proved wrong (both accum 16 and accum 8 under 1.3x): no

s_per_update_median = median over the rounds of each round's mean s/update (the bench convention); median_of_chunks = median over every timed chunk of every round. peak_alloc_gb is torch max_memory_allocated in GiB, reset before each timed run. rounds_per_micro_batch = mean of aux["rounds"] (n = max(K, longest call chain + 2), K drawn per micro-batch) over the timed updates. A different accum is a new recipe (b3g2 draws one K per micro-batch), never the registered G2f.

