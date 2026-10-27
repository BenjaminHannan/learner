# Experiment 42b — automatic sleep that may only make a small change. Fixed 2026-09-21 before any 42b run
(written after seeing 8 early rows of experiment 42: R20 ≈ 0.05–0.10, R100 seed 4101 = 0.435, squeeze-long rows; no 42b number existed).
One thing changed vs exp-42 R20/R100: which numbers sleep may alter — `embed` = only the new skill's 160-number word vector; `norms` = that plus layer-norm gains/biases (3,040 numbers). LR 1e-2, no weight decay, 3000 updates, same raw replay batches.
Seeds 4101–4105; valid seed = base old skills ≥ 0.95; claims need ≥ 3 valid seeds; every seed shown.
- B1: R20-embed fresh − R20 fresh ≥ 0.20 in ≥ 2/3 of valid seeds → "a tiny allowed change helps from 20 episodes".
- B2: R20-norms fresh − R20 fresh ≥ 0.20 in ≥ 2/3 of valid seeds.
- B3: R100-embed or R100-norms fresh − R100 fresh ≥ 0.20 in ≥ 2/3 of valid seeds.
- B4 (safety): old-skill drop ≤ 0.03 in every valid seed for any arm that is claimed to help.
- Diagnostic (no claim): `seen` accuracy — if the arm cannot even fit the episodes it replayed, the allowed change was too small to hold the skill.
