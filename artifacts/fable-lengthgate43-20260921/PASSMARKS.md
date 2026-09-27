# Experiment 43A — length gate — pass marks (fixed before any full run)

Date: 2026-09-21. Script: scripts/fable_lengthgate43.py. Seeds 4102, 4103, 4104 (the valid exp-42 seeds).
Question: what is the smallest architecture change that lets OLD, fully practised skills
work on inputs longer than any seen in training (trained on lengths 4-8)?

Control (already measured, probe, no claim): registered bases with offset positions:
mean old-skill accuracy at length 10 = 0.10-0.20, at length 12 = 0.00, all three seeds.

Metric: closed-book exact match, mean over the six old ops, 100 fresh inputs per op per length.

| Mark | Arm | Condition | Needed |
|---|---|---|---|
| G0 | each arm | validity: mean accuracy on lengths 4-8 >= 0.95 | per seed; a seed failing G0 is invalid for that arm |
| G1 | randpos | length 10 mean >= 0.90 | 3/3 valid seeds |
| G2 | randpos | length 12 mean >= 0.80 | 3/3 valid seeds |
| G3 | randpos-loop | length 12 mean >= 0.80 | 3/3 valid seeds |
| G4 | randpos-loop vs randpos | length 12 mean higher by >= 0.10 | 3/3 seeds valid in both |

Length 16 is reported, no mark. Every seed reported separately; nothing averaged across seeds.
Reading rules fixed now:
- G1+G2 pass  -> randomised positions become the base for the next sleep experiment (43B).
- G1/G2 fail, G3 pass -> the looped shared block is needed as well.
- all fail -> the length wall is not fixed by either change; say so; next rung = relative-position attention.
- Whatever happens: this is an ARCHITECTURE result about old skills, not a sleep result.
