# dl-7b shaky-fact KL anchor: GPU result (rental, 2026-09-26)

Registered rule: artifacts/claude-dl7-20260926/PASSMARKS.md (origin/main, with Addendum 2: dl-7 never runs, dl-7b replaces it).
Code: scripts/claude_dl7b_glmsuffix.py (imports scripts/claude_dl7_fragile.py unchanged; GLM suffix) + scripts/claude_dl1_nights.py + scripts/claude_blurt1.py + scripts/claude_blurt2.py + scripts/claude_dl3_replay.py + scripts/claude_dl4_anchor.py, all from origin/main via `git archive origin/main`, unmodified, never edited.
Command: `python -B scripts/claude_dl7b_glmsuffix.py --model BASE --out gpu`
BASE = local MiniCPM5-1B snapshot on the rental (openbmb/MiniCPM5-1B, pinned revision 87179e5c1f455ef22e6223592d2d61351b525bfc, same files as dl-2, thinking off).
Suffix: " Answer only, no explanation." (gpu/suffix.json, sha256 3c1fe9c1...14bc pinned).
Python: rental image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime (torch 2.8.0+cu128, CUDA True, transformers 5.17.0 pip-installed; image ships torch but no transformers).
Selftest: `python -B scripts/claude_dl7b_glmsuffix.py --selftest` printed "selftest ok" / "dl7b selftest ok" before the run.

## marks block (whole block from gpu/dl7_results.json)

```json
{
 "L0": 66,
 "reached0": 35,
 "F_final_lost": [
  3,
  4
 ],
 "S_final_lost": [
  11,
  15
 ],
 "F_final_lucky": [
  179,
  216
 ],
 "S_final_lucky": [
  273,
  204
 ],
 "F_nights_lost_over_15": 0,
 "F_worse_nights": 0,
 "F_final_reached": [
  52,
  53
 ],
 "report_F_nights_lost_over_5": 3,
 "F1 forgetting cut: F final lost <= 0.5 x S final lost (sums), and each F seed < each S seed": true,
 "F2 low forgetting every night: F nights with lost > 10 (5% of base-right) <= 1 of 14": true,
 "F3 still learns: F final lucky >= 2 x L0 on each seed, and F gain over L0 >= 0.8 x S gain (sums)": false,
 "F4 nights rarely hurt the day's work: F nights with TEST lucky > 15% below the night before <= 1 of 14": true,
 "F5 variety kept: F final reached >= base on each seed": true,
 "verdict": "FAIL",
 "proved_wrong": false
}
```

- Base TEST (100 fresh puzzles, TEST seed 3290, 20 guesses each): lucky 66, reached 35, greedy 2. HARM right 200/300. Shaky pool 427 items (pool seed 3291: asked 3000, kept questions 1479, answered 1282, conf cut 0.1979).
- Final TEST lucky: F seeds 179, 216 (mean 197.5); S seeds 273, 204 (mean 238.5). L0 66.
- Final TEST reached: F 52, 53; S 58, 60; base 35.
- Final lost (right at base, wrong now): F 3, 4 (sum 7); S 11, 15 (sum 26).
- Not INCONCLUSIVE: L0 66 >= 10; S night-7 lost sum 26 >= 20; pool 427 >= 100.

- F1 forgetting cut: F sum 7 <= 0.5 x S sum 26 = 13.0? Yes (7 <= 13). Per-seed each F < each S: max(F) 4 < min(S) 11? Yes (3 < 11, 3 < 15, 4 < 11, 4 < 15). **F1 PASS.**
- F2 low forgetting every night: 0 of F's 14 nights have lost > 10 (F s12: 0, 7, 4, 5, 8, 8, 3; F s13: 2, 0, 0, 0, 4, 3, 4). 0 <= 1. **F2 PASS.**
- F3 still learns: F final 179 >= 2 x 66 = 132 and 216 >= 132 yes. Gains over L0: F sum 395 - 132 = 263; S sum 477 - 132 = 345; 263 >= 0.8 x 345 = 276.0? No (263 < 276, short by 13). **F3 FAIL.**
- F4 nights rarely hurt the day's work: 0 of 14 F nights worse than 15% below the night before (largest F dip: s12 night 6 -> 7, 200 -> 179 = -10.5%). 0 <= 1. **F4 PASS.**
- F5 variety kept: F final reached 52 >= 35 and 53 >= 35. **F5 PASS.**

- Verdict: **FAIL** (F3 fails; F1, F2, F4, F5 pass).
- Proved wrong (F night-7 lost >= S on both seeds): s12 3 >= 11? No. **Not proved wrong.**

Lost per night:
- S s12: 4, 3, 6, 12, 8, 11, 11
- S s13: 8, 8, 12, 11, 9, 11, 15
- F s12: 0, 7, 4, 5, 8, 8, 3
- F s13: 2, 0, 0, 0, 4, 3, 4

TEST lucky per night:
- S s12: 122, 142, 146, 200, 235, 329, 273
- S s13: 95, 140, 138, 201, 177, 212, 204
- F s12: 101, 110, 145, 184, 207, 200, 179
- F s13: 82, 103, 172, 211, 205, 217, 216

Reported, not marked:
- KL to base on general replies, night 7: F 0.0175 (s12), 0.0128 (s13); S 0.1529 (s12), 0.1764 (s13). The anchor held drift near base level all week (F KL never above 0.0175; S rose to 0.15-0.18), same pattern as dl-4.
- Anchor KL in training (last batch per night): 0.008-0.035.
- Gained (wrong at base, right now), night 7: F 14 (s12), 20 (s13); S 47 (s12), 50 (s13).
- Premise check (Addendum 1, report-only, fixed rule): S night-7 lost items pooled over both seeds, 22 of 26 in the lowest third of base-right panel items by base_panel_conf = 84.6% (union: 16 of 19 = 84.2%). 60% or more = premise supported. **Premise SUPPORTED on fresh seeds** (lost items are the base's shakiest facts, far above the 60% bar).

## Run facts
- GPU: NVIDIA GeForce RTX 5090 (rental, South Korea).
- Wall: 72.4 minutes run-internal (18:48Z-20:01Z; rental span ~1.45 h incl. setup).
- Dollars: ~$0.60 of the $1.00 task budget (1 rental of max 3; contract 52799251, offer 38694854, dph $0.4167, ~1.45 h; $0.95 kill line never reached).
- Credit at gate: 4.09 (balance 0; >= 1.50, proceeded).
- Code commit hash (origin/main): f35b1b09f4af4996741658b4d36fd45eec92e3da. Model commit hash (HF snapshot revision): 87179e5c1f455ef22e6223592d2d61351b525bfc.
- Copy-back: gpu/dl7_results.json, gpu/fragile_pool.json, gpu/suffix.json, gpu/log.txt (force-added; artifacts/ is git-ignored). No weights (the run saves none). No code edits. No TEST-ONLY panel involved (test puzzles made inside the run, never printed).
- Instance destroyed, 0 claude-fixsleep-dl7b live (confirmed).
