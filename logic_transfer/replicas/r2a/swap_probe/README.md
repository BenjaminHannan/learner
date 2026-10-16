# Swap-pair binding probe

## State probe

Prereg item 3 (`logic_transfer/PREREG-SWAP-PROBE-2026-10-16.md`). `logic_transfer/state_probe.py`; results in `STATE_PROBE.json` (per checkpoint x feature set x task: AUC mean, fold AUCs, n, chosen C). Linear probe = L2 logistic regression, standardised features, C by 3-fold inner CV, 5-fold CV grouped by pair_id; AUC is on held-out pairs. Features: `zf` = ln_z of control token 1 after the last loop (the state mode_head and q_word read; primary); `qword` = q_word(zf); `ctrl_mean` = the 8 control tokens after the loop, mean-pooled (the flattened 2048-d block is extracted and cached but not probed: too slow to fit here, see the module docstring); `zf_it1/3/5` = zf after iteration 1/3/5 (last is 7). Tasks: T1 split vs bound, equal-not, dev vocabulary; T2 the same, differ-not; T3 word-missing vs bound (positive control); T4 shuffled-label control (split/bound label swapped at the pair level by a seeded coin; T4b, T4c are two more coins, in the JSON); T5 train T1 on dev, test on newwords equal-not pairs. `pointer` = AUC of the model's own logP(unknown), split vs bound, same rows and folds (nothing fitted).

Primary feature set `zf`, test AUC (mean over folds):

| checkpoint | T1 eq-not | T2 diff-not | T3 word-missing | T4 shuffled | T5 transfer | pointer T1 |
|---|---|---|---|---|---|---|
| parent-s200 | 0.517 | 0.509 | 0.525 | 0.516 | 0.490 | 0.512 |
| parent-s201 | 0.512 | 0.501 | 0.495 | 0.502 | 0.486 | 0.495 |
| parent-s204 | 0.496 | 0.516 | 0.519 | 0.493 | 0.513 | 0.508 |
| s200-s1 | 0.604 | 0.713 | 0.743 | 0.500 | 0.622 | 0.587 |
| s200-s2 | 0.506 | 0.576 | 0.657 | 0.487 | 0.482 | 0.510 |
| s201-s1 | 0.487 | 0.492 | 0.616 | 0.496 | 0.518 | 0.502 |
| s201-s2 | 0.476 | 0.487 | 0.650 | 0.503 | 0.505 | 0.503 |
| s204-s1 | 0.485 | 0.527 | 0.623 | 0.500 | 0.515 | 0.504 |
| s204-s2 | 0.495 | 0.585 | 0.618 | 0.491 | 0.522 | 0.507 |

Feature set `qword`:

| checkpoint | T1 eq-not | T2 diff-not | T3 word-missing | T4 shuffled | T5 transfer | pointer T1 |
|---|---|---|---|---|---|---|
| parent-s200 | 0.505 | 0.516 | 0.503 | 0.510 | 0.495 | 0.512 |
| parent-s201 | 0.509 | 0.488 | 0.479 | 0.496 | 0.480 | 0.495 |
| parent-s204 | 0.498 | 0.512 | 0.516 | 0.513 | 0.502 | 0.508 |
| s200-s1 | 0.600 | 0.700 | 0.734 | 0.489 | 0.614 | 0.587 |
| s200-s2 | 0.512 | 0.549 | 0.651 | 0.488 | 0.508 | 0.510 |
| s201-s1 | 0.485 | 0.477 | 0.614 | 0.500 | 0.500 | 0.502 |
| s201-s2 | 0.499 | 0.492 | 0.638 | 0.498 | 0.524 | 0.503 |
| s204-s1 | 0.495 | 0.526 | 0.612 | 0.483 | 0.525 | 0.504 |
| s204-s2 | 0.512 | 0.541 | 0.608 | 0.490 | 0.483 | 0.507 |

Feature set `ctrl_mean`:

| checkpoint | T1 eq-not | T2 diff-not | T3 word-missing | T4 shuffled | T5 transfer | pointer T1 |
|---|---|---|---|---|---|---|
| parent-s200 | 0.514 | 0.531 | 0.529 | 0.505 | 0.487 | 0.512 |
| parent-s201 | 0.508 | 0.504 | 0.512 | 0.488 | 0.488 | 0.495 |
| parent-s204 | 0.482 | 0.496 | 0.530 | 0.488 | 0.500 | 0.508 |
| s200-s1 | 0.603 | 0.686 | 0.716 | 0.501 | 0.618 | 0.587 |
| s200-s2 | 0.508 | 0.555 | 0.653 | 0.506 | 0.487 | 0.510 |
| s201-s1 | 0.493 | 0.483 | 0.570 | 0.497 | 0.502 | 0.502 |
| s201-s2 | 0.487 | 0.474 | 0.616 | 0.502 | 0.505 | 0.503 |
| s204-s1 | 0.492 | 0.512 | 0.568 | 0.499 | 0.510 | 0.504 |
| s204-s2 | 0.502 | 0.531 | 0.579 | 0.505 | 0.513 | 0.507 |

Feature set `zf_it1`:

| checkpoint | T1 eq-not | T2 diff-not | T3 word-missing | T4 shuffled | T5 transfer | pointer T1 |
|---|---|---|---|---|---|---|
| parent-s200 | 0.499 | 0.510 | 0.519 | 0.517 | 0.503 | 0.512 |
| parent-s201 | 0.506 | 0.518 | 0.513 | 0.516 | 0.502 | 0.495 |
| parent-s204 | 0.484 | 0.505 | 0.530 | 0.490 | 0.503 | 0.508 |
| s200-s1 | 0.586 | 0.631 | 0.667 | 0.516 | 0.594 | 0.587 |
| s200-s2 | 0.482 | 0.503 | 0.560 | 0.494 | 0.500 | 0.510 |
| s201-s1 | 0.488 | 0.506 | 0.598 | 0.489 | 0.517 | 0.502 |
| s201-s2 | 0.480 | 0.516 | 0.628 | 0.507 | 0.523 | 0.503 |
| s204-s1 | 0.488 | 0.525 | 0.607 | 0.513 | 0.513 | 0.504 |
| s204-s2 | 0.500 | 0.554 | 0.602 | 0.489 | 0.508 | 0.507 |

Feature set `zf_it3`:

| checkpoint | T1 eq-not | T2 diff-not | T3 word-missing | T4 shuffled | T5 transfer | pointer T1 |
|---|---|---|---|---|---|---|
| parent-s200 | 0.511 | 0.515 | 0.519 | 0.522 | 0.515 | 0.512 |
| parent-s201 | 0.508 | 0.518 | 0.519 | 0.496 | 0.476 | 0.495 |
| parent-s204 | 0.475 | 0.526 | 0.521 | 0.492 | 0.505 | 0.508 |
| s200-s1 | 0.593 | 0.662 | 0.707 | 0.508 | 0.603 | 0.587 |
| s200-s2 | 0.498 | 0.546 | 0.618 | 0.495 | 0.490 | 0.510 |
| s201-s1 | 0.495 | 0.507 | 0.613 | 0.489 | 0.527 | 0.502 |
| s201-s2 | 0.483 | 0.511 | 0.637 | 0.508 | 0.510 | 0.503 |
| s204-s1 | 0.479 | 0.536 | 0.614 | 0.498 | 0.523 | 0.504 |
| s204-s2 | 0.497 | 0.571 | 0.616 | 0.484 | 0.498 | 0.507 |

Feature set `zf_it5`:

| checkpoint | T1 eq-not | T2 diff-not | T3 word-missing | T4 shuffled | T5 transfer | pointer T1 |
|---|---|---|---|---|---|---|
| parent-s200 | 0.506 | 0.512 | 0.513 | 0.516 | 0.502 | 0.512 |
| parent-s201 | 0.511 | 0.509 | 0.498 | 0.498 | 0.479 | 0.495 |
| parent-s204 | 0.488 | 0.523 | 0.522 | 0.488 | 0.508 | 0.508 |
| s200-s1 | 0.602 | 0.696 | 0.734 | 0.504 | 0.612 | 0.587 |
| s200-s2 | 0.504 | 0.565 | 0.645 | 0.490 | 0.485 | 0.510 |
| s201-s1 | 0.489 | 0.498 | 0.615 | 0.494 | 0.517 | 0.502 |
| s201-s2 | 0.485 | 0.487 | 0.645 | 0.506 | 0.520 | 0.503 |
| s204-s1 | 0.492 | 0.534 | 0.620 | 0.497 | 0.519 | 0.504 |
| s204-s2 | 0.497 | 0.580 | 0.618 | 0.490 | 0.515 | 0.507 |

Prereg probe thresholds, applied mechanically (replicas = the six 8,000-update checkpoints; parents shown above for the floor):

| feature set | T1 AUC < 0.65 | T1 AUC >= 0.75 | pointer AUC < 0.65 | T1 >= 0.75 and pointer < 0.65 | T4 outside 0.40-0.60 | T3 < 0.80 |
|---|---|---|---|---|---|---|
| zf | 6/6 | 0/6 | 6/6 | 0/6 | 0/9 | 9/9 |
| qword | 6/6 | 0/6 | 6/6 | 0/6 | 0/9 | 9/9 |
| ctrl_mean | 6/6 | 0/6 | 6/6 | 0/6 | 0/9 | 9/9 |
| zf_it1 | 6/6 | 0/6 | 6/6 | 0/6 | 0/9 | 9/9 |
| zf_it3 | 6/6 | 0/6 | 6/6 | 0/6 | 0/9 | 9/9 |
| zf_it5 | 6/6 | 0/6 | 6/6 | 0/6 | 0/9 | 9/9 |

Primary set `zf`: T1 < 0.65 in s200-s1, s200-s2, s201-s1, s201-s2, s204-s1, s204-s2; T1 >= 0.75 in none; pointer < 0.65 in s200-s1, s200-s2, s201-s1, s201-s2, s204-s1, s204-s2. Instrument checks (all 9 checkpoints): T4 outside 0.40-0.60: none (any of the 3 coins: none); T3 below 0.80: parent-s200, parent-s201, parent-s204, s200-s1, s200-s2, s201-s1, s201-s2, s204-s1, s204-s2.

Commands (cwd /home/user/replica):

```
python3 -m logic_transfer.state_probe verify --ckpt logic_transfer/replicas/r2a/s200-s1/checkpoint.pt
python3 -m logic_transfer.state_probe all
```
