# dl-6 GPU: BUDGET-STOP (partial — 27 of 28 nights; no marks, no verdict)

Label claude-fixsleep-dl6b (rent-zdl6b). Sealed origin/main code, never edited.
Code origin/main de083cd30c442262d209b36553df9e556d26a2de.
Model: local snapshot openbmb/MiniCPM5-1B revision 87179e5c1f455ef22e6223592d2d61351b525bfc (same pinned files as dl-2).
Rental 1/1: contract 52778152, offer 45669547 (RTX 5090, South Korea, reliability 0.9980),
image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime, disk 40, torch 2.8.0+cu128, transformers 5.17.0 (pip-installed).
`--selftest` printed "selftest ok". One detached process (PID 522):
`python -B scripts/claude_dl6_light.py --model BASE --out gpu`, launched 16:30:31 UTC, killed by exact PID at ~17:36:30 UTC.

STOP: BUDGET-STOP. Spend hit the $0.57 kill line with L s11 night 6 in progress
(duration 70.8 min x dph $0.4852 = $0.573); killed per the rental rule. Copy-back + destroy ≈ 3 min more,
task total ≈ $0.59 of the $0.60 cap. No re-rents (1 rental used, 2 spare never needed: the first host worked).

## Marks block
NONE — `score()` never ran (process killed before L s11 night 7). No F1-F5, no PASS/FAIL/INCONCLUSIVE, nothing proved wrong.
`gpu/dl6_results.json` (rewritten after every arm-seed) holds S s10, S s11, L s10 (21 nights).
`gpu/log.txt` additionally holds L s11 nights 1-6 (27 of 28 night lines; only L s11 night 7 missing).

Base TEST (100 fresh puzzles x 20 guesses, seed 3590): lucky L0 = 75, reached 35, greedy 7; HARM right 200/300.

Completed arm-seeds (from dl6_results.json):
- S s10 night 7: lucky 198, reached 55, lost 25
- S s11 night 7: lucky 237, reached 58, lost 27
- L s10 night 7: lucky 140, reached 50, lost 13
L s11 (log lines only, nights 1-6): lucky 100, 135, 151, 120, 125, 115; lost 3, 4, 6, 4, 7, 7.

## Counts
- Rentals: 1 (no HOST-FAIL this time; proxy-failure offers 43165145/46753301 and stuck offer 43982861 skipped)
- Selftests: 1 ("selftest ok")
- Night lines printed: 27 of 28 (S 14/14, L s10 7/7, L s11 6/7)
- Marks computed: 0
- GPU: NVIDIA GeForce RTX 5090. Run wall ≈ 66 min (16:30-17:36 UTC). Dollars ≈ $0.59 of $0.60.
- Instance destroyed, 0 claude-fixsleep-dl6b live (confirmed). No weights saved (run saves none).

## Deviations
- D1: Killed at the $0.57 line with 1 night unrun instead of completing steps 3-5 (steps 1-2 done exactly).
- D2: RESULTS-gpu.md has no marks block, F1-F5, verdict, or proved-wrong clause (nothing to quote).
- D3: Credit re-checked before the single rent (8.93) but no re-rents occurred, so no pre-re-rent re-checks were needed.
- D4: Push covers the 3 listed paths with PARTIAL gpu/ contents (21-night json + 27-night log).
