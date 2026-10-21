# T1: the calculator outside the model (PASS-MARKS.md addendum 17)

T1 minus q33 plain B2 on the same seed.

## Screen, seeds 200-201: NOT SHOWN at the screen: diagnose the link, no 6-seed run

- S1 pooled-5 T1 - B2 >= -2.0 on both seeds: {200: +1.72, 201: -0.31} -> True
- S2 chain-5 >= 95 on both seeds: {200: +99.70, 201: +99.90} -> True
- S3 write_copy operand and answer exact copy >= 99 on both seeds (D0 writing, addendum 17): {200: {operand: +29.28, answer: +42.08}, 201: {operand: +30.94, answer: +42.35}} -> False

| seed | call acc TF / free | free-run program | tool off | swap | loops:0 T1 / B2 | donor T1 / B2 | copy gate | machine differs |
|---|---|---|---|---|---|---|---|---|
| 200 | +98.39 / +98.26 | +96.75 | +0.29 | +95.90 | +9.41 / +0.00 | +4.85 / +3.24 | +0.70 | ['data'] |
| 201 | +98.76 / +98.64 | +97.50 | +0.53 | +96.51 | +5.00 / +10.81 | +4.78 / +3.31 | +0.73 | ['data'] |

## 6-seed confirm, seeds 200-205: NOT JUDGED

- missing or invalid: {202: [T1 missing], 203: [T1 missing], 204: [T1 missing], 205: [T1 missing]}

