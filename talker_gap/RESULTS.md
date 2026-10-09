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
2. **The copytalk-style failure does not appear in this harness.** A non-autoregressive pointer head that reads contextual reader states of "passage + question" scores 85% on kinds it never saw, against 13.6% for PR #37's copytalk head on unseen kinds. This run changes several things at once (reader, head, data size, question in the reader input), so it does not say which one fixed it. (shown for the numbers; the cause is suggested: PR #37's head had no question input and 59% of different questions got identical spans, see DIAGNOSIS.md)
3. **The thinker helps a little, not a lot.** +2.2 points on S (+4.2 on S_H) over the same head with the layers removed, one seed. The bootstrap is over rows; it does not measure seed-to-seed variation. (shown in seed 0; it holds in seeds 1 and 2 too, see the seed table)
4. **P0 shows the answer location is not readable by a linear map alone** (67.7). The pointer head's query from the pooled state is worth +17.6 over it. (shown) P0 starts with a very large loss because its inputs are unnormalised (no LayerNorm, unlike the other arms); I did not change it. (suggested: P0 may be understated)
5. **Remaining weakness is boundaries on longer answers**: 120 of 212 errors have the right location and wrong edges; answers over 8 characters are 63.8%. (shown)
6. **TEACH-DEV does not separate unseen from practised kinds here.** B0 is 85.3 on DEV (unseen kinds) and 85.9 on PRACTISED; B0-nothinker 83.1 vs 84.0; P0 67.7 vs 66.0. PR #37's copytalk fell from 58.7 practised to 13.6 on unseen kinds; that drop is not reproduced. So a T1 win or loss on TEACH-DEV cannot answer "does a better talker transfer to new kinds"; the sealed R5/R6 sets (60.6% long answers, kinds outside TEACH) are the only place a transfer gap could show. (shown for the numbers)
7. **Question-sensitivity (DIAGNOSIS.md claim 2) is absent in B0.** DEV passages with two questions of different gold spans are rare (28 of 12,194 passages; TEACH is mostly one question per passage), so this is a small sample: B0 gave the identical span for 1 of 28 pairs (3.6%) and B0-nothinker 0 of 28, against 335/564 (59%) for copytalk on unseen kinds. B0 got the exact gold span on 51/56 of these rows. (shown, n=28 pairs; `probe_pairs_build.py`, `probe_pairs_eval.py`, `results/pairs_qsens.json`)
8. **The shuffled-state check drops every arm to about 20%** (nearly automatic here, since the notes are the talker's only view of the passage). It is not evidence against bypass. (shown, as SPEC.md predicted)

## Not done

- Seeds 1 and 2 for P0 (untested). R, T1, T1-nothinker, T2 are not built (SPEC.md: built only after wave 1 reports). Sealed R5+R6 check not run.
- Not compared against the real B2 talker (8-character GEN register, NUM path): B0 here is the SPEC.md stand-in (untested against B2).
- Agent context peaks for the three build agents: 77k, 68k and 49k tokens (all under 100k).
