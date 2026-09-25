# RESULTS-blurt1 (rent-blurt1 DEV measurement, 2026-09-25)

DEV only. No pass marks, no TEST-ONLY panel. Code: scripts/claude_blurt1.py (unmodified).

## Puzzle determinism check (step 1)
On the rental, after setup:
`python -B scripts/claude_blurt1.py make --out /tmp/pzcheck --n 60 --seed 1` then
`cmp /tmp/pzcheck/puzzles.jsonl artifacts/claude-blurt1-dev-20260925/puzzles.jsonl`
printed nothing (same 60 puzzles).

## Runs (step 2, sequential, each under nohup)
1. `python -B scripts/claude_blurt1.py puzzle --model BASE --puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --out artifacts/claude-blurt1-dev-20260925/run/puzzles_t06.jsonl --n 30 --temp 0.6`
   last line: `puzzles 60: lucky blurts 2/1800, solved at least once 2/60`
2. `python -B scripts/claude_blurt1.py puzzle --model BASE --puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --out artifacts/claude-blurt1-dev-20260925/run/puzzles_t10.jsonl --n 30 --temp 1.0`
   last line: `puzzles 60: lucky blurts 4/1800, solved at least once 3/60`
3. `python -B scripts/claude_blurt1.py ideas --model BASE --dev artifacts/claude-cre333e-dev-20260924 --out artifacts/claude-blurt1-dev-20260925/run/ideas_t10.jsonl --n 30 --temp 1.0`
   log has 42 lines (40 item lines + header context); no summary line printed by design.

## Row counts (checked on Mac after copy-back)
- artifacts/claude-blurt1-dev-20260925/run/puzzles_t06.jsonl: 60 rows
- artifacts/claude-blurt1-dev-20260925/run/puzzles_t10.jsonl: 60 rows
- artifacts/claude-blurt1-dev-20260925/run/ideas_t10.jsonl: 40 rows, 30 blurts each
- logs: artifacts/claude-blurt1-dev-20260925/run/log_puzzle_t06.txt (63 lines), log_puzzle_t10.txt (63 lines), log_ideas_t10.txt (42 lines)

## Machine / money
- GPU: 1x RTX 5090, South Korea (offer 45669396), contract 52513848, label rent-blurt1
- dph: $0.49629629629629624
- rented 2026-09-25 01:46:36Z, running ~01:49Z, destroyed 2026-09-25 02:00:27Z
- hours: ~0.23 (13.9 min alive); dollars: ~$0.11 (0.2308 h x $0.4963)
- budget $0.60: respected. Credit at start $1.90.
- rentals used: 1 of 4 allowed. No HOST-FAIL, no BUDGET-STOP.
- BASE model: openbmb/MiniCPM5-1B commit 87179e5c1f455ef22e6223592d2d61351b525bfc
- setup: image torch 2.8.0+cu128 True, pip transformers>=5 safetensors huggingface_hub accelerate numpy, route122 smoke test ok, HF_HUB_OFFLINE=1
- wall time total (create to destroy): ~14 min. Individual process walls not separately timed; t06 done by 01:54Z poll, t10 done by 01:56Z poll, ideas done by 01:59Z poll.
