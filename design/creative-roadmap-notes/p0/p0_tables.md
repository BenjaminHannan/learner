
## B2_s100  (N=32, temps=[0.7, 1.0, 1.5], seed=20261006, torch 2.14.1+cu130)

Greedy on the full splits (CPU fp32): frame 85.59% of 1360 (196 wrong rows probed); vocab 88.00% of 800 (96 wrong rows probed)

### heldout/prog  (n=160 rows; greedy modes {'NUM': 105, 'GEN': 39, 'WORD': 16})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.6 | 0.7 | 1.1 | 1.2 | 1.2 | 2 | +0.6 | COLD START | 2.17 / 2 / 10 | 15.9 | 14.4 | 67.3 | 98.5 | 65.5 |
| 1.0 | 0.6 | 0.7 | 1.2 | 1.2 | 1.2 | 2 | +0.6 | COLD START | 2.84 / 2 / 12 | 19.6 | 19.8 | 77.5 | 98.3 | 65.1 |
| 1.5 | 0.6 | 0.7 | 1.5 | 1.9 | 1.9 | 3 | +1.2 | COLD START | 3.74 / 3 / 19 | 24.3 | 27.6 | 87.7 | 98.0 | 64.6 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| clock_date | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 2.70 |
| op_define | 40 | 0.0 | 0.0 | 0.0 | 2.5 | 1 | 4.03 |
| string_transform | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.15 |
| unit_convert | 40 | 2.5 | 5.0 | 5.0 | 5.0 | 2 | 3.48 |

Rows greedy misses that some sample hits (any T): 2
- op_define-DF1-36 (op_define): answer '2', greedy '0', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 3}
- unit_convert-DF1-18 (unit_convert): answer '252', greedy '1764', hits of 32 by T {0.7: 4, 1.0: 6, 1.5: 6}

### heldout/all  (n=160 rows; greedy modes {'NUM': 105, 'GEN': 39, 'WORD': 16})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.6 | 0.7 | 1.2 | 1.2 | 1.2 | 2 | +0.6 | exploratory | 2.75 / 2 / 11 | 15.6 | 21.7 | 67.7 | 98.6 | 65.7 |
| 1.0 | 0.6 | 0.9 | 1.7 | 1.9 | 1.9 | 3 | +1.2 | exploratory | 3.71 / 3 / 17 | 19.4 | 27.7 | 77.1 | 98.3 | 65.4 |
| 1.5 | 0.6 | 0.8 | 1.9 | 3.1 | 3.1 | 5 | +2.5 | exploratory | 5.42 / 5 / 17 | 24.3 | 40.2 | 87.6 | 97.7 | 64.6 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| clock_date | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 3.33 |
| op_define | 40 | 0.0 | 0.0 | 2.5 | 2.5 | 1 | 4.33 |
| string_transform | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 3.62 |
| unit_convert | 40 | 2.5 | 5.0 | 5.0 | 10.0 | 4 | 3.55 |

Rows greedy misses that some sample hits (any T): 4
- op_define-DF1-36 (op_define): answer '2', greedy '0', hits of 32 by T {0.7: 0, 1.0: 4, 1.5: 4}
- unit_convert-DF1-18 (unit_convert): answer '252', greedy '1764', hits of 32 by T {0.7: 6, 1.0: 10, 1.5: 7}
- unit_convert-DF1-32 (unit_convert): answer '72', greedy '21', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- unit_convert-DF1-4 (unit_convert): answer '10', greedy '-2', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}

### frame_wrong/prog  (n=196 rows; greedy modes {'GEN': 116, 'WORD': 58, 'NUM': 22})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.0 | 1.7 | 6.9 | 10.7 | 10.7 | 21 | +10.7 | (rescue rate; SIGNAL by the same lines) | 1.21 / 1 / 5 | 18.8 | 2.8 | 68.3 | 100.0 | 4.6 |
| 1.0 | 0.0 | 2.2 | 9.2 | 13.3 | 13.3 | 26 | +13.3 | (rescue rate; SIGNAL by the same lines) | 1.26 / 1 / 7 | 22.6 | 3.9 | 77.2 | 100.0 | 4.6 |
| 1.5 | 0.0 | 3.2 | 12.1 | 17.3 | 17.3 | 34 | +17.3 | (rescue rate; SIGNAL by the same lines) | 1.36 / 1 / 8 | 26.7 | 5.4 | 87.0 | 100.0 | 4.8 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| cipher_map | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| copy_word | 8 | 0.0 | 12.5 | 12.5 | 12.5 | 1 | 1.12 |
| digits_parity | 7 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| fewshot_number_rule | 29 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| group_induct | 4 | 0.0 | 0.0 | 0.0 | 50.0 | 2 | 1.00 |
| kin_chain | 11 | 0.0 | 9.1 | 0.0 | 9.1 | 1 | 1.00 |
| letter_ops | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.50 |
| list_index | 17 | 0.0 | 5.9 | 17.6 | 17.6 | 3 | 1.18 |
| list_stats | 5 | 0.0 | 0.0 | 0.0 | 60.0 | 3 | 1.20 |
| object_track | 9 | 0.0 | 33.3 | 33.3 | 55.6 | 5 | 1.56 |
| odd_one_out | 2 | 0.0 | 50.0 | 50.0 | 50.0 | 1 | 1.50 |
| order_chain | 18 | 0.0 | 11.1 | 5.6 | 11.1 | 2 | 1.22 |
| passage_qa | 6 | 0.0 | 33.3 | 33.3 | 33.3 | 2 | 1.33 |
| prop_eval | 7 | 0.0 | 28.6 | 71.4 | 71.4 | 5 | 1.71 |
| rule_apply | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| seq_cycle | 7 | 0.0 | 14.3 | 28.6 | 0.0 | 0 | 1.29 |
| seq_next | 6 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| state_update | 1 | 0.0 | 100.0 | 100.0 | 100.0 | 1 | 2.00 |
| table_calc | 8 | 0.0 | 62.5 | 75.0 | 87.5 | 7 | 3.88 |
| table_lookup | 28 | 0.0 | 3.6 | 3.6 | 3.6 | 1 | 1.04 |
| verify_claim | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| word_filter | 7 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |

Rows greedy misses that some sample hits (any T): 36
- copy_word-Df1-537 (copy_word): answer 'yula', greedy 'out', hits of 32 by T {0.7: 1, 1.0: 4, 1.5: 11}
- group_induct-Df1-253 (group_induct): answer 'B', greedy 'A', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- group_induct-Df1-41 (group_induct): answer 'B', greedy 'A', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 2}
- kin_chain-Df1-311 (kin_chain): answer 'Gus', greedy 'out', hits of 32 by T {0.7: 2, 1.0: 0, 1.5: 5}
- list_index-Df1-1440 (list_index): answer 'spider', greedy 'button', hits of 32 by T {0.7: 0, 1.0: 2, 1.5: 2}
- list_index-Df1-669 (list_index): answer 'pocket', greedy 'magnet', hits of 32 by T {0.7: 5, 1.0: 8, 1.5: 11}
- list_index-Df1-843 (list_index): answer 'river', greedy 'hammer', hits of 32 by T {0.7: 0, 1.0: 4, 1.5: 4}
- list_stats-Df1-129 (list_stats): answer '89', greedy '80', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- list_stats-Df1-151 (list_stats): answer '15', greedy '23', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- list_stats-Df1-286 (list_stats): answer '45', greedy '44', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- object_track-Df1-139 (object_track): answer 'saddle', greedy 'Please', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- object_track-Df1-423 (object_track): answer 'falcon', greedy 'bridge', hits of 32 by T {0.7: 0, 1.0: 4, 1.5: 9}
- ... 24 more

### frame_wrong/all  (n=196 rows; greedy modes {'GEN': 116, 'WORD': 58, 'NUM': 22})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.0 | 3.9 | 16.2 | 26.0 | 26.0 | 51 | +26.0 | exploratory | 2.51 / 2 / 12 | 18.8 | 17.0 | 67.7 | 100.0 | 4.6 |
| 1.0 | 0.0 | 5.2 | 21.5 | 34.7 | 34.7 | 68 | +34.7 | exploratory | 3.22 / 2 / 14 | 22.9 | 24.2 | 78.0 | 100.0 | 4.6 |
| 1.5 | 0.0 | 7.3 | 30.2 | 46.4 | 46.4 | 91 | +46.4 | exploratory | 4.52 / 3 / 19 | 26.6 | 33.2 | 86.6 | 99.9 | 4.9 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| cipher_map | 1 | 0.0 | 100.0 | 100.0 | 100.0 | 1 | 2.00 |
| copy_word | 8 | 0.0 | 12.5 | 12.5 | 25.0 | 2 | 1.12 |
| digits_parity | 7 | 0.0 | 42.9 | 42.9 | 42.9 | 3 | 1.57 |
| fewshot_number_rule | 29 | 0.0 | 27.6 | 44.8 | 51.7 | 15 | 5.45 |
| group_induct | 4 | 0.0 | 0.0 | 0.0 | 50.0 | 2 | 1.00 |
| kin_chain | 11 | 0.0 | 18.2 | 18.2 | 36.4 | 4 | 2.55 |
| letter_ops | 2 | 0.0 | 0.0 | 0.0 | 50.0 | 1 | 1.50 |
| list_index | 17 | 0.0 | 29.4 | 35.3 | 47.1 | 8 | 2.35 |
| list_stats | 5 | 0.0 | 20.0 | 20.0 | 20.0 | 1 | 5.20 |
| object_track | 9 | 0.0 | 33.3 | 55.6 | 33.3 | 3 | 1.89 |
| odd_one_out | 2 | 0.0 | 0.0 | 0.0 | 50.0 | 1 | 1.00 |
| order_chain | 18 | 0.0 | 11.1 | 16.7 | 33.3 | 6 | 1.61 |
| passage_qa | 6 | 0.0 | 66.7 | 83.3 | 83.3 | 5 | 1.83 |
| prop_eval | 7 | 0.0 | 42.9 | 42.9 | 71.4 | 5 | 1.43 |
| rule_apply | 9 | 0.0 | 0.0 | 33.3 | 44.4 | 4 | 3.33 |
| seq_cycle | 7 | 0.0 | 0.0 | 14.3 | 42.9 | 3 | 1.29 |
| seq_next | 6 | 0.0 | 100.0 | 83.3 | 100.0 | 6 | 4.17 |
| state_update | 1 | 0.0 | 0.0 | 100.0 | 100.0 | 1 | 2.00 |
| table_calc | 8 | 0.0 | 62.5 | 62.5 | 87.5 | 7 | 3.50 |
| table_lookup | 28 | 0.0 | 10.7 | 17.9 | 25.0 | 7 | 5.75 |
| verify_claim | 4 | 0.0 | 25.0 | 25.0 | 25.0 | 1 | 3.50 |
| word_filter | 7 | 0.0 | 42.9 | 57.1 | 71.4 | 5 | 1.86 |

Rows greedy misses that some sample hits (any T): 93
- cipher_map-Df1-206 (cipher_map): answer '9 3 6', greedy '9 6 6', hits of 32 by T {0.7: 1, 1.0: 3, 1.5: 1}
- copy_word-Df1-537 (copy_word): answer 'yula', greedy 'out', hits of 32 by T {0.7: 3, 1.0: 2, 1.5: 6}
- copy_word-Df1-907 (copy_word): answer 'nejozi', greedy 'out', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- digits_parity-Df1-23 (digits_parity): answer '18', greedy '17', hits of 32 by T {0.7: 1, 1.0: 2, 1.5: 12}
- digits_parity-Df1-26 (digits_parity): answer '22', greedy '21', hits of 32 by T {0.7: 2, 1.0: 2, 1.5: 4}
- digits_parity-Df1-38 (digits_parity): answer '16', greedy '17', hits of 32 by T {0.7: 1, 1.0: 2, 1.5: 5}
- fewshot_number_rule-Df1-100 (fewshot_number_rule): answer '126', greedy '108', hits of 32 by T {0.7: 2, 1.0: 2, 1.5: 3}
- fewshot_number_rule-Df1-149 (fewshot_number_rule): answer '34', greedy '30', hits of 32 by T {0.7: 4, 1.0: 12, 1.5: 13}
- fewshot_number_rule-Df1-180 (fewshot_number_rule): answer '41', greedy '40', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 1}
- fewshot_number_rule-Df1-185 (fewshot_number_rule): answer '16', greedy '18', hits of 32 by T {0.7: 20, 1.0: 19, 1.5: 10}
- fewshot_number_rule-Df1-200 (fewshot_number_rule): answer '86', greedy '76', hits of 32 by T {0.7: 0, 1.0: 7, 1.5: 2}
- fewshot_number_rule-Df1-308 (fewshot_number_rule): answer '-26', greedy '-28', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 3}
- ... 81 more

### vocab_wrong/prog  (n=96 rows; greedy modes {'GEN': 50, 'WORD': 27, 'NUM': 19})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.0 | 2.2 | 9.6 | 15.6 | 15.6 | 15 | +15.6 | (rescue rate; SIGNAL by the same lines) | 1.38 / 1 / 5 | 19.5 | 4.6 | 68.8 | 100.0 | 17.7 |
| 1.0 | 0.0 | 3.8 | 15.1 | 19.8 | 19.8 | 19 | +19.8 | (rescue rate; SIGNAL by the same lines) | 1.54 / 1 / 7 | 24.0 | 7.2 | 79.7 | 100.0 | 17.7 |
| 1.5 | 0.0 | 4.8 | 18.2 | 25.0 | 25.0 | 24 | +25.0 | (rescue rate; SIGNAL by the same lines) | 1.79 / 1 / 7 | 27.4 | 10.4 | 88.0 | 100.0 | 17.7 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| kin_chain | 10 | 0.0 | 0.0 | 0.0 | 10.0 | 1 | 1.00 |
| letter_ops | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| list_index | 12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| object_track | 6 | 0.0 | 16.7 | 16.7 | 16.7 | 1 | 1.17 |
| order_chain | 14 | 0.0 | 7.1 | 14.3 | 28.6 | 4 | 1.14 |
| passage_qa | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| rule_apply | 8 | 0.0 | 50.0 | 50.0 | 50.0 | 4 | 1.62 |
| table_calc | 17 | 0.0 | 52.9 | 70.6 | 76.5 | 13 | 3.59 |
| table_lookup | 23 | 0.0 | 0.0 | 0.0 | 4.3 | 1 | 1.00 |
| word_filter | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |

Rows greedy misses that some sample hits (any T): 24
- kin_chain-Dv1-145 (kin_chain): answer 'Tess', greedy 'Ola', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 4}
- object_track-Dv1-52 (object_track): answer 'stone', greedy 'dragon', hits of 32 by T {0.7: 11, 1.0: 14, 1.5: 13}
- order_chain-Dv1-112 (order_chain): answer 'Wren', greedy 'Gil', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- order_chain-Dv1-127 (order_chain): answer 'Fay', greedy 'Val', hits of 32 by T {0.7: 7, 1.0: 11, 1.5: 17}
- order_chain-Dv1-151 (order_chain): answer 'Dax', greedy 'Ola', hits of 32 by T {0.7: 0, 1.0: 2, 1.5: 6}
- order_chain-Dv1-24 (order_chain): answer 'Uma', greedy 'Gil', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 2}
- rule_apply-Dv1-12 (rule_apply): answer 'hide', greedy 'go', hits of 32 by T {0.7: 4, 1.0: 4, 1.5: 11}
- rule_apply-Dv1-174 (rule_apply): answer 'jump', greedy 'hide', hits of 32 by T {0.7: 1, 1.0: 6, 1.5: 7}
- rule_apply-Dv1-245 (rule_apply): answer 'turn', greedy 'hide', hits of 32 by T {0.7: 1, 1.0: 3, 1.5: 3}
- rule_apply-Dv1-26 (rule_apply): answer 'sing', greedy 'go', hits of 32 by T {0.7: 2, 1.0: 6, 1.5: 8}
- table_calc-Dv1-100 (table_calc): answer '20', greedy '32', hits of 32 by T {0.7: 12, 1.0: 10, 1.5: 18}
- table_calc-Dv1-109 (table_calc): answer '6', greedy '12', hits of 32 by T {0.7: 3, 1.0: 7, 1.5: 5}
- ... 12 more

### vocab_wrong/all  (n=96 rows; greedy modes {'GEN': 50, 'WORD': 27, 'NUM': 19})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.0 | 5.4 | 20.1 | 28.1 | 28.1 | 27 | +28.1 | exploratory | 2.42 / 2 / 9 | 19.5 | 17.6 | 68.9 | 100.0 | 17.7 |
| 1.0 | 0.0 | 6.2 | 23.6 | 35.4 | 35.4 | 34 | +35.4 | exploratory | 3.34 / 2 / 15 | 23.9 | 24.0 | 79.5 | 100.0 | 17.7 |
| 1.5 | 0.0 | 6.6 | 28.2 | 43.8 | 43.8 | 42 | +43.8 | exploratory | 4.40 / 3 / 19 | 27.2 | 32.5 | 87.5 | 100.0 | 17.7 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| kin_chain | 10 | 0.0 | 10.0 | 20.0 | 20.0 | 2 | 2.30 |
| letter_ops | 2 | 0.0 | 0.0 | 50.0 | 50.0 | 1 | 2.00 |
| list_index | 12 | 0.0 | 41.7 | 41.7 | 66.7 | 8 | 2.92 |
| object_track | 6 | 0.0 | 16.7 | 16.7 | 16.7 | 1 | 1.17 |
| order_chain | 14 | 0.0 | 14.3 | 21.4 | 35.7 | 5 | 1.93 |
| passage_qa | 2 | 0.0 | 50.0 | 50.0 | 50.0 | 1 | 2.00 |
| rule_apply | 8 | 0.0 | 50.0 | 50.0 | 50.0 | 4 | 1.62 |
| table_calc | 17 | 0.0 | 58.8 | 70.6 | 70.6 | 12 | 4.12 |
| table_lookup | 23 | 0.0 | 4.3 | 13.0 | 26.1 | 6 | 5.74 |
| word_filter | 2 | 0.0 | 100.0 | 100.0 | 100.0 | 2 | 3.00 |

Rows greedy misses that some sample hits (any T): 45
- kin_chain-Dv1-145 (kin_chain): answer 'Tess', greedy 'Ola', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 2}
- kin_chain-Dv1-166 (kin_chain): answer 'no', greedy 'yns', hits of 32 by T {0.7: 3, 1.0: 1, 1.5: 2}
- letter_ops-Dv1-154 (letter_ops): answer '2', greedy '1', hits of 32 by T {0.7: 0, 1.0: 4, 1.5: 3}
- list_index-Dv1-134 (list_index): answer '4', greedy '1', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- list_index-Dv1-16 (list_index): answer '4', greedy '5', hits of 32 by T {0.7: 1, 1.0: 4, 1.5: 2}
- list_index-Dv1-39 (list_index): answer '6', greedy '2', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 2}
- list_index-Dv1-46 (list_index): answer '2', greedy '5', hits of 32 by T {0.7: 4, 1.0: 2, 1.5: 6}
- list_index-Dv1-51 (list_index): answer '6', greedy '4', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- list_index-Dv1-63 (list_index): answer '2', greedy '4', hits of 32 by T {0.7: 8, 1.0: 10, 1.5: 9}
- list_index-Dv1-90 (list_index): answer '4', greedy '2', hits of 32 by T {0.7: 17, 1.0: 10, 1.5: 9}
- list_index-Dv1-92 (list_index): answer '5', greedy '2', hits of 32 by T {0.7: 3, 1.0: 2, 1.5: 3}
- object_track-Dv1-52 (object_track): answer 'stone', greedy 'dragon', hits of 32 by T {0.7: 14, 1.0: 13, 1.5: 15}
- ... 33 more


## B2_s101  (N=32, temps=[0.7, 1.0, 1.5], seed=20261006, torch 2.14.1+cu130)

Greedy on the full splits (CPU fp32): frame 87.72% of 1360 (167 wrong rows probed); vocab 87.12% of 800 (103 wrong rows probed)

### heldout/prog  (n=160 rows; greedy modes {'GEN': 66, 'NUM': 79, 'WORD': 15})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 1.2 | 1.5 | 3.3 | 4.4 | 4.4 | 7 | +3.1 | WEAK SIGNAL | 1.95 / 2 / 7 | 19.2 | 13.3 | 74.3 | 93.8 | 54.7 |
| 1.0 | 1.2 | 1.1 | 3.1 | 4.4 | 4.4 | 7 | +3.1 | WEAK SIGNAL | 2.58 / 2 / 10 | 23.2 | 18.3 | 84.5 | 93.6 | 55.3 |
| 1.5 | 1.2 | 1.2 | 3.7 | 5.6 | 5.6 | 9 | +4.4 | WEAK SIGNAL | 3.56 / 3 / 15 | 27.7 | 26.5 | 92.9 | 94.3 | 56.3 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| clock_date | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 2.38 |
| op_define | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 2.92 |
| string_transform | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.43 |
| unit_convert | 40 | 5.0 | 17.5 | 17.5 | 22.5 | 9 | 3.60 |

Rows greedy misses that some sample hits (any T): 7
- unit_convert-DF1-14 (unit_convert): answer '80', greedy '2', hits of 32 by T {0.7: 2, 1.0: 3, 1.5: 1}
- unit_convert-DF1-15 (unit_convert): answer '7', greedy '41', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- unit_convert-DF1-19 (unit_convert): answer '8', greedy '4', hits of 32 by T {0.7: 3, 1.0: 1, 1.5: 3}
- unit_convert-DF1-20 (unit_convert): answer '104', greedy '21', hits of 32 by T {0.7: 11, 1.0: 7, 1.5: 9}
- unit_convert-DF1-27 (unit_convert): answer '144', greedy '96', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- unit_convert-DF1-3 (unit_convert): answer '55', greedy '6', hits of 32 by T {0.7: 1, 1.0: 2, 1.5: 6}
- unit_convert-DF1-32 (unit_convert): answer '72', greedy '63', hits of 32 by T {0.7: 11, 1.0: 4, 1.5: 6}

### heldout/all  (n=160 rows; greedy modes {'GEN': 66, 'NUM': 79, 'WORD': 15})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 1.2 | 1.2 | 3.0 | 3.8 | 3.8 | 6 | +2.5 | exploratory | 3.15 / 3 / 11 | 19.3 | 26.3 | 74.6 | 93.9 | 54.6 |
| 1.0 | 1.2 | 1.4 | 3.6 | 5.0 | 5.0 | 8 | +3.8 | exploratory | 4.31 / 4 / 16 | 23.3 | 33.6 | 83.5 | 94.0 | 55.3 |
| 1.5 | 1.2 | 1.4 | 4.2 | 6.2 | 6.2 | 10 | +5.0 | exploratory | 6.82 / 6 / 22 | 27.8 | 46.4 | 93.3 | 93.8 | 56.2 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| clock_date | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 4.03 |
| op_define | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 5.25 |
| string_transform | 40 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 4.12 |
| unit_convert | 40 | 5.0 | 15.0 | 20.0 | 25.0 | 10 | 3.83 |

Rows greedy misses that some sample hits (any T): 8
- unit_convert-DF1-14 (unit_convert): answer '80', greedy '2', hits of 32 by T {0.7: 1, 1.0: 4, 1.5: 2}
- unit_convert-DF1-15 (unit_convert): answer '7', greedy '41', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- unit_convert-DF1-19 (unit_convert): answer '8', greedy '4', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 6}
- unit_convert-DF1-20 (unit_convert): answer '104', greedy '21', hits of 32 by T {0.7: 7, 1.0: 8, 1.5: 15}
- unit_convert-DF1-25 (unit_convert): answer '54', greedy '-45', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 1}
- unit_convert-DF1-27 (unit_convert): answer '144', greedy '96', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- unit_convert-DF1-3 (unit_convert): answer '55', greedy '6', hits of 32 by T {0.7: 5, 1.0: 4, 1.5: 4}
- unit_convert-DF1-32 (unit_convert): answer '72', greedy '63', hits of 32 by T {0.7: 7, 1.0: 11, 1.5: 7}

### frame_wrong/prog  (n=167 rows; greedy modes {'GEN': 117, 'WORD': 35, 'NUM': 15})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.0 | 1.1 | 3.1 | 4.8 | 4.8 | 8 | +4.8 | (rescue rate; WEAK SIGNAL by the same lines) | 1.11 / 1 / 4 | 23.5 | 1.6 | 82.6 | 100.0 | 3.6 |
| 1.0 | 0.0 | 1.4 | 6.1 | 10.2 | 10.2 | 17 | +10.2 | (rescue rate; SIGNAL by the same lines) | 1.18 / 1 / 6 | 27.3 | 2.2 | 90.5 | 100.0 | 3.6 |
| 1.5 | 0.0 | 2.2 | 9.3 | 13.8 | 13.8 | 23 | +13.8 | (rescue rate; SIGNAL by the same lines) | 1.23 / 1 / 4 | 30.1 | 3.5 | 96.1 | 100.0 | 3.7 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| cipher_map | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| copy_word | 1 | 0.0 | 0.0 | 100.0 | 100.0 | 1 | 2.00 |
| digits_parity | 6 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| div_exact | 1 | 0.0 | 100.0 | 100.0 | 100.0 | 1 | 2.00 |
| fewshot_number_rule | 31 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| kin_chain | 12 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| letter_ops | 10 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.30 |
| list_index | 13 | 0.0 | 0.0 | 7.7 | 7.7 | 1 | 1.08 |
| list_stats | 4 | 0.0 | 0.0 | 25.0 | 25.0 | 1 | 2.25 |
| object_track | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| odd_one_out | 2 | 0.0 | 0.0 | 100.0 | 100.0 | 2 | 2.50 |
| order_chain | 14 | 0.0 | 0.0 | 7.1 | 21.4 | 3 | 1.14 |
| passage_qa | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| prop_eval | 3 | 0.0 | 0.0 | 0.0 | 33.3 | 1 | 1.00 |
| rule_apply | 6 | 0.0 | 16.7 | 16.7 | 16.7 | 1 | 1.17 |
| seq_cycle | 8 | 0.0 | 50.0 | 75.0 | 75.0 | 6 | 1.75 |
| seq_next | 7 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| table_calc | 4 | 0.0 | 25.0 | 25.0 | 50.0 | 2 | 2.25 |
| table_lookup | 29 | 0.0 | 3.4 | 6.9 | 13.8 | 4 | 1.07 |
| verify_claim | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| word_filter | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |

Rows greedy misses that some sample hits (any T): 23
- copy_word-Df1-162 (copy_word): answer 'nuse', greedy 'out', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 3}
- div_exact-Df1-233 (div_exact): answer '12', greedy '588', hits of 32 by T {0.7: 6, 1.0: 7, 1.5: 11}
- list_index-Df1-1440 (list_index): answer 'spider', greedy 'saddle', hits of 32 by T {0.7: 0, 1.0: 4, 1.5: 7}
- list_stats-Df1-315 (list_stats): answer '2', greedy '28', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 1}
- odd_one_out-Df1-266 (odd_one_out): answer '73', greedy '42', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 3}
- odd_one_out-Df1-323 (odd_one_out): answer '74', greedy '70', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 5}
- order_chain-Df1-1189 (order_chain): answer 'Sue', greedy 'Cy', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- order_chain-Df1-554 (order_chain): answer 'Zoe', greedy 'Sue', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- order_chain-Df1-669 (order_chain): answer 'Cy', greedy 'Fay', hits of 32 by T {0.7: 0, 1.0: 4, 1.5: 5}
- prop_eval-Df1-55 (prop_eval): answer 'true', greedy 'false', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 3}
- rule_apply-Df1-641 (rule_apply): answer 'go', greedy 'out', hits of 32 by T {0.7: 11, 1.0: 14, 1.5: 9}
- seq_cycle-Df1-173 (seq_cycle): answer 'w', greedy 'p', hits of 32 by T {0.7: 0, 1.0: 2, 1.5: 5}
- ... 11 more

### frame_wrong/all  (n=167 rows; greedy modes {'GEN': 117, 'WORD': 35, 'NUM': 15})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.0 | 4.1 | 14.8 | 22.8 | 22.8 | 38 | +22.8 | exploratory | 2.54 / 2 / 14 | 23.5 | 18.0 | 82.6 | 100.0 | 3.6 |
| 1.0 | 0.0 | 4.7 | 18.8 | 31.1 | 31.1 | 52 | +31.1 | exploratory | 3.51 / 2 / 19 | 27.2 | 25.1 | 89.7 | 100.0 | 3.6 |
| 1.5 | 0.0 | 6.8 | 27.1 | 40.1 | 40.1 | 67 | +40.1 | exploratory | 4.74 / 4 / 25 | 30.0 | 34.1 | 96.0 | 100.0 | 3.7 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| cipher_map | 4 | 0.0 | 50.0 | 75.0 | 75.0 | 3 | 2.25 |
| copy_word | 1 | 0.0 | 0.0 | 0.0 | 100.0 | 1 | 1.00 |
| digits_parity | 6 | 0.0 | 50.0 | 50.0 | 66.7 | 4 | 2.00 |
| div_exact | 1 | 0.0 | 100.0 | 100.0 | 100.0 | 1 | 2.00 |
| fewshot_number_rule | 31 | 0.0 | 19.4 | 22.6 | 32.3 | 10 | 5.35 |
| kin_chain | 12 | 0.0 | 0.0 | 16.7 | 8.3 | 1 | 3.00 |
| letter_ops | 10 | 0.0 | 10.0 | 20.0 | 20.0 | 2 | 2.70 |
| list_index | 13 | 0.0 | 23.1 | 53.8 | 53.8 | 7 | 2.69 |
| list_stats | 4 | 0.0 | 0.0 | 25.0 | 25.0 | 1 | 5.25 |
| object_track | 3 | 0.0 | 0.0 | 0.0 | 66.7 | 2 | 1.00 |
| odd_one_out | 2 | 0.0 | 100.0 | 100.0 | 100.0 | 2 | 2.50 |
| order_chain | 14 | 0.0 | 7.1 | 7.1 | 28.6 | 4 | 2.29 |
| passage_qa | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.50 |
| prop_eval | 3 | 0.0 | 0.0 | 0.0 | 33.3 | 1 | 1.00 |
| rule_apply | 6 | 0.0 | 33.3 | 33.3 | 50.0 | 3 | 2.17 |
| seq_cycle | 8 | 0.0 | 62.5 | 75.0 | 75.0 | 6 | 1.75 |
| seq_next | 7 | 0.0 | 71.4 | 71.4 | 85.7 | 6 | 4.43 |
| table_calc | 4 | 0.0 | 25.0 | 25.0 | 25.0 | 1 | 2.50 |
| table_lookup | 29 | 0.0 | 13.8 | 24.1 | 34.5 | 10 | 5.28 |
| verify_claim | 3 | 0.0 | 33.3 | 33.3 | 33.3 | 1 | 1.67 |
| word_filter | 4 | 0.0 | 25.0 | 25.0 | 25.0 | 1 | 1.25 |

Rows greedy misses that some sample hits (any T): 73
- cipher_map-Df1-206 (cipher_map): answer '9 3 6', greedy '3 3 6', hits of 32 by T {0.7: 0, 1.0: 2, 1.5: 7}
- cipher_map-Df1-223 (cipher_map): answer '7 2 2', greedy '2 2 2', hits of 32 by T {0.7: 11, 1.0: 10, 1.5: 11}
- cipher_map-Df1-88 (cipher_map): answer '5 5 5', greedy '5 2 5', hits of 32 by T {0.7: 3, 1.0: 2, 1.5: 6}
- copy_word-Df1-162 (copy_word): answer 'nuse', greedy 'out', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 7}
- digits_parity-Df1-221 (digits_parity): answer '19', greedy '18', hits of 32 by T {0.7: 5, 1.0: 2, 1.5: 5}
- digits_parity-Df1-26 (digits_parity): answer '22', greedy '21', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 2}
- digits_parity-Df1-306 (digits_parity): answer '11', greedy '12', hits of 32 by T {0.7: 11, 1.0: 10, 1.5: 20}
- digits_parity-Df1-384 (digits_parity): answer '26', greedy '28', hits of 32 by T {0.7: 14, 1.0: 13, 1.5: 8}
- div_exact-Df1-233 (div_exact): answer '12', greedy '588', hits of 32 by T {0.7: 4, 1.0: 6, 1.5: 12}
- fewshot_number_rule-Df1-100 (fewshot_number_rule): answer '126', greedy '122', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 0}
- fewshot_number_rule-Df1-149 (fewshot_number_rule): answer '34', greedy '30', hits of 32 by T {0.7: 9, 1.0: 7, 1.5: 12}
- fewshot_number_rule-Df1-185 (fewshot_number_rule): answer '16', greedy '10', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- ... 61 more

### vocab_wrong/prog  (n=103 rows; greedy modes {'GEN': 57, 'WORD': 28, 'NUM': 18})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.0 | 1.6 | 6.5 | 10.7 | 10.7 | 11 | +10.7 | (rescue rate; SIGNAL by the same lines) | 1.19 / 1 / 4 | 24.7 | 2.9 | 85.7 | 100.0 | 12.7 |
| 1.0 | 0.0 | 2.2 | 9.0 | 14.6 | 14.6 | 15 | +14.6 | (rescue rate; SIGNAL by the same lines) | 1.27 / 1 / 4 | 27.9 | 4.5 | 92.3 | 100.0 | 12.7 |
| 1.5 | 0.0 | 2.9 | 10.9 | 16.5 | 16.5 | 17 | +16.5 | (rescue rate; SIGNAL by the same lines) | 1.34 / 1 / 5 | 30.2 | 6.2 | 96.7 | 100.0 | 12.7 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| kin_chain | 14 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| letter_ops | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| list_index | 14 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| object_track | 5 | 0.0 | 80.0 | 60.0 | 80.0 | 4 | 1.60 |
| order_chain | 14 | 0.0 | 7.1 | 7.1 | 21.4 | 3 | 1.21 |
| passage_qa | 3 | 0.0 | 33.3 | 33.3 | 33.3 | 1 | 1.33 |
| rule_apply | 10 | 0.0 | 10.0 | 40.0 | 30.0 | 3 | 1.50 |
| table_calc | 14 | 0.0 | 28.6 | 42.9 | 42.9 | 6 | 2.14 |
| table_lookup | 24 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |
| word_filter | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0 | 1.00 |

Rows greedy misses that some sample hits (any T): 18
- object_track-Dv1-124 (object_track): answer 'onion', greedy 'castle', hits of 32 by T {0.7: 4, 1.0: 9, 1.5: 6}
- object_track-Dv1-52 (object_track): answer 'stone', greedy 'dragon', hits of 32 by T {0.7: 3, 1.0: 11, 1.5: 10}
- object_track-Dv1-7 (object_track): answer 'anchor', greedy 'mirror', hits of 32 by T {0.7: 1, 1.0: 0, 1.5: 2}
- object_track-Dv1-80 (object_track): answer 'meadow', greedy 'hammer', hits of 32 by T {0.7: 4, 1.0: 6, 1.5: 8}
- order_chain-Dv1-151 (order_chain): answer 'Dax', greedy 'Ola', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 2}
- order_chain-Dv1-155 (order_chain): answer 'Gil', greedy 'Una', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 2}
- order_chain-Dv1-24 (order_chain): answer 'Uma', greedy 'Eli', hits of 32 by T {0.7: 17, 1.0: 14, 1.5: 19}
- passage_qa-Dv1-29 (passage_qa): answer 'yellow', greedy 'brown', hits of 32 by T {0.7: 2, 1.0: 4, 1.5: 7}
- rule_apply-Dv1-126 (rule_apply): answer 'stop', greedy 'hide', hits of 32 by T {0.7: 0, 1.0: 2, 1.5: 4}
- rule_apply-Dv1-187 (rule_apply): answer 'wait', greedy 'go', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 0}
- rule_apply-Dv1-245 (rule_apply): answer 'turn', greedy 'jump', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 1}
- rule_apply-Dv1-8 (rule_apply): answer 'turn', greedy 'jump', hits of 32 by T {0.7: 1, 1.0: 3, 1.5: 3}
- ... 6 more

### vocab_wrong/all  (n=103 rows; greedy modes {'GEN': 57, 'WORD': 28, 'NUM': 18})

| T | greedy pass@1 | pass@1 | pass@8 | pass@32 | greedy-or-any | rows with a hit | pass@32 - greedy | verdict (heldout/prog only) | distinct answers mean / median / max | distinct programs mean | answer != greedy % | program != greedy % | well-formed % | any non-NOOP op % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.7 | 0.0 | 3.6 | 14.5 | 23.3 | 23.3 | 24 | +23.3 | exploratory | 2.11 / 2 / 8 | 24.6 | 15.8 | 86.1 | 100.0 | 12.6 |
| 1.0 | 0.0 | 4.5 | 19.1 | 29.1 | 29.1 | 30 | +29.1 | exploratory | 2.53 / 2 / 12 | 28.0 | 20.2 | 92.5 | 100.0 | 12.6 |
| 1.5 | 0.0 | 6.4 | 26.3 | 41.7 | 41.7 | 43 | +41.7 | exploratory | 3.45 / 3 / 15 | 30.1 | 27.9 | 96.6 | 100.0 | 12.7 |

Per family (pass@32 at T = 0.7, 1.0, 1.5; greedy):

| family | n | greedy | pass@32 T=0.7 | pass@32 T=1.0 | pass@32 T=1.5 | rows with hit (T=1.5) | distinct answers mean (T=1.0) |
|---|---|---|---|---|---|---|---|
| kin_chain | 14 | 0.0 | 28.6 | 28.6 | 28.6 | 4 | 2.79 |
| letter_ops | 2 | 0.0 | 50.0 | 50.0 | 50.0 | 1 | 1.50 |
| list_index | 14 | 0.0 | 14.3 | 28.6 | 57.1 | 8 | 2.71 |
| object_track | 5 | 0.0 | 60.0 | 80.0 | 100.0 | 5 | 1.80 |
| order_chain | 14 | 0.0 | 7.1 | 21.4 | 28.6 | 4 | 1.29 |
| passage_qa | 3 | 0.0 | 66.7 | 100.0 | 100.0 | 3 | 2.00 |
| rule_apply | 10 | 0.0 | 20.0 | 20.0 | 30.0 | 3 | 1.30 |
| table_calc | 14 | 0.0 | 21.4 | 28.6 | 50.0 | 7 | 1.93 |
| table_lookup | 24 | 0.0 | 20.8 | 16.7 | 25.0 | 6 | 4.33 |
| word_filter | 3 | 0.0 | 33.3 | 33.3 | 66.7 | 2 | 1.33 |

Rows greedy misses that some sample hits (any T): 43
- kin_chain-Dv1-109 (kin_chain): answer 'no', greedy 'eo', hits of 32 by T {0.7: 13, 1.0: 10, 1.5: 10}
- kin_chain-Dv1-48 (kin_chain): answer 'yes', greedy 'yns', hits of 32 by T {0.7: 3, 1.0: 5, 1.5: 4}
- kin_chain-Dv1-62 (kin_chain): answer 'yes', greedy 'yns', hits of 32 by T {0.7: 2, 1.0: 2, 1.5: 4}
- kin_chain-Dv1-91 (kin_chain): answer 'no', greedy 'yes', hits of 32 by T {0.7: 1, 1.0: 4, 1.5: 4}
- letter_ops-Dv1-154 (letter_ops): answer '2', greedy '1', hits of 32 by T {0.7: 4, 1.0: 6, 1.5: 11}
- list_index-Dv1-126 (list_index): answer '8', greedy '0', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 2}
- list_index-Dv1-134 (list_index): answer '4', greedy '1', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 1}
- list_index-Dv1-16 (list_index): answer '4', greedy '5', hits of 32 by T {0.7: 10, 1.0: 6, 1.5: 9}
- list_index-Dv1-37 (list_index): answer '1', greedy '2', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 2}
- list_index-Dv1-46 (list_index): answer '2', greedy '5', hits of 32 by T {0.7: 0, 1.0: 0, 1.5: 2}
- list_index-Dv1-54 (list_index): answer '1', greedy '5', hits of 32 by T {0.7: 3, 1.0: 3, 1.5: 10}
- list_index-Dv1-90 (list_index): answer '4', greedy '5', hits of 32 by T {0.7: 0, 1.0: 1, 1.5: 1}
- ... 31 more


meaning fixed in PROBE-SPEC.md: pass@32 - greedy >= +10 signal; <= +2 cold start; else weak signal
