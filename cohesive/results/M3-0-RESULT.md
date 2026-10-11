# M3-0 result: skill pieces with their before-the-loop parts removed

Overall: **PROVED WRONG (sheet, rpn, stats, invoice, py)**. Sanity (untrimmed = M1 final alone near/far): True. Total 132.6 s; {'trace': 5.3, 'trim_and_score': 127.4}

## Before-the-loop layers (called before the first call to core.0.qkv)

Same set in all six traced batches: True; differences {}

| layer | also called inside the loop |
|---|---|
| k_word | False |
| k_wc | False |
| core.0.kv | True |
| core.1.kv | True |
| core.0.q | True |
| core.0.o | True |

## Share of each piece in those layers

| subject | rank-8 numbers | in trimmed layers | share % |
|---|---|---|---|
| sheet | 129047 | 23872 | 18.5 |
| rpn | 129047 | 23872 | 18.5 |
| stats | 129047 | 23872 | 18.5 |
| invoice | 129047 | 23872 | 18.5 |
| py | 129047 | 23872 | 18.5 |

## Panel scores alone (decontaminated)

| subject | untrimmed near | trimmed near | threshold | proved wrong below | verdict | hair-miss | untrimmed far | trimmed far | n near | M1 match |
|---|---|---|---|---|---|---|---|---|---|---|
| sheet | 40.24 | 3.33 | 37.24 | 30.24 | PROVED WRONG | False | 1.79 | 0.00 | 420 | True |
| rpn | 90.07 | 34.38 | 87.07 | 80.07 | PROVED WRONG | False | 0.36 | 0.36 | 413 | True |
| stats | 99.29 | 15.24 | 96.29 | 89.29 | PROVED WRONG | False | 18.57 | 1.07 | 420 | True |
| invoice | 62.22 | 9.72 | 59.22 | 52.22 | PROVED WRONG | False | 16.67 | 5.00 | 360 | True |
| py | 61.17 | 36.67 | 58.17 | 51.17 | PROVED WRONG | False | 2.50 | 0.25 | 600 | True |

## DEV in_dist pooled (parent 90.22)

| subject | untrimmed | trimmed |
|---|---|---|
| sheet | 84.04 | 84.34 |
| rpn | 86.1 | 88.24 |
| stats | 87.21 | 88.16 |
| invoice | 86.91 | 88.46 |
| py | 87.28 | 89.26 |
