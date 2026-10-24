# Generalization breakdown: /tmp/dg/base0/pulled/base0/D-final.pt

kind d-only; extra loops 0; max visits 500

## Accuracy per set

| set | questions | accuracy % | mean loops |
|---|---|---|---|
| validation | 4359 | 47.35 | 2.26 |
| P0 | 4329 | 77.15 | 2.25 |
| Pword | 4329 | 53.11 | 2.21 |
| Pdepth | 4367 | 71.81 | 2.37 |

## Gap attribution

acc(P0) 77.15, acc(validation) 47.35, G = 29.80 points

| probe | acc % | drop (points) | share of G | >= G/2 | >= G/4 |
|---|---|---|---|---|---|
| Pword | 53.11 | 24.05 | 81% | True | True |
| Pdepth | 71.81 | 5.34 | 18% | False | False |

sum of single drops 29.39 points. Verdict: **bottleneck: Pword**

## By depth (accuracy % (questions))

| depth | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| 0 | 42.7 (248) | 71.4 (276) | 39.1 (276) | 67.6 (256) |
| 1 | 52.8 (1340) | 86.3 (1692) | 62.1 (1692) | 88.4 (1314) |
| 2 | 50.8 (1044) | 73.4 (1415) | 49.5 (1415) | 76.0 (1088) |
| 3 | 46.8 (958) | 68.1 (946) | 46.6 (946) | 68.5 (914) |
| 4 | 36.9 (597) | - | - | 46.1 (610) |
| 5 | 30.2 (159) | - | - | 36.7 (177) |
| 6 | 38.5 (13) | - | - | 37.5 (8) |

## By qtype (accuracy % (questions))

| qtype | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| Q1 | 75.7 (423) | 88.8 (579) | 79.8 (579) | 86.6 (448) |
| Q11 | 0.0 (208) | 93.7 (271) | 0.0 (271) | 88.8 (215) |
| Q12 | 25.0 (577) | 73.4 (320) | 37.2 (320) | 51.3 (573) |
| Q13 | 92.4 (395) | 86.8 (235) | 86.8 (235) | 94.5 (399) |
| Q2 | 77.4 (195) | 86.9 (283) | 82.0 (283) | 86.6 (201) |
| Q3 | 27.3 (143) | 61.7 (206) | 21.4 (206) | 66.9 (151) |
| Q4 | 44.9 (755) | 77.2 (535) | 59.4 (535) | 60.3 (735) |
| Q5 | 49.2 (315) | 59.8 (336) | 50.6 (336) | 53.5 (310) |
| Q6 | 24.1 (319) | 71.0 (400) | 25.5 (400) | 74.4 (309) |
| Q7 | 6.7 (134) | 38.4 (190) | 5.3 (190) | 40.5 (173) |
| Q8 | 12.8 (313) | 96.9 (223) | 22.4 (223) | 99.0 (207) |
| Q9 | 73.0 (582) | 76.3 (751) | 78.3 (751) | 76.9 (646) |

## By n_families (accuracy % (questions))

| n_families | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| 0 | 52.2 (3626) | 78.0 (3899) | 57.0 (3899) | 74.3 (3731) |
| 1 | 23.2 (733) | 69.1 (430) | 17.9 (430) | 57.1 (636) |

## By r8 (accuracy % (questions))

| r8 | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 48.8 (4160) | 77.2 (4329) | 53.1 (4329) | 71.8 (4367) |
| True | 18.1 (199) | - | - | - |

## By style_status (accuracy % (questions))

| style_status | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| train | - | 77.2 (4329) | 53.1 (4329) | 71.8 (4367) |
| validation | 47.4 (4359) | - | - | - |

## By name_answer (accuracy % (questions))

| name_answer | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 46.1 (4178) | 76.5 (4081) | 51.3 (4081) | 71.2 (4176) |
| True | 77.3 (181) | 87.9 (248) | 83.5 (248) | 85.9 (191) |

## By knowable (accuracy % (questions))

| knowable | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 42.7 (248) | 71.4 (276) | 39.1 (276) | 67.6 (256) |
| True | 47.6 (4111) | 77.5 (4053) | 54.1 (4053) | 72.1 (4111) |
