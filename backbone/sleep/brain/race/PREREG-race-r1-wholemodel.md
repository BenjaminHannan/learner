# Sleep race, round 1, whole-model side: 4-bit scale sleep ("qs") vs the add-on champion

Sealed before any run of this arm. Rules: /mnt/project-files/sleep-race/LEADERBOARD.md (frozen 2026-10-25 21:45Z).

## The one change
Same recipe as the add-on champion (ab_ob_b4_nb on IFM/K2-Horizon-3.7B rev 9d280ff742235796925c9fe3cf243dc1beea5c08, 4-bit MLX-affine base
group 64 via --q4-base, work scale 4, Week-2, same dream pipeline, same morning gate). Only the storage form differs:
- add-on: LoRA r16 a32 lr 2e-4 on the LoRA targets (q/k/v/o, gate/up/down).
- whole-model (this arm, `--storage qs`): the LoRA is frozen at zero; for every weight group (64 weights) of every LoRA-target layer, sleep trains a
  relative scale change u and an offset change v. Served group scale S = s0(1+u), offset B = b0 + s0 v, so every weight of those layers moves
  (W = q S + B), the 4-bit codes q never change, and S, B are what a 4-bit file already stores. No bf16 master, no separate matrix.
  Each morning, together with SHY (u, v x 0.85), S and B are rounded to fp16 (nearest; race rule 3) and u, v are read back from the rounded values,
  so the run itself is the served copy and no extra precision carries over between nights. ~105M trained numbers (vs ~30M LoRA).

## Step 0: lr card test (Week-1 world only, backbone/sleep/brain/qs_card.py, defaults)
Arms lora:2e-4 and qs:{1e-3, 3e-3, 1e-2, 3e-2}, 150 Trainer steps each on Week-1 fact sentences + forward Q&A, KL guard on.
Rule: qs lr = the one with the highest trained-question recall on the served copy (fp16 nearest) among those with ARC-val(100) drop <= 3 points; ties -> lower lr.
If no qs lr passes the ARC rule, use 1e-3. Reported, not a pass mark: qs vs LoRA recall at equal steps (capacity check).

## Step 1: Week-2 runs
    python backbone/sleep/brain/sleepb.py --arm ab_ob_b4_nb --model IFM/K2-Horizon-3.7B --revision 9d280ff742235796925c9fe3cf243dc1beea5c08 \
      --week backbone/sleep/brain/data/week2.json --q4-base --storage qs --qs-store fp16 --qs-round nearest --qs-lr <step-0 pick> \
      --tok-budget 1024 --arc-base --seed {1,2} --out out/race_r1/qs_s{1,2}
No --schedule: in sleepb.py a schedule entry is the REFERENCE night and is multiplied by the work scale (4), so passing the champion's realized steps
(208, 1200, ...) would give 4x the work. Both sides' natural step plan is min(300, 40 + 4 n_active) x 4 (nights 2-7 hit the 1200 cap); the realized
steps are compared after the run and any night that differs by more than 5% is reported.

Opponent: add-on champion seed 1 = results_a11/result_k2s_q4.json (86.0); seed 2 = the add-on thread's round-1 control run (same command with
--storage lora, i.e. the a11 q4 command with --seed 2).

## Scores (served copy; weights only unless said)
Headline R = recall C2+C4 (200 items, scores.weights). Also: two-step, reverse, C1, changed new/stale, routine; ARC-Easy 500 and diary vs base.

## Pass mark (fixed now)
- PASS (whole-model takes the lead): mean R over seeds 1, 2 >= add-on mean + 5.0 AND paired exact McNemar (paired.py) on the pooled 400 items p < 0.05
  in the qs direction AND no harm on either seed (ARC-Easy 500 >= arc_easy_base - 5 points; diary >= base_diary - 5 points).
- TIE: |difference| < 5 or p >= 0.05, no harm -> the add-on keeps the title (the champion holds on a tie).
- WRONG (the idea is refuted as a storage form at this lr): qs mean R < add-on mean - 5 with p < 0.05, or harm on either seed.
Seed-1-only early read: if only seed 1 can run before the PC queue moves on, it is reported as "suggested", never as a lead.

## Why this could fail (written before the run)
- Capacity: one scale + one offset per 64 weights may store fewer facts than a rank-16 LoRA (the step-0 card test reports this).
- The base roles (tagging, dreaming, KL reference) use the ORIGINAL 4-bit grid in both arms, so the dream pipeline is identical; any difference is storage.
- fp16 rounding of S, B may erase small nightly changes (step 0 reports round_err_energy_frac per lr).
