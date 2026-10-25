# Dopamine-1 results (2026-10-25, one seed)

Qwen3-1.7B LoRA, one try per task, checks-only reward, 20 steps x 16 tasks, lr 1e-5. Held-out = the same 100
tasks for every arm, greedy, all checks must pass. Arms: base/none/value on Kaggle T4 (fp16; the value eval was
rerun alone after an out-of-memory crash), self/batch on BensPC (bf16). Raw files: /mnt/project-files/dopamine1/.

| arm | held-out success | train reward, steps 1-5 -> 16-20 | mean abs(delta), steps 1-5 -> 16-20 |
|---|---|---|---|
| base (untrained) | 25 | - | - |
| d_none (A = r) | 27 | 0.367 -> 0.340 | - |
| d_value (A = r - V[type]) | 21 | 0.390 -> 0.371 | 0.334 -> 0.196 |
| d_self (A = r - own guess) | 27 | 0.350 -> 0.356 | 0.565 -> 0.573 |
| d_batch (A = r - batch mean) | 26 | 0.358 -> 0.346 | 0.362 -> 0.323 |

Paired exact McNemar on the shared 100 tasks (number only arm A solved / number only arm B solved, p):
value vs none 0/6 p=0.031; value vs base 1/5 p=0.22; value vs batch 0/5 p=0.06; self vs none 2/2 p=1;
self vs value 7/1 p=0.07; batch vs none 1/2 p=1; none vs base 3/1 p=0.63.

## Verdicts against the preregistered marks

- P1 (d_value >= d_none + 5): FAIL. PROVED WRONG (d_value <= d_none). Shown at p=0.03 on this seed: the
  running-average dopamine arm did worse than plain.
- P2 (d_value >= base + 5): FAIL (21 vs 25). The harm alarm (5 or more below base) was not triggered (-4).
- P3 (the expectation is real): PASS. mean abs(delta) fell from 0.33 to 0.20. The learned values are sensible:
  direct_answer 0.85, clarify 0.60, single_tool 0.50, multi_step 0.09, error_recovery 0.08, summarize_long 0.06.
- S1 (d_self >= d_none + 5): FAIL. PROVED WRONG (27 = 27).
- S2 (d_self vs d_value): +6 for self (p=0.07), which is moot because self only ties plain.
- S3 (the untrained model's guesses track success, corr >= 0.2): FAIL. corr 0.17 on held-out. During training,
  corr was -0.01 and the mean guess 0.87 against a mean reward of 0.37. The 1.7B model's stated guesses are noise.
- B1 (d_batch >= d_none + 5): FAIL (tie). B2 (d_value >= d_batch + 5): FAIL.

## What this means

- Shown (this seed): the model learned what to expect from each task type, but using that expectation as the
  training baseline made held-out success worse than no baseline. A likely cause, untested: the hard types have
  V about 0.08, so their partial tries got large positive pushes, and the easy types' partial tries got pushed
  down.
- Shown: no arm's training reward rose (all flat at 0.34-0.39). At lr 1e-5 with 320 single tries, single-try RL
  barely moved the model in any arm. The test therefore has little power to rank baselines, except for the one
  harm it found.
- Shown: a 1.7B model's own success guess is not usable as a baseline without training it first.

## Next (one change)

Make plain single-try learning move first, otherwise baseline comparisons are noise. Dopamine-2: d_none and
d_value at lr 1e-4 (10x), same everything else. Pass mark: d_none >= base + 5. Then d_value >= d_none + 5. If
d_none at 1e-4 is still within 5 of base, single-try RL at this scale doesn't learn, and the nightly update
should use correction pairs (DPO/KTO, see lit-user-feedback.md) instead of a reward baseline.
