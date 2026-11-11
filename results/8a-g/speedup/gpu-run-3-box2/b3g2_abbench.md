# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## abbench

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

reference A = accum 4; 3 interleaved rounds A,B,A,B,A,B x 40 timed updates after 10 warm-up (chunks of 5); marks (PREREG-b3g2-speed-ab.md, fixed before any number): speed counts at >= 1.3x, memory fits at <= 10.0 GB, rounds rise reported above +25 %, a cheap win needs B 5 % lower in the median and below A in every round, mark 7: inside noise under 2 x A's spread, under 2 % does nothing, 2 to 5 % small; complete: True

arm order (variants first, then the accum rows): accum 8, accum 16

mark 5 as coded: B below A in EVERY round (all 3 rounds completed; an arm with fewer is "incomplete, cannot count"), the median of B at least 5 % lower than the median of A, i.e. B <= 0.95 x A (slightly stricter than "speed at least 1.05x", which would allow B <= 0.9524 x A), peak allocated <= 10 GB, and mark 6 holds.

| arm | kind | A median s/update | B median s/update | speed (A/B) | B lower than A by | A round medians | B round medians | A spread (max/min) | peak alloc GB | mark 7 |
|---|---|---|---|---|---|---|---|---|---|---|
| accum 8 | accum | 2.2397 | 3.2571 | 0.688 | -45.4 % | 2.297, 2.237, 2.240 | 3.298, 3.246, 3.257 | 1.027 | 4.47 | large |
| accum 16 | accum | 2.2367 | 6.0102 | 0.372 | -168.7 % | 2.238, 2.237, 2.222 | 5.988, 6.033, 6.010 | 1.007 | 2.52 | large |

accum rows (marks 1, 2, 4):

| arm | mark 1: speed >= 1.3x | mark 2: <= 10 GB | rounds vs A | mark 4: rise > 25 % | B rounds/micro-batch | A rounds/micro-batch |
|---|---|---|---|---|---|---|
| accum 8 | no | yes | 0.924 | no | 15.96 | 17.28 |
| accum 16 | no | yes | 0.928 | no | 16.04 | 17.28 |

predictions (suggested, untested; marks 3 and 8):

| prediction | measured | proved wrong |
|---|---|---|
| neither accum 8 nor accum 16 passes mark 1 against accum 4 | {'accum 8': False, 'accum 16': False} | no |

money (dph 0.5304 $/h; 24,000-update run = hours x dph; arm cost = the arm's A + B wall minutes / 60 x dph; 35.2 wall min in all, $0.31):

| arm | s/update | updates/hour | hours per 24,000 | USD per 1,000 updates | USD per 24,000-update run | wall min (A + B) | arm cost USD |
|---|---|---|---|---|---|---|---|
| A (reference) | 2.2375 | 1609 | 14.92 | 0.330 | 7.91 | - | - |
| accum 8 | 3.2571 | 1105 | 21.71 | 0.480 | 11.52 | 14.2 | 0.125 |
| accum 16 | 6.0102 | 599 | 40.07 | 0.886 | 21.25 | 21.0 | 0.186 |

round value = median of the chunks' s/update (chunk = --chunk updates between two syncs); an arm's median = median of its round values; A is re-run in every arm, A and B alternate (A,B,A,B,A,B), so A's spread is that arm's own. speed_vs_a = A median / B median; b_lower_than_a_by = 1 - B/A (positive: B faster). inside_noise: |b_lower_than_a_by| < 2 x (A spread - 1). peak_alloc_gb = torch max_memory_allocated in GiB, reset before each timed run. cost_arm_usd = (A + B wall minutes) / 60 x dph. One seed, one box, one host.

