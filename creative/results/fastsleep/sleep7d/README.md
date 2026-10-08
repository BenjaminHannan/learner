# Roadmap 7d screens: creative-only sleep (loop 1), CPU, DEV only

Spec: creative roadmap sec. 7d, rulings b69b136446, 71050e463c, 13f4b987eb. Code: `creative/sleep7d.py`, `creative/knew.py`. Parents: N' rebuilt on CPU from B2_s100 / B2_s101 (`build_nprime.py`, `s1/s10x/nprime-build.json`). Run: `chain2.sh`. No sealed file, C2 labelled set, research-loop holdout or K_new test was opened. No K_new set was written or sealed.

## S1 (finished 03:56 UTC 10-08 = 11:56 PM ET 10-07)

Day: the worker (adapter off) tries each of 1,024 C2 pool questions greedily, and it fails almost all of them (passes 0.1% and 0.6%). On the stuck questions, the adapter-on search makes 32 tries, then 480 more where none of the 32 fit. Loop 1 (REINFORCE on the adapter only, KL 0.1 to the pre-night adapter) trains on up to 8 fitting and 8 failing tries per question: 550 and 565 questions kept. S is the placebo: the same updates with shuffled rewards. U is the untrained adapter. The setting is picked on fit@32 over the C2 DEV questions the worker fails (255 / 254 of 256). Both parents picked lr 1e-3 with 1 pass. Higher lr or more passes collapsed (KL 30-66, fit@32 down to 0-19%).

Measures: 512 tries per question at T=3 in creative mode, one sampling seed for every arm. The intervals are paired 95% bootstraps per question.

| | s100 | s101 |
|---|---|---|
| C2 DEV reach@32: U / S / C | 24.2 / 25.0 / 42.2 | 27.3 / 25.0 / 43.4 |
| **C - U** (mark >= +5) | **+18.0** [13.3, 22.7] | **+16.0** [11.3, 21.1] |
| **C - S** (mark >= +3) | **+17.2** [12.1, 21.9] | **+18.4** [13.7, 23.4] |
| distinct fitting programs / question within 32: C vs U (mark C >= 0.8 x U) | 0.79 vs 0.33 | 0.52 vs 0.36 |
| worker untouched (adapter off == N', before and after training) | pass | pass |
| reach@512: C - U | -0.8 [-5.1, 3.5] | -0.8 [-3.9, 2.3] |
| tries to first fit (questions with a fit): U / C | 90 / 31 | 79 / 34 |
| near-copy kinds (102 q), C - U | +40.2 [30.4, 50.0] | +35.3 [26.5, 45.1] |
| multi-step kinds (154 q), C - U | +3.2 [-0.6, 7.1] | +3.2 [-0.6, 7.8] |
| transfer, K_new DEV reach@512 (192 q, report only), C - U | -2.1 [-4.2, -0.5] | -2.6 [-4.7, -0.5] |

Verdict (`s1/s1-report.json`): **PASS on both parents.** Multi-step C - U pooled over both parents is +3.2 [0.6, 6.2]. That lower end is above 0, so the label is **"beyond near-copy"**, though only narrowly. Not proved wrong: the upper end of C - S is far above +1.

How to read it:
- *Shown:* within 32 tries, the trained creative part finds a fitting answer about 3 times sooner on the kinds the worker was stuck on. Shuffled rewards do nothing.
- *Shown:* it does not reach more questions at 512 tries (C - U is about -1 at reach@512). It finds the same answers faster; it does not find new ones. This is the usual pattern when reinforcement learning sharpens a sampler.
- *Shown:* most of the gain is on the near-copy kinds. The multi-step gain is small (+3).
- *Shown, small:* on the transfer kinds it loses the few rows the untrained search reached (reach@512 2-3% falls to 0).
- *Caveat:* the setting was picked on the same C2 DEV questions it is measured on, with different samples. The pick beat 5 other settings by a wide margin on s100, but tied with lr 1e-3 / 2 passes on s101. The pick can inflate C a little, and S (trained at the same setting) does not cancel that inflation.
- Wording, per the ruling: "finds answers faster on the kinds it was stuck on", never "more creative in general".

## S3 (finished 04:42 UTC 10-08 = 12:42 AM ET)

W1 is one C2b W night from N'. Its search tries come from S1's day on the same parent; the few rows where the greedy try passed get their own search. W1 then has a day on the pool. P sleeps on its shaky passes, the questions where the greedy try fits and 1-7 of 8 samples at T=1 fit (255 and 228 records). Z is the control: the same dose, made of a seeded half-skills, half-warm-row draw. All three arms get the same sleep replay. Next day: greedy first try on C2 DEV (256 q) and on 256 fresh practised (add/mult) rows, plus the skills check.

| | s100 | s101 |
|---|---|---|
| stuck rate (C2 DEV greedy fails the check): W1 / P / Z | 68.4 / 66.0 / 98.0 | 65.6 / 62.9 / 89.5 |
| **Z - P** (mark >= +3) | **+32.0** [26.2, 37.9] pass | **+26.6** [21.1, 32.4] pass |
| first try right P - Z: near-copy / multi-step / practised (mark: none below -2) | +71.6 / +5.2 / **-10.2** fail | +59.8 / +4.5 / **-7.0** fail |
| skills harm vs W1 (mark <= 2): P / Z | 0.2 pass / 0.8 | **3.1** fail / 3.1 |
| P - W1 (no mark): stuck / multi-step first try / pooled DEV first try | -2.3 / +2.6 / +2.3 | -2.7 / +2.6 / +2.7 |
| written steps per right answer, DEV: W1 / P / Z | 1.51 / 1.76 / 1.60 | 1.16 / 1.22 / 1.52 |

Verdict: **S3 fails as written.** The groups mark fails on both parents, and harm fails on s101. It is not proved wrong, because the lower end of Z - P is far above +1.

How to read it:
- *Shown:* the control Z is not a "no practice" control. It makes the worker forget C2: near-copy first try falls from 74-81% (W1) to 4-25%. Most of Z - P is the forgetting P avoids, not something P learns. The stuck pass therefore does not show that practice helps.
- *Suggested (points only, no interval: per-row next-day scores and the P/Z models were not kept):* P against W1 is about -2.5 stuck and +2.6 multi-step first try on both parents. That is short of a -3 bar if the bar were measured against W1.
- *Shown:* Z beats P on the practised add/mult rows (85% vs 75% and 86% vs 79%) because Z trains on warm rows. That is why the groups mark fails.
- *Shown:* the s101 harm (3.1) is the same for P and Z, so it comes from a second night on top of W1, not from practising.
- *Not shown:* "faster". Written steps per right answer go up a little with P, because P gets more multi-step rows right.

## S1b (finished 06:30 UTC 10-08 = 2:30 AM ET; roadmap 083303c493)

No training. F = the trained adapter (C) for tries 1-32, then the untrained one (U) for tries 33-512. S1 did not keep its tries, so S1b redraws U and C with S1's adapters and sampling seed and keeps them. Every per-row score equals S1's on both parents and both sets (0 rows differ), so F is computed from S1's own draws. Per-try records: `~/c7d/s1b/<parent>/tries_{U,C}.pkl` and `/mnt/project-files/fast-sleep/sleep7d/s1b/`.

| | s100 | s101 |
|---|---|---|
| (1) C2 DEV reach@32: F vs S1's C | 42.2 = 42.2 pass | 43.4 = 43.4 pass |
| (2) new kinds (sq_minus / triple_add / mult_sub, 192 q) reach@512: F - U (mark >= -1) | 0.0 [0.0, 0.0] (2.1 vs 2.1) pass | -0.5 [-1.6, 0.0] (2.1 vs 2.6) pass |
| (3) C2 DEV reach@512: F - U (mark >= -2) | +0.8 [0.0, 2.0] (53.1 vs 52.3) pass | +0.8 [0.0, 2.0] (55.1 vs 54.3) pass |
| tries to first fit, C2 DEV (rows with a fit): U / C / F | 90 / 31 / 51 | 79 / 34 / 49 |
| distinct fitting programs per question within 512, C2 DEV: U / C / F | 1.87 / 1.85 / 1.96 | 1.49 / 1.25 / 1.50 |
| C2 DEV reach@32: F - U | +18.0 [13.3, 22.7] | +16.0 [11.3, 21.1] |

Verdict: **PASS on both parents**, not proved wrong: F still reaches the new kinds (2.1% on both), where C reached 0.

*Shown:* switching the trained creative part off after 32 tries keeps its 32-try gain (+16 to +18) and gives back what C lost. New-kind reach returns to U's level, within one question on s101, and in-kind reach@512 is no lower than U's.

## S3' (finished 06:51 UTC 10-08 = 2:51 AM ET; roadmap 36d3fc2d14)

One change from S3: the control. Z' sleeps on a seeded draw of W1's own previous-night records, with the same dose (the same number of updates) as P. W1 is S3's W1.pt. W1's records were rebuilt from the same day and seeds, and their counts match W1's night (835 / 808). P was redrawn and its numbers are identical to S3's P. Per-row next-day scores and P.pt / Z.pt are kept (`~/c7d/s3p/<parent>/`, `/mnt/project-files/fast-sleep/sleep7d/s3p/`).

| | s100 | s101 |
|---|---|---|
| stuck rate: W1 / P / Z' | 68.4 / 66.0 / 65.2 | 65.6 / 62.9 / 62.9 |
| **(1) Z' - P** (mark >= +3) | **-0.8** [-5.5, 3.5] fail | **0.0** [-3.5, 3.5] fail |
| (2) first try P - Z': near-copy / multi-step / practised (none below -2) | **-4.9** / +1.3 / **-4.3** fail | -2.0 / +1.3 / **-2.7** fail |
| (3) skills harm vs W1: P / Z' (mark P <= 2; or P > 2 within 0.5 of Z') | 0.2 / 0.1 pass | **3.1 / 3.8** fail (0.7 apart) |
| P - W1 stuck reduction | +2.3 [-2.7, 7.4] | +2.7 [-0.8, 6.6] |
| P - W1 first try: multi-step / practised / pooled DEV | +2.6 [0.0, 5.8] / +7.8 [3.1, 12.9] / +2.3 [-2.3, 7.4] | +2.6 [-1.3, 6.5] / +1.2 [-4.3, 6.3] / +2.7 [-0.8, 6.6] |
| written steps per right answer, DEV: W1 / P / Z' | 1.51 / 1.76 / 1.49 | 1.16 / 1.22 / 1.37 |
| P - W1 written steps on rows both get right | +0.21 [0.10, 0.34] (62 rows) | 0.00 [-0.05, 0.06] (79 rows) |

Verdict: **S3' fails.** Marks 1 and 2 fail on both parents, and harm fails on s101. It is **not proved wrong**: the upper end of Z' - P is +3.5 on both parents, not below +1.

How to read it:
- *Shown:* practising the shaky passes does no better than sleeping again on the previous night's records. The point estimates are -0.8 and 0.0. The intervals are wide (about +/-4.5 points on 256 questions), so a 3-point effect cannot be ruled out either way.
- *Suggested:* any second night helps a little. Against W1, P is about 2.5 less stuck, but neither interval clears 0. The intervals for Z' are not computed here.
- *Shown:* on s101 every second night costs skills: P 3.1, Z 3.1, Z' 3.8 points of pooled-5 against W1, which itself is only 0.9 below N'. On s100 the second night costs nothing (0.1-0.8).
- *Shown:* P does not make answers shorter. On rows both models get right, P writes the same number of steps or more.

## Skills harm by family (first look, 3:15 AM ET 10-08; `creative/harm_look.py`, `harm/`)

No training. Greedy answers on skills DEV in_dist (34 families x 200 = 6,800 rows) for B2, N', W1 (night 1), P and Z' (night 2), with row flips between every pair.

| exact % | seq_next | rule_apply | cipher_map | digits_parity | passage_qa | order_chain | story_chain3 | in_dist (34) | pooled-5 (the guard) |
|---|---|---|---|---|---|---|---|---|---|
| s100 B2 | 81.0 | 89.5 | 97.0 | 94.0 | 95.0 | 66.0 | 100.0 | 89.4 | 99.7 |
| s100 N' | 62.0 | 77.5 | 90.0 | 87.0 | 90.0 | 63.5 | 99.0 | 86.7 | 98.1 |
| s100 W1 | 43.0 | 50.0 | 71.5 | 83.0 | 84.0 | 56.0 | 99.5 | 82.9 | 97.4 |
| s100 P / Z' | 30.5 / 32.5 | 47.5 / 48.0 | 61.5 / 63.5 | 80.0 / 78.5 | 82.5 / 81.5 | 51.5 / 53.5 | 99.0 / 99.0 | 81.7 / 81.7 | 97.2 / 97.3 |
| s101 B2 | 88.5 | 92.5 | 99.5 | 95.5 | 95.5 | 60.0 | 99.5 | 90.5 | 99.8 |
| s101 N' | 66.5 | 85.0 | 89.0 | 85.5 | 90.5 | 59.5 | 99.0 | 87.8 | 98.9 |
| s101 W1 | 42.5 | 64.0 | 72.5 | 79.0 | 79.0 | 53.5 | 99.5 | 84.2 | 98.0 |
| s101 P / Z' | 30.0 / 34.5 | 54.5 / 56.0 | 58.5 / 56.5 | 79.0 / 73.0 | 78.0 / 74.5 | 51.5 / 49.0 | 91.0 / 87.5 | 81.7 / 81.8 | 94.9 / 94.2 |

What it shows:
- *Shown:* the harm is not a second-night quirk. Every step costs skills: the stepping-stone build (B2 to N') costs about 2.7 in_dist points, night 1 about 3.7, night 2 about 1.2 (s100) and 2.5 (s101). From B2 to night 2 that is 7.7 and 8.9 points.
- *Shown:* the same few families take most of it, on both parents and in every step: seq_next (81 to 31, 89 to 30), rule_apply, cipher_map, digits_parity, passage_qa and order_chain. These are mostly induce-a-rule-from-examples families, the nearest in format to C2.
- *Shown:* the nightly guard (pooled-5 = the five chain families) is nearly blind to this. It moved 2.5 points (s100) while in_dist lost 7.7 and seq_next lost 50. On s101 it only fired on night 2, because night 2 finally reached story_chain3 and state_update.
- *Shown:* half of every sleep batch is skills replay over all 34 families, and that does not protect these families.
- *Untested:* the research loop's "harm none" (71.3% C2 holdout) used the same pooled-5 guard (`creative/rl/eval_c2.py` chain5_harm), so its in_dist harm was never measured.

## Test J (finished 10:55 UTC 10-08 = 6:55 AM ET; roadmap a27faa485b)

Loops 1 + 2 (J) against loop 2 alone (W), two days and nights from N'. Night 1 is shared: W1 = S3's W1, and J's adapter C1 equals S1's C exactly (max abs difference 0 on both parents). Day 2 uses the same 1,024 pool questions, seed+1. W searches with no trained adapter; J searches in F mode (adapter on for pass 1's 32 tries, off for pass 2). Night 2: J runs loop 1 first, then both arms sleep the worker on their own records. Measures use one sampling seed for both arms. No repair in either arm.

| | s100 | s101 |
|---|---|---|
| (1) stuck W / J, W - J (mark >= +3) | 66.0 / 58.2, **+7.8** [3.1, 12.9] pass | 60.2 / 59.0, +1.2 [-2.3, 5.1] fail |
| (2) creative reach@32 (F) W / J, J - W (mark >= +5) | 58.6 / 52.3, **-6.3** [-10.9, -1.6] fail | 54.7 / 55.1, +0.4 [-3.1, 4.3] fail |
| (3) new-kind reach@512 (F) W / J, J - W (mark >= -1) | 7.3 / 5.2, -2.1 [-6.3, 2.1] fail | 4.2 / 6.2, +2.1 [-1.6, 6.3] pass |
| (4) C2 first try W / J, J - W (mark >= -2) | 34.0 / 41.8, +7.8 [3.1, 12.9] pass | 39.5 / 41.0, +1.6 [-2.0, 5.1] pass |
| first try J - W: near-copy / multi-step | +26.5 [17.6, 35.3] / -4.5 [-9.7, 0.0] | +4.9 [-1.0, 10.8] / -0.6 [-4.5, 3.2] |
| (5) harm J vs W (new measure) | in_dist +0.2 better, nothing fires, pass | in_dist -0.3, word_filter fires, **fail** |
| harm vs N' (report): W / J in_dist drop, families firing | 3.8 / 3.6; 7 / 8 families | 3.1 / 3.4; 7 / 9 families |
| harm vs B2 (report): W / J in_dist drop | 6.5 / 6.3 | 5.8 / 6.2 |
| day 2: pool questions with a fit in pass 1, W / J | 566 / 506 | 586 / 548 |
| night 2: records W / J; J's loop-1 kept rows (share whose fits all came from tries 33+) | 1187 / 1038; 249 (53%) | 1118 / 1078; 138 (54%) |

Verdict: **J fails on both parents.** Mark 2 fails on both; s100 also fails mark 3, and s101 fails marks 1 and 5. It is not proved wrong, because s100's stuck interval reaches +12.9.

How to read it:
- *Shown:* the creative part's night-1 training does not carry over to the slept worker. On day 2, J's adapter (trained on N') finds FEWER fits in its 32 tries than plain sampling on W1 (506 vs 566, 548 vs 586). After night 2, J's creative reach@32 is no better than W's: -6.3 and +0.4, against S1's +16 to +18 on N'. Most of the loss is on sq_plus (18 vs 41, 16 vs 25).
- *Suggested:* the adapter is trained on one worker and then used on the next one, after that worker has slept. Night 2's loop 1 is also half off-policy (53-54% of kept rows had fits only from adapter-off tries).
- *Shown, s100 only:* J's worker gets better on near-copy first try (+26.5). J's day-2 records hold far fewer last_digit programs (218 vs 382). *Suggested:* fewer, more consistent programs per question teach x mod 10 better. s101 shows the same sign but much smaller (+4.9, interval crosses 0).
- *Shown:* both arms carry the per-night skills harm (vs N': in_dist -3.1 to -3.8, 7-9 families firing). J adds none on s100 and a little on s101 (word_filter; pooled-5 97.4 vs 98.9).
