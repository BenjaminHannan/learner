# dl-4 KL-anchor week: GPU result (rental, 2026-09-26)

Registered rule: artifacts/claude-dl4-20260926/PASSMARKS.md (origin/main).
Code: scripts/claude_dl4_anchor.py + scripts/claude_dl1_nights.py + scripts/claude_blurt1.py + scripts/claude_blurt2.py + scripts/claude_dl3_replay.py from origin/main (archived via `git archive origin/main`, unmodified, never edited; byte-identical before and after a main move mid-run).
Command: `python -B scripts/claude_dl4_anchor.py --model BASE --out gpu`
BASE = local MiniCPM5-1B snapshot on the rental (openbmb/MiniCPM5-1B, pinned revision 87179e5c1f455ef22e6223592d2d61351b525bfc, same files as dl-2/dl-3, thinking off).
Python: rental image pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime (torch 2.8.0+cu128, CUDA True, transformers 5.17.0 pip-installed on the rental; the runtime image ships torch but no transformers).
Selftest: `python -B scripts/claude_dl4_anchor.py --selftest` printed "selftest ok" before the run.

## marks block (whole block from gpu/dl4_results.json)

```json
{
 "L0": 59,
 "reached0": 37,
 "K_final_lost": [
  6,
  19
 ],
 "S_final_lost": [
  16,
  17
 ],
 "K_final_lucky": [
  208,
  298
 ],
 "S_final_lucky": [
  184,
  353
 ],
 "K_nights_lost_over_15": 4,
 "K_worse_nights": 0,
 "K_final_reached": [
  64,
  59
 ],
 "report_K_nights_lost_over_5": 10,
 "F1 forgetting cut: K final lost <= 0.5 x S final lost (sums), and each K seed < each S seed": false,
 "F2 low forgetting every night: K nights with lost > 10 (5% of base-right) <= 1 of 14": false,
 "F3 still learns: K final lucky >= 2 x L0 on each seed, and K gain over L0 >= 0.8 x S gain (sums)": true,
 "F4 nights rarely hurt the day's work: K nights with TEST lucky > 15% below the night before <= 1 of 14": true,
 "F5 variety kept: K final reached >= base on each seed": true,
 "verdict": "FAIL",
 "proved_wrong": false
}
```

- Base TEST (100 fresh puzzles, TEST seed 3690, 20 guesses each): lucky 59, reached 37, greedy 4. HARM right 200/300. Anchor pool 880 items (pool seed 3691).
- Final TEST lucky: K seeds 208, 298 (mean 253.0); S seeds 184, 353 (mean 268.5). L0 59.
- Final TEST reached: K 64, 59; S 52, 61; base 37.
- Final greedy solves: K 18, 12; S 11, 20; base 4.
- Final lost (right at base, wrong now): K 6, 19 (sum 25); S 16, 17 (sum 33).
- Not INCONCLUSIVE: L0 59 >= 10; S night-7 lost sum 33 >= 20; pool 880 >= 100.

- F1 forgetting cut: K sum 25 <= 0.5 x S sum 33 = 16.5? No (25 > 16.5). Per-seed each K < each S: max(K) 19 < min(S) 16? No (s6 6 < 16 yes, 6 < 17 yes; s7 19 < 16 no, 19 < 17 no). **F1 FAIL.**
- F2 low forgetting every night: 4 of K's 14 nights have lost > 10 (K s6: 4, 5, 7, 9, 3, 8, 6, none over 10; K s7: 4, 9, 8, 12, 19, 16, 19, four over 10 on nights 4-7). 4 > 1. **F2 FAIL.**
- F3 still learns: K final 208 >= 2 x 59 = 118 and 298 >= 118 yes. Gains over L0: K sum 506 - 118 = 388; S sum 537 - 118 = 419; 388 >= 0.8 x 419 = 335.2 yes. **F3 PASS.**
- F4 nights rarely hurt the day's work: 0 of 14 K nights worse than 15% below the night before (K s6 lucky 83, 156, 154, 138, 210, 236, 208, largest dip 236 -> 208 = -11.9%; K s7 83, 161, 182, 226, 252, 294, 298, no dips). 0 <= 1. **F4 PASS.**
- F5 variety kept: K final reached 64 >= 37 and 59 >= 37. **F5 PASS.**

- Verdict: **FAIL** (F1 and F2 fail; F3, F4, F5 pass).
- Proved wrong (K night-7 lost >= S on both seeds): s6 6 >= 16? No. **Not proved wrong.**

Lost per night:
- S s6: 7, 10, 10, 13, 15, 16, 16
- S s7: 10, 4, 4, 7, 12, 11, 17
- K s6: 4, 5, 7, 9, 3, 8, 6
- K s7: 4, 9, 8, 12, 19, 16, 19

Reported, not marked:
- KL to base on general replies, night 7: K 0.035 (s6), 0.031 (s7); S 0.175 (s6), 0.186 (s7). The anchor held drift near base level all week (K KL never above 0.035; S rose to 0.14-0.19).
- Anchor KL in training (last batch per night): 0.004-0.010.
- Gained (wrong at base, right now), night 7: K 54 (s6), 26 (s7); S 45 (s6), 46 (s7).

## Run facts
- GPU: NVIDIA GeForce RTX 5090. Run-internal wall 84.7 minutes.
- Dollars: ~$0.99 of the $1.20 task budget (3 rentals of max 3; $1.10 kill line never reached).
  Rentals: 52756261 (offer 46753293 US, 5090, dph 0.4963, host could not pull the docker image: registry proxy refused, destroyed without running, ~0.18h ~$0.09) + 52757337 (offer 43165150 US, 5090, dph 0.4963, same host, same image-pull failure, destroyed without running, ~0.16h ~$0.08) + 52758310 (offer 48989650 KR, 5090, dph 0.5037, ran 14:06Z-15:44Z, destroyed after copy-back, 1.634h $0.823). Post-destroy 0 claude-fixsleep-dl4b live (confirmed).
- Credit at gate: 5.487064616269862 (>= 1.50, proceeded).
- Origin/main commit at report: ba72f9b5a4d834eae708114a130b2690b824bc7e. Sealed files archived at run start are byte-identical to this commit.
- Copy-back: gpu/dl4_results.json, gpu/anchor_pool.json, gpu/log.txt (force-added; artifacts/ is git-ignored). No weights (the run saves none). No code edits. No TEST-ONLY panel involved.
