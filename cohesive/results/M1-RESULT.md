# M1 "one shelf" result

DEV sha256 f975d9fb312c02d7...; total 538.7 s; timings {'pieces': 1.4, 'features': 298.7, 'fit': 10.3, 'equivalence': 16.7, 'hits': 206.8}

## Pieces

| subject | tensors changed | numbers | max recon err |
|---|---|---|---|
| sheet | 28 | 129047 | 4.14e-08 |
| rpn | 28 | 129047 | 5.12e-08 |
| stats | 28 | 129047 | 2.87e-08 |
| invoice | 28 | 129047 | 3.97e-08 |
| py | 28 | 129047 | 4.77e-08 |

Class sizes {'none': 4096, 'sheet': 5995, 'rpn': 3534, 'stats': 3072, 'invoice': 3072, 'py': 4931}; prompts in two or more classes (dropped): 0
Readout train accuracy {'T': 1.0, 'R': 0.9983}
Sizes {'parent': 3314132, 'pieces': 645235, 'router': 16390, 'total': 3975757, 'readout_R_for_comparison': 2054, 'parent_plus_five_full_copies': 19884792, 'file_bytes': 15989295}

## Equivalence (shelf.pt vs picked checkpoint): 100.0% of 500

{'n': 500, 'share': 100.0, 'by_set': {'panel:sheet': 100.0, 'panel:rpn': 100.0, 'panel:stats': 100.0, 'panel:invoice': 100.0, 'panel:py': 100.0, 'dev': 100.0}, 'route_agrees_with_in_memory': '500/500', 'routes': {'sheet': 75, 'rpn': 49, 'stats': 46, 'none': 221, 'invoice': 59, 'py': 50}}

## Arm T: overall FAIL (S1 FAIL, S2 PASS, S3 PASS)

| subject | near | threshold | own routed near | parent near | final alone near | verdict | hair-miss used |
|---|---|---|---|---|---|---|---|
| sheet | 40.24 | 37.24 | 40.24 | 2.14 | 40.24 | PASS | False |
| rpn | 89.83 | 87.07 | 90.07 | 6.54 | 90.07 | PASS | False |
| stats | 97.14 | 96.29 | 99.29 | 0.00 | 99.29 | PASS | False |
| invoice | 58.89 | 59.22 | 62.22 | 0.28 | 62.22 | FAIL | False |
| py | 61.00 | 58.0 | 61.0 | 14.67 | 61.17 | PASS | False |

| subject | far | own routed far | parent far | final alone far |
|---|---|---|---|---|
| sheet | 1.79 | 1.79 | 1.07 | 1.79 |
| rpn | 0.36 | 0.36 | 0.71 | 0.36 |
| stats | 8.93 | 18.57 | 0.00 | 18.57 |
| invoice | 16.67 | 16.67 | 0.00 | 16.67 |
| py | 2.25 | 2.5 | 3.00 | 2.50 |

Routing of the subject panels (all rows; columns none, sheet, rpn, stats, invoice, py):

| panel | none | sheet | rpn | stats | invoice | py |
|---|---|---|---|---|---|---|
| sheet | 0 | 1000 | 0 | 0 | 0 | 0 |
| rpn | 1 | 124 | 672 | 0 | 2 | 1 |
| stats | 168 | 0 | 0 | 531 | 0 | 1 |
| invoice | 18 | 0 | 0 | 0 | 578 | 4 |
| py | 55 | 39 | 8 | 4 | 8 | 886 |

S2 DEV: parent 90.22 -> 90.15, drop 0.07, fired [], PASS
S3 look-alike old: parent 85.0 -> 85.12, drop -0.12, fired [], PASS
Held-out (reported): parent 2.0 -> 6.75, drop -4.75, fired [], PASS

Wrongly switched on: DEV 7/1360 {'rpn': 1, 'stats': 5, 'invoice': 1}; old 55/800 {'py': 1, 'stats': 42, 'invoice': 12}; held 83/400 {'py': 6, 'stats': 53, 'invoice': 24}; total 145
DEV by family: {'arith_bare': {'on': 1, 'n': 40}, 'compare_numbers': {'on': 2, 'n': 40}, 'fewshot_number_rule': {'on': 1, 'n': 40}, 'list_stats': {'on': 3, 'n': 40}}
old by variant: {'column_sum': {'on': 8, 'n': 100}, 'count_even': {'on': 1, 'n': 100}, 'largest_of': {'on': 10, 'n': 100}, 'range': {'on': 27, 'n': 100}, 'row_total': {'on': 4, 'n': 100}, 'second_largest': {'on': 1, 'n': 100}, 'smaller': {'on': 1, 'n': 100}, 'smallest_of': {'on': 3, 'n': 100}}
held by variant: {'cost': {'on': 15, 'n': 100}, 'count_above': {'on': 14, 'n': 100}, 'larger': {'on': 5, 'n': 100}, 'sum': {'on': 49, 'n': 100}}

## Arm R: overall PASS (S1 PASS, S2 PASS, S3 PASS)

| subject | near | threshold | own routed near | parent near | final alone near | verdict | hair-miss used |
|---|---|---|---|---|---|---|---|
| sheet | 40.24 | 37.24 | 40.24 | 2.14 | 40.24 | PASS | False |
| rpn | 90.07 | 87.07 | 90.07 | 6.54 | 90.07 | PASS | False |
| stats | 99.29 | 96.29 | 99.29 | 0.00 | 99.29 | PASS | False |
| invoice | 62.22 | 59.22 | 62.22 | 0.28 | 62.22 | PASS | False |
| py | 61.00 | 58.0 | 61.0 | 14.67 | 61.17 | PASS | False |

| subject | far | own routed far | parent far | final alone far |
|---|---|---|---|---|
| sheet | 1.79 | 1.79 | 1.07 | 1.79 |
| rpn | 0.36 | 0.36 | 0.71 | 0.36 |
| stats | 18.57 | 18.57 | 0.00 | 18.57 |
| invoice | 16.67 | 16.67 | 0.00 | 16.67 |
| py | 2.50 | 2.5 | 3.00 | 2.50 |

Routing of the subject panels (all rows; columns none, sheet, rpn, stats, invoice, py):

| panel | none | sheet | rpn | stats | invoice | py |
|---|---|---|---|---|---|---|
| sheet | 0 | 1000 | 0 | 0 | 0 | 0 |
| rpn | 0 | 0 | 800 | 0 | 0 | 0 |
| stats | 22 | 0 | 0 | 678 | 0 | 0 |
| invoice | 0 | 0 | 0 | 0 | 600 | 0 |
| py | 11 | 0 | 0 | 0 | 0 | 989 |

S2 DEV: parent 90.22 -> 90.15, drop 0.07, fired [], PASS
S3 look-alike old: parent 85.0 -> 84.88, drop 0.12, fired [], PASS
Held-out (reported): parent 2.0 -> 5.25, drop -3.25, fired [], PASS

Wrongly switched on: DEV 19/1360 {'rpn': 3, 'sheet': 1, 'invoice': 8, 'stats': 7}; old 109/800 {'stats': 57, 'invoice': 52}; held 68/400 {'invoice': 14, 'stats': 54}; total 196
DEV by family: {'arith_bare': {'on': 3, 'n': 40}, 'list_stats': {'on': 6, 'n': 40}, 'table_calc': {'on': 7, 'n': 40}, 'var_chain': {'on': 1, 'n': 40}, 'verify_claim': {'on': 2, 'n': 40}}
old by variant: {'column_sum': {'on': 31, 'n': 100}, 'count_even': {'on': 0, 'n': 100}, 'largest_of': {'on': 13, 'n': 100}, 'range': {'on': 31, 'n': 100}, 'row_total': {'on': 16, 'n': 100}, 'second_largest': {'on': 3, 'n': 100}, 'smaller': {'on': 0, 'n': 100}, 'smallest_of': {'on': 15, 'n': 100}}
held by variant: {'cost': {'on': 11, 'n': 100}, 'count_above': {'on': 3, 'n': 100}, 'larger': {'on': 0, 'n': 100}, 'sum': {'on': 54, 'n': 100}}

## Comparison rule

{
 "false_on_T": 145,
 "false_on_R": 196,
 "T_fewer_by": 51,
 "threshold": 20,
 "T_not_worse_than_R_on_S2_S3": true,
 "S2_drop": {
  "T": 0.07,
  "R": 0.07
 },
 "S3_drop": {
  "T": -0.12,
  "R": 0.12
 },
 "statement": "the brain's own thinking picks skills better than the reader's mean (suggested, one seed)"
}

## Deviations

