# T1S: T1 + span copy (Amendment 3, PASS-MARKS.md addendum 22)

## Re-screen, seeds 200-201: NOT SHOWN: answer selection (operand copy holds >= 90; next = the learned entry-index signal on the span keys, Amendment 5)

- R1 write_copy exact copy >= 99, operand AND answer, EACH length 1-9, both seeds: FAIL
- R2 pooled-5 T1S - B2 >= -2.0 on both seeds: pass
- R3 chain-5 >= 95 on both seeds, and no length 1-3 write_copy cell below T1's (same seed): FAIL
- R4 tool off < 5 and call accuracy free run >= 98, both seeds: pass
- proved-wrong cells (operand, length 4-9 below 90, n >= 200): none
- every cell at 4-9 digits below 90 (operand or answer): [(200, 'answer', 7, 82.65524625267666), (201, 'answer', 8, 88.56502242152466), (201, 'answer', 9, 86.71023965141612)]
- cells below n = 200 (cannot pass or fail by themselves): none

### Seed 200: pooled-5 T1S 74.5 vs B2 73.0 (+1.52), T1 74.7; chain-5 99.5 (T1 99.7); tool off 0.0; call acc free 98.1 (teacher-forced 98.4); span use {'operand': 98.07692307692308, 'answer': 91.5, 'n_sides': 1612, 'n_rows': 400}

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| operand T1S (unambiguous, n) | 100.0 (396) | 100.0 (412) | 100.0 (429) | 100.0 (446) | 98.8 (400) | 97.2 (432) | 94.2 (415) | 94.4 (481) | 93.7 (427) |
| operand T1 re-scored (unambiguous, n) | 97.8 (1696) | 99.9 (1644) | 99.5 (1668) | 17.8 (1723) | 0.9 (1679) | 0.0 (1718) | 0.0 (1773) | 0.0 (1733) | 0.0 (1717) |
| operand T1S ambiguous, not counted | 78.4 (245) | 80.3 (208) | 76.5 (247) | 77.7 (238) | 73.9 (276) | 69.6 (263) | 65.8 (240) | 66.1 (236) | 66.7 (270) |
| operand T1S old scorer | 91.2 | 92.5 | 92.7 | 93.1 | 89.2 | 86.6 | 83.7 | 83.9 | 83.1 |
| operand T1 old scorer | 85.5 | 93.5 | 84.6 | 13.6 | 0.9 | 0.0 | 0.0 | 0.0 | 0.0 |
| answer T1S (unambiguous, n) | 99.3 (456) | 99.8 (434) | 100.0 (452) | 99.8 (478) | 98.4 (435) | 95.2 (475) | 82.7 (467) | 92.6 (445) | 95.2 (458) |
| answer T1 re-scored (unambiguous, n) | 97.0 (1780) | 97.9 (1765) | 97.9 (1779) | 59.2 (1855) | 2.5 (1792) | 0.0 (1783) | 0.0 (1877) | 0.0 (1869) | - (0) |
| answer T1S ambiguous, not counted | 99.0 (102) | 100.0 (84) | 100.0 (81) | 100.0 (78) | 93.9 (99) | 88.8 (98) | 78.8 (99) | 88.5 (96) | 92.2 (102) |
| answer T1S old scorer | 99.3 | 99.6 | 100.0 | 100.0 | 98.6 | 93.2 | 82.1 | 89.8 | 94.5 |
| answer T1 old scorer | 95.7 | 97.7 | 98.1 | 58.5 | 1.4 | 0.0 | 0.0 | 0.0 | - |
Scorer passes: {'T1S': 2, 'T1': 8}

### Seed 201: pooled-5 T1S 74.0 vs B2 74.3 (-0.26), T1 74.0; chain-5 99.7 (T1 99.9); tool off 0.0; call acc free 98.5 (teacher-forced 98.6); span use {'operand': 98.07692307692308, 'answer': 91.5, 'n_sides': 1612, 'n_rows': 400}

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| operand T1S (unambiguous, n) | 99.5 (395) | 100.0 (412) | 100.0 (428) | 99.6 (447) | 99.5 (399) | 99.1 (429) | 93.3 (418) | 94.6 (483) | 93.7 (428) |
| operand T1 re-scored (unambiguous, n) | 99.1 (1704) | 100.0 (1648) | 99.7 (1672) | 26.9 (1728) | 1.3 (1684) | 0.0 (1725) | 0.0 (1776) | 0.0 (1732) | 0.0 (1725) |
| operand T1S ambiguous, not counted | 74.2 (240) | 84.1 (207) | 79.2 (245) | 81.9 (232) | 77.7 (265) | 71.8 (262) | 68.8 (237) | 69.1 (230) | 67.2 (265) |
| operand T1S old scorer | 89.0 | 94.4 | 93.3 | 93.7 | 91.8 | 87.1 | 86.9 | 85.1 | 85.3 |
| operand T1 old scorer | 85.3 | 93.8 | 86.5 | 25.5 | 1.2 | 0.0 | 0.0 | 0.0 | 0.0 |
| answer T1S (unambiguous, n) | 96.7 (456) | 98.6 (432) | 99.3 (454) | 98.3 (477) | 97.7 (441) | 96.6 (476) | 93.4 (469) | 88.6 (446) | 86.7 (459) |
| answer T1 re-scored (unambiguous, n) | 97.9 (1784) | 99.3 (1779) | 97.5 (1791) | 62.6 (1869) | 0.4 (1813) | 0.0 (1797) | 0.0 (1897) | 0.0 (1869) | - (0) |
| answer T1S ambiguous, not counted | 92.2 (102) | 98.8 (85) | 100.0 (81) | 98.7 (78) | 98.0 (99) | 92.0 (100) | 80.8 (99) | 84.4 (96) | 79.6 (103) |
| answer T1S old scorer | 95.7 | 98.5 | 100.0 | 98.1 | 96.9 | 95.3 | 91.9 | 86.8 | 83.2 |
| answer T1 old scorer | 97.1 | 98.1 | 97.3 | 59.5 | 0.7 | 0.0 | 0.0 | 0.0 | - |
Scorer passes: {'T1S': 2, 'T1': 8}

## 6-seed confirm (marks 1-6 as amended): NOT JUDGED

