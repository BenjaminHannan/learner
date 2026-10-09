# Small talker check - Wave 1 results (2026-10-08 ET, seed 0, Mac/MPS, ~5 min per arm)

Marks and arms: see SPEC.md (fixed before any arm trained). Harness: `prep_states.py` (frozen EmbeddingGemma-2 token states, cached outside the repo), `models.py`, `run_arm.py` (one fixed config for every arm: batch 64, 3000 updates, AdamW 1e-3, 24,000 train rows). Every number below is from `results/<arm>_s0/results.json` and `hits_dev.json`. DEV = 3,000 rows of 8 kinds never trained on (1,440 short answers, 549 of them "hard": >8 characters or 2+ words). Scoring = exact match after `en_norm`. Labels: **shown** = measured here; **suggested** = fits the data, not isolated; **untested** = not run.

## Numbers (DEV, unseen kinds)

| arm | params | short-answer EM (S) | hard slice (S_H) | yes/no EM | PRACTISED EM (short / all) | shuffled-state S |
|---|---|---|---|---|---|---|
| P0 linear probe on frozen Gemma states | 0.20M | 67.71 | 62.48 | 77.2 | 66.0 / 73.2 | 19.2 |
| B0-nothinker (projection only) | 0.48M | 83.06 | 80.33 | 84.9 | 84.0 / 84.4 | 21.0 |
| **B0** (projection + 2-layer core looped 3x) | 2.06M | **85.28** | **84.52** (464/549) | 87.1 | 85.9 / 87.0 | 21.3 |

Paired bootstrap on DEV rows (95%): B0 - B0-nothinker = +2.22 (0.62, 3.75) on S, +4.19 (1.28, 6.92) on S_H. B0 - P0 = +17.57 (15.28, 19.86). B0 decodes in 2.6 ms/answer at batch 1 on CPU.

B0 errors on DEV short answers (212 wrong of 1,440): wrong location 92, right place but wrong edges 120, wrong mode 0. B0 is 88.9% on answers of 8 characters or fewer (n=1,233) and 63.8% on longer ones (n=207).

## Seeds 0-2 (B0 and B0-nothinker; P0 seed 0 only)

| arm | seed | S | S_H | yes/no | PRACTISED all |
|---|---|---|---|---|---|
| B0 | 0 / 1 / 2 | 85.28 / 84.93 / 86.39 | 84.52 / 82.88 / 85.61 | 87.1 / 86.8 / 86.5 | 87.0 / 85.9 / 88.1 |
| B0-nothinker | 0 / 1 / 2 | 83.06 / 84.31 / 82.64 | 80.33 / 81.60 / 79.96 | 84.9 / 84.6 / 84.5 | 84.4 / 85.1 / 84.8 |

Means: B0 S 85.53, S_H 84.34; B0-nothinker S 83.34, S_H 80.63. B0 is above B0-nothinker in all three seeds on both S and S_H (mean gap +2.2 on S, +3.7 on S_H). S_H(B0) is 84.52 / 82.88 / 85.61, so the 85 ceiling line sits inside the seed spread; the ceiling decision stays the seed-0 reading (see claim 1). (shown)

## What this shows

1. **Ceiling rule (pre-registered): S(B0) = 85.28 >= 80, so the headline switches to S_H. S_H(B0) = 84.52, which is below 85 by 0.48 points, so the "build nothing" branch does not fire by the letter of the rule.** This ceiling decision is the seed-0 reading, recorded before seeds 1 and 2 finished; seeds 1 and 2 are for mark 1's seed-matched comparison and are not used to re-decide the ceiling. The pass mark with S_H would need S_H(T) >= 94.5 (mark 1 asks +10 over B0). That leaves almost no headroom. (shown)
2. **On held-out TEACH kinds (DEV, TEST) the copytalk-style failure does not appear; on the sealed outside sets it does.** B0 scores 85% (DEV) and 82% (TEST) on kinds it never trained on, but 11% on pooled R5+R6 and 20% on FRESH-EN-R3 (see "Sealed check"). Held-out TEACH kinds are an easy test of transfer; the outside sets are the real one. (shown)
3. **The thinker helps a little, not a lot.** +2.2 points on S (+4.2 on S_H) over the same head with the layers removed, one seed. The bootstrap is over rows; it does not measure seed-to-seed variation. (shown in seed 0; it holds in seeds 1 and 2 too, see the seed table)
4. **P0 shows the answer location is not readable by a linear map alone** (67.7). The pointer head's query from the pooled state is worth +17.6 over it. (shown) P0 starts with a very large loss because its inputs are unnormalised (no LayerNorm, unlike the other arms); I did not change it. (suggested: P0 may be understated)
5. **Remaining weakness is boundaries on longer answers**: 120 of 212 errors have the right location and wrong edges; answers over 8 characters are 63.8%. (shown)
6. **TEACH-DEV does not separate unseen from practised kinds here.** B0 is 85.3 on DEV (unseen kinds) and 85.9 on PRACTISED; B0-nothinker 83.1 vs 84.0; P0 67.7 vs 66.0. PR #37's copytalk fell from 58.7 practised to 13.6 on unseen kinds; that drop is not reproduced. So a T1 win or loss on TEACH-DEV cannot answer "does a better talker transfer to new kinds"; the sealed R5/R6 sets (60.6% long answers, kinds outside TEACH) are the only place a transfer gap could show. (shown for the numbers)
7. **Question-sensitivity (DIAGNOSIS.md claim 2) is absent in B0.** DEV passages with two questions of different gold spans are rare (28 of 12,194 passages; TEACH is mostly one question per passage), so this is a small sample: B0 gave the identical span for 1 of 28 pairs (3.6%) and B0-nothinker 0 of 28, against 335/564 (59%) for copytalk on unseen kinds. B0 got the exact gold span on 51/56 of these rows. (shown, n=28 pairs; `probe_pairs_build.py`, `probe_pairs_eval.py`, `results/pairs_qsens.json`)
8. **The shuffled-state check drops every arm to about 20%** (nearly automatic here, since the notes are the talker's only view of the passage). It is not evidence against bypass. (shown, as SPEC.md predicted)

## Sealed check (run once, 2026-10-08 ET; B0, B0-nothinker, P0 only; no tuning on these sets)

Rows: each of the 96 questions per set scored on both its source text and its paraphrase = 192 rows per set (`seal_build.py`, `seal_eval.py`, `results/sealed_results.json`). Short-answer EM, mean over seeds 0-2 (P0: seed 0):

| set | B0 | B0-nothinker | P0 |
|---|---|---|---|
| TEST (held-out TEACH kinds, 3,000 rows) | 81.6 | 79.8 | 63.1 |
| FRESH-EN-R3 | 20.0 | 17.3 | 8.8 |
| GEN-HELDOUT-R4 | 17.0 | 16.3 | 13.6 |
| NEW-KINDS-R5 | 12.7 | 11.7 | 8.3 |
| NEW-KINDS2-R6 | 10.3 | 8.7 | 2.9 |
| **R5+R6 pooled (mark 6 set)** | **11.5** (11.2 / 11.2 / 12.1) | 10.2 (10.0 / 10.9 / 9.7) | 5.6 |

Paired bootstrap on pooled R5+R6 short answers: B0 - B0-nothinker = +1.18 (-2.35, 4.71), +0.29 (-2.94, 3.82), +2.35 (-0.88, 5.59) for seeds 0, 1, 2 (all intervals include 0). B0 - P0 = +5.59 (2.35, 9.12). On TEST: B0 - B0-nothinker = +0.9 (-0.76, 2.48), +0.3 (-1.45, 2.00), +4.1 (2.34, 5.72). Speed 2.6 ms/answer.

What this shows:
- **The talker gap is real on outside sets: 11-20% against 80-85% on held-out TEACH kinds.** It is the same size as PR #37's copytalk number (13.6%). (shown)
- **Question type explains part of it, not all.** TEACH's full train side (61,417 short-answer questions) opens with "who" 35,839 times, "what" 23,112 and "which" 2,450, and never with "where", "why", "when" or "how"; the held-out DEV (12,252) and TEST (8,940) kinds have the same zero, which is why they are an easy test. B0 short-answer EM by opener (mean of 3 seeds, n = questions per seed): TEST who 80% (1,055), what 87% (368). Outside sets, R3 who 45% (28), what 20% (54), which 8% (56), where 12% (20); R4 who 48% (22), what 16% (66), which 6% (60), where 6% (16); R5 what 26% (66), how 3% (30), when 2% (28), where 8% (26), why 2% (16); R6 how 5% (58), what 8% (56), which 21% (30), where 14% (28). So where/why/when/how are near 0, but who/what/which, the types TEACH does cover, also fall from 80-87% to 6-48% on outside sets. (shown)
- **Cause: untested which part dominates.** The outside sets differ from TEACH in made-up names, phrasing and passage style as well as question type; no run here separates them (that needs a training set with the new question types added, or outside-style who/what questions held out). Question-type coverage is a suggested contributor; broad style shift is also consistent with the data. (suggested)
- **Error mix on outside sets, B0 seed 0 (short answers; right / wrong place / right place wrong edges / yes-or-no instead of a span):** R3 35 / 74 / 46 / 13, R4 29 / 69 / 63 / 13, R5 20 / 64 / 43 / 41, R6 18 / 72 / 58 / 24 (R3 and R4 also have 2 unreachable each). Answering "yes"/"no" to a span question never happened on DEV and is a sign of the head not understanding the question type. (shown)
- **The thinker's +2 points on held-out TEACH kinds shrinks to +1 on R5+R6 and is not distinguishable from 0 there.** (shown)
- **The reader-side check is untested:** whether a pretrained LM talker (R) transfers better was not built, because Ben chose to stop on 2026-10-08 (the ceiling rule did not fire: 84.52 < 85).

Because this one-shot check is now spent, any later candidate needs a new unseen test set; reusing R3-R6 would no longer be a clean test.

## Not done

- P0 seeds 1 and 2 (untested). R, T1, T1-nothinker, T2 are not built (stopped after wave 1 by Ben's choice; the sealed check was run on B0, B0-nothinker, P0 only). Adding where/why/how-many question types to training is untested: it is the natural next experiment, not run here.
- Not compared against the real B2 talker (8-character GEN register, NUM path): B0 here is the SPEC.md stand-in (untested against B2).
- Agent context peaks for the three build agents: 77k, 68k and 49k tokens (all under 100k).

# Option C: T1, T1-nothinker, T2, T1-long (2026-10-08/09 ET, seeds 0-2, Mac/MPS, one job at a time)

Marks: SPEC.md Amendments 2, 2b, 2c (fixed before FRESH-R7 was read). Harness: `models_t1.py` (T1 character decoder with a pointer over the prompt, fed the thinker notes), `run_t.py` (same optimiser and 24,000 TEACH rows as `run_arm.py`, 3000 TEACH updates, batch 64, AdamW 1e-3, 200-update warm-up then cosine), `seal_eval_t.py` (FRESH-R7, refuses to run without `--final`, never overwrites). Queues: `run_queue.sh` (t1, t1_nothinker, t2), `run_queue_t1long.sh` (t1_long). Every number is from `results/<arm>_s<seed>/results.json`. B0 rows are the wave-1 runs above.

- **T1** = thinker notes (loop of 3) -> 4-layer, d=256 character decoder, 99-character vocabulary, trained on the say-back target `question + " " + answer`. The score reads only the answer part.
- **T1-nothinker** = T1 fed only the projection notes (no thinker layers).
- **T2** = T1 after 3000 updates of FineWeb-Edu recurring-span cloze (target `<cloze sentence> ? <span>`, 36,363 rows from 30,000 pages, 8-word-gram overlap with TEACH and every test set: 0), then the same 3000 TEACH updates.
- **T1-long** = T1 trained for 6000 TEACH updates (one warm-up/cosine), the same total updates as T2 without the FineWeb text.

## DEV (held-out TEACH kinds; S = short-answer EM on 1,440, S_H = 549 hard answers)

| arm | params | S, seeds 0 / 1 / 2 | mean S | S_H, seeds 0 / 1 / 2 | yes/no | wrong-notes S | ms/answer |
|---|---|---|---|---|---|---|---|
| B0 | 2.06M | 85.28 / 84.93 / 86.39 | 85.53 | 84.52 / 82.88 / 85.61 | 87.1 / 86.8 / 86.5 | 21.3 / 21.9 / 20.5 | 2.6 |
| T1 | 6.24M | 89.03 / 88.47 / 88.40 | 88.63 | 87.25 / 87.25 / 88.71 | 88.8 / 89.2 / 89.5 | 11.9 / 8.8 / 11.7 | 24-28 |
| T1-nothinker | 4.66M | 88.47 / 87.78 / 87.78 | 88.01 | 87.25 / 85.97 / 86.16 | 89.3 / 87.2 / 88.6 | 7.5 / 7.4 / 7.3 | 24 |
| T2 | 6.24M | 89.93 / 89.44 / 89.51 | 89.63 | 89.44 / 89.98 / 89.80 | 90.1 / 89.2 / 90.3 | 5.6 / 4.4 / 4.0 | 26-27 |
| T1-long | 6.24M | 89.58 / 89.58 / 89.44 | 89.54 | 89.25 / 88.89 / 88.71 | 90.5 / 89.5 / 89.9 | 11.9 / 10.4 / 11.4 | 24-25 |

DEV marks (Amendment 2, reported pass/fail; they decide nothing, R7 does):
- T1 - B0 >= 5 on S: **+3.10, fails** (+3.75 / +3.54 / +2.01 by seed). On S_H T1 - B0 = +3.40 (reported only; Amendment 2 puts the mark on S). (shown)
- T1 - T1-nothinker >= 10: **+0.62, fails** (+0.56 / +0.69 / +0.62). Expected in SPEC (B0's thinker added 2.2). (shown)
- T2 - T1 >= 3: **+1.00, fails** (+0.90 / +0.97 / +1.11). Positive in every seed. On S_H T2 - T1 = +2.0 (+2.19 / +2.73 / +1.09), reported only. (shown)
- T1-long - T1 (reported only): **+0.90** (+0.55 / +1.11 / +1.04). T2 - T1-long on DEV: **+0.09** (+0.35 / -0.14 / +0.07). On DEV, the T2 gain over T1 is about the size of what 3000 extra TEACH updates give. DEV only; R7 decides. (shown, DEV)
- Guards: S(T2) >= S(T1) - 2 passes in all seeds; wrong-notes drop >= 20 passes for every T arm (T1 drops 77-80 points); <= 25M params and <= 50 ms pass. (shown)

## FRESH-R7 (read once, 2026-10-09 ~12:35 ET; 320 rows = 160 questions x source/paraphrase; S = short-answer EM)

`seal_eval_t.py --final` ran once and finished without error. Output: `results/fresh_r7_results.json`, `results/fresh_r7_hits.json`, `results/fresh_r7_run.log`. Before the read, all 15 checkpoints were loaded and scored on TEST through the same script (pipeline check; TEST is not a mark).

| arm | S, seeds 0 / 1 / 2 | mean S |
|---|---|---|
| B0 | 14.37 / 15.62 / 15.62 | 15.21 |
| T1 | 0.94 / 1.56 / 2.19 | 1.56 |
| T1-nothinker | 0.94 / 1.88 / 0.62 | 1.15 |
| T2 | 3.44 / 2.81 / 2.19 | 2.81 |
| T1-long | 1.88 / 2.50 / 1.56 | 1.98 |

Marks (Amendments 2 and 2c; `pass_by_rows` decides, question-cluster interval is sensitivity only):

| mark | mean diff | row 95% CI | question-cluster 95% CI | per seed 0 / 1 / 2 | result |
|---|---|---|---|---|---|
| C1 T2 - T1 >= 3 | +1.25 | [+0.10, +2.29] | [-0.21, +2.60] | +2.50 / +1.25 / 0.00 | **fail** (under 3; seed 2 not > 0) |
| C1b T2 - T1-long >= 3 | +0.83 | [-0.21, +1.87] | [-0.42, +2.19] | +1.56 / +0.31 / +0.62 | **fail** (report-only under 2c, since C1 fails) |
| C2 T2 - B0 >= 5 | -12.40 | [-15.73, -8.96] | [-16.98, -8.12] | -10.94 / -12.81 / -13.44 | **fail** |
| C3 T1 - B0 (no mark) | -13.65 | [-17.19, -9.90] | [-18.54, -8.96] | -13.44 / -14.06 / -13.44 | reported |
| T1 - T1-nothinker | +0.42 | [0.00, +0.94] | [-0.10, +1.04] | 0.00 / -0.31 / +1.56 | reported |
| T1-long - T1 | +0.42 | [-0.31, +1.15] | [-0.42, +1.35] | +0.94 / +0.94 / -0.62 | report-only (2c) |

Secondary (descriptive, Amendment 2): T2 - T1 on practised openers (who/what/which, 128 rows) +3.39; never-practised openers (where/why/when/how, 192 rows) -0.17. Every T arm is near 0 on the never-practised openers, so this split cannot separate the two guesses. (suggested at most)

Reading:
- **The FineWeb practice did not pass.** C1 fails, so under Amendment 2c this run does not show that the FineWeb text helped. All four T arms sit at 1-3 % (about 3-11 of 320 rows), so the T2 - T1 comparison is at the floor: it shows neither help nor harm. Say "not shown to help", not "does not help". (shown: C1 fails; untested: whether FineWeb helps a talker that is off the floor)
- **The character say-back talker is far worse than B0 on the outside set.** T1 - B0 = -13.65, interval well below 0, about -13.5 in every seed. On DEV the same difference was +3.10. The talker beats B0 on held-out TEACH kinds and loses badly on fresh outside questions. (shown)
- **B0's scoring path behaves as before.** B0 scores 15.2 on R7, inside its wave-1 range of 11-20 % on R3-R6. (shown)
- **Test-set caveat.** R7 answers average 20.3 characters (TEACH train 4.6, R3-R6 7.8-11.0). 86 of 320 R7 say-back targets are longer than the longest TEACH train say-back (69 characters). R7 was written and hashed before any T training, so this does not void the read, but it tilts R7 against talkers that write their answers character by character. (shown: the lengths; untested: how much it matters)
- From the saved hits only (no second R7 read): every T arm scores 0 on the 86 rows longer than 69 characters, including T2, whose FineWeb targets reached 126 characters. On 1-word answers (54 rows) B0 scores 38.9 and T1 1.9. So length alone does not explain the gap. (shown, small n; cause untested)

## Run notes

- **Mac restarts (2).** The first came after two T1 runs finished training but before they saved; both were retrained from scratch with the same seed. The second came with three jobs running and memory full (macOS watchdog restart). After that: one job at a time, weights saved before scoring, `--eval-only` resume, and a queue that skips finished runs. No result was picked from a restart; each reported run is the one complete run for that arm and seed.
- **T2 target fix, before any T2 run.** The FineWeb practice target first lacked the ` ? ` separator SPEC asks for (`<cloze sentence> ? <span>`); `pretrain_target` in `run_t.py` was corrected before T2 seed 0 started.
- **Timing probe.** Amendment 2b's numbers were fixed after a 20-update timing probe that ran real T1 updates (seed 0, 0.31 s/update), so "before the first real T1 step" means before the first real training run; the probe model was not kept or used.
- **Amendment 2c** (T1-long always run, C1b, row interval decides) was added during the T1-nothinker runs, before any FRESH-R7 read, after a fact-check found that "T1-long only if C1 passes" would need a second R7 read.
- **One-read rule, written before FRESH-R7 was read.** `seal_eval_t.py --final` runs once. If it crashes partway, that read is void and documented here (SPEC: a bug found after seeing R7 voids the run), not quietly rerun. Before the read, all 15 checkpoints were loaded and scored on TEST through the same script (pipeline check, not a mark).
- Run times: T1-type ~10 min, T2 34-38 min, T1-long 34 min (seed 0, during heavy macOS background load), ~21 min (seeds 1, 2). All on the Mac, $0.
