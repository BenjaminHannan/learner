# bm-390 VERIFY addendum: the finishing run (rent-bm390f) and the full score (benchmarks thread, 2026-09-25)

New file; VERIFY-bm390.md is sealed and unchanged. The finishing run (AMEND-finish.md) ran on a rented RTX 5090,
17:43-20:01 UTC, $1.13 of its $3.00 cap (RESULTS-rent2.md). The verdict of bm-390 does not change: 0.1 is a
registered FAIL, now against every arm.

## Checks
- Seals: SEAL-code 8 of 8 OK, SEAL-finish 4 of 4 OK (RESULTS-rent2.md section 1).
- Data: the sealed fetch printed locomo_qa 1986 and the registered Linux sample hashes (e294f5fc..., df57d09b...).
  The scoring data here (scratchpad data390) has the same two hashes.
- MODE = registered: the long-prompt check on BASE used 3.95 GiB at 31,114 tokens, so no wrapper was needed. Q2
  peaked at 8.0 GiB and L12 at 4.57 GiB; both are under the 12 GiB limit, so both ran.
- 14 of 14 commands exited 0. Every LoCoMo arm has 1,986 rows (Q2's five parts: 304 + 453 + 400 + 429 + 400).
  Every general arm has 300. The run2 sha256 values match those in RESULTS-rent2.md.
- Scored with scripts/claude_bm390_score.py (sealed) over run/ (BensPC: P, P_bare, Rb, P's generals) plus run2/:
  `--primary P --baselines T,Rb,Q2,L12 --report C,P_bare`.
- Blind recount (recount4/, a separate agent that wrote its own scorer from the LoCoMo repo's evaluation.py and
  never saw scripts/claude_bm390_score.py or its output). It agrees on every LoCoMo headline and category: T 27.50,
  C 3.27, L12 19.01, Q2 47.87. Its per-item F1 matched the repo's own functions on all 7,944 items. MMLU agrees
  exactly: T 50, Q2 201, L12 159, and 234 of T's replies have no pickable letter. Paired intervals: Q2 - T +20.37
  [18.43, 22.32], L12 - T -8.49 [-10.03, -6.91].
  GSM8K agrees under the sealed scorer's rule: T 191, Q2 209, L12 217. The prompt I gave the recount agent
  described the rule loosely. Read strictly ("the answer is" present but no number after it = wrong), the counts are
  T 190 and L12 165. The sealed rule instead falls back to the reply's last number. That matters for 73 L12 replies:
  each writes a format placeholder after "The answer is", and the last number before it equals the gold in 52 of
  them. The registered number stays 217; a strict reading would put L12 at 165 (55.0%).

## Scores (LoCoMo after this run is practice; categories 1-4 F1 on 1,540 questions)
| Arm | LoCoMo 1-4 F1 | cat 1 / 2 / 3 / 4 | MMLU-Redux-300 | GSM8K-300 |
|---|---|---|---|---|
| P, Premonition 0.1 | 2.98 | 3.05 / 1.73 / 5.31 / 3.17 | 85 (28.3%) | 29 (9.7%) |
| T, plain MiniCPM5-1B, whole chat | 27.50 | 24.37 / 19.46 / 16.07 / 32.92 | 50 (16.7%) | 191 (63.7%) |
| Rb, plain MiniCPM5-1B, BM25 top 10 | 25.06 | 13.63 / 26.93 / 12.06 / 29.65 | - | - |
| Q2, Qwen3.5-2B, whole chat | 47.87 | 36.29 / 34.37 / 14.72 / 60.69 | 201 (67.0%) | 209 (69.7%) |
| L12, LFM2.5-1.2B, whole chat | 19.01 | 19.46 / 22.91 / 15.24 / 17.80 | 159 (53.0%) | 217 (72.3%) |
| C, plain 1B, no chat (contamination check) | 3.27 | 3.65 / 0.65 / 9.71 / 3.40 | - | - |

## Marks
- M1 (P at least 3 above each baseline, interval above 0): FAIL against all four. P - T -24.52 [-26.00, -23.08];
  P - Rb -22.07 [-23.61, -20.54]; P - Q2 -44.89 [-46.87, -42.95]; P - L12 -16.03 [-17.20, -14.88].
- M3 (fewer confident wrong answers than each baseline): FAIL. P has 450; T 467, Rb 615 and L12 660 are higher,
  but Q2 has 402, fewer than P.
- M4 (P within 3 points of T on both general tests): FAIL on GSM8K, 9.67 vs 63.67. MMLU "passes" (28.33 vs 16.67),
  but only because T rarely gives a letter: 234 of T's 300 replies have no answer letter the registered rule can
  pick, against 0 for Q2, 2 for L12 and 134 for P. So T's MMLU number mostly measures answer format, not knowledge.
  This is reported, not re-scored; the registered rule stays.

## Predictions
- F1 right: T 27.50 is in 15-35, Rb is within 5 points of T (2.44), C 3.27 is at most 8, and Q2 and L12 are both
  above P.
- F2 right: M4 fails on GSM8K.
- F3 right: the registered code path fit on the 5090.
- Earlier ones (VERIFY-bm390.md) now scored in full: P390.1 half right (M1 fails, but P's 2.98 is under the
  predicted 3-15); P390.2 right (M3 passes against T and Rb; it was not predicted for Q2 and L12); P390.3 (coin
  flip) came out FAIL; P390.4 right; P390.5 right; P390.6 wrong (as already reported).

## What it means
- The bar for "better than models its size" on LoCoMo is Qwen3.5-2B at 47.87. It has about twice the weights of
  MiniCPM5-1B and reads the whole chat in one prompt. LFM2.5-1.2B, at 19.01, is below even the plain 1B (27.50).
- The plain 1B reading the whole chat (27.50) beats the same model shown BM25's top 10 lines (25.06). Any memory
  arm has to beat reading everything, not just beat search.
- The cheapest honest general-test fix for any build on MiniCPM5-1B is answer format: its MMLU replies rarely name
  a letter. This is a note for a later registered change, not a re-score.
- The rivals' numbers are the fixed bar for later builds on this harness (0.2 in bm-391).
