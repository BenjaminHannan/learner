# Guess-1 report

**Verdict: PROVED WRONG**

T = 48 tasks; seeds [1, 2]; BEST = MENU (marks x2)

- P1 (BEST cracked >= IND + 8): False
- P2 (BEST >= HOT + 6): False
- P3 (BEST distinct correct plans >= 1.5x IND): False
- P4 (only-BEST 12 vs only-IND 10, >= 2:1): False
- PROVED WRONG test (LIST and MENU both <= IND + 2): True
- Diagnostic (diversity without quality): False

## Seed 1

| arm | tries | cracked | distinct plans | distinct correct | top-share | gen tokens | prompt tokens |
|---|---|---|---|---|---|---|---|
| IND | 576 | 31 | 540 | 102 | 0.132 | 133216 | 3003151 |
| HOT | 576 | 32 | 543 | 108 | 0.128 | 131956 | 2923774 |
| LIST | 576 | 21 | 457 | 93 | 0.224 | 113972 | 3634370 |
| MENU | 576 | 34 | 556 | 120 | 0.111 | 150975 | 3243291 |
| IND12 | 576 | 31 | 540 | 102 | 0.132 | 133216 | 3003151 |

IND is the topped-up arm; IND12 is its first 12 tries. Generated-token ratio vs IND: IND 1.00, HOT 0.99, LIST 0.86, MENU 1.13

## Seed 2

| arm | tries | cracked | distinct plans | distinct correct | top-share | gen tokens | prompt tokens |
|---|---|---|---|---|---|---|---|
| IND | 624 | 33 | 574 | 113 | 0.141 | 142553 | 3275871 |
| HOT | 576 | 33 | 549 | 129 | 0.122 | 138764 | 2978979 |
| LIST | 576 | 25 | 448 | 131 | 0.253 | 115559 | 3777771 |
| MENU | 576 | 32 | 540 | 102 | 0.135 | 154973 | 3235939 |
| IND12 | 576 | 33 | 534 | 107 | 0.142 | 132191 | 3017206 |

IND is the topped-up arm; IND12 is its first 12 tries. Generated-token ratio vs IND: IND 1.00, HOT 0.97, LIST 0.81, MENU 1.09
