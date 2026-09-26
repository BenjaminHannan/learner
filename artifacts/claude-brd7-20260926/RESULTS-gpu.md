# brd-7: fresh-panel confirmation GPU result (rental, 2026-09-26)

Registered rule: artifacts/claude-brd7-20260926/PASSMARKS-brd7.md (origin/main).
Code: scripts/claude_brd5.py + scripts/claude_blurt1.py + scripts/claude_blurt2.py + scripts/claude_blurt4.py + scripts/claude_blurt5s.py + scripts/claude_cre333b_agent.py from origin/main, UNMODIFIED, run only.
Command: `python -B scripts/claude_brd5.py --model BASE --out gpu --temps 1.0,1.5 --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl --test-puzzles artifacts/claude-brd7-20260926/test_puzzles.jsonl --train-seed 9`
BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc, commit 87179e5c1f455ef22e6223592d2d61351b525bfc (expected hash, plain MiniCPM5-1B, no other model downloaded).
Selftest: `python -B scripts/claude_brd5.py --selftest` printed "selftest ok".
Test panel md5: 6977ea8626e47c004a25b1e495743b1d (matched, run proceeded).
GPU: RTX 5090 (vastai offer 44173814, KR, reliability 0.9981, 16 cores, 60 GB disk, image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel, torch 2.8.0+cu128). Run wall: 20.1 min (script-reported; rental 10:57:28Z-11:27:06Z, ~0.494 h x dph $0.49444 = ~$0.24 of $1.00 budget, 1 rental). Instance destroyed, confirmed gone (`vastai show instances` empty).
No weights saved or pushed. No secrets. Fictional names only (none used).

## brd5_summary.json (whole file)

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {
  "1.0": 24,
  "1.5": 50
 },
 "temp_chosen": 1.5,
 "n_train": 400,
 "n_test": 240,
 "temp": 1.5,
 "n_test_3num": 160,
 "base": {
  "cov@1": 12,
  "cov@5": 39,
  "cov@10": 76,
  "cov@30": 135,
  "lucky": 330
 },
 "own": 20,
 "wins": 183,
 "examples": 203,
 "N_distinct_wins": 20,
 "N_distinct_puzzles": 40,
 "W_distinct_puzzles": 203,
 "W_seed0": {
  "cov@1": 18,
  "cov@5": 75,
  "cov@10": 110,
  "cov@30": 158,
  "lucky": 590
 },
 "W_seed1": {
  "cov@1": 20,
  "cov@5": 64,
  "cov@10": 95,
  "cov@30": 158,
  "lucky": 564
 },
 "W_seed2": {
  "cov@1": 21,
  "cov@5": 68,
  "cov@10": 100,
  "cov@30": 146,
  "lucky": 547
 },
 "N_seed0": {
  "cov@1": 26,
  "cov@5": 65,
  "cov@10": 80,
  "cov@30": 99,
  "lucky": 690
 },
 "N_seed1": {
  "cov@1": 26,
  "cov@5": 50,
  "cov@10": 65,
  "cov@30": 89,
  "lucky": 808
 },
 "N_seed2": {
  "cov@1": 23,
  "cov@5": 56,
  "cov@10": 71,
  "cov@30": 96,
  "lucky": 686
 },
 "C_seed0": {
  "cov@1": 21,
  "cov@5": 25,
  "cov@10": 27,
  "cov@30": 28,
  "lucky": 633
 },
 "C_seed1": {
  "cov@1": 20,
  "cov@5": 25,
  "cov@10": 28,
  "cov@30": 33,
  "lucky": 640
 },
 "C_seed2": {
  "cov@1": 20,
  "cov@5": 23,
  "cov@10": 23,
  "cov@30": 27,
  "lucky": 603
 },
 "ci95_W_minus_N_cov30_pct": [
  20.03,
  29.34
 ],
 "ci95_W_minus_base_cov30_pct": [
  2.65,
  13.31
 ],
 "ci95_N_minus_base_cov30_pct": [
  -22.78,
  -10.53
 ],
 "minutes": 20.1
}
```

## Registered marks (PASSMARKS-brd7.md clauses with numbers)

- PASS: W's cov@30 >= base cov@30 + 24 (= 159) in EVERY seed: W = 158, 158, 146 vs base 135 (deltas +23, +23, +11) -- FAILS (none reaches 159). 95% interval for W - base = [2.65, 13.31], above 0 -- holds. W >= C + 24 every seed: C = 28, 33, 27, W - C = 130, 125, 119 -- holds. First clause fails, so NO PASS.
- Proved wrong: upper 95% bound of W - base below +5 points (12 puzzles): upper bound 13.31 > 5 -- NOT proved wrong.
- Inconclusive: 183 won practice puzzles (>= 40) and 20 own greedy-correct answers (>= 10) -- NOT inconclusive.
- Otherwise: NOT SHOWN. Registered verdict: NOT SHOWN.
- Reported, not marks: cov@1 base 12 / W 18,20,21 / N 26,26,23 / C 21,20,20; W - N interval [20.03, 29.34]; N collapses coverage (89-99 vs base 135); C collapses further (27-33).
