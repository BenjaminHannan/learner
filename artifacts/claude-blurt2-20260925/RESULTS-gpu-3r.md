# blurt-3r learning loop: GPU replication result (BensPC, 2026-09-25)

Registered rule: artifacts/claude-blurt2-20260925/PASSMARKS-blurt3.md, section "Replication blurt-3r" (origin/main).
Code: scripts/claude_blurt2.py + scripts/claude_blurt1.py + scripts/claude_cre333b_agent.py from origin/main (unmodified).
Command: `python -B scripts/claude_blurt2.py loop --model BASE --out gpu-3r --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --train-seed 6 --test-seed 781 --n-test 80 --luck`
BASE = local MiniCPM5-1B snapshot on BensPC (openbmb/MiniCPM5-1B, no download, thinking off).
Python: C:\Users\benja\text-predict\.venv\Scripts\python.exe (torch 2.11.0+cu128, CUDA True, transformers 5.15.0).

## loop_summary.json (whole file)

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {
  "1.0": 27,
  "1.5": 46
 },
 "temp_chosen": 1.5,
 "n_train": 400,
 "n_test": 67,
 "test_dropped_overlap": 13,
 "temp": 1.5,
 "S0_test_before": 1,
 "L0_lucky_blurts": 59,
 "L0_puzzles_hit": 29,
 "train_reasoner_right": 22,
 "train_missed": 378,
 "train_missed_then_lucky": 158,
 "lucky_blurts_on_misses": 304,
 "blurts_on_misses": 11340,
 "extra_distinct_hits": 0,
 "examples_W": 180,
 "examples_C": 180,
 "S_W_seed0_test_after": 6,
 "L_W_seed0_lucky_blurts": 129,
 "L_W_seed0_puzzles_hit": 40,
 "S_W_seed0_train_missed_after": 34,
 "S_W_seed1_test_after": 6,
 "L_W_seed1_lucky_blurts": 148,
 "L_W_seed1_puzzles_hit": 43,
 "S_W_seed1_train_missed_after": 48,
 "S_W_test_after_mean": 6.0,
 "S_C_seed0_test_after": 2,
 "L_C_seed0_lucky_blurts": 59,
 "L_C_seed0_puzzles_hit": 4,
 "S_C_seed0_train_missed_after": 0,
 "S_C_seed1_test_after": 2,
 "L_C_seed1_lucky_blurts": 58,
 "L_C_seed1_puzzles_hit": 3,
 "S_C_seed1_train_missed_after": 0,
 "S_C_test_after_mean": 2.0,
 "minutes": 31.1
}
```

## Marks (lucky blurts on the fresh test set, mean of the two seeds; 67 puzzles after dropping 13 practice/DEV overlaps, 30 blurts per puzzle = 2010 per measurement)

- U1 luck rises (bar: mean W >= 1.5 x L0): mean W = 138.5 (seeds 129, 148), L0 = 59 → 138.5 >= 88.5. **U1 PASS.**
  Not inconclusive (158 won practice puzzles >= 20; L0 59 >= 10).
- U2 the wins caused it (bar: mean W >= 1.3 x mean C, and each W seed beats each C seed):
  mean W 138.5 vs mean C 58.5 (seeds 59, 58) → 138.5 >= 76.05; W seeds 129, 148 each beat C seeds 59, 58. **U2 PASS.**
  Not proved-wrong (138.5 > 58.5).

Registered verdict: **PASS** (PASS needs U1 and U2; both passed). Blurt-3 already PASSED, so 3r passing means "replicated" is claimed.

Reported, not marked: temp picked on DEV = 1.5 (lucky blurts 46 vs 27 at 1.0 on 58 missed DEV puzzles);
luck rate on practice misses 304/11340 per-blurt, 158/378 misses solved at least once;
test puzzles with at least one lucky blurt: before 29, W 40 + 43, C 4 + 3;
greedy solves (reasoner alone): before 1/67, W 6 + 6, C 2 + 2;
practice misses solved after sleep: W 34 + 48, C 0 + 0.
Test puzzles were made inside the run (seed 781) and never printed.

## Run facts

- GPU: NVIDIA GeForce RTX 5070 Ti (BensPC, CUDA 13.1, driver 591.86)
- Wall: 31.1 minutes
- Model commit hash (HF snapshot revision): 87179e5c1f455ef22e6223592d2d61351b525bfc
- No weights pushed (the run saves none; LoRA adapters lived only in GPU memory).
- Files: artifacts/claude-blurt2-20260925/gpu-3r/loop_summary.json, gpu-3r/wins.jsonl (158 rows), gpu-3r/log_loop.txt.
