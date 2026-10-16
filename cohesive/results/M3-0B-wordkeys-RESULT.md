# M3-0 result: skill pieces with their before-the-loop parts removed

Overall: **PASS**. Sanity (untrimmed = M1 final alone near/far): True. Total 137.4 s; {'trace': 5.0, 'trim_and_score': 132.4}

## Before-the-loop layers (called before the first call to core.0.qkv)

Same set in all six traced batches: True; differences {}

| layer | also called inside the loop |
|---|---|
| k_word | False |
| k_wc | False |

## Share of each piece in those layers

| subject | rank-8 numbers | in trimmed layers | share % |
|---|---|---|---|
| sheet | 129047 | 3392 | 2.63 |
| rpn | 129047 | 3392 | 2.63 |
| stats | 129047 | 3392 | 2.63 |
| invoice | 129047 | 3392 | 2.63 |
| py | 129047 | 3392 | 2.63 |

## Panel scores alone (decontaminated)

| subject | untrimmed near | trimmed near | threshold | proved wrong below | verdict | hair-miss | untrimmed far | trimmed far | n near | M1 match |
|---|---|---|---|---|---|---|---|---|---|---|
| sheet | 40.24 | 40.24 | 37.24 | 30.24 | PASS | False | 1.79 | 1.79 | 420 | True |
| rpn | 90.07 | 90.07 | 87.07 | 80.07 | PASS | False | 0.36 | 0.36 | 413 | True |
| stats | 99.29 | 99.29 | 96.29 | 89.29 | PASS | False | 18.57 | 18.57 | 420 | True |
| invoice | 62.22 | 62.22 | 59.22 | 52.22 | PASS | False | 16.67 | 16.67 | 360 | True |
| py | 61.17 | 61.17 | 58.17 | 51.17 | PASS | False | 2.50 | 2.50 | 600 | True |

## DEV in_dist pooled (parent 90.22)

| subject | untrimmed | trimmed |
|---|---|---|
| sheet | 84.04 | 83.9 |
| rpn | 86.1 | 86.03 |
| stats | 87.21 | 87.28 |
| invoice | 86.91 | 87.06 |
| py | 87.28 | 87.28 |
