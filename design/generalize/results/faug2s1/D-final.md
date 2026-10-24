# Generalization breakdown: /tmp/dg/faug2s1/pulled/faug2s1/D-final.pt

kind d-only; extra loops 0; max visits 500

## Accuracy per set

| set | questions | accuracy % | mean loops |
|---|---|---|---|
| validation | 4359 | 58.68 | 2.49 |
| P0 | 4329 | 79.65 | 2.33 |
| Pword | 4329 | 68.91 | 2.31 |
| Pdepth | 4367 | 72.41 | 2.55 |

## Gap attribution

acc(P0) 79.65, acc(validation) 58.68, G = 20.97 points

| probe | acc % | drop (points) | share of G | >= G/2 | >= G/4 |
|---|---|---|---|---|---|
| Pword | 68.91 | 10.74 | 51% | True | True |
| Pdepth | 72.41 | 7.24 | 35% | False | True |

sum of single drops 17.98 points. Verdict: **bottleneck: Pword**

## By depth (accuracy % (questions))

| depth | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| 0 | 65.7 (248) | 66.7 (276) | 63.0 (276) | 64.1 (256) |
| 1 | 62.0 (1340) | 87.4 (1692) | 74.7 (1692) | 87.2 (1314) |
| 2 | 68.8 (1044) | 79.2 (1415) | 69.9 (1415) | 78.2 (1088) |
| 3 | 57.9 (958) | 70.4 (946) | 58.8 (946) | 73.4 (914) |
| 4 | 39.2 (597) | - | - | 43.6 (610) |
| 5 | 32.7 (159) | - | - | 33.9 (177) |
| 6 | 38.5 (13) | - | - | 50.0 (8) |

## By qtype (accuracy % (questions))

| qtype | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| Q1 | 50.6 (423) | 91.2 (579) | 58.2 (579) | 87.1 (448) |
| Q11 | 83.7 (208) | 93.0 (271) | 91.5 (271) | 88.8 (215) |
| Q12 | 46.6 (577) | 70.6 (320) | 70.0 (320) | 49.7 (573) |
| Q13 | 92.4 (395) | 86.8 (235) | 86.8 (235) | 93.5 (399) |
| Q2 | 84.6 (195) | 92.2 (283) | 91.9 (283) | 89.6 (201) |
| Q3 | 62.2 (143) | 72.8 (206) | 71.8 (206) | 72.2 (151) |
| Q4 | 45.4 (755) | 81.1 (535) | 59.3 (535) | 62.9 (735) |
| Q5 | 47.9 (315) | 59.2 (336) | 47.3 (336) | 52.6 (310) |
| Q6 | 67.7 (319) | 73.0 (400) | 72.0 (400) | 74.4 (309) |
| Q7 | 1.5 (134) | 68.9 (190) | 0.5 (190) | 63.6 (173) |
| Q8 | 44.7 (313) | 98.2 (223) | 88.3 (223) | 100.0 (207) |
| Q9 | 73.9 (582) | 73.5 (751) | 79.9 (751) | 71.5 (646) |

## By n_families (accuracy % (questions))

| n_families | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| 0 | 63.2 (3626) | 79.7 (3899) | 70.8 (3899) | 74.2 (3731) |
| 1 | 36.2 (733) | 79.3 (430) | 51.9 (430) | 61.8 (636) |

## By r8 (accuracy % (questions))

| r8 | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 60.7 (4160) | 79.6 (4329) | 68.9 (4329) | 72.4 (4367) |
| True | 16.1 (199) | - | - | - |

## By style_status (accuracy % (questions))

| style_status | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| train | - | 79.6 (4329) | 68.9 (4329) | 72.4 (4367) |
| validation | 58.7 (4359) | - | - | - |

## By name_answer (accuracy % (questions))

| name_answer | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 57.6 (4178) | 78.9 (4081) | 67.5 (4081) | 71.6 (4176) |
| True | 84.0 (181) | 92.7 (248) | 92.7 (248) | 89.0 (191) |

## By knowable (accuracy % (questions))

| knowable | validation | P0 | Pword | Pdepth |
|---|---|---|---|---|
| False | 65.7 (248) | 66.7 (276) | 63.0 (276) | 64.1 (256) |
| True | 58.3 (4111) | 80.5 (4053) | 69.3 (4053) | 72.9 (4111) |
