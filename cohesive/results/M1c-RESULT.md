# M1 "one shelf" result (M1c)

Arms run ['T', 'R', 'TR']; saved shelf = arm TR
DEV sha256 f975d9fb312c02d7...; total 270.2 s; timings {'pieces': 1.2, 'features': 180.3, 'fit': 9.5, 'equivalence': 8.6, 'hits': 64.1}

## Pieces

| subject | tensors changed | numbers | max recon err |
|---|---|---|---|
| sheet | 28 | 129047 | 4.26e-08 |
| py | 28 | 129047 | 3.04e-08 |

Class sizes {'none': 4096, 'sheet': 6734, 'py': 4005}; prompts in two or more classes (dropped): 0
Readout train accuracy {'T': 1.0, 'R': 1.0, 'TR': 1.0}
Sizes {'parent': 3314132, 'pieces': 258094, 'router': 11523, 'total': 3583749, 'readout_R_for_comparison': 1283, 'saved_arm': 'TR', 'parent_plus_2_full_copies': 9942396, 'file_bytes': 14385679}

## Equivalence (shelf.pt vs picked checkpoint): 100.0% of 320

{'n': 320, 'share': 100.0, 'by_set': {'panel:sheet': 100.0, 'panel:py': 100.0, 'dev': 100.0}, 'route_agrees_with_in_memory': '320/320', 'routes': {'sheet': 60, 'py': 60, 'none': 200}}

## Arm T: overall PASS (S1 PASS, S2 PASS, S3 PASS)

| subject | near | threshold | own routed near (n/a for final_alone) | parent near | final alone near | verdict | hair-miss used |
|---|---|---|---|---|---|---|---|
| sheet | 54.76 | 51.76 | 40.24 | 0.95 | 54.76 | PASS | False |
| py | 56.33 | 54.33 | 61.0 | 10.50 | 57.33 | PASS | False |

| subject | far | own routed far | parent far | final alone far |
|---|---|---|---|---|
| sheet | 1.43 | 1.79 | 0.36 | 1.43 |
| py | 4.25 | 2.5 | 4.50 | 4.75 |

Routing of the subject panels (all rows; columns none, sheet, py):

| panel | none | sheet | py |
|---|---|---|---|
| sheet | 1 | 999 | 0 |
| py | 111 | 35 | 854 |

S2 DEV: parent 90.88 -> 90.88, drop 0.0, fired [], PASS
S3 look-alike old: parent 86.12 -> 86.12, drop 0.0, fired [], PASS
Held-out (reported): parent 3.0 -> 2.75, drop 0.25, fired [], PASS

Wrongly switched on: DEV 0/1360 {}; old 0/800 {}; held 27/400 {'py': 26, 'sheet': 1}; total 27
DEV by family: {}
old by variant: {'column_sum': {'on': 0, 'n': 100}, 'count_even': {'on': 0, 'n': 100}, 'largest_of': {'on': 0, 'n': 100}, 'range': {'on': 0, 'n': 100}, 'row_total': {'on': 0, 'n': 100}, 'second_largest': {'on': 0, 'n': 100}, 'smaller': {'on': 0, 'n': 100}, 'smallest_of': {'on': 0, 'n': 100}}
held by variant: {'cost': {'on': 0, 'n': 100}, 'count_above': {'on': 1, 'n': 100}, 'larger': {'on': 17, 'n': 100}, 'sum': {'on': 9, 'n': 100}}

## Arm R: overall PASS (S1 PASS, S2 PASS, S3 PASS)

| subject | near | threshold | own routed near (n/a for final_alone) | parent near | final alone near | verdict | hair-miss used |
|---|---|---|---|---|---|---|---|
| sheet | 54.76 | 51.76 | 40.24 | 0.95 | 54.76 | PASS | False |
| py | 57.33 | 54.33 | 61.0 | 10.50 | 57.33 | PASS | False |

| subject | far | own routed far | parent far | final alone far |
|---|---|---|---|---|
| sheet | 1.43 | 1.79 | 0.36 | 1.43 |
| py | 4.75 | 2.5 | 4.50 | 4.75 |

Routing of the subject panels (all rows; columns none, sheet, py):

| panel | none | sheet | py |
|---|---|---|---|
| sheet | 0 | 1000 | 0 |
| py | 11 | 0 | 989 |

S2 DEV: parent 90.88 -> 90.88, drop 0.0, fired [], PASS
S3 look-alike old: parent 86.12 -> 86.12, drop 0.0, fired [], PASS
Held-out (reported): parent 3.0 -> 3.0, drop 0.0, fired [], PASS

Wrongly switched on: DEV 2/1360 {'sheet': 1, 'py': 1}; old 0/800 {}; held 0/400 {}; total 2
DEV by family: {'arith_bare': {'on': 1, 'n': 40}, 'digits_parity': {'on': 1, 'n': 40}}
old by variant: {'column_sum': {'on': 0, 'n': 100}, 'count_even': {'on': 0, 'n': 100}, 'largest_of': {'on': 0, 'n': 100}, 'range': {'on': 0, 'n': 100}, 'row_total': {'on': 0, 'n': 100}, 'second_largest': {'on': 0, 'n': 100}, 'smaller': {'on': 0, 'n': 100}, 'smallest_of': {'on': 0, 'n': 100}}
held by variant: {'cost': {'on': 0, 'n': 100}, 'count_above': {'on': 0, 'n': 100}, 'larger': {'on': 0, 'n': 100}, 'sum': {'on': 0, 'n': 100}}

## Arm TR: overall PASS (S1 PASS, S2 PASS, S3 PASS)

| subject | near | threshold | own routed near (n/a for final_alone) | parent near | final alone near | verdict | hair-miss used |
|---|---|---|---|---|---|---|---|
| sheet | 54.76 | 51.76 | 40.24 | 0.95 | 54.76 | PASS | False |
| py | 56.67 | 54.33 | 61.0 | 10.50 | 57.33 | PASS | False |

| subject | far | own routed far | parent far | final alone far |
|---|---|---|---|---|
| sheet | 1.43 | 1.79 | 0.36 | 1.43 |
| py | 4.25 | 2.5 | 4.50 | 4.75 |

Routing of the subject panels (all rows; columns none, sheet, py):

| panel | none | sheet | py |
|---|---|---|---|
| sheet | 0 | 1000 | 0 |
| py | 57 | 9 | 934 |

S2 DEV: parent 90.88 -> 90.81, drop 0.07, fired [], PASS
S3 look-alike old: parent 86.12 -> 86.12, drop 0.0, fired [], PASS
Held-out (reported): parent 3.0 -> 3.0, drop 0.0, fired [], PASS

Wrongly switched on: DEV 1/1360 {'py': 1}; old 0/800 {}; held 2/400 {'py': 2}; total 3
DEV by family: {'fewshot_number_rule': {'on': 1, 'n': 40}}
old by variant: {'column_sum': {'on': 0, 'n': 100}, 'count_even': {'on': 0, 'n': 100}, 'largest_of': {'on': 0, 'n': 100}, 'range': {'on': 0, 'n': 100}, 'row_total': {'on': 0, 'n': 100}, 'second_largest': {'on': 0, 'n': 100}, 'smaller': {'on': 0, 'n': 100}, 'smallest_of': {'on': 0, 'n': 100}}
held by variant: {'cost': {'on': 0, 'n': 100}, 'count_above': {'on': 0, 'n': 100}, 'larger': {'on': 2, 'n': 100}, 'sum': {'on': 0, 'n': 100}}

## Comparison rule (T vs R)

{
 "false_on_T": 27,
 "false_on_R": 2,
 "T_fewer_by": -25,
 "threshold": 20,
 "T_not_worse_than_R_on_S2_S3": true,
 "S2_drop": {
  "T": 0.0,
  "R": 0.0
 },
 "S3_drop": {
  "T": 0.0,
  "R": 0.0
 },
 "statement": "no comparison statement is fixed for M1c: numbers and difference only"
}

## Comparison rule M1b (TR vs R)

{
 "false_on_TR": 3,
 "false_on_R": 2,
 "TR_fewer_by": -1,
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
  "py": -0.6667
 },
 "S2_drop": {
  "TR": 0.07,
  "R": 0.0
 },
 "S3_drop": {
  "TR": 0.0,
  "R": 0.0
 },
 "statement": "no comparison statement is fixed for M1c: numbers and difference only"
}

## Deviations

