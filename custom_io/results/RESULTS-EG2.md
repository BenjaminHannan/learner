# EmbeddingGemma 2 arms (PASS-MARKS.md addendum 4), Test LR (addendum 5) and the reader without its window (addendum 6) for B2

Seeds [200, 201], each arm minus plain B2 on the same seed.

## EGE: FAIL (stop this arm)

- 1 pooled-5 gain >= +1.0 on both seeds: 200: +1.59, 201: +2.12 -> True
- 2 variant gain >= +3.0, 2-seed mean: +1.70 -> False
- 3 no dev split drops more than 2.0 (2-seed mean): in_dist: +1.18, answer: +0.25, frame: +3.60, vocab: +2.69, variant: +1.70 -> True
- 4 chain-5 >= 99.0 on both seeds: 200: 99.90, 201: 100.00 -> True
- 5 loops:0 in_dist <= 5 and donor in_dist <= 5 on both seeds: 200: loops0: 18.09, donor: 3.53, 201: loops0: 4.49, donor: 3.46 -> False
  - plain B2 on the same seeds (read only): 200: loops0: 1.40, donor: 3.46, 201: loops0: 4.34, donor: 3.68
- read only: family split change 200: -0.62, 201: -1.25; size {200: {'trainable': 3500881, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 3500881, 'whole': 274503505}, 201: {'trainable': 3500881, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 3500881, 'whole': 274503505}}

## EGT: FAIL (stop this arm)

- 1 pooled-5 gain >= +1.0 on both seeds: 200: +0.18, 201: +0.61 -> False
- 2 variant gain >= +3.0, 2-seed mean: +2.54 -> False
- 3 no dev split drops more than 2.0 (2-seed mean): in_dist: -0.44, answer: -1.08, frame: -0.22, vocab: +1.56, variant: +2.54 -> True
- 4 chain-5 >= 99.0 on both seeds: 200: 99.50, 201: 99.50 -> True
- 5 loops:0 in_dist <= 5 and donor in_dist <= 5 on both seeds: 200: loops0: 2.50, donor: 3.53, 201: loops0: 3.82, donor: 3.82 -> True
  - plain B2 on the same seeds (read only): 200: loops0: 0.00, donor: 3.24, 201: loops0: 10.81, donor: 3.31
- read only: family split change 200: +0.00, 201: +0.62; size {200: {'trainable': 3368785, 'discarded': 66304, 'frozen_borrowed': 0, 'shipped_trainable': 3302481, 'whole': 3302481}, 201: {'trainable': 3368785, 'discarded': 66304, 'frozen_borrowed': 0, 'shipped_trainable': 3302481, 'whole': 3302481}}

## LR: FAIL (stop this arm)

- 1 pooled-5 gain >= +1.0 on both seeds: 200: +1.14, 201: +1.27 -> True
- 2 in_dist at loops:16 minus at 8 >= -0.3 on both seeds: 200: -0.51, 201: -0.22 -> False
  - plain B2 on the same seeds (read only): 200: -1.91, 201: -1.62
- 3 no dev split drops more than 2.0 (2-seed mean): in_dist: -0.22, answer: +0.21, frame: +1.10, vocab: +2.12, variant: +3.14 -> True
- 4 chain-5 >= 99.0 and loops:1 chain-5 <= 5 on both seeds: chain5: 200: 99.50, 201: 99.70, loops1_chain5: 200: 2.20, 201: 3.00 -> True
- 5 loops:0 in_dist <= plain B2 + 1.0 and donor in_dist <= 5 on both seeds: 200: loops0: 15.88, donor: 3.75, 201: loops0: 0.00, donor: 3.60 -> False
  - plain B2 on the same seeds (read only): 200: loops0: 0.00, donor: 3.24, 201: loops0: 10.81, donor: 3.31
- proved wrong: {'pooled5_mean_below_0': False, 'stability_missed_both': False}
- read only: family split change 200: -0.62, 201: -1.88; size {200: None, 201: None}

## EGR: FAIL (stop this arm)

- 1 pooled-5 change >= -1.0 on both seeds: 200: -0.26, 201: -2.68 -> False
- 2 new words + new wording change >= 0.0, 2-seed mean: -0.51 -> False
- 3 no dev split drops more than 2.0 (2-seed mean): in_dist: -1.58, answer: -4.58, frame: -0.74, vocab: -0.12, variant: -0.11 -> False
- 4 chain-5 >= 99.0 on both seeds: 200: 98.80, 201: 99.00 -> False
- 5 loops:0 in_dist <= plain B2 + 1.0 and donor in_dist <= 5 on both seeds: 200: loops0: 11.54, donor: 3.53, 201: loops0: 12.57, donor: 3.60 -> False
  - plain B2 on the same seeds (read only): 200: loops0: 1.40, donor: 3.46, 201: loops0: 4.34, donor: 3.68
- proved wrong: {'pooled5_mean_below_minus3': False, 'chain5_below_95': False}
- read only: family split change 200: -0.62, 201: +0.62; size {200: {'trainable': 2843985, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 2843985, 'whole': 273846609}, 201: {'trainable': 2843985, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 2843985, 'whole': 273846609}}

## R0: the window matters

- B2 minus R0 pooled-5, per seed: 200: 6.84, 201: 6.26 -> read only
- read only: family split change 200: +0.62, 201: +0.62; size {200: None, 201: None}

## EGO: FAIL (stop this arm)

- 1 pooled-5 change >= -1.0 on both seeds: 200: -0.73, 201: -1.84 -> False
- 2 new words + new wording change >= 0.0, 2-seed mean: -0.44 -> False
- 3 no dev split drops more than 2.0 (2-seed mean): in_dist: -1.32, answer: -4.21, frame: -1.03, vocab: +0.56, variant: +0.04 -> False
- 4 chain-5 >= 99.0 on both seeds: 200: 99.00, 201: 99.60 -> True
- 5 loops:0 in_dist <= plain B2 + 1.0 and donor in_dist <= 5 on both seeds: 200: loops0: 11.32, donor: 3.68, 201: loops0: 10.59, donor: 3.24 -> False
  - plain B2 on the same seeds (read only): 200: loops0: 1.40, donor: 3.46, 201: loops0: 4.34, donor: 3.68
- proved wrong: {'pooled5_mean_below_minus3': False, 'chain5_below_95': False}
- read only: family split change 200: -1.25, 201: -1.25; size {200: {'trainable': 2843985, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 2843985, 'whole': 273846609}, 201: {'trainable': 2843985, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 2843985, 'whole': 273846609}}

## EGM: FAIL (stop this arm)

- 1 pooled-5 change >= -1.0 on both seeds: 200: -1.18, 201: -1.36 -> False
- 2 new words + new wording change >= 0.0, 2-seed mean: +0.12 -> True
- 3 no dev split drops more than 2.0 (2-seed mean): in_dist: -1.84, answer: -4.79, frame: -0.85, vocab: +1.75, variant: +0.27 -> False
- 4 chain-5 >= 99.0 on both seeds: 200: 99.70, 201: 99.70 -> True
- 5 loops:0 in_dist <= plain B2 + 1.0 and donor in_dist <= 5 on both seeds: 200: loops0: 11.18, donor: 3.38, 201: loops0: 14.56, donor: 3.75 -> False
  - plain B2 on the same seeds (read only): 200: loops0: 1.40, donor: 3.46, 201: loops0: 4.34, donor: 3.68
- proved wrong: {'pooled5_mean_below_minus3': False, 'chain5_below_95': False}
- read only: family split change 200: -0.62, 201: +0.00; size {200: {'trainable': 2909777, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 2909777, 'whole': 273912401}, 201: {'trainable': 2909777, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 2909777, 'whole': 273912401}}

## EGW: FAIL (stop this arm)

- 1 pooled-5 change >= -1.0 on both seeds: 200: -3.39, 201: -5.30 -> False
- 2 new words + new wording change >= 0.0, 2-seed mean: -3.29 -> False
- 3 no dev split drops more than 2.0 (2-seed mean): in_dist: -5.96, answer: -9.92, frame: -5.07, vocab: -0.25, variant: +0.64 -> False
- 4 chain-5 >= 99.0 on both seeds: 200: 98.30, 201: 97.60 -> False
- 5 loops:0 in_dist <= plain B2 + 1.0 and donor in_dist <= 5 on both seeds: 200: loops0: 5.29, donor: 3.24, 201: loops0: 11.25, donor: 3.46 -> False
  - plain B2 on the same seeds (read only): 200: loops0: 1.40, donor: 3.46, 201: loops0: 4.34, donor: 3.68
- proved wrong: {'pooled5_mean_below_minus3': True, 'chain5_below_95': False}
- read only: family split change 200: +0.62, 201: +0.62; size {200: {'trainable': 22164357, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 22164357, 'whole': 293166981}, 201: {'trainable': 22164357, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 22164357, 'whole': 293166981}}

## EGK: FAIL (unstable: non-finite loss in both runs of seed 201, addendum 14 retry note)

- problems: {200: [], 201: ['missing']}
- 1 pooled-5 gain >= +1.0 on both seeds: 200: +0.98 -> n/a
- 2 variant gain >= +3.0, 2-seed mean: None -> n/a
- 3 no dev split drops more than 2.0 (2-seed mean): in_dist: None, answer: None, frame: None, vocab: None, variant: None -> n/a
- 4 chain-5 >= 99.0 on both seeds: 200: 99.70 -> n/a
- 5 loops:0 in_dist <= 5 and donor in_dist <= 5 on both seeds: 200: loops0: 13.68, donor: 3.38 -> n/a
  - plain B2 on the same seeds (read only): 200: loops0: 1.40, donor: 3.46
- proved wrong: {'pooled5_mean_gain_below_0_5': None}
- read only: family split change 200: -1.25; size {200: {'trainable': 3500881, 'discarded': 0, 'frozen_borrowed': 271002624, 'shipped_trainable': 3500881, 'whole': 274503505}}

## EGO minus EGR (read only, addendum 7)

- 200: pooled5: -0.46, letter_ops: -10.00, copy_word: +0.00, cipher_map: +5.00, digits_parity: +2.50, group_induct: +7.50, 201: pooled5: +0.84, letter_ops: +0.00, copy_word: +0.00, cipher_map: +0.00, digits_parity: -2.50, group_induct: +0.00

## EGM minus EGO (read only, addendum 8)

- 200: pooled5: -0.45, letter_ops: +5.00, copy_word: +0.00, cipher_map: -7.50, digits_parity: +0.00, group_induct: -5.00, 201: pooled5: +0.48, letter_ops: -2.50, copy_word: +0.00, cipher_map: -2.50, digits_parity: +2.50, group_induct: +0.00

## EGW minus EGM (read only, addendum 9)

- 200: pooled5: -2.22, letter_ops: -5.00, copy_word: +0.00, cipher_map: +0.00, digits_parity: -15.00, group_induct: -2.50, 201: pooled5: -3.94, letter_ops: -2.50, copy_word: +0.00, cipher_map: +0.00, digits_parity: -17.50, group_induct: +5.00

## EGK minus EGE (read only, addendum 14)

- 200: pooled5: -0.61, letter_ops: +7.50, copy_word: +0.00, cipher_map: +2.50, digits_parity: +2.50, group_induct: -2.50

## EGE 6-seed confirm, seeds 202-207 (addendum 15): NOT JUDGED

- missing or invalid: 202, 203, 204, 205, 206, 207

## Diagnosis checks (read only, addenda 12 and 13)

- cipher_map in_dist, EGR: 200: 5.00, 201: 2.50 -> letter explanation wrong
- cipher_map in_dist, R0: 200: 12.50, 201: 2.50; EGE: 200: 97.50, 201: 95.00 -> the window is what cipher_map needs

## Device check (read only, addendum 10)

- plain B2 on the rented 5090 minus plain B2 on the PC, pooled-5: 200: +0.48, 201: +0.12

