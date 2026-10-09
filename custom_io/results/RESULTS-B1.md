# Test B1 results (students)

Seeds: [300, 301]. Scores are exact match under the round-6 scorer, in percent (unrounded in B1-ANALYSIS.json).

## Marks

| mark | verdict | mean | per seed | ahead on every seed |
|---|---|---|---|---|
| B1-a | **PROVED WRONG** | 0.78 | 300: -0.52, 301: 2.08 | False |
| B1-c | **FAIL** | -2.73 | 300: -2.60, 301: -2.86 | False |
| B1-b | **UNINFORMATIVE (intact new-kinds mean 11.20 < 20; the rule alone would say PASS)** | 9.44 | 300: 9.04, 301: 9.84 |  |
| B1-a guard: short-answer rows only | needs mean >= +10 | 0.15 | 300: 0.00, 301: 0.29 | |

## Runs

| run | valid | FRESH | R5 | R6 | new pooled | GEN-HELDOUT (GEN arm's own distribution) | in-dist held-out | donor | loops:0 | size |
|---|---|---|---|---|---|---|---|---|---|---|
| b2g_s300 | True | 48.96 | 11.98 | 9.90 | 10.94 | 95.31 | 96.57 | 7.71 | 0.00 | 10,914,681 |
| b2g_s301 | True | 48.96 | 12.50 | 7.29 | 9.90 | 96.88 | 96.36 | 5.85 | 0.00 | 10,914,681 |
| b2t_s300 | True | 22.92 | 16.15 | 4.69 | 10.42 | 22.40 | 91.06 | 9.04 | 0.78 | 10,914,681 |
| b2t_s301 | True | 22.92 | 16.15 | 7.81 | 11.98 | 23.44 | 91.32 | 9.84 | 0.78 | 10,914,681 |
| tft_s300 | True | 17.19 | 16.67 | 9.38 | 13.02 | 18.23 | 92.13 | n/a | n/a | 10,782,336 |
| tft_s301 | True | 18.23 | 20.31 | 9.38 | 14.84 | 14.58 | 92.24 | n/a | n/a | 10,782,336 |

## Read only

### Means over valid seeds

| arm | n | fresh | new_r5 | new_r6 | new_pooled | gen_heldout | in_dist_heldout | donor | loops:0 |
|---|---|---|---|---|---|---|---|---|---|
| b2t | 2 | 22.92 | 16.15 | 6.25 | 11.20 | 22.92 | 91.19 | 9.44 | 0.78 |
| b2g | 2 | 48.96 | 12.24 | 8.59 | 10.42 | 96.09 | 96.47 | 6.78 | 0.00 |
| tft | 2 | 17.71 | 18.49 | 9.38 | 13.93 | 16.41 | 92.19 | n/a | n/a |

### Difference by answer type (new kinds pooled, mean over seeds; per-seed in the JSON)

| comparison | atype | diff |
|---|---|---|
| B1-a (b2t - b2g) | span1 | 1.29 |
| B1-a (b2t - b2g) | spanN | -0.45 |
| B1-a (b2t - b2g) | yes_no | 5.68 |
| B1-c (b2t - tft) | span1 | -3.02 |
| B1-c (b2t - tft) | spanN | 0.22 |
| B1-c (b2t - tft) | yes_no | -17.05 |

### By question type, new_pooled (mean exact over valid seeds; n rows)

| question type | n | b2t | b2g | tft |
|---|---|---|---|---|
| short_answer | 340 | 7.65 | 7.50 | 8.53 |
| yes_no | 44 | 38.64 | 32.95 | 55.68 |

### By question type, fresh (mean exact over valid seeds; n rows)

| question type | n | b2t | b2g | tft |
|---|---|---|---|---|
| short_answer | 170 | 19.71 | 50.00 | 12.35 |
| yes_no | 22 | 47.73 | 40.91 | 59.09 |

### By kind, new_pooled (mean exact over valid seeds; n rows)

| kind | n | b2t | b2g | tft |
|---|---|---|---|---|
| attribute_lookup | 32 | 10.94 | 15.62 | 15.62 |
| cause_reason | 32 | 21.88 | 10.94 | 21.88 |
| counting_quantity | 32 | 6.25 | 3.12 | 9.38 |
| direction_turn | 32 | 7.81 | 3.12 | 17.19 |
| duration_length | 32 | 4.69 | 3.12 | 3.12 |
| instrument_purpose | 32 | 42.19 | 23.44 | 42.19 |
| location_tracking | 32 | 6.25 | 10.94 | 10.94 |
| price_cost | 32 | 4.69 | 4.69 | 7.81 |
| source_origin | 32 | 4.69 | 25.00 | 15.62 |
| speech_quote | 32 | 9.38 | 12.50 | 6.25 |
| time_when | 32 | 9.38 | 9.38 | 10.94 |
| weather_condition | 32 | 6.25 | 3.12 | 6.25 |

### By kind, fresh (mean exact over valid seeds; n rows)

| kind | n | b2t | b2g | tft |
|---|---|---|---|---|
| comparative_direction | 32 | 20.31 | 65.62 | 23.44 |
| event_ordering | 32 | 12.50 | 32.81 | 10.94 |
| explicit_negation_with_positive_alternative | 32 | 32.81 | 42.19 | 25.00 |
| giver_recipient_roles | 32 | 45.31 | 73.44 | 34.38 |
| two_simple_relations_combined | 32 | 18.75 | 37.50 | 12.50 |
| unambiguous_descriptive_reference | 32 | 7.81 | 42.19 | 0.00 |

### Always yes / always no (the yes/no rows)

- fresh: 22 yes/no rows of 192; always-yes scores 45.45% of them (5.21% of all rows), always-no 54.55% (6.25%)
- new_pooled: 44 yes/no rows of 384; always-yes scores 50.00% of them (5.73% of all rows), always-no 50.00% (5.73%)

### Donor and loops:0 (read only, b2t first)

| run | donor exact | skipped | donor_match | donor_position_match | pos_coincide | exact given intact right | plain exact | plain pos_coincide | loops:0 exact | loops:0 modes (question-blind talker) |
|---|---|---|---|---|---|---|---|---|---|---|
| b2g_s300 | 7.71 | 8 | 3.19 | 2.06 | 0.00 | 34.21 | 4.43 | 13.02 | 0.00 | {'NUM': 0, 'span': 0, 'GEN': 384} |
| b2g_s301 | 5.85 | 8 | 3.99 | 1.18 | 0.00 | 30.56 | 6.51 | 13.02 | 0.00 | {'NUM': 0, 'span': 0, 'GEN': 384} |
| b2t_s300 | 9.04 | 8 | 3.46 | 7.06 | 0.00 | 27.03 | 4.69 | 13.02 | 0.78 | {'NUM': 0, 'span': 384, 'GEN': 0} |
| b2t_s301 | 9.84 | 8 | 4.26 | 7.35 | 0.00 | 28.57 | 5.73 | 13.02 | 0.78 | {'NUM': 0, 'span': 384, 'GEN': 0} |
| tft_s300 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| tft_s301 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

### Reachability (share of new-kinds-pooled rows the talker can emit at all)

- b2g_s300: 100.00%
- b2g_s301: 100.00%
- b2t_s300: 100.00%
- b2t_s301: 100.00%
- tft_s300: 100.00%
- tft_s301: 100.00%

### Distance to the references (mean over valid seeds)

- b2t: fresh - bare 8-shot -52.08, new_r5 - bare 8-shot -51.55, new_r6 - bare 8-shot -71.35, fresh - sandwich -69.28, new_pooled - sandwich -67.00
- b2g: fresh - bare 8-shot -26.04, new_r5 - bare 8-shot -55.46, new_r6 - bare 8-shot -69.01, fresh - sandwich -43.24, new_pooled - sandwich -67.78
- tft: fresh - bare 8-shot -57.29, new_r5 - bare 8-shot -49.21, new_r6 - bare 8-shot -68.22, fresh - sandwich -74.49, new_pooled - sandwich -64.27

References: bare 1.2B 8-shot 75.0 FRESH, 67.7 R5, 77.6 R6; today's sandwich 92.2 FRESH, 78.2 new pooled.

GEN-HELDOUT-R4 is the GEN arm's own distribution (most of its names and nouns are in that arm's training pools) and is never subtracted across arms.
