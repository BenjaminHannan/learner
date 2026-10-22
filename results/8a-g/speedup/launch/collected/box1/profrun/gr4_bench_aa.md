# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## abbench

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

reference A = accum 4; 3 interleaved rounds A,B,A,B,A,B x 40 timed updates after 10 warm-up (chunks of 5); marks (PREREG-b3g2-speed-ab.md, fixed before any number): speed counts at >= 1.3x, memory fits at <= 10.0 GB, rounds rise reported above +25 %, a cheap win needs B 5 % lower in the median and below A in every round, mark 7: inside noise under 2 x A's spread, under 2 % does nothing, 2 to 5 % small; complete: True

arm order (variants first, then the accum rows): same

mark 5 as coded: B below A in EVERY round (all 3 rounds completed; an arm with fewer is "incomplete, cannot count"), the median of B at least 5 % lower than the median of A, i.e. B <= 0.95 x A (slightly stricter than "speed at least 1.05x", which would allow B <= 0.9524 x A), peak allocated <= 10 GB, and mark 6 holds.

| arm | kind | A median s/update | B median s/update | speed (A/B) | B lower than A by | A round medians | B round medians | A spread (max/min) | peak alloc GB | mark 7 |
|---|---|---|---|---|---|---|---|---|---|---|
| same | variant | 2.4019 | 2.4041 | 0.999 | -0.1 % | 2.460, 2.381, 2.402 | 2.463, 2.381, 2.404 | 1.033 | 8.33 | does nothing; inside noise |

cheap wins (mark 5; mark 6 comes from abequiv, with the label of the check it rests on):

| arm | B below A every round | B >= 5 % lower (B <= 0.95 A) | peak <= 10 GB | mark 6 holds | counts (without mark 6) | mark 5: counts |
|---|---|---|---|---|---|---|
| same | no | no | yes | yes (bf16_bar_only) | no | **no** |

mark 6 labelled bf16_bar_only above rests on the bar alone: CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run.

predictions (suggested, untested; marks 3 and 8):

| prediction | measured | proved wrong |
|---|---|---|
| neither accum 8 nor accum 16 passes mark 1 against accum 4 | {} | - |

money (dph 0.443 $/h; 24,000-update run = hours x dph; arm cost = the arm's A + B wall minutes / 60 x dph; 12.2 wall min in all, $0.09):

| arm | s/update | updates/hour | hours per 24,000 | USD per 1,000 updates | USD per 24,000-update run | wall min (A + B) | arm cost USD |
|---|---|---|---|---|---|---|---|
| A (reference) | 2.4019 | 1499 | 16.01 | 0.296 | 7.09 | - | - |
| same | 2.4041 | 1497 | 16.03 | 0.296 | 7.10 | 12.2 | 0.090 |

round value = median of the chunks' s/update (chunk = --chunk updates between two syncs); an arm's median = median of its round values; A is re-run in every arm, A and B alternate (A,B,A,B,A,B), so A's spread is that arm's own. speed_vs_a = A median / B median; b_lower_than_a_by = 1 - B/A (positive: B faster). inside_noise: |b_lower_than_a_by| < 2 x (A spread - 1). peak_alloc_gb = torch max_memory_allocated in GiB, reset before each timed run. cost_arm_usd = (A + B wall minutes) / 60 x dph. One seed, one box, one host.

