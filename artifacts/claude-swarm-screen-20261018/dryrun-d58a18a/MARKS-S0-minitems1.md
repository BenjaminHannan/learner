# Swarm screen readout, card S0

**DRY RUN: tiny preset, CPU, T=120 s; the numbers mean nothing (second pass: --min-items 1)**

directory `/home/user/learner/artifacts/claude-swarm-screen-20261018/dryrun-d58a18a`; seeds [0, 1, 2]; T = 120; far_deep minimum 1 items; seconds tolerance 2%

| mark | what | status | bar | value |
|---|---|---|---|---|
| M1 | join (promote): far_deep, S0 - D1 | fail | S0 - D1 >= +3.0 pts pooled, p < 0.01, positive on >= 2 of 3 seeds | +3.23 pts pooled (n 186), p 0.03516, per seed +1.61, +8.06, +0.00 |
| M2 | DEV slip (guard): near / overall, S0 vs D1 | pass | S0 vs D1: near slips on < 2 seeds AND overall slips on < 2 seeds (slip = below by more than 3.0 pts) | near slips on 0/3 seeds, overall slips on 0/3 seeds |
| M3 | desk usage (guard), S0 | fail | every desk ask_rate >= 0.05 and min fetch_count >= 0.1 x max, on >= 2 of 3 seeds | ok on 0/3 seeds |
| M4 | diversity (guard), S0 | pass | info; collapsed (register_cos > 0.95 and fetch_overlap > 0.8) on >= 2 of 3 seeds -> 'COLLAPSED: the desks are copies' | collapsed on 0/3 seeds; s0: overlap 0.246 cos 0.534 ask [0.74, 0.0, 0.23, 0.3] fetch [11.77, 0.0, 3.76, 4.79] silent 1 / s1: overlap 0.000 cos 0.899 ask [0.0, 0.25, 0.0, 0.0] fetch [0.0, 4.0, 0.0, 0.0] silent 3 / s2: overlap 0.000 cos 0.984 ask [0.25, 0.0, 0.0, 0.0] fetch [4.0, 0.0, 0.0, 0.0] silent 3 |
| M5 | matching (validity) | pass | every train completed, train_seconds within T +- 2% (T from c0.json), loop_mismatches = 0, final loss finite, one data tag and one tokenizer sha256 | valid |
| M6 | cells | pass | far_deep has >= 1 items in every eval file (else INSUFFICIENT) | far_deep n: min 62, max 62 over 6 files |
| KILL | kill condition: pooled <= 0 or S0 < D1 on >= 2 of 3 seeds | pass | pooled S0 - D1 <= 0 OR negative on >= 2 of 3 seeds (a KILL is shown as fail) | pooled +3.23 pts, negative on 0/3 seeds |

VERDICT: FAIL (M3 USAGE-COLLAPSE)

## Information (not marks)

Steps in T, per arm (mean over seeds):

| arm | steps per seed | mean | over D1 | parameters |
|---|---|---|---|---|
| D1 | [414, 424, 402] | 413.3333333333333 | 1.000 | [304388] |
| S0 | [386, 371, 369] | 375.3333333333333 | 0.908 | [304516] |

Pooled accuracy % (hits/n) over seeds, validation:

| cell | D1 | S0 |
|---|---|---|
| overall | 0.5 (3/564) | 4.4 (25/564) |
| near | 0.6 (2/315) | 5.1 (16/315) |
| far | 0.5 (1/219) | 4.1 (9/219) |
| far_deep | 0.5 (1/186) | 3.8 (7/186) |
| multi_hop | 0.8 (3/366) | 3.6 (13/366) |
| depth_1 | 0.0 (0/168) | 7.1 (12/168) |
| depth_2 | 1.3 (2/159) | 5.7 (9/159) |
| depth_3 | 0.0 (0/126) | 3.2 (4/126) |
| depth_4 | 1.4 (1/69) | 0.0 (0/69) |
| depth_5 | 0.0 (0/12) | 0.0 (0/12) |
| depth_6 | n/a (0/0) | n/a (0/0) |
| changed | 1.5 (3/204) | 6.4 (13/204) |
