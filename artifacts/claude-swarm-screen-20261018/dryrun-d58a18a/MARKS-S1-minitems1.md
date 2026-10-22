# Swarm screen readout, card S1

**DRY RUN: tiny preset, CPU, T=120 s; the numbers mean nothing (second pass: --min-items 1)**

directory `/home/user/learner/artifacts/claude-swarm-screen-20261018/dryrun-d58a18a`; seeds [0, 1, 2]; T = 120; far_deep minimum 1 items; seconds tolerance 2%

| mark | what | status | bar | value |
|---|---|---|---|---|
| M1 | communication adds: far_deep, S1 - S0 | fail | S1 - S0 >= +3.0 pts pooled, p < 0.01, positive on >= 2 of 3 seeds | -1.61 pts pooled (n 186), p 0.9375, per seed +0.00, -4.84, +0.00 |
| M2 | board is used: S1 intact - S1 lesion=board on far_deep | fail | intact - lesion >= +3.0 pts pooled, p < 0.01, positive on >= 2 of 3 seeds | +0.00 pts pooled (n 186), p 1, per seed +0.00, +0.00, +0.00 |
| M3 | DEV slip vs D1 (guard): near / overall, S1 vs D1 | pass | S1 vs D1: near slips on < 2 seeds AND overall slips on < 2 seeds (slip = below by more than 3.0 pts) | near slips on 0/3 seeds, overall slips on 0/3 seeds |
| M4 | desk usage (guard), S1 | fail | every desk ask_rate >= 0.05 and min fetch_count >= 0.1 x max, on >= 2 of 3 seeds | ok on 0/3 seeds |
| M5 | diversity (guard), S1 | pass | info; collapsed (register_cos > 0.95 and fetch_overlap > 0.8) on >= 2 of 3 seeds -> 'COLLAPSED: the desks are copies' | collapsed on 0/3 seeds; s0: overlap nan cos 0.789 ask [0.0, 0.0, 0.0, 0.0] fetch [0.0, 0.0, 0.0, 0.0] silent 4 / s1: overlap nan cos 0.952 ask [0.0, 0.0, 0.0, 0.0] fetch [0.0, 0.0, 0.0, 0.0] silent 4 / s2: overlap nan cos 0.998 ask [0.0, 0.0, 0.0, 0.0] fetch [0.0, 0.0, 0.0, 0.0] silent 4 // S1 - S0 register_cos per seed +0.255, +0.052, +0.014 |
| M6 | validity | pass | every train completed, train_seconds within T +- 2% (T from c0.json), loop_mismatches = 0, final loss finite, one data tag and one tokenizer sha256 | valid |
| M6b | cells | pass | far_deep has >= 1 items in every eval file (else INSUFFICIENT) | far_deep n: min 62, max 62 over 18 files |
| KILL-COMM | pooled S1 - S0 <= 0 or S1 < S0 on >= 2 of 3 seeds | fail | a KILL-COMM is shown as fail | pooled -1.61 pts, negative on 1/3 seeds |

VERDICT: KILL-COMM: S1 does not beat S0 on far_deep (pooled -1.61 pts, negative on 1/3 seeds)

## Information (not marks)

Steps in T, per arm (mean over seeds):

| arm | steps per seed | mean | over D1 | parameters |
|---|---|---|---|---|
| D1 | [414, 424, 402] | 413.3333333333333 | 1.000 | [304388] |
| S0 | [386, 371, 369] | 375.3333333333333 | 0.908 | [304516] |
| S1 | [322, 331, 337] | 330.0 | 0.798 | [304580] |

Pooled accuracy % (hits/n) over seeds, validation:

| cell | D1 | S0 | S1 |
|---|---|---|---|
| overall | 0.5 (3/564) | 4.4 (25/564) | 2.1 (12/564) |
| near | 0.6 (2/315) | 5.1 (16/315) | 2.5 (8/315) |
| far | 0.5 (1/219) | 4.1 (9/219) | 1.8 (4/219) |
| far_deep | 0.5 (1/186) | 3.8 (7/186) | 2.2 (4/186) |
| multi_hop | 0.8 (3/366) | 3.6 (13/366) | 2.2 (8/366) |
| depth_1 | 0.0 (0/168) | 7.1 (12/168) | 2.4 (4/168) |
| depth_2 | 1.3 (2/159) | 5.7 (9/159) | 1.3 (2/159) |
| depth_3 | 0.0 (0/126) | 3.2 (4/126) | 4.8 (6/126) |
| depth_4 | 1.4 (1/69) | 0.0 (0/69) | 0.0 (0/69) |
| depth_5 | 0.0 (0/12) | 0.0 (0/12) | 0.0 (0/12) |
| depth_6 | n/a (0/0) | n/a (0/0) | n/a (0/0) |
| changed | 1.5 (3/204) | 6.4 (13/204) | 2.0 (4/204) |

S1 information rows (pooled paired differences, far_deep):

- lesion_board_drop: +0.00 pts (n 186, p 1, seeds positive 0)
- lesion_notes_drop: +0.00 pts (n 186, p 1, seeds positive 0)
- lesion_cards_drop: +0.00 pts (n 186, p 1, seeds positive 0)
- S1_vs_D1_far_deep: +1.61 pts (n 186, p 0.1875, seeds positive 2)
- S0_vs_D1_far_deep: +3.23 pts (n 186, p 0.03516, seeds positive 2)
