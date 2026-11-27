# T1SD_s200 answer-miss breakdown (Amendment 7: NOT SHOWN, breakdown before any change)

Read only, CPU fp32, `python3 -m custom_io.diag_wc_misses --ck .../60-t1sd-s200/T1SD_s200/checkpoint.pt --big-data <curriculum seed 1, dev-per-cell 200>
--passes 5 --length 8 --answer-lengths 5 6 7 8 9 --fresh-n 1000` (checkpoint sha256 b70682f7..., the box's own; in_dist sha 3e3a5edb05c7).
The failing cell: seed 200's answer side (mean of nine cells 98.96 on the box, mark 99). Seed 201's checkpoint is not here (see the thread).

## Answer cells: write_copy_u's own five draws re-run on CPU, and a fresh draw

| digits | own draws, exact (n) | fresh draw, exact (n) | own-draw misses by kind |
|---|---|---|---|
| 1 | 99.91 (1081) | 99.91 (1098) | prompt_number 1 |
| 2 | 100.00 (1092) | 100.00 (1117) |  |
| 3 | 99.73 (1098) | 99.92 (1199) | other_result 3 |
| 4 | 99.83 (1147) | 99.64 (1118) | same_entry_operand 1, other_result 1 |
| 5 | 99.12 (1136) | 98.79 (1078) | other_result 5, not_span 3, prompt_number 1, same_entry_operand 1 |
| 6 | 98.96 (1151) | 98.32 (1132) | other_result 10, same_entry_operand 1, not_span 1 |
| 7 | 97.84 (1156) | 97.42 (1163) | same_entry_operand 11, other_result 10, prompt_number 4 |
| 8 | 97.56 (1187) | 98.04 (1175) | other_result 18, same_entry_operand 7, prompt_number 4 |
| 9 | 97.62 (1133) | 97.72 (1098) | other_result 18, prompt_number 5, same_entry_operand 3, not_span 1 |

Mean of nine: own draws 98.95 (box, bf16 cuda: 98.96), fresh 98.86. The CPU re-run matches the box to within 0.1 at 7-9 digits, and the
fresh draw lands in the same place, so the miss is not draw noise.

## What the 81 misses at 7-9 digits are (own draws)

- In 80 of 81 the mode head chose the span and the start pointer sits on the units digit of a WRONG number (1 chose GEN). No cut_short, too_long
  or mid_number: the stop head and the step-left copy work; the error is which number the answer pointer picks.
- Which number: the previous entry's result 45, an operand inside the right entry 21, a prompt number 13, another result 1.
- 80 of 81 copy a SHORTER number than the answer: 42 one digit, 26 two digits, 8 three, 2 four (2 seven, 1 nine).
- 80 of 81 wanted the newest entry's result.
- Training answers are short: of 13,638 program rows in the first 60,000 curriculum training rows, answers are 1 digit 20.0%, 2 digits 54.7%,
  3 digits 24.9%, 4 digits 0.5%, 5+ none. Write-copy answers at 5-9 digits are all outside that range.

Shown: the counts above. Suggested, not tested: the answer pointer learned a short-number prior from training answers, which pulls it to a short
number when the true answer is long. Seed 201 reads 99.0-100 on the same cells, so the prior's strength varies by seed.

Operand side (cell 8, own draws 97.53, fresh 98.61): mid_number 12, other_result 10, other_number 5.
