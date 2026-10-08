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

## Test R (finished 12:42 UTC 10-08 = 8:42 AM ET; roadmap e9e0bd2aeb, `creative/repair7d.py`, `r/`)

The repair pass runs after each night. The model checks itself on a held slice of its own skills training rows (100 per family, 3,400 rows, never DEV), compared with the same check before that night. Families that fire under the new harm rule get 64 replay-only updates on 1,024 of their other training rows (lr 1e-3), and the check runs again, for up to 4 rounds. Arm E (report only) gets the same number of updates spread evenly over all 34 families. Point 1 is night 1 (W1, from N'). Point 2 is night 2 (each arm sleeps on J's W day-2 records, from its own repaired model). The DEV harm measure and C2 DEV first try are taken on every model.

| | s100 | s101 |
|---|---|---|
| skills in_dist: N' / W1 / W1r / W1e | 86.7 / 82.9 / **77.3** / 79.1 | 87.8 / 84.2 / **79.9** / 80.1 |
| held-slice check during point-1 repair (pre-night 92.2 / 92.5) | 87.7, 84.2, 81.7, 83.5, 80.8 (families firing: 12, 20, 21, 16, 23) | 87.4, 79.8, 83.9, 79.9, 82.2 (8, 21, 17, 18, 19) |
| repair updates point 1 / point 2 | 256 / 0 | 256 / 0 |
| (a) harm vs the pre-night model, point 1 (W1r vs N') | drop 9.4, 23 families fire, **fail** | drop 7.9, 16 fire, **fail** |
| (a) harm, point 2 (W2r vs W1r) | in_dist +5.6 better, rule_apply fires, fail | +4.9 better, nothing fires, pass |
| (b) C2 first try, W1r - W1 (mark >= -2) | 31.2 -> 0.0, **-31.2** [-37.1, -25.8] fail | 34.4 -> 14.8, **-19.5** [-24.6, -14.8] fail |
| (b) C2 first try, W2r - W2 | 34.0 -> 38.7, +4.7 [0.8, 8.6] pass | 39.5 -> 40.2, +0.8 [-2.3, 3.9] pass |
| E (even spread): W1e in_dist / C2 first try | 79.1 / 2.0 | 80.1 / 2.7 |
| after night 2, vs N' (report): W2 / W2r / W2e in_dist drop | 3.8 / 3.8 / 4.2 | 3.1 / 3.0 / 3.6 |
| night 2 alone (W2 vs W1, J's arm, no repair) | drop -0.0, nothing fires | drop -0.5, nothing fires |

Verdict: **R fails on both parents and is proved wrong** (the rule fixed in advance: after repair, point-1 in_dist is still more than 1.5 below N' on both parents; it is 9.4 and 7.9 below).

How to read it:
- *Shown:* replay-only updates on the model's own training rows make the skills harm worse, not better. The held check falls round after round (s100 87.7 to 80.8), and more families fire after the first round than before it. DEV agrees: W1r is 5.6 / 4.3 below W1. The even spread does the same (79.1 / 80.1), so it isn't about which families are picked.
- *Shown:* the same updates wipe out the C2 gain from night 1 (first try 31 -> 0, 34 -> 15; E 2-3%).
- *Shown:* night 2 (half C2 records, half replay drawn fresh from all 200k training rows) brings W1r back up to the unrepaired level (in_dist 82.9 / 84.8, C2 first try 38.7 / 40.2). So in the end, after two nights, the repair changed nothing (vs N' 3.8 / 3.0 against 3.8 / 3.1).
- *Shown (J's W arm):* night 2 by itself adds no skills harm (W2 vs W1: 0.0 / -0.5, nothing fires). The cost comes from night 1 and from the N' stepping stone.
- *Suggested, untested:* the cause is the optimiser, not the data. Each repair round starts a fresh AdamW at lr 1e-3, which is B2's own peak pretraining lr. On rows the model already fits, the gradients are mostly noise, and Adam scales noise up to full-size steps, so the weights drift. A second suspect is overfitting to small row sets: R visits each of its 1,024 rows 4 times per round, and E visits its 1,024 rows 16 times. In the night, by contrast, replay rows are fresh and seen about once each. A 2 x 2 check on N' (lr 1e-3 or 1e-4, by 1,024 rows reused or fresh rows each step, 256 replay-only updates, held check) would tell the two apart.

## Test S1w (finished 13:41 UTC 10-08 = 9:41 AM ET; roadmap 7d 10-08, `s1w/`)

S1 with the slept worker: loop 1 trains the creative adapter on **W1** (S3's night-1 worker) from day 1's kept tries (S1's day, drawn by N'), at S1's setting (lr 1e-3, 1 pass, KL 0.1, no grid). U = W1 with the untrained adapter. C = W1 with the adapter trained on W1. C1 (report only) = S1's adapter trained on N', loaded on W1 (the same adapter J used on day 2). All arms are measured on W1 with one sampling seed. Greedy first try is identical across arms (adapter off).

| | s100 | s101 |
|---|---|---|
| kept tries (rows) / loop-1 updates / KL to W1 at end (S1 on N': 13.2 / 7.8) | 6,205 (550) / 97 / 21.2 | 6,387 (565) / 100 / 27.4 |
| (1) C2 DEV creative reach@32: U / C / C1; C - U (mark >= +5) | 46.9 / 44.1 / 44.1; **-2.7** [-6.2, +0.8] fail | 48.0 / 44.5 / 47.3; **-3.5** [-7.4, -0.4] fail |
| C - U near-copy / multi-step | -4.9 [-9.8, -1.0] / -1.3 [-6.5, 3.9] | 0.0 / -5.8 [-11.7, 0.0] |
| C - C1 (report) | 0.0 [-3.5, 3.5] | -2.7 [-5.9, 0.0] |
| reach@32 by kind U -> C (sq_plus, double_add, affine) | 16 -> 6, 22 -> 25, 2 -> 4 | 10 -> 0, 33 -> 24, 0 -> 2 |
| distinct fitting programs per question in 32 tries: U / C / C1 | 1.47 / 1.07 / 1.12 | 1.39 / 0.70 / 0.99 |
| (2) new-kind reach@512 in F mode: U / C; C - U (mark >= -1) | 5.7 / 10.4; **+4.7** [2.1, 7.8] pass (sq_minus 17 -> 31) | 6.2 / 6.2; 0.0 pass |
| (3) worker untouched (before / after) | pass / pass | pass / pass |
| for comparison, S1 on N': C - U | +18.0 [13.3, 22.7] (U 24.2) | +16.0 [11.3, 21.1] (U 27.3) |

Verdict: **S1w fails on both parents and is proved wrong** (the rule fixed in advance: C - U upper end < +1 on both parents; it is +0.8 and -0.4).

How to read it:
- *Shown:* refitting the adapter on the slept worker from day 1's tries does not help. On W1 the adapter is no better than no adapter (-2.7, -3.5), and no better than the N'-trained one (0.0, -2.7). sq_plus, the multi-step kind S1 helped most on N', drops to 0-6%.
- *Shown:* W1 alone already reaches what S1's adapter reached on N' (U 47-48 on W1 vs C 42-43 on N'). Night 1 slept on records from the same day, so the kept tries mostly teach W1 what it has already learned.
- *Shown:* on W1 the adapter narrows the search. Distinct fitting programs per question fall from 1.4-1.5 to 0.7-1.1, below S1's variety bar (0.8 x U) on both parents. The KL to W1 ends 2-3x higher than S1's KL to N'.
- *Suggested:* day 1's kept tries are off-policy for W1 (drawn by N', a broader worker). Loop 1 has no correction for that, so it sharpens W1 further onto programs it already favours, and loses the rare ones. This is the roadmap's stated next step: a few fresh adapter tries at night on the slept worker (on-policy for W1).
- J2 (the swapped night order) does not run, because its gate was S1w passing.

## 2 x 2 drift check (finished 14:27 UTC 10-08 = 10:27 AM ET; roadmap 8e924aaa2f, `creative/drift7d.py`, `drift/`)

Why R failed. Each cell starts from W1 and runs 256 replay-only updates on its own skills training rows (fresh AdamW, batch 64, warmup 10, cosine). The cells are lr 1e-3 or 1e-4, crossed with `reused` (1,024 rows spread over all 34 families, each seen 16 times; the same draw as R's arm E) or `fresh` (16,384 distinct rows, each seen once). Measures: the held check (R's 3,400 held training rows), skills DEV in_dist with the harm measure, and C2 DEV first try, all against W1. The (1e-3, reused) cell reproduces R's W1e exactly on both parents (same held and DEV hits).

| s100 / s101 | held in_dist (drop vs W1) | DEV in_dist (change vs W1) | DEV families firing | C2 first try (vs W1) |
|---|---|---|---|---|
| W1 | 87.6 / 87.4 | 82.9 / 84.2 | - | 31.2 / 34.4 |
| lr 1e-3, reused | 82.0 / 81.9 (**5.6 / 5.5**) | 79.1 / 80.1 (-3.7 / -4.1) | 6 / 8 | 2.0 / 2.7 (**-29 / -32**) |
| lr 1e-3, fresh | 87.4 / 89.0 (0.2 / -1.6) | 84.7 / 86.5 (**+1.8 / +2.3**) | 1 / 1 | 0.0 / 2.3 (**-31 / -32**) |
| lr 1e-4, reused | 87.3 / 87.2 (0.4 / 0.1) | 82.9 / 84.5 (0.0 / +0.3) | 1 / 1 | 24.6 / 30.9 (-6.6 [-10.5, -2.3] / -3.5 [-7.0, 0.0]) |
| lr 1e-4, fresh | 89.5 / 89.7 (-1.9 / -2.4) | 84.5 / 86.2 (**+1.6 / +2.0**) | 1 / 1 | 24.2 / 30.1 (-7.0 [-11.3, -3.1] / -4.3 [-7.8, -0.8]) |

The one family firing in the good cells is fewshot_number_rule, the C2-like family that the night had pushed up. For comparison, N' DEV in_dist is 86.7 / 87.8.

Marks (fixed in advance): **overfit confirmed on both parents** (1e-3 fresh drops 0.2 / -1.6, so at most 1.0; 1e-3 reused drops 5.6 / 5.5, so at least 3). Drift is not confirmed: 1e-3 with fresh rows does not hurt skills. Not proved wrong.

How to read it:
- *Shown:* the skills damage in R and E came from reusing a small row set (16 visits per row at lr 1e-3), not from the optimiser's step size. The same number of updates on fresh rows, at either lr, makes skills **better** than W1 (DEV +1.6 to +2.3, about two-thirds of the way back to N').
- *Shown:* a separate effect. Any 256 replay-only updates at lr 1e-3 erase night 1's C2 gain (first try down to 0-3%), whether the rows are reused or fresh. At lr 1e-4 most of the C2 gain survives (-3.5 to -7.0).
- *Suggested:* the night's own records are a small set seen 32 times at lr 1e-3, the same pattern as the damaging cell. Against that, night 2 uses the same recipe and adds no skills harm, while night 1 does. So the cost may belong to the first big move onto C2, not to reuse as such.
- *Suggested:* a fresh-row replay pass at lr 1e-4 after a night trades about 2 DEV skills points back for about 4-7 points of C2 first try. As it stands, that misses a "C2 within 2 points" mark.

## Test S1f (finished 14:53 UTC 10-08 = 10:53 AM ET; roadmap 377df3fc2c, `s1f/`)

Loop 1 on W1 from **fresh on-policy night tries**. W1's greedy try is checked on all 1,024 pool questions. On the questions it still fails, 32 tries each are drawn with the adapter on in its untrained state (so these are plain W1 samples at T 3.0), one round. Loop 1 then runs at S1's setting (lr 1e-3, 1 pass, KL 0.1). U = W1 untrained. W (report only) = S1w's adapter. U and W reuse S1w's cached measures (same draws), so only C is new.

| | s100 | s101 |
|---|---|---|
| night draw: still-stuck questions / with a fit in 32 / samples / CPU s (wall s) | 567 / 128 / 19,168 / 533 (292) | 493 / 75 / 16,800 / 466 (255) |
| kept tries (rows) / loop-1 updates / KL to W1 at end | 1,535 (128) / 24 / 0.47 | 860 (75) / 14 / 0.10 |
| (1) C2 DEV creative reach@32: U / C; C - U (mark >= +5) | 46.9 / 49.6; **+2.7** [0.8, 5.1] fail | 48.0 / 47.7; -0.4 [-1.2, 0.0] fail |
| C - U multi-step | **+4.5** [1.3, 8.4] (sq_plus 16 -> 20, double_add 22 -> 31) | -0.6 [-1.9, 0.0] |
| (2) variety, distinct fits in 32: U / C (mark C >= 0.8 x U) | 1.47 / 1.57 pass | 1.39 / 1.41 pass |
| (3) new-kind reach@512 F mode, C - U (mark >= -1) | +0.5 pass | 0.0 pass |
| (4) worker untouched | pass | pass |
| C - W (S1w's adapter, report) | +5.5 [2.0, 9.0] | +3.1 [0.0, 7.0] |

Verdict: **S1f fails on both parents and is NOT proved wrong**. The rule is C - U upper end < +1 on both parents; s101 meets it (0.0) but s100 does not (+5.1).

How to read it:
- *Shown:* on-policy tries fix what S1w broke. Variety holds or rises (S1w cut it to 0.7-1.1), sq_plus no longer collapses, and C beats S1w's adapter on both parents.
- *Shown:* the training signal is small. Only 13-23% of the questions W1 still fails get a fit in 32 tries, giving 128 / 75 kept rows and 24 / 14 updates (S1 on N' had 550 rows and 97 updates). The adapter hardly moves (KL 0.47 / 0.10). s100 shows a real but small gain, mostly multi-step; s101 shows none.
- *Suggested:* the limit is how many fits the night finds, not the method. The single change that builds on this is more night tries per still-stuck question.
- J2 does not run, because its gate was S1f passing.

## Test VL (finished 15:31 UTC 10-08 = 11:31 AM ET; roadmap 7526d614e5, `creative/night7d.py`, `vl/`)

Each arm makes one change to night 1 from N', against the standard night 1 (W1: lr 1e-3, each record seen 32 times). Both arms use the same 835 / 808 records (W1's own, rebuilt and count-checked) and the same seed and replay. V sees each record 8 times (208 / 202 updates). L uses lr 1e-4 with 32 visits (835 / 808 updates). Measures are on DEV.

| | s100 | s101 |
|---|---|---|
| skills in_dist: N' / W1 / V / L | 86.7 / 82.9 / 83.0 / **87.5** | 87.8 / 84.2 / 84.9 / **88.3** |
| (1) harm vs N' (drop; families firing) | W1 3.8 (9); V 3.7 (9) fail; **L -0.8 (0) pass** | W1 3.6 (9); V 2.9 (8) fail; **L -0.6 (0) pass** |
| pooled-5: W1 / V / L | 97.4 / 97.3 / 98.2 | 98.0 / 94.5 / 99.0 |
| C2 first try: W1 / V / L | 31.2 / 29.7 / 28.9 | 34.4 / 33.6 / 33.6 |
| (2) first try vs W1 (mark >= -2) | V -1.6 [-5.9, 3.1] pass; **L -2.3 [-7.0, 2.3] fail** | V -0.8 [-4.3, 2.7] pass; L -0.8 [-4.3, 2.3] pass |
| arm passes (1) and (2) | V no, L no (by 0.3 on first try) | V no, **L yes** |
| proved wrong (drop not at least 1.0 below W1's on both parents) | V yes; L no | |
| reference (report only): W1 + 256 fresh-row replay-only updates at 1e-4 | in_dist 84.5, first try 24.2 | 86.2, 30.1 |

Verdict: **neither arm passes on both parents.** V is proved wrong. L is not proved wrong; it passes on s101 and misses on s100 only by first try (-2.3 against the -2 mark, interval [-7.0, 2.3]). By the rule fixed in advance, L is the one to build on.

How to read it:
- *Shown:* night 1 at lr 1e-4 costs no skills at all. in_dist ends up 0.6-0.8 above N', no family fires, and pooled-5 rises. It keeps nearly all of night 1's C2 gain (28.9 / 33.6 against W1's 31.2 / 34.4, from N' at 0.4).
- *Shown:* fewer visits at lr 1e-3 (V) keeps the C2 gain but not the skills. Its harm matches W1's.
- *Suggested:* together with the 2 x 2, the night's lr is what sets the skills cost. At lr 1e-3, reusing a small set (the records, 32 visits) overfits. At 1e-4, the same reuse is harmless. N' itself came from an lr 1e-3 stepping-stone night (N' vs B2 in_dist -2.2 to -2.7), and so did the research loop's sleep. Both are worth re-checking under a lower lr.

## Test L2 (finished 17:07 UTC 10-08 = 1:07 PM ET; roadmap 7c8041caa3, `night7d.py l2`, `l2/`)

Both nights at lr 1e-4, compared with the standard two nights at lr 1e-3 (W1 then W2, job 8's recipe). Night 1 is VL's L. Day 2 from L uses the same two-pass search and seeds as W's day 2 (2,864 / 2,715 s on 2 threads). Night 2 = L's own day-2 records at lr 1e-4, 32 visits. On DEV, the multi-step set is the 154 HARD_KINDS questions.

| | s100 | s101 |
|---|---|---|
| skills in_dist: N' / W1 / W2 / L / L2 (B2) | 86.7 / 82.9 / 82.9 / 87.5 / **87.1** (89.4) | 87.8 / 84.2 / 84.7 / 88.3 / **88.6** (90.5) |
| (1) harm L2 vs N' | -0.4 (better), nothing fires, **pass** | -0.8 (better), nothing fires, **pass** |
| night 2's own cost (L2 vs L) | 0.4, nothing fires | -0.2, nothing fires |
| (2) multi-step first try L2 - W2 (mark >= -2) | **-4.5** [-9.7, +0.6] fail | **-3.2** [-7.8, +0.6] fail |
| multi-step first try L2 - N' (report; job 8's climb mark +10) | +3.9 [0.6, 7.8] | +3.2 [0.0, 6.5] |
| pooled C2 first try: W1 / W2 / L / L2 | 31.2 / 34.0 / 28.9 / 33.6 (L2 - W2 -0.4 [-5.5, 4.7]) | 34.4 / 39.5 / 33.6 / 30.1 (**-9.4** [-14.1, -4.7]) |
| multi-step reach@32 (plain sampling): W1 / W2 / L / L2 | 13.0 / 31.8 / 6.5 / 9.1 (L2 - W2 **-22.7** [-29.9, -16.2]) | 14.3 / 24.7 / 7.1 / 9.1 (**-15.6** [-22.7, -9.1]) |
| night-2 records: W2 / L2 (sq_plus) | 1,187 / 1,046 (136 / 103) | 1,118 / 1,048 (68 / 61) |
| skills drop vs B2: N' / W1 / W2 / L / L2 | 2.7 / 6.5 / 6.5 / 1.9 / 2.3 | 2.8 / 6.3 / 5.8 / 2.2 / 2.0 |

Verdict: **L2 fails mark 2 on both parents and is not proved wrong** (the upper ends are +0.6, not below 0). By the pre-set rule, L64 (both nights at lr 1e-4 with 64 visits) is the next single change.

How to read it:
- *Shown:* at lr 1e-4 the skills cost stays at zero across two nights. Neither night costs skills against the night before or against N'.
- *Shown:* the C2 climb is much smaller. Multi-step first try rises only +3-4 over N' (the climb mark is +10), and trails W2 by 3-5. Pooled first try matches W2 on s100 but trails by 9 on s101, where L2 even fell from L (33.6 to 30.1).
- *Shown:* the lr 1e-3 nights widen the worker's sampling on multi-step kinds (reach@32 13 -> 32 and 14 -> 25 across night 2). The lr 1e-4 nights don't (6.5 -> 9.1, 7.1 -> 9.1, below W1). The low lr also finds fewer night-2 records (1,046 vs 1,187 on s100).
- *Suggested:* part of what costs skills at lr 1e-3 is also what drives the multi-step search climb. More visits at lr 1e-4 (L64) tests whether the climb can be bought back without the cost.

## Test L64 (finished 19:53 UTC 10-08 = 3:53 PM ET; roadmap 7c8041caa3, `night7d.py l2 --visits 64`, `l64/`)

L2 with 64 visits per record on both nights instead of 32 (lr 1e-4 on both). Everything else is L2's recipe: same records on night 1 (835 / 808), same day-2 search and seeds from the new night-1 model, then night 2 on its own day-2 records. Marks are L2's, plus one pre-set proved-wrong rule: "more practice at the low lr adds no climb" if L64 - L2 on multi-step first try is below +1.0 on both parents. In the table, L1 / L64 are this run's night-1 / night-2 models.

| | s100 | s101 |
|---|---|---|
| skills in_dist: N' / W2 / L2 / L1 / **L64** (B2) | 86.7 / 82.9 / 87.1 / 87.6 / **87.6** (89.4) | 87.8 / 84.7 / 88.6 / 88.5 / **88.9** (90.5) |
| (1) harm L64 vs N' | -0.9 (better), but **table_calc fires**: 62.5 -> 56.0 (-6.5 [-11.5, -1.0]); **fail** | -1.2 (better), nothing fires, **pass** |
| (2) multi-step first try L64 - W2 (mark >= -2) | **-2.6** [-7.8, +2.6] fail | **-2.6** [-7.1, +1.9] fail |
| proved wrong? (vs W2 upper end < 0 on both; L64 - L2 multi-step < +1.0 on both) | no (+2.6); no (+1.9) | no (+1.9); yes (+0.6) |
| multi-step first try L64 - N' (report; job 8's climb mark +10) | +5.8 [1.9, 10.4] | +3.9 [0.6, 7.8] |
| pooled C2 first try: W1 / W2 / L2 / L1 / L64 | 31.2 / 34.0 / 33.6 / 28.5 / 35.2 (L64 - W2 +1.2 [-3.9, 6.3]) | 34.4 / 39.5 / 30.1 / 34.0 / 35.2 (-4.3 [-8.6, 0.0]) |
| multi-step reach@32: W1 / W2 / L2 / L1 / L64 | 13.0 / 31.8 / 9.1 / 10.4 / 18.2 (L64 - W2 **-13.6** [-21.4, -5.8]) | 14.3 / 24.7 / 9.1 / 11.0 / 13.0 (**-11.7** [-18.2, -5.2]) |
| L64 - L2 (report): multi-step first try / pooled first try / multi-step reach@32 | +1.9 [-2.6, 6.5] / +1.6 [-3.1, 6.6] / **+9.1** [3.2, 14.9] | +0.6 [-3.2, 4.5] / **+5.1** [0.8, 9.4] / +3.9 [-1.9, 9.1] |
| night 1 at 64 vs 32 visits (VL's L): skills in_dist / C2 first try | 87.6 vs 87.5 / 28.5 vs 28.9 | 88.5 vs 88.3 / 34.0 vs 33.6 |
| night-2 records: W2 / L2 / L64 (sq_plus) | 1,187 / 1,046 / 1,107 (136 / 103 / 94) | 1,118 / 1,048 / 1,046 (68 / 61 / 53) |
| CPU seconds: night 1 / day 2 / night 2 | 2,579 / 2,269 / 3,770 | 2,522 / 2,237 / 3,530 |

Verdict: **L64 fails on both parents and is not proved wrong.** Mark 2 misses by one question on each parent: on 154 questions one question is 0.65 points, so -2.6 is 4 questions behind W2 where the mark allows 3. On s100 the harm mark also fails on one family. The no-climb rule holds only on s101, and the vs-W2 upper ends are above 0, so neither proved-wrong rule is met.

Roadmap ruling (009028cd42, 3:57 PM ET): fails, not proved wrong. The blocker is s100's table_calc fire (3 rows past the line, a real fire). The one-question miss on mark 2 counts as met under Ben's near-miss rule. lr 3e-4 is the next single change and stays held; the 7d line pauses until the big-run thread asks.

How to read it:
- *Shown:* doubling the visits on night 1 changes nothing (skills and C2 first try within 0.4 of VL's L). The gain is on night 2: reach@32 on multi-step recovers part of the lr 1e-3 nights' widening (+9.1 and +3.9 over L2), and pooled first try rises.
- *Shown:* the skills cost stays near zero overall (in_dist is above N' on both parents), but 64 visits on night 2 starts to cost one family on s100. table_calc was 62.0 after L2 and is 56.0 after L64 (-6.0 [-10.5, -1.5]); night 1 at 64 visits left it within its interval.
- *Shown:* multi-step first try still trails W2 by 4 questions on both parents, and the climb over N' (+5.8 / +3.9) is still below the +10 mark.
- *Suggested:* more visits at lr 1e-4 buy back sampling breadth faster than first-try accuracy, and the first family cost appears at 64 visits. That puts the lever between lr 1e-4 and 1e-3 rather than in more visits. The pre-set next step (lr 3e-4) is held under the one-big-run rule (3:27 PM ET 10-08), so nothing more runs here unless the big-run thread asks for it.
