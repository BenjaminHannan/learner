# Generalization breakdown: /tmp/dg/fwordR1/pulled/fwordR1/D-final.pt

kind d-only; extra loops 0; max visits 500

## Accuracy per set

| set | questions | accuracy % | mean loops |
|---|---|---|---|
| validation | 4359 | 53.91 | 2.85 |
| P0 | 4329 | 71.24 | 2.86 |
| Pword | 4329 | 61.38 | 2.77 |
| Pdepth | 4367 | 66.43 | 3.00 |

## Gap attribution

acc(P0) 71.24, acc(validation) 53.91, G = 17.33 points

| probe | acc % | drop (points) | share of G | >= G/2 | >= G/4 |
|---|---|---|---|---|---|
| Pword | 61.38 | 9.86 | 57% | True | True |
| Pdepth | 66.43 | 4.81 | 28% | False | True |

sum of single drops 14.67 points. Verdict: **bottleneck: Pword**

## By depth (accuracy % (questions))

| depth | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| 0 | 64.5 (248) | 60.9 (276) | 53.6 (276) | 60.9 (256) |
| 1 | 50.7 (1340) | 72.9 (1692) | 61.8 (1692) | 74.0 (1314) |
| 2 | 62.8 (1044) | 77.2 (1415) | 64.7 (1415) | 77.8 (1088) |
| 3 | 56.7 (958) | 62.5 (946) | 57.9 (946) | 64.4 (914) |
| 4 | 42.7 (597) | - | - | 44.1 (610) |
| 5 | 32.1 (159) | - | - | 36.7 (177) |
| 6 | 38.5 (13) | - | - | 37.5 (8) |

## By qtype (accuracy % (questions))

| qtype | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| Q1 | 48.9 (423) | 56.6 (579) | 54.7 (579) | 55.6 (448) |
| Q11 | 86.5 (208) | 94.8 (271) | 92.6 (271) | 89.3 (215) |
| Q12 | 41.1 (577) | 59.1 (320) | 59.1 (320) | 41.5 (573) |
| Q13 | 92.7 (395) | 86.8 (235) | 86.8 (235) | 94.5 (399) |
| Q2 | 77.9 (195) | 91.2 (283) | 89.4 (283) | 88.1 (201) |
| Q3 | 58.7 (143) | 72.3 (206) | 63.6 (206) | 70.2 (151) |
| Q4 | 49.8 (755) | 74.0 (535) | 65.4 (535) | 59.7 (735) |
| Q5 | 53.3 (315) | 57.4 (336) | 54.8 (336) | 51.3 (310) |
| Q6 | 27.6 (319) | 72.5 (400) | 28.7 (400) | 75.4 (309) |
| Q7 | 9.7 (134) | 60.5 (190) | 10.5 (190) | 53.2 (173) |
| Q8 | 23.6 (313) | 81.6 (223) | 46.2 (223) | 86.0 (207) |
| Q9 | 69.6 (582) | 69.6 (751) | 71.9 (751) | 71.4 (646) |

## By n_families (accuracy % (questions))

| n_families | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| 0 | 58.9 (3626) | 71.6 (3899) | 64.4 (3899) | 68.3 (3731) |
| 1 | 29.3 (733) | 67.7 (430) | 33.7 (430) | 55.7 (636) |

## By r8 (accuracy % (questions))

| r8 | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 55.7 (4160) | 71.2 (4329) | 61.4 (4329) | 66.4 (4367) |
| True | 16.6 (199) | - | - | - |

## By style_status (accuracy % (questions))

| style_status | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| train | - | 71.2 (4329) | 61.4 (4329) | 66.4 (4367) |
| validation | 53.9 (4359) | - | - | - |

## By name_answer (accuracy % (questions))

| name_answer | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 52.9 (4178) | 70.1 (4081) | 59.7 (4081) | 65.5 (4176) |
| True | 76.2 (181) | 89.9 (248) | 89.1 (248) | 87.4 (191) |

## By knowable (accuracy % (questions))

| knowable | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 64.5 (248) | 60.9 (276) | 53.6 (276) | 60.9 (256) |
| True | 53.3 (4111) | 71.9 (4053) | 61.9 (4053) | 66.8 (4111) |
