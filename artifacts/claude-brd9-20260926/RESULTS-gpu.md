# brd-9 GPU results (registered run, rental rent-brd9, 2026-09-26)

Registered question: do three nights in a row, each practised by the model that slept the night
before, clear problem 7's bar? One GPU run is the registered result.
Code: origin/main scripts/claude_brd9.py, unmodified. Command:

    python -B scripts/claude_brd9.py --model BASE --out gpu --temps 1.0,1.5 \
      --dev-puzzles artifacts/claude-blurt1-dev-20260925/puzzles.jsonl \
      --test-puzzles artifacts/claude-brd9-20260926/test_puzzles.jsonl \
      --transfer-puzzles artifacts/claude-brd9-20260926/transfer_puzzles.jsonl --train-seed 9

BASE = /root/.cache/huggingface/hub/models--openbmb--MiniCPM5-1B/snapshots/87179e5c1f455ef22e6223592d2d61351b525bfc
(model commit hash 87179e5c1f455ef22e6223592d2d61351b525bfc; plain MiniCPM5-1B only, no other model downloaded).
md5(test_puzzles.jsonl) = 9e07a74ebc5914b6f2cd86da219d1188 (matched).
md5(transfer_puzzles.jsonl) = 39ffe6e4d22da7bbd90bb613fece63de (matched).
Selftest: "selftest ok".
GPU: NVIDIA GeForce RTX 5090 (rental 52775111, KR, dph $0.4944). Script wall: 46.7 min.
Rental wall 16:06:30Z-17:17:15Z (~70.7 min incl. setup incl. one torch rebuild; run launched 16:24Z),
~$0.58 + ~$0.05 unreachable first host = ~$0.63 of the $0.90 task budget.
DEV temperature rule picked 1.5 (lucky blurts 52 vs 43 on 58 missed DEV puzzles).

## Whole brd9_summary.json

```json
{
 "dev_missed": 58,
 "dev_lucky_by_temp": {
  "1.0": 43,
  "1.5": 52
 },
 "temp_chosen": 1.5,
 "n_test": 240,
 "temp": 1.5,
 "n_test_3num": 80,
 "transfer_base": {
  "cov@1": 0,
  "cov@5": 6,
  "cov@10": 6,
  "cov@30": 13,
  "lucky": 17
 },
 "base": {
  "cov@1": 10,
  "cov@5": 36,
  "cov@10": 53,
  "cov@30": 96,
  "lucky": 224,
  "cov@30_3num": 56,
  "cov@30_4num": 40
 },
 "base_unreached": 144,
 "bar_pass": 28.8,
 "night1_practice": {
  "own": 20,
  "win": 185,
  "miss": 195
 },
 "N1_seed0": {
  "cov@1": 13,
  "cov@5": 46,
  "cov@10": 65,
  "cov@30": 111,
  "lucky": 410,
  "cov@30_3num": 66,
  "cov@30_4num": 45,
  "examples": 205
 },
 "transfer_N1_seed0": {
  "cov@1": 1,
  "cov@5": 6,
  "cov@10": 15,
  "cov@30": 26,
  "lucky": 54
 },
 "night2_practice_seed0": {
  "own": 25,
  "win": 218,
  "miss": 157
 },
 "N2_seed0": {
  "cov@1": 20,
  "cov@5": 60,
  "cov@10": 89,
  "cov@30": 142,
  "lucky": 516,
  "cov@30_3num": 76,
  "cov@30_4num": 66,
  "examples": 448
 },
 "transfer_N2_seed0": {
  "cov@1": 0,
  "cov@5": 8,
  "cov@10": 19,
  "cov@30": 31,
  "lucky": 66
 },
 "night3_practice_seed0": {
  "own": 61,
  "win": 225,
  "miss": 114
 },
 "N3_seed0": {
  "cov@1": 24,
  "cov@5": 65,
  "cov@10": 94,
  "cov@30": 139,
  "lucky": 588,
  "cov@30_3num": 75,
  "cov@30_4num": 64,
  "examples": 734
 },
 "transfer_N3_seed0": {
  "cov@1": 4,
  "cov@5": 13,
  "cov@10": 24,
  "cov@30": 45,
  "lucky": 91
 },
 "N1_seed1": {
  "cov@1": 7,
  "cov@5": 50,
  "cov@10": 74,
  "cov@30": 114,
  "lucky": 393,
  "cov@30_3num": 71,
  "cov@30_4num": 43,
  "examples": 205
 },
 "transfer_N1_seed1": {
  "cov@1": 1,
  "cov@5": 6,
  "cov@10": 9,
  "cov@30": 21,
  "lucky": 33
 },
 "night2_practice_seed1": {
  "own": 22,
  "win": 238,
  "miss": 140
 },
 "N2_seed1": {
  "cov@1": 17,
  "cov@5": 54,
  "cov@10": 83,
  "cov@30": 124,
  "lucky": 451,
  "cov@30_3num": 74,
  "cov@30_4num": 50,
  "examples": 465
 },
 "transfer_N2_seed1": {
  "cov@1": 3,
  "cov@5": 9,
  "cov@10": 14,
  "cov@30": 28,
  "lucky": 56
 },
 "night3_practice_seed1": {
  "own": 58,
  "win": 214,
  "miss": 128
 },
 "N3_seed1": {
  "cov@1": 21,
  "cov@5": 70,
  "cov@10": 98,
  "cov@30": 135,
  "lucky": 604,
  "cov@30_3num": 72,
  "cov@30_4num": 63,
  "examples": 737
 },
 "transfer_N3_seed1": {
  "cov@1": 1,
  "cov@5": 12,
  "cov@10": 18,
  "cov@30": 32,
  "lucky": 79
 },
 "N1_seed2": {
  "cov@1": 13,
  "cov@5": 43,
  "cov@10": 70,
  "cov@30": 122,
  "lucky": 446,
  "cov@30_3num": 67,
  "cov@30_4num": 55,
  "examples": 205
 },
 "transfer_N1_seed2": {
  "cov@1": 2,
  "cov@5": 8,
  "cov@10": 12,
  "cov@30": 24,
  "lucky": 58
 },
 "night2_practice_seed2": {
  "own": 51,
  "win": 216,
  "miss": 133
 },
 "N2_seed2": {
  "cov@1": 19,
  "cov@5": 51,
  "cov@10": 78,
  "cov@30": 132,
  "lucky": 537,
  "cov@30_3num": 76,
  "cov@30_4num": 56,
  "examples": 472
 },
 "transfer_N2_seed2": {
  "cov@1": 2,
  "cov@5": 9,
  "cov@10": 15,
  "cov@30": 28,
  "lucky": 67
 },
 "night3_practice_seed2": {
  "own": 70,
  "win": 211,
  "miss": 119
 },
 "N3_seed2": {
  "cov@1": 17,
  "cov@5": 58,
  "cov@10": 91,
  "cov@30": 131,
  "lucky": 557,
  "cov@30_3num": 72,
  "cov@30_4num": 59,
  "examples": 753
 },
 "transfer_N3_seed2": {
  "cov@1": 1,
  "cov@5": 10,
  "cov@10": 15,
  "cov@30": 32,
  "lucky": 63
 },
 "ci95_N1_minus_base_cov30_pct": [
  2.5,
  13.74
 ],
 "ci95_N2_minus_base_cov30_pct": [
  9.38,
  21.22
 ],
 "ci95_N3_minus_base_cov30_pct": [
  10.56,
  21.81
 ],
 "ci95_N3_minus_N1_cov30_pct": [
  4.58,
  11.84
 ],
 "transfer_ci95_N1_minus_base_cov30_pct": [
  3.57,
  22.78
 ],
 "transfer_ci95_N2_minus_base_cov30_pct": [
  9.17,
  30.45
 ],
 "transfer_ci95_N3_minus_base_cov30_pct": [
  18.14,
  40.08
 ],
 "minutes": 46.7
}
```

Base cov@30 = 96, so unreached = 144 and the bar = 0.20 x 144 = 28.8 points (12.0% of 240).
Per-seed N3 − base: seed0 +43 (139), seed1 +39 (135), seed2 +35 (131).
Per-seed N3 − N1: seed0 +28, seed1 +21, seed2 +9 (N1 = 111 / 114 / 122).

## PASS — MET

Requires N3's cov@30 ≥ base cov@30 + bar (need ≥ 124.8) in EVERY seed, AND the 95% interval
for N3 − base above 0.
Seed checks: 139 (+43 ✓), 135 (+39 ✓), 131 (+35 ✓).
Interval: [+10.56, +21.81] — above 0 ✓. Both conditions hold.

## G7 (problem 7's old bar, its own line) — MET

Requires N3's cov@30 ≥ base cov@30 + 24 (need ≥ 120) in EVERY seed, AND the 95% interval
for N3 − base above 0.
Seeds: 139 (+43 ✓), 135 (+39 ✓), 131 (+35 ✓). Interval: [+10.56, +21.81] — above 0 ✓.

## NIGHTS (its own line) — NOT MET

Requires N3's cov@30 ≥ N1's cov@30 + 12 in EVERY seed (seed k vs seed k), AND the 95% interval
for N3 − N1 above 0.
Seed checks (need ≥123 / ≥126 / ≥134): 139 (+28 ✓), 135 (+21 ✓), 131 (+9 ✗, miss by 3).
Interval: [+4.58, +11.84] — above 0 ✓, but the per-seed condition fails on seed 2.

## Proved-wrong — NO

Requires the upper 95% bound of N3 − base (in points of the 240) below 100 × bar / 240 = 12.0%.
Upper bound +21.81% = +52.3 puzzles of 240 — not below 28.8.

## Inconclusive — NO (question was posed)

Would trigger on fewer than 40 night-1 wins (blurt hits, not greedy answers): got 185.

## Verdict

PASS MET on this panel: three nights as the loop would really run cleared the unreached-fraction
bar (+43 / +39 / +35 vs bar 28.8, interval above 0). G7 met as its own line. NIGHTS not met
(seed 2 gained only +9 over N1, 3 short of +12). Not proved wrong; not inconclusive.
Split gains as a share of each part's own unreached puzzles: 3-number room was 24
(base 56/80), N3 gained +19 / +16 / +16 (79% / 67% / 67%); 4-number room was 120
(base 40/160), N3 gained +24 / +23 / +19 (20% / 19% / 16%).

## Transfer row (report only, Addendum T)

Transfer set: 80 puzzles, 4 numbers 1-13, target 10-40 other than 24. Base cov@30 = 13.
N3 cov@30: 45 / 32 / 32 (gains +32 / +19 / +19).
N3 − base interval: [+18.14, +40.08] — above 0. Read as "transfer seen".
(N1 − base [+3.57, +22.78] and N2 − base [+9.17, +30.45] also above 0.)

Files: artifacts/claude-brd9-20260926/gpu/{brd9_summary.json,streams.json,transfer_streams.json,practice.json,log.txt}.
No weights saved or pushed. Code unedited.
