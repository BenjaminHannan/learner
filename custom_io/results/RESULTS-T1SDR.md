# T1SDR: T1SD + drawn-result drills, ans_drill 0.25 (Amendment 8 marks; T1SDR in the T1S columns below)

## Re-screen, seeds 200-201: NOT SHOWN (failing: R4): a miss breakdown first, then at most one more change (the entries-back table on the answer keys is the only one named)

- R1 per side and seed: mean of the nine length cells >= 99 and every cell >= 97 (n >= 1000 per cell): pass
- R2 pooled-5 T1SD - B2 >= -2.0 on both seeds: pass
- R3 1-3 digit operand and answer cells >= 99 and no more than 1.0 below T1's re-score: pass
- R4 tool off < 5 and call accuracy free run >= 98, both seeds: FAIL
- S2 chain-5 >= 95 on both seeds: pass
- R5 natural (drill-free) in_dist number-answer exact, T1SDR - T1SD >= -1.0 on both seeds: pass
- R1 per side and seed: 200 operand: mean 99.5, worst 99.2; 200 answer: mean 100.0, worst 100.0; 201 operand: mean 99.1, worst 98.6; 201 answer: mean 100.0, worst 100.0
- reading (a), all nine cells >= 99 (printed beside, not a mark): {'200 operand': True, '200 answer': True, '201 operand': False, '201 answer': True}
- proved-wrong cells (operand or answer, length 4-9 below 90, n >= 1000): none
- natural in_dist, seed 200 (R5 = number answers; all rows and per-length cells beside, not marks): T1SDR 87.39 vs T1SD 87.27 (n 825); all rows 90.29 vs 90.37; by length 1: 86.77 vs 85.71 (n 189), 2: 84.77 vs 85.74 (n 512), 3: 99.15 vs 95.76 (n 118), 4: 100.0 vs 100.0 (n 6)
- natural in_dist, seed 201 (R5 = number answers; all rows and per-length cells beside, not marks): T1SDR 88.24 vs T1SD 89.21 (n 825); all rows 90.88 vs 91.03; by length 1: 90.48 vs 89.42 (n 189), 2: 84.96 vs 87.11 (n 512), 3: 98.31 vs 97.46 (n 118), 4: 100.0 vs 100.0 (n 6)
- cells below n = 1000 (cannot pass or fail by themselves): none

### Seed 200: pooled-5 T1S 74.9 vs B2 73.0 (+1.94), T1 74.7; chain-5 99.7 (T1 99.7); tool off 0.0; call acc free 97.9 (teacher-forced 98.3); span use {'operand': 98.07692307692308, 'answer': 91.5, 'n_sides': 1612, 'n_rows': 400}

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| operand T1SDR (unambiguous, n) | 99.8 (1045) | 99.2 (1019) | 99.3 (1074) | 99.6 (1080) | 99.8 (1043) | 99.6 (1081) | 99.3 (1097) | 99.3 (1094) | 99.3 (1073) |
| operand T1 re-scored (unambiguous, n) | 97.8 (1696) | 99.9 (1644) | 99.5 (1668) | 17.8 (1723) | 0.9 (1679) | 0.0 (1718) | 0.0 (1773) | 0.0 (1733) | 0.0 (1717) |
| operand T1SDR ambiguous, not counted | 21.2 (614) | 22.7 (608) | 21.8 (650) | 22.0 (628) | 23.5 (680) | 20.1 (622) | 21.5 (576) | 20.8 (619) | 21.7 (618) |
| operand T1SDR old scorer | 70.7 | 72.9 | 68.9 | 73.2 | 70.1 | 69.8 | 71.0 | 71.4 | 69.7 |
| operand T1 old scorer | 85.5 | 93.5 | 84.6 | 13.6 | 0.9 | 0.0 | 0.0 | 0.0 | 0.0 |
| answer T1SDR (unambiguous, n) | 100.0 (1085) | 100.0 (1096) | 100.0 (1111) | 100.0 (1148) | 100.0 (1159) | 100.0 (1158) | 100.0 (1166) | 100.0 (1189) | 100.0 (1137) |
| answer T1 re-scored (unambiguous, n) | 97.0 (1780) | 97.9 (1765) | 97.9 (1779) | 59.2 (1855) | 2.5 (1792) | 0.0 (1783) | 0.0 (1877) | 0.0 (1869) | - (0) |
| answer T1SDR ambiguous, not counted | 100.0 (247) | 100.0 (220) | 100.0 (233) | 100.0 (211) | 100.0 (214) | 100.0 (257) | 100.0 (230) | 100.0 (230) | 100.0 (253) |
| answer T1SDR old scorer | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| answer T1 old scorer | 95.7 | 97.7 | 98.1 | 58.5 | 1.4 | 0.0 | 0.0 | 0.0 | - |
Scorer passes: {'T1S': 5, 'T1': 8}

### Seed 201: pooled-5 T1S 74.1 vs B2 74.3 (-0.15), T1 74.0; chain-5 99.7 (T1 99.9); tool off 0.0; call acc free 98.6 (teacher-forced 98.8); span use {'operand': 98.07692307692308, 'answer': 91.5, 'n_sides': 1612, 'n_rows': 400}

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| operand T1SDR (unambiguous, n) | 99.6 (1041) | 99.8 (1020) | 99.4 (1075) | 99.4 (1083) | 98.8 (1044) | 98.8 (1082) | 98.6 (1089) | 98.6 (1091) | 99.2 (1071) |
| operand T1 re-scored (unambiguous, n) | 99.1 (1704) | 100.0 (1648) | 99.7 (1672) | 26.9 (1728) | 1.3 (1684) | 0.0 (1725) | 0.0 (1776) | 0.0 (1732) | 0.0 (1725) |
| operand T1SDR ambiguous, not counted | 21.1 (612) | 20.7 (613) | 19.5 (650) | 18.8 (626) | 19.7 (681) | 15.8 (626) | 18.0 (573) | 18.2 (615) | 19.9 (613) |
| operand T1SDR old scorer | 70.5 | 72.2 | 69.8 | 72.7 | 68.3 | 67.6 | 69.0 | 70.1 | 67.6 |
| operand T1 old scorer | 85.3 | 93.8 | 86.5 | 25.5 | 1.2 | 0.0 | 0.0 | 0.0 | 0.0 |
| answer T1SDR (unambiguous, n) | 100.0 (1086) | 100.0 (1099) | 100.0 (1107) | 100.0 (1151) | 100.0 (1161) | 100.0 (1159) | 100.0 (1169) | 100.0 (1190) | 100.0 (1141) |
| answer T1 re-scored (unambiguous, n) | 97.9 (1784) | 99.3 (1779) | 97.5 (1791) | 62.6 (1869) | 0.4 (1813) | 0.0 (1797) | 0.0 (1897) | 0.0 (1869) | - (0) |
| answer T1SDR ambiguous, not counted | 100.0 (250) | 100.0 (222) | 100.0 (232) | 100.0 (211) | 100.0 (212) | 100.0 (256) | 100.0 (232) | 100.0 (231) | 100.0 (253) |
| answer T1SDR old scorer | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| answer T1 old scorer | 97.1 | 98.1 | 97.3 | 59.5 | 0.7 | 0.0 | 0.0 | 0.0 | - |
Scorer passes: {'T1S': 5, 'T1': 8}

## 6-seed confirm (marks 1-6 as amended): NOT SHOWN (failing: 4, 5; mark 5 open on seed(s) 205). Mark 4 donor fails as Amendment 12 item 6 says: the confirm stays NOT SHOWN on mark 4 unless Ben explicitly clears it

- 1 parity (Amendment 2): mean T1 - B2 >= -1.0, 95% CI lower >= -2.0, T1 >= B2 - 1.0 on >= 5 of 6 seeds: pass
- 2 chain-5 mean within 1.0 of B2 and >= 99 on 5 of 6 seeds: pass
- 3 tool off: noexec program set < 5 on every seed: pass
- 4 loops:0 and donor in_dist <= 5 on every seed: FAIL
- 5 opswap (Amendment 12): lower of unambiguous-only and own-pointer >= 99, unambiguous n >= 500, every seed: FAIL
- 6 no dev split 6-seed mean drop > 2.0: pass
- parity: mean +0.62, sd 0.81, 95% CI [-0.23, +1.46], seeds within 1.0: 6 of 6
- proved wrong (pooled-5 mean < -2.0 or chain-5 mean < 95): False
- mark 5 re-scores read the --opswap-dev set (LF or CRLF copy of the same file): True; open seeds: [205]
- Amendment 11 item 1 other reading (not a mark): a value over 5 counts as a miss only if it is > 1.0 above B2 on that seed: misses {200: ['donor'], 201: ['loops0', 'donor'], 202: ['donor'], 203: ['donor'], 205: ['donor']} -> FAIL

| seed | pooled-5 T1SDR - B2 | chain-5 T1SDR / B2 | tool off | loops:0 T1SDR / B2 | donor T1SDR / B2 | swap mark 5 (unamb / own / text; n; amb rate) | B2 swap | swap run (text) | machine differs |
|---|---|---|---|---|---|---|---|---|---|
| 200 | +1.94 | 99.7 / 99.4 | 0.0 | 1.6 / 0.0 | 5.6 / 3.2 | 99.9 (99.9 / 99.9 / 97.5; n 772; 7.3%) | 99.9 | 97.5 | ['data'] |
| 201 | -0.15 | 99.7 / 99.6 | 0.0 | 12.9 / 10.8 | 5.1 / 3.3 | 99.3 (99.5 / 99.3 / 97.2; n 773; 7.2%) | 99.9 | 97.2 | ['data'] |
| 202 | +0.18 | 99.8 / 99.6 | 0.0 | 2.5 / 0.0 | 5.6 / 3.3 | 99.4 (99.5 / 99.4 / 97.1; n 773; 7.3%) | 99.9 | 97.1 | - |
| 203 | +0.89 | 99.6 / 99.5 | 0.0 | 3.4 / 5.7 | 5.1 / 3.1 | 99.7 (99.7 / 99.8 / 97.3; n 771; 7.3%) | 99.9 | 97.3 | - |
| 204 | +0.96 | 99.7 / 99.6 | 0.0 | 2.1 / 3.5 | 5.0 / 3.8 | 99.6 (99.6 / 99.6 / 97.2; n 772; 7.3%) | 99.9 | 97.2 | ['data'] |
| 205 | -0.12 | 99.8 / 99.7 | 0.0 | 4.6 / 0.0 | 5.6 / 3.5 | open | - | 97.6 | ['data'] |

