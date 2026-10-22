# G1 diagnostic D: free measurements on the saved 3M and 10M B2 weights

device cpu, fp32, N_REG 36, register tokens ['B', 36, 448], blocks {'3M': 2, '10M': 2}. generate() self-check mismatches: 0 of 6200 rows x 2 models.

## Decision rules (sealed before the run)

- **R1 does not fire**: oracle-mode 10M gain -0.30 (bar >= +3.0; D's normal gain -0.56, G1's -0.35). 
- **R2 does not fire**: skipping blocks 3-8 at 10M: in_dist n/a vs intact 87.43, cost n/a points (bar < 1.0). 
- **R3 does not fire**: skill train loss total 3M 0.1001, 10M 0.0895, ratio 0.894 (bar <= 0.5: False); dev gain G1 +1.64, D recomputed -0.56 (flat = below 3.0: True; the sealed rule names no cutoff). 

## Oracle-mode rescoring (a row counts if ANY of NUM / WORD / GEN hits)

| rows | n | 3M normal | 3M oracle | 10M normal | 10M oracle | gain normal | gain oracle | err ratio normal | err ratio oracle |
|---|---|---|---|---|---|---|---|---|---|
| pooled-5 | 6040 | 73.79 | 74.52 | 73.23 | 74.22 | -0.56 | -0.30 | 1.021 | 1.012 |
| 13-family block | 2440 | 88.65 | 88.93 | 88.52 | 88.77 | -0.12 | -0.16 | 1.011 | 1.015 |
| 21-family block | 3600 | 63.72 | 64.75 | 62.86 | 64.36 | -0.86 | -0.39 | 1.024 | 1.011 |

Per split:

| split | n | 3M normal | 3M oracle | 10M normal | 10M oracle |
|---|---|---|---|---|---|
| in_dist | 1360 | 86.91 | 87.21 | 87.43 | 87.87 |
| answer | 1200 | 71.25 | 72.42 | 71.50 | 72.08 |
| frame | 1360 | 86.47 | 86.76 | 87.35 | 87.87 |
| vocab | 800 | 91.50 | 91.88 | 90.12 | 91.00 |
| variant | 1320 | 38.79 | 40.23 | 35.38 | 37.88 |
| family | 160 | 1.88 | 3.12 | 1.88 | 1.88 |

13-family block present: 13 of 13 (none missing); 21-family block = the 25 other families in the dev files.

## D vs G1 RESULT.json (normal pooled-5; on CPU fp32 small differences are expected)

| model | G1 | D | diff (points) | diff (rows) |
|---|---|---|---|---|
| 3M | 73.675 (4450/6040) | 73.791 (4457/6040) | 0.116 | 7 |
| 10M | 73.328 (4429/6040) | 73.228 (4423/6040) | -0.099 | -6 |

## 10M block knockout on in_dist (every round)

intact 87.43 on 1360 rows

| removed (0-based) | in_dist exact | cost vs intact |
|---|---|---|
| skip_0 | 30.07 | 57.35 |
| skip_1 | 22.87 | 64.56 |

## Teacher-forced loss, train sample (row means)

| group | n | model | total | prog | mode | ans | word | gen |
|---|---|---|---|---|---|---|---|---|
| web | 2000 | 3M | 2.6345 | 0.0000 | 0.4811 | 0.0000 | 0.4290 | 1.7244 |
| web | 2000 | 10M | 2.5008 | 0.0000 | 0.4453 | 0.0000 | 0.3144 | 1.7410 |
| skill | 2000 | 3M | 0.1001 | -0.0054 | 0.0055 | 0.0043 | 0.0206 | 0.0750 |
| skill | 2000 | 10M | 0.0895 | -0.0055 | 0.0052 | 0.0032 | 0.0193 | 0.0673 |

## Gold log-likelihood (teacher-forced loss) per family, dev pooled-5

| family | n | 3M total | 10M total | 3M prog | 10M prog | 3M mode | 10M mode | 3M ans | 10M ans | 3M word | 10M word | 3M gen | 10M gen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| arith_bare | 160 | 0.212 | 0.389 | 0.212 | 0.389 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| backward_solve | 160 | 7.006 | 8.236 | 7.006 | 8.236 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| chain_ops | 200 | 0.015 | -0.003 | 0.015 | -0.003 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| chain_story2 | 200 | 1.096 | 0.408 | 1.096 | 0.408 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| cipher_map | 120 | 0.150 | 0.198 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.150 | 0.198 |
| compare_numbers | 160 | 2.350 | 1.582 | 1.975 | 0.939 | 0.147 | 0.155 | 0.000 | 0.000 | 0.000 | 0.000 | 0.228 | 0.487 |
| copy_word | 200 | 0.551 | 0.926 | 0.000 | 0.000 | 0.023 | 0.164 | 0.000 | 0.000 | 0.528 | 0.762 | 0.000 | 0.000 |
| digits_parity | 160 | 1.058 | 1.415 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.058 | 1.415 |
| distance_units | 200 | 6.497 | 5.512 | 6.497 | 5.512 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| div_exact | 200 | 4.928 | 6.052 | 4.928 | 6.052 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| fewshot_number_rule | 160 | 1.647 | 1.699 | 0.000 | 0.000 | 0.180 | 0.182 | 0.070 | 0.091 | 0.000 | 0.000 | 1.397 | 1.425 |
| group_induct | 120 | 0.553 | 0.601 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.552 | 0.600 | 0.000 | 0.000 |
| kin_chain | 200 | 0.126 | 0.128 | 0.000 | 0.000 | 0.004 | 0.006 | 0.000 | 0.000 | 0.001 | 0.000 | 0.122 | 0.121 |
| letter_ops | 200 | 0.538 | 0.698 | 0.000 | 0.000 | 0.000 | 0.153 | 0.000 | 0.000 | 0.000 | 0.000 | 0.538 | 0.545 |
| list_index | 200 | 2.297 | 1.513 | 0.000 | 0.000 | 0.061 | 0.127 | 0.000 | 0.000 | 1.832 | 1.032 | 0.404 | 0.353 |
| list_stats | 160 | 2.010 | 2.709 | 0.301 | 0.629 | 0.058 | 0.438 | 0.250 | 0.241 | 0.000 | 0.000 | 1.401 | 1.402 |
| object_track | 200 | 1.366 | 1.840 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.366 | 1.840 | 0.000 | 0.000 |
| odd_one_out | 160 | 0.595 | 0.704 | 0.000 | 0.000 | 0.000 | 0.000 | 0.595 | 0.703 | 0.000 | 0.000 | 0.000 | 0.000 |
| order_chain | 200 | 2.309 | 2.778 | 0.000 | 0.000 | 0.017 | 0.032 | 0.000 | 0.000 | 2.164 | 2.626 | 0.128 | 0.120 |
| passage_qa | 200 | 1.898 | 1.526 | 0.000 | 0.000 | 1.036 | 0.808 | 0.000 | 0.000 | 0.608 | 0.490 | 0.254 | 0.227 |
| percent_rate | 200 | 0.692 | 0.790 | 0.692 | 0.790 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| prop_eval | 120 | 1.688 | 1.206 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.688 | 1.206 | 0.000 | 0.000 |
| rule_apply | 200 | 1.278 | 1.291 | 0.000 | 0.000 | 0.016 | 0.049 | 0.007 | 0.002 | 0.006 | 0.001 | 1.249 | 1.239 |
| seq_cycle | 160 | 5.109 | 5.030 | 0.000 | 0.000 | 2.759 | 2.698 | 0.614 | 0.845 | 1.736 | 1.487 | 0.000 | 0.000 |
| seq_next | 160 | 1.316 | 1.431 | 0.000 | 0.000 | 0.001 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.315 | 1.431 |
| state_update | 200 | -0.020 | -0.004 | -0.020 | -0.004 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| story_addsub | 200 | 0.698 | 1.028 | 0.698 | 1.028 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| story_chain3 | 200 | -0.003 | -0.003 | -0.003 | -0.003 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.001 | 0.000 |
| syllogism | 160 | 1.394 | 1.298 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 1.393 | 1.298 |
| table_calc | 200 | 2.408 | 3.327 | 0.745 | 1.344 | 0.460 | 1.120 | 0.000 | 0.000 | 0.000 | 0.000 | 1.203 | 0.863 |
| table_lookup | 200 | 1.655 | 1.605 | 0.000 | 0.000 | 0.538 | 0.468 | 0.270 | 0.303 | 0.033 | 0.078 | 0.815 | 0.757 |
| var_chain | 160 | 8.150 | 7.948 | 8.149 | 7.946 | 0.000 | 0.000 | 0.001 | 0.002 | 0.000 | 0.000 | 0.000 | 0.000 |
| verify_claim | 120 | 0.296 | 1.304 | 0.205 | 1.115 | 0.001 | 0.114 | 0.000 | 0.000 | 0.000 | 0.000 | 0.090 | 0.075 |
| word_filter | 200 | 1.483 | 1.670 | 0.000 | 0.000 | 0.036 | 0.021 | 0.000 | 0.000 | 0.000 | 0.000 | 1.446 | 1.649 |
| pooled-5 | 6040 | 1.858 | 1.954 | 0.956 | 1.004 | 0.156 | 0.192 | 0.050 | 0.060 | 0.307 | 0.301 | 0.389 | 0.398 |

## Error ledger

Wrong rows, pooled-5, by gold mode (what the labels say) x chosen mode (what the model printed), with whether its own workspace held the gold number:

**3M** (wrong per split: {'in_dist': 178, 'answer': 345, 'frame': 184, 'vocab': 68, 'variant': 808, 'family': 157})

| gold | chosen | workspace holds gold | wrong rows |
|---|---|---|---|
| gold GEN | chosen GEN | False | 749 |
| gold WORD | chosen WORD | False | 285 |
| gold NUM | chosen NUM | False | 156 |
| gold GEN | chosen GEN | True | 112 |
| gold NUM | chosen NUM | True | 105 |
| gold GEN | chosen NUM | False | 94 |
| gold NUM | chosen GEN | True | 31 |
| gold WORD | chosen GEN | False | 25 |
| gold NUM | chosen WORD | True | 18 |
| gold GEN | chosen NUM | True | 6 |
| gold GEN | chosen WORD | False | 1 |
| gold NUM | chosen GEN | False | 1 |

**10M** (wrong per split: {'in_dist': 171, 'answer': 342, 'frame': 172, 'vocab': 79, 'variant': 853, 'family': 157})

| gold | chosen | workspace holds gold | wrong rows |
|---|---|---|---|
| gold GEN | chosen GEN | False | 742 |
| gold WORD | chosen WORD | False | 283 |
| gold NUM | chosen NUM | False | 153 |
| gold GEN | chosen GEN | True | 118 |
| gold GEN | chosen NUM | False | 105 |
| gold NUM | chosen NUM | True | 101 |
| gold WORD | chosen GEN | False | 32 |
| gold NUM | chosen GEN | True | 30 |
| gold NUM | chosen WORD | True | 18 |
| gold GEN | chosen WORD | False | 16 |
| gold GEN | chosen NUM | True | 9 |
| gold NUM | chosen GEN | False | 7 |
| gold WORD | chosen NUM | False | 2 |
| gold NUM | chosen WORD | False | 1 |

Largest cells (split | family | chosen | gold), wrong rows:

- 3M: answer|word_filter|GEN|gold GEN = 40; family|op_define|NUM|gold GEN = 40; variant|rule_apply|GEN|gold GEN = 40; variant|table_calc|NUM|gold GEN = 40; variant|div_exact|NUM|gold NUM = 39; variant|list_stats|NUM|gold GEN = 39; family|unit_convert|NUM|gold NUM = 38; variant|seq_next|GEN|gold GEN = 38; variant|digits_parity|GEN|gold GEN = 37; variant|object_track|WORD|gold WORD = 37; answer|fewshot_number_rule|GEN|gold GEN = 36; variant|fewshot_number_rule|GEN|gold GEN = 36
- 10M: answer|word_filter|GEN|gold GEN = 40; variant|digits_parity|GEN|gold GEN = 40; variant|seq_next|GEN|gold GEN = 40; variant|table_calc|NUM|gold GEN = 40; variant|div_exact|NUM|gold NUM = 39; variant|rule_apply|GEN|gold GEN = 38; answer|rule_apply|GEN|gold GEN = 37; variant|list_stats|NUM|gold GEN = 37; variant|object_track|WORD|gold WORD = 37; family|op_define|NUM|gold GEN = 36; variant|fewshot_number_rule|GEN|gold GEN = 36; answer|fewshot_number_rule|GEN|gold GEN = 34

Fixed / broken 3M -> 10M: pooled-5 {'fixed': 211, 'broken': 245, 'both_wrong': 1372}; by split {'in_dist': {'fixed': 54, 'broken': 47}, 'answer': {'fixed': 28, 'broken': 25}, 'frame': {'fixed': 61, 'broken': 49}, 'vocab': {'fixed': 15, 'broken': 26}, 'variant': {'fixed': 53, 'broken': 98}, 'family': {'fixed': 3, 'broken': 3}}

Most changed (split | family): in_dist|seq_next +9/-9; variant|verify_claim +0/-18; variant|odd_one_out +4/-8; variant|seq_cycle +5/-7; in_dist|fewshot_number_rule +5/-6; variant|prop_eval +2/-9; frame|list_index +5/-5; frame|seq_next +8/-2; in_dist|rule_apply +9/-1; variant|copy_word +4/-6; variant|list_index +5/-5; frame|cipher_map +2/-7

Full tables: g1diag.json (ledger, wrong_by_split_family_chosen_gold, fixed_broken_3M_to_10M.by_split_family) and rows.jsonl.
