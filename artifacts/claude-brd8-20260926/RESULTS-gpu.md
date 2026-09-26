# brd-8 GPU results (registered run, rental rent-brd8, 2026-09-26)

Registered question: does a second practice round help more when the SLEPT model (M1) collects the round-2 hits
(ITER) than when the base model collects them (CTRL), at equal exposure? One GPU run is the registered result.
Code: origin/main scripts/claude_brd8.py, unmodified. Command:

    python -B scripts/claude_brd8.py --model BASE --out gpu --temps 1.0,1.5 \
      --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl \
      --test-puzzles artifacts/claude-brd8-20260926/test_puzzles.jsonl --train-seed 9

BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
(model commit hash 87179e5c1f455ef22e6223592d2d61351b525bfc; plain MiniCPM5-1B only, no other model downloaded).
md5(test_puzzles.jsonl) = beb76d9492f990641754dc8bb509c2a0 (matched). Selftest: "selftest ok".
GPU: NVIDIA GeForce RTX 5090 (rental 52761669, KR, dph $0.4944). Script wall: 31.2 min.
Rental wall 14:29:47Z-15:13:05Z (~43 min, setup + run + copy-back), ~$0.36 of the $1.00 task budget.

## Whole brd8_summary.json

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {
  "1.0": 47,
  "1.5": 42
 },
 "temp_chosen": 1.0,
 "n_test": 240,
 "temp": 1.0,
 "n_test_3num": 160,
 "base": {
  "cov@1": 5,
  "cov@5": 31,
  "cov@10": 58,
  "cov@30": 108,
  "lucky": 318
 },
 "round1": {
  "own": 20,
  "win": 165,
  "miss": 215
 },
 "round2_ctrl": {
  "own": 13,
  "win": 171,
  "miss": 216
 },
 "passes_each": 1107,
 "round2_iter_seed0": {
  "own": 46,
  "win": 200,
  "miss": 154
 },
 "ITER_seed0": {
  "cov@1": 21,
  "cov@5": 77,
  "cov@10": 105,
  "cov@30": 143,
  "lucky": 697,
  "examples": 431
 },
 "CTRL_seed0": {
  "cov@1": 16,
  "cov@5": 75,
  "cov@10": 104,
  "cov@30": 152,
  "lucky": 599,
  "examples": 369
 },
 "round2_iter_seed1": {
  "own": 41,
  "win": 215,
  "miss": 144
 },
 "ITER_seed1": {
  "cov@1": 24,
  "cov@5": 85,
  "cov@10": 117,
  "cov@30": 161,
  "lucky": 762,
  "examples": 441
 },
 "CTRL_seed1": {
  "cov@1": 27,
  "cov@5": 72,
  "cov@10": 104,
  "cov@30": 152,
  "lucky": 642,
  "examples": 369
 },
 "round2_iter_seed2": {
  "own": 53,
  "win": 185,
  "miss": 162
 },
 "ITER_seed2": {
  "cov@1": 22,
  "cov@5": 81,
  "cov@10": 124,
  "cov@30": 166,
  "lucky": 739,
  "examples": 423
 },
 "CTRL_seed2": {
  "cov@1": 26,
  "cov@5": 89,
  "cov@10": 127,
  "cov@30": 167,
  "lucky": 737,
  "examples": 369
 },
 "ci95_ITER_minus_CTRL_cov30_pct": [
  -3.96,
  3.33
 ],
 "ci95_ITER_minus_base_cov30_pct": [
  14.66,
  25.65
 ],
 "ci95_CTRL_minus_base_cov30_pct": [
  15.24,
  25.46
 ],
 "minutes": 31.2
}
```

Seed table, cov@30 of 240 (base 108): ITER 143 / 161 / 166; CTRL 152 / 152 / 167.
Per-seed ITER − CTRL: seed0 −9, seed1 +9, seed2 −1. Per-seed ITER − base: +35 / +53 / +58.

## PASS (compounding) — NOT MET

Requires ITER cov@30 ≥ CTRL cov@30 + 12 in EVERY seed, AND the 95% interval for ITER − CTRL above 0.
Seed checks (need ≥164 / ≥164 / ≥179): 143 (miss by 21), 161 (miss by 3), 166 (miss by 13).
Interval: [−3.96, +3.33] — not above 0. Both conditions fail.

## G7 (problem 7's bar, separate line) — MET

Requires ITER cov@30 ≥ base cov@30 + 24 in EVERY seed (need ≥132), AND the 95% interval for ITER − base above 0.
Seeds: 143 (+35 ✓), 161 (+53 ✓), 166 (+58 ✓). Interval: [+14.66, +25.65] — above 0 ✓.

## Proved-wrong (compounding) — NO

Requires the upper 95% bound of ITER − CTRL below +2.5 points (6 puzzles).
Upper bound +3.33% = +8.0 puzzles of 240 — not below 6.

## Inconclusive — NO (question was posed)

Would trigger on fewer than 40 round-1 wins (got 165), or M1 winning fewer B puzzles than the base model in
every seed. ITER round-2 wins per seed: 200 / 215 / 185 vs CTRL 171 — ITER won MORE in every seed.

## Verdict

NOT SHOWN for compounding (PASS missed, not proved wrong); G7 met as its own line.
The slept model practised better (more round-2 wins every seed, on the same B set) but that did not compound
into higher coverage than the base-collected arm at equal exposure.
Files: artifacts/claude-brd8-20260926/gpu/{brd8_summary.json,streams.json,practice.json,log.txt}.
No weights saved or pushed. Code unedited.
