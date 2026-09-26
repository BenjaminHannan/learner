# tgt-5 GPU results (registered run, 2026-09-26)

Rental: instance 52674236, NVIDIA GeForce RTX 5090, label rent-tgt5, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime.
BASE: openbmb/MiniCPM5-1B snapshot 87179e5c1f455ef22e6223592d2d61351b525bfc (matches expected commit).
Code: unmodified origin/main scripts (claude_tgt5.py + blurt1/2/4/5s + cre333b agent) via git archive; never edited.
Command: `python -B scripts/claude_tgt5.py --model BASE --out gpu --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 9 --pair-seed 795`
Selftest before the run: `selftest ok`.
Wall: script-reported 10.7 min; rental ~0.38 h x $0.49444/h = ~$0.19 of $1.00 budget, 1 rental, no re-rents.
gpu/ holds tgt5_summary.json, pairs.jsonl (120 pairs), contrasts.json, log.txt.

## Whole tgt5_summary.json

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {
  "1.0": 41,
  "1.5": 44
 },
 "temp_chosen": 1.5,
 "temp": 1.5,
 "n_pairs": 120,
 "n_hands": 60,
 "base": {
  "pairs_D_pos": 81,
  "mean_D": 0.5069,
  "raw_pairs_D_pos": 79,
  "raw_mean_D": 0.3849
 },
 "own": 20,
 "wins": 179,
 "examples": 199,
 "W_seed0": {
  "pairs_D_pos": 97,
  "mean_D": 1.5264,
  "raw_pairs_D_pos": 97,
  "raw_mean_D": 1.6863
 },
 "W_seed1": {
  "pairs_D_pos": 97,
  "mean_D": 2.0673,
  "raw_pairs_D_pos": 100,
  "raw_mean_D": 2.1987
 },
 "W_seed2": {
  "pairs_D_pos": 100,
  "mean_D": 2.1138,
  "raw_pairs_D_pos": 98,
  "raw_mean_D": 2.2763
 },
 "E_seed0": {
  "pairs_D_pos": 109,
  "mean_D": 2.4548,
  "raw_pairs_D_pos": 107,
  "raw_mean_D": 2.6766
 },
 "E_seed1": {
  "pairs_D_pos": 103,
  "mean_D": 2.417,
  "raw_pairs_D_pos": 104,
  "raw_mean_D": 2.4902
 },
 "E_seed2": {
  "pairs_D_pos": 102,
  "mean_D": 2.4695,
  "raw_pairs_D_pos": 102,
  "raw_mean_D": 2.4851
 },
 "C_seed0": {
  "pairs_D_pos": 89,
  "mean_D": 1.8179,
  "raw_pairs_D_pos": 91,
  "raw_mean_D": 2.0624
 },
 "C_seed1": {
  "pairs_D_pos": 87,
  "mean_D": 2.124,
  "raw_pairs_D_pos": 87,
  "raw_mean_D": 2.3693
 },
 "C_seed2": {
  "pairs_D_pos": 81,
  "mean_D": 2.6775,
  "raw_pairs_D_pos": 85,
  "raw_mean_D": 3.0522
 },
 "W_minus_base_mean_D": 1.3956,
 "W_minus_base_bounds_98_33": [
  1.0099,
  1.797
 ],
 "minutes": 10.7
}
```

## Registered verdict: PASS

PASS clause (PASSMARKS-tgt5.md): "W has D > 0 on at least 84/120 pairs in EACH of its three seeds, AND the mean of (W's D averaged over seeds − base D) is at least 0.20 nats with a lower bound above 0."
Numbers: W seeds 97/120, 97/120, 100/120 (each ≥ 84); mean difference 1.3956 nats (≥ 0.20) with 98.33% bootstrap bounds [1.0099, 1.797], lower bound 1.0099 > 0. Both conditions met: PASS.
Proved-wrong clause ("sleep did not improve target matching": the upper bound of that mean is at or below 0): upper bound 1.797 > 0, NOT triggered.
Inconclusive check: won practice puzzles 179 (≥ 20), own greedy-correct answers 20 (≥ 10): conclusive.
Reported counts: base 81/120 masked (79/120 raw), mean D 0.5069 masked (0.3849 raw); practice wins 179, examples 199, DEV temp rule 1.0 vs 1.5 → 1.5.
Interpretation limit (reviewer): a pass shows better target matching, not a new arithmetic procedure.
