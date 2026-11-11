# Profile: B3G2 3M accum 4 batch 256 on NVIDIA GeForce RTX 4090 (cuda), torch 2.11.0+cu128

model b3g2, 4,023,302 trained params, data /job/work/g8a/pools/p10-rung30-s400-a64-L (200,000 rows), EG front real, bf16 autocast True, seed 400, caps caps_b3g2.json

## abbench

arm B3G2 | rung 3M | accum 4 | batch 256 | device cuda | torch 2.11.0+cu128

reference A = accum 4; 3 interleaved rounds A,B,A,B,A,B x 40 timed updates after 10 warm-up (chunks of 5); marks (PREREG-b3g2-speed-ab.md, fixed before any number): speed counts at >= 1.3x, memory fits at <= 10.0 GB, rounds rise reported above +25 %, a cheap win needs B 5 % lower in the median and below A in every round, mark 7: inside noise under 2 x A's spread, under 2 % does nothing, 2 to 5 % small; complete: True

arm order (variants first, then the accum rows): nosync, pad64p, pad64, tf32, unfused, accum 8, accum 16, accum 2

mark 5 as coded: B below A in EVERY round (all 3 rounds completed; an arm with fewer is "incomplete, cannot count"), the median of B at least 5 % lower than the median of A, i.e. B <= 0.95 x A (slightly stricter than "speed at least 1.05x", which would allow B <= 0.9524 x A), peak allocated <= 10 GB, and mark 6 holds.

| arm | kind | A median s/update | B median s/update | speed (A/B) | B lower than A by | A round medians | B round medians | A spread (max/min) | peak alloc GB | mark 7 |
|---|---|---|---|---|---|---|---|---|---|---|
| nosync | variant | 2.2877 | 2.2398 | 1.021 | +2.1 % | 2.288, 2.234, 5.484 | 2.240, 2.229, 4.501 | 2.455 | 8.33 | small, reported, not recommended; inside noise |
| pad64p | variant | 5.5082 | 5.1122 | 1.077 | +7.2 % | 5.510, 5.496, 5.508 | 5.112, 5.093, 5.159 | 1.003 | 8.28 | large |
| pad64 | variant | 5.4959 | 5.3344 | 1.030 | +2.9 % | 5.490, 5.497, 5.496 | 5.333, 5.334, 5.343 | 1.001 | 8.64 | small, reported, not recommended |
| tf32 | variant | 5.3995 | 2.2288 | 2.423 | +58.7 % | 5.487, 5.399, 2.223 | 5.486, 2.229, 2.227 | 2.469 | 8.33 | large; inside noise |
| unfused | variant | 2.2220 | 2.2167 | 1.002 | +0.2 % | 2.215, 2.223, 2.222 | 2.216, 2.222, 2.217 | 1.003 | 8.33 | does nothing; inside noise |
| accum 8 | accum | 2.2183 | 3.2017 | 0.693 | -44.3 % | 2.218, 2.216, 2.229 | 3.210, 3.187, 3.202 | 1.006 | 4.47 | large |
| accum 16 | accum | skipped: --ab-max-min 100 reached before this arm |  |  |  |  |  |  |  |  |
| accum 2 | accum | skipped: --ab-max-min 100 reached before this arm |  |  |  |  |  |  |  |  |

accum rows (marks 1, 2, 4):

| arm | mark 1: speed >= 1.3x | mark 2: <= 10 GB | rounds vs A | mark 4: rise > 25 % | B rounds/micro-batch | A rounds/micro-batch |
|---|---|---|---|---|---|---|
| accum 8 | no | yes | 0.924 | no | 15.96 | 17.28 |

cheap wins (mark 5; mark 6 comes from abequiv, with the label of the check it rests on):

| arm | B below A every round | B >= 5 % lower (B <= 0.95 A) | peak <= 10 GB | mark 6 holds | counts (without mark 6) | mark 5: counts |
|---|---|---|---|---|---|---|
| nosync | yes | no | yes | yes (bf16_bar_only) | no | **no** |
| pad64p | yes | yes | yes | yes (bf16_bar_only) | yes | **yes** |
| pad64 | yes | no | yes | yes (bf16_bar_only) | no | **no** |
| tf32 | no | yes | yes | yes (bf16_bar_only) | no | **no** |
| unfused | no | no | yes | yes (bf16_bar_only) | no | **no** |

mark 6 labelled bf16_bar_only above rests on the bar alone: CPU fp32 exactness is checked by test_prof.py off the box (Amendment 1), not on this run.

predictions (suggested, untested; marks 3 and 8):

| prediction | measured | proved wrong |
|---|---|---|
| neither accum 8 nor accum 16 passes mark 1 against accum 4 | {'accum 8': False} | no |
| changes the speed by under 2 %; proved wrong if it counts under mark 5 | False | no |
| is at least 2 % slower than A; proved wrong if it is faster or equal within noise | False | yes |
| under 3 %; proved wrong if it counts under mark 5 | True | no |
| at least 5 % faster; proved wrong if it comes in below 2 % | False | no |

money (dph 0.3696 $/h; 24,000-update run = hours x dph; arm cost = the arm's A + B wall minutes / 60 x dph; 113.2 wall min in all, $0.70):

| arm | s/update | updates/hour | hours per 24,000 | USD per 1,000 updates | USD per 24,000-update run | wall min (A + B) | arm cost USD |
|---|---|---|---|---|---|---|---|
| A (reference) | 3.8436 | 937 | 25.62 | 0.395 | 9.47 | - | - |
| nosync | 2.2398 | 1607 | 14.93 | 0.230 | 5.52 | 15.5 | 0.095 |
| pad64p | 5.1122 | 704 | 34.08 | 0.525 | 12.60 | 26.6 | 0.164 |
| pad64 | 5.3344 | 675 | 35.56 | 0.548 | 13.14 | 27.1 | 0.167 |
| tf32 | 2.2288 | 1615 | 14.86 | 0.229 | 5.49 | 19.0 | 0.117 |
| unfused | 2.2167 | 1624 | 14.78 | 0.228 | 5.46 | 11.2 | 0.069 |
| accum 8 | 3.2017 | 1124 | 21.34 | 0.329 | 7.89 | 13.8 | 0.085 |

round value = median of the chunks' s/update (chunk = --chunk updates between two syncs); an arm's median = median of its round values; A is re-run in every arm, A and B alternate (A,B,A,B,A,B), so A's spread is that arm's own. speed_vs_a = A median / B median; b_lower_than_a_by = 1 - B/A (positive: B faster). inside_noise: |b_lower_than_a_by| < 2 x (A spread - 1). peak_alloc_gb = torch max_memory_allocated in GiB, reset before each timed run. cost_arm_usd = (A + B wall minutes) / 60 x dph. One seed, one box, one host.

