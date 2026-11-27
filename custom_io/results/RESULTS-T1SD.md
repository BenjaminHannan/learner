# T1SD: T1SI + the distance-from-end table on the span keys (Amendment 7 marks + Clarification 7a; T1SD in the T1S columns below)

## Re-screen, seeds 200-201: NOT SHOWN: one more change, named from a miss breakdown of the failing cell, run before building it

- R1 per side and seed: mean of the nine length cells >= 99 and every cell >= 97 (n >= 1000 per cell): FAIL
- R2 pooled-5 T1SD - B2 >= -2.0 on both seeds: pass
- R3 1-3 digit operand and answer cells >= 99 and no more than 1.0 below T1's re-score: pass
- R4 tool off < 5 and call accuracy free run >= 98, both seeds: pass
- S2 chain-5 >= 95 on both seeds: pass
- R1 per side and seed: 200 operand: mean 99.3, worst 97.5; 200 answer: mean 99.0, worst 97.6; 201 operand: mean 99.6, worst 98.4; 201 answer: mean 99.5, worst 99.0
- reading (a), all nine cells >= 99 (printed beside, not a mark): {'200 operand': False, '200 answer': False, '201 operand': False, '201 answer': False}
- proved-wrong cells (operand or answer, length 4-9 below 90, n >= 1000): none
- cells below n = 1000 (cannot pass or fail by themselves): none

### Seed 200: pooled-5 T1S 74.6 vs B2 73.0 (+1.56), T1 74.7; chain-5 99.6 (T1 99.7); tool off 0.0; call acc free 98.3 (teacher-forced 98.5); span use {'operand': 98.07692307692308, 'answer': 91.5, 'n_sides': 1612, 'n_rows': 400}

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| operand T1SD (unambiguous, n) | 99.9 (1044) | 100.0 (1018) | 100.0 (1077) | 100.0 (1073) | 99.6 (1041) | 99.3 (1082) | 99.1 (1096) | 97.5 (1094) | 98.6 (1074) |
| operand T1 re-scored (unambiguous, n) | 97.8 (1696) | 99.9 (1644) | 99.5 (1668) | 17.8 (1723) | 0.9 (1679) | 0.0 (1718) | 0.0 (1773) | 0.0 (1733) | 0.0 (1717) |
| operand T1SD ambiguous, not counted | 77.6 (606) | 82.3 (605) | 78.3 (637) | 80.0 (599) | 75.3 (652) | 75.5 (609) | 76.4 (563) | 71.5 (608) | 73.1 (603) |
| operand T1SD old scorer | 91.2 | 95.4 | 93.9 | 93.3 | 91.7 | 90.3 | 92.5 | 86.6 | 89.3 |
| operand T1 old scorer | 85.5 | 93.5 | 84.6 | 13.6 | 0.9 | 0.0 | 0.0 | 0.0 | 0.0 |
| answer T1SD (unambiguous, n) | 99.9 (1081) | 100.0 (1092) | 99.7 (1098) | 99.8 (1147) | 99.1 (1136) | 99.0 (1151) | 97.9 (1156) | 97.6 (1187) | 97.6 (1133) |
| answer T1 re-scored (unambiguous, n) | 97.0 (1780) | 97.9 (1765) | 97.9 (1779) | 59.2 (1855) | 2.5 (1792) | 0.0 (1783) | 0.0 (1877) | 0.0 (1869) | - (0) |
| answer T1SD ambiguous, not counted | 99.6 (250) | 100.0 (220) | 99.6 (233) | 99.5 (212) | 99.1 (214) | 97.3 (256) | 96.1 (230) | 97.4 (230) | 95.7 (253) |
| answer T1SD old scorer | 100.0 | 100.0 | 100.0 | 100.0 | 98.9 | 99.3 | 97.2 | 98.6 | 96.9 |
| answer T1 old scorer | 95.7 | 97.7 | 98.1 | 58.5 | 1.4 | 0.0 | 0.0 | 0.0 | - |
Scorer passes: {'T1S': 5, 'T1': 8}

### Seed 201: pooled-5 T1S 74.4 vs B2 74.3 (+0.12), T1 74.0; chain-5 99.5 (T1 99.9); tool off 0.0; call acc free 98.8 (teacher-forced 98.9); span use {'operand': 98.07692307692308, 'answer': 91.5, 'n_sides': 1612, 'n_rows': 400}

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| operand T1SD (unambiguous, n) | 100.0 (1040) | 100.0 (1016) | 100.0 (1076) | 99.9 (1081) | 99.8 (1047) | 99.6 (1079) | 99.4 (1092) | 98.4 (1089) | 99.6 (1068) |
| operand T1 re-scored (unambiguous, n) | 99.1 (1704) | 100.0 (1648) | 99.7 (1672) | 26.9 (1728) | 1.3 (1684) | 0.0 (1725) | 0.0 (1776) | 0.0 (1732) | 0.0 (1725) |
| operand T1SD ambiguous, not counted | 75.4 (597) | 82.8 (603) | 81.1 (629) | 84.4 (570) | 79.9 (633) | 78.5 (613) | 78.2 (550) | 75.5 (597) | 75.0 (597) |
| operand T1SD old scorer | 91.4 | 95.0 | 93.9 | 95.1 | 92.7 | 90.2 | 92.8 | 89.3 | 89.8 |
| operand T1 old scorer | 85.3 | 93.8 | 86.5 | 25.5 | 1.2 | 0.0 | 0.0 | 0.0 | 0.0 |
| answer T1SD (unambiguous, n) | 99.4 (1095) | 99.8 (1105) | 99.7 (1120) | 99.7 (1168) | 99.7 (1176) | 99.6 (1162) | 99.7 (1181) | 99.4 (1197) | 99.0 (1153) |
| answer T1 re-scored (unambiguous, n) | 97.9 (1784) | 99.3 (1779) | 97.5 (1791) | 62.6 (1869) | 0.4 (1813) | 0.0 (1797) | 0.0 (1897) | 0.0 (1869) | - (0) |
| answer T1SD ambiguous, not counted | 97.2 (250) | 99.1 (223) | 98.3 (233) | 99.1 (213) | 99.5 (214) | 99.2 (257) | 99.1 (231) | 97.0 (232) | 97.3 (255) |
| answer T1SD old scorer | 99.3 | 99.6 | 100.0 | 100.0 | 99.0 | 98.6 | 100.0 | 99.3 | 98.1 |
| answer T1 old scorer | 97.1 | 98.1 | 97.3 | 59.5 | 0.7 | 0.0 | 0.0 | 0.0 | - |
Scorer passes: {'T1S': 5, 'T1': 8}

## 6-seed confirm (marks 1-6 as amended): NOT JUDGED

