# Tricks Mac test (M1 Pro 32 GB, mlx-lm 0.32.x)
Setup once: `python3.12 -m venv ~/venvs/mlx && source ~/venvs/mlx/bin/activate && pip install "mlx-lm>=0.32,<0.33"`, then `cd tricks/mac`. Run one model at a time (32 GB). Set `BOSS` to the local folder if the boss is already on disk.
```
W=mlx-community/Qwen3.5-4B-4bit; BOSS=LiquidAI/LFM2.5-24B-A2B-MLX-4bit
python run_mac.py --part lookup --model $W    --tag w4b_look                  # 1. 4B + forced Wikipedia lookup, ~15-25 min
python run_mac.py --part lookup --model $W    --tag w4b_closed --no-evidence  # 2. 4B closed-book control, ~2 min
python run_mac.py --part lookup --model $BOSS --tag boss_look                 # 3. boss + lookup, ~15-30 min
python run_mac.py --part lookup --model $BOSS --tag boss_closed --no-evidence # 4. boss closed-book, ~2 min
python run_mac.py --part timing --model $W    --tag w4b                       # 5. n=1 vs 8 in one batch vs 8 in a row, 1k and 8k prompt, ~15 min
python run_mac.py --part timing --model $BOSS --tag boss                      # 6. same for the boss, ~15 min
```
Before each lookup run, try `--limit 10 --tag smoke_w4b` (or `smoke_boss`) and read the `[sample]` lines (prompt end and first output). For the boss the sample must show a short answer, not reasoning (see the next line).
LFM2.5-24B-A2B cannot switch thinking off: its template always opens `<think>`, so `--think off` closes it by prefill (a hack, not tested on the real model). If answers come out empty or odd, use `--think on --max-tokens 1024` (slow) or `LiquidAI/LFM2-24B-A2B-MLX-4bit` (the non-reasoning predecessor), and tell Claude.
Interrupted runs resume where they stopped (same command, same `--tag`); use a new tag for a new setting. `--batch 1` runs one prompt at a time (slower; a check against batched answers).
Results land in `tricks/mac/out/`: `rows_<tag>.jsonl` (one row per question), `result_<tag>.json` (accuracy, rare/pop, tokens, seconds, tok/s), `timing_<tag>.json`. Send the whole `out/` folder back.
Pass marks (RANKING.md): timing, voting is out if `ratio_batched8_over_single` > 6; lookup, send fact questions to the boss only if boss+lookup >= 4B+lookup + 5 points (paired CI above 0, computed from the rows files by id).
