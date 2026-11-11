# T1SI write_copy misses, CPU checks (MARKS-D0-T1-2026-10-07.md Amendment 6, read only)

`python -m custom_io.diag_wc_misses --ck .../53-t1si-s200/T1SI_s200/checkpoint.pt .../53-t1si-s201/T1SI_s201/checkpoint.pt --big-data <big build> --passes 2 --length 8 --fresh-n 1000`
(CPU fp32; same 2,793 program rows, oracle and unambiguous rule as Tool.write_copy_u; data in WC-MISSES-T1SI.json).

## 1. The 58 missed s201 8-digit operands (write_copy_u's own two draws)
CPU fp32 reproduces the box's cells: s201 8 digits 87.99 (n 483, 58 misses), s200 98.34 (n 482).

| kind | s201, 8 digits | what it means |
|---|---|---|
| mid_number, inside the wanted number | 46 | right entry, right number, the start pointer sits on its 1st or 2nd digit (entry chars 11-13 in 39 of 46), so the copy is the number's first 1-2 digits |
| other_number, same entry | 10 | right entry, the start pointer sits on one of that entry's operands |
| other_result | 2 | another entry's result |
| cells / cut_short / too_long | 0 / 0 / 0 | the gate always chose the span; the stop head never cut short or ran on |

So 56 of 58 misses are start-pointer misses inside the right entry. Not one is a stop-head miss. In training, results are mostly 1-3 digits, so a result's units digit sits at about entry char 11-13. The misses start at that position.
Same picture at 7 and 9 digits and on s200, where there are fewer misses (miss kinds per length are in the JSON). s201 also has 16 short-operand misses at 1-2 digits, all "other_number" (another number picked).

## 2. Noise check: fresh draw, n >= 1000 per cell (5 passes, oracle seed + '|fresh<p>')

| digits | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| s200 operand | 100.0 | 100.0 | 100.0 | 100.0 | 99.9 | 100.0 | 98.4 | 98.5 | 98.0 |
| s201 operand | 99.6 | 98.0 | 99.7 | 99.7 | 99.1 | 99.2 | 97.7 | 91.6 | 93.2 |
| s200 answer | 99.6 | 100.0 | 99.8 | 100.0 | 99.6 | 99.7 | 99.7 | 99.5 | 98.7 |
| s201 answer | 98.7 | 98.9 | 99.5 | 99.6 | 99.0 | 99.3 | 98.8 | 96.9 | 96.9 |

n is 1,026-1,208 per cell. On the fresh draw, s201's 8-digit cell is 91.6, not 88.0. The weakness is real (the misses are genuine wrong copies of an unambiguous result, not a label artefact). The 88.0 sat about 2 standard errors low. T1SI is not re-judged (Amendment 6, item 1).
