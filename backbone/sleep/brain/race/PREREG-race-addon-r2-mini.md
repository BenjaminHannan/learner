# PREREG sleep race, add-on side, round 2 on race-mini (LFM3): tune the plain LoRA learning rate at 75 steps

Sealed 2026-11-01 before any round-2 run. Round 1 (RESULT-round1.md, commit 6342cf8b78, numbers re-checked on the add-on side with the per-item rows):
whole-model qs 76.0 pooled final C2+C4 (lr 3e-3 picked by a 3-rung scout) PASSED; add-on LoRA+ x16 71.5 FAILED on harm (ARC-500 42.8 / 32.2, KL 1.6-1.9);
the 75-step LoRA control kept its 300-step lr 2e-4 and scored 20.8, while the same LoRA at 300 steps scored 97.0 with ARC 83.6 and KL 0.10. So the add-on's
round-1 gap at 75 steps is mostly an untuned learning rate, and LoRA+ x16 overshot. Round 2 changes ONE thing: plain LoRA's lr, chosen by the same rule qs got.

Code: race_mini.py at the frozen round-1 code (6342cf8b78 line, add-on branch claude/project-thread-vof84z) + race/pc_race_r2_addon.sh (this commit). Same model,
served QAD-Q4_0 base, tapes, Week-2, seeds 1 and 2, 75 steps a night, LoRA r16 a32 on the 142 LFM3 Linears, SHY as round 1. No LoRA+.

Scout (the whole-model side's round-1 rule, unchanged): Week-1 tape, 3 nights x 75 steps, seed 1, lr in {6e-4, 2e-3, 6e-3} (3x, 10x, 30x of 2e-4;
the same 3x-spaced, 3-rung shape as qs's 1e-3 / 3e-3 / 1e-2); pick = best final C2+C4 with ARC-100 >= base - 3, ties to the lower lr; none passes -> 6e-4.
Then lr_s1, lr_s2 on Week-2 at the picked lr.

Comparison: lr vs round 1's qs_s1 / qs_s2 (the whole-model champion; same code path for both storages, same tapes, seeds, steps) on the pooled 400 forward C2+C4
items, final night (round 1's ceiling decision, from c75, stands: headline = final), paired exact McNemar (paired.py logic). Also vs c75 (round 1).
- PASS (add-on retakes the lead): pooled lr >= pooled qs + 4, p < 0.05, and lr >= qs on each seed.
- TIE / no lead: |lr - qs| < 4 or p >= 0.05 (seed 3 for both if 0.05 <= p < 0.2, protocol rule).
- WRONG (tuning lr is not the add-on's gap): pooled lr <= pooled qs - 4 with p < 0.05.
- Harm (fails the round whatever the recall): ARC-500 more than 5 below the same-seed round-1 c75 (82.4 / 83.4), i.e. < 77.4 / 78.4. Stricter than round 1's
  "base - 5" because every arm rises above the 72.2 base after training (a letter-format effect of score_arc, RESULT-round1 caveat), so base - 5 catches too little.
- Recorded, no mark: night-4 recall, held-out KL (round-1 qs 0.32-0.40, c75 0.05), changed new/stale, routine, wall time, the scout table.
Expectation (not a mark): picked lr 2e-3, pooled ~75-90, KL < 0.4. Risk: 6e-3 collapses ARC like LoRA+ x16 did (its B matrices ran at 3.2e-3); the rule excludes it.
