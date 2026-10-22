# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## abbench

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

reference A = accum 4; 3 interleaved rounds A,B,A,B,A,B x 40 timed updates after 10 warm-up (chunks of 5); marks (PREREG-b3g2-speed-ab.md, fixed before any number): speed counts at >= 1.3x, memory fits at <= 10.0 GB, rounds rise reported above +25 %, a cheap win needs B 5 % lower in the median and below A in every round, mark 7: inside noise under 2 x A's spread, under 2 % does nothing, 2 to 5 % small; complete: True

arm order (variants first, then the accum rows): defer

mark 5 as coded: B below A in EVERY round (all 3 rounds completed; an arm with fewer is "incomplete, cannot count"), the median of B at least 5 % lower than the median of A, i.e. B <= 0.95 x A (slightly stricter than "speed at least 1.05x", which would allow B <= 0.9524 x A), peak allocated <= 10 GB, and mark 6 holds.

| arm | kind | A median s/update | B median s/update | speed (A/B) | B lower than A by | A round medians | B round medians | A spread (max/min) | peak alloc GB | mark 7 |
|---|---|---|---|---|---|---|---|---|---|---|
| defer | variant | 1.8093 | 1.3321 | 1.358 | +26.4 % | 1.827, 1.809, 1.806 | 1.332, 1.335, 1.332 | 1.011 | 8.15 | large |

cheap wins (mark 5; mark 6 comes from abequiv, with the label of the check it rests on):

| arm | B below A every round | B >= 5 % lower (B <= 0.95 A) | peak <= 10 GB | mark 6 holds | counts (without mark 6) | mark 5: counts |
|---|---|---|---|---|---|---|
| defer | yes | yes | yes | - | yes | **-** |

predictions (suggested, untested; marks 3 and 8):

| prediction | measured | proved wrong |
|---|---|---|
| neither accum 8 nor accum 16 passes mark 1 against accum 4 | {} | - |

money (dph 0.4593 $/h; 24,000-update run = hours x dph; arm cost = the arm's A + B wall minutes / 60 x dph; 7.8 wall min in all, $0.06):

| arm | s/update | updates/hour | hours per 24,000 | USD per 1,000 updates | USD per 24,000-update run | wall min (A + B) | arm cost USD |
|---|---|---|---|---|---|---|---|
| A (reference) | 1.8093 | 1990 | 12.06 | 0.231 | 5.54 | - | - |
| defer | 1.3321 | 2702 | 8.88 | 0.170 | 4.08 | 7.8 | 0.060 |

round value = median of the chunks' s/update (chunk = --chunk updates between two syncs); an arm's median = median of its round values; A is re-run in every arm, A and B alternate (A,B,A,B,A,B), so A's spread is that arm's own. speed_vs_a = A median / B median; b_lower_than_a_by = 1 - B/A (positive: B faster). inside_noise: |b_lower_than_a_by| < 2 x (A spread - 1). peak_alloc_gb = torch max_memory_allocated in GiB, reset before each timed run. cost_arm_usd = (A + B wall minutes) / 60 x dph. One seed, one box, one host.

