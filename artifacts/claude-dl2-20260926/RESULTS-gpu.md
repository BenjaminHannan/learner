# dl-2 copy-practice week: GPU result (rental, 2026-09-26)

Registered rule: artifacts/claude-dl2-20260926/PASSMARKS.md (origin/main).
Code: scripts/claude_dl2_nights.py + scripts/claude_dl1_nights.py + scripts/claude_blurt1.py + scripts/claude_blurt2.py from origin/main (unmodified, never edited).
Command: `python -B scripts/claude_dl2_nights.py --model BASE --out gpu`
BASE = openbmb/MiniCPM5-1B snapshot at commit 87179e5c1f455ef22e6223592d2d61351b525bfc (pinned HF revision, same files as blurt-4/5s, thinking off).
Python: rental image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime (torch 2.8.0+cu128, CUDA True, transformers 5.17.0).

## marks block (whole block from gpu/dl2_results.json)

```json
{
 "L0": 64,
 "reached0": 34,
 "S_final_lucky": [
  237,
  249
 ],
 "P_final_lucky": [
  42,
  51
 ],
 "S_worse_nights": 0,
 "S_nights_net_harm_over_5": 0,
 "S_final_net_harm": [
  -10,
  -8
 ],
 "S_final_reached": [
  62,
  60
 ],
 "W1 better after a week: S final lucky >= 2 x L0 on each seed": true,
 "W2 nights rarely hurt the day's work: S nights with TEST lucky > 15% below the night before <= 1 of 14": true,
 "W3 nights rarely hurt anything else: S nights with net harm > 5 on the panel <= 1 of 14, and final net harm <= 0 on each seed": true,
 "W4 variety kept: S final reached >= base on each seed": true,
 "W5 right answers caused it: S >= 1.3 x P (means) and each S seed > each P seed": true,
 "verdict": "PASS",
 "proved_wrong": false
}
```

- Base TEST (100 fresh puzzles, 20 guesses each): lucky 64, reached 34, greedy 3. HARM right 200/300.
- Final TEST lucky: S seeds 237, 249 (mean 243.0); P seeds 42, 51 (mean 46.5). L0 64.
- Final TEST reached: S 62, 60; P 28, 32; base 34.
- Final greedy solves: S 17, 18; P 1, 4; base 3.
- Final net harm (lost minus gained vs base): S -10, -8 (mean -9.0); P -24, -20.
- Not INCONCLUSIVE: L0 64 >= 10.

- W1 better after a week: S final 237 >= 2 x 64 = 128 and 249 >= 128. **W1 PASS.**
- W2 nights rarely hurt the day's work: 0 of 14 S nights fell more than 15% below the night before (worst night-to-night move: S s3 night 4 -> 5, 235 -> 209, -11%). **W2 PASS.**
- W3 nights rarely hurt anything else: 0 of 14 S nights had net harm > 5 (max 5, S s3 night 6), and final net harm -10, -8 <= 0 on each seed. **W3 PASS.**
- W4 variety kept: S final reached 62 and 60 >= base 34. **W4 PASS.**
- W5 the right answers caused it: S mean 243.0 >= 1.3 x P mean 46.5 = 60.5, and each S seed (237, 249) > each P seed (42, 51). **W5 PASS.**

Registered verdict: **PASS** (W1-W5 all pass).
Proved-wrong clause: S final lucky <= 1.1 x L0 = 70.4 on either seed is false (237, 249); >= 3 worse S nights is false (0); S mean 243.0 <= P mean 46.5 is false. **Not proved wrong.**

Reported, not marked: per-night TEST lucky (S s2: 102, 123, 156, 227, 223, 230, 237; S s3: 101, 155, 179, 235, 209, 210, 249; P s2: 78, 68, 59, 56, 64, 83, 42; P s3: 53, 38, 34, 40, 29, 43, 51), per-night reached/greedy/harm/KL in gpu/dl2_results.json; gains did not flatten after night 3 on S (both seeds kept climbing to nights 4-7: s2 156 -> 237, s3 179 -> 249, with one -11% dip on s3 night 5).

## Run facts

- GPU: NVIDIA GeForce RTX 5090 (rental, South Korea).
- Wall: 67.1 minutes (run; rental span ~80 min incl. setup).
- Dollars: ~$0.65 (contract 52669927, dph $0.4852, ~00:26Z-01:46Z ~1.33 h; 1 rental; task total ~$0.65 of $2.00 budget).
- Code commit hash (origin/main): 589946c92c4400e937437fc7a731f4b345a172dc.
- Model commit hash (HF snapshot revision): 87179e5c1f455ef22e6223592d2d61351b525bfc.
- No weights pushed (the run saves none; adapters lived only in GPU memory).
- Files: artifacts/claude-dl2-20260926/gpu/dl2_results.json, gpu/log.txt.
- Test puzzles were made inside the run and never printed.
