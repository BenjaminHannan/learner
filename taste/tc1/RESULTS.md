# TC-1 results (toy Paint taste critic; card experiment, not the village model)

Sealed spec and full write-up: /mnt/project-files/night-mode/UNCHECKABLE-SKILLS-2026-10-12.md sec. 8. Outputs: night-mode/tc1-v1, tc1b,
tc1b-6seeds-6nights, tc1b-12nights, tc1c. Mean hidden house score after the last night, temperature 1.0 (C = critic picks,
R = random picks, O = oracle picks; M = 0.05 bar).

| run | change | seeds x nights | C | R | best control | O | verdict |
|---|---|---|---|---|---|---|---|
| TC-1 | (base: uniform-clutter day-0 programs) | 3 x 6 | 0.064 | 0.063 | 0.067 | 0.101 | TOY TOO HARD |
| TC-1b | touching-shapes day-0 prior | 3 x 6 | 0.114 | 0.070 | 0.077 | 0.168 | UNDERPOWERED |
| TC-1b ext. | (pre-set extension) | 6 x 12 | 0.197 | 0.070 | 0.084* | 0.244 | NOT A PASS (variety 0.676 < 0.687) |
| TC-1c | + each folded picture kept once a night | 6 x 12 | 0.176 | 0.074 | 0.103* | 0.193 | **PASS** |

\* per-seed best of {B, H, R07 at 0.7/1.0, N at 0.7/1.0}, averaged. A 6 x 6 run (first extension launch, which dropped the nights
setting by a script bug) is kept as extra data: C 0.107 vs R 0.072.

Scope: a critic learned only from 200 finished pictures taught a small maker some house traits (mostly roofs) in a 12x12 toy when
the night keeps only distinct pictures. Without that guard, long practice narrowed what the maker drew.
