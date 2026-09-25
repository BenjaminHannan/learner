# blurt-2 learning loop: GPU result (BensPC, 2026-09-25)

Registered rule: artifacts/claude-blurt2-20260925/PASSMARKS-blurt2.md (origin/main).
Code: scripts/claude_blurt2.py + scripts/claude_blurt1.py + scripts/claude_cre333b_agent.py from origin/main (unmodified).
Command: `python -B scripts/claude_blurt2.py loop --model BASE --out gpu --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl`
BASE = local MiniCPM5-1B snapshot on BensPC (openbmb/MiniCPM5-1B, no download, thinking off).
Python: C:\Users\benja\text-predict\.venv\Scripts\python.exe (torch 2.11.0+cu128, CUDA True, transformers 5.15.0).

## loop_summary.json (whole file)

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {
  "1.0": 39,
  "1.5": 44
 },
 "temp_chosen": 1.5,
 "n_train": 400,
 "n_test": 127,
 "test_dropped_overlap": 23,
 "temp": 1.5,
 "S0_test_before": 6,
 "train_reasoner_right": 21,
 "train_missed": 379,
 "train_missed_then_lucky": 184,
 "lucky_blurts_on_misses": 338,
 "blurts_on_misses": 11370,
 "examples_W": 205,
 "examples_C": 205,
 "S_W_seed0_test_after": 13,
 "S_W_seed0_train_missed_after": 39,
 "S_W_seed1_test_after": 11,
 "S_W_seed1_train_missed_after": 30,
 "S_W_test_after_mean": 12.0,
 "S_C_seed0_test_after": 5,
 "S_C_seed0_train_missed_after": 2,
 "S_C_seed1_test_after": 6,
 "S_C_seed1_train_missed_after": 4,
 "S_C_test_after_mean": 5.5,
 "minutes": 27.7
}
```

## Marks (fresh test set, 127 puzzles after dropping 23 practice/DEV overlaps, reasoner alone, one greedy answer each)

- L1 learning (bar: mean S_W_after − S0 ≥ +8): mean W after = 12 (seeds 13, 11), S0 = 6 → +6. **L1 FAIL.**
  Not proved-wrong (12.0 > 5.5 and 12.0 > 6) and not inconclusive (184 creative wins ≥ 20; S0 6/127 = 4.7% < 60%).
- L2 the creative wins caused it (bar: mean S_W_after − mean S_C_after ≥ +5 AND each W seed beats each C seed):
  12.0 − 5.5 = +6.5; W seeds 13, 11 each beat C seeds 5, 6. **L2 PASS.**

Registered verdict: **FAIL** (PASS needs L1 and L2; L1 failed, L2 passed).

Reported, not marked: temp picked on DEV = 1.5 (lucky blurts 44 vs 39 at 1.0 on 58 missed DEV puzzles);
luck rate on practice misses 338/11370 per-blurt (≈ 1 per 30), 184/379 misses solved at least once;
practice misses solved after sleep: W 39 + 30 (seeds 0, 1), C 2 + 4; seed gap W 2, C 1.
Test puzzles were made inside the run (seed 777) and never printed.

## Run facts

- GPU: NVIDIA GeForce RTX 5070 Ti (BensPC, CUDA 13.1, driver 591.86)
- Wall: 27.7 minutes
- Model commit hash (HF snapshot revision): 87179e5c1f455ef22e6223592d2d61351b525bfc
- No weights pushed (the run saves none; LoRA adapters lived only in GPU memory).
- Files: artifacts/claude-blurt2-20260925/gpu/loop_summary.json, gpu/wins.jsonl (184 rows), gpu/log_loop.txt.
