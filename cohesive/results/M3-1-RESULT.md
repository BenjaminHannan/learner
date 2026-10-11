# M1 "one shelf" result (M3-1)

Arms run ['R', 'TR']; saved shelf = arm TR
DEV sha256 f975d9fb312c02d7...; total 127.7 s; timings {'pieces': 1.5, 'features': 79.4, 'fit': 26.6, 'equivalence': 14.6, 'hits': 1.2}

## Pieces

| subject | tensors changed | numbers | max recon err |
|---|---|---|---|
| sheet | 28 | 129047 | 4.14e-08 |
| rpn | 28 | 129047 | 5.12e-08 |
| stats | 28 | 129047 | 2.87e-08 |
| invoice | 28 | 129047 | 3.97e-08 |
| py | 28 | 129047 | 4.77e-08 |

Class sizes {'none': 4096, 'sheet': 5995, 'rpn': 3534, 'stats': 3072, 'invoice': 3072, 'py': 4931}; prompts in two or more classes (dropped): 0
Readout train accuracy {'R': 0.9983, 'TR': 1.0}
Sizes {'parent': 3314132, 'pieces': 645235, 'router': 18438, 'total': 3977805, 'readout_R_for_comparison': 2054, 'saved_arm': 'TR', 'parent_plus_five_full_copies': 19884792, 'file_bytes': 15997551}

## Equivalence (shelf.pt vs picked checkpoint): 100.0% of 500

{'n': 500, 'share': 100.0, 'by_set': {'panel:sheet': 100.0, 'panel:rpn': 100.0, 'panel:stats': 100.0, 'panel:invoice': 100.0, 'panel:py': 100.0, 'dev': 100.0}, 'route_agrees_with_in_memory': '500/500', 'routes': {'sheet': 79, 'rpn': 43, 'none': 218, 'stats': 50, 'invoice': 62, 'py': 48}}

## Arm R: overall PASS (S1 PASS, S2 PASS, S3 PASS)

| subject | near | threshold | own routed near (n/a for final_alone) | parent near | final alone near | verdict | hair-miss used |
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

## Arm TR: overall PASS (S1 PASS, S2 PASS, S3 PASS)

| subject | near | threshold | own routed near (n/a for final_alone) | parent near | final alone near | verdict | hair-miss used |
|---|---|---|---|---|---|---|---|
| sheet | 40.24 | 37.24 | 40.24 | 2.14 | 40.24 | PASS | False |
| rpn | 89.59 | 87.07 | 90.07 | 6.54 | 90.07 | PASS | False |
| stats | 98.33 | 96.29 | 99.29 | 0.00 | 99.29 | PASS | False |
| invoice | 61.94 | 59.22 | 62.22 | 0.28 | 62.22 | PASS | False |
| py | 61.00 | 58.0 | 61.0 | 14.67 | 61.17 | PASS | False |

| subject | far | own routed far | parent far | final alone far |
|---|---|---|---|---|
| sheet | 1.79 | 1.79 | 1.07 | 1.79 |
| rpn | 0.71 | 0.36 | 0.71 | 0.36 |
| stats | 7.86 | 18.57 | 0.00 | 18.57 |
| invoice | 16.67 | 16.67 | 0.00 | 16.67 |
| py | 2.75 | 2.5 | 3.00 | 2.50 |

Routing of the subject panels (all rows; columns none, sheet, rpn, stats, invoice, py):

| panel | none | sheet | rpn | stats | invoice | py |
|---|---|---|---|---|---|---|
| sheet | 0 | 1000 | 0 | 0 | 0 | 0 |
| rpn | 2 | 248 | 550 | 0 | 0 | 0 |
| stats | 166 | 0 | 0 | 534 | 0 | 0 |
| invoice | 3 | 0 | 0 | 0 | 597 | 0 |
| py | 81 | 22 | 0 | 16 | 40 | 841 |

S2 DEV: parent 90.22 -> 90.22, drop 0.0, fired [], PASS
S3 look-alike old: parent 85.0 -> 84.38, drop 0.62, fired [], PASS
Held-out (reported): parent 2.0 -> 5.0, drop -3.0, fired [], PASS

Wrongly switched on: DEV 12/1360 {'rpn': 1, 'sheet': 3, 'stats': 6, 'invoice': 1, 'py': 1}; old 45/800 {'stats': 34, 'invoice': 11}; held 34/400 {'stats': 32, 'invoice': 2}; total 91
DEV by family: {'arith_bare': {'on': 2, 'n': 40}, 'fewshot_number_rule': {'on': 1, 'n': 40}, 'list_stats': {'on': 5, 'n': 40}, 'table_calc': {'on': 1, 'n': 40}, 'var_chain': {'on': 2, 'n': 40}, 'verify_claim': {'on': 1, 'n': 40}}
old by variant: {'column_sum': {'on': 4, 'n': 100}, 'count_even': {'on': 6, 'n': 100}, 'largest_of': {'on': 5, 'n': 100}, 'range': {'on': 23, 'n': 100}, 'row_total': {'on': 7, 'n': 100}, 'second_largest': {'on': 0, 'n': 100}, 'smaller': {'on': 0, 'n': 100}, 'smallest_of': {'on': 0, 'n': 100}}
held by variant: {'cost': {'on': 2, 'n': 100}, 'count_above': {'on': 0, 'n': 100}, 'larger': {'on': 0, 'n': 100}, 'sum': {'on': 32, 'n': 100}}

## Comparison rule

null

## Comparison rule M1b (TR vs R)

{
 "false_on_TR": 91,
 "false_on_R": 196,
 "TR_fewer_by": 105,
 "threshold": 20,
 "TR_not_worse_than_R_on_S1_S2_S3": true,
 "verdicts": {
  "TR": {
   "S1": "PASS",
   "S2": "PASS",
   "S3": "PASS"
  },
  "R": {
   "S1": "PASS",
   "S2": "PASS",
   "S3": "PASS"
  }
 },
 "near_diff_TR_minus_R": {
  "sheet": 0.0,
  "rpn": -0.4843,
  "stats": -0.9524,
  "invoice": -0.2778,
  "py": 0.0
 },
 "S2_drop": {
  "TR": 0.0,
  "R": 0.07
 },
 "S3_drop": {
  "TR": 0.62,
  "R": 0.12
 },
 "statement": "no comparison statement is fixed for M1c: numbers and difference only"
}

## Comparison rule M3-1 (TR vs M1b TR 119 + 20)

{
 "look_loops": 1,
 "overall_TR": "PASS",
 "false_on_TR": 91,
 "bar": 139,
 "M1b_TR_false_on": 119,
 "false_on_R": 196,
 "statement": "a one-round look picks skills as well as a full look (suggested, one seed)"
}

## Deviations

