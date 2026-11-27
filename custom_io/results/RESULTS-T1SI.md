# T1SI: T1S + the entry-index term on the span keys (Amendment 5; judged in the T1S columns below, R1-R4 unchanged)

## Re-screen, seeds 200-201: PROVED WRONG: span copy stands falsified; next = the diagnostic fine-tune on 4-9 digit rows

- R1 write_copy exact copy >= 99, operand AND answer, EACH length 1-9, both seeds: FAIL
- R2 pooled-5 T1S - B2 >= -2.0 on both seeds: pass
- R3 chain-5 >= 95 on both seeds, and no length 1-3 write_copy cell below T1's (same seed): FAIL
- R4 tool off < 5 and call accuracy free run >= 98, both seeds: pass
- proved-wrong cells (operand, length 4-9 below 90, n >= 200): [(201, 'operand', 8, 87.99171842650104)]
- every cell at 4-9 digits below 90 (operand or answer): [(201, 'operand', 8, 87.99171842650104)]
- cells below n = 200 (cannot pass or fail by themselves): none

### Seed 200: pooled-5 T1S 74.8 vs B2 73.0 (+1.75), T1 74.7; chain-5 99.6 (T1 99.7); tool off 0.0; call acc free 98.5 (teacher-forced 98.6); span use {'operand': 98.07692307692308, 'answer': 91.5, 'n_sides': 1612, 'n_rows': 400}

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| operand T1S (unambiguous, n) | 100.0 (394) | 100.0 (412) | 100.0 (429) | 100.0 (445) | 100.0 (399) | 99.8 (433) | 97.6 (417) | 98.3 (482) | 97.2 (428) |
| operand T1 re-scored (unambiguous, n) | 97.8 (1696) | 99.9 (1644) | 99.5 (1668) | 17.8 (1723) | 0.9 (1679) | 0.0 (1718) | 0.0 (1773) | 0.0 (1733) | 0.0 (1717) |
| operand T1S ambiguous, not counted | 75.6 (242) | 85.7 (210) | 82.2 (241) | 82.8 (232) | 77.9 (272) | 77.0 (265) | 76.0 (233) | 77.6 (232) | 72.7 (264) |
| operand T1S old scorer | 90.6 | 95.1 | 94.2 | 94.2 | 91.3 | 90.9 | 90.9 | 90.6 | 89.3 |
| operand T1 old scorer | 85.5 | 93.5 | 84.6 | 13.6 | 0.9 | 0.0 | 0.0 | 0.0 | 0.0 |
| answer T1S (unambiguous, n) | 99.8 (454) | 100.0 (431) | 100.0 (453) | 99.8 (471) | 99.3 (432) | 99.4 (472) | 98.9 (467) | 99.3 (443) | 97.8 (458) |
| answer T1 re-scored (unambiguous, n) | 97.0 (1780) | 97.9 (1765) | 97.9 (1779) | 59.2 (1855) | 2.5 (1792) | 0.0 (1783) | 0.0 (1877) | 0.0 (1869) | - (0) |
| answer T1S ambiguous, not counted | 97.1 (104) | 100.0 (83) | 100.0 (81) | 100.0 (78) | 100.0 (99) | 100.0 (99) | 99.0 (99) | 100.0 (96) | 96.1 (102) |
| answer T1S old scorer | 99.6 | 100.0 | 100.0 | 99.6 | 99.3 | 99.7 | 98.6 | 99.0 | 98.0 |
| answer T1 old scorer | 95.7 | 97.7 | 98.1 | 58.5 | 1.4 | 0.0 | 0.0 | 0.0 | - |
Scorer passes: {'T1S': 2, 'T1': 8}

### Seed 201: pooled-5 T1S 74.6 vs B2 74.3 (+0.36), T1 74.0; chain-5 99.8 (T1 99.9); tool off 0.0; call acc free 98.9 (teacher-forced 99.0); span use {'operand': 98.07692307692308, 'answer': 91.5, 'n_sides': 1612, 'n_rows': 400}

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| operand T1S (unambiguous, n) | 98.7 (395) | 97.3 (414) | 100.0 (429) | 100.0 (447) | 99.8 (401) | 99.3 (432) | 95.9 (418) | 88.0 (483) | 93.9 (429) |
| operand T1 re-scored (unambiguous, n) | 99.1 (1704) | 100.0 (1648) | 99.7 (1672) | 26.9 (1728) | 1.3 (1684) | 0.0 (1725) | 0.0 (1776) | 0.0 (1732) | 0.0 (1725) |
| operand T1S ambiguous, not counted | 75.0 (244) | 79.1 (211) | 76.7 (249) | 78.9 (237) | 71.7 (276) | 72.1 (269) | 64.9 (242) | 57.9 (235) | 53.5 (271) |
| operand T1S old scorer | 89.3 | 90.8 | 91.6 | 93.5 | 89.2 | 87.4 | 83.5 | 74.5 | 80.8 |
| operand T1 old scorer | 85.3 | 93.8 | 86.5 | 25.5 | 1.2 | 0.0 | 0.0 | 0.0 | 0.0 |
| answer T1S (unambiguous, n) | 98.5 (456) | 99.1 (435) | 99.8 (454) | 99.0 (478) | 99.8 (437) | 99.4 (478) | 98.9 (469) | 96.8 (441) | 95.9 (460) |
| answer T1 re-scored (unambiguous, n) | 97.9 (1784) | 99.3 (1779) | 97.5 (1791) | 62.6 (1869) | 0.4 (1813) | 0.0 (1797) | 0.0 (1897) | 0.0 (1869) | - (0) |
| answer T1S ambiguous, not counted | 96.2 (104) | 98.8 (85) | 100.0 (81) | 100.0 (79) | 99.0 (100) | 98.0 (100) | 98.0 (101) | 96.9 (97) | 95.1 (103) |
| answer T1S old scorer | 98.2 | 99.6 | 100.0 | 98.8 | 99.3 | 98.6 | 98.3 | 97.3 | 95.7 |
| answer T1 old scorer | 97.1 | 98.1 | 97.3 | 59.5 | 0.7 | 0.0 | 0.0 | 0.0 | - |
Scorer passes: {'T1S': 2, 'T1': 8}

## 6-seed confirm (marks 1-6 as amended): NOT JUDGED

