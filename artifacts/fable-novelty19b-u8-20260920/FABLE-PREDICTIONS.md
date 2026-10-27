# Experiment 19b (U8 vs U5, D only) — Fable's predictions

Written 2026-09-20 by Fable after reading Astra's `design/v3/19-development-readout-and-next-step.md`
and BEFORE any 19b buffer, panel, fit or score exists. They change no pass mark. Counts are out of 64,
"strict" = correct full call sequence and native STOP. Seeds 1900/1901/1902, 2,000 offline updates.

Reasoning in one paragraph: in experiment 19, U (uniform c=1..5) moved the ceiling to 4–6 calls but
unevenly (c4 strict 46–61 / 27; c5 0 / 51–56 / 42). U8 spreads the same 2,000 updates over eight
lengths, so each of c=4,5 gets 12.5% of proposals instead of 20%, and c=6–8 must be learned from a
final-answer-only reward on six-person worlds that cycle. I expect longer execution, partial c=6
success in the best seed, dilution at c=4/5, and no all-seed pass.

| # | Statement | Probability |
|---|---|---|
| P83 | Full development pass (all five conditions, all three seeds) | 0.03 |
| P84 | U8 meets bounded competence (condition 1: all N/P c4/5 and all nine c6–8 cells ≥58 answers and strict) in at least one seed | 0.07 |
| P85 | U8 reaches ≥58 strict on at least one c=6 cell in at least one seed | 0.30 |
| P86 | U8 reaches ≥58 strict on at least one c=7 or c=8 cell in at least one seed | 0.10 |
| P87 | U8's mean calls on the c=8/r10 cell exceed U5's in all three seeds | 0.80 |
| P88 | Treatment-effect mark (U8−U5 ≥13 strict in each of the three c=6/7/8 r10 cells) is met in at least one seed | 0.15 |
| P89 | Dilution: U8's summed strict over the four c=4/5 N cells is below U5's in at least two of three seeds | 0.60 |
| P90 | U8 loses ≥7/64 from the awake anchor on at least one H cell in at least one seed | 0.45 |
| P91 | U5 roughly reproduces experiment 19's U on fresh panels: its c=4 N strict counts are within ±12 of 46/47, 61/59, 27/27 for every seed and cell | 0.60 |
| P92 | Any c=8 edit-pair E cell reaches ≥58 strict pair units in any seed and arm | 0.04 |
| P93 | All seven F cells stay ≥61 answers and strict in U8 in all three seeds | 0.55 |
