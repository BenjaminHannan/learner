# blurt-4 hindsight hits: GPU result (rental, 2026-09-25)

Registered rule: artifacts/claude-blurt4-20260925/PASSMARKS-blurt4.md (origin/main).
Code: scripts/claude_blurt4.py + scripts/claude_blurt1.py + scripts/claude_blurt2.py + scripts/claude_cre333b_agent.py from origin/main (unmodified).
Command: `python -B scripts/claude_blurt4.py --model BASE --out gpu-4 --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 8 --test-seed 783 --n-test 80`
BASE = openbmb/MiniCPM5-1B snapshot at commit 87179e5c1f455ef22e6223592d2d61351b525bfc (pinned HF revision, thinking off).
Python: rental image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime (torch 2.8.0+cu128, CUDA True, transformers 5.17.0).

## blurt4_summary.json (whole file)

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {
  "1.0": 41,
  "1.5": 35
 },
 "temp_chosen": 1.0,
 "n_train": 400,
 "n_test": 64,
 "test_dropped_overlap": 16,
 "temp": 1.0,
 "S0_test_before": 1,
 "L0_lucky_blurts": 66,
 "L0_puzzles_hit": 32,
 "train_reasoner_right": 20,
 "train_missed": 380,
 "train_missed_then_lucky": 165,
 "lucky_blurts_on_misses": 327,
 "blurts_on_misses": 11400,
 "hindsight_hits": 375,
 "examples_H": 560,
 "examples_W": 560,
 "examples_P": 560,
 "S_W_seed0_test_after": 5,
 "L_W_seed0_lucky_blurts": 219,
 "L_W_seed0_puzzles_hit": 32,
 "S_W_seed1_test_after": 8,
 "L_W_seed1_lucky_blurts": 223,
 "L_W_seed1_puzzles_hit": 35,
 "L_W_mean": 221.0,
 "S_H_seed0_test_after": 5,
 "L_H_seed0_lucky_blurts": 156,
 "L_H_seed0_puzzles_hit": 41,
 "S_H_seed1_test_after": 3,
 "L_H_seed1_lucky_blurts": 124,
 "L_H_seed1_puzzles_hit": 43,
 "L_H_mean": 140.0,
 "S_P_seed0_test_after": 7,
 "L_P_seed0_lucky_blurts": 163,
 "L_P_seed0_puzzles_hit": 46,
 "S_P_seed1_test_after": 1,
 "L_P_seed1_lucky_blurts": 117,
 "L_P_seed1_puzzles_hit": 42,
 "L_P_mean": 140.0,
 "minutes": 16.0
}
```

## Marks (integer counts)

- Practice: reasoner right 20/400; won 165 of 380 misses (327/11400 blurts); hindsight hits 375; examples H = 560, W = 560, P = 560.
- Test: 64 fresh puzzles (16 overlap drops from requested 80); 30 blurts/puzzle; temp 1.0 picked on DEV (41 vs 35 lucky blurts on 58 missed DEV puzzles).
- L0 lucky blurts before sleep: 66 (32 puzzles hit). Greedy before: 1/64.
- W: seed 0 = 219 (32 hit), greedy 5/64; seed 1 = 223 (35 hit), greedy 8/64; mean 221.0.
- H: seed 0 = 156 (41 hit), greedy 5/64; seed 1 = 124 (43 hit), greedy 3/64; mean 140.0.
- P: seed 0 = 163 (46 hit), greedy 7/64; seed 1 = 117 (42 hit), greedy 1/64; mean 140.0.

## H1 (hindsight adds luck beyond more examples): FAIL

- Mean H >= 1.2 x mean W: 140.0 >= 265.2 is false.
- Each H seed > each W seed: 156 > 219 false; 124 > 223 false.
- Proved-wrong clause (mean H <= mean W): 140.0 <= 221.0 is true, so blurt-4 is proved wrong on H1.
- Not inconclusive (hindsight hits 375 >= 100; L0 66 >= 10).

## H2 (the RIGHT relabel helps): FAIL

- Mean H >= 1.2 x mean P: 140.0 >= 168.0 is false.

## Registered verdict: FAIL (H1 proved wrong; H2 fails)

- GPU: NVIDIA GeForce RTX 5090 (rental, South Korea).
- Wall: 16.0 minutes.
- Model commit hash: 87179e5c1f455ef22e6223592d2d61351b525bfc.
- No weights pushed (the run saves none; LoRA adapters lived only in GPU memory).
- Files: artifacts/claude-blurt4-20260925/gpu-4/blurt4_summary.json (41 keys), gpu-4/log.txt (36 lines).
