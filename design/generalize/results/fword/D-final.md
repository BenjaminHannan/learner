# Generalization breakdown: /tmp/dg/fword/pulled/fword/D-final.pt

kind d-only; extra loops 0; max visits 500

## Accuracy per set

| set | questions | accuracy % | mean loops |
|---|---|---|---|
| validation | 4359 | 51.75 | 2.28 |
| P0 | 4329 | 78.12 | 2.25 |
| Pword | 4329 | 61.31 | 2.20 |
| Pdepth | 4367 | 69.52 | 2.46 |

## Gap attribution

acc(P0) 78.12, acc(validation) 51.75, G = 26.37 points

| probe | acc % | drop (points) | share of G | >= G/2 | >= G/4 |
|---|---|---|---|---|---|
| Pword | 61.31 | 16.82 | 64% | True | True |
| Pdepth | 69.52 | 8.60 | 33% | False | True |

sum of single drops 25.42 points. Verdict: **bottleneck: Pword**

## By depth (accuracy % (questions))

| depth | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| 0 | 68.5 (248) | 70.3 (276) | 68.5 (276) | 71.1 (256) |
| 1 | 62.1 (1340) | 86.4 (1692) | 72.3 (1692) | 83.1 (1314) |
| 2 | 51.1 (1044) | 77.5 (1415) | 56.4 (1415) | 74.5 (1088) |
| 3 | 45.1 (958) | 66.5 (946) | 46.8 (946) | 66.8 (914) |
| 4 | 38.4 (597) | - | - | 45.6 (610) |
| 5 | 34.6 (159) | - | - | 33.3 (177) |
| 6 | 30.8 (13) | - | - | 37.5 (8) |

## By qtype (accuracy % (questions))

| qtype | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| Q1 | 78.0 (423) | 87.6 (579) | 81.7 (579) | 81.0 (448) |
| Q11 | 76.4 (208) | 91.9 (271) | 85.2 (271) | 86.5 (215) |
| Q12 | 5.4 (577) | 66.2 (320) | 10.6 (320) | 46.6 (573) |
| Q13 | 92.2 (395) | 86.8 (235) | 86.8 (235) | 93.7 (399) |
| Q2 | 79.5 (195) | 90.5 (283) | 88.0 (283) | 85.1 (201) |
| Q3 | 56.6 (143) | 72.8 (206) | 68.4 (206) | 69.5 (151) |
| Q4 | 48.7 (755) | 75.7 (535) | 61.9 (535) | 58.6 (735) |
| Q5 | 46.7 (315) | 56.8 (336) | 53.6 (336) | 46.5 (310) |
| Q6 | 33.5 (319) | 74.2 (400) | 32.5 (400) | 67.6 (309) |
| Q7 | 7.5 (134) | 60.0 (190) | 6.3 (190) | 53.8 (173) |
| Q8 | 31.9 (313) | 96.0 (223) | 53.8 (223) | 96.1 (207) |
| Q9 | 69.4 (582) | 77.6 (751) | 73.1 (751) | 76.5 (646) |

## By n_families (accuracy % (questions))

| n_families | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| 0 | 55.9 (3626) | 78.6 (3899) | 64.3 (3899) | 71.7 (3731) |
| 1 | 31.4 (733) | 74.0 (430) | 34.2 (430) | 56.6 (636) |

## By r8 (accuracy % (questions))

| r8 | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 53.6 (4160) | 78.1 (4329) | 61.3 (4329) | 69.5 (4367) |
| True | 12.6 (199) | - | - | - |

## By style_status (accuracy % (questions))

| style_status | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| train | - | 78.1 (4329) | 61.3 (4329) | 69.5 (4367) |
| validation | 51.8 (4359) | - | - | - |

## By name_answer (accuracy % (questions))

| name_answer | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 50.6 (4178) | 77.4 (4081) | 59.8 (4081) | 68.8 (4176) |
| True | 78.5 (181) | 89.5 (248) | 86.7 (248) | 84.3 (191) |

## By knowable (accuracy % (questions))

| knowable | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 68.5 (248) | 70.3 (276) | 68.5 (276) | 71.1 (256) |
| True | 50.7 (4111) | 78.7 (4053) | 60.8 (4053) | 69.4 (4111) |
