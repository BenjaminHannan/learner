# dl-3 replay-into-the-night: GPU result (rental, 2026-09-26)

Registered rule: artifacts/claude-dl3-20260926/PASSMARKS.md (origin/main).
Code: scripts/claude_dl3_replay.py + scripts/claude_dl1_nights.py + scripts/claude_blurt1.py + scripts/claude_blurt2.py from origin/main (unmodified, never edited).
Command: `python -B scripts/claude_dl3_replay.py --model BASE --out gpu`
BASE = local MiniCPM5-1B snapshot on the rental (openbmb/MiniCPM5-1B, pinned revision 87179e5c1f455ef22e6223592d2d61351b525bfc, same files as dl-2, thinking off).
Python: rental image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-devel (torch 2.8.0+cu128, CUDA True, transformers 5.17.0).

## marks block (whole block from gpu/dl3_results.json)

```json
{
 "L0": 59,
 "reached0": 30,
 "A_final_lost": [
  20,
  36
 ],
 "S_final_lost": [
  39,
  24
 ],
 "A_final_lucky": [
  227,
  216
 ],
 "S_final_lucky": [
  171,
  257
 ],
 "A_nights_lost_over_15": 11,
 "A_worse_nights": 1,
 "A_final_reached": [
  53,
  59
 ],
 "report_A_nights_lost_over_5": 14,
 "F1 forgetting cut: A final lost <= 0.5 x S final lost (sums), and each A seed < each S seed": false,
 "F2 low forgetting every night: A nights with lost > 10 (5% of base-right) <= 1 of 14": false,
 "F3 still learns: A final lucky >= 2 x L0 on each seed, and A gain over L0 >= 0.8 x S gain (sums)": true,
 "F4 nights rarely hurt the day's work: A nights with TEST lucky > 15% below the night before <= 1 of 14": true,
 "F5 variety kept: A final reached >= base on each seed": true,
 "verdict": "FAIL",
 "proved_wrong": false
}
```

- Base TEST (100 fresh puzzles, 20 guesses each): lucky 59, reached 30, greedy 5. HARM right 200/300.
- Final TEST lucky: A seeds 227, 216 (mean 221.5); S seeds 171, 257 (mean 214.0). L0 59.
- Final TEST reached: A 53, 59; S 60, 55; base 30.
- Final greedy solves: A 9, 15; S 10, 16; base 5.
- Final lost (right at base, wrong now): A 20, 36 (sum 56); S 39, 24 (sum 63).
- Not INCONCLUSIVE: L0 59 >= 10; S night-7 lost sum 63 >= 20; replay pool 908 pairs >= 100.

- F1 forgetting cut: A sum 56 <= 0.5 x S sum 63 = 31.5? No (56 > 31.5). Per-seed: s4 20 < 39 yes, s5 36 < 24 no; max(A) 36 < min(S) 24 no. **F1 FAIL.**
- F2 low forgetting every night: 11 of A's 14 nights have lost > 10 (A s4: 10, 15, 22, 16, 18, 17, 20; A s5: 7, 10, 13, 16, 32, 41, 36). Only A s4 night 1 (10) and A s5 nights 1-2 (7, 10) stay at or under 10. 11 > 1. **F2 FAIL.**
- F3 still learns: A final 227 >= 2 x 59 = 118 and 216 >= 118 yes. Gains over L0: A sum 443 - 118 = 325; S sum 428 - 118 = 310; 325 >= 0.8 x 310 = 248 yes. **F3 PASS.**
- F4 nights rarely hurt the day's work: 1 of 14 A nights worse than 15% below the night before (A s5 night 7: 266 -> 216, -19%; A s4 has 0). 1 <= 1. **F4 PASS.**
- F5 variety kept: A final reached 53 >= 30 and 59 >= 30. **F5 PASS.**

- Registered verdict: **FAIL** (F1 and F2 false).
- Proved-wrong clause (A's night-7 lost >= S's on both seeds): s4 20 >= 39 no. **NOT triggered.**

Reported, not marked:
- gained per night: S s4: 28, 48, 36, 39, 34, 32, 36; S s5: 43, 27, 45, 42, 53, 47, 42; A s4: 19, 21, 14, 16, 18, 19, 19; A s5: 22, 29, 24, 39, 38, 31, 33.
- A nights with lost > 5 (2.5% line): 14 of 14 (minimum A lost is 7).
- Replay pool: 908 pairs (1,500 asks at T 1.0, deduplicated, panel topics dropped, base greedy answers). Sample: "What is the historical figure known for being a polymath and a pivotal figure in the development of science?" (9 more samples in gpu/replay_pool.json).
- Lost by panel kind: not broken out here; per-night per-item panels are in gpu/dl3_results.json (harm_items every night).
- KL(current || base) night 7: A 0.28, 0.28; S 0.17, 0.13.

## Run facts
RTX 5090 rental (offer 44173877, KR), 81.2 min run wall (03:35-04:56 UTC), about $0.86 of the $1.50 budget (2 rentals of max 3; first host 46753297 failed with a docker registry proxy error while stopped, destroyed, ~$0). Code from origin/main ca08ccc1 (verified byte-identical for all dl-3 inputs at 43457707), model MiniCPM5-1B @ 87179e5c, unmodified, selftest ok before the run. No weights saved. No TEST-ONLY panel involved (test puzzles made inside the run, never printed).
