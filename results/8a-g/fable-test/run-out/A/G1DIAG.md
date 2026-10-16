# G1 diagnostic D: free measurements on the saved 3M and 10M B2 weights

device cpu, fp32, N_REG 36, register tokens ['B', 36, 256], blocks {'3M': 2, '10M': 8}. generate() self-check mismatches: 0 of 6200 rows x 2 models.

## Decision rules (sealed before the run)

- **R1 does not fire**: oracle-mode 10M gain 1.66 (bar >= +3.0; D's normal gain 1.66, G1's 1.64). 
- **R2 does not fire**: skipping blocks 3-8 at 10M: in_dist 16.10 vs intact 88.46, cost 72.35 points (bar < 1.0). 
- **R3 does not fire**: skill train loss total 3M 0.1115, 10M 0.1037, ratio 0.930 (bar <= 0.5: False); dev gain G1 +1.64, D recomputed 1.66 (flat = below 3.0: True; the sealed rule names no cutoff). 

## Oracle-mode rescoring (a row counts if ANY of NUM / WORD / GEN hits)

| rows | n | 3M normal | 3M oracle | 10M normal | 10M oracle | gain normal | gain oracle | err ratio normal | err ratio oracle |
|---|---|---|---|---|---|---|---|---|---|
| pooled-5 | 6040 | 73.03 | 73.68 | 74.69 | 75.33 | 1.66 | 1.66 | 0.939 | 0.937 |
| 13-family block | 2440 | 88.93 | 89.14 | 88.89 | 89.02 | -0.04 | -0.12 | 1.004 | 1.011 |
| 21-family block | 3600 | 62.25 | 63.19 | 65.06 | 66.06 | 2.81 | 2.86 | 0.926 | 0.922 |

Per split:

| split | n | 3M normal | 3M oracle | 10M normal | 10M oracle |
|---|---|---|---|---|---|
| in_dist | 1360 | 86.10 | 86.47 | 88.46 | 88.75 |
| answer | 1200 | 72.00 | 72.25 | 72.75 | 73.17 |
| frame | 1360 | 86.62 | 87.13 | 87.94 | 88.24 |
| vocab | 800 | 89.50 | 90.00 | 91.75 | 92.62 |
| variant | 1320 | 36.52 | 38.03 | 38.26 | 39.70 |
| family | 160 | 1.25 | 1.88 | 1.88 | 2.50 |

13-family block present: 13 of 13 (none missing); 21-family block = the 25 other families in the dev files.

## D vs G1 RESULT.json (normal pooled-5; on CPU fp32 small differences are expected)

| model | G1 | D | diff (points) | diff (rows) |
|---|---|---|---|---|
| 3M | 73.013 (4410/6040) | 73.030 (4411/6040) | 0.017 | 1 |
| 10M | 74.652 (4509/6040) | 74.685 (4511/6040) | 0.033 | 2 |

## 10M block knockout on in_dist (every round)

intact 88.46 on 1360 rows

| removed (0-based) | in_dist exact | cost vs intact |
|---|---|---|
| skip_0 | 32.72 | 55.74 |
| skip_1 | 62.13 | 26.32 |
| skip_2 | 84.34 | 4.12 |
| skip_3 | 86.62 | 1.84 |
| skip_4 | 85.66 | 2.79 |
| skip_5 | 83.38 | 5.07 |
| skip_6 | 87.06 | 1.40 |
| skip_7 | 83.97 | 4.49 |
| skip_2-7 | 16.10 | 72.35 |

## Teacher-forced loss, train sample (row means)

| group | n | model | total | prog | mode | ans | word | gen |
|---|---|---|---|---|---|---|---|---|
| web | 2000 | 3M | 2.4760 | 0.0000 | 0.4480 | 0.0000 | 0.3128 | 1.7153 |
| web | 2000 | 10M | 2.4685 | 0.0000 | 0.4493 | 0.0000 | 0.3124 | 1.7069 |
| skill | 2000 | 3M | 0.1115 | -0.0055 | 0.0067 | 0.0039 | 0.0254 | 0.0810 |
| skill | 2000 | 10M | 0.1037 | -0.0055 | 0.0073 | 0.0040 | 0.0243 | 0.0735 |

## Gold log-likelihood (teacher-forced loss) per family, dev pooled-5

| family | n | 3M total | 10M total | 3M prog | 10M prog | 3M mode | 10M mode | 3M ans | 10M ans | 3M word | 10M word | 3M gen | 10M gen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arith_bare | 160 | 0.657 | 0.053 | 0.657 | 0.053 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| backward_solve | 160 | 6.383 | 4.468 | 6.383 | 4.468 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| chain_ops | 200 | -0.003 | -0.002 | -0.003 | -0.002 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| chain_story2 | 200 | 0.677 | 1.108 | 0.677 | 1.108 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cipher_map | 120 | 0.179 | 0.201 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.179 | 0.201 |
| compare_numbers | 160 | 4.615 | 1.486 | 3.448 | 0.822 | 0.807 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 | 0.360 | 0.658 |
| copy_word | 200 | 0.540 | 1.379 | 0.000 | 0.000 | 0.077 | 0.710 | 0.000 | 0.000 | 0.463 | 0.669 | 0.000 | 0.000 |
| digits_parity | 160 | 0.974 | 0.886 | 0.003 | 0.000 | 0.000 | 0.001 | 0.000 | 0.000 | 0.000 | 0.000 | 0.970 | 0.885 |
| distance_units | 200 | 4.667 | 4.793 | 4.667 | 4.793 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| div_exact | 200 | 2.126 | 3.914 | 2.126 | 3.914 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fewshot_number_rule | 160 | 1.761 | 1.714 | 0.000 | 0.000 | 0.168 | 0.166 | 0.125 | 0.103 | 0.000 | 0.000 | 1.468 | 1.445 |
| group_induct | 120 | 0.611 | 0.627 | 0.000 | 0.000 | 0.001 | 0.000 | 0.000 | 0.000 | 0.610 | 0.627 | 0.000 | 0.000 |
| kin_chain | 200 | 0.252 | 0.148 | 0.000 | 0.000 | 0.008 | 0.005 | 0.000 | 0.000 | 0.000 | 0.001 | 0.244 | 0.142 |
| letter_ops | 200 | 0.837 | 0.691 | 0.000 | 0.000 | 0.070 | 0.001 | 0.000 | 0.000 | 0.000 | 0.000 | 0.767 | 0.689 |
| list_index | 200 | 1.493 | 1.728 | 0.000 | 0.000 | 0.130 | 0.043 | 0.000 | 0.000 | 0.962 | 1.361 | 0.401 | 0.324 |
| list_stats | 160 | 4.836 | 5.120 | 0.586 | 1.138 | 2.662 | 2.019 | 0.200 | 0.247 | 0.000 | 0.000 | 1.387 | 1.716 |
| object_track | 200 | 1.394 | 1.998 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.394 | 1.998 | 0.000 | 0.000 |
| odd_one_out | 160 | 0.509 | 0.809 | 0.000 | 0.000 | 0.001 | 0.000 | 0.509 | 0.809 | 0.000 | 0.000 | 0.000 | 0.000 |
| order_chain | 200 | 2.430 | 2.297 | 0.000 | 0.000 | 0.028 | 0.027 | 0.000 | 0.000 | 2.281 | 2.139 | 0.121 | 0.131 |
| passage_qa | 200 | 1.511 | 2.025 | 0.000 | 0.000 | 0.892 | 1.133 | 0.000 | 0.000 | 0.399 | 0.730 | 0.220 | 0.162 |
| percent_rate | 200 | 3.244 | 2.104 | 3.243 | 2.104 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| prop_eval | 120 | 1.149 | 1.272 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.149 | 1.271 | 0.000 | 0.000 |
| rule_apply | 200 | 1.230 | 1.002 | 0.000 | 0.000 | 0.018 | 0.022 | 0.002 | 0.008 | 0.052 | 0.003 | 1.158 | 0.970 |
| seq_cycle | 160 | 5.331 | 4.184 | 0.000 | 0.000 | 3.133 | 2.040 | 0.641 | 0.620 | 1.557 | 1.523 | 0.000 | 0.000 |
| seq_next | 160 | 1.428 | 1.557 | 0.000 | 0.000 | 0.002 | 0.001 | 0.000 | 0.000 | 0.000 | 0.000 | 1.426 | 1.556 |
| state_update | 200 | -0.020 | -0.020 | -0.020 | -0.020 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| story_addsub | 200 | 0.836 | 0.867 | 0.836 | 0.867 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| story_chain3 | 200 | -0.003 | 0.005 | -0.003 | 0.004 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.001 |
| syllogism | 160 | 1.386 | 1.583 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.385 | 1.583 |
| table_calc | 200 | 2.300 | 3.013 | 0.300 | 0.479 | 0.554 | 1.514 | 0.000 | 0.000 | 0.000 | 0.000 | 1.446 | 1.019 |
| table_lookup | 200 | 1.626 | 1.581 | 0.000 | 0.000 | 0.457 | 0.493 | 0.289 | 0.275 | 0.068 | 0.045 | 0.811 | 0.768 |
| var_chain | 160 | 5.709 | 5.138 | 5.706 | 5.138 | 0.000 | 0.000 | 0.002 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| verify_claim | 120 | 3.036 | 0.614 | 2.851 | 0.326 | 0.007 | 0.028 | 0.000 | 0.000 | 0.000 | 0.000 | 0.178 | 0.260 |
| word_filter | 200 | 1.495 | 1.362 | 0.000 | 0.000 | 0.015 | 0.044 | 0.000 | 0.000 | 0.000 | 0.000 | 1.479 | 1.317 |
| pooled-5 | 6040 | 1.870 | 1.762 | 0.893 | 0.753 | 0.254 | 0.245 | 0.049 | 0.056 | 0.262 | 0.308 | 0.413 | 0.400 |

## Error ledger

Wrong rows, pooled-5, by gold mode (what the labels say) x chosen mode (what the model printed), with whether its own workspace held the gold number:

**3M** (wrong per split: {'in_dist': 189, 'answer': 336, 'frame': 182, 'vocab': 84, 'variant': 838, 'family': 158})

| gold | chosen | workspace holds gold | wrong rows |
|---|---|---|---|
| gold GEN | chosen GEN | False | 793 |
| gold WORD | chosen WORD | False | 273 |
| gold NUM | chosen NUM | False | 147 |
| gold GEN | chosen GEN | True | 109 |
| gold NUM | chosen NUM | True | 106 |
| gold GEN | chosen NUM | False | 99 |
| gold NUM | chosen GEN | True | 30 |
| gold WORD | chosen GEN | False | 29 |
| gold NUM | chosen WORD | True | 19 |
| gold GEN | chosen WORD | False | 15 |
| gold GEN | chosen NUM | True | 9 |

**10M** (wrong per split: {'in_dist': 157, 'answer': 327, 'frame': 164, 'vocab': 66, 'variant': 815, 'family': 157})

| gold | chosen | workspace holds gold | wrong rows |
|---|---|---|---|
| gold GEN | chosen GEN | False | 731 |
| gold WORD | chosen WORD | False | 254 |
| gold NUM | chosen NUM | False | 141 |
| gold NUM | chosen NUM | True | 106 |
| gold GEN | chosen GEN | True | 91 |
| gold GEN | chosen NUM | False | 85 |
| gold WORD | chosen GEN | False | 54 |
| gold NUM | chosen GEN | True | 35 |
| gold NUM | chosen WORD | True | 16 |
| gold NUM | chosen GEN | False | 10 |
| gold GEN | chosen WORD | False | 4 |
| gold GEN | chosen NUM | True | 2 |

Largest cells (split | family | chosen | gold), wrong rows:

- 3M: answer|word_filter|GEN|gold GEN = 40; variant|list_stats|NUM|gold GEN = 40; variant|rule_apply|GEN|gold GEN = 40; variant|seq_next|GEN|gold GEN = 40; variant|table_calc|NUM|gold GEN = 40; family|unit_convert|NUM|gold NUM = 39; family|op_define|NUM|gold GEN = 38; family|string_transform|GEN|gold GEN = 38; variant|digits_parity|GEN|gold GEN = 36; variant|fewshot_number_rule|GEN|gold GEN = 36; variant|object_track|WORD|gold WORD = 36; in_dist|fewshot_number_rule|GEN|gold GEN = 35
- 10M: answer|word_filter|GEN|gold GEN = 40; variant|letter_ops|GEN|gold GEN = 40; variant|list_stats|NUM|gold GEN = 40; variant|rule_apply|GEN|gold GEN = 40; variant|seq_next|GEN|gold GEN = 40; variant|table_calc|NUM|gold GEN = 40; variant|object_track|WORD|gold WORD = 39; family|op_define|NUM|gold GEN = 38; frame|fewshot_number_rule|GEN|gold GEN = 36; variant|fewshot_number_rule|GEN|gold GEN = 36; family|string_transform|GEN|gold GEN = 34; in_dist|fewshot_number_rule|GEN|gold GEN = 34

Fixed / broken 3M -> 10M: pooled-5 {'fixed': 257, 'broken': 157, 'both_wrong': 1372}; by split {'in_dist': {'fixed': 64, 'broken': 32}, 'answer': {'fixed': 35, 'broken': 26}, 'frame': {'fixed': 51, 'broken': 33}, 'vocab': {'fixed': 33, 'broken': 15}, 'variant': {'fixed': 74, 'broken': 51}, 'family': {'fixed': 3, 'broken': 2}}

Most changed (split | family): variant|verify_claim +17/-5; variant|digits_parity +19/-0; answer|rule_apply +15/-2; in_dist|object_track +8/-4; variant|seq_cycle +8/-4; vocab|passage_qa +11/-1; in_dist|seq_next +5/-6; answer|seq_next +7/-3; frame|rule_apply +7/-3; in_dist|seq_cycle +8/-2; variant|div_exact +2/-8; in_dist|list_index +7/-2

Full tables: g1diag.json (ledger, wrong_by_split_family_chosen_gold, fixed_broken_3M_to_10M.by_split_family) and rows.jsonl.
