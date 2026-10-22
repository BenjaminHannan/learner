# Swarm screen readout, card S0

**DRY RUN: tiny preset, CPU, T=30 s; the numbers mean nothing (second pass: --min-items 1)**

directory `/home/user/learner/artifacts/claude-swarm-screen-20261018/dryrun`; seeds [0, 1, 2]; T = 30; far_deep minimum 1 items; seconds tolerance 2%

| mark | what | status | bar | value |
|---|---|---|---|---|
| M1 | join (promote): far_deep, S0 - D1 | fail | S0 - D1 >= +3.0 pts pooled, p < 0.01, positive on >= 2 of 3 seeds | +0.00 pts pooled (n 186), p 1, per seed +0.00, +0.00, +0.00 |
| M2 | DEV slip (guard): near / overall, S0 vs D1 | pass | S0 vs D1: near slips on < 2 seeds AND overall slips on < 2 seeds (slip = below by more than 3.0 pts) | near slips on 0/3 seeds, overall slips on 0/3 seeds |
| M3 | desk usage (guard), S0 | fail | every desk ask_rate >= 0.05 and min fetch_count >= 0.1 x max, on >= 2 of 3 seeds | ok on 0/3 seeds |
| M4 | diversity (guard), S0 | pass | info; collapsed (register_cos > 0.95 and fetch_overlap > 0.8) on >= 2 of 3 seeds -> 'COLLAPSED: the desks are copies' | collapsed on 0/3 seeds; s0: overlap 0.005 cos 0.380 ask [1.0, 0.0, 0.0, 0.01] fetch [12.0, 0.0, 0.0, 0.19] silent 3 / s1: overlap nan cos 0.984 ask [0.0, 0.0, 0.0, 0.0] fetch [0.0, 0.0, 0.0, 0.0] silent 4 / s2: overlap nan cos 0.988 ask [0.0, 0.0, 0.0, 0.0] fetch [0.0, 0.0, 0.0, 0.0] silent 4 |
| M5 | matching (validity) | pass | every train completed, train_seconds within T +- 2% (T from c0.json), loop_mismatches = 0, final loss finite, one data tag and one tokenizer sha256 | valid |
| M6 | cells | pass | far_deep has >= 1 items in every eval file (else INSUFFICIENT) | far_deep n: min 62, max 62 over 6 files |
| KILL | kill condition: pooled <= 0 or S0 < D1 on >= 2 of 3 seeds | fail | pooled S0 - D1 <= 0 OR negative on >= 2 of 3 seeds (a KILL is shown as fail) | pooled +0.00 pts, negative on 0/3 seeds |

VERDICT: KILL: S0 does not beat D1 on far_deep (pooled +0.00 pts, negative on 0/3 seeds); the swarm line stops

## Information (not marks)

Steps in T, per arm (mean over seeds):

| arm | steps per seed | mean | over D1 | parameters |
|---|---|---|---|---|
| D1 | [103, 107, 109] | 106.33333333333333 | 1.000 | [304388] |
| S0 | [92, 98, 91] | 93.66666666666667 | 0.881 | [304516] |

Pooled accuracy % (hits/n) over seeds, validation:

| cell | D1 | S0 |
|---|---|---|
| overall | 0.0 (0/564) | 0.0 (0/564) |
| near | 0.0 (0/315) | 0.0 (0/315) |
| far | 0.0 (0/219) | 0.0 (0/219) |
| far_deep | 0.0 (0/186) | 0.0 (0/186) |
| multi_hop | 0.0 (0/366) | 0.0 (0/366) |
| depth_1 | 0.0 (0/168) | 0.0 (0/168) |
| depth_2 | 0.0 (0/159) | 0.0 (0/159) |
| depth_3 | 0.0 (0/126) | 0.0 (0/126) |
| depth_4 | 0.0 (0/69) | 0.0 (0/69) |
| depth_5 | 0.0 (0/12) | 0.0 (0/12) |
| depth_6 | n/a (0/0) | n/a (0/0) |
| changed | 0.0 (0/204) | 0.0 (0/204) |
