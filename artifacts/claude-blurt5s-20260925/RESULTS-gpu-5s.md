# blurt-5s own lucky hits vs exact-solver answers: GPU result (rental, 2026-09-25)

Registered rule: artifacts/claude-blurt5s-20260925/PASSMARKS-blurt5s.md (origin/main).
Code: scripts/claude_blurt5s.py + scripts/claude_blurt1.py + scripts/claude_blurt2.py + scripts/claude_cre333b_agent.py from origin/main (unmodified, run only).
Command: `python -B scripts/claude_blurt5s.py --model BASE --out gpu-5s --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 9 --test-seed 785 --n-test 240`
BASE = openbmb/MiniCPM5-1B snapshot at commit 87179e5c1f455ef22e6223592d2d61351b525bfc (pinned HF revision, thinking off).
Python: rental image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel (torch 2.8.0+cu128, CUDA True, transformers 5.17.0).

## blurt5s_summary.json (whole file)

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {
  "1.0": 37,
  "1.5": 44
 },
 "temp_chosen": 1.5,
 "n_train": 400,
 "n_test": 184,
 "test_dropped_overlap": 56,
 "temp": 1.5,
 "n_test_3num": 116,
 "base": {
  "cov@1": 3,
  "cov@5": 28,
  "cov@10": 45,
  "cov@30": 77,
  "lucky": 167
 },
 "own": 20,
 "wins": 191,
 "examples": 211,
 "mean_len_W_wins": 8.13,
 "mean_len_E_wins": 6.96,
 "E_equal_to_own_hit": 9,
 "W_seed0": {
  "cov@1": 8,
  "cov@5": 43,
  "cov@10": 71,
  "cov@30": 112,
  "lucky": 287
 },
 "W_seed1": {
  "cov@1": 9,
  "cov@5": 41,
  "cov@10": 69,
  "cov@30": 108,
  "lucky": 326
 },
 "W_seed2": {
  "cov@1": 8,
  "cov@5": 44,
  "cov@10": 70,
  "cov@30": 110,
  "lucky": 344
 },
 "E_seed0": {
  "cov@1": 12,
  "cov@5": 62,
  "cov@10": 85,
  "cov@30": 123,
  "lucky": 429
 },
 "E_seed1": {
  "cov@1": 14,
  "cov@5": 48,
  "cov@10": 75,
  "cov@30": 113,
  "lucky": 429
 },
 "E_seed2": {
  "cov@1": 12,
  "cov@5": 51,
  "cov@10": 76,
  "cov@30": 117,
  "lucky": 409
 },
 "C_seed0": {
  "cov@1": 9,
  "cov@5": 11,
  "cov@10": 13,
  "cov@30": 14,
  "lucky": 237
 },
 "C_seed1": {
  "cov@1": 7,
  "cov@5": 8,
  "cov@10": 9,
  "cov@30": 12,
  "lucky": 238
 },
 "C_seed2": {
  "cov@1": 8,
  "cov@5": 10,
  "cov@10": 10,
  "cov@30": 11,
  "lucky": 237
 },
 "ci95_W_minus_E_cov30_pct": [
  -8.7,
  0.54
 ],
 "ci95_E_minus_base_cov30_pct": [
  15.77,
  28.96
 ],
 "minutes": 17.8
}
```

## Marks (integer counts)

n_test kept 184 of requested 240 (56 overlap drops), so D = ceil(184/10) = 19.
DEV: 58 missed puzzles; lucky blurts 37 at temp 1.0 vs 44 at temp 1.5, temp 1.5 chosen.
Practice (train seed 9, 400 puzzles): own greedy-correct 20, newly won 191, examples 211 per arm (W and E).
Mean target length: W wins 8.13, E wins 6.96; E targets equal to the own hit on 9 of 191 wins.
Base test coverage: cov@1 3, cov@5 28, cov@10 45, cov@30 77, lucky samples 167 (184 puzzles, 30 samples each).
W cov@30 by seed: 112, 108, 110. E cov@30 by seed: 123, 113, 117. Base cov@30: 77.
C cov@30 by seed: 14, 12, 11 (repeated known answers collapse variety again; not part of S1).
Seed-averaged 95% interval W-E cov@30: [-8.70, 0.54]; E-base cov@30: [15.77, 28.96].
Not inconclusive (191 won practice puzzles >= 20; 20 own greedy-correct answers >= 10).
Sanity passes: W beats base in every seed (112, 108, 110 vs 77).

## S1 (self-made hits are special): FAIL

- Seed 0: W 112 >= E 123 + 19 (= 142)? No (W - E = -11).
- Seed 1: W 108 >= E 113 + 19 (= 132)? No (W - E = -5).
- Seed 2: W 110 >= E 117 + 19 (= 136)? No (W - E = -7).
- Seed-averaged 95% interval for W - E = [-8.70, 0.54] includes zero.
- S1 requires every-seed margin plus an interval excluding zero: not met.

## Proved-wrong clause ("correct supervision is enough"): TRUE

- E >= base + D in every seed: 123 >= 96, 113 >= 96, 117 >= 96 (margins +46, +36, +40).
- Upper bound of W - E = 0.54, below +5 (lower 95% bound of E - W = -0.54, above -5).
- Both conditions hold, so blurt-5s is proved wrong on S1: fresh exact-solver supervision suffices.

## Registered verdict: PROVED WRONG (not a pass; not "no difference shown")

- GPU: NVIDIA GeForce RTX 5090 (vast rental, contract 52639754, offer 49024377).
- Wall: 17.8 minutes (run); instance ~0.47 h total (~28 min per vast duration 1686 s) x $0.5037/h = ~$0.24 (budget $3.00; credit $7.63 at start; 1 rental, no re-rents).
- Model commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc.
- No weights pushed (the run saves none; LoRA adapters lived only in GPU memory).
- Files: artifacts/claude-blurt5s-20260925/gpu-5s/blurt5s_summary.json (98 lines), gpu-5s/log.txt (71 lines), copied back and sha-verified before destroy.
